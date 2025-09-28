"""
Advanced Slippage Models Package

Provides sophisticated slippage calculation including order book depth-based
models, volume-weighted slippage, market impact analysis, and realistic fill simulation.
"""

from .models import (
    SlippageResult,
    OrderBookSnapshot,
    MarketDepth,
    OrderLevel,
    SlippageType,
    MarketCondition,
    SlippageContext,
    SlippageCalculationError,
    InsufficientLiquidityError,
    InvalidOrderBookError,
)
from .depth_based import DepthBasedSlippage
from .volume_based import VolumeBasedSlippage
from .market_impact import MarketImpactCalculator
from .backtest_slippage import BacktestSlippageCalculator, SlippageStats

__all__ = [
    "SlippageResult",
    "OrderBookSnapshot",
    "MarketDepth",
    "OrderLevel",
    "SlippageType",
    "MarketCondition",
    "SlippageContext",
    "SlippageCalculationError",
    "InsufficientLiquidityError",
    "InvalidOrderBookError",
    "DepthBasedSlippage",
    "VolumeBasedSlippage",
    "MarketImpactCalculator",
    "BacktestSlippageCalculator",
    "SlippageStats",
]
