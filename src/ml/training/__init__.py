"""
Model training and validation framework.

Provides comprehensive ML model training for:
- Regime classification (trending, ranging, volatile, etc.)
- Signal enhancement (improving trading signal quality)
- Multi-source data integration (price, social, on-chain)
"""

from .regime_classifier import RegimeClassifierTrainer, RegimeData, RegimeModel
from .signal_enhancer import SignalEnhancerTrainer, SignalData, SignalModel
from .training_pipeline import TrainingPipeline

__all__ = [
    'RegimeClassifierTrainer', 'RegimeData', 'RegimeModel',
    'SignalEnhancerTrainer', 'SignalData', 'SignalModel',
    'TrainingPipeline'
]
