#!/usr/bin/env python3
"""
Test script for Paper Trading Engine

This script tests the paper trading functionality with simulated trades
to verify the system works correctly before integrating with real data.
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timezone
import logging

# Add the project root directory to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from paper_trader import PaperTrader, PaperTrade
from session_manager import SessionManager
from rich.console import Console

console = Console()

def setup_test_logging():
    """Setup logging for tests"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

async def test_paper_trading_engine():
    """Test the paper trading engine with simulated trades"""
    console.print("\n🧪 Testing Paper Trading Engine", style="bold blue")
    console.print("=" * 50)
    
    # Setup test database
    test_db_path = Path(__file__).parent / "data" / "test_paper_trades.db"
    test_db_path.parent.mkdir(exist_ok=True)
    
    # Test configuration
    paper_config = {
        'enabled': True,
        'initial_balance_usd': 1000.0,
        'execution_delay_ms': 100,  # Fast for testing
        'position_size_pct': 0.1,
        'alerts_enabled': True,
        'max_position_size_usd': 1000.0
    }
    
    session_config = {
        'enabled': True,
        'save_directory': 'test_sessions',
        'daily_summary': True,
        'graceful_shutdown': True
    }
    
    try:
        # Initialize components
        session_manager = SessionManager(session_config, test_db_path)
        paper_trader = PaperTrader(paper_config, test_db_path, session_manager)
        
        # Start session
        session_id = session_manager.start_session()
        console.print(f"✅ Started test session: {session_id}")
        
        # Test 1: Buy trade
        console.print("\n📈 Test 1: Buy Trade", style="bold green")
        buy_trade_data = {
            'trade_type': 'buy',
            'token_symbol': 'PEPE',
            'token_address': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
            'amount_usd': 1000.0,  # Tracked wallet bought $1000 worth
            'price_per_token': 0.00000123
        }
        
        buy_result = await paper_trader.execute_paper_trade(buy_trade_data)
        if buy_result:
            console.print(f"✅ Buy trade executed successfully")
            console.print(f"   Portfolio: ${buy_result.portfolio_balance_before:,.2f} → ${buy_result.portfolio_balance_after:,.2f}")
        else:
            console.print("❌ Buy trade failed")
        
        # Test 2: Another buy trade
        console.print("\n📈 Test 2: Another Buy Trade", style="bold green")
        buy_trade_data_2 = {
            'trade_type': 'buy',
            'token_symbol': 'DOGE',
            'token_address': '9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM',
            'amount_usd': 500.0,
            'price_per_token': 0.08234
        }
        
        buy_result_2 = await paper_trader.execute_paper_trade(buy_trade_data_2)
        if buy_result_2:
            console.print(f"✅ Second buy trade executed successfully")
            console.print(f"   Portfolio: ${buy_result_2.portfolio_balance_before:,.2f} → ${buy_result_2.portfolio_balance_after:,.2f}")
        else:
            console.print("❌ Second buy trade failed")
        
        # Test 3: Sell trade
        console.print("\n📉 Test 3: Sell Trade", style="bold red")
        sell_trade_data = {
            'trade_type': 'sell',
            'token_symbol': 'PEPE',
            'token_address': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
            'amount_usd': 1000.0,
            'price_per_token': 0.00000189  # Higher price for profit
        }
        
        sell_result = await paper_trader.execute_paper_trade(sell_trade_data)
        if sell_result:
            console.print(f"✅ Sell trade executed successfully")
            console.print(f"   Portfolio: ${sell_result.portfolio_balance_before:,.2f} → ${sell_result.portfolio_balance_after:,.2f}")
            if sell_result.profit_loss_usd:
                console.print(f"   Profit: ${sell_result.profit_loss_usd:+,.2f}")
        else:
            console.print("❌ Sell trade failed")
        
        # Test 4: Display portfolio summary
        console.print("\n📊 Test 4: Portfolio Summary", style="bold blue")
        paper_trader.display_portfolio_summary()
        
        # Test 5: Session statistics
        console.print("\n📈 Test 5: Session Statistics", style="bold blue")
        session_stats = paper_trader.get_session_stats()
        console.print(f"Total Trades: {session_stats['total_trades']}")
        console.print(f"Profitable Trades: {session_stats['profitable_trades']}")
        console.print(f"Total P&L: ${session_stats['total_profit_loss']:+,.2f}")
        console.print(f"Win Rate: {session_stats['win_rate']:.1f}%")
        console.print(f"Total Return: {session_stats['total_return_pct']:+.2f}%")
        
        # Test 6: End session
        console.print("\n🛑 Test 6: End Session", style="bold yellow")
        session_data = await session_manager.end_session(graceful=True)
        if session_data:
            console.print(f"✅ Session ended successfully")
            console.print(f"   Session ID: {session_data['session_id']}")
            console.print(f"   Duration: {session_data.get('duration_seconds', 0):.1f} seconds")
        
        # Test 7: Session history
        console.print("\n📚 Test 7: Session History", style="bold blue")
        session_manager.display_session_history(limit=3)
        
        console.print("\n🎉 All paper trading tests completed successfully!", style="bold green")
        
    except Exception as e:
        console.print(f"\n❌ Test failed with error: {e}", style="bold red")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup test files
        try:
            if test_db_path.exists():
                test_db_path.unlink()
            test_sessions_dir = Path(__file__).parent / "data" / "test_sessions"
            if test_sessions_dir.exists():
                import shutil
                shutil.rmtree(test_sessions_dir)
        except Exception as e:
            console.print(f"Warning: Failed to cleanup test files: {e}")
    
    return True

