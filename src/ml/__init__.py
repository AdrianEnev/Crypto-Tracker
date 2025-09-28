"""
Machine Learning module for intelligent trading strategies.
Provides ML-enhanced trading capabilities while preserving existing algorithms.
"""

from .feature_engineering import FeaturePipeline, TechnicalFeatures, OnChainFeatures
from .models import BaseModel, ModelMetadata, ParameterOptimizer, RegimeDetector, SignalEnhancer, PricePredictor
from .integration import MLEnhancedStrategy, MLStrategyConfig, StrategyEnsemble, EnsembleConfig, MLStrategyManager

# Phase 5C: ML Integration with existing strategies implemented
# Optimization and monitoring will be added in Phase 5D

__all__ = [
    'FeaturePipeline', 'TechnicalFeatures', 'OnChainFeatures',
    'BaseModel', 'ModelMetadata', 'ParameterOptimizer', 'RegimeDetector', 'SignalEnhancer', 'PricePredictor',
    'MLEnhancedStrategy', 'MLStrategyConfig', 'StrategyEnsemble', 'EnsembleConfig', 'MLStrategyManager'
]
