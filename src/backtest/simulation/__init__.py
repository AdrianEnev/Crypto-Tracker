"""
Backtest simulation package.
Contains modules for running trading simulations.
"""

from .models import Trade, BacktestResult
from .simulator import TradingSimulator
from .data_loader import BacktestDataLoader
from .metrics import MetricsCalculator

__all__ = [
    'Trade',
    'BacktestResult', 
    'TradingSimulator',
    'BacktestDataLoader',
    'MetricsCalculator'
]
