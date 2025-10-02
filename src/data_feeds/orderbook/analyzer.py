"""
Orderbook depth analysis for market microstructure insights
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict
import numpy as np
from cachetools import TTLCache

from ...intelligence.models import OrderbookSignal


class OrderbookAnalyzer:
    """
    Analyzes orderbook depth and structure
    
    Features:
    - Bid/ask imbalance calculation
    - Whale wall detection
    - Spread analysis
    - Liquidity assessment
    """
    
    def __init__(self, exchange_client, config: dict = None):
        self.logger = logging.getLogger(__name__)
        self.exchange = exchange_client
        self.config = config or {}
        
        # Configuration
        self.cache_ttl = self.config.get('cache_ttl_seconds', 10)  # 10 seconds
        self.depth_limit = self.config.get('depth_limit', 100)
        self.wall_threshold_multiplier = self.config.get('wall_threshold_multiplier', 3.0)
        self.min_liquidity = self.config.get('min_liquidity_threshold', 10000)
        self.max_spread_bps = self.config.get('max_spread_bps', 50)
        
        # State
        self.cache = TTLCache(maxsize=100, ttl=self.cache_ttl)
        self.request_count = 0
    
    async def analyze(self, symbol: str) -> OrderbookSignal:
        """
        Analyze orderbook for a symbol
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            
        Returns:
            OrderbookSignal with analysis results
        """
        # Check cache
        cache_key = f"ob_{symbol}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            # Fetch orderbook (CCXT is synchronous)
            orderbook = self.exchange.fetch_order_book(
                symbol,
                limit=self.depth_limit
            )
            
            if not orderbook.get('bids') or not orderbook.get('asks'):
                return OrderbookSignal.default()
            
            # Calculate metrics
            result = self._calculate_metrics(orderbook)
            
            self.cache[cache_key] = result
            self.request_count += 1
            return result
            
        except Exception as e:
            self.logger.error(f"Orderbook analysis error for {symbol}: {e}")
            return OrderbookSignal.default()
    
    def _calculate_metrics(self, orderbook: dict) -> OrderbookSignal:
        """Calculate all orderbook metrics"""
        bids = orderbook['bids']
        asks = orderbook['asks']
        
        # Volume calculations
        bid_volume_10 = sum([bid[1] for bid in bids[:10]])
        ask_volume_10 = sum([ask[1] for ask in asks[:10]])
        
        total_bid_volume = sum([bid[1] for bid in bids[:50]])
        total_ask_volume = sum([ask[1] for ask in asks[:50]])
        
        # Bid/ask imbalance
        total_volume_10 = bid_volume_10 + ask_volume_10
        imbalance = (
            (bid_volume_10 - ask_volume_10) / total_volume_10
            if total_volume_10 > 0 else 0.0
        )
        
        # Spread
        best_bid = bids[0][0] if bids else 0
        best_ask = asks[0][0] if asks else 0
        spread_bps = (
            ((best_ask - best_bid) / best_bid * 10000)
            if best_bid > 0 else 999.0
        )
        
        # Detect walls
        bid_walls = self._detect_walls(bids)
        ask_walls = self._detect_walls(asks)
        
        # Depth score (0-1)
        total_volume = total_bid_volume + total_ask_volume
        depth_score = min(1.0, total_volume / 100000)
        
        # Liquidity check
        is_liquid = (
            spread_bps < self.max_spread_bps and
            total_volume > self.min_liquidity
        )
        
        # Favorable for trading
        is_favorable = (
            is_liquid and
            abs(imbalance) < 0.5 and  # Not too imbalanced
            len(bid_walls) + len(ask_walls) < 3  # Not too many walls
        )
        
        return OrderbookSignal(
            bid_ask_imbalance=float(imbalance),
            spread_bps=float(spread_bps),
            bid_walls=bid_walls,
            ask_walls=ask_walls,
            is_liquid=is_liquid,
            is_favorable=is_favorable,
            depth_score=float(depth_score),
            timestamp=datetime.now(timezone.utc)
        )
    
    def _detect_walls(self, orders: List[List[float]]) -> List[Dict[str, float]]:
        """
        Detect abnormally large orders (walls)
        
        Args:
            orders: List of [price, volume] pairs
            
        Returns:
            List of detected walls with price, volume, and significance
        """
        if len(orders) < 20:
            return []
        
        # Calculate statistics on order volumes
        volumes = [order[1] for order in orders[:50]]
        mean_vol = np.mean(volumes)
        std_vol = np.std(volumes)
        
        if std_vol == 0:
            return []
        
        threshold = mean_vol + self.wall_threshold_multiplier * std_vol
        
        # Find walls in top 20 orders
        walls = []
        for price, volume in orders[:20]:
            if volume > threshold:
                walls.append({
                    'price': float(price),
                    'volume': float(volume),
                    'significance': float(volume / mean_vol) if mean_vol > 0 else 0.0
                })
        
        return walls
    
    def get_stats(self) -> dict:
        """Get statistics"""
        return {
            'request_count': self.request_count,
            'cache_size': len(self.cache),
            'cache_ttl': self.cache_ttl
        }
