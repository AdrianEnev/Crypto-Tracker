"""
Smart order router for optimal order execution across multiple venues.
Provides intelligent venue selection, routing strategies, and execution optimization.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from .venue_manager import VenueManager, Venue
from .latency_optimizer import LatencyOptimizer, Route
from .liquidity_aggregator import LiquidityAggregator, LiquiditySnapshot


class RoutingStrategy(Enum):
    """Routing strategy types."""
    BEST_PRICE = "best_price"
    BEST_LIQUIDITY = "best_liquidity"
    LOWEST_LATENCY = "lowest_latency"
    LOWEST_COST = "lowest_cost"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


@dataclass
class RoutingResult:
    """Result of smart order routing."""
    order_id: str
    symbol: str
    side: str
    quantity: float
    routing_strategy: RoutingStrategy
    
    # Execution plan
    selected_venue: str
    execution_plan: Dict
    estimated_cost: float
    estimated_slippage_bps: float
    estimated_latency_ms: float
    
    # Routing metadata
    alternative_venues: List[Dict]
    routing_confidence: float
    timestamp: datetime
    
    # Performance tracking
    actual_execution_time_ms: Optional[float] = None
    actual_slippage_bps: Optional[float] = None
    actual_cost: Optional[float] = None
    execution_success: Optional[bool] = None


class SmartOrderRouter:
    """
    Smart order router for optimal execution across multiple venues.
    
    Features:
    - Intelligent venue selection based on multiple factors
    - Multiple routing strategies (price, liquidity, latency, cost)
    - Real-time market data integration
    - Execution plan optimization
    - Performance monitoring and feedback
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # Initialize components
        self.venue_manager = VenueManager(self.config.get('venue_config', {}))
        self.latency_optimizer = LatencyOptimizer(self.config.get('latency_config', {}))
        self.liquidity_aggregator = LiquidityAggregator(self.config.get('liquidity_config', {}))
        
        # Routing configuration
        self.default_strategy = RoutingStrategy(self.config.get('default_strategy', 'balanced'))
        self.routing_history: List[RoutingResult] = []
        
        # Performance tracking
        self.routing_stats = {
            'total_orders': 0,
            'successful_routes': 0,
            'avg_execution_time_ms': 0.0,
            'avg_slippage_bps': 0.0,
            'strategy_performance': {}
        }
        
        # Initialize mock data for demonstration
        self._initialize_mock_data()
    
    def _initialize_mock_data(self) -> None:
        """Initialize mock data for demonstration."""
        # Generate mock liquidity data
        symbols = ['BTC-USDT', 'ETH-USDT', 'ADA-USDT']
        for symbol in symbols:
            self.liquidity_aggregator.generate_mock_data(symbol)
    
    def route_order(self, order_id: str, symbol: str, side: str, quantity: float,
                   order_type: str = 'market', strategy: Optional[RoutingStrategy] = None,
                   preferences: Optional[Dict] = None) -> RoutingResult:
        """
        Route an order to the optimal venue.
        
        Args:
            order_id: Unique order identifier
            symbol: Trading symbol
            side: 'buy' or 'sell'
            quantity: Order quantity
            order_type: Type of order (market, limit, etc.)
            strategy: Routing strategy to use
            preferences: Additional routing preferences
            
        Returns:
            Routing result with execution plan
        """
        if strategy is None:
            strategy = self.default_strategy
        
        preferences = preferences or {}
        
        # Get current liquidity snapshot
        liquidity_snapshot = self.liquidity_aggregator.get_liquidity_snapshot(symbol)
        
        # Find suitable venues
        suitable_venues = self._find_suitable_venues(symbol, quantity, order_type, preferences)
        
        if not suitable_venues:
            # Return error result
            return RoutingResult(
                order_id=order_id,
                symbol=symbol,
                side=side,
                quantity=quantity,
                routing_strategy=strategy,
                selected_venue="",
                execution_plan={'error': 'No suitable venues found'},
                estimated_cost=0.0,
                estimated_slippage_bps=0.0,
                estimated_latency_ms=0.0,
                alternative_venues=[],
                routing_confidence=0.0,
                timestamp=datetime.now(timezone.utc)
            )
        
        # Select optimal venue based on strategy
        selected_venue = self._select_venue_by_strategy(
            suitable_venues, strategy, symbol, quantity, side, preferences
        )
        
        # Generate execution plan
        execution_plan = self._generate_execution_plan(
            selected_venue, symbol, quantity, side, liquidity_snapshot
        )
        
        # Calculate estimates
        estimates = self._calculate_execution_estimates(
            selected_venue, execution_plan, symbol, quantity, side
        )
        
        # Get alternative venues
        alternative_venues = self._get_alternative_venues(suitable_venues, selected_venue)
        
        # Calculate routing confidence
        routing_confidence = self._calculate_routing_confidence(
            selected_venue, strategy, estimates
        )
        
        # Create routing result
        result = RoutingResult(
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            routing_strategy=strategy,
            selected_venue=selected_venue.venue_id,
            execution_plan=execution_plan,
            estimated_cost=estimates['cost'],
            estimated_slippage_bps=estimates['slippage_bps'],
            estimated_latency_ms=estimates['latency_ms'],
            alternative_venues=alternative_venues,
            routing_confidence=routing_confidence,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Store routing history
        self.routing_history.append(result)
        
        # Update routing stats
        self._update_routing_stats(result)
        
        return result
    
    def _find_suitable_venues(self, symbol: str, quantity: float, order_type: str,
                            preferences: Optional[Dict] = None) -> List[Venue]:
        """Find venues that can handle the order."""
        preferences = preferences or {}
        
        suitable_venues = []
        
        for venue in self.venue_manager.venues.values():
            if venue.can_handle_order(symbol, quantity, order_type):
                # Check additional preferences
                if 'region' in preferences and venue.region != preferences['region']:
                    continue
                
                if 'max_fee_bps' in preferences:
                    metrics = venue.get_metrics(symbol)
                    if metrics and metrics.taker_fee_bps > preferences['max_fee_bps']:
                        continue
                
                suitable_venues.append(venue)
        
        return suitable_venues
    
    def _select_venue_by_strategy(self, venues: List[Venue], strategy: RoutingStrategy,
                                symbol: str, quantity: float, side: str,
                                preferences: Dict) -> Venue:
        """Select venue based on routing strategy."""
        if not venues:
            raise ValueError("No suitable venues available")
        
        if len(venues) == 1:
            return venues[0]
        
        # Get liquidity snapshot for comparison
        liquidity_snapshot = self.liquidity_aggregator.get_liquidity_snapshot(symbol)
        
        venue_scores = []
        
        for venue in venues:
            score = 0.0
            
            if strategy == RoutingStrategy.BEST_PRICE:
                score = self._calculate_price_score(venue, symbol, side, liquidity_snapshot)
            
            elif strategy == RoutingStrategy.BEST_LIQUIDITY:
                score = self._calculate_liquidity_score(venue, symbol, liquidity_snapshot)
            
            elif strategy == RoutingStrategy.LOWEST_LATENCY:
                score = self._calculate_latency_score(venue, symbol, preferences)
            
            elif strategy == RoutingStrategy.LOWEST_COST:
                score = self._calculate_cost_score(venue, symbol)
            
            elif strategy == RoutingStrategy.BALANCED:
                score = self._calculate_balanced_score(venue, symbol, side, liquidity_snapshot, preferences)
            
            elif strategy == RoutingStrategy.AGGRESSIVE:
                score = self._calculate_aggressive_score(venue, symbol, side, liquidity_snapshot, preferences)
            
            venue_scores.append((venue, score))
        
        # Sort by score (descending) and return best venue
        venue_scores.sort(key=lambda x: x[1], reverse=True)
        return venue_scores[0][0]
    
    def _calculate_price_score(self, venue: Venue, symbol: str, side: str,
                             liquidity_snapshot: Optional[LiquiditySnapshot]) -> float:
        """Calculate price-based score for venue selection."""
        if not liquidity_snapshot:
            return 0.5  # Default score
        
        # Find venue's best price
        venue_levels = []
        for level in (liquidity_snapshot.bids if side == 'sell' else liquidity_snapshot.asks):
            if level.venue_id == venue.venue_id:
                venue_levels.append(level)
        
        if not venue_levels:
            return 0.3
        
        if side == 'sell':
            best_price = max(venue_levels, key=lambda x: x.price).price
            # Compare to best bid across all venues
            best_market_price = liquidity_snapshot.best_bid_price
        else:
            best_price = min(venue_levels, key=lambda x: x.price).price
            # Compare to best ask across all venues
            best_market_price = liquidity_snapshot.best_ask_price
        
        if best_market_price == 0:
            return 0.5
        
        # Calculate price improvement score
        if side == 'sell':
            price_improvement = (best_price - best_market_price) / best_market_price
        else:
            price_improvement = (best_market_price - best_price) / best_market_price
        
        return max(0, min(1, 0.5 + price_improvement * 100))  # Convert to 0-1 score
    
    def _calculate_liquidity_score(self, venue: Venue, symbol: str,
                                 liquidity_snapshot: Optional[LiquiditySnapshot]) -> float:
        """Calculate liquidity-based score for venue selection."""
        if not liquidity_snapshot:
            return 0.5
        
        # Get venue's liquidity contribution
        venue_bid_quantity = sum(level.quantity for level in liquidity_snapshot.bids
                               if level.venue_id == venue.venue_id)
        venue_ask_quantity = sum(level.quantity for level in liquidity_snapshot.asks
                               if level.venue_id == venue.venue_id)
        
        total_bid_quantity = liquidity_snapshot.total_bid_quantity
        total_ask_quantity = liquidity_snapshot.total_ask_quantity
        
        if total_bid_quantity == 0 or total_ask_quantity == 0:
            return 0.3
        
        # Calculate liquidity contribution ratio
        bid_ratio = venue_bid_quantity / total_bid_quantity
        ask_ratio = venue_ask_quantity / total_ask_quantity
        liquidity_ratio = (bid_ratio + ask_ratio) / 2
        
        return min(1.0, liquidity_ratio * 2)  # Scale up for better scoring
    
    def _calculate_latency_score(self, venue: Venue, symbol: str, preferences: Dict) -> float:
        """Calculate latency-based score for venue selection."""
        source_region = preferences.get('source_region', 'us-east')
        
        # Get best route to venue
        route = self.latency_optimizer.get_best_route(source_region, venue.venue_id, 'latency')
        
        if not route:
            return 0.3
        
        # Calculate latency score
        latency_score = self.latency_optimizer.get_route_score(route.route_id)
        
        return latency_score
    
    def _calculate_cost_score(self, venue: Venue, symbol: str) -> float:
        """Calculate cost-based score for venue selection."""
        metrics = venue.get_metrics(symbol)
        if not metrics:
            return 0.5
        
        # Lower fees = higher score
        fee_score = max(0, 1 - (metrics.taker_fee_bps / 50.0))  # Normalize to 50 bps max
        
        return fee_score
    
    def _calculate_balanced_score(self, venue: Venue, symbol: str, side: str,
                                liquidity_snapshot: Optional[LiquiditySnapshot],
                                preferences: Dict) -> float:
        """Calculate balanced score considering all factors."""
        price_score = self._calculate_price_score(venue, symbol, side, liquidity_snapshot)
        liquidity_score = self._calculate_liquidity_score(venue, symbol, liquidity_snapshot)
        latency_score = self._calculate_latency_score(venue, symbol, preferences)
        cost_score = self._calculate_cost_score(venue, symbol)
        
        # Weighted combination
        balanced_score = (
            price_score * 0.3 +
            liquidity_score * 0.3 +
            latency_score * 0.2 +
            cost_score * 0.2
        )
        
        return balanced_score
    
    def _calculate_aggressive_score(self, venue: Venue, symbol: str, side: str,
                                  liquidity_snapshot: Optional[LiquiditySnapshot],
                                  preferences: Dict) -> float:
        """Calculate aggressive score prioritizing speed and fill rate."""
        latency_score = self._calculate_latency_score(venue, symbol, preferences)
        liquidity_score = self._calculate_liquidity_score(venue, symbol, liquidity_snapshot)
        
        # Get venue metrics for fill rate
        metrics = venue.get_metrics(symbol)
        fill_rate_score = metrics.fill_rate if metrics else 0.5
        
        # Aggressive weighting: speed > liquidity > fill rate
        aggressive_score = (
            latency_score * 0.5 +
            liquidity_score * 0.3 +
            fill_rate_score * 0.2
        )
        
        return aggressive_score
    
    def _generate_execution_plan(self, venue: Venue, symbol: str, quantity: float,
                               side: str, liquidity_snapshot: Optional[LiquiditySnapshot]) -> Dict:
        """Generate execution plan for the selected venue."""
        execution_plan = {
            'venue_id': venue.venue_id,
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'execution_strategy': 'single_venue',
            'slices': [],
            'risk_controls': {
                'max_slippage_bps': 10.0,
                'max_execution_time_ms': 30000,
                'max_retries': 3
            }
        }
        
        # For large orders, consider slicing
        if quantity > 10.0:  # Large order threshold
            slice_count = min(5, max(2, int(quantity / 5.0)))  # 2-5 slices
            slice_quantity = quantity / slice_count
            
            for i in range(slice_count):
                execution_plan['slices'].append({
                    'slice_id': f"{execution_plan['venue_id']}_slice_{i+1}",
                    'quantity': slice_quantity,
                    'execution_delay_ms': i * 1000  # 1 second between slices
                })
        
        return execution_plan
    
    def _calculate_execution_estimates(self, venue: Venue, execution_plan: Dict,
                                     symbol: str, quantity: float, side: str) -> Dict:
        """Calculate execution cost and performance estimates."""
        metrics = venue.get_metrics(symbol)
        if not metrics:
            return {
                'cost': quantity * 50000.0 * 0.001,  # Default estimate
                'slippage_bps': 5.0,
                'latency_ms': 100.0
            }
        
        # Estimate cost (including fees and slippage)
        estimated_price = 50000.0  # Mock price
        notional_value = quantity * estimated_price
        
        # Fee cost
        fee_cost = notional_value * (metrics.taker_fee_bps / 10000)
        
        # Slippage cost
        slippage_cost = notional_value * (metrics.avg_slippage_bps / 10000)
        
        total_cost = fee_cost + slippage_cost
        
        return {
            'cost': total_cost,
            'slippage_bps': metrics.avg_slippage_bps,
            'latency_ms': metrics.avg_latency_ms
        }
    
    def _get_alternative_venues(self, suitable_venues: List[Venue], 
                              selected_venue: Venue) -> List[Dict]:
        """Get alternative venue options."""
        alternatives = []
        
        for venue in suitable_venues:
            if venue.venue_id != selected_venue.venue_id:
                metrics = venue.get_metrics('BTC-USDT')  # Default symbol for comparison
                alternatives.append({
                    'venue_id': venue.venue_id,
                    'name': venue.name,
                    'region': venue.region,
                    'execution_score': venue.calculate_execution_score('BTC-USDT', 'market'),
                    'taker_fee_bps': metrics.taker_fee_bps if metrics else 10.0
                })
        
        # Sort by execution score
        alternatives.sort(key=lambda x: x['execution_score'], reverse=True)
        
        return alternatives[:3]  # Return top 3 alternatives
    
    def _calculate_routing_confidence(self, venue: Venue, strategy: RoutingStrategy,
                                    estimates: Dict) -> float:
        """Calculate confidence in the routing decision."""
        confidence = 0.5  # Base confidence
        
        # Adjust based on venue performance
        metrics = venue.get_metrics('BTC-USDT')  # Default symbol
        if metrics:
            confidence += metrics.fill_rate * 0.2
            confidence -= (metrics.avg_slippage_bps / 50.0) * 0.1
            confidence += (1 - metrics.avg_latency_ms / 1000.0) * 0.1
        
        # Adjust based on estimates
        if estimates['slippage_bps'] < 5.0:
            confidence += 0.1
        if estimates['latency_ms'] < 200.0:
            confidence += 0.1
        
        return max(0.0, min(1.0, confidence))
    
    def _update_routing_stats(self, result: RoutingResult) -> None:
        """Update routing statistics."""
        self.routing_stats['total_orders'] += 1
        
        if result.execution_success:
            self.routing_stats['successful_routes'] += 1
        
        # Update strategy performance
        strategy = result.routing_strategy.value
        if strategy not in self.routing_stats['strategy_performance']:
            self.routing_stats['strategy_performance'][strategy] = {
                'total_orders': 0,
                'successful_orders': 0,
                'avg_slippage_bps': 0.0,
                'avg_latency_ms': 0.0
            }
        
        strategy_stats = self.routing_stats['strategy_performance'][strategy]
        strategy_stats['total_orders'] += 1
        
        if result.execution_success:
            strategy_stats['successful_orders'] += 1
        
        if result.actual_slippage_bps:
            strategy_stats['avg_slippage_bps'] = (
                (strategy_stats['avg_slippage_bps'] * (strategy_stats['total_orders'] - 1) + 
                 result.actual_slippage_bps) / strategy_stats['total_orders']
            )
        
        if result.actual_execution_time_ms:
            strategy_stats['avg_latency_ms'] = (
                (strategy_stats['avg_latency_ms'] * (strategy_stats['total_orders'] - 1) + 
                 result.actual_execution_time_ms) / strategy_stats['total_orders']
            )
    
    def update_execution_result(self, order_id: str, execution_result: Dict) -> None:
        """Update routing result with actual execution data."""
        # Find the routing result
        for result in self.routing_history:
            if result.order_id == order_id:
                result.actual_execution_time_ms = execution_result.get('execution_time_ms')
                result.actual_slippage_bps = execution_result.get('slippage_bps')
                result.actual_cost = execution_result.get('cost')
                result.execution_success = execution_result.get('success', False)
                
                # Update venue metrics
                self.venue_manager.update_venue_metrics(
                    result.selected_venue,
                    result.symbol,
                    execution_result
                )
                
                # Recalculate stats
                self._update_routing_stats(result)
                break
    
    def get_routing_performance_report(self) -> Dict:
        """Generate routing performance report."""
        total_orders = self.routing_stats['total_orders']
        success_rate = (self.routing_stats['successful_routes'] / total_orders * 100 
                       if total_orders > 0 else 0)
        
        return {
            'overall_performance': {
                'total_orders': total_orders,
                'successful_routes': self.routing_stats['successful_routes'],
                'success_rate_percent': success_rate,
                'avg_execution_time_ms': self.routing_stats['avg_execution_time_ms'],
                'avg_slippage_bps': self.routing_stats['avg_slippage_bps']
            },
            'strategy_performance': self.routing_stats['strategy_performance'],
            'venue_performance': self.venue_manager.get_all_venues_performance(),
            'latency_report': self.latency_optimizer.get_latency_report()
        }
