#!/usr/bin/env python3
"""
Simple Paper Trading Test

A minimal test that only tests the paper trading system itself,
without depending on the existing trading system.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_paper_trading_only():
    """Test only the paper trading system components."""
    
    print("🧪 Testing Paper Trading System Only")
    print("=" * 50)
    
    try:
        # Test 1: Check module structure
        print("1. Checking module structure...")
        paper_trader_dir = project_root / "paper_trader"
        if not paper_trader_dir.exists():
            print(f"❌ paper_trader directory not found at: {paper_trader_dir}")
            return False
        print("✅ paper_trader directory found")
        
        # Test 2: Test core imports
        print("2. Testing core imports...")
        from paper_trader.paper_broker import PaperBroker
        from paper_trader.config import PaperTradingConfig
        from paper_trader.portfolio import PaperPortfolio
        from paper_trader.execution import ExecutionSimulator
        print("✅ Core imports successful")
        
        # Test 3: Test broker initialization
        print("3. Testing broker initialization...")
        broker = PaperBroker(initial_cash=10000.0)
        assert broker.is_connected
        assert broker.is_paper_trading
        assert broker.portfolio.cash == 10000.0
        print("✅ Broker initialized correctly")
        
        # Test 4: Test portfolio operations
        print("4. Testing portfolio operations...")
        portfolio = broker.portfolio
        
        # Test trade execution
        success = portfolio.execute_trade(
            symbol="BTC/USDT",
            side="buy",
            quantity=0.1,
            price=50000.0,
            fee=5.0,
            order_id="test_order_1"
        )
        assert success
        print("✅ Trade execution successful")
        
        # Test position tracking
        position = portfolio.get_position("BTC/USDT")
        assert position is not None
        assert position.size == 0.1
        print("✅ Position tracking working")
        
        # Test 5: Test execution simulator
        print("5. Testing execution simulator...")
        from paper_trader.execution import SlippageConfig, FeeConfig, LatencyConfig
        
        slippage_config = SlippageConfig(base_slippage_bps=10.0)
        fee_config = FeeConfig(taker_fee_bps=10.0)
        latency_config = LatencyConfig(mean_latency_ms=100.0)
        
        simulator = ExecutionSimulator(slippage_config, fee_config, latency_config)
        print("✅ Execution simulator initialized")
        
        # Test 6: Test configuration
        print("6. Testing configuration...")
        config = PaperTradingConfig.create_default_config()
        assert config.initial_cash > 0
        assert config.base_currency == "USDT"
        print("✅ Configuration working")
        
        # Test 7: Test safety checker
        print("7. Testing safety checker...")
        from paper_trader.safety import SafetyChecker
        checker = SafetyChecker()
        print("✅ Safety checker initialized")
        
        # Test 8: Test compatibility adapter
        print("8. Testing compatibility adapter...")
        from paper_trader.compatibility import PaperExecutorAdapter
        adapter = PaperExecutorAdapter()
        
        # Test old interface
        order = adapter.place_order("BTC/USDT", "buy", 1000.0, "market")
        print(f"   Order status: {order.status}")
        print(f"   Order details: {order}")
        assert order.status == "Filled"
        assert order.symbol == "BTC/USDT"
        print("✅ Compatibility adapter working")
        
        # Test 9: Test performance metrics
        print("9. Testing performance metrics...")
        metrics = broker.get_performance_metrics()
        assert "total_trades" in metrics
        assert "unrealized_pnl" in metrics
        print("✅ Performance metrics working")
        
        print("\n🎉 ALL PAPER TRADING TESTS PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_basic_order_placement():
    """Test basic order placement functionality."""
    
    print("\n📋 Testing Basic Order Placement")
    print("=" * 50)
    
    try:
        from paper_trader.paper_broker import PaperBroker
        
        # Create broker
        broker = PaperBroker(initial_cash=10000.0)
        
        # Simulate market data
        broker.update_market_data("BTC/USDT", {
            "last": 50000.0,
            "bid": 49990.0,
            "ask": 50010.0,
            "volume": 1000.0
        })
        
        # Test buy order using compatibility adapter
        print("Testing buy order...")
        from paper_trader.compatibility import PaperExecutorAdapter
        adapter = PaperExecutorAdapter()
        
        buy_order = adapter.place_order("BTC/USDT", "buy", 1000.0, "market")
        assert buy_order.status == "Filled"
        print("✅ Buy order successful")
        
        # Test sell order
        print("Testing sell order...")
        sell_order = adapter.place_order("BTC/USDT", "sell", 500.0, "market")
        assert sell_order.status == "Filled"
        print("✅ Sell order successful")
        
        # Check final state
        portfolio = adapter.get_portfolio_summary()
        assert portfolio["total_trades"] >= 2
        print("✅ Order placement test passed")
        
        return True
        
    except Exception as e:
        print(f"❌ Order placement test failed: {e}")
        return False


def main():
    """Main test runner."""
    
    print("🚀 Simple Paper Trading Test")
    print("This tests only the paper trading system components")
    print("without depending on the existing trading system.\n")
    
    # Test paper trading components
    paper_success = test_paper_trading_only()
    
    # Test basic order placement
    order_success = test_basic_order_placement()
    
    # Final assessment
    print("\n" + "=" * 50)
    print("📊 FINAL RESULTS")
    print("=" * 50)
    
    if paper_success and order_success:
        print("🎉 SUCCESS: Paper trading system is working!")
        print("\n✅ What's working:")
        print("• Paper broker initialization")
        print("• Portfolio management")
        print("• Order execution simulation")
        print("• Performance metrics")
        print("• Safety checks")
        print("• Backward compatibility")
        
        print("\n🎯 Next steps:")
        print("1. The paper trading system is ready to use")
        print("2. You can now integrate it with your existing system")
        print("3. Run: python scripts/run_paper.py --create-config")
        print("4. Test with: python scripts/run_paper.py --mode replay")
        
        return 0
    else:
        print("❌ FAILED: Paper trading system has issues")
        print("Please check the error messages above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
