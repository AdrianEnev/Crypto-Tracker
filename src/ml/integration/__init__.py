"""
ML Integration module for enhancing existing trading strategies.
Provides ML-enhanced wrappers and integration components.
"""

from .ml_enhanced_strategy import MLEnhancedStrategy, MLStrategyConfig
from .strategy_ensemble import StrategyEnsemble, EnsembleConfig, EnsembleMethod
from .ml_strategy_manager import MLStrategyManager, MLStrategyManagerConfig

__all__ = [
    'MLEnhancedStrategy', 'MLStrategyConfig',
    'StrategyEnsemble', 'EnsembleConfig', 'EnsembleMethod',
    'MLStrategyManager', 'MLStrategyManagerConfig'
]
