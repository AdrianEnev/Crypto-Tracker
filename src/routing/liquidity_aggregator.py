"""
Liquidity aggregation system for combining order book data from multiple venues.
Provides real-time liquidity monitoring, depth analysis, and optimal venue selection.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np


@dataclass
class OrderBookLevel:
    """Represents a single level in the order book."""
    price: float
    quantity: float
    venue_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class LiquiditySnapshot:
    """Snapshot of aggregated liquidity across venues."""
    symbol: str
    timestamp: datetime
    venues: List[str]
    
    # Aggregated order book
    bids: List[OrderBookLevel] = field(default_factory=list)
    asks: List[OrderBookLevel] = field(default_factory=list)
    
    # Liquidity metrics
    total_bid_quantity: float = 0.0
    total_ask_quantity: float = 0.0
    best_bid_price: float = 0.0
    best_ask_price: float = 0.0
    spread_bps: float = 0.0
    mid_price: float = 0.0
    
    # Depth analysis
    depth_5bps: float = 0.0  # Quantity within 5 bps of mid
    depth_10bps: float = 0.0  # Quantity within 10 bps of mid
    depth_20bps: float = 0.0  # Quantity within 20 bps of mid
    
    def __post_init__(self):
        """Calculate derived metrics after initialization."""
        if self.bids and self.asks:
            # Sort bids (highest first) and asks (lowest first)
            self.bids.sort(key=lambda x: x.price, reverse=True)
            self.asks.sort(key=lambda x: x.price)
            
            self.best_bid_price = self.bids[0].price if self.bids else 0.0
            self.best_ask_price = self.asks[0].price if self.asks else 0.0
            
            if self.best_bid_price > 0 and self.best_ask_price > 0:
                self.mid_price = (self.best_bid_price + self.best_ask_price) / 2
                self.spread_bps = ((self.best_ask_price - self.best_bid_price) / 
                                 self.mid_price) * 10000
            
            self.total_bid_quantity = sum(level.quantity for level in self.bids)
            self.total_ask_quantity = sum(level.quantity for level in self.asks)
            
            # Calculate depth metrics
            self._calculate_depth_metrics()
    
    def _calculate_depth_metrics(self):
        """Calculate depth metrics at various price levels."""
        if not self.mid_price:
            return
        
        # Calculate quantity within different bps ranges
        for level in self.bids:
            price_diff_bps = ((self.mid_price - level.price) / self.mid_price) * 10000
            if price_diff_bps <= 5:
                self.depth_5bps += level.quantity
            if price_diff_bps <= 10:
                self.depth_10bps += level.quantity
            if price_diff_bps <= 20:
                self.depth_20bps += level.quantity
        
        for level in self.asks:
            price_diff_bps = ((level.price - self.mid_price) / self.mid_price) * 10000
            if price_diff_bps <= 5:
                self.depth_5bps += level.quantity
            if price_diff_bps <= 10:
                self.depth_10bps += level.quantity
            if price_diff_bps <= 20:
                self.depth_20bps += level.quantity


@dataclass
class VenueLiquidity:
    """Liquidity information for a specific venue."""
    venue_id: str
    symbol: str
    timestamp: datetime
    
    # Order book data
    bids: List[OrderBookLevel] = field(default_factory=list)
    asks: List[OrderBookLevel] = field(default_factory=list)
    
    # Venue-specific metrics
    venue_spread_bps: float = 0.0
    venue_depth_ratio: float = 0.0  # Ratio of venue depth to total depth
    venue_liquidity_score: float = 0.0


class LiquidityAggregator:
    """
    Liquidity aggregation system for combining data from multiple venues.
    
    Features:
    - Real-time order book aggregation
    - Cross-venue liquidity analysis
    - Optimal venue selection for large orders
    - Liquidity monitoring and alerts
    - Depth analysis and market impact estimation
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.venue_liquidity: Dict[str, Dict[str, VenueLiquidity]] = {}
        self.aggregated_snapshots: Dict[str, List[LiquiditySnapshot]] = {}
        self.liquidity_history: Dict[str, List[Dict]] = {}
        
        # Configuration
        self.max_order_book_levels = self.config.get('max_order_book_levels', 20)
        self.snapshot_retention_minutes = self.config.get('snapshot_retention_minutes', 60)
        
    def update_venue_liquidity(self, venue_id: str, symbol: str, 
                              bids: List[Tuple[float, float]], 
                              asks: List[Tuple[float, float]]) -> None:
        """
        Update liquidity data for a specific venue.
        
        Args:
            venue_id: Venue identifier
            symbol: Trading symbol
            bids: List of (price, quantity) tuples for bids
            asks: List of (price, quantity) tuples for asks
        """
        timestamp = datetime.now(timezone.utc)
        
        # Convert to OrderBookLevel objects
        bid_levels = [OrderBookLevel(price=price, quantity=quantity, venue_id=venue_id)
                     for price, quantity in bids[:self.max_order_book_levels]]
        
        ask_levels = [OrderBookLevel(price=price, quantity=quantity, venue_id=venue_id)
                     for price, quantity in asks[:self.max_order_book_levels]]
        
        # Create venue liquidity object
        venue_liquidity = VenueLiquidity(
            venue_id=venue_id,
            symbol=symbol,
            timestamp=timestamp,
            bids=bid_levels,
            asks=ask_levels
        )
        
        # Calculate venue-specific metrics
        if bid_levels and ask_levels:
            best_bid = max(bid_levels, key=lambda x: x.price)
            best_ask = min(ask_levels, key=lambda x: x.price)
            
            if best_bid.price > 0 and best_ask.price > 0:
                mid_price = (best_bid.price + best_ask.price) / 2
                venue_liquidity.venue_spread_bps = ((best_ask.price - best_bid.price) / 
                                                  mid_price) * 10000
        
        # Store venue liquidity
        if venue_id not in self.venue_liquidity:
            self.venue_liquidity[venue_id] = {}
        
        self.venue_liquidity[venue_id][symbol] = venue_liquidity
        
        # Update aggregated snapshot
        self._update_aggregated_snapshot(symbol)
    
    def _update_aggregated_snapshot(self, symbol: str) -> None:
        """Update aggregated liquidity snapshot for a symbol."""
        timestamp = datetime.now(timezone.utc)
        
        # Collect all venue liquidity for this symbol
        all_bids = []
        all_asks = []
        venues = []
        
        for venue_id, venue_symbols in self.venue_liquidity.items():
            if symbol in venue_symbols:
                venue_liquidity = venue_symbols[symbol]
                all_bids.extend(venue_liquidity.bids)
                all_asks.extend(venue_liquidity.asks)
                venues.append(venue_id)
        
        # Create aggregated snapshot
        snapshot = LiquiditySnapshot(
            symbol=symbol,
            timestamp=timestamp,
            venues=venues,
            bids=all_bids,
            asks=all_asks
        )
        
        # Store snapshot
        if symbol not in self.aggregated_snapshots:
            self.aggregated_snapshots[symbol] = []
        
        self.aggregated_snapshots[symbol].append(snapshot)
        
        # Keep only recent snapshots
        cutoff_time = timestamp.timestamp() - (self.snapshot_retention_minutes * 60)
        self.aggregated_snapshots[symbol] = [
            s for s in self.aggregated_snapshots[symbol] 
            if s.timestamp.timestamp() > cutoff_time
        ]
        
        # Update liquidity history
        self._update_liquidity_history(symbol, snapshot)
    
    def _update_liquidity_history(self, symbol: str, snapshot: LiquiditySnapshot) -> None:
        """Update liquidity history for analysis."""
        if symbol not in self.liquidity_history:
            self.liquidity_history[symbol] = []
        
        history_entry = {
            'timestamp': snapshot.timestamp,
            'spread_bps': snapshot.spread_bps,
            'mid_price': snapshot.mid_price,
            'total_bid_quantity': snapshot.total_bid_quantity,
            'total_ask_quantity': snapshot.total_ask_quantity,
            'depth_5bps': snapshot.depth_5bps,
            'depth_10bps': snapshot.depth_10bps,
            'depth_20bps': snapshot.depth_20bps,
            'venue_count': len(snapshot.venues)
        }
        
        self.liquidity_history[symbol].append(history_entry)
        
        # Keep only recent history (last 1000 entries)
        if len(self.liquidity_history[symbol]) > 1000:
            self.liquidity_history[symbol] = self.liquidity_history[symbol][-1000:]
    
    def get_liquidity_snapshot(self, symbol: str) -> Optional[LiquiditySnapshot]:
        """Get the latest aggregated liquidity snapshot for a symbol."""
        if symbol not in self.aggregated_snapshots or not self.aggregated_snapshots[symbol]:
            return None
        
        return self.aggregated_snapshots[symbol][-1]
    
    def find_optimal_execution_plan(self, symbol: str, quantity: float, 
                                  side: str, max_slippage_bps: float = 10.0) -> Dict:
        """
        Find optimal execution plan across venues for a large order.
        
        Args:
            symbol: Trading symbol
            quantity: Order quantity
            side: 'buy' or 'sell'
            max_slippage_bps: Maximum acceptable slippage in basis points
            
        Returns:
            Execution plan with venue allocations
        """
        snapshot = self.get_liquidity_snapshot(symbol)
        if not snapshot:
            return {'error': 'No liquidity data available'}
        
        if side == 'buy':
            levels = snapshot.asks
            price_threshold = snapshot.mid_price * (1 + max_slippage_bps / 10000)
        else:
            levels = snapshot.bids
            price_threshold = snapshot.mid_price * (1 - max_slippage_bps / 10000)
        
        # Sort levels by price (ascending for asks, descending for bids)
        if side == 'buy':
            levels.sort(key=lambda x: x.price)
        else:
            levels.sort(key=lambda x: x.price, reverse=True)
        
        # Build execution plan
        execution_plan = {
            'symbol': symbol,
            'side': side,
            'total_quantity': quantity,
            'max_slippage_bps': max_slippage_bps,
            'execution_venues': [],
            'estimated_slippage_bps': 0.0,
            'estimated_cost': 0.0,
            'remaining_quantity': quantity
        }
        
        remaining_quantity = quantity
        total_cost = 0.0
        
        for level in levels:
            if remaining_quantity <= 0:
                break
            
            # Check if level is within slippage tolerance
            if side == 'buy' and level.price > price_threshold:
                break
            elif side == 'sell' and level.price < price_threshold:
                break
            
            # Calculate quantity to execute at this level
            execute_quantity = min(remaining_quantity, level.quantity)
            level_cost = execute_quantity * level.price
            
            execution_plan['execution_venues'].append({
                'venue_id': level.venue_id,
                'price': level.price,
                'quantity': execute_quantity,
                'cost': level_cost,
                'slippage_bps': abs((level.price - snapshot.mid_price) / snapshot.mid_price) * 10000
            })
            
            remaining_quantity -= execute_quantity
            total_cost += level_cost
        
        execution_plan['remaining_quantity'] = remaining_quantity
        execution_plan['estimated_cost'] = total_cost
        
        # Calculate weighted average slippage
        if execution_plan['execution_venues']:
            total_executed = quantity - remaining_quantity
            weighted_slippage = sum(
                venue['slippage_bps'] * venue['quantity'] for venue in execution_plan['execution_venues']
            ) / total_executed
            execution_plan['estimated_slippage_bps'] = weighted_slippage
        
        return execution_plan
    
    def get_venue_liquidity_ranking(self, symbol: str, side: str) -> List[Dict]:
        """
        Rank venues by liquidity quality for a specific side.
        
        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            
        Returns:
            List of venues ranked by liquidity quality
        """
        venue_rankings = []
        
        for venue_id, venue_symbols in self.venue_liquidity.items():
            if symbol not in venue_symbols:
                continue
            
            venue_liquidity = venue_symbols[symbol]
            
            if side == 'buy':
                levels = venue_liquidity.asks
                if not levels:
                    continue
                best_price = min(levels, key=lambda x: x.price).price
            else:
                levels = venue_liquidity.bids
                if not levels:
                    continue
                best_price = max(levels, key=lambda x: x.price).price
            
            # Calculate liquidity metrics
            total_quantity = sum(level.quantity for level in levels)
            avg_quantity = total_quantity / len(levels) if levels else 0
            
            # Calculate liquidity score
            spread_penalty = max(0, 1 - venue_liquidity.venue_spread_bps / 10.0)
            depth_score = min(1.0, total_quantity / 1000.0)  # Normalize to 1000 units
            consistency_score = min(1.0, avg_quantity / 100.0)  # Normalize to 100 units
            
            liquidity_score = (spread_penalty * 0.4 + depth_score * 0.4 + consistency_score * 0.2)
            
            venue_rankings.append({
                'venue_id': venue_id,
                'best_price': best_price,
                'total_quantity': total_quantity,
                'spread_bps': venue_liquidity.venue_spread_bps,
                'liquidity_score': liquidity_score,
                'level_count': len(levels)
            })
        
        # Sort by liquidity score (descending)
        venue_rankings.sort(key=lambda x: x['liquidity_score'], reverse=True)
        
        return venue_rankings
    
    def get_liquidity_analytics(self, symbol: str, lookback_hours: int = 24) -> Dict:
        """Get liquidity analytics for a symbol over time."""
        if symbol not in self.liquidity_history:
            return {'error': 'No liquidity history available'}
        
        history = self.liquidity_history[symbol]
        
        # Filter by lookback period
        cutoff_time = datetime.now(timezone.utc).timestamp() - (lookback_hours * 3600)
        recent_history = [h for h in history if h['timestamp'].timestamp() > cutoff_time]
        
        if not recent_history:
            return {'error': 'No recent liquidity data'}
        
        # Calculate analytics
        spreads = [h['spread_bps'] for h in recent_history]
        depths_5bps = [h['depth_5bps'] for h in recent_history]
        depths_10bps = [h['depth_10bps'] for h in recent_history]
        depths_20bps = [h['depth_20bps'] for h in recent_history]
        venue_counts = [h['venue_count'] for h in recent_history]
        
        return {
            'symbol': symbol,
            'lookback_hours': lookback_hours,
            'data_points': len(recent_history),
            'spread_analytics': {
                'avg_spread_bps': np.mean(spreads),
                'min_spread_bps': np.min(spreads),
                'max_spread_bps': np.max(spreads),
                'std_spread_bps': np.std(spreads)
            },
            'depth_analytics': {
                'avg_depth_5bps': np.mean(depths_5bps),
                'avg_depth_10bps': np.mean(depths_10bps),
                'avg_depth_20bps': np.mean(depths_20bps),
                'depth_stability': np.std(depths_10bps) / np.mean(depths_10bps) if np.mean(depths_10bps) > 0 else 0
            },
            'venue_analytics': {
                'avg_venue_count': np.mean(venue_counts),
                'min_venue_count': np.min(venue_counts),
                'max_venue_count': np.max(venue_counts)
            },
            'liquidity_quality': {
                'avg_spread_score': max(0, 1 - np.mean(spreads) / 10.0),  # Better if < 10 bps
                'depth_score': min(1.0, np.mean(depths_10bps) / 1000.0),  # Better if > 1000 units
                'stability_score': max(0, 1 - (np.std(spreads) / np.mean(spreads)) if np.mean(spreads) > 0 else 0)
            }
        }
    
    def generate_mock_data(self, symbol: str, venue_count: int = 3) -> None:
        """Generate mock liquidity data for testing."""
        venues = ['binance', 'coinbase', 'kraken'][:venue_count]
        
        # Generate realistic order book data
        base_price = 50000.0  # BTC price
        spread_bps = np.random.uniform(1, 5)  # 1-5 bps spread
        
        for venue_id in venues:
            # Generate bids and asks
            bids = []
            asks = []
            
            # Generate 10 levels each
            for i in range(10):
                bid_price = base_price * (1 - (i + 1) * 0.001)  # Decreasing prices
                ask_price = base_price * (1 + (i + 1) * 0.001)  # Increasing prices
                
                bid_quantity = np.random.uniform(0.1, 2.0)
                ask_quantity = np.random.uniform(0.1, 2.0)
                
                bids.append((bid_price, bid_quantity))
                asks.append((ask_price, ask_quantity))
            
            self.update_venue_liquidity(venue_id, symbol, bids, asks)
