"""
Machine Learning module for intelligent trading strategies.
Provides ML-enhanced trading capabilities while preserving existing algorithms.
"""

from .feature_engineering import FeaturePipeline, TechnicalFeatures, OnChainFeatures

# Phase 5A: Only feature engineering is implemented
# Models, training, inference, and monitoring will be added in Phase 5B

__all__ = [
    'FeaturePipeline', 'TechnicalFeatures', 'OnChainFeatures'
]
