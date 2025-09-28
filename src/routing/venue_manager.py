"""
Venue management system for tracking exchange performance and capabilities.
Provides venue selection, performance monitoring, and fee optimization.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class VenueMetrics:
    """Performance metrics for a trading venue."""
    venue_id: str
    symbol: str
    
    # Execution metrics
    avg_fill_time_ms: float = 0.0
    fill_rate: float = 0.0
    avg_slippage_bps: float = 0.0
    rejection_rate: float = 0.0
    
    # Cost metrics
    maker_fee_bps: float = 0.0
    taker_fee_bps: float = 0.0
    withdrawal_fee: float = 0.0
    
    # Latency metrics
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    connection_stability: float = 1.0
    
    # Liquidity metrics
    avg_bid_ask_spread_bps: float = 0.0
    avg_order_book_depth: float = 0.0
    volume_24h: float = 0.0
    
    # Quality metrics
    uptime_percentage: float = 100.0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Venue:
    """Represents a trading venue with its capabilities and performance."""
    venue_id: str
    name: str
    region: str
    supported_symbols: List[str]
    capabilities: Dict[str, bool]
    limits: Dict[str, float]
    metrics: Dict[str, VenueMetrics] = field(default_factory=dict)
    
    # Routing preferences
    preferred_for_symbols: List[str] = field(default_factory=list)
    blacklisted_symbols: List[str] = field(default_factory=list)
    max_order_size: float = 1000000.0
    min_order_size: float = 0.001
    
    # Connection info
    endpoint: str = ""
    api_version: str = "1.0"
    requires_auth: bool = True
    
    def get_metrics(self, symbol: str) -> Optional[VenueMetrics]:
        """Get metrics for a specific symbol."""
        return self.metrics.get(symbol)
    
    def update_metrics(self, symbol: str, metrics: VenueMetrics) -> None:
        """Update metrics for a specific symbol."""
        self.metrics[symbol] = metrics
    
    def can_handle_order(self, symbol: str, quantity: float, order_type: str) -> bool:
        """Check if venue can handle the order."""
        if symbol not in self.supported_symbols:
            return False
        
        if symbol in self.blacklisted_symbols:
            return False
        
        if quantity > self.max_order_size or quantity < self.min_order_size:
            return False
        
        return self.capabilities.get(order_type, False)
    
    def calculate_execution_score(self, symbol: str, order_type: str, urgency: float = 1.0) -> float:
        """Calculate execution quality score for this venue."""
        metrics = self.get_metrics(symbol)
        if not metrics:
            return 0.5  # Default score if no metrics available
        
        # Weighted score calculation
        score = 0.0
        weights = {
            'fill_rate': 0.25,
            'slippage': 0.20,
            'latency': 0.20,
            'spread': 0.15,
            'fees': 0.10,
            'stability': 0.10
        }
        
        # Fill rate score (higher is better)
        fill_rate_score = metrics.fill_rate
        score += fill_rate_score * weights['fill_rate']
        
        # Slippage score (lower is better)
        slippage_score = max(0, 1 - (metrics.avg_slippage_bps / 10.0))  # Normalize to 10 bps max
        score += slippage_score * weights['slippage']
        
        # Latency score (lower is better)
        latency_score = max(0, 1 - (metrics.avg_latency_ms / 1000.0))  # Normalize to 1000ms max
        score += latency_score * weights['latency']
        
        # Spread score (lower is better)
        spread_score = max(0, 1 - (metrics.avg_bid_ask_spread_bps / 5.0))  # Normalize to 5 bps max
        score += spread_score * weights['spread']
        
        # Fee score (lower is better)
        fee_score = max(0, 1 - (metrics.taker_fee_bps / 20.0))  # Normalize to 20 bps max
        score += fee_score * weights['fees']
        
        # Stability score (higher is better)
        stability_score = metrics.connection_stability * metrics.uptime_percentage / 100.0
        score += stability_score * weights['stability']
        
        # Adjust for urgency (higher urgency favors speed over cost)
        if urgency > 1.0:
            # Boost latency and fill rate scores
            score = score * 0.7 + (fill_rate_score * 0.2 + latency_score * 0.1) * urgency
        
        return min(1.0, max(0.0, score))


class VenueManager:
    """
    Manages trading venues and their performance metrics.
    
    Features:
    - Venue registration and management
    - Performance monitoring and metrics collection
    - Venue selection based on order requirements
    - Fee optimization and cost analysis
    - Latency tracking and optimization
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.venues: Dict[str, Venue] = {}
        self.performance_history: Dict[str, List[Dict]] = {}
        
        # Initialize default venues
        self._initialize_default_venues()
    
    def _initialize_default_venues(self) -> None:
        """Initialize default trading venues."""
        default_venues = [
            {
                'venue_id': 'binance',
                'name': 'Binance',
                'region': 'global',
                'supported_symbols': ['BTC-USDT', 'ETH-USDT', 'ADA-USDT', 'DOT-USDT', 'LINK-USDT'],
                'capabilities': {
                    'market': True,
                    'limit': True,
                    'stop_limit': True,
                    'twap': False,
                    'vwap': False
                },
                'limits': {
                    'max_order_size': 1000.0,
                    'min_order_size': 0.001,
                    'rate_limit': 1200  # orders per minute
                },
                'maker_fee': 0.1,  # 0.1%
                'taker_fee': 0.1,   # 0.1%
                'endpoint': 'https://api.binance.com'
            },
            {
                'venue_id': 'coinbase',
                'name': 'Coinbase Pro',
                'region': 'us',
                'supported_symbols': ['BTC-USD', 'ETH-USD', 'ADA-USD', 'DOT-USD', 'LINK-USD'],
                'capabilities': {
                    'market': True,
                    'limit': True,
                    'stop_limit': True,
                    'twap': False,
                    'vwap': False
                },
                'limits': {
                    'max_order_size': 500.0,
                    'min_order_size': 0.01,
                    'rate_limit': 300  # orders per minute
                },
                'maker_fee': 0.5,  # 0.5%
                'taker_fee': 0.5,   # 0.5%
                'endpoint': 'https://api.pro.coinbase.com'
            },
            {
                'venue_id': 'kraken',
                'name': 'Kraken',
                'region': 'global',
                'supported_symbols': ['BTC-USD', 'ETH-USD', 'ADA-USD', 'DOT-USD', 'LINK-USD'],
                'capabilities': {
                    'market': True,
                    'limit': True,
                    'stop_limit': False,
                    'twap': False,
                    'vwap': False
                },
                'limits': {
                    'max_order_size': 250.0,
                    'min_order_size': 0.01,
                    'rate_limit': 180  # orders per minute
                },
                'maker_fee': 0.16,  # 0.16%
                'taker_fee': 0.26,   # 0.26%
                'endpoint': 'https://api.kraken.com'
            }
        ]
        
        for venue_data in default_venues:
            venue = Venue(
                venue_id=venue_data['venue_id'],
                name=venue_data['name'],
                region=venue_data['region'],
                supported_symbols=venue_data['supported_symbols'],
                capabilities=venue_data['capabilities'],
                limits=venue_data['limits'],
                max_order_size=venue_data['limits']['max_order_size'],
                min_order_size=venue_data['limits']['min_order_size'],
                endpoint=venue_data['endpoint']
            )
            
            # Initialize default metrics for supported symbols
            for symbol in venue.supported_symbols:
                metrics = VenueMetrics(
                    venue_id=venue.venue_id,
                    symbol=symbol,
                    maker_fee_bps=venue_data['maker_fee'] * 100,
                    taker_fee_bps=venue_data['taker_fee'] * 100,
                    avg_latency_ms=np.random.uniform(50, 200),
                    fill_rate=np.random.uniform(0.85, 0.98),
                    avg_slippage_bps=np.random.uniform(1, 5),
                    avg_bid_ask_spread_bps=np.random.uniform(1, 3),
                    volume_24h=np.random.uniform(1000000, 5000000)
                )
                venue.update_metrics(symbol, metrics)
            
            self.venues[venue.venue_id] = venue
    
    def register_venue(self, venue: Venue) -> None:
        """Register a new trading venue."""
        self.venues[venue.venue_id] = venue
        self.performance_history[venue.venue_id] = []
    
    def get_venue(self, venue_id: str) -> Optional[Venue]:
        """Get venue by ID."""
        return self.venues.get(venue_id)
    
    def get_venues_for_symbol(self, symbol: str) -> List[Venue]:
        """Get all venues that support a specific symbol."""
        return [venue for venue in self.venues.values() 
                if symbol in venue.supported_symbols]
    
    def select_best_venue(self, symbol: str, quantity: float, order_type: str, 
                         urgency: float = 1.0, preferences: Optional[Dict] = None) -> Optional[Venue]:
        """
        Select the best venue for an order based on performance metrics.
        
        Args:
            symbol: Trading symbol
            quantity: Order quantity
            order_type: Type of order (market, limit, etc.)
            urgency: Urgency factor (1.0 = normal, >1.0 = more urgent)
            preferences: Additional preferences (region, max_fee, etc.)
            
        Returns:
            Best venue for the order, or None if no suitable venue found
        """
        suitable_venues = []
        
        for venue in self.venues.values():
            if venue.can_handle_order(symbol, quantity, order_type):
                # Check preferences if provided
                if preferences:
                    if 'region' in preferences and venue.region != preferences['region']:
                        continue
                    if 'max_fee_bps' in preferences:
                        metrics = venue.get_metrics(symbol)
                        if metrics and metrics.taker_fee_bps > preferences['max_fee_bps']:
                            continue
                
                execution_score = venue.calculate_execution_score(symbol, order_type, urgency)
                suitable_venues.append((venue, execution_score))
        
        if not suitable_venues:
            return None
        
        # Sort by execution score (descending)
        suitable_venues.sort(key=lambda x: x[1], reverse=True)
        
        return suitable_venues[0][0]
    
    def update_venue_metrics(self, venue_id: str, symbol: str, 
                           execution_result: Dict) -> None:
        """Update venue metrics based on execution result."""
        venue = self.get_venue(venue_id)
        if not venue:
            return
        
        metrics = venue.get_metrics(symbol)
        if not metrics:
            metrics = VenueMetrics(venue_id=venue_id, symbol=symbol)
        
        # Update metrics based on execution result
        if 'fill_time_ms' in execution_result:
            # Exponential moving average for fill time
            alpha = 0.1
            metrics.avg_fill_time_ms = (alpha * execution_result['fill_time_ms'] + 
                                      (1 - alpha) * metrics.avg_fill_time_ms)
        
        if 'filled' in execution_result:
            # Update fill rate
            fill_rate = 1.0 if execution_result['filled'] else 0.0
            alpha = 0.1
            metrics.fill_rate = (alpha * fill_rate + (1 - alpha) * metrics.fill_rate)
        
        if 'slippage_bps' in execution_result:
            # Update slippage
            alpha = 0.1
            metrics.avg_slippage_bps = (alpha * execution_result['slippage_bps'] + 
                                      (1 - alpha) * metrics.avg_slippage_bps)
        
        if 'rejected' in execution_result:
            # Update rejection rate
            rejection = 1.0 if execution_result['rejected'] else 0.0
            alpha = 0.1
            metrics.rejection_rate = (alpha * rejection + (1 - alpha) * metrics.rejection_rate)
        
        metrics.last_updated = datetime.now(timezone.utc)
        venue.update_metrics(symbol, metrics)
        
        # Store in performance history
        if venue_id not in self.performance_history:
            self.performance_history[venue_id] = []
        
        self.performance_history[venue_id].append({
            'timestamp': datetime.now(timezone.utc),
            'symbol': symbol,
            'execution_result': execution_result
        })
    
    def get_venue_performance_report(self, venue_id: str, symbol: str) -> Dict:
        """Generate performance report for a venue and symbol."""
        venue = self.get_venue(venue_id)
        if not venue:
            return {}
        
        metrics = venue.get_metrics(symbol)
        if not metrics:
            return {}
        
        # Calculate performance trends from history
        history = self.performance_history.get(venue_id, [])
        recent_history = [h for h in history 
                         if h['symbol'] == symbol and 
                         (datetime.now(timezone.utc) - h['timestamp']).days <= 7]
        
        fill_rates = [h['execution_result'].get('filled', False) for h in recent_history]
        avg_fill_rate_recent = sum(fill_rates) / len(fill_rates) if fill_rates else 0
        
        return {
            'venue_id': venue_id,
            'symbol': symbol,
            'current_metrics': {
                'fill_rate': metrics.fill_rate,
                'avg_slippage_bps': metrics.avg_slippage_bps,
                'avg_latency_ms': metrics.avg_latency_ms,
                'taker_fee_bps': metrics.taker_fee_bps,
                'execution_score': venue.calculate_execution_score(symbol, 'market')
            },
            'recent_performance': {
                'avg_fill_rate_7d': avg_fill_rate_recent,
                'total_orders_7d': len(recent_history)
            },
            'venue_info': {
                'name': venue.name,
                'region': venue.region,
                'supported_order_types': [k for k, v in venue.capabilities.items() if v],
                'limits': venue.limits
            }
        }
    
    def get_all_venues_performance(self) -> Dict[str, Dict]:
        """Get performance summary for all venues."""
        performance_summary = {}
        
        for venue_id, venue in self.venues.items():
            venue_performance = {}
            
            for symbol in venue.supported_symbols:
                metrics = venue.get_metrics(symbol)
                if metrics:
                    venue_performance[symbol] = {
                        'execution_score': venue.calculate_execution_score(symbol, 'market'),
                        'fill_rate': metrics.fill_rate,
                        'avg_slippage_bps': metrics.avg_slippage_bps,
                        'taker_fee_bps': metrics.taker_fee_bps
                    }
            
            performance_summary[venue_id] = {
                'name': venue.name,
                'region': venue.region,
                'symbols': venue_performance
            }
        
        return performance_summary
