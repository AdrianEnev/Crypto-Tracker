"""
Base Executor Interface

Abstract base class for order execution across different exchanges
and execution modes (paper vs live).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from .models import Order, OrderRequest, OrderResult, OrderState, OrderType


class BaseExecutor(ABC):
    """Abstract base class for order executors."""

    def __init__(self, exchange_name: str):
        self.exchange_name = exchange_name
        self.is_connected = False

    @abstractmethod
    def connect(self) -> bool:
        """Connect to exchange."""
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """Disconnect from exchange."""
        pass

    @abstractmethod
    def place_order(self, order_request: OrderRequest) -> OrderResult:
        """Place a new order."""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an existing order."""
        pass

    @abstractmethod
    def get_order_status(self, order_id: str, symbol: str) -> Optional[OrderState]:
        """Get current order status."""
        pass

    @abstractmethod
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get all open orders."""
        pass

    def validate_order_request(self, order_request: OrderRequest) -> bool:
        """Validate order request before execution."""
        # Basic validation - can be overridden by specific executors
        if order_request.quantity <= 0:
            return False

        if (
            order_request.order_type.value in ["limit", "stop_limit"]
            and order_request.price is None
        ):
            return False

        if order_request.order_type.value == "stop_limit" and order_request.stop_price is None:
            return False

        return True

    def get_exchange_info(self) -> Dict[str, Any]:
        """Get exchange-specific information."""
        return {
            "name": self.exchange_name,
            "connected": self.is_connected,
            "supported_order_types": self.get_supported_order_types(),
            "supported_symbols": self.get_supported_symbols(),
        }

    @abstractmethod
    def get_supported_order_types(self) -> List[str]:
        """Get list of supported order types."""
        pass

    @abstractmethod
    def get_supported_symbols(self) -> List[str]:
        """Get list of supported trading symbols."""
        pass


class EnhancedPaperExecutor(BaseExecutor):
    """Enhanced paper executor with realistic simulation features."""

    def __init__(self):
        super().__init__("paper")
        self._order_counter = 0
        self._orders: Dict[str, Order] = {}
        self._simulation_config = {
            "fill_probability": 0.95,  # 95% chance of immediate fill
            "partial_fill_probability": 0.1,  # 10% chance of partial fill
            "slippage_bps": 5,  # 5 basis points average slippage
            "latency_ms": 50,  # 50ms average latency
        }

    def connect(self) -> bool:
        """Connect to paper trading environment."""
        self.is_connected = True
        return True

    def disconnect(self) -> bool:
        """Disconnect from paper trading environment."""
        self.is_connected = False
        return True

    def place_order(self, order_request: OrderRequest) -> OrderResult:
        """Place paper order with realistic simulation."""
        import random
        import time

        if not self.validate_order_request(order_request):
            return OrderResult(order_id="", success=False, error_message="Invalid order request")

        # Generate order ID
        self._order_counter += 1
        order_id = f"paper-{self._order_counter}"

        # Simulate latency
        time.sleep(self._simulation_config["latency_ms"] / 1000.0)

        # Create order
        order = Order(
            id=order_id,
            client_order_id=order_request.client_order_id or order_id,
            symbol=order_request.symbol,
            side=order_request.side,
            order_type=order_request.order_type,
            state=OrderState.PENDING,
            quantity=order_request.quantity,
            price=order_request.price,
            stop_price=order_request.stop_price,
            time_in_force=order_request.time_in_force,
            exchange=self.exchange_name,
            strategy_id=order_request.strategy_id,
            tags=order_request.tags,
        )

        # Simulate order execution
        fill_probability = self._simulation_config["fill_probability"]
        final_state = OrderState.PENDING  # Default state

        if random.random() < fill_probability:
            # Order gets filled
            if random.random() < self._simulation_config["partial_fill_probability"]:
                # Partial fill
                fill_ratio = random.uniform(0.3, 0.8)
                fill_quantity = order.quantity * fill_ratio
                final_state = OrderState.PARTIALLY_FILLED
            else:
                # Full fill
                fill_quantity = order.quantity
                final_state = OrderState.FILLED

            # Apply slippage
            slippage_bps = self._simulation_config["slippage_bps"]
            slippage_factor = 1 + (random.uniform(-slippage_bps, slippage_bps) / 10000.0)

            if order.price is not None:
                fill_price = order.price * slippage_factor
            else:
                # Market order - simulate price discovery
                fill_price = random.uniform(0.95, 1.05)  # Simulate market price

            # Update fill information (this will handle state transitions internally)
            order.update_fill(fill_quantity, fill_price)
        else:
            # Order rejected
            final_state = OrderState.REJECTED

        # Store order
        self._orders[order_id] = order

        return OrderResult(
            order_id=order_id,
            success=True,
            exchange_order_id=order_id,
            state=final_state,
            execution_time_ms=self._simulation_config["latency_ms"],
        )

    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel paper order."""
        if order_id in self._orders:
            order = self._orders[order_id]
            if order.state in [OrderState.PENDING, OrderState.PARTIALLY_FILLED]:
                order.state = OrderState.CANCELED
                order.canceled_at = datetime.now()
                return True
        return False

    def get_order_status(self, order_id: str, symbol: str) -> Optional[OrderState]:
        """Get paper order status."""
        if order_id in self._orders:
            return self._orders[order_id].state
        return None

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get open paper orders."""
        open_orders = []
        for order in self._orders.values():
            if order.is_active and (symbol is None or order.symbol == symbol):
                open_orders.append(order)
        return open_orders

    def get_supported_order_types(self) -> List[str]:
        """Get supported order types for paper trading."""
        return ["market", "limit", "stop_limit", "twap", "vwap"]

    def get_supported_symbols(self) -> List[str]:
        """Get supported symbols for paper trading."""
        return [
            "BTC/USDT",
            "ETH/USDT",
            "BNB/USDT",
            "ADA/USDT",
            "SOL/USDT",
            "COIN0/USDT",
            "COIN1/USDT",
            "COIN2/USDT",
            "COIN3/USDT",
        ]


class EnhancedCCXTExecutor(BaseExecutor):
    """Enhanced CCXT executor with order management features."""

    def __init__(self, ccxt_executor, order_manager):
        super().__init__(ccxt_executor.ex.id if hasattr(ccxt_executor, "ex") else "unknown")
        self.ccxt_executor = ccxt_executor
        self.order_manager = order_manager
        self._order_cache: Dict[str, Order] = {}

    def connect(self) -> bool:
        """Connect to exchange via CCXT."""
        try:
            # Test connection by fetching markets
            markets = self.ccxt_executor.ex.load_markets()
            self.is_connected = True
            return True
        except Exception:
            self.is_connected = False
            return False

    def disconnect(self) -> bool:
        """Disconnect from exchange."""
        self.is_connected = False
        return True

    def place_order(self, order_request: OrderRequest) -> OrderResult:
        """Place order via CCXT with enhanced error handling."""
        if not self.validate_order_request(order_request):
            return OrderResult(order_id="", success=False, error_message="Invalid order request")

        try:
            # Convert order request to CCXT format
            ccxt_order = self._convert_to_ccxt_order(order_request)

            # Place order via CCXT
            result = self.ccxt_executor.place_order(
                symbol=order_request.symbol,
                side=order_request.side,
                size_usd=order_request.quantity * (order_request.price or 1.0),
                order_type=order_request.order_type.value,
                price=order_request.price,
                client_order_id=order_request.client_order_id,
            )

            # Convert result to our format
            order_result = OrderResult(
                order_id=result.id,
                success=True,
                exchange_order_id=result.id,
                state=self._map_ccxt_status(result.status),
            )

            return order_result

        except Exception as e:
            return OrderResult(order_id="", success=False, error_message=str(e))

    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel order via CCXT."""
        try:
            self.ccxt_executor.cancel_order_retry(order_id, symbol)
            return True
        except Exception:
            return False

    def get_order_status(self, order_id: str, symbol: str) -> Optional[OrderState]:
        """Get order status via CCXT."""
        try:
            # This would need to be implemented in the CCXT executor
            # For now, return None to indicate not implemented
            return None
        except Exception:
            return None

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get open orders via CCXT."""
        try:
            orders = self.ccxt_executor.fetch_open_orders_retry(symbol or "")
            return [self._convert_from_ccxt_order(order) for order in orders]
        except Exception:
            return []

    def get_supported_order_types(self) -> List[str]:
        """Get supported order types from exchange."""
        try:
            markets = self.ccxt_executor.ex.markets
            # Extract supported order types from markets
            order_types = set()
            for market in markets.values():
                if "orderTypes" in market:
                    order_types.update(market["orderTypes"])
            return list(order_types)
        except Exception:
            return ["market", "limit"]

    def get_supported_symbols(self) -> List[str]:
        """Get supported symbols from exchange."""
        try:
            markets = self.ccxt_executor.ex.markets
            return list(markets.keys())
        except Exception:
            return []

    def _convert_to_ccxt_order(self, order_request: OrderRequest) -> Dict[str, Any]:
        """Convert order request to CCXT format."""
        return {
            "symbol": order_request.symbol,
            "type": order_request.order_type.value,
            "side": order_request.side,
            "amount": order_request.quantity,
            "price": order_request.price,
            "params": {
                "timeInForce": order_request.time_in_force.value,
                "clientOrderId": order_request.client_order_id,
            },
        }

    def _convert_from_ccxt_order(self, ccxt_order: Dict[str, Any]) -> Order:
        """Convert CCXT order to our Order format."""
        return Order(
            id=ccxt_order["id"],
            client_order_id=ccxt_order.get("clientOrderId", ccxt_order["id"]),
            symbol=ccxt_order["symbol"],
            side=ccxt_order["side"],
            order_type=OrderType(ccxt_order["type"]),
            state=self._map_ccxt_status(ccxt_order["status"]),
            quantity=ccxt_order["amount"],
            price=ccxt_order.get("price"),
            exchange=self.exchange_name,
            filled_quantity=ccxt_order.get("filled", 0.0),
            average_fill_price=ccxt_order.get("average"),
            remaining_quantity=ccxt_order.get("remaining", ccxt_order["amount"]),
        )

    def _map_ccxt_status(self, ccxt_status: str) -> OrderState:
        """Map CCXT status to our OrderState."""
        status_mapping = {
            "open": OrderState.PENDING,
            "closed": OrderState.FILLED,
            "canceled": OrderState.CANCELED,
            "rejected": OrderState.REJECTED,
            "expired": OrderState.EXPIRED,
        }
        return status_mapping.get(ccxt_status.lower(), OrderState.PENDING)
