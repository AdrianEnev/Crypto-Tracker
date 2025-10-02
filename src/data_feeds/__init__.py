"""
Data Feeds - Real-time alternative data integration

Provides:
- Social media sentiment (Twitter, Reddit)
- Orderbook analysis
- On-chain metrics
- Derivatives data
"""

from .social import SocialMediaAggregator
from .orderbook import OrderbookAnalyzer

__all__ = [
    'SocialMediaAggregator',
    'OrderbookAnalyzer'
]
