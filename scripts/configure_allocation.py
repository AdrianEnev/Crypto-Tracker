#!/usr/bin/env python3
"""
Configuration Helper Script
Helps users understand and customize their portfolio allocation.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config.flexible_loader import FlexibleConfigLoader, get_allocation_summary, create_config_for_risk_profile


def main():
    """Main configuration helper function."""
    print("🎯 Portfolio Allocation Configuration Helper")
    print("=" * 50)
    
    # Check if config file exists
    config_path = "config/paper_24_7_optimized.yaml"
    if not os.path.exists(config_path):
        print(f"❌ Configuration file not found: {config_path}")
        print("Please make sure you're running this from the project root directory.")
        return
    
    try:
        # Load current configuration
        loader = FlexibleConfigLoader(config_path)
        
        # Show current allocation summary
        print(get_allocation_summary(config_path))
        
        # Interactive configuration
        print("\n🔧 Configuration Options:")
        print("1. View current allocation")
        print("2. Create conservative configuration")
        print("3. Create moderate configuration") 
        print("4. Create aggressive configuration")
        print("5. Create custom configuration")
        print("6. Exit")
        
        while True:
            choice = input("\nEnter your choice (1-6): ").strip()
            
            if choice == "1":
                print(get_allocation_summary(config_path))
                
            elif choice == "2":
                create_custom_config("conservative")
                
            elif choice == "3":
                create_custom_config("moderate")
                
            elif choice == "4":
                create_custom_config("aggressive")
                
            elif choice == "5":
                create_custom_config_interactive()
                
            elif choice == "6":
                print("👋 Goodbye!")
                break
                
            else:
                print("❌ Invalid choice. Please enter 1-6.")
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("Please check your configuration file.")


def create_custom_config(risk_profile: str):
    """Create a configuration file for a specific risk profile."""
    try:
        config_path = create_config_for_risk_profile(risk_profile)
        print(f"✅ Created {risk_profile} configuration: {config_path}")
        
        # Show the allocation summary
        print(get_allocation_summary(config_path))
        
    except Exception as e:
        print(f"❌ Error creating {risk_profile} configuration: {str(e)}")


def create_custom_config_interactive():
    """Create a custom configuration interactively."""
    print("\n🎯 Custom Configuration Creator")
    print("=" * 40)
    
    try:
        # Get allocation preferences
        bitcoin_pct = float(input("Bitcoin allocation percentage (0-100): "))
        ethereum_pct = float(input("Ethereum allocation percentage (0-100): "))
        altcoins_pct = float(input("Altcoins allocation percentage (0-100): "))
        
        # Validate allocation
        total = bitcoin_pct + ethereum_pct + altcoins_pct
        if abs(total - 100.0) > 0.1:
            print(f"⚠️  Warning: Allocation totals {total:.1f}%, not 100%")
            adjust = input("Adjust to 100%? (y/n): ").lower() == 'y'
            if adjust:
                bitcoin_pct = (bitcoin_pct / total) * 100
                ethereum_pct = (ethereum_pct / total) * 100
                altcoins_pct = (altcoins_pct / total) * 100
                print(f"✅ Adjusted: BTC {bitcoin_pct:.1f}%, ETH {ethereum_pct:.1f}%, Altcoins {altcoins_pct:.1f}%")
        
        # Get risk preferences
        print("\nRisk Management:")
        daily_loss = float(input("Max daily loss percentage (1-10): "))
        drawdown = float(input("Max drawdown percentage (5-25): "))
        risk_per_trade = float(input("Risk per trade percentage (0.5-3.0): "))
        
        # Get strategy preferences
        print("\nAdvanced Strategies:")
        use_advanced = input("Use advanced strategies? (y/n): ").lower() == 'y'
        use_derivatives = input("Use derivatives signals? (y/n): ").lower() == 'y'
        use_onchain = input("Use on-chain metrics? (y/n): ").lower() == 'y'
        
        # Create custom configuration
        custom_config = {
            "risk_profile": "custom",
            "portfolio_allocation": {
                "bitcoin_allocation_pct": bitcoin_pct,
                "ethereum_allocation_pct": ethereum_pct,
                "altcoins_allocation_pct": altcoins_pct,
                "rebalancing": {
                    "enabled": True,
                    "threshold_pct": 10.0,
                    "min_interval_days": 30
                }
            },
            "advanced_strategies": {
                "bitcoin_multi_bucket": {"enabled": use_advanced},
                "ethereum_staking_trading": {"enabled": use_advanced},
                "derivatives_integration": {"enabled": use_derivatives},
                "onchain_metrics": {"enabled": use_onchain},
                "volatility_regime_classification": {"enabled": use_advanced}
            },
            "risk_management": {
                "max_daily_loss_pct": daily_loss,
                "max_drawdown_pct": drawdown,
                "position_sizing": {
                    "method": "atr_based" if use_advanced else "fixed",
                    "risk_per_trade_pct": risk_per_trade,
                    "max_position_size_pct": min(15.0, risk_per_trade * 5)
                }
            }
        }
        
        # Save configuration
        import yaml
        config_filename = "config/paper_24_7_custom.yaml"
        with open(config_filename, 'w') as file:
            yaml.dump(custom_config, file, default_flow_style=False, indent=2)
        
        print(f"✅ Created custom configuration: {config_filename}")
        
        # Show summary
        print(f"""
📊 Your Custom Configuration:
===============================

🎯 Asset Allocation:
   • Bitcoin: {bitcoin_pct:.1f}% of crypto portfolio
   • Ethereum: {ethereum_pct:.1f}% of crypto portfolio  
   • Altcoins: {altcoins_pct:.1f}% of crypto portfolio

🛡️ Risk Management:
   • Max Daily Loss: {daily_loss:.1f}%
   • Max Drawdown: {drawdown:.1f}%
   • Risk per Trade: {risk_per_trade:.1f}%

🚀 Advanced Features:
   • Advanced Strategies: {'Enabled' if use_advanced else 'Disabled'}
   • Derivatives Signals: {'Enabled' if use_derivatives else 'Disabled'}
   • On-Chain Metrics: {'Enabled' if use_onchain else 'Disabled'}

💡 Example with $100,000 portfolio:
   • Bitcoin: ${bitcoin_pct * 1000:.0f}
   • Ethereum: ${ethereum_pct * 1000:.0f}
   • Altcoins: ${altcoins_pct * 1000:.0f}
        """)
        
    except ValueError:
        print("❌ Invalid input. Please enter valid numbers.")
    except Exception as e:
        print(f"❌ Error creating custom configuration: {str(e)}")


if __name__ == "__main__":
    main()
