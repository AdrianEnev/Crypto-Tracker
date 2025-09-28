"""
Machine Learning module for intelligent trading strategies.
Provides ML-enhanced trading capabilities while preserving existing algorithms.
"""

from .feature_engineering import FeaturePipeline, TechnicalFeatures, OnChainFeatures
from .models import BaseModel, ModelMetadata, ParameterOptimizer, RegimeDetector, SignalEnhancer, PricePredictor

# Phase 5B: Core ML models implemented
# Training, inference, and monitoring will be added in Phase 5C

__all__ = [
    'FeaturePipeline', 'TechnicalFeatures', 'OnChainFeatures',
    'BaseModel', 'ModelMetadata', 'ParameterOptimizer', 'RegimeDetector', 'SignalEnhancer', 'PricePredictor'
]
