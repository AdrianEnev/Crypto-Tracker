"""
Demo: Order Book Simulation and Replay

This demo showcases Phase 4 capabilities including:
- Order book data fetching and storage
- Historical order book replay
- Realistic order execution simulation
- Integration with enhanced fee and slippage models
"""

import sys
import os
from pathlib import Path
import asyncio
from datetime import datetime, timedelta

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from orderbook import (
    OrderBookSnapshot, OrderBookFetcher, SQLiteOrderBookStorage, 
    OrderBookReplayEngine, OrderBookSimulator, SimulatedOrder
)
from fees import BacktestFeeCalculator, FeeCalculationMode, OrderFeeContext
from slippage import BacktestSlippageCalculator, SlippageType, SlippageContext
from data.ohlcv import get_candles


def create_sample_order_book_data():
    """Create sample order book data for demonstration."""
    print("📊 Creating sample order book data...")
    
    # Create sample bid/ask levels
    bids = [
        (50000.0, 1.5),   # 1.5 BTC at $50,000
        (49999.5, 2.0),   # 2.0 BTC at $49,999.5
        (49999.0, 1.8),   # 1.8 BTC at $49,999
        (49998.5, 3.2),   # 3.2 BTC at $49,998.5
        (49998.0, 2.5),   # 2.5 BTC at $49,998
        (49997.5, 4.0),   # 4.0 BTC at $49,997.5
        (49997.0, 1.2),   # 1.2 BTC at $49,997
        (49996.5, 2.8),   # 2.8 BTC at $49,996.5
        (49996.0, 3.5),   # 3.5 BTC at $49,996
        (49995.5, 2.1),   # 2.1 BTC at $49,995.5
    ]
    
    asks = [
        (50001.0, 1.2),   # 1.2 BTC at $50,001
        (50001.5, 1.8),   # 1.8 BTC at $50,001.5
        (50002.0, 2.3),   # 2.3 BTC at $50,002
        (50002.5, 1.5),   # 1.5 BTC at $50,002.5
        (50003.0, 3.0),   # 3.0 BTC at $50,003
        (50003.5, 2.2),   # 2.2 BTC at $50,003.5
        (50004.0, 1.9),   # 1.9 BTC at $50,004
        (50004.5, 2.7),   # 2.7 BTC at $50,004.5
        (50005.0, 3.3),   # 3.3 BTC at $50,005
        (50005.5, 2.4),   # 2.4 BTC at $50,005.5
    ]
    
    # Create order book snapshots at different times
    snapshots = []
    base_time = datetime.now() - timedelta(hours=1)
    
    for i in range(60):  # 60 snapshots (1 per minute)
        timestamp = base_time + timedelta(minutes=i)
        
        # Simulate some price movement
        price_move = (i % 10 - 5) * 0.5  # Oscillate between -2.5 and +2.5
        
        adjusted_bids = [(price + price_move, qty) for price, qty in bids]
        adjusted_asks = [(price + price_move, qty) for price, qty in asks]
        
        snapshot = OrderBookSnapshot(
            symbol="BTC/USDT",
            timestamp=timestamp,
            bids=adjusted_bids,
            asks=adjusted_asks,
            last_trade_price=50000.0 + price_move,
            last_trade_quantity=0.5 + (i % 3) * 0.2,  # Vary trade size
            sequence_number=i
        )
        
        snapshots.append(snapshot)
    
    print(f"✅ Created {len(snapshots)} sample order book snapshots")
    return snapshots


