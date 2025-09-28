"""
Demo script for Smart Order Routing system.
Demonstrates venue selection, routing strategies, and execution optimization.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
from datetime import datetime, timezone
from src.routing.router import SmartOrderRouter, RoutingStrategy
from src.routing.venue_manager import VenueManager
from src.routing.latency_optimizer import LatencyOptimizer
from src.routing.liquidity_aggregator import LiquidityAggregator


def demo_basic_routing():
    """Demonstrate basic smart order routing."""
    print("=== Basic Smart Order Routing Demo ===\n")
    
    # Initialize router
    router = SmartOrderRouter()
    
    # Route a simple order
    print("1. Routing a simple BTC-USDT buy order...")
    result = router.route_order(
        order_id="demo_order_1",
        symbol="BTC-USDT",
        side="buy",
        quantity=1.0,
        order_type="market",
        strategy=RoutingStrategy.BALANCED
    )
    
    print(f"Selected Venue: {result.selected_venue}")
    print(f"Estimated Cost: ${result.estimated_cost:.2f}")
    print(f"Estimated Slippage: {result.estimated_slippage_bps:.2f} bps")
    print(f"Estimated Latency: {result.estimated_latency_ms:.1f} ms")
    print(f"Routing Confidence: {result.routing_confidence:.2f}")
    print(f"Alternative Venues: {len(result.alternative_venues)}")
    
    # Show execution plan
    print("\nExecution Plan:")
    for key, value in result.execution_plan.items():
        print(f"  {key}: {value}")
    
    print()


def demo_routing_strategies():
    """Demonstrate different routing strategies."""
    print("=== Routing Strategies Comparison ===\n")
    
    router = SmartOrderRouter()
    
    strategies = [
        RoutingStrategy.BEST_PRICE,
        RoutingStrategy.BEST_LIQUIDITY,
        RoutingStrategy.LOWEST_LATENCY,
        RoutingStrategy.LOWEST_COST,
        RoutingStrategy.BALANCED,
        RoutingStrategy.AGGRESSIVE
    ]
    
    print("Comparing routing strategies for BTC-USDT buy order (5.0 units):")
    print("-" * 80)
    print(f"{'Strategy':<15} {'Venue':<12} {'Cost ($)':<10} {'Slippage (bps)':<15} {'Latency (ms)':<12} {'Confidence':<10}")
    print("-" * 80)
    
    for strategy in strategies:
        result = router.route_order(
            order_id=f"demo_{strategy.value}",
            symbol="BTC-USDT",
            side="buy",
            quantity=5.0,
            order_type="market",
            strategy=strategy
        )
        
        print(f"{strategy.value:<15} {result.selected_venue:<12} "
              f"${result.estimated_cost:<9.2f} {result.estimated_slippage_bps:<14.2f} "
              f"{result.estimated_latency_ms:<11.1f} {result.routing_confidence:<9.2f}")
    
    print()


def demo_venue_performance():
    """Demonstrate venue performance analysis."""
    print("=== Venue Performance Analysis ===\n")
    
    router = SmartOrderRouter()
    
    # Get venue performance report
    print("1. Overall Venue Performance:")
    performance = router.venue_manager.get_all_venues_performance()
    
    for venue_id, venue_data in performance.items():
        print(f"\n{venue_id.upper()} ({venue_data['name']}) - {venue_data['region'].upper()}")
        print("-" * 50)
        
        for symbol, metrics in venue_data['symbols'].items():
            print(f"  {symbol}:")
            print(f"    Execution Score: {metrics['execution_score']:.3f}")
            print(f"    Fill Rate: {metrics['fill_rate']:.1%}")
            print(f"    Avg Slippage: {metrics['avg_slippage_bps']:.2f} bps")
            print(f"    Taker Fee: {metrics['taker_fee_bps']:.2f} bps")
    
    print()


def demo_latency_optimization():
    """Demonstrate latency optimization."""
    print("=== Latency Optimization Demo ===\n")
    
    router = SmartOrderRouter()
    
    # Test latency from different regions
    regions = ['us-east', 'us-west', 'eu-west', 'asia-east']
    venues = ['binance', 'coinbase', 'kraken']
    
    print("Latency from different regions to venues:")
    print("-" * 60)
    print(f"{'Region':<12} {'Binance (ms)':<15} {'Coinbase (ms)':<15} {'Kraken (ms)':<15}")
    print("-" * 60)
    
    for region in regions:
        latencies = []
        for venue in venues:
            route = router.latency_optimizer.get_best_route(region, venue, 'latency')
            if route:
                latency = route.latency_metrics.avg_latency_ms
                latencies.append(f"{latency:.1f}")
            else:
                latencies.append("N/A")
        
        print(f"{region:<12} {latencies[0]:<15} {latencies[1]:<15} {latencies[2]:<15}")
    
    print()


def demo_liquidity_aggregation():
    """Demonstrate liquidity aggregation."""
    print("=== Liquidity Aggregation Demo ===\n")
    
    router = SmartOrderRouter()
    
    # Get liquidity snapshot
    snapshot = router.liquidity_aggregator.get_liquidity_snapshot('BTC-USDT')
    
    if snapshot:
        print("1. Current BTC-USDT Liquidity Snapshot:")
        print(f"   Best Bid: ${snapshot.best_bid_price:.2f}")
        print(f"   Best Ask: ${snapshot.best_ask_price:.2f}")
        print(f"   Mid Price: ${snapshot.mid_price:.2f}")
        print(f"   Spread: {snapshot.spread_bps:.2f} bps")
        print(f"   Total Bid Quantity: {snapshot.total_bid_quantity:.2f} BTC")
        print(f"   Total Ask Quantity: {snapshot.total_ask_quantity:.2f} BTC")
        print(f"   Active Venues: {', '.join(snapshot.venues)}")
        
        print(f"\n2. Depth Analysis:")
        print(f"   Depth within 5 bps: {snapshot.depth_5bps:.2f} BTC")
        print(f"   Depth within 10 bps: {snapshot.depth_10bps:.2f} BTC")
        print(f"   Depth within 20 bps: {snapshot.depth_20bps:.2f} BTC")
        
        # Show venue liquidity ranking
        print(f"\n3. Venue Liquidity Ranking (Buy Side):")
        rankings = router.liquidity_aggregator.get_venue_liquidity_ranking('BTC-USDT', 'buy')
        
        for i, ranking in enumerate(rankings[:3], 1):
            print(f"   {i}. {ranking['venue_id']}: Score {ranking['liquidity_score']:.3f}, "
                  f"Quantity {ranking['total_quantity']:.2f} BTC, "
                  f"Best Price ${ranking['best_price']:.2f}")
    
    print()


def demo_large_order_execution():
    """Demonstrate large order execution planning."""
    print("=== Large Order Execution Planning ===\n")
    
    router = SmartOrderRouter()
    
    # Plan execution for a large order
    large_quantity = 50.0  # 50 BTC
    
    print(f"Planning execution for {large_quantity} BTC buy order:")
    
    # Get optimal execution plan
    execution_plan = router.liquidity_aggregator.find_optimal_execution_plan(
        symbol='BTC-USDT',
        quantity=large_quantity,
        side='buy',
        max_slippage_bps=15.0
    )
    
    if 'error' not in execution_plan:
        print(f"\nExecution Plan:")
        print(f"  Total Quantity: {execution_plan['total_quantity']} BTC")
        print(f"  Remaining Quantity: {execution_plan['remaining_quantity']} BTC")
        print(f"  Estimated Cost: ${execution_plan['estimated_cost']:,.2f}")
        print(f"  Estimated Slippage: {execution_plan['estimated_slippage_bps']:.2f} bps")
        
        print(f"\nVenue Allocations:")
        for venue in execution_plan['execution_venues']:
            print(f"  {venue['venue_id']}: {venue['quantity']:.2f} BTC @ ${venue['price']:.2f} "
                  f"(Slippage: {venue['slippage_bps']:.2f} bps)")
    else:
        print(f"Error: {execution_plan['error']}")
    
    print()


def demo_routing_with_preferences():
    """Demonstrate routing with specific preferences."""
    print("=== Routing with Preferences Demo ===\n")
    
    router = SmartOrderRouter()
    
    # Test different preferences
    preferences_scenarios = [
        {
            'name': 'US Region Only',
            'preferences': {'region': 'us', 'max_fee_bps': 20}
        },
        {
            'name': 'Low Fee Priority',
            'preferences': {'max_fee_bps': 5}
        },
        {
            'name': 'High Urgency',
            'preferences': {'urgency': 2.0}
        }
    ]
    
    print("Routing same order with different preferences:")
    print("-" * 70)
    print(f"{'Scenario':<20} {'Venue':<12} {'Cost ($)':<10} {'Latency (ms)':<12} {'Confidence':<10}")
    print("-" * 70)
    
    for scenario in preferences_scenarios:
        result = router.route_order(
            order_id=f"demo_pref_{scenario['name'].replace(' ', '_').lower()}",
            symbol="BTC-USDT",
            side="buy",
            quantity=2.0,
            order_type="market",
            strategy=RoutingStrategy.BALANCED,
            preferences=scenario['preferences']
        )
        
        print(f"{scenario['name']:<20} {result.selected_venue:<12} "
              f"${result.estimated_cost:<9.2f} {result.estimated_latency_ms:<11.1f} "
              f"{result.routing_confidence:<9.2f}")
    
    print()


def demo_performance_monitoring():
    """Demonstrate routing performance monitoring."""
    print("=== Performance Monitoring Demo ===\n")
    
    router = SmartOrderRouter()
    
    # Simulate some routing decisions
    print("Simulating routing decisions...")
    
    orders = [
        ("order_1", "BTC-USDT", "buy", 1.0, RoutingStrategy.BEST_PRICE),
        ("order_2", "ETH-USDT", "sell", 5.0, RoutingStrategy.BALANCED),
        ("order_3", "BTC-USDT", "buy", 10.0, RoutingStrategy.LOWEST_LATENCY),
        ("order_4", "ADA-USDT", "buy", 1000.0, RoutingStrategy.BEST_LIQUIDITY),
        ("order_5", "BTC-USDT", "sell", 0.5, RoutingStrategy.LOWEST_COST)
    ]
    
    for order_id, symbol, side, quantity, strategy in orders:
        result = router.route_order(
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type="market",
            strategy=strategy
        )
        
        # Simulate execution result
        execution_result = {
            'execution_time_ms': np.random.uniform(50, 300),
            'slippage_bps': np.random.uniform(1, 8),
            'cost': result.estimated_cost * np.random.uniform(0.95, 1.05),
            'success': np.random.random() > 0.1  # 90% success rate
        }
        
        router.update_execution_result(order_id, execution_result)
    
    # Get performance report
    print("Routing Performance Report:")
    performance_report = router.get_routing_performance_report()
    
    overall = performance_report['overall_performance']
    print(f"\nOverall Performance:")
    print(f"  Total Orders: {overall['total_orders']}")
    print(f"  Success Rate: {overall['success_rate_percent']:.1f}%")
    print(f"  Avg Execution Time: {overall['avg_execution_time_ms']:.1f} ms")
    print(f"  Avg Slippage: {overall['avg_slippage_bps']:.2f} bps")
    
    print(f"\nStrategy Performance:")
    for strategy, stats in performance_report['strategy_performance'].items():
        success_rate = (stats['successful_orders'] / stats['total_orders'] * 100 
                       if stats['total_orders'] > 0 else 0)
        print(f"  {strategy}: {success_rate:.1f}% success, "
              f"{stats['avg_slippage_bps']:.2f} bps avg slippage")
    
    print()


def main():
    """Run all smart routing demos."""
    print("Smart Order Routing System Demo")
    print("=" * 50)
    print()
    
    try:
        demo_basic_routing()
        demo_routing_strategies()
        demo_venue_performance()
        demo_latency_optimization()
        demo_liquidity_aggregation()
        demo_large_order_execution()
        demo_routing_with_preferences()
        demo_performance_monitoring()
        
        print("All demos completed successfully!")
        
    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
