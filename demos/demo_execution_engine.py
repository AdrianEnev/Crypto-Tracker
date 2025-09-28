"""
Demo script for TWAP/VWAP execution engine and execution analytics.
Shows advanced order execution capabilities with market impact modeling.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
from datetime import datetime, timedelta, timezone
from src.execution.twap_executor import TWAPExecutor, TWAPConfig
from src.execution.vwap_executor import VWAPExecutor, VWAPConfig
from src.execution.execution_analytics import ExecutionAnalytics, ExecutionReport
from src.execution.market_impact_model import MarketImpactModel, MarketImpactConfig
from src.order_manager.models import OrderState, Order, OrderType


def demo_twap_execution():
    """Demo TWAP execution with market impact minimization."""
    print("=== TWAP Execution Demo ===\n")
    
    # Create TWAP configuration
    twap_config = TWAPConfig(
        duration_minutes=30,
        slices=10,
        min_slice_size=0.01,  # 1% minimum
        max_slice_size=0.15,  # 15% maximum
        slice_interval_seconds=180,  # 3 minutes between slices
        market_impact_threshold=0.001,  # 0.1% impact threshold
        urgency_factor=1.2,  # Slightly urgent
        adaptive_sizing=True,
        volume_participation_rate=0.08  # 8% of average volume
    )
    
    # Create TWAP executor
    twap_executor = TWAPExecutor(twap_config)
    
    print("TWAP Configuration:")
    print(f"  Duration: {twap_config.duration_minutes} minutes")
    print(f"  Slices: {twap_config.slices}")
    print(f"  Slice interval: {twap_config.slice_interval_seconds} seconds")
    print(f"  Min/Max slice size: {twap_config.min_slice_size*100:.1f}% / {twap_config.max_slice_size*100:.1f}%")
    print(f"  Market impact threshold: {twap_config.market_impact_threshold*100:.1f}%")
    print(f"  Urgency factor: {twap_config.urgency_factor}")
    print()
    
    # Execute TWAP order
    symbol = "BTC-USDT"
    side = "buy"
    quantity = 2.5  # 2.5 BTC
    
    print(f"Executing TWAP order:")
    print(f"  Symbol: {symbol}")
    print(f"  Side: {side}")
    print(f"  Quantity: {quantity} BTC")
    print(f"  Estimated value: ${quantity * 50000:,.0f}")
    print()
    
    execution_id = twap_executor.execute_twap(symbol, side, quantity)
    print(f"TWAP execution started with ID: {execution_id}")
    
    # Simulate execution progress
    print("\nExecution Progress:")
    for i in range(5):  # Show first 5 slices
        status = twap_executor.get_execution_status(execution_id)
        if status:
            print(f"  Slice {i+1}: {status['progress']*100:.1f}% complete, "
                  f"Executed: {status['executed_quantity']:.2f} BTC, "
                  f"Remaining: {status['remaining_quantity']:.2f} BTC")
        else:
            print(f"  Slice {i+1}: Execution completed or not found")
    
    # Show execution history
    history = twap_executor.get_execution_history()
    if history:
        print(f"\nExecution History ({len(history)} executions):")
        for execution in history[-3:]:  # Show last 3
            print(f"  {execution['symbol']} {execution['side']}: "
                  f"{execution['executed_quantity']:.2f} units, "
                  f"Avg price: ${execution['avg_execution_price']:.2f}, "
                  f"Impact: {execution['market_impact']*100:.2f}%")


def demo_vwap_execution():
    """Demo VWAP execution with volume-based slicing."""
    print("\n=== VWAP Execution Demo ===\n")
    
    # Create VWAP configuration
    vwap_config = VWAPConfig(
        duration_minutes=60,
        slices=20,
        participation_rate=0.12,  # 12% of average volume
        min_slice_size=0.005,  # 0.5% minimum
        max_slice_size=0.18,  # 18% maximum
        volume_lookback_days=30,
        adaptive_timing=True,
        market_hours_only=True,
        urgency_factor=1.0
    )
    
    # Create VWAP executor
    vwap_executor = VWAPExecutor(vwap_config)
    
    print("VWAP Configuration:")
    print(f"  Duration: {vwap_config.duration_minutes} minutes")
    print(f"  Slices: {vwap_config.slices}")
    print(f"  Participation rate: {vwap_config.participation_rate*100:.1f}%")
    print(f"  Volume lookback: {vwap_config.volume_lookback_days} days")
    print(f"  Market hours only: {vwap_config.market_hours_only}")
    print()
    
    # Execute VWAP order
    symbol = "ETH-USDT"
    side = "sell"
    quantity = 50.0  # 50 ETH
    
    print(f"Executing VWAP order:")
    print(f"  Symbol: {symbol}")
    print(f"  Side: {side}")
    print(f"  Quantity: {quantity} ETH")
    print(f"  Estimated value: ${quantity * 3000:,.0f}")
    print()
    
    execution_id = vwap_executor.execute_vwap(symbol, side, quantity)
    print(f"VWAP execution started with ID: {execution_id}")
    
    # Simulate execution progress
    print("\nExecution Progress:")
    for i in range(5):  # Show first 5 slices
        status = vwap_executor.get_execution_status(execution_id)
        if status:
            print(f"  Slice {i+1}: {status['progress']*100:.1f}% complete, "
                  f"Executed: {status['executed_quantity']:.2f} ETH, "
                  f"Current VWAP: ${status['current_vwap']:.2f}")
        else:
            print(f"  Slice {i+1}: Execution completed or not found")
    
    # Show execution history
    history = vwap_executor.get_execution_history()
    if history:
        print(f"\nExecution History ({len(history)} executions):")
        for execution in history[-3:]:  # Show last 3
            print(f"  {execution['symbol']} {execution['side']}: "
                  f"{execution['executed_quantity']:.2f} units, "
                  f"VWAP deviation: {execution['vwap_deviation']*100:.2f}%, "
                  f"Volume participation: {execution['volume_participation']*100:.1f}%")


def demo_market_impact_modeling():
    """Demo market impact modeling and optimization."""
    print("\n=== Market Impact Modeling Demo ===\n")
    
    # Create market impact model
    impact_config = MarketImpactConfig(
        model_type="square_root",
        impact_constant=0.001,
        participation_rate_exponent=0.5,
        volatility_multiplier=1.2,
        permanent_impact_ratio=0.6
    )
    
    impact_model = MarketImpactModel(impact_config)
    
    print("Market Impact Model Configuration:")
    print(f"  Model type: {impact_config.model_type}")
    print(f"  Impact constant: {impact_config.impact_constant}")
    print(f"  Participation rate exponent: {impact_config.participation_rate_exponent}")
    print(f"  Volatility multiplier: {impact_config.volatility_multiplier}")
    print(f"  Permanent impact ratio: {impact_config.permanent_impact_ratio}")
    print()
    
    # Test different order sizes
    symbol = "BTC-USDT"
    current_price = 50000.0
    market_volume = 2000000.0  # 2M BTC daily volume
    volatility = 0.025  # 2.5% daily volatility
    
    print("Market Impact Analysis:")
    print(f"  Symbol: {symbol}")
    print(f"  Current price: ${current_price:,.0f}")
    print(f"  Market volume: {market_volume:,.0f} BTC/day")
    print(f"  Volatility: {volatility*100:.1f}%")
    print()
    
    order_sizes = [10, 50, 100, 250, 500]  # BTC
    
    print("Order Size Impact Analysis:")
    print(f"{'Size (BTC)':<12} {'Participation':<15} {'Temp Impact':<12} {'Perm Impact':<12} {'Total Impact':<12} {'Cost ($)':<12}")
    print("-" * 80)
    
    for size in order_sizes:
        impact_result = impact_model.calculate_market_impact(
            symbol, size, current_price, market_volume, volatility
        )
        
        participation = size / market_volume
        cost = impact_result.total_impact * size * current_price
        
        print(f"{size:<12} {participation*100:<14.3f}% {impact_result.temporary_impact*100:<11.2f}% "
              f"{impact_result.permanent_impact*100:<11.2f}% {impact_result.total_impact*100:<11.2f}% "
              f"${cost:,.0f}")
    
    # Optimize order size for impact threshold
    print(f"\nOrder Size Optimization:")
    total_quantity = 200.0  # Want to buy 200 BTC
    max_impact_threshold = 0.005  # 0.5% max impact
    
    optimal_size, num_slices = impact_model.optimize_order_size(
        symbol, total_quantity, current_price, market_volume, volatility, max_impact_threshold
    )
    
    print(f"  Target quantity: {total_quantity} BTC")
    print(f"  Max impact threshold: {max_impact_threshold*100:.1f}%")
    print(f"  Optimal slice size: {optimal_size:.2f} BTC")
    print(f"  Number of slices: {num_slices}")
    print(f"  Execution time: ~{num_slices * 3:.0f} minutes (3 min per slice)")
    
    # Calculate execution cost
    execution_cost = impact_model.estimate_execution_cost(
        symbol, optimal_size, current_price, market_volume, volatility, num_slices * 3
    )
    
    print(f"\nExecution Cost Breakdown:")
    print(f"  Trading fees: ${execution_cost['trading_fees']:,.2f}")
    print(f"  Market impact cost: ${execution_cost['market_impact_cost']:,.2f}")
    print(f"  Timing cost: ${execution_cost['timing_cost']:,.2f}")
    print(f"  Total cost: ${execution_cost['total_cost']:,.2f}")
    print(f"  Cost in bps: {execution_cost['cost_bps']:.1f} bps")


def demo_execution_analytics():
    """Demo execution quality analytics and reporting."""
    print("\n=== Execution Analytics Demo ===\n")
    
    # Create execution analytics
    analytics = ExecutionAnalytics()
    
    # Generate mock order data for analysis
    mock_orders = generate_mock_orders()
    
    print(f"Generated {len(mock_orders)} mock orders for analysis")
    print()
    
    # Analyze execution quality
    analysis_period = (
        datetime.now(timezone.utc) - timedelta(days=1),
        datetime.now(timezone.utc)
    )
    
    report = analytics.analyze_execution_quality(mock_orders, analysis_period)
    
    # Display comprehensive report
    print("Execution Quality Analysis:")
    print(f"  Analysis period: {analysis_period[0].strftime('%Y-%m-%d %H:%M')} to {analysis_period[1].strftime('%Y-%m-%d %H:%M')}")
    print(f"  Total orders analyzed: {report.total_orders_analyzed}")
    print(f"  Overall quality score: {report.quality_score:.1f}/100")
    print()
    
    # Key metrics
    metrics = report.metrics
    print("Key Performance Metrics:")
    print(f"  Fill rate: {metrics.overall_fill_rate:.1%}")
    print(f"  Average slippage: {metrics.avg_slippage_bps:.1f} bps")
    print(f"  Average fill time: {metrics.avg_fill_time_seconds:.1f} seconds")
    print(f"  Market impact: {metrics.avg_market_impact_bps:.1f} bps")
    print(f"  Execution cost: {metrics.avg_execution_cost_bps:.1f} bps")
    print()
    
    # Performance by symbol
    if report.performance_by_symbol:
        print("Performance by Symbol:")
        for symbol, symbol_metrics in report.performance_by_symbol.items():
            print(f"  {symbol}: Fill rate {symbol_metrics.overall_fill_rate:.1%}, "
                  f"Slippage {symbol_metrics.avg_slippage_bps:.1f} bps")
        print()
    
    # Performance by side
    if report.performance_by_side:
        print("Performance by Order Side:")
        for side, side_metrics in report.performance_by_side.items():
            print(f"  {side}: Fill rate {side_metrics.overall_fill_rate:.1%}, "
                  f"Slippage {side_metrics.avg_slippage_bps:.1f} bps")
        print()
    
    # Recommendations
    if report.recommendations:
        print("Recommendations:")
        for i, rec in enumerate(report.recommendations, 1):
            print(f"  {i}. {rec}")
        print()
    
    # Generate full report summary
    print("Full Execution Report:")
    print(analytics.generate_execution_report_summary(report))


def generate_mock_orders() -> list:
    """Generate mock order data for demonstration."""
    orders = []
    symbols = ["BTC-USDT", "ETH-USDT", "ADA-USDT"]
    sides = ["buy", "sell"]
    
    np.random.seed(42)
    
    for i in range(50):
        symbol = np.random.choice(symbols)
        side = np.random.choice(sides)
        quantity = np.random.uniform(0.1, 5.0)
        price = np.random.uniform(45000, 55000) if symbol == "BTC-USDT" else np.random.uniform(2500, 3500)
        
        # Create order
        order = Order(
            id=f"mock_order_{i}",
            client_order_id=f"mock_client_{i}",
            symbol=symbol,
            side=side,
            order_type=OrderType.MARKET,
            state=np.random.choice([OrderState.FILLED, OrderState.PARTIALLY_FILLED, OrderState.CANCELED]),
            quantity=quantity,
            price=price,
            stop_price=None,
            time_in_force=None,
            exchange="mock_exchange"
        )
        
        # Add filled data for filled orders
        if order.state in [OrderState.FILLED, OrderState.PARTIALLY_FILLED]:
            order.filled_quantity = quantity * np.random.uniform(0.8, 1.0)
            order.average_fill_price = price * np.random.uniform(0.999, 1.001)
            order.filled_at = order.created_at + timedelta(seconds=np.random.uniform(10, 300))
        
        orders.append(order)
    
    return orders


def demo_comprehensive_execution_analysis():
    """Demo comprehensive execution analysis combining all components."""
    print("\n=== Comprehensive Execution Analysis Demo ===\n")
    
    # Create all execution components
    twap_config = TWAPConfig(duration_minutes=30, slices=10)
    vwap_config = VWAPConfig(duration_minutes=60, slices=20)
    impact_config = MarketImpactConfig(model_type="square_root")
    
    twap_executor = TWAPExecutor(twap_config)
    vwap_executor = VWAPExecutor(vwap_config)
    impact_model = MarketImpactModel(impact_config)
    analytics = ExecutionAnalytics()
    
    print("Execution Strategy Comparison:")
    print("Comparing TWAP vs VWAP execution for large order")
    print()
    
    # Test parameters
    symbol = "BTC-USDT"
    quantity = 100.0  # 100 BTC
    side = "buy"
    
    # TWAP execution
    print("TWAP Execution Analysis:")
    twap_execution_id = twap_executor.execute_twap(symbol, side, quantity)
    
    # VWAP execution
    print("VWAP Execution Analysis:")
    vwap_execution_id = vwap_executor.execute_vwap(symbol, side, quantity)
    
    # Market impact analysis
    current_price = 50000.0
    market_volume = 2000000.0
    volatility = 0.025
    
    twap_impact = impact_model.calculate_market_impact(
        symbol, quantity, current_price, market_volume, volatility, 30
    )
    
    vwap_impact = impact_model.calculate_market_impact(
        symbol, quantity, current_price, market_volume, volatility, 60
    )
    
    print(f"\nMarket Impact Comparison:")
    print(f"  TWAP (30 min): {twap_impact.total_impact*100:.3f}% total impact")
    print(f"  VWAP (60 min): {vwap_impact.total_impact*100:.3f}% total impact")
    print(f"  TWAP temporary impact: {twap_impact.temporary_impact*100:.3f}%")
    print(f"  VWAP temporary impact: {vwap_impact.temporary_impact*100:.3f}%")
    print(f"  TWAP permanent impact: {twap_impact.permanent_impact*100:.3f}%")
    print(f"  VWAP permanent impact: {vwap_impact.permanent_impact*100:.3f}%")
    
    # Cost comparison
    twap_cost = impact_model.estimate_execution_cost(
        symbol, quantity, current_price, market_volume, volatility, 30
    )
    
    vwap_cost = impact_model.estimate_execution_cost(
        symbol, quantity, current_price, market_volume, volatility, 60
    )
    
    print(f"\nExecution Cost Comparison:")
    print(f"  TWAP total cost: ${twap_cost['total_cost']:,.2f} ({twap_cost['cost_bps']:.1f} bps)")
    print(f"  VWAP total cost: ${vwap_cost['total_cost']:,.2f} ({vwap_cost['cost_bps']:.1f} bps)")
    print(f"  Cost difference: ${abs(twap_cost['total_cost'] - vwap_cost['total_cost']):,.2f}")
    
    # Recommendations
    if twap_cost['total_cost'] < vwap_cost['total_cost']:
        print(f"\nRecommendation: Use TWAP execution for better cost efficiency")
    else:
        print(f"\nRecommendation: Use VWAP execution for better cost efficiency")
    
    print(f"\nKey Insights:")
    print(f"- TWAP provides faster execution with potentially higher market impact")
    print(f"- VWAP spreads execution over time to minimize market impact")
    print(f"- Choice depends on urgency vs. cost optimization priorities")
    print(f"- Both strategies significantly outperform naive market orders")


if __name__ == "__main__":
    demo_twap_execution()
    demo_vwap_execution()
    demo_market_impact_modeling()
    demo_execution_analytics()
    demo_comprehensive_execution_analysis()
    
    print("\n=== Demo Complete ===")
    print("\nKey Features of Advanced Execution Engine:")
    print("1. TWAP EXECUTION: Time-weighted average price with intelligent slicing")
    print("2. VWAP EXECUTION: Volume-weighted average price with volume profile analysis")
    print("3. MARKET IMPACT MODELING: Multiple impact models with optimization")
    print("4. EXECUTION ANALYTICS: Comprehensive quality analysis and reporting")
    print("5. COST OPTIMIZATION: Smart order sizing and timing decisions")
    print("6. PERFORMANCE MONITORING: Real-time execution tracking and adjustment")
    print("\nBenefits:")
    print("- Minimizes market impact for large orders")
    print("- Optimizes execution costs and timing")
    print("- Provides detailed execution quality analysis")
    print("- Enables data-driven execution strategy selection")
    print("- Supports institutional-grade order management")