def demo_order_book_storage():
    """Demo order book data storage and retrieval."""
    print("\n💾 ORDER BOOK STORAGE DEMO")
    print("=" * 50)
    
    # Create storage
    storage = SQLiteOrderBookStorage("./demo_orderbook.db")
    
    # Create sample data
    snapshots = create_sample_order_book_data()
    
    # Store snapshots
    print("Storing order book snapshots...")
    stored_count = 0
    for snapshot in snapshots:
        if storage.store_snapshot(snapshot):
            stored_count += 1
    
    print(f"✅ Stored {stored_count} snapshots")
    
    # Retrieve and display some snapshots
    print("\nRetrieving snapshots...")
    start_time = snapshots[0].timestamp
    end_time = snapshots[10].timestamp
    
    retrieved_snapshots = list(storage.get_snapshots("BTC/USDT", start_time, end_time))
    print(f"✅ Retrieved {len(retrieved_snapshots)} snapshots")
    
    # Display details of first snapshot
    if retrieved_snapshots:
        first_snapshot = retrieved_snapshots[0]
        print(f"\nFirst snapshot details:")
        print(f"  Timestamp: {first_snapshot.timestamp}")
        print(f"  Symbol: {first_snapshot.symbol}")
        print(f"  Best Bid: ${first_snapshot.best_bid:,.2f}")
        print(f"  Best Ask: ${first_snapshot.best_ask:,.2f}")
        print(f"  Spread: ${first_snapshot.spread:,.2f} ({first_snapshot.spread_bps:.2f} bps)")
        print(f"  Mid Price: ${first_snapshot.mid_price:,.2f}")
        print(f"  Bid Levels: {len(first_snapshot.bids.levels)}")
        print(f"  Ask Levels: {len(first_snapshot.asks.levels)}")
    
    storage.close()
    return storage


def demo_order_book_simulation():
    """Demo order book simulation and execution."""
    print("\n🎯 ORDER BOOK SIMULATION DEMO")
    print("=" * 50)
    
    # Create simulator
    simulator = OrderBookSimulator(
        latency_ms=25.0,
        partial_fill_probability=0.05,
        rejection_probability=0.01
    )
    
    # Create sample data
    snapshots = create_sample_order_book_data()
    
    # Set order book
    test_snapshot = snapshots[30]  # Use middle snapshot
    simulator.set_order_book(test_snapshot)
    
    print(f"Using order book snapshot from {test_snapshot.timestamp}")
    print(f"Best Bid: ${test_snapshot.best_bid:,.2f}")
    print(f"Best Ask: ${test_snapshot.best_ask:,.2f}")
    print(f"Spread: {test_snapshot.spread_bps:.2f} bps")
    
    # Create test orders
    test_orders = [
        simulator.create_order("BTC/USDT", "buy", "market", 1.0),   # Small buy
        simulator.create_order("BTC/USDT", "sell", "market", 2.0),  # Medium sell
        simulator.create_order("BTC/USDT", "buy", "market", 5.0),   # Large buy
        simulator.create_order("BTC/USDT", "buy", "limit", 1.0, price=49999.0),  # Limit buy
        simulator.create_order("BTC/USDT", "sell", "limit", 1.0, price=50002.0), # Limit sell
    ]
    
    print(f"\nSimulating {len(test_orders)} orders...")
    
    # Simulate orders
    results = []
    for i, order in enumerate(test_orders, 1):
        print(f"\nOrder {i}: {order.side.upper()} {order.quantity} BTC ({order.order_type})")
        
        fill = simulator.simulate_order(order)
        results.append(fill)
        
        print(f"  Status: {'FILLED' if fill.is_completely_filled else 'PARTIAL' if fill.is_partial_fill else 'UNFILLED'}")
        print(f"  Filled: {fill.filled_quantity:.4f} BTC")
        print(f"  Remaining: {fill.remaining_quantity:.4f} BTC")
        print(f"  Avg Price: ${fill.average_price:,.2f}")
        print(f"  Total Cost: ${fill.total_cost:,.2f}")
        print(f"  Slippage: {fill.slippage_bps:.2f} bps")
        print(f"  Market Impact: {fill.market_impact_bps:.2f} bps")
        print(f"  Levels Consumed: {fill.levels_consumed}")
        print(f"  Execution Time: {fill.execution_time_ms:.1f} ms")
    
    # Display simulation statistics
    stats = simulator.get_simulation_statistics()
    print(f"\n📊 SIMULATION STATISTICS")
    print("-" * 30)
    print(f"Total Orders: {stats['total_orders']}")
    print(f"Filled Orders: {stats['filled_orders']}")
    print(f"Partial Fills: {stats['partial_fills']}")
    print(f"Rejected Orders: {stats['rejected_orders']}")
    print(f"Fill Rate: {stats['fill_rate']:.1f}%")
    print(f"Avg Execution Time: {stats['avg_execution_time_ms']:.1f} ms")
    print(f"Avg Slippage: {stats['avg_slippage_bps']:.2f} bps")
    print(f"Avg Market Impact: {stats['avg_market_impact_bps']:.2f} bps")
    
    return results


