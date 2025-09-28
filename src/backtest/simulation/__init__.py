"""
Backtest simulation package.
Contains modules for running trading simulations.
"""

from .data_loader import BacktestDataLoader
from .metrics import MetricsCalculator
from .models import BacktestResult, Trade
from .simulator import TradingSimulator

__all__ = ["Trade", "BacktestResult", "TradingSimulator", "BacktestDataLoader", "MetricsCalculator"]
