#!/usr/bin/env python3
"""
Quick Test for 24/7 Paper Trading System

Tests the system for 5 minutes to verify everything works before starting 2-week run.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from scripts.paper_trading_24_7 import PaperTrading24_7


async def quick_test():
    """Run a quick 5-minute test of the 24/7 system."""
    print("🧪 Starting 5-minute quick test of 24/7 paper trading system")
    print("=" * 60)
    
    # Initialize the system
    paper_system = PaperTrading24_7("config/paper_24_7.yaml", 50000)
    
    # Initialize
    if not await paper_system.initialize():
        print("❌ Initialization failed")
        return False
    
    print("✅ System initialized successfully")
    print("🚀 Starting 5-minute test...")
    
    # Run for 5 minutes
    start_time = time.time()
    test_duration = 300  # 5 minutes
    
    try:
        while time.time() - start_time < test_duration:
            # Update mock prices
            paper_system._update_mock_prices()
            
            # Let the tracker make decisions
            paper_system.tracker.check_all_prices()
            
            # Wait 30 seconds between checks
            await asyncio.sleep(30)
            
            # Show progress
            elapsed = time.time() - start_time
            remaining = test_duration - elapsed
            print(f"⏱️  Test progress: {elapsed:.0f}s elapsed, {remaining:.0f}s remaining")
    
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    
    # Show final results
    print("\n" + "=" * 60)
    print("📊 QUICK TEST RESULTS")
    print("=" * 60)
    
    summary = paper_system.simulator.get_performance_summary()
    
    print(f"✅ System Status: {'WORKING' if summary['total_trades'] >= 0 else 'ERROR'}")
    print(f"💰 Portfolio Value: ${summary['current_value']:,.2f}")
    print(f"🔄 Total Trades: {summary['total_trades']}")
    print(f"⏱️  Runtime: {summary['runtime_hours']:.2f} hours")
    print(f"📦 Positions: {len(summary['positions'])}")
    
    if summary['total_trades'] > 0:
        print(f"🎯 Win Rate: {summary['win_rate_pct']:.1f}%")
        print(f"💵 Net P&L: ${summary['total_pnl']:,.2f}")
    
    print("=" * 60)
    
    # Recommendations
    if summary['total_trades'] == 0:
        print("⚠️  WARNING: No trades executed during test")
        print("   This may indicate strategies are too conservative")
        print("   Consider adjusting config before 2-week run")
    else:
        print("✅ SUCCESS: System is working correctly")
        print("   Ready for 2-week test!")
    
    return summary['total_trades'] > 0


def main():
    """Main entry point."""
    print("🧪 Quick Test for 24/7 Paper Trading System")
    print("This will test the system for 5 minutes to verify it works")
    print("Press Ctrl+C to stop early")
    print()
    
    try:
        result = asyncio.run(quick_test())
        
        if result:
            print("\n🎉 Test completed successfully!")
            print("You can now start your 2-week test with confidence:")
            print("   ./scripts/paper_trading_24_7.sh start")
        else:
            print("\n⚠️  Test completed with warnings")
            print("Review the results and consider adjusting config")
            
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