def demo_order_book_replay():
    """Demo order book replay functionality."""
    print("\n⏯️  ORDER BOOK REPLAY DEMO")
    print("=" * 50)
    
    # Create storage and sample data
    storage = SQLiteOrderBookStorage("./demo_orderbook.db")
    snapshots = create_sample_order_book_data()
    
    # Store snapshots
    for snapshot in snapshots:
        storage.store_snapshot(snapshot)
    
    # Create replay engine
    replay_engine = OrderBookReplayEngine(
        storage=storage,
        replay_speed=10.0,  # 10x speed for demo
        start_time=snapshots[0].timestamp,
        end_time=snapshots[-1].timestamp
    )
    
    # Add event handlers
    def snapshot_handler(snapshot):
        print(f"📊 Replay: {snapshot.timestamp} - Bid: ${snapshot.best_bid:,.2f}, Ask: ${snapshot.best_ask:,.2f}, Spread: {snapshot.spread_bps:.2f} bps")
    
    replay_engine.add_snapshot_handler(snapshot_handler)
    
    # Start replay
    print("Starting order book replay...")
    replay_engine.start_replay()
    
    # Replay first 10 snapshots
    replayed_count = 0
    for snapshot in replay_engine.replay_snapshots("BTC/USDT", snapshots[0].timestamp, snapshots[10].timestamp):
        replayed_count += 1
        if replayed_count >= 10:
            break
    
    print(f"✅ Replayed {replayed_count} snapshots")
    
    # Get replay statistics
    stats = replay_engine.get_replay_statistics("BTC/USDT", snapshots[0].timestamp, snapshots[-1].timestamp)
    print(f"\n📈 REPLAY STATISTICS")
    print("-" * 30)
    print(f"Total Snapshots: {stats['snapshot_count']}")
    print(f"Duration: {stats['duration_hours']:.2f} hours")
    print(f"Avg Interval: {stats['avg_snapshot_interval_seconds']:.1f} seconds")
    
    storage.close()


