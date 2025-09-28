"""
Advanced Slippage Models Package

Provides sophisticated slippage calculation including order book depth-based
models, volume-weighted slippage, market impact analysis, and realistic fill simulation.
"""

from .backtest_slippage import BacktestSlippageCalculator, SlippageStats
from .depth_based import DepthBasedSlippage
from .market_impact import MarketImpactCalculator
from .models import (
    InsufficientLiquidityError,
    InvalidOrderBookError,
    MarketCondition,
    MarketDepth,
    OrderBookSnapshot,
    OrderLevel,
    SlippageCalculationError,
    SlippageContext,
    SlippageResult,
    SlippageType,
)
from .volume_based import VolumeBasedSlippage

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
