"""
Social Media Integration Module

This module provides social media and alternative data integration for the trading system.
All features are designed to be easily configurable and can be disabled independently.

Key Components:
- Data source integrations (LunarCrush, Santiment, Glassnode, CryptoQuant)
- NLP pipeline for sentiment analysis and entity extraction
- Social momentum feature engineering
- Cross-validation with on-chain data
- Bot detection and manipulation safeguards
- ML model integration
- Monitoring and alerting

Configuration:
All features can be controlled via config/social_media.yaml or the main config.yaml
"""

from .config import SocialMediaConfig
from .data_sources import SocialDataManager
from .features import SocialFeatureEngine
from .validation import SocialSignalValidator
from .monitoring import SocialMonitoringDashboard
from .integration import SocialMediaIntegration, create_social_integration

__all__ = [
    "SocialMediaConfig",
    "SocialDataManager", 
    "SocialFeatureEngine",
    "SocialSignalValidator",
    "SocialMonitoringDashboard",
    "SocialMediaIntegration",
    "create_social_integration"
]