def demo_integrated_backtest():
    """Demo integrated backtesting with order book simulation."""
    print("\n🚀 INTEGRATED BACKTEST DEMO")
    print("=" * 50)
    
    # Create fee and slippage calculators
    fee_calculator = BacktestFeeCalculator(FeeCalculationMode.REALISTIC)
    slippage_calculator = BacktestSlippageCalculator(SlippageType.DEPTH_BASED)
    
    # Create order book simulator
    order_simulator = OrderBookSimulator()
    
    # Create sample order book
    snapshots = create_sample_order_book_data()
    test_snapshot = snapshots[30]
    order_simulator.set_order_book(test_snapshot)
    
    print(f"Using order book: {test_snapshot.symbol} at {test_snapshot.timestamp}")
    
    # Create test strategy orders
    strategy_orders = [
        {
            "symbol": "BTC/USDT",
            "side": "buy",
            "quantity": 1.0,
            "order_type": "market",
            "strategy": "momentum"
        },
        {
            "symbol": "BTC/USDT", 
            "side": "sell",
            "quantity": 0.5,
            "order_type": "limit",
            "price": 50002.0,
            "strategy": "mean_reversion"
        }
    ]
    
    total_costs = 0.0
    total_slippage = 0.0
    total_fees = 0.0
    
    print(f"\nExecuting {len(strategy_orders)} strategy orders...")
    
    for i, order_data in enumerate(strategy_orders, 1):
        print(f"\n--- Order {i}: {order_data['strategy'].upper()} Strategy ---")
        
        # Create simulated order
        order = order_simulator.create_order(
            symbol=order_data["symbol"],
            side=order_data["side"],
            order_type=order_data["order_type"],
            quantity=order_data["quantity"],
            price=order_data.get("price"),
            strategy_id=order_data["strategy"]
        )
        
        # Simulate order execution
        fill = order_simulator.simulate_order(order)
        
        print(f"Order: {order.side.upper()} {order.quantity} BTC")
        print(f"Fill: {fill.filled_quantity:.4f} BTC at ${fill.average_price:,.2f}")
        print(f"Execution Cost: ${fill.total_cost:,.2f}")
        print(f"Slippage: {fill.slippage_bps:.2f} bps")
        
        # Calculate fees
        if fill.filled_quantity > 0:
            trade_value = fill.filled_quantity * fill.average_price
            
            fee_context = OrderFeeContext(
                order_value_usd=trade_value,
                order_quantity=fill.filled_quantity,
                order_price=fill.average_price,
                side=order.side,
                order_type=order.order_type,
                is_maker=(order.order_type == "limit"),
                exchange="binance",
                symbol=order.symbol,
                monthly_volume_usd=100000.0
            )
            
            fee_breakdown = fee_calculator.calculate_fees_with_tracking(fee_context, trade_value)
            
            print(f"Fees: ${fee_breakdown.total_fees_usd:.2f} ({fee_breakdown.trading_fee_usd / trade_value * 10000:.2f} bps)")
            
            # Calculate slippage
            slippage_context = SlippageContext(
                symbol=order.symbol,
                side=order.side,
                quantity=fill.filled_quantity,
                order_type=order.order_type,
                timestamp=fill.fill_timestamp,
                current_price=fill.average_price,
                volume_24h=None,
                volatility=None
            )
            
            slippage_result = slippage_calculator.calculate_slippage_with_tracking(
                slippage_context, trade_value, fill.filled_quantity
            )
            
            print(f"Modeled Slippage: {slippage_result.slippage_bps:.2f} bps")
            
            # Accumulate costs
            total_costs += fill.total_cost
            total_slippage += fill.slippage_bps
            total_fees += fee_breakdown.total_fees_usd
    
    print(f"\n💰 TOTAL EXECUTION SUMMARY")
    print("-" * 30)
    print(f"Total Trade Value: ${total_costs:,.2f}")
    print(f"Total Fees: ${total_fees:,.2f}")
    print(f"Avg Slippage: {total_slippage / len(strategy_orders):.2f} bps")
    print(f"Total Execution Costs: ${total_fees + (total_slippage / 10000 * total_costs):,.2f}")
    
    # Display detailed statistics
    fee_stats = fee_calculator.export_fee_report()
    slippage_stats = slippage_calculator.export_slippage_report()
    
    print(f"\n📊 DETAILED STATISTICS")
    print("-" * 30)
    print(f"Fee Efficiency Score: {fee_stats['summary'].get('fee_efficiency_score', 0):.4f}")
    print(f"Slippage Efficiency Score: {slippage_stats['summary'].get('slippage_efficiency_score', 0):.4f}")
    print(f"Maker Ratio: {fee_stats['summary'].get('maker_ratio', 0):.1f}%")


def main():
    """Run all demos."""
    print("🎯 ORDER BOOK SIMULATION & REPLAY DEMO")
    print("=" * 60)
    print("This demo showcases Phase 4 capabilities:")
    print("- Order book data management")
    print("- Historical replay simulation")
    print("- Realistic order execution")
    print("- Integration with fee/slippage models")
    print("=" * 60)
    
    try:
        # Run demos
        demo_order_book_storage()
        demo_order_book_simulation()
        demo_order_book_replay()
        demo_integrated_backtest()
        
        print("\n✅ All demos completed successfully!")
        print("\nKey Insights:")
        print("- Order book simulation provides ultra-realistic execution modeling")
        print("- Historical replay enables strategy testing on real market conditions")
        print("- Integration with fee/slippage models gives complete cost analysis")
        print("- Different order types (market, limit, stop) behave realistically")
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
