"""
Crypto Tracker - Refactored modular structure

This package contains the refactored components of the crypto tracker system:
- core: Main tracker orchestration
- price_manager: Price fetching and aggregation
- portfolio_manager: Portfolio and equity management
- risk_manager: Risk controls and protection
- execution_manager: Order execution and exits
- display: UI and status display
"""

from .core import CryptoTracker

__all__ = ["CryptoTracker"]
