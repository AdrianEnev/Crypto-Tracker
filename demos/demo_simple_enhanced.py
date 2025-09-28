"""
Simple Enhanced Backtesting Demo

A simplified demo that showcases the new fee and slippage models
without complex imports.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

def demo_fee_models():
    """Demo the fee calculation models."""
    print("💰 FEE MODELS DEMO")
    print("=" * 50)
    
    try:
        from fees import FeeCalculator, FeeCalculationMode, OrderFeeContext
        
        # Test different fee calculation modes
        print("Testing fee calculation modes...")
        
        # Zero fees
        calc_zero = FeeCalculator(FeeCalculationMode.ZERO)
        context = OrderFeeContext(
            order_value_usd=10000.0,
            order_quantity=0.2,
            order_price=50000.0,
            side="buy",
            order_type="market",
            exchange="binance",
            symbol="BTC/USDT"  # Add symbol
        )
        
        fees_zero = calc_zero.calculate_fees(context)
        print(f"Zero fees: ${fees_zero.total_fees_usd:.2f}")
        
        # Simplified fees
        calc_simple = FeeCalculator(FeeCalculationMode.SIMPLIFIED)
        fees_simple = calc_simple.calculate_fees(context)
        print(f"Simplified fees: ${fees_simple.total_fees_usd:.2f}")
        
        # Realistic fees
        calc_realistic = FeeCalculator(FeeCalculationMode.REALISTIC)
        fees_realistic = calc_realistic.calculate_fees(context)
        print(f"Realistic fees: ${fees_realistic.total_fees_usd:.2f}")
        print(f"Fee type: {fees_realistic.fee_type_used.value}")
        print(f"Volume tier: {fees_realistic.volume_tier}")
        
        # Test exchange comparison
        print(f"\nExchange fee comparison for $10,000 BTC trade:")
        exchanges = ["binance", "coinbase", "bybit", "kraken", "okx"]
        
        for exchange in exchanges:
            try:
                context.exchange = exchange
                fees = calc_realistic.calculate_fees(context)
                print(f"{exchange.capitalize():<10}: ${fees.trading_fee_usd:>6.2f} ({fees.taker_bps:>4.1f} bps)")
            except Exception as e:
                print(f"{exchange.capitalize():<10}: Error - {str(e)[:30]}")
        
        print("✅ Fee models demo completed successfully!")
        
    except Exception as e:
        print(f"❌ Fee models demo failed: {e}")
        import traceback
        traceback.print_exc()


def demo_slippage_models():
    """Demo the slippage calculation models."""
    print("\n📊 SLIPPAGE MODELS DEMO")
    print("=" * 50)
    
    try:
        from slippage import VolumeBasedSlippage, SlippageContext, SlippageType
        
        # Test volume-based slippage
        slippage_calc = VolumeBasedSlippage()
        
        # Small order
        small_context = SlippageContext(
            symbol="BTC/USDT",
            side="buy",
            quantity=0.1,  # Small order
            order_type="market",
            current_price=50000.0,
            volume_24h=10000000.0,  # $10M daily volume
            volatility=0.02  # 2% volatility
        )
        
        small_result = slippage_calc.calculate_slippage(small_context)
        print(f"Small order (0.1 BTC):")
        print(f"  Slippage: {small_result.slippage_bps:.2f} bps")
        print(f"  Effective price: ${small_result.effective_price:.2f}")
        print(f"  Market condition: {small_result.market_condition.value}")
        
        # Large order
        large_context = SlippageContext(
            symbol="BTC/USDT",
            side="buy",
            quantity=10.0,  # Large order
            order_type="market",
            current_price=50000.0,
            volume_24h=10000000.0,  # $10M daily volume
            volatility=0.02  # 2% volatility
        )
        
        large_result = slippage_calc.calculate_slippage(large_context)
        print(f"\nLarge order (10 BTC):")
        print(f"  Slippage: {large_result.slippage_bps:.2f} bps")
        print(f"  Effective price: ${large_result.effective_price:.2f}")
        print(f"  Market condition: {large_result.market_condition.value}")
        
        # Compare slippage
        slippage_increase = large_result.slippage_bps - small_result.slippage_bps
        print(f"\nSlippage increase: {slippage_increase:.2f} bps")
        print(f"Cost impact: ${(slippage_increase / 10000) * 50000 * 10:.2f}")
        
        print("✅ Slippage models demo completed successfully!")
        
    except Exception as e:
        print(f"❌ Slippage models demo failed: {e}")
        import traceback
        traceback.print_exc()


def demo_order_book_basics():
    """Demo basic order book functionality."""
    print("\n📈 ORDER BOOK BASICS DEMO")
    print("=" * 50)
    
    try:
        from orderbook import OrderBookSnapshot
        
        # Create sample order book
        bids = [
            (50000.0, 1.5),   # 1.5 BTC at $50,000
            (49999.5, 2.0),   # 2.0 BTC at $49,999.5
            (49999.0, 1.8),   # 1.8 BTC at $49,999
        ]
        
        asks = [
            (50001.0, 1.2),   # 1.2 BTC at $50,001
            (50001.5, 1.8),   # 1.8 BTC at $50,001.5
            (50002.0, 2.3),   # 2.3 BTC at $50,002
        ]
        
        snapshot = OrderBookSnapshot(
            symbol="BTC/USDT",
            timestamp=None,  # Will use current time
            bids=bids,
            asks=asks,
            last_trade_price=50000.5
        )
        
        print(f"Order book for {snapshot.symbol}:")
        print(f"  Best Bid: ${snapshot.best_bid:,.2f}")
        print(f"  Best Ask: ${snapshot.best_ask:,.2f}")
        print(f"  Spread: ${snapshot.spread:,.2f} ({snapshot.spread_bps:.2f} bps)")
        print(f"  Mid Price: ${snapshot.mid_price:,.2f}")
        print(f"  Bid Levels: {len(snapshot.bids.levels)}")
        print(f"  Ask Levels: {len(snapshot.asks.levels)}")
        
        # Test order book validation
        print(f"  Valid Order Book: {snapshot.is_valid()}")
        
        # Test market depth
        depth = snapshot.get_market_depth(levels=3)
        print(f"\nMarket Depth (Top 3 levels):")
        print("  Bids:")
        for price, qty in depth["bids"]:
            print(f"    ${price:,.2f}: {qty:.1f} BTC")
        print("  Asks:")
        for price, qty in depth["asks"]:
            print(f"    ${price:,.2f}: {qty:.1f} BTC")
        
        print("✅ Order book basics demo completed successfully!")
        
    except Exception as e:
        print(f"❌ Order book basics demo failed: {e}")
        import traceback
        traceback.print_exc()


def demo_integration():
    """Demo integration between fee and slippage models."""
    print("\n🔗 INTEGRATION DEMO")
    print("=" * 50)
    
    try:
        from fees import FeeCalculator, FeeCalculationMode, OrderFeeContext
        from slippage import VolumeBasedSlippage, SlippageContext
        
        # Create calculators
        fee_calc = FeeCalculator(FeeCalculationMode.REALISTIC)
        slippage_calc = VolumeBasedSlippage()
        
        # Simulate a trade
        trade_value = 10000.0  # $10,000 trade
        quantity = 0.2  # 0.2 BTC
        price = 50000.0  # $50,000 per BTC
        
        print(f"Simulating trade: {quantity} BTC at ${price:,.0f}")
        print(f"Trade value: ${trade_value:,.0f}")
        
        # Calculate fees
        fee_context = OrderFeeContext(
            order_value_usd=trade_value,
            order_quantity=quantity,
            order_price=price,
            side="buy",
            order_type="market",
            exchange="binance",
            symbol="BTC/USDT",  # Add symbol
            monthly_volume_usd=50000.0
        )
        
        fees = fee_calc.calculate_fees(fee_context)
        
        # Calculate slippage
        slippage_context = SlippageContext(
            symbol="BTC/USDT",
            side="buy",
            quantity=quantity,
            order_type="market",
            current_price=price,
            volume_24h=10000000.0,  # $10M daily volume
            volatility=0.02  # 2% volatility
        )
        
        slippage = slippage_calc.calculate_slippage(slippage_context)
        
        # Calculate total costs
        slippage_cost = (slippage.slippage_bps / 10000.0) * trade_value
        total_costs = fees.total_fees_usd + slippage_cost
        
        print(f"\nCost Breakdown:")
        print(f"  Trading Fees: ${fees.trading_fee_usd:.2f} ({fees.trading_fee_usd/trade_value*10000:.1f} bps)")
        print(f"  Slippage Cost: ${slippage_cost:.2f} ({slippage.slippage_bps:.1f} bps)")
        print(f"  Total Costs: ${total_costs:.2f} ({total_costs/trade_value*10000:.1f} bps)")
        
        # Calculate effective price
        effective_price = slippage.effective_price
        total_cost_per_unit = total_costs / quantity
        
        print(f"\nExecution Results:")
        print(f"  Effective Price: ${effective_price:.2f}")
        print(f"  Cost per BTC: ${total_cost_per_unit:.2f}")
        print(f"  Total Cost Impact: {(total_costs/trade_value)*100:.3f}%")
        
        print("✅ Integration demo completed successfully!")
        
    except Exception as e:
        print(f"❌ Integration demo failed: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all demos."""
    print("🎯 ENHANCED BACKTESTING FEATURES DEMO")
    print("=" * 60)
    print("This demo showcases the new Phase 3 & 4 capabilities:")
    print("- Realistic fee modeling per exchange")
    print("- Advanced slippage calculation")
    print("- Order book simulation")
    print("- Integrated cost analysis")
    print("=" * 60)
    
    try:
        demo_fee_models()
        demo_slippage_models()
        demo_order_book_basics()
        demo_integration()
        
        print("\n🎉 ALL DEMOS COMPLETED SUCCESSFULLY!")
        print("\nKey Insights:")
        print("- Enhanced backtesting provides realistic cost estimates")
        print("- Execution costs can significantly impact strategy performance")
        print("- Different exchanges have varying fee structures")
        print("- Order size affects slippage and market impact")
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
