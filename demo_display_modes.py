#!/usr/bin/env python3
"""
Demo script to showcase different display modes for the crypto tracker.
Run this script to see how different UI configurations affect the display.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.append('src')

def demo_display_mode(config_path: str, mode_name: str):
    """Demonstrate a specific display mode."""
    print(f"\n{'='*60}")
    print(f"🚀 DEMONSTRATING {mode_name.upper()} DISPLAY MODE")
    print(f"{'='*60}")
    print(f"Config: {config_path}")
    
    try:
        from src.tracker.core import CryptoTracker
        
        # Initialize tracker with specific config
        tracker = CryptoTracker(config_path)
        
        # Show startup banner
        tracker.display_manager.display_startup_banner("demo", 23)
        
        # Show some sample decisions
        sample_decisions = {
            'bitcoin': {
                'action': 'Hold',
                'signal': 'mean_reversion_signal',
                'confidence': 0.65,
                'reason': 'strat=mean_reversion,signal=flat,vol_gate_blocked,regime=bullish'
            },
            'ethereum': {
                'action': 'Buy',
                'signal': 'threshold_breakout',
                'confidence': 0.82,
                'reason': 'strat=momentum,signal=buy,vol_gate_pass,regime=bullish,mtf_confirm=3/4'
            },
            'solana': {
                'action': 'Sell',
                'signal': 'mean_reversion_exit',
                'confidence': 0.74,
                'reason': 'strat=mean_reversion,signal=sell,profit_target_hit,oco_triggered'
            }
        }
        
        # Display decisions
        tracker.display_manager.display_decisions(sample_decisions)
        
        # Show sample status
        from src.models import CoinConfig
        sample_coins = {
            'bitcoin': CoinConfig(
                name='Bitcoin',
                symbol='BTC',
                threshold=45000.0,
                disabled=False
            ),
            'ethereum': CoinConfig(
                name='Ethereum', 
                symbol='ETH',
                threshold=3200.0,
                disabled=False
            ),
            'solana': CoinConfig(
                name='Solana',
                symbol='SOL', 
                threshold=95.0,
                disabled=False
            )
        }
        
        sample_prices = {
            'bitcoin': 45234.56,
            'ethereum': 3245.78,
            'solana': 97.23
        }
        
        # Display status
        tracker.display_manager.display_status(sample_coins, sample_prices)
        
        print(f"\n✅ {mode_name.title()} mode demonstration complete!")
        
    except Exception as e:
        print(f"❌ Error demonstrating {mode_name} mode: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main demo function."""
    print("🎨 Crypto Tracker Display Modes Demo")
    print("This script demonstrates the different UI display configurations available.")
    
    # Check if config files exist
    config_files = {
        'minimal': 'config/config_minimal.yaml',
        'standard': 'config/config.yaml', 
        'detailed': 'config/config_detailed.yaml',
        'verbose': 'config/config_verbose.yaml'
    }
    
    for mode, config_path in config_files.items():
        if not Path(config_path).exists():
            print(f"⚠️  Warning: {config_path} not found, skipping {mode} mode demo")
            continue
            
        demo_display_mode(config_path, mode)
        
        # Pause between demos
        input(f"\nPress Enter to continue to next mode...")
    
    print(f"\n{'='*60}")
    print("🎉 Display modes demonstration complete!")
    print("")
    print("📋 Available display modes:")
    print("  • minimal   - Clean, essential information only")
    print("  • standard  - Balanced view with key metrics")
    print("  • detailed  - Comprehensive analysis and indicators")
    print("  • verbose   - Everything including OCO details")
    print("")
    print("🔧 To use a specific mode:")
    print("  1. Copy the desired config file over config.yaml")
    print("  2. Or modify the 'display_mode' setting in config.yaml")
    print("  3. Run: python3 -m src.entry")
    print("")

if __name__ == "__main__":
    main()
