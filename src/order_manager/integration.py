"""
Order Manager Integration

Seamless integration of the new order management system with
the existing execution framework while maintaining backward compatibility.
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from .manager import OrderManager, OrderManagerConfig
from .models import OrderRequest, OrderType, OrderState
from .executors import EnhancedPaperExecutor, EnhancedCCXTExecutor
from .twap import TWAPConfig
from .vwap import VWAPConfig
from .retry import RetryConfig


class OrderManagerAdapter:
    """Adapter to integrate OrderManager with existing ExecutionManager."""
    
    def __init__(self, order_manager: OrderManager):
        self.order_manager = order_manager
        self.logger = logging.getLogger(__name__)
        
        # Map existing execution modes to order manager
        self.execution_mode_map = {
            'paper': 'paper',
            'live': 'binance'  # Default live exchange
        }
    
    def execute_buy_order(self, symbol: str, coin_id: str, current_price: float, confidence: float) -> bool:
        """Execute buy order using order manager."""
        try:
            # Create order request
            order_request = OrderRequest(
                symbol=symbol,
                side='buy',
                order_type=OrderType.MARKET,
                quantity=self._calculate_position_size(symbol, current_price, confidence),
                price=current_price,
                strategy_id=f"strategy_{coin_id}"
            )
            
            # Place order
            order = self.order_manager.place_order(order_request)
            
            self.logger.info(f"Placed buy order {order.id} for {symbol}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error placing buy order for {symbol}: {e}")
            return False
    
    def execute_sell_order(self, symbol: str, coin_id: str, current_price: float, reason: str) -> bool:
        """Execute sell order using order manager."""
        try:
            # Create order request
            order_request = OrderRequest(
                symbol=symbol,
                side='sell',
                order_type=OrderType.MARKET,
                quantity=self._get_position_size(symbol),
                price=current_price,
                strategy_id=f"strategy_{coin_id}"
            )
            
            # Place order
            order = self.order_manager.place_order(order_request)
            
            self.logger.info(f"Placed sell order {order.id} for {symbol}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error placing sell order for {symbol}: {e}")
            return False
    
    def _calculate_position_size(self, symbol: str, price: float, confidence: float) -> float:
        """Calculate position size based on confidence and risk management."""
        # This would integrate with existing position sizing logic
        base_size = 50.0  # Default size
        confidence_multiplier = min(confidence, 1.0)
        return base_size * confidence_multiplier / price
    
    def _get_position_size(self, symbol: str) -> float:
        """Get current position size for symbol."""
        # This would integrate with existing portfolio management
        return 1.0  # Placeholder
    
    def get_execution_status(self) -> Dict[str, Any]:
        """Get execution status compatible with existing system."""
        stats = self.order_manager.get_order_statistics()
        
        return {
            'active_orders': stats['active_orders'],
            'total_orders': stats['total_orders'],
            'orders_by_state': stats['orders_by_state'],
            'orders_by_exchange': stats['orders_by_exchange'],
            'retry_statistics': stats['retry_statistics']
        }


class OrderManagerIntegration:
    """Handles integration of order manager with existing tracker system."""
    
    def __init__(self, tracker):
        self.tracker = tracker
        self.logger = logging.getLogger(__name__)
        self.order_manager: Optional[OrderManager] = None
        self.adapter: Optional[OrderManagerAdapter] = None
    
    def initialize_order_manager(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """Initialize order manager with configuration."""
        try:
            # Create order manager configuration
            om_config = self._create_order_manager_config(config)
            
            # Initialize order manager
            self.order_manager = OrderManager(
                config_manager=self.tracker.config_manager,
                portfolio_manager=self.tracker.portfolio_manager,
                risk_manager=self.tracker.risk_manager,
                config=om_config
            )
            
            # Register existing executors
            self._register_existing_executors()
            
            # Create adapter
            self.adapter = OrderManagerAdapter(self.order_manager)
            
            # Replace execution manager
            self.tracker.execution_manager = self.adapter
            
            self.logger.info("Order manager initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing order manager: {e}")
            return False
    
    def _create_order_manager_config(self, config: Optional[Dict[str, Any]]) -> OrderManagerConfig:
        """Create order manager configuration from tracker config."""
        if config is None:
            config = {}
        
        # Extract configuration from tracker
        try:
            full_config = self.tracker.config_manager.load_full_config()
            order_config = full_config.get('order_manager', {})
        except Exception:
            order_config = {}
        
        # Create retry config
        retry_config = RetryConfig(
            max_retries=order_config.get('retry', {}).get('max_attempts', 3),
            base_delay_seconds=order_config.get('retry', {}).get('base_delay_seconds', 1.0),
            max_delay_seconds=order_config.get('retry', {}).get('max_delay_seconds', 30.0)
        )
        
        # Create TWAP config
        twap_config = TWAPConfig(
            min_slice_size_usd=order_config.get('twap', {}).get('min_slice_size_usd', 100.0),
            max_slices=order_config.get('twap', {}).get('max_slices', 20),
            min_slice_interval_seconds=order_config.get('twap', {}).get('min_slice_interval_seconds', 30)
        )
        
        # Create VWAP config
        vwap_config = VWAPConfig(
            participation_rate=order_config.get('vwap', {}).get('participation_rate', 0.1),
            max_participation_rate=order_config.get('vwap', {}).get('max_participation_rate', 0.2),
            min_slice_size_usd=order_config.get('vwap', {}).get('min_slice_size_usd', 100.0)
        )
        
        return OrderManagerConfig(
            max_active_orders=order_config.get('max_active_orders', 1000),
            order_timeout_minutes=order_config.get('order_timeout_minutes', 60),
            reconciliation_interval_minutes=order_config.get('reconciliation_interval_minutes', 5),
            retry_config=retry_config,
            twap_config=twap_config,
            vwap_config=vwap_config,
            enable_smart_routing=order_config.get('routing', {}).get('enabled', True),
            enable_reconciliation=order_config.get('reconciliation', {}).get('enabled', True),
            enable_circuit_breaker=order_config.get('circuit_breaker', {}).get('enabled', True)
        )
    
    def _register_existing_executors(self) -> None:
        """Register existing executors with order manager."""
        if not self.order_manager:
            return
        
        # Register paper executor
        if hasattr(self.tracker, 'paper'):
            paper_executor = EnhancedPaperExecutor()
            self.order_manager.register_executor('paper', paper_executor)
        
        # Register live executor
        if hasattr(self.tracker, 'live_executor') and self.tracker.live_executor:
            live_executor = EnhancedCCXTExecutor(
                self.tracker.live_executor,
                self.order_manager
            )
            exchange_name = getattr(self.tracker.live_executor.ex, 'id', 'unknown')
            self.order_manager.register_executor(exchange_name, live_executor)
    
    def get_order_manager(self) -> Optional[OrderManager]:
        """Get the order manager instance."""
        return self.order_manager
    
    def get_adapter(self) -> Optional[OrderManagerAdapter]:
        """Get the adapter instance."""
        return self.adapter
    
    def is_initialized(self) -> bool:
        """Check if order manager is initialized."""
        return self.order_manager is not None and self.adapter is not None


def integrate_order_manager(tracker, config: Optional[Dict[str, Any]] = None) -> bool:
    """Convenience function to integrate order manager with tracker."""
    integration = OrderManagerIntegration(tracker)
    return integration.initialize_order_manager(config)
