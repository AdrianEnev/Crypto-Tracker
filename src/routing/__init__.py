"""
Smart order routing module for optimal order execution across multiple venues.
Provides intelligent venue selection, latency optimization, and liquidity aggregation.
"""

from .router import SmartOrderRouter, RoutingStrategy, RoutingResult
from .venue_manager import VenueManager, Venue, VenueMetrics
from .latency_optimizer import LatencyOptimizer, LatencyMetrics
from .liquidity_aggregator import LiquidityAggregator, LiquiditySnapshot

__all__ = [
    'SmartOrderRouter', 'RoutingStrategy', 'RoutingResult',
    'VenueManager', 'Venue', 'VenueMetrics',
    'LatencyOptimizer', 'LatencyMetrics',
    'LiquidityAggregator', 'LiquiditySnapshot'
]
