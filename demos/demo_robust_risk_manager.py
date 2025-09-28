#!/usr/bin/env python3
"""
Demo script for the Robust Risk Manager.
Shows how the comprehensive risk management system works.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.tracker.config_manager import ConfigManager
from src.tracker.portfolio_manager import PortfolioManager
from src.risk import RobustRiskManager
from src.portfolio import Portfolio


def demo_risk_manager():
    """Demonstrate the robust risk manager functionality."""
    print("🚀 Robust Risk Manager Demo")
    print("=" * 50)
    
    try:
        # Initialize components
        config_manager = ConfigManager("config/config.yaml")
        config = config_manager.load_config()
        portfolio_manager = PortfolioManager(config_manager, config)
        
        # Initialize robust risk manager
        robust_risk_manager = RobustRiskManager(
            config_manager, 
            portfolio_manager
        )
        
        print("✅ Risk manager initialized successfully")
        
        # Demo 1: Check if trading is allowed
        print(f"\n📊 Trading Status:")
        print(f"   Trading Allowed: {robust_risk_manager.is_trading_allowed()}")
        print(f"   Risk Manager Enabled: {robust_risk_manager.config.enabled}")
        
        # Demo 2: Get current risk summary
        print(f"\n📈 Risk Summary:")
        risk_summary = robust_risk_manager.get_risk_summary()
        
        if risk_summary:
            print(f"   Overall Risk Level: {risk_summary.get('overall_risk_level', 'unknown')}")
            print(f"   Kill Switch Active: {risk_summary.get('kill_switch_active', False)}")
            
            exposure = risk_summary.get('exposure_metrics', {})
            print(f"   Total Exposure: {exposure.get('total_exposure_pct', 0):.2f}%")
            print(f"   Leverage Utilization: {exposure.get('leverage_utilization', 0):.2f}x")
            
            drawdown = risk_summary.get('drawdown_metrics', {})
            print(f"   Current Drawdown: {drawdown.get('current_drawdown_pct', 0):.2f}%")
            print(f"   Daily Drawdown: {drawdown.get('daily_drawdown_pct', 0):.2f}%")
            print(f"   Max Drawdown: {drawdown.get('max_drawdown_pct', 0):.2f}%")
        else:
            print("   No risk data available")
        
        # Demo 3: Simulate a risk assessment
        print(f"\n🔍 Simulating Risk Assessment:")
        
        # Mock price data
        mock_prices = {
            'BTC': 45000.0,
            'ETH': 3000.0,
            'SOL': 100.0
        }
        
        risk_status = robust_risk_manager.perform_risk_assessment(mock_prices)
        print(f"   Risk Level: {risk_status.overall_risk_level.value}")
        print(f"   Active Violations: {len(risk_status.active_violations)}")
        print(f"   Kill Switch Active: {risk_status.kill_switch_active}")
        
        if risk_status.active_violations:
            print("   Violations:")
            for violation in risk_status.active_violations[:3]:  # Show first 3
                print(f"     - {violation.message}")
        
        # Demo 4: Pre-trade risk check
        print(f"\n⚡ Pre-Trade Risk Check Demo:")
        
        # Simulate a buy order
        risk_check = robust_risk_manager.check_pre_trade_risk(
            symbol='BTC',
            side='buy',
            quantity=0.1,
            price=45000.0,
            stop_loss=43000.0
        )
        
        print(f"   Trade Allowed: {risk_check.is_valid}")
        if not risk_check.is_valid:
            print("   Rejection Reasons:")
            for violation in risk_check.violations:
                print(f"     - {violation.message}")
        else:
            print("   ✅ Trade passed all risk checks")
        
        # Demo 5: Configuration display
        print(f"\n⚙️  Risk Configuration:")
        limits = robust_risk_manager.config.limits
        print(f"   Max Exposure per Coin: {limits.portfolio.max_exposure_per_coin_pct}%")
        print(f"   Max Total Exposure: {limits.portfolio.max_total_exposure_pct}%")
        print(f"   Max Open Positions: {limits.portfolio.max_open_positions}")
        print(f"   Daily Drawdown Limit: {limits.drawdown.daily_max_drawdown_pct}%")
        print(f"   Kill Switch Trigger: {limits.drawdown.kill_switch_drawdown_pct}%")
        print(f"   Max Leverage: {limits.leverage.max_leverage}x")
        
        # Demo 6: Kill switch functionality
        print(f"\n🚨 Kill Switch Demo:")
        print(f"   Current Status: {'ACTIVE' if robust_risk_manager.kill_switch.is_active else 'INACTIVE'}")
        
        if not robust_risk_manager.kill_switch.is_active:
            print("   Testing manual kill switch activation...")
            robust_risk_manager.force_kill_switch_activation("demo_test")
            print(f"   Status After Activation: {'ACTIVE' if robust_risk_manager.kill_switch.is_active else 'INACTIVE'}")
            print(f"   Trading Allowed: {robust_risk_manager.is_trading_allowed()}")
            
            # Deactivate
            robust_risk_manager.force_kill_switch_deactivation("demo_complete")
            print(f"   Status After Deactivation: {'ACTIVE' if robust_risk_manager.kill_switch.is_active else 'INACTIVE'}")
        
        print(f"\n✅ Demo completed successfully!")
        print(f"\n💡 Key Features Demonstrated:")
        print(f"   • Portfolio exposure tracking")
        print(f"   • Multi-timeframe drawdown monitoring")
        print(f"   • Pre-trade risk validation")
        print(f"   • Automated kill switch system")
        print(f"   • Comprehensive risk reporting")
        print(f"   • Configurable risk limits")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    demo_risk_manager()
