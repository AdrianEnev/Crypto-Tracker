#!/usr/bin/env python3
"""
Demo script to showcase the different table formats for the crypto tracker.
This script demonstrates both 'standard' and 'per_coin' table formats.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.append('src')

def demo_table_format(config_path: str, format_name: str):
    """Demonstrate a specific table format."""
    print(f"\n{'='*80}")
    print(f"🎨 DEMONSTRATING {format_name.upper()} TABLE FORMAT")
    print(f"{'='*80}")
    print(f"Config: {config_path}")
    
    try:
        from src.tracker.core import CryptoTracker
        from src.models import CoinConfig
        
        # Initialize tracker with specific config
        tracker = CryptoTracker(config_path)
        
        # Create sample data for demonstration
        sample_coins = {
            'bitcoin': CoinConfig(
                symbol='BTC',
                name='Bitcoin',
                threshold=45000.0,
                check_interval=60,
                disabled=False
            ),
            'ethereum': CoinConfig(
                symbol='ETH',
                name='Ethereum', 
                threshold=3200.0,
                check_interval=60,
                disabled=False
            ),
            'solana': CoinConfig(
                symbol='SOL',
                name='Solana', 
                threshold=95.0,
                check_interval=60,
                disabled=False
            ),
            'cardano': CoinConfig(
                symbol='ADA',
                name='Cardano',
                threshold=0.45,
                check_interval=60,
                disabled=False
            )
        }
        
        sample_prices = {
            'bitcoin': 45234.56,
            'ethereum': 3245.78,
            'solana': 97.23,
            'cardano': 0.42
        }
        
        # Display the table format
        tracker.display_manager.display_status(sample_coins, sample_prices)
        
        print(f"\n✅ {format_name.title()} table format demonstration complete!")
        
    except Exception as e:
        print(f"❌ Error demonstrating {format_name} format: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main demo function."""
    print("🎨 Crypto Tracker Table Formats Demo")
    print("This script demonstrates the different table display formats available.")
    
    # Check if config files exist
    config_files = {
        'standard_table': 'config/config.yaml',
        'per_coin_table': 'config/config_per_coin.yaml'
    }
    
    for format_name, config_path in config_files.items():
        if not Path(config_path).exists():
            print(f"⚠️  Warning: {config_path} not found, skipping {format_name} demo")
            continue
            
        demo_table_format(config_path, format_name)
        
        # Pause between demos
        input(f"\nPress Enter to continue to next format...")
    
    print(f"\n{'='*80}")
    print("🎉 Table formats demonstration complete!")
    print("")
    print("📋 Available table formats:")
    print("  • standard  - Traditional table with all coins in rows")
    print("  • per_coin  - Individual table for each cryptocurrency")
    print("")
    print("🔧 To use a specific table format:")
    print("  1. Set 'table_format' in config/config.yaml:")
    print("     table_display:")
    print("       table_format: 'per_coin'  # or 'standard'")
    print("  2. Or copy config_per_coin.yaml over config.yaml")
    print("  3. Run: python3 -m src.entry")
    print("")
    print("💡 Benefits of each format:")
    print("  • Standard: Compact view, easy to compare all coins at once")
    print("  • Per-coin: Detailed view, easier to read individual coin metrics")
    print("")

if __name__ == "__main__":
    main()
