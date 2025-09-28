"""
Simple Order Book Simulation Demo

A simplified demo that showcases order book simulation capabilities
without external dependencies.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

def demo_order_book_simulation():
    """Demo order book simulation without external dependencies."""
    print("📈 ORDER BOOK SIMULATION DEMO")
    print("=" * 50)
    
    try:
        from orderbook import OrderBookSnapshot, OrderBookSimulator, SimulatedOrder
        
        # Create sample order book
        print("Creating sample order book...")
        bids = [
            (50000.0, 1.5),   # 1.5 BTC at $50,000
            (49999.5, 2.0),   # 2.0 BTC at $49,999.5
            (49999.0, 1.8),   # 1.8 BTC at $49,999
            (49998.5, 3.2),   # 3.2 BTC at $49,998.5
            (49998.0, 2.5),   # 2.5 BTC at $49,998
        ]
        
        asks = [
            (50001.0, 1.2),   # 1.2 BTC at $50,001
            (50001.5, 1.8),   # 1.8 BTC at $50,001.5
            (50002.0, 2.3),   # 2.3 BTC at $50,002
            (50002.5, 1.5),   # 1.5 BTC at $50,002.5
            (50003.0, 3.0),   # 3.0 BTC at $50,003
        ]
        
        snapshot = OrderBookSnapshot(
            symbol="BTC/USDT",
            timestamp=datetime.now(),
            bids=bids,
            asks=asks,
            last_trade_price=50000.5
        )
        
        print(f"Order book created:")
        print(f"  Symbol: {snapshot.symbol}")
        print(f"  Best Bid: ${snapshot.best_bid:,.2f}")
        print(f"  Best Ask: ${snapshot.best_ask:,.2f}")
        print(f"  Spread: ${snapshot.spread:,.2f} ({snapshot.spread_bps:.2f} bps)")
        print(f"  Mid Price: ${snapshot.mid_price:,.2f}")
        print(f"  Valid: {snapshot.is_valid()}")
        
        # Create simulator
        print(f"\nCreating order book simulator...")
        simulator = OrderBookSimulator(
            latency_ms=25.0,
            partial_fill_probability=0.05,
            rejection_probability=0.01
        )
        simulator.set_order_book(snapshot)
        
        # Test different order types
        test_orders = [
            {
                "name": "Small Market Buy",
                "side": "buy",
                "order_type": "market",
                "quantity": 0.5
            },
            {
                "name": "Large Market Buy",
                "side": "buy", 
                "order_type": "market",
                "quantity": 3.0
            },
            {
                "name": "Market Sell",
                "side": "sell",
                "order_type": "market", 
                "quantity": 1.0
            },
            {
                "name": "Limit Buy (Below Market)",
                "side": "buy",
                "order_type": "limit",
                "quantity": 1.0,
                "price": 49999.0
            },
            {
                "name": "Limit Buy (Above Market)",
                "side": "buy",
                "order_type": "limit",
                "quantity": 1.0,
                "price": 50001.5
            }
        ]
        
        print(f"\nSimulating {len(test_orders)} different orders...")
        
        for i, order_data in enumerate(test_orders, 1):
            print(f"\n--- Order {i}: {order_data['name']} ---")
            
            # Create order
            order = simulator.create_order(
                symbol="BTC/USDT",
                side=order_data["side"],
                order_type=order_data["order_type"],
                quantity=order_data["quantity"],
                price=order_data.get("price")
            )
            
            print(f"Order: {order.side.upper()} {order.quantity} BTC ({order.order_type})")
            if order.price:
                print(f"Price: ${order.price:,.2f}")
            
            # Simulate execution
            fill = simulator.simulate_order(order)
            
            print(f"Result:")
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
        
        print("✅ Order book simulation demo completed successfully!")
        
    except Exception as e:
        print(f"❌ Order book simulation demo failed: {e}")
        import traceback
        traceback.print_exc()


def demo_order_book_storage():
    """Demo order book data storage."""
    print("\n💾 ORDER BOOK STORAGE DEMO")
    print("=" * 50)
    
    try:
        from orderbook import OrderBookSnapshot, SQLiteOrderBookStorage
        
        # Create storage
        storage = SQLiteOrderBookStorage(":memory:")  # In-memory database
        
        # Create sample snapshots
        print("Creating sample order book snapshots...")
        snapshots = []
        base_time = datetime.now()
        
        for i in range(5):
            timestamp = base_time + timedelta(minutes=i)
            
            # Simulate price movement
            price_move = i * 0.5  # $0.50 per minute
            
            bids = [(50000.0 + price_move, 1.0), (49999.0 + price_move, 2.0)]
            asks = [(50001.0 + price_move, 1.0), (50002.0 + price_move, 2.0)]
            
            snapshot = OrderBookSnapshot(
                symbol="BTC/USDT",
                timestamp=timestamp,
                bids=bids,
                asks=asks,
                last_trade_price=50000.5 + price_move,
                sequence_number=i
            )
            
            snapshots.append(snapshot)
        
        print(f"Created {len(snapshots)} snapshots")
        
        # Store snapshots
        print("Storing snapshots...")
        stored_count = 0
        for snapshot in snapshots:
            if storage.store_snapshot(snapshot):
                stored_count += 1
        
        print(f"✅ Stored {stored_count} snapshots")
        
        # Retrieve snapshots
        print("Retrieving snapshots...")
        start_time = snapshots[0].timestamp
        end_time = snapshots[-1].timestamp
        
        retrieved_snapshots = list(storage.get_snapshots("BTC/USDT", start_time, end_time))
        print(f"✅ Retrieved {len(retrieved_snapshots)} snapshots")
        
        # Display first snapshot details
        if retrieved_snapshots:
            first = retrieved_snapshots[0]
            print(f"\nFirst snapshot:")
            print(f"  Timestamp: {first.timestamp}")
            print(f"  Best Bid: ${first.best_bid:,.2f}")
            print(f"  Best Ask: ${first.best_ask:,.2f}")
            print(f"  Spread: {first.spread_bps:.2f} bps")
        
        storage.close()
        print("✅ Order book storage demo completed successfully!")
        
    except Exception as e:
        print(f"❌ Order book storage demo failed: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all order book demos."""
    print("🎯 ORDER BOOK SIMULATION DEMO")
    print("=" * 60)
    print("This demo showcases Phase 4 capabilities:")
    print("- Order book data structures")
    print("- Order execution simulation")
    print("- Data storage and retrieval")
    print("- Realistic fill modeling")
    print("=" * 60)
    
    try:
        demo_order_book_simulation()
        demo_order_book_storage()
        
        print("\n🎉 ALL ORDER BOOK DEMOS COMPLETED SUCCESSFULLY!")
        print("\nKey Insights:")
        print("- Order book simulation provides realistic execution modeling")
        print("- Different order types behave differently (market vs limit)")
        print("- Order size affects slippage and market impact")
        print("- Storage system enables historical replay capabilities")
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
