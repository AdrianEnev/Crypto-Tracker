"""
Paper Trading System

A comprehensive paper trading implementation that simulates real trading
with configurable slippage, fees, latency, and market impact models.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

__version__ = "1.0.0"
__author__ = "Crypto Tracker Team"

# Core paper trading components
from .broker import AbstractBroker
from .paper_broker import PaperBroker
from .execution import ExecutionSimulator, SlippageModel, FeeModel
from .portfolio import PaperPortfolio, AccountSnapshot
from .market_data import MarketDataAdapter, DataMode, DataSource
from .persistence import PaperTradingPersistence
from .metrics import PerformanceMetrics, ReportGenerator
from .config import PaperTradingConfig
from .safety import SafetyChecker, enforce_paper_mode

__all__ = [
    "PaperBroker",
    "AbstractBroker", 
    "ExecutionSimulator",
    "SlippageModel",
    "FeeModel",
    "PaperPortfolio",
    "AccountState",
    "MarketDataAdapter",
    "ReplayMode",
    "LiveMode",
    "PaperTradingPersistence",
    "PerformanceMetrics",
    "ReportGenerator",
    "PaperTradingConfig",
    "SafetyChecker",
    "enforce_paper_mode",
]
