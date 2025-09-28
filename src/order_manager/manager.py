"""
Order Manager

Main orchestrator for the order management system, coordinating
order placement, execution, state management, and reconciliation.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import logging
import uuid

from .models import (
    Order, OrderRequest, OrderResult, OrderState, OrderType,
    OrderValidationError, OrderNotFoundError, OrderAlreadyExistsError
)
from .state_machine import OrderStateMachine
from .executors import BaseExecutor, EnhancedPaperExecutor, EnhancedCCXTExecutor
from .routing import SmartOrderRouter
from .retry import OrderRetryManager, RetryConfig
from .cancellation import OrderCancellationManager
from .reconciliation import OrderReconciler
from .twap import TWAPSlicer, TWAPConfig
from .vwap import VWAPSlicer, VWAPConfig


@dataclass
class OrderManagerConfig:
    """Configuration for order manager."""
    max_active_orders: int = 1000
    order_timeout_minutes: int = 60
    reconciliation_interval_minutes: int = 5
    retry_config: Optional[RetryConfig] = None
    twap_config: Optional[TWAPConfig] = None
    vwap_config: Optional[VWAPConfig] = None
    enable_smart_routing: bool = True
    enable_reconciliation: bool = True
    enable_circuit_breaker: bool = True


class OrderManager:
    """Main order management orchestrator."""
    
    def __init__(self, config_manager, portfolio_manager, risk_manager, config: Optional[OrderManagerConfig] = None):
        self.config_manager = config_manager
        self.portfolio_manager = portfolio_manager
        self.risk_manager = risk_manager
        self.config = config or OrderManagerConfig()
        
        # Core components
        self.state_machine = OrderStateMachine()
        self.smart_router = SmartOrderRouter()
        self.retry_manager = OrderRetryManager(self.config.retry_config)
        self.cancellation_manager = OrderCancellationManager(self)
        self.reconciler = OrderReconciler(self)
        self.twap_slicer = TWAPSlicer(self.config.twap_config)
        self.vwap_slicer = VWAPSlicer(self.config.vwap_config)
        
        # Order tracking
        self.active_orders: Dict[str, Order] = {}
        self.order_history: List[Order] = []
        self.executors: Dict[str, BaseExecutor] = {}
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = {
            'order_placed': [],
            'order_filled': [],
            'order_canceled': [],
            'order_rejected': [],
            'order_error': []
        }
        
        self.logger = logging.getLogger(__name__)
        
        # Initialize default executors
        self._initialize_default_executors()
    
    def _initialize_default_executors(self) -> None:
        """Initialize default executors."""
        # Paper executor
        paper_executor = EnhancedPaperExecutor()
        self.register_executor("paper", paper_executor)
        
        # Register with smart router
        if self.config.enable_smart_routing:
            self.smart_router.register_executor("paper", paper_executor)
    
    def register_executor(self, exchange_name: str, executor: BaseExecutor) -> None:
        """Register an executor for order execution."""
        self.executors[exchange_name] = executor
        
        if self.config.enable_smart_routing:
            self.smart_router.register_executor(exchange_name, executor)
        
        self.logger.info(f"Registered executor for exchange: {exchange_name}")
    
    def unregister_executor(self, exchange_name: str) -> None:
        """Unregister an executor."""
        if exchange_name in self.executors:
            del self.executors[exchange_name]
        
        if self.config.enable_smart_routing:
            self.smart_router.unregister_executor(exchange_name)
        
        self.logger.info(f"Unregistered executor for exchange: {exchange_name}")
    
    def place_order(self, order_request: OrderRequest) -> Order:
        """Place a new order."""
        try:
            # Validate order request
            validation_result = self._validate_order_request(order_request)
            if not validation_result.is_valid:
                raise OrderValidationError(validation_result)
            
            # Check if we can accept more orders
            if len(self.active_orders) >= self.config.max_active_orders:
                from .models import OrderValidationResult
                validation_result = OrderValidationResult(is_valid=False)
                validation_result.add_error(f"Maximum active orders ({self.config.max_active_orders}) exceeded")
                raise OrderValidationError(validation_result)
            
            # Create order
            order = self._create_order(order_request)
            
            # Check for duplicate orders
            if order.id in self.active_orders:
                raise OrderAlreadyExistsError(f"Order {order.id} already exists")
            
            # Store order
            self.active_orders[order.id] = order
            
            # Execute order
            self._execute_order(order)
            
            # Emit event
            self._emit_event('order_placed', order)
            
            self.logger.info(f"Placed order {order.id}: {order.symbol} {order.side} {order.quantity}")
            return order
            
        except Exception as e:
            self.logger.error(f"Error placing order: {e}")
            raise
    
    def cancel_order(self, order_id: str, reason: str = "manual") -> bool:
        """Cancel an order."""
        return self.cancellation_manager.cancel_order(order_id, reason).success
    
    def cancel_all_orders(self, symbol: Optional[str] = None, reason: str = "bulk_cancel") -> int:
        """Cancel all active orders."""
        results = self.cancellation_manager.cancel_all_orders(symbol, reason)
        return sum(1 for result in results if result.success)
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        return self.active_orders.get(order_id)
    
    def get_active_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get all active orders, optionally filtered by symbol."""
        orders = []
        for order in self.active_orders.values():
            if order.is_active and (symbol is None or order.symbol == symbol):
                orders.append(order)
        return orders
    
    def get_orders_by_strategy(self, strategy_id: str) -> List[Order]:
        """Get all orders for a specific strategy."""
        orders = []
        for order in self.active_orders.values():
            if order.strategy_id == strategy_id:
                orders.append(order)
        return orders
    
    def get_executor(self, exchange_name: str) -> Optional[BaseExecutor]:
        """Get executor for exchange."""
        return self.executors.get(exchange_name)
    
    def reconcile_orders(self, force: bool = False) -> Any:
        """Reconcile orders with exchange state."""
        if not self.config.enable_reconciliation:
            return None
        
        return self.reconciler.reconcile_orders(force)
    
    def get_order_statistics(self) -> Dict[str, Any]:
        """Get order management statistics."""
        total_orders = len(self.active_orders)
        active_orders = len([o for o in self.active_orders.values() if o.is_active])
        
        orders_by_state = {}
        for order in self.active_orders.values():
            state = order.state.value
            orders_by_state[state] = orders_by_state.get(state, 0) + 1
        
        orders_by_exchange = {}
        for order in self.active_orders.values():
            exchange = order.exchange
            orders_by_exchange[exchange] = orders_by_exchange.get(exchange, 0) + 1
        
        return {
            'total_orders': total_orders,
            'active_orders': active_orders,
            'orders_by_state': orders_by_state,
            'orders_by_exchange': orders_by_exchange,
            'registered_executors': list(self.executors.keys()),
            'retry_statistics': self.retry_manager.get_retry_statistics(),
            'routing_statistics': self.smart_router.get_exchange_statistics() if self.config.enable_smart_routing else {}
        }
    
    def add_event_handler(self, event_type: str, handler: Callable) -> None:
        """Add event handler for order events."""
        if event_type in self.event_handlers:
            self.event_handlers[event_type].append(handler)
    
    def remove_event_handler(self, event_type: str, handler: Callable) -> None:
        """Remove event handler."""
        if event_type in self.event_handlers and handler in self.event_handlers[event_type]:
            self.event_handlers[event_type].remove(handler)
    
    def _validate_order_request(self, order_request: OrderRequest) -> Any:
        """Validate order request."""
        from .models import OrderValidationResult
        
        result = OrderValidationResult(is_valid=True)
        
        # Basic validation
        if order_request.quantity <= 0:
            result.add_error("Quantity must be positive")
        
        if order_request.side not in ['buy', 'sell']:
            result.add_error("Side must be 'buy' or 'sell'")
        
        if order_request.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT] and order_request.price is None:
            result.add_error("Price is required for limit orders")
        
        if order_request.order_type == OrderType.STOP_LIMIT and order_request.stop_price is None:
            result.add_error("Stop price is required for stop-limit orders")
        
        # TWAP/VWAP validation
        if order_request.order_type == OrderType.TWAP:
            if order_request.twap_duration_seconds is None or order_request.twap_duration_seconds <= 0:
                result.add_error("TWAP duration must be positive")
        
        if order_request.order_type == OrderType.VWAP:
            if order_request.vwap_participation_rate is None or order_request.vwap_participation_rate <= 0:
                result.add_error("VWAP participation rate must be positive")
        
        return result
    
    def _create_order(self, order_request: OrderRequest) -> Order:
        """Create order from request."""
        order_id = str(uuid.uuid4())
        
        # Determine exchange
        exchange = order_request.preferred_exchange or order_request.exchange or "paper"
        
        # Create order
        order = Order(
            id=order_id,
            client_order_id=order_request.client_order_id or order_id,
            symbol=order_request.symbol,
            side=order_request.side,
            order_type=order_request.order_type,
            state=OrderState.NEW,
            quantity=order_request.quantity,
            price=order_request.price,
            stop_price=order_request.stop_price,
            time_in_force=order_request.time_in_force,
            exchange=exchange,
            strategy_id=order_request.strategy_id,
            max_slippage_bps=order_request.max_slippage_bps,
            min_fill_size=order_request.min_fill_size,
            twap_duration_seconds=order_request.twap_duration_seconds,
            twap_slice_size=order_request.twap_slice_size,
            vwap_reference_price=order_request.vwap_reference_price,
            vwap_participation_rate=order_request.vwap_participation_rate,
            tags=order_request.tags
        )
        
        return order
    
    def _execute_order(self, order: Order) -> None:
        """Execute order using appropriate executor."""
        try:
            # Handle different order types
            if order.order_type == OrderType.TWAP:
                self._execute_twap_order(order)
            elif order.order_type == OrderType.VWAP:
                self._execute_vwap_order(order)
            else:
                self._execute_simple_order(order)
            
        except Exception as e:
            self.logger.error(f"Error executing order {order.id}: {e}")
            self.state_machine.transition(order, OrderState.REJECTED, "execution_error")
            order.last_error = str(e)
            self._emit_event('order_error', order)
    
    def _execute_twap_order(self, order: Order) -> None:
        """Execute TWAP order."""
        try:
            # Select executor
            if self.config.enable_smart_routing:
                executor = self.smart_router.select_executor(order)
            else:
                executor = self.get_executor(order.exchange)
                if not executor:
                    raise RuntimeError(f"No executor found for exchange {order.exchange}")
            
            # Create TWAP execution
            self.twap_slicer.create_twap_order(order, executor)
            
            # Update order state
            self.state_machine.transition(order, OrderState.PENDING, "twap_started")
            
            self.logger.info(f"Started TWAP execution for order {order.id}")
            
        except Exception as e:
            self.logger.error(f"Error starting TWAP order {order.id}: {e}")
            raise
    
    def _execute_vwap_order(self, order: Order) -> None:
        """Execute VWAP order."""
        try:
            # Select executor
            if self.config.enable_smart_routing:
                executor = self.smart_router.select_executor(order)
            else:
                executor = self.get_executor(order.exchange)
                if not executor:
                    raise RuntimeError(f"No executor found for exchange {order.exchange}")
            
            # Create VWAP execution
            self.vwap_slicer.create_vwap_order(order, executor)
            
            # Update order state
            self.state_machine.transition(order, OrderState.PENDING, "vwap_started")
            
            self.logger.info(f"Started VWAP execution for order {order.id}")
            
        except Exception as e:
            self.logger.error(f"Error starting VWAP order {order.id}: {e}")
            raise
    
    def _execute_simple_order(self, order: Order) -> None:
        """Execute simple order (market, limit, etc.)."""
        try:
            # Select executor
            if self.config.enable_smart_routing:
                executor = self.smart_router.select_executor(order)
            else:
                executor = self.get_executor(order.exchange)
                if not executor:
                    raise RuntimeError(f"No executor found for exchange {order.exchange}")
            
            # Convert order to order request for execution
            order_request = OrderRequest(
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                quantity=order.quantity,
                price=order.price,
                stop_price=order.stop_price,
                time_in_force=order.time_in_force,
                client_order_id=order.client_order_id,
                strategy_id=order.strategy_id
            )
            
            # Execute with retry logic
            def execution_func(order: Order) -> OrderResult:
                return executor.place_order(order_request)
            
            result = self.retry_manager.execute_with_retry(order, executor, execution_func)
            
            # Update order state based on result
            if result.success:
                # First transition to PENDING
                self.state_machine.transition(order, OrderState.PENDING, "execution")
                
                # Then transition to final state if provided
                if result.state and result.state != OrderState.PENDING:
                    self.state_machine.transition(order, result.state, "execution_complete")
                
                # Update exchange order ID
                if result.exchange_order_id:
                    order.exchange_order_id = result.exchange_order_id
            else:
                self.state_machine.transition(order, OrderState.REJECTED, "execution_failed")
                order.last_error = result.error_message
                self._emit_event('order_rejected', order)
            
        except Exception as e:
            self.logger.error(f"Error executing simple order {order.id}: {e}")
            raise
    
    def _emit_event(self, event_type: str, order: Order) -> None:
        """Emit order event to registered handlers."""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    handler(order)
                except Exception as e:
                    self.logger.error(f"Error in event handler for {event_type}: {e}")
    
    def cleanup_expired_orders(self) -> int:
        """Clean up expired orders."""
        expired_count = 0
        cutoff_time = datetime.now() - timedelta(minutes=self.config.order_timeout_minutes)
        
        orders_to_remove = []
        for order_id, order in self.active_orders.items():
            if order.created_at < cutoff_time and order.is_active:
                orders_to_remove.append(order_id)
        
        for order_id in orders_to_remove:
            order = self.active_orders[order_id]
            self.state_machine.transition(order, OrderState.EXPIRED, "timeout")
            expired_count += 1
        
        return expired_count
    
    def get_order_lifecycle_summary(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get lifecycle summary for an order."""
        order = self.get_order(order_id)
        if not order:
            return None
        
        return self.state_machine.get_order_lifecycle_summary(order_id)
    
    def get_twap_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get TWAP order status."""
        return self.twap_slicer.get_twap_status(order_id)
    
    def get_vwap_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get VWAP order status."""
        return self.vwap_slicer.get_vwap_status(order_id)
    
    def cancel_twap_order(self, order_id: str) -> bool:
        """Cancel TWAP order."""
        return self.twap_slicer.cancel_twap_order(order_id)
    
    def cancel_vwap_order(self, order_id: str) -> bool:
        """Cancel VWAP order."""
        return self.vwap_slicer.cancel_vwap_order(order_id)
