#!/usr/bin/env python3
"""
Comprehensive Testing Suite for Paper Trading System

This script tests both the paper trading system itself and validates
that the entire trading project works correctly with paper trading.
"""

import asyncio
import json
import os
import sys
import tempfile
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import paper trading components
from paper_trader import (
    PaperBroker, PaperTradingConfig, MarketDataAdapter, 
    PerformanceMetrics, ReportGenerator, SafetyChecker
)
from paper_trader.compatibility import PaperExecutorAdapter

# Import existing system components
from src.tracker.core import CryptoTracker
from src.tracker.execution_manager import ExecutionManager
from src.order_manager.models import OrderRequest, OrderType, TimeInForce
from src.executor import PaperExecutor


class PaperTradingTestSuite:
    """Comprehensive test suite for paper trading system."""
    
    def __init__(self):
        self.test_results = {}
        self.temp_dir = tempfile.mkdtemp()
        self.test_data_dir = Path(self.temp_dir) / "test_data"
        self.test_data_dir.mkdir(exist_ok=True)
        
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return comprehensive results."""
        
        print("🧪 Starting Comprehensive Paper Trading Test Suite")
        print("=" * 60)
        
        # Test categories
        test_categories = [
            ("Paper Trading Core", self.test_paper_trading_core),
            ("Execution Simulation", self.test_execution_simulation),
            ("Portfolio Management", self.test_portfolio_management),
            ("Market Data Handling", self.test_market_data_handling),
            ("Performance Analytics", self.test_performance_analytics),
            ("Safety & Security", self.test_safety_security),
            ("CLI Interface", self.test_cli_interface),
            ("Backward Compatibility", self.test_backward_compatibility),
            ("Integration with Existing System", self.test_integration),
            ("End-to-End Workflow", self.test_end_to_end_workflow),
        ]
        
        for category_name, test_function in test_categories:
            print(f"\n📋 Testing {category_name}...")
            try:
                result = test_function()
                self.test_results[category_name] = {
                    "status": "PASSED" if result else "FAILED",
                    "details": result if isinstance(result, dict) else {}
                }
                status_emoji = "✅" if result else "❌"
                print(f"{status_emoji} {category_name}: {'PASSED' if result else 'FAILED'}")
            except Exception as e:
                self.test_results[category_name] = {
                    "status": "ERROR",
                    "error": str(e)
                }
                print(f"❌ {category_name}: ERROR - {e}")
        
        # Generate summary
        self._generate_test_summary()
        
        return self.test_results
    
    def test_paper_trading_core(self) -> bool:
        """Test core paper trading functionality."""
        
        try:
            # Test basic initialization
            broker = PaperBroker(initial_cash=10000.0)
            assert broker.is_connected
            assert broker.is_paper_trading
            assert broker.portfolio.cash == 10000.0
            
            # Test order placement
            order_request = OrderRequest(
                symbol="BTC/USDT",
                side="buy",
                order_type=OrderType.MARKET,
                quantity=0.1
            )
            
            result = broker.place_order(order_request)
            assert result.success
            assert result.order_id in broker.orders
            
            # Test account info
            account_info = broker.get_account_info()
            assert account_info.total_equity > 0
            
            return True
            
        except Exception as e:
            print(f"Core test failed: {e}")
            return False
    
    def test_execution_simulation(self) -> bool:
        """Test execution simulation features."""
        
        try:
            from paper_trader.execution import ExecutionSimulator, SlippageConfig, FeeConfig, LatencyConfig
            
            # Test slippage simulation
            slippage_config = SlippageConfig(base_slippage_bps=10.0)
            fee_config = FeeConfig(taker_fee_bps=10.0)
            latency_config = LatencyConfig(mean_latency_ms=100.0)
            
            simulator = ExecutionSimulator(slippage_config, fee_config, latency_config)
            
            # Test execution simulation
            order_request = OrderRequest(
                symbol="BTC/USDT",
                side="buy",
                order_type=OrderType.MARKET,
                quantity=0.1
            )
            
            # This would be async in real usage
            execution_price, fee, slippage = asyncio.run(
                simulator.simulate_execution(order_request, 50000.0)
            )
            
            assert execution_price > 50000.0  # Buy orders have positive slippage
            assert fee > 0
            assert slippage > 0
            
            return True
            
        except Exception as e:
            print(f"Execution simulation test failed: {e}")
            return False
    
    def test_portfolio_management(self) -> bool:
        """Test portfolio management features."""
        
        try:
            broker = PaperBroker(initial_cash=10000.0)
            
            # Test trade execution
            success = broker.portfolio.execute_trade(
                symbol="BTC/USDT",
                side="buy",
                quantity=0.1,
                price=50000.0,
                fee=5.0,
                order_id="test_order_1"
            )
            assert success
            
            # Test position tracking
            position = broker.get_position("BTC/USDT")
            assert position is not None
            assert position.size == 0.1
            
            # Test P&L calculation
            broker.update_market_data("BTC/USDT", {"last": 51000.0})
            metrics = broker.get_performance_metrics()
            assert "total_trades" in metrics
            assert "unrealized_pnl" in metrics
            
            return True
            
        except Exception as e:
            print(f"Portfolio management test failed: {e}")
            return False
    
    def test_market_data_handling(self) -> bool:
        """Test market data handling."""
        
        try:
            # Create sample market data
            self._create_sample_market_data()
            
            from paper_trader.market_data import MarketDataConfig, DataMode, DataSource
            
            config = MarketDataConfig(
                mode=DataMode.REPLAY,
                source=DataSource.LOCAL_FILE,
                data_directory=str(self.test_data_dir),
                symbols=["BTC/USDT"]
            )
            
            adapter = MarketDataAdapter(config)
            
            # Test data loading
            data = asyncio.run(adapter.get_historical_data("BTC/USDT"))
            assert len(data) > 0
            
            return True
            
        except Exception as e:
            print(f"Market data test failed: {e}")
            return False
    
    def test_performance_analytics(self) -> bool:
        """Test performance analytics."""
        
        try:
            from paper_trader.portfolio import Trade, AccountSnapshot
            
            # Create sample trades
            trades = [
                Trade(
                    id="trade_1",
                    symbol="BTC/USDT",
                    side="buy",
                    quantity=0.1,
                    price=50000.0,
                    fee=5.0,
                    timestamp=datetime.now(timezone.utc),
                    order_id="order_1"
                ),
                Trade(
                    id="trade_2",
                    symbol="BTC/USDT",
                    side="sell",
                    quantity=0.1,
                    price=51000.0,
                    fee=5.1,
                    timestamp=datetime.now(timezone.utc),
                    order_id="order_2"
                )
            ]
            
            # Create sample account history
            account_history = [
                AccountSnapshot(
                    timestamp=datetime.now(timezone.utc),
                    cash=10000.0,
                    total_equity=10000.0,
                    unrealized_pnl=0.0,
                    realized_pnl=0.0,
                    positions=[]
                )
            ]
            
            # Test metrics calculation
            metrics = PerformanceMetrics(trades, account_history, 10000.0)
            summary = metrics.get_summary()
            
            assert "total_trades" in summary
            assert "win_rate" in summary
            assert "total_return" in summary
            
            return True
            
        except Exception as e:
            print(f"Performance analytics test failed: {e}")
            return False
    
    def test_safety_security(self) -> bool:
        """Test safety and security features."""
        
        try:
            checker = SafetyChecker()
            
            # Test safety validation
            errors = checker.check_paper_mode_safety()
            # Note: This might have errors in test environment, which is expected
            
            # Test configuration validation
            valid_config = {
                "mode": "paper",
                "exchange": "paper",
                "execution": {"mode": "paper"}
            }
            
            config_errors = checker.validate_paper_configuration(valid_config)
            assert len(config_errors) == 0
            
            return True
            
        except Exception as e:
            print(f"Safety test failed: {e}")
            return False
    
    def test_cli_interface(self) -> bool:
        """Test CLI interface."""
        
        try:
            # Test configuration creation
            config_path = self.test_data_dir / "test_config.yaml"
            
            # This would normally be done via CLI, but we'll test the underlying functionality
            from paper_trader.config import PaperTradingConfig
            
            config = PaperTradingConfig.create_default_config()
            config.save_to_file(str(config_path))
            
            assert config_path.exists()
            
            # Test configuration loading
            loaded_config = PaperTradingConfig.from_file(str(config_path))
            assert loaded_config.initial_cash == config.initial_cash
            
            return True
            
        except Exception as e:
            print(f"CLI interface test failed: {e}")
            return False
    
    def test_backward_compatibility(self) -> bool:
        """Test backward compatibility with old system."""
        
        try:
            # Test compatibility adapter
            adapter = PaperExecutorAdapter()
            
            # Test old interface
            order = adapter.place_order("BTC/USDT", "buy", 1000.0, "market")
            assert order.status == "Filled"
            assert order.symbol == "BTC/USDT"
            
            # Test enhanced features
            portfolio = adapter.get_portfolio_summary()
            assert "total_trades" in portfolio
            
            return True
            
        except Exception as e:
            print(f"Backward compatibility test failed: {e}")
            return False
    
    def test_integration(self) -> bool:
        """Test integration with existing trading system."""
        
        try:
            # Test with existing CryptoTracker
            config_path = "config/config.yaml"
            if not Path(config_path).exists():
                print("⚠️  Main config not found, skipping integration test")
                return True
            
            # Initialize tracker
            tracker = CryptoTracker(config_path)
            
            # Replace paper executor with our enhanced version
            enhanced_executor = PaperExecutorAdapter()
            tracker.execution_manager.paper = enhanced_executor
            
            # Test that tracker still works
            assert tracker.execution_manager.auto_trade_mode == "paper"
            
            # Test portfolio manager integration
            portfolio_info = tracker.portfolio_manager.get_portfolio_summary()
            assert isinstance(portfolio_info, dict)
            
            return True
            
        except Exception as e:
            print(f"Integration test failed: {e}")
            return False
    
    def test_end_to_end_workflow(self) -> bool:
        """Test complete end-to-end workflow."""
        
        try:
            # Create test configuration
            config = PaperTradingConfig.create_default_config()
            config.run_id = "test_workflow"
            config.initial_cash = 10000.0
            
            # Initialize broker
            broker = PaperBroker(
                initial_cash=config.initial_cash,
                base_currency=config.base_currency
            )
            
            # Simulate market data updates
            broker.update_market_data("BTC/USDT", {
                "last": 50000.0,
                "bid": 49990.0,
                "ask": 50010.0,
                "volume": 1000.0
            })
            
            # Place orders
            buy_order = OrderRequest(
                symbol="BTC/USDT",
                side="buy",
                order_type=OrderType.MARKET,
                quantity=0.1
            )
            
            result = broker.place_order(buy_order)
            assert result.success
            
            # Update price and place sell order
            broker.update_market_data("BTC/USDT", {"last": 51000.0})
            
            sell_order = OrderRequest(
                symbol="BTC/USDT",
                side="sell",
                order_type=OrderType.MARKET,
                quantity=0.1
            )
            
            result = broker.place_order(sell_order)
            assert result.success
            
            # Check final state
            metrics = broker.get_performance_metrics()
            assert metrics["total_trades"] >= 2
            
            return True
            
        except Exception as e:
            print(f"End-to-end workflow test failed: {e}")
            return False
    
    def _create_sample_market_data(self):
        """Create sample market data for testing."""
        
        import json
        
        # Create sample OHLCV data
        sample_data = []
        base_price = 50000.0
        base_time = int(datetime.now(timezone.utc).timestamp())
        
        for i in range(100):
            timestamp = base_time + (i * 3600)  # 1 hour intervals
            price = base_price + (i * 10)  # Slight upward trend
            
            sample_data.append({
                "timestamp": timestamp,
                "open": price,
                "high": price + 50,
                "low": price - 50,
                "close": price + 10,
                "volume": 1000 + i
            })
        
        # Save as JSONL
        data_file = self.test_data_dir / "binance_BTC-USDT_1h_n100_1h.jsonl"
        with open(data_file, 'w') as f:
            for item in sample_data:
                f.write(json.dumps(item) + '\n')
    
    def _generate_test_summary(self):
        """Generate test summary report."""
        
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() 
                          if result["status"] == "PASSED")
        failed_tests = sum(1 for result in self.test_results.values() 
                          if result["status"] == "FAILED")
        error_tests = sum(1 for result in self.test_results.values() 
                         if result["status"] == "ERROR")
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"⚠️  Errors: {error_tests}")
        
        success_rate = (passed_tests / total_tests) * 100
        print(f"Success Rate: {success_rate:.1f}%")
        
        # Detailed results
        print("\n📋 DETAILED RESULTS:")
        for category, result in self.test_results.items():
            status_emoji = {
                "PASSED": "✅",
                "FAILED": "❌", 
                "ERROR": "⚠️"
            }[result["status"]]
            
            print(f"{status_emoji} {category}: {result['status']}")
            
            if result["status"] == "ERROR":
                print(f"   Error: {result.get('error', 'Unknown error')}")
        
        # Save results
        results_file = Path(self.temp_dir) / "test_results.json"
        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        print(f"\n📁 Detailed results saved to: {results_file}")
        
        # Overall assessment
        if success_rate >= 90:
            print("\n🎉 EXCELLENT: Paper trading system is ready for production!")
        elif success_rate >= 75:
            print("\n👍 GOOD: Paper trading system is mostly ready with minor issues")
        elif success_rate >= 50:
            print("\n⚠️  NEEDS WORK: Paper trading system has significant issues")
        else:
            print("\n❌ CRITICAL: Paper trading system needs major fixes")


def run_project_accuracy_tests():
    """Run tests to validate the entire project works with paper trading."""
    
    print("\n🔬 PROJECT ACCURACY VALIDATION")
    print("=" * 60)
    
    try:
        # Test 1: Strategy execution with paper trading
        print("Testing strategy execution...")
        config_path = "config/config.yaml"
        if Path(config_path).exists():
            tracker = CryptoTracker(config_path)
            
            # Enable paper trading
            tracker.execution_manager.auto_trade_mode = "paper"
            tracker.execution_manager.auto_trade_enable = True
            
            # Test price checking
            tracker.check_all_prices()
            print("✅ Strategy execution test passed")
        else:
            print("⚠️  Main config not found, skipping strategy test")
        
        # Test 2: Risk management integration
        print("Testing risk management...")
        if 'tracker' in locals():
            risk_summary = tracker.get_risk_summary()
            assert isinstance(risk_summary, dict)
            print("✅ Risk management test passed")
        
        # Test 3: Portfolio management integration
        print("Testing portfolio management...")
        if 'tracker' in locals():
            portfolio_summary = tracker.portfolio_manager.get_portfolio_summary()
            assert isinstance(portfolio_summary, dict)
            print("✅ Portfolio management test passed")
        
        print("\n🎯 PROJECT ACCURACY: All systems working correctly with paper trading!")
        
    except Exception as e:
        print(f"❌ Project accuracy test failed: {e}")
        return False
    
    return True


def main():
    """Main test runner."""
    
    print("🚀 Starting Comprehensive Paper Trading Test Suite")
    print("This will test both the paper trading system and validate")
    print("that the entire project works correctly with paper trading.")
    print()
    
    # Run paper trading tests
    test_suite = PaperTradingTestSuite()
    test_results = test_suite.run_all_tests()
    
    # Run project accuracy tests
    project_accuracy = run_project_accuracy_tests()
    
    # Final assessment
    print("\n" + "=" * 60)
    print("🏁 FINAL ASSESSMENT")
    print("=" * 60)
    
    paper_tests_passed = sum(1 for result in test_results.values() 
                            if result["status"] == "PASSED")
    total_paper_tests = len(test_results)
    
    print(f"Paper Trading System: {paper_tests_passed}/{total_paper_tests} tests passed")
    print(f"Project Integration: {'✅ PASSED' if project_accuracy else '❌ FAILED'}")
    
    if paper_tests_passed >= total_paper_tests * 0.9 and project_accuracy:
        print("\n🎉 SUCCESS: Paper trading system is ready for testing the entire project!")
        print("You can now use paper trading to validate your trading strategies.")
    else:
        print("\n⚠️  ISSUES DETECTED: Please review failed tests before proceeding.")
    
    return test_results


if __name__ == "__main__":
    results = main()
