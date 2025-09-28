#!/usr/bin/env python3
"""
Order Management System Demo

Demonstrates the usage of the new order management system
with various order types and features.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.order_manager import (
    OrderManager, OrderManagerConfig, OrderRequest, OrderType, 
    OrderState, TimeInForce, RetryConfig, TWAPConfig, VWAPConfig
)
from src.order_manager.executors import EnhancedPaperExecutor
from src.order_manager.integration import OrderManagerIntegration


def demo_basic_orders():
    """Demonstrate basic order placement."""
    print("=== Basic Order Management Demo ===")
    
    # Create order manager
    config = OrderManagerConfig()
    order_manager = OrderManager(None, None, None, config)
    
    # Register paper executor
    paper_executor = EnhancedPaperExecutor()
    order_manager.register_executor("paper", paper_executor)
    
    # Disable smart routing for basic demo
    order_manager.config.enable_smart_routing = False
    
    # Place a market buy order
    buy_request = OrderRequest(
        symbol="BTC/USDT",
        side="buy",
        order_type=OrderType.MARKET,
        quantity=0.1,
        strategy_id="demo_strategy"
    )
    
    buy_order = order_manager.place_order(buy_request)
    print(f"Placed buy order: {buy_order.id}")
    print(f"Order state: {buy_order.state.value}")
    print(f"Fill percentage: {buy_order.fill_percentage:.2f}%")
    
    # Place a limit sell order
    sell_request = OrderRequest(
        symbol="BTC/USDT",
        side="sell",
        order_type=OrderType.LIMIT,
        quantity=0.1,
        price=50000.0,
        time_in_force=TimeInForce.GTC,
        strategy_id="demo_strategy"
    )
    
    sell_order = order_manager.place_order(sell_request)
    print(f"Placed sell order: {sell_order.id}")
    print(f"Order state: {sell_order.state.value}")
    
    # Get order statistics
    stats = order_manager.get_order_statistics()
    print(f"Total orders: {stats['total_orders']}")
    print(f"Active orders: {stats['active_orders']}")
    
    return order_manager


def demo_twap_orders():
    """Demonstrate TWAP order execution."""
    print("\n=== TWAP Order Demo ===")
    
    # Create order manager with TWAP config
    twap_config = TWAPConfig(
        min_slice_size_usd=50,
        max_slices=10,
        min_slice_interval_seconds=10
    )
    
    config = OrderManagerConfig(twap_config=twap_config)
    order_manager = OrderManager(None, None, None, config)
    
    # Register paper executor
    paper_executor = EnhancedPaperExecutor()
    order_manager.register_executor("paper", paper_executor)
    
    # Disable smart routing for TWAP demo
    order_manager.config.enable_smart_routing = False
    
    # Place TWAP order
    twap_request = OrderRequest(
        symbol="ETH/USDT",
        side="buy",
        order_type=OrderType.TWAP,
        quantity=1.0,
        price=3000.0,
        twap_duration_seconds=300,  # 5 minutes
        strategy_id="twap_strategy"
    )
    
    twap_order = order_manager.place_order(twap_request)
    print(f"Placed TWAP order: {twap_order.id}")
    print(f"TWAP duration: {twap_order.twap_duration_seconds} seconds")
    print(f"Slice count: {twap_order.twap_slice_count}")
    print(f"Slice interval: {twap_order.twap_slice_interval} seconds")
    
    # Get TWAP status
    twap_status = order_manager.get_twap_status(twap_order.id)
    if twap_status:
        print(f"TWAP status: {twap_status['completed_slices']}/{twap_status['total_slices']} slices completed")
        print(f"Total filled: {twap_status['total_filled']}")
    
    return order_manager


def demo_vwap_orders():
    """Demonstrate VWAP order execution."""
    print("\n=== VWAP Order Demo ===")
    
    # Create order manager with VWAP config
    vwap_config = VWAPConfig(
        participation_rate=0.05,  # 5% participation
        min_slice_size_usd=50,
        slice_duration_minutes=2
    )
    
    config = OrderManagerConfig(vwap_config=vwap_config)
    order_manager = OrderManager(None, None, None, config)
    
    # Register paper executor
    paper_executor = EnhancedPaperExecutor()
    order_manager.register_executor("paper", paper_executor)
    
    # Disable smart routing for VWAP demo
    order_manager.config.enable_smart_routing = False
    
    # Place VWAP order
    vwap_request = OrderRequest(
        symbol="SOL/USDT",
        side="buy",
        order_type=OrderType.VWAP,
        quantity=10.0,
        price=100.0,
        vwap_participation_rate=0.1,  # 10% participation
        strategy_id="vwap_strategy"
    )
    
    vwap_order = order_manager.place_order(vwap_request)
    print(f"Placed VWAP order: {vwap_order.id}")
    print(f"Participation rate: {vwap_order.vwap_participation_rate:.2%}")
    
    # Get VWAP status
    vwap_status = order_manager.get_vwap_status(vwap_order.id)
    if vwap_status:
        print(f"VWAP status: {vwap_status['executed_slices']} slices executed")
        print(f"Total filled: {vwap_status['total_filled']}")
        print(f"Average participation: {vwap_status['average_participation_rate']:.2%}")
    
    return order_manager


def demo_order_cancellation():
    """Demonstrate order cancellation."""
    print("\n=== Order Cancellation Demo ===")
    
    config = OrderManagerConfig()
    order_manager = OrderManager(None, None, None, config)
    
    # Register paper executor
    paper_executor = EnhancedPaperExecutor()
    order_manager.register_executor("paper", paper_executor)
    
    # Disable smart routing for cancellation demo
    order_manager.config.enable_smart_routing = False
    
    # Place multiple orders
    orders = []
    for i in range(3):
        request = OrderRequest(
            symbol=f"COIN{i}/USDT",
            side="buy",
            order_type=OrderType.LIMIT,
            quantity=1.0,
            price=100.0 + i * 10,
            strategy_id="cancellation_demo"
        )
        order = order_manager.place_order(request)
        orders.append(order)
        print(f"Placed order {i+1}: {order.id}")
    
    # Cancel one order
    if orders:
        order_to_cancel = orders[0]
        success = order_manager.cancel_order(order_to_cancel.id, "demo_cancellation")
        print(f"Cancelled order {order_to_cancel.id}: {success}")
        print(f"Order state after cancellation: {order_to_cancel.state.value}")
    
    # Cancel all orders
    cancelled_count = order_manager.cancel_all_orders(reason="bulk_cancel_demo")
    print(f"Cancelled {cancelled_count} orders in bulk")
    
    return order_manager


def demo_smart_routing():
    """Demonstrate smart order routing."""
    print("\n=== Smart Order Routing Demo ===")
    
    config = OrderManagerConfig()
    order_manager = OrderManager(None, None, None, config)
    
    # Register multiple executors
    paper_executor = EnhancedPaperExecutor()
    order_manager.register_executor("paper", paper_executor)
    
    # Set preferred exchanges
    order_manager.smart_router.set_preferred_exchanges(["paper"])
    
    # Place order and see routing recommendation
    request = OrderRequest(
        symbol="BTC/USDT",
        side="buy",
        order_type=OrderType.MARKET,
        quantity=0.1,
        strategy_id="routing_demo"
    )
    
    recommendation = order_manager.smart_router.get_routing_recommendation(request)
    print("Routing recommendation:")
    for rec in recommendation['recommendations']:
        print(f"  Exchange: {rec['exchange']}, Score: {rec['score']:.3f}, Recommended: {rec['recommended']}")
    
    # Place order
    order = order_manager.place_order(request)
    print(f"Order routed to: {order.exchange}")
    
    return order_manager


def main():
    """Run all demos."""
    print("Order Management System Demo")
    print("=" * 50)
    
    try:
        # Run demos
        demo_basic_orders()
        demo_twap_orders()
        demo_vwap_orders()
        demo_order_cancellation()
        demo_smart_routing()
        
        print("\n" + "=" * 50)
        print("All demos completed successfully!")
        
    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
