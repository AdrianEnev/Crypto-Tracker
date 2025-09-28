"""
Demo: Enhanced Backtesting with Realistic Fees and Slippage

This demo showcases the new enhanced backtesting capabilities with:
- Realistic fee models per exchange
- Advanced slippage calculation
- Detailed cost analysis
- Performance comparison between simple and enhanced models
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

# Import the working simplified demo functions directly
import importlib.util
spec = importlib.util.spec_from_file_location("demo_simple_enhanced", str(Path(__file__).parent / "demo_simple_enhanced.py"))
demo_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo_module)

# Get the demo functions
demo_fee_models = demo_module.demo_fee_models
demo_slippage_models = demo_module.demo_slippage_models
demo_order_book_basics = demo_module.demo_order_book_basics
demo_integration = demo_module.demo_integration


def run_enhanced_backtest_demo():
    """Run the enhanced backtesting demo using the working components."""
    print("🚀 Enhanced Backtesting Demo")
    print("=" * 50)
    print("This demo showcases Phase 3 & 4 capabilities:")
    print("- Realistic fee modeling per exchange")
    print("- Advanced slippage calculation")
    print("- Order book simulation")
    print("- Integrated cost analysis")
    print("=" * 50)
    
    try:
        # Run all the working demos
        demo_fee_models()
        demo_slippage_models()
        demo_order_book_basics()
        demo_integration()
        
        print("\n🎉 ENHANCED BACKTESTING DEMO COMPLETED SUCCESSFULLY!")
        print("\nKey Insights:")
        print("- Enhanced backtesting provides realistic cost estimates")
        print("- Execution costs can significantly impact strategy performance")
        print("- Different exchanges have varying fee structures")
        print("- Order size affects slippage and market impact")
        print("- Order book simulation enables ultra-realistic execution modeling")
        
    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        run_enhanced_backtest_demo()
    except KeyboardInterrupt:
        print("\n\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
