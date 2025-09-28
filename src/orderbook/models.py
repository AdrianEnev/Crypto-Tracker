"""
Order Book Data Models

Defines data structures for order book management, replay, and simulation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple


class OrderBookEventType(Enum):
    """Types of order book events."""

    SNAPSHOT = "snapshot"  # Complete order book snapshot
    UPDATE = "update"  # Incremental update
    TRADE = "trade"  # Trade execution
    HEARTBEAT = "heartbeat"  # Keep-alive


class OrderBookState(Enum):
    """Order book state."""

    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"
    ERROR = "error"


@dataclass
class OrderLevel:
    """Represents a single level in the order book."""

    price: float
    quantity: float
    orders_count: Optional[int] = None  # Number of orders at this level

    def __post_init__(self):
        """Ensure quantity is non-negative."""
        self.quantity = max(0.0, self.quantity)


@dataclass
class MarketDepth:
    """Market depth for a single side (bids or asks)."""

    levels: List[OrderLevel] = field(default_factory=list)

    def add_level(self, price: float, quantity: float, orders_count: Optional[int] = None) -> None:
        """Add or update a level."""
        # Remove existing level at this price
        self.levels = [level for level in self.levels if level.price != price]

        # Add new level
        if quantity > 0:
            self.levels.append(OrderLevel(price, quantity, orders_count))

        # Sort levels
        self.sort_levels()

    def remove_level(self, price: float) -> None:
        """Remove a level at the specified price."""
        self.levels = [level for level in self.levels if level.price != price]

    def sort_levels(self) -> None:
        """Sort levels by price. Override in subclasses for bid/ask specific sorting."""
        pass

    def get_total_quantity_to_price(self, target_price: float) -> float:
        """Get total quantity available up to target price."""
        total = 0.0
        for level in self.levels:
            if self._should_include_level(level.price, target_price):
                total += level.quantity
        return total

    def _should_include_level(self, level_price: float, target_price: float) -> bool:
        """Determine if level should be included. Override in subclasses."""
        return True

    def simulate_fill(self, quantity: float) -> Tuple[float, float, int]:
        """
        Simulate filling quantity and return (filled_quantity, avg_price, levels_used).

        Args:
            quantity: Quantity to fill

        Returns:
            Tuple of (filled_quantity, average_price, levels_used)
        """
        remaining = quantity
        total_cost = 0.0
        levels_used = 0

        for level in self.levels:
            if remaining <= 0:
                break

            fill_quantity = min(remaining, level.quantity)
            total_cost += fill_quantity * level.price
            remaining -= fill_quantity
            levels_used += 1

        filled_quantity = quantity - remaining
        avg_price = total_cost / filled_quantity if filled_quantity > 0 else 0.0

        return filled_quantity, avg_price, levels_used


class BidDepth(MarketDepth):
    """Bid side market depth (sorted by price descending)."""

    def sort_levels(self) -> None:
        """Sort bids by price descending (highest first)."""
        self.levels.sort(key=lambda x: x.price, reverse=True)

    def _should_include_level(self, level_price: float, target_price: float) -> bool:
        """Include levels with price >= target price."""
        return level_price >= target_price


class AskDepth(MarketDepth):
    """Ask side market depth (sorted by price ascending)."""

    def sort_levels(self) -> None:
        """Sort asks by price ascending (lowest first)."""
        self.levels.sort(key=lambda x: x.price)

    def _should_include_level(self, level_price: float, target_price: float) -> bool:
        """Include levels with price <= target price."""
        return level_price <= target_price


@dataclass
class OrderBookSnapshot:
    """Complete order book snapshot at a point in time."""

    symbol: str
    timestamp: datetime
    bids: BidDepth
    asks: AskDepth
    last_trade_price: Optional[float] = None
    last_trade_quantity: Optional[float] = None
    last_trade_id: Optional[str] = None
    sequence_number: Optional[int] = None

    def __post_init__(self):
        """Initialize bid/ask depths if not provided."""
        if isinstance(self.bids, list):
            self.bids = BidDepth([OrderLevel(price, qty) for price, qty in self.bids])
            self.bids.sort_levels()
        elif not isinstance(self.bids, BidDepth):
            self.bids = BidDepth()

        if isinstance(self.asks, list):
            self.asks = AskDepth([OrderLevel(price, qty) for price, qty in self.asks])
            self.asks.sort_levels()
        elif not isinstance(self.asks, AskDepth):
            self.asks = AskDepth()

    @property
    def best_bid(self) -> Optional[float]:
        """Get the best bid price."""
        return self.bids.levels[0].price if self.bids.levels else None

    @property
    def best_ask(self) -> Optional[float]:
        """Get the best ask price."""
        return self.asks.levels[0].price if self.asks.levels else None

    @property
    def spread(self) -> Optional[float]:
        """Calculate bid-ask spread."""
        if self.best_bid and self.best_ask:
            return self.best_ask - self.best_bid
        return None

    @property
    def spread_bps(self) -> Optional[float]:
        """Calculate bid-ask spread in basis points."""
        if self.best_bid and self.best_ask and self.best_bid > 0:
            return ((self.best_ask - self.best_bid) / self.best_bid) * 10000
        return None

    @property
    def mid_price(self) -> Optional[float]:
        """Calculate mid price."""
        if self.best_bid and self.best_ask:
            return (self.best_bid + self.best_ask) / 2.0
        return None

    def is_valid(self) -> bool:
        """Check if order book is valid."""
        if not self.bids.levels or not self.asks.levels:
            return False

        if self.best_bid is None or self.best_ask is None:
            return False

        if self.best_bid >= self.best_ask:
            return False

        return True

    def get_market_depth(self, levels: int = 10) -> Dict[str, List[Tuple[float, float]]]:
        """Get market depth up to specified levels."""
        return {
            "bids": [(level.price, level.quantity) for level in self.bids.levels[:levels]],
            "asks": [(level.price, level.quantity) for level in self.asks.levels[:levels]],
        }

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "bids": [(level.price, level.quantity) for level in self.bids.levels],
            "asks": [(level.price, level.quantity) for level in self.asks.levels],
            "last_trade_price": self.last_trade_price,
            "last_trade_quantity": self.last_trade_quantity,
            "last_trade_id": self.last_trade_id,
            "sequence_number": self.sequence_number,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> OrderBookSnapshot:
        """Create from dictionary."""
        return cls(
            symbol=data["symbol"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            bids=BidDepth([OrderLevel(price, qty) for price, qty in data.get("bids", [])]),
            asks=AskDepth([OrderLevel(price, qty) for price, qty in data.get("asks", [])]),
            last_trade_price=data.get("last_trade_price"),
            last_trade_quantity=data.get("last_trade_quantity"),
            last_trade_id=data.get("last_trade_id"),
            sequence_number=data.get("sequence_number"),
        )


@dataclass
class OrderBookEvent:
    """Order book event for incremental updates."""

    symbol: str
    timestamp: datetime
    event_type: OrderBookEventType

    # Update data
    bids_update: List[Tuple[float, float]] = field(default_factory=list)  # (price, quantity)
    asks_update: List[Tuple[float, float]] = field(default_factory=list)  # (price, quantity)

    # Trade data
    trade_price: Optional[float] = None
    trade_quantity: Optional[float] = None
    trade_side: Optional[str] = None  # "buy" or "sell"

    sequence_number: Optional[int] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "bids_update": self.bids_update,
            "asks_update": self.asks_update,
            "trade_price": self.trade_price,
            "trade_quantity": self.trade_quantity,
            "trade_side": self.trade_side,
            "sequence_number": self.sequence_number,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> OrderBookEvent:
        """Create from dictionary."""
        return cls(
            symbol=data["symbol"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            event_type=OrderBookEventType(data["event_type"]),
            bids_update=data.get("bids_update", []),
            asks_update=data.get("asks_update", []),
            trade_price=data.get("trade_price"),
            trade_quantity=data.get("trade_quantity"),
            trade_side=data.get("trade_side"),
            sequence_number=data.get("sequence_number"),
        )


@dataclass
class FillResult:
    """Result of order fill simulation."""

    filled_quantity: float
    remaining_quantity: float
    average_price: float
    total_cost: float

    # Execution details
    levels_consumed: int
    slippage_bps: float
    is_partial_fill: bool
    is_completely_filled: bool

    # Market impact
    market_impact_bps: float = 0.0
    liquidity_consumed: float = 0.0

    @property
    def fill_percentage(self) -> float:
        """Calculate fill percentage."""
        total_quantity = self.filled_quantity + self.remaining_quantity
        if total_quantity == 0:
            return 0.0
        return (self.filled_quantity / total_quantity) * 100.0


@dataclass
class OrderBookMetrics:
    """Metrics for order book analysis."""

    symbol: str
    timestamp: datetime

    # Liquidity metrics
    total_bid_liquidity: float
    total_ask_liquidity: float
    weighted_bid_price: float
    weighted_ask_price: float

    # Spread metrics
    spread: float
    spread_bps: float
    mid_price: float

    # Depth metrics
    depth_5_levels: float  # Total liquidity in top 5 levels
    depth_10_levels: float  # Total liquidity in top 10 levels
    depth_20_levels: float  # Total liquidity in top 20 levels

    # Imbalance metrics
    bid_ask_ratio: float  # Ratio of bid to ask liquidity
    order_imbalance: float  # Order count imbalance

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "total_bid_liquidity": self.total_bid_liquidity,
            "total_ask_liquidity": self.total_ask_liquidity,
            "weighted_bid_price": self.weighted_bid_price,
            "weighted_ask_price": self.weighted_ask_price,
            "spread": self.spread,
            "spread_bps": self.spread_bps,
            "mid_price": self.mid_price,
            "depth_5_levels": self.depth_5_levels,
            "depth_10_levels": self.depth_10_levels,
            "depth_20_levels": self.depth_20_levels,
            "bid_ask_ratio": self.bid_ask_ratio,
            "order_imbalance": self.order_imbalance,
        }
