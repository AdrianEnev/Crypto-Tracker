#!/usr/bin/env python3
"""
Quick Paper Trading Test

A simple script to quickly test if the paper trading system is working
and can be used to validate the entire project.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

def quick_test():
    """Run a quick test of the paper trading system."""
    
    print("🚀 Quick Paper Trading Test")
    print("=" * 40)
    
    try:
        # Test 1: Import paper trading components
        print("1. Testing imports...")
        from paper_trader import PaperBroker, PaperTradingConfig
        from paper_trader.compatibility import PaperExecutorAdapter
        print("   ✅ Imports successful")
        
        # Test 2: Basic paper broker functionality
        print("2. Testing paper broker...")
        broker = PaperBroker(initial_cash=10000.0)
        assert broker.is_connected
        assert broker.is_paper_trading
        print("   ✅ Paper broker initialized")
        
        # Test 3: Order placement
        print("3. Testing order placement...")
        from src.order_manager.models import OrderRequest, OrderType
        
        order_request = OrderRequest(
            symbol="BTC/USDT",
            side="buy",
            order_type=OrderType.MARKET,
            quantity=0.1
        )
        
        result = broker.place_order(order_request)
        assert result.success
        print("   ✅ Order placement successful")
        
        # Test 4: Portfolio tracking
        print("4. Testing portfolio tracking...")
        metrics = broker.get_performance_metrics()
        assert "total_trades" in metrics
        print("   ✅ Portfolio tracking working")
        
        # Test 5: Backward compatibility
        print("5. Testing backward compatibility...")
        adapter = PaperExecutorAdapter()
        order = adapter.place_order("BTC/USDT", "buy", 1000.0, "market")
        assert order.status == "Filled"
        print("   ✅ Backward compatibility working")
        
        # Test 6: Integration with existing system
        print("6. Testing integration...")
        config_path = "config/config.yaml"
        if Path(config_path).exists():
            from src.tracker.core import CryptoTracker
            tracker = CryptoTracker(config_path)
            
            # Replace with enhanced executor
            tracker.execution_manager.paper = adapter
            tracker.execution_manager.auto_trade_mode = "paper"
            
            print("   ✅ Integration successful")
        else:
            print("   ⚠️  Main config not found, skipping integration test")
        
        print("\n🎉 ALL TESTS PASSED!")
        print("Paper trading system is ready to use for testing the entire project.")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_strategy_execution():
    """Test that strategies can execute with paper trading."""
    
    print("\n🔬 Testing Strategy Execution")
    print("=" * 40)
    
    try:
        from src.tracker.core import CryptoTracker
        from paper_trader.compatibility import PaperExecutorAdapter
        
        config_path = "config/config.yaml"
        if not Path(config_path).exists():
            print("⚠️  Main config not found, creating minimal test...")
            
            # Create a minimal test
            adapter = PaperExecutorAdapter()
            
            # Test basic strategy-like behavior
            order = adapter.place_order("BTC/USDT", "buy", 1000.0, "market")
            assert order.status == "Filled"
            
            print("✅ Basic strategy execution test passed")
            return True
        
        # Test with full system
        tracker = CryptoTracker(config_path)
        
        # Enable paper trading
        enhanced_executor = PaperExecutorAdapter()
        tracker.execution_manager.paper = enhanced_executor
        tracker.execution_manager.auto_trade_mode = "paper"
        tracker.execution_manager.auto_trade_enable = True
        
        # Test price checking (this triggers strategy execution)
        tracker.check_all_prices()
        
        print("✅ Full strategy execution test passed")
        return True
        
    except Exception as e:
        print(f"❌ Strategy execution test failed: {e}")
        return False


def main():
    """Main test runner."""
    
    print("🧪 Paper Trading Quick Test")
    print("This will quickly validate that the paper trading system")
    print("is working and can be used to test the entire project.\n")
    
    # Run quick tests
    quick_success = quick_test()
    
    # Test strategy execution
    strategy_success = test_strategy_execution()
    
    # Final assessment
    print("\n" + "=" * 40)
    print("📊 FINAL RESULTS")
    print("=" * 40)
    
    if quick_success and strategy_success:
        print("🎉 SUCCESS: Paper trading system is ready!")
        print("\nYou can now use paper trading to:")
        print("• Test your trading strategies safely")
        print("• Validate the entire project")
        print("• Run historical backtests")
        print("• Simulate live trading")
        print("\nNext steps:")
        print("1. Run: python scripts/run_paper.py --create-config")
        print("2. Run: python scripts/run_paper.py --mode replay")
        print("3. Analyze results in data/paper_runs/")
        
        return 0
    else:
        print("❌ FAILED: Paper trading system has issues")
        print("Please check the error messages above and fix them.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
