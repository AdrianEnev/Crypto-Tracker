"""
Compatibility Adapter

Bridges the old simple PaperExecutor with the new comprehensive PaperBroker
to maintain backward compatibility while enabling advanced features.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from src.executor import Order as OldOrder, PaperExecutor as OldPaperExecutor
from paper_trader import PaperBroker
from paper_trader.config import PaperTradingConfig


class PaperExecutorAdapter(OldPaperExecutor):
    """
    Adapter that wraps the new PaperBroker to provide compatibility
    with the old PaperExecutor interface.
    """
    
    def __init__(self, config: Optional[PaperTradingConfig] = None):
        # Initialize the old interface
        super().__init__()
        
        # Initialize the new paper broker
        if config is None:
            config = PaperTradingConfig.create_default_config()
        
        self.paper_broker = PaperBroker(
            initial_cash=config.initial_cash,
            base_currency=config.base_currency,
            slippage_config=config.slippage_config,
            fee_config=config.fee_config,
            latency_config=config.latency_config
        )
        
        # Connect the broker
        self.paper_broker.connect()
    
    def place_order(
        self, symbol: str, side: str, size_usd: float, order_type: str = "limit"
    ) -> OldOrder:
        """
        Place order using the new paper broker but return old Order format.
        """
        
        # Convert to new order request format
        from src.order_manager.models import OrderRequest, OrderType, TimeInForce
        
        # Map order types
        order_type_mapping = {
            "market": OrderType.MARKET,
            "limit": OrderType.LIMIT,
            "stop-limit": OrderType.STOP_LIMIT,
        }
        
        new_order_type = order_type_mapping.get(order_type, OrderType.MARKET)
        
        # Calculate quantity from USD size (simplified - assumes current price)
        # In a real implementation, you'd get the current price from market data
        current_price = 50000.0  # Placeholder - should get from market data
        quantity = size_usd / current_price
        
        order_request = OrderRequest(
            symbol=symbol,
            side=side,
            order_type=new_order_type,
            quantity=quantity,
            time_in_force=TimeInForce.GTC,
            strategy_id="legacy_adapter"
        )
        
        # Place order using new broker
        result = self.paper_broker.place_order(order_request)
        
        if not result.success:
            # Return rejected order in old format
            return OldOrder(
                id=result.order_id or f"rejected-{self._counter}",
                symbol=symbol,
                side=side,
                size_usd=size_usd,
                order_type=order_type,
                status="Rejected",
                created_at=datetime.now(timezone.utc),
                filled_price=None,
                note=f"Rejected: {result.error_message}"
            )
        
        # Get the order from the new broker
        new_order = self.paper_broker.orders.get(result.order_id)
        
        if new_order is None:
            # Fallback to old format
            return OldOrder(
                id=result.order_id,
                symbol=symbol,
                side=side,
                size_usd=size_usd,
                order_type=order_type,
                status="Placed",
                created_at=datetime.now(timezone.utc),
                filled_price=None,
                note="paper-fill"
            )
        
        # Convert new order to old format
        status = "Filled" if new_order.state.value == "FILLED" else "Placed"
        
        return OldOrder(
            id=new_order.id,
            symbol=new_order.symbol,
            side=new_order.side,
            size_usd=new_order.quantity * (new_order.price or current_price),
            order_type=order_type,
            status=status,
            created_at=new_order.created_at,
            filled_price=new_order.average_fill_price,
            note="enhanced-paper-fill"
        )
    
    def get_portfolio_summary(self) -> dict:
        """Get portfolio summary from the new broker."""
        return self.paper_broker.get_performance_metrics()
    
    def get_account_info(self):
        """Get account information from the new broker."""
        return self.paper_broker.get_account_info()
    
    def update_market_data(self, symbol: str, price: float, **kwargs):
        """Update market data for the symbol."""
        ticker = {
            "last": price,
            "bid": price * 0.999,
            "ask": price * 1.001,
            "volume": kwargs.get("volume", 0),
            "high": kwargs.get("high", price),
            "low": kwargs.get("low", price),
            "open": kwargs.get("open", price),
            "close": price,
        }
        self.paper_broker.update_market_data(symbol, ticker)


def create_enhanced_paper_executor(config_path: Optional[str] = None) -> PaperExecutorAdapter:
    """
    Factory function to create an enhanced paper executor.
    
    Args:
        config_path: Path to paper trading configuration file
        
    Returns:
        PaperExecutorAdapter instance
    """
    
    if config_path:
        config = PaperTradingConfig.from_file(config_path)
    else:
        config = PaperTradingConfig.create_default_config()
    
    return PaperExecutorAdapter(config)


# Backward compatibility - users can still import the old class
PaperExecutor = PaperExecutorAdapter
