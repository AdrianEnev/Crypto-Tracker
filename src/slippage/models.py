"""
Slippage Model Data Structures

Defines core data structures for slippage calculation including
order book snapshots, market depth, and slippage results.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class SlippageType(Enum):
    """Types of slippage models."""

    STATIC = "static"  # Fixed basis points
    DEPTH_BASED = "depth_based"  # Based on order book depth
    VOLUME_BASED = "volume_based"  # Based on trading volume
    MARKET_IMPACT = "market_impact"  # Based on market impact
    ADAPTIVE = "adaptive"  # Adaptive based on market conditions


class MarketCondition(Enum):
    """Market condition classifications."""

    CALM = "calm"  # Low volatility, good liquidity
    NORMAL = "normal"  # Standard market conditions
    VOLATILE = "volatile"  # High volatility
    ILLIQUID = "illiquid"  # Poor liquidity
    STRESSED = "stressed"  # Market stress conditions


@dataclass
class OrderLevel:
    """Represents a single level in the order book."""

    price: float
    quantity: float
    orders_count: int = 1  # Number of orders at this level


@dataclass
class MarketDepth:
    """Market depth information for bid/ask sides."""

    bids: List[OrderLevel] = field(default_factory=list)  # Sorted by price desc
    asks: List[OrderLevel] = field(default_factory=list)  # Sorted by price asc

    @property
    def best_bid(self) -> Optional[float]:
        """Get the best bid price."""
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> Optional[float]:
        """Get the best ask price."""
        return self.asks[0].price if self.asks else None

    @property
    def spread_bps(self) -> Optional[float]:
        """Calculate bid-ask spread in basis points."""
        if self.best_bid and self.best_ask:
            return ((self.best_ask - self.best_bid) / self.best_bid) * 10000
        return None

    def get_total_quantity_to_price(self, side: str, target_price: float) -> float:
        """Get total quantity available up to a target price."""
        levels = self.asks if side == "buy" else self.bids

        total_quantity = 0.0
        for level in levels:
            if side == "buy" and level.price <= target_price:
                total_quantity += level.quantity
            elif side == "sell" and level.price >= target_price:
                total_quantity += level.quantity
            else:
                break

        return total_quantity

    def simulate_order_fill(self, side: str, quantity: float) -> Tuple[float, float]:
        """
        Simulate filling an order and return average price and slippage.

        Args:
            side: "buy" or "sell"
            quantity: Order quantity

        Returns:
            Tuple of (average_fill_price, slippage_bps)
        """
        levels = self.asks if side == "buy" else self.bids

        if not levels:
            raise ValueError("No liquidity available")

        remaining_quantity = quantity
        total_cost = 0.0

        for level in levels:
            if remaining_quantity <= 0:
                break

            fill_quantity = min(remaining_quantity, level.quantity)
            total_cost += fill_quantity * level.price
            remaining_quantity -= fill_quantity

        if remaining_quantity > 0:
            # Order not fully filled - use worst case price
            worst_price = levels[-1].price
            total_cost += remaining_quantity * worst_price

        average_price = total_cost / quantity

        # Calculate slippage
        if side == "buy":
            reference_price = self.best_ask
            slippage_bps = ((average_price - reference_price) / reference_price) * 10000
        else:
            reference_price = self.best_bid
            slippage_bps = ((reference_price - average_price) / reference_price) * 10000

        return average_price, slippage_bps


@dataclass
class OrderBookSnapshot:
    """Complete order book snapshot at a point in time."""

    symbol: str
    timestamp: datetime
    bids: List[OrderLevel]
    asks: List[OrderLevel]
    last_trade_price: Optional[float] = None
    last_trade_quantity: Optional[float] = None
    volume_24h: Optional[float] = None

    @property
    def mid_price(self) -> Optional[float]:
        """Calculate mid price."""
        if self.bids and self.asks:
            return (self.bids[0].price + self.asks[0].price) / 2.0
        return None

    @property
    def spread_bps(self) -> Optional[float]:
        """Calculate bid-ask spread in basis points."""
        if self.bids and self.asks:
            return ((self.asks[0].price - self.bids[0].price) / self.bids[0].price) * 10000
        return None

    def get_market_depth(self) -> MarketDepth:
        """Get market depth from this snapshot."""
        return MarketDepth(bids=self.bids.copy(), asks=self.asks.copy())


@dataclass
class SlippageResult:
    """Result of slippage calculation."""

    slippage_bps: float
    slippage_usd: float
    effective_price: float
    reference_price: float
    slippage_type: SlippageType
    market_condition: MarketCondition

    # Additional metadata
    liquidity_used: float = 0.0  # Amount of liquidity consumed
    depth_levels_used: int = 0  # Number of order book levels used
    market_impact_bps: float = 0.0  # Market impact in basis points

    # Fill simulation results
    fill_quantity: float = 0.0
    unfilled_quantity: float = 0.0
    partial_fill: bool = False

    @property
    def fill_percentage(self) -> float:
        """Calculate fill percentage."""
        total_quantity = self.fill_quantity + self.unfilled_quantity
        if total_quantity == 0:
            return 0.0
        return (self.fill_quantity / total_quantity) * 100.0


@dataclass
class SlippageContext:
    """Context for slippage calculation."""

    symbol: str
    side: str  # "buy" or "sell"
    quantity: float
    order_type: str  # "market", "limit", etc.
    limit_price: Optional[float] = None
    timestamp: Optional[datetime] = None

    # Market data
    current_price: Optional[float] = None
    order_book: Optional[OrderBookSnapshot] = None
    volume_24h: Optional[float] = None

    # Market conditions
    volatility: Optional[float] = None  # Recent volatility
    market_condition: MarketCondition = MarketCondition.NORMAL


class SlippageCalculationError(Exception):
    """Exception raised when slippage calculation fails."""

    pass


class InsufficientLiquidityError(SlippageCalculationError):
    """Exception raised when insufficient liquidity for order."""

    pass


class InvalidOrderBookError(SlippageCalculationError):
    """Exception raised when order book data is invalid."""

    pass