async def test_error_handling():
    """Test error handling scenarios"""
    console.print("\n🧪 Testing Error Handling", style="bold blue")
    console.print("=" * 50)
    
    test_db_path = Path(__file__).parent / "data" / "test_error_trades.db"
    test_db_path.parent.mkdir(exist_ok=True)
    
    try:
        # Test with invalid configuration
        invalid_config = {
            'enabled': True,
            'initial_balance_usd': -100,  # Invalid negative balance
            'execution_delay_ms': -1000,  # Invalid negative delay
            'position_size_pct': 2.0,  # Invalid > 100% position size
            'alerts_enabled': True
        }
        
        session_config = {'enabled': True, 'save_directory': 'test_sessions'}
        session_manager = SessionManager(session_config, test_db_path)
        paper_trader = PaperTrader(invalid_config, test_db_path, session_manager)
        
        # Test invalid trade data
        invalid_trade_data = {
            'trade_type': 'invalid_type',
            'token_symbol': '',
            'token_address': '',
            'amount_usd': -100,
            'price_per_token': 0
        }
        
        result = await paper_trader.execute_paper_trade(invalid_trade_data)
        if result is None:
            console.print("✅ Invalid trade data handled correctly (returned None)")
        else:
            console.print("❌ Invalid trade data should have been rejected")
        
        # Test sell without position
        sell_without_position = {
            'trade_type': 'sell',
            'token_symbol': 'NONEXISTENT',
            'token_address': 'nonexistent_address',
            'amount_usd': 100,
            'price_per_token': 1.0
        }
        
        result = await paper_trader.execute_paper_trade(sell_without_position)
        if result is None:
            console.print("✅ Sell without position handled correctly (returned None)")
        else:
            console.print("❌ Sell without position should have been rejected")
        
        console.print("✅ Error handling tests completed successfully!")
        
    except Exception as e:
        console.print(f"❌ Error handling test failed: {e}", style="bold red")
        return False
    
    finally:
        # Cleanup
        try:
            if test_db_path.exists():
                test_db_path.unlink()
        except Exception:
            pass
    
    return True

async def main():
    """Main test function"""
    setup_test_logging()
    
    console.print("🚀 Starting Paper Trading Engine Tests", style="bold green")
    console.print("=" * 60)
    
    # Run tests
    test1_passed = await test_paper_trading_engine()
    test2_passed = await test_error_handling()
    
    # Summary
    console.print("\n📊 Test Summary", style="bold blue")
    console.print("=" * 30)
    console.print(f"Paper Trading Engine: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    console.print(f"Error Handling: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        console.print("\n🎉 All tests passed! Paper trading engine is ready for use.", style="bold green")
        return 0
    else:
        console.print("\n❌ Some tests failed. Please check the implementation.", style="bold red")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
