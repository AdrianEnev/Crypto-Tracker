"""
Order Book Simulation Package

Provides order book data management, historical replay capabilities,
and realistic fill simulation for advanced backtesting.
"""

from .models import (
    AskDepth,
    BidDepth,
    FillResult,
    MarketDepth,
    OrderBookEvent,
    OrderBookEventType,
    OrderBookMetrics,
    OrderBookSnapshot,
    OrderBookState,
    OrderLevel,
)

# Note: OrderBookFetcher requires ccxt, so we'll import it conditionally
try:
    from .fetcher import MultiExchangeOrderBookFetcher, OrderBookFetcher

    FETCHER_AVAILABLE = True
except ImportError:
    FETCHER_AVAILABLE = False
    OrderBookFetcher = None
    MultiExchangeOrderBookFetcher = None

from .replay_engine import OrderBookReplayEngine
from .simulator import OrderBookSimulator, SimulatedFill, SimulatedOrder
from .storage import JSONLOrderBookStorage, OrderBookStorage, SQLiteOrderBookStorage

__all__ = [
    "OrderBookSnapshot",
    "OrderLevel",
    "MarketDepth",
    "OrderBookEvent",
    "FillResult",
    "OrderBookState",
    "OrderBookMetrics",
    "OrderBookEventType",
    "BidDepth",
    "AskDepth",
    "OrderBookStorage",
    "JSONLOrderBookStorage",
    "SQLiteOrderBookStorage",
    "OrderBookReplayEngine",
    "OrderBookSimulator",
    "SimulatedOrder",
    "SimulatedFill",
    "FETCHER_AVAILABLE",
]

if FETCHER_AVAILABLE:
    __all__.extend(["OrderBookFetcher", "MultiExchangeOrderBookFetcher"])
