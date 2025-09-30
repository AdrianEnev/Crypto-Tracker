"""
Paper Broker Implementation

A comprehensive paper trading broker that implements the AbstractBroker interface
and provides realistic order execution simulation with configurable slippage,
fees, and latency.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.order_manager.models import Order, OrderRequest, OrderResult, OrderState, OrderType

from .broker import AbstractBroker, AccountBalance, Position, AccountInfo, BrokerError
from .execution import ExecutionSimulator, SlippageConfig, FeeConfig, LatencyConfig
from .portfolio import PaperPortfolio


class PaperBroker(AbstractBroker):
    """Paper trading broker with realistic execution simulation."""
    
    def __init__(
        self,
        initial_cash: float = 100000.0,
        base_currency: str = "USDT",
        slippage_config: Optional[SlippageConfig] = None,
        fee_config: Optional[FeeConfig] = None,
        latency_config: Optional[LatencyConfig] = None,
        random_seed: Optional[int] = None,
        supported_symbols: Optional[List[str]] = None
    ):
        super().__init__("PaperBroker")
        
        # Default configurations
        self.slippage_config = slippage_config or SlippageConfig()
        self.fee_config = fee_config or FeeConfig()
        self.latency_config = latency_config or LatencyConfig()
        
        # Initialize portfolio
        self.portfolio = PaperPortfolio(initial_cash, base_currency)
        
        # Initialize execution simulator
        self.execution_simulator = ExecutionSimulator(
            self.slippage_config,
            self.fee_config,
            self.latency_config,
            random_seed
        )
        
        # Order management
        self.orders: Dict[str, Order] = {}
        self.order_counter = 0
        
        # Market data cache
        self.ticker_cache: Dict[str, Dict[str, Any]] = {}
        self.orderbook_cache: Dict[str, Dict[str, Any]] = {}
        
        # Supported symbols
        self._supported_symbols = supported_symbols or [
            "BTC/USDT", "ETH/USDT", "BNB/USDT", "ADA/USDT", "SOL/USDT",
            "DOT/USDT", "LINK/USDT", "LTC/USDT", "BCH/USDT", "XRP/USDT",
            "AVAX/USDT", "MATIC/USDT", "UNI/USDT", "ATOM/USDT", "NEAR/USDT"
        ]
        
        # Connection state
        self.is_connected = True  # Paper broker is always "connected"
    
    def connect(self) -> bool:
        """Connect to the paper broker (always succeeds)."""
        self.is_connected = True
        return True
    
    def disconnect(self) -> bool:
        """Disconnect from the paper broker."""
        self.is_connected = False
        return True
    
    def place_order(self, order_request: OrderRequest) -> OrderResult:
        """Place a new order."""
        
        if not self.is_connected:
            return OrderResult(
                order_id="",
                success=False,
                error_message="Broker not connected"
            )
        
        # Validate order request
        if not self.validate_order_request(order_request):
            return OrderResult(
                order_id="",
                success=False,
                error_message="Invalid order request"
            )
        
        # Generate order ID
        order_id = self._generate_order_id()
        
        # Create order
        order = Order(
            id=order_id,
            client_order_id=order_request.client_order_id or str(uuid.uuid4()),
            symbol=order_request.symbol,
            side=order_request.side,
            order_type=order_request.order_type,
            state=OrderState.NEW,
            quantity=order_request.quantity,
            price=order_request.price,
            stop_price=order_request.stop_price,
            time_in_force=order_request.time_in_force,
            exchange="paper",
            strategy_id=order_request.strategy_id
        )
        
        # Store order
        self.orders[order_id] = order
        
        # Execute order synchronously for compatibility
        try:
            # Get current market price synchronously
            current_price = self._get_current_price_sync(order.symbol)
            if current_price is None:
                self._update_order_state(order, OrderState.REJECTED, "No market data available")
                return OrderResult(
                    order_id=order_id,
                    success=False,
                    error="No market data available",
                    state=OrderState.REJECTED
                )
            
            # Simulate execution
            execution_price, fee, slippage = self._simulate_execution(order, current_price)
            
            # Execute trade in portfolio
            success = self.portfolio.execute_trade(
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                price=execution_price,
                fee=fee,
                order_id=order_id
            )
            
            if success:
                self._update_order_state(order, OrderState.FILLED, f"Filled at {execution_price}")
            else:
                self._update_order_state(order, OrderState.REJECTED, "Insufficient funds")
                
        except Exception as e:
            self._update_order_state(order, OrderState.REJECTED, str(e))
        
        return OrderResult(
            order_id=order_id,
            success=True,
            exchange_order_id=order_id,
            state=order.state
        )
    
    async def _execute_order(self, order: Order):
        """Execute an order asynchronously."""
        
        try:
            # Get current market price
            current_price = await self._get_current_price(order.symbol)
            if current_price is None:
                self._update_order_state(order, OrderState.REJECTED, "No market data available")
                return
            
            # Update order state to pending
            self._update_order_state(order, OrderState.PENDING)
            
            # Simulate execution
            execution_price, fee, slippage = await self.execution_simulator.simulate_execution(
                OrderRequest(
                    symbol=order.symbol,
                    side=order.side,
                    order_type=order.order_type,
                    quantity=order.quantity,
                    price=order.price
                ),
                current_price,
                self.orderbook_cache.get(order.symbol),
                None  # volatility
            )
            
            # Execute trade in portfolio
            success = self.portfolio.execute_trade(
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                price=execution_price,
                fee=fee,
                order_id=order.id,
                strategy_id=order.strategy_id
            )
            
            if success:
                # Update order with fill information
                order.update_fill(order.quantity, execution_price)
                self._update_order_state(order, OrderState.FILLED)
            else:
                self._update_order_state(order, OrderState.REJECTED, "Insufficient funds")
        
        except Exception as e:
            self._update_order_state(order, OrderState.REJECTED, str(e))
    
    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an existing order."""
        
        if order_id not in self.orders:
            return False
        
        order = self.orders[order_id]
        
        # Only cancel active orders
        if order.is_active:
            self._update_order_state(order, OrderState.CANCELED, "Cancelled by user")
            return True
        
        return False
    
    def get_order_status(self, order_id: str, symbol: str) -> Optional[OrderState]:
        """Get current order status."""
        
        if order_id not in self.orders:
            return None
        
        return self.orders[order_id].state
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get all open orders."""
        
        open_orders = []
        
        for order in self.orders.values():
            if order.is_active and (symbol is None or order.symbol == symbol):
                open_orders.append(order)
        
        return open_orders
    
    def get_account_info(self) -> AccountInfo:
        """Get complete account information."""
        return self.portfolio.get_account_info()
    
    def get_balance(self, currency: str) -> Optional[AccountBalance]:
        """Get balance for a specific currency."""
        return self.portfolio.get_balance(currency)
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a specific symbol."""
        return self.portfolio.get_position(symbol)
    
    def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current ticker information for a symbol."""
        return self.ticker_cache.get(symbol)
    
    def get_orderbook(self, symbol: str, limit: int = 100) -> Optional[Dict[str, Any]]:
        """Get order book for a symbol."""
        return self.orderbook_cache.get(symbol)
    
    def validate_order_request(self, order_request: OrderRequest) -> bool:
        """Validate order request before execution."""
        
        # Basic validation
        if order_request.quantity <= 0:
            return False
        
        if order_request.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT] and order_request.price is None:
            return False
        
        if order_request.order_type == OrderType.STOP_LIMIT and order_request.stop_price is None:
            return False
        
        # Check if symbol is supported
        if order_request.symbol not in self.supported_symbols:
            return False
        
        # Check sufficient funds for buy orders
        if order_request.side == "buy":
            required_cash = order_request.quantity * (order_request.price or 1.0)
            if self.portfolio.cash < required_cash:
                return False
        
        # Check sufficient position for sell orders
        elif order_request.side == "sell":
            position = self.portfolio.get_position(order_request.symbol)
            if position is None or position.size < order_request.quantity:
                return False
        
        return True
    
    @property
    def supported_symbols(self) -> List[str]:
        """Get list of supported trading symbols."""
        return self._supported_symbols.copy()
    
    @property
    def is_paper_trading(self) -> bool:
        """Check if this is a paper trading broker."""
        return True
    
    def update_market_data(self, symbol: str, ticker: Dict[str, Any], orderbook: Optional[Dict[str, Any]] = None):
        """Update market data for a symbol."""
        self.ticker_cache[symbol] = ticker
        
        if orderbook:
            self.orderbook_cache[symbol] = orderbook
        
        # Update portfolio position prices
        price_updates = {symbol: ticker.get("last", ticker.get("close", 0.0))}
        self.portfolio.update_position_prices(price_updates)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get portfolio performance metrics."""
        return self.portfolio.get_performance_metrics()
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """Get execution simulator statistics."""
        return self.execution_simulator.get_statistics()
    
    def get_trade_history(self) -> List[Any]:
        """Get complete trade history."""
        return self.portfolio.get_trade_history()
    
    def reset_portfolio(self, initial_cash: Optional[float] = None):
        """Reset portfolio to initial state."""
        self.portfolio.reset(initial_cash)
        self.orders.clear()
        self.order_counter = 0
    
    def _generate_order_id(self) -> str:
        """Generate unique order ID."""
        self.order_counter += 1
        return f"paper_{self.order_counter}_{uuid.uuid4().hex[:8]}"
    
    def _update_order_state(self, order: Order, state: OrderState, reason: Optional[str] = None):
        """Update order state."""
        order.state = state
        order.updated_at = datetime.now(timezone.utc)
        
        if reason:
            order.last_error = reason
        
        if state in [OrderState.CANCELED, OrderState.REJECTED]:
            order.canceled_at = datetime.now(timezone.utc)
        elif state == OrderState.FILLED:
            order.filled_at = datetime.now(timezone.utc)
    
    def _get_current_price_sync(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol (synchronous)."""
        ticker = self.ticker_cache.get(symbol)
        if ticker:
            return ticker.get("last") or ticker.get("close")
        
        # Fallback to default price for testing
        return 50000.0  # Default BTC price for testing
    
    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol."""
        ticker = self.ticker_cache.get(symbol)
        if ticker:
            return ticker.get("last") or ticker.get("close")
        return None
    
    def _simulate_execution(self, order: Order, current_price: float) -> Tuple[float, float, float]:
        """Simulate order execution with slippage and fees."""
        
        # Calculate slippage
        slippage_bps = self.execution_simulator.slippage_config.base_slippage_bps
        slippage = (slippage_bps / 10000.0) * current_price
        
        # Apply slippage based on order side
        if order.side == "buy":
            execution_price = current_price + slippage
        else:  # sell
            execution_price = current_price - slippage
        
        # Calculate fee
        fee_rate = self.execution_simulator.fee_config.taker_fee_bps / 10000.0
        fee = execution_price * order.quantity * fee_rate
        
        return execution_price, fee, slippage
