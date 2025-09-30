#!/usr/bin/env python3
"""
Quick Paper Trading Test - Fixed Version

A simple script to quickly test if the paper trading system is working
and can be used to validate the entire project.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

def check_module_structure():
    """Check if the paper_trader module exists and has the right structure."""
    
    print("🔍 Checking module structure...")
    
    # Check if paper_trader directory exists
    paper_trader_dir = project_root / "paper_trader"
    if not paper_trader_dir.exists():
        print(f"❌ paper_trader directory not found at: {paper_trader_dir}")
        return False
    
    print(f"✅ paper_trader directory found at: {paper_trader_dir}")
    
    # Check for required files
    required_files = [
        "__init__.py",
        "broker.py", 
        "execution.py",
        "portfolio.py",
        "market_data.py",
        "persistence.py",
        "metrics.py",
        "config.py",
        "safety.py",
        "compatibility.py"
    ]
    
    missing_files = []
    for file in required_files:
        file_path = paper_trader_dir / file
        if not file_path.exists():
            missing_files.append(file)
        else:
            print(f"✅ {file} found")
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    
    # Check if src directory exists
    src_dir = project_root / "src"
    if not src_dir.exists():
        print(f"❌ src directory not found at: {src_dir}")
        return False
    
    print(f"✅ src directory found at: {src_dir}")
    
    return True

def quick_test():
    """Run a quick test of the paper trading system."""
    
    print("🚀 Quick Paper Trading Test")
    print("=" * 40)
    
    try:
        # Test 1: Check module structure first
        print("1. Checking module structure...")
        if not check_module_structure():
            print("❌ Module structure check failed")
            return False
        print("   ✅ Module structure OK")
        
        # Test 2: Test imports
        print("2. Testing imports...")
        try:
            from paper_trader.paper_broker import PaperBroker
            from paper_trader.config import PaperTradingConfig
            from paper_trader.compatibility import PaperExecutorAdapter
            print("   ✅ Paper trading imports successful")
        except ImportError as e:
            print(f"   ❌ Import failed: {e}")
            return False
        
        # Test 3: Basic paper broker functionality
        print("3. Testing paper broker...")
        broker = PaperBroker(initial_cash=10000.0)
        assert broker.is_connected
        assert broker.is_paper_trading
        print("   ✅ Paper broker initialized")
        
        # Test 4: Order placement
        print("4. Testing order placement...")
        try:
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
        except Exception as e:
            print(f"   ❌ Order placement failed: {e}")
            return False
        
        # Test 5: Portfolio tracking
        print("5. Testing portfolio tracking...")
        metrics = broker.get_performance_metrics()
        assert "total_trades" in metrics
        print("   ✅ Portfolio tracking working")
        
        # Test 6: Backward compatibility
        print("6. Testing backward compatibility...")
        adapter = PaperExecutorAdapter()
        order = adapter.place_order("BTC/USDT", "buy", 1000.0, "market")
        assert order.status == "Filled"
        print("   ✅ Backward compatibility working")
        
        return True
        
    except Exception as e:
        print(f"❌ Quick test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_strategy_execution():
    """Test that strategies can execute with paper trading."""
    
    print("\n🔬 Testing Strategy Execution")
    print("=" * 40)
    
    try:
        # Check if main config exists
        config_path = project_root / "config" / "config.yaml"
        if not config_path.exists():
            print("⚠️  Main config not found, creating minimal test...")
            
            # Create a minimal test
            from paper_trader.compatibility import PaperExecutorAdapter
            adapter = PaperExecutorAdapter()
            
            # Test basic strategy-like behavior
            order = adapter.place_order("BTC/USDT", "buy", 1000.0, "market")
            assert order.status == "Filled"
            
            print("✅ Basic strategy execution test passed")
            return True
        
        # Test with full system
        from src.tracker.core import CryptoTracker
        from paper_trader.compatibility import PaperExecutorAdapter
        
        tracker = CryptoTracker(str(config_path))
        
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
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test runner."""
    
    print("🧪 Paper Trading Quick Test - Fixed Version")
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
        print("\nTroubleshooting:")
        print("1. Make sure you're running from the project root directory")
        print("2. Check that all paper_trader files exist")
        print("3. Verify Python path includes the project root")
        return 1


if __name__ == "__main__":
    sys.exit(main())
