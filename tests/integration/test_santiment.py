#!/usr/bin/env python3
"""
Santiment Social Media Integration Test

This script tests the social media integration specifically with Santiment API.
Make sure you have set your SANTIMENT_API_KEY environment variable.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def check_environment():
    """Check if required environment variables are set"""
    print("🔑 Checking Environment Variables...")
    
    santiment_key = os.environ.get("SANTIMENT_API_KEY")
    if santiment_key:
        print(f"  ✅ SANTIMENT_API_KEY: {'*' * (len(santiment_key) - 4) + santiment_key[-4:]}")
        return True
    else:
        print("  ❌ SANTIMENT_API_KEY not set")
        print("  💡 Set it with: export SANTIMENT_API_KEY='your_api_key'")
        return False


async def test_santiment_integration():
    """Test Santiment integration specifically"""
    print("\n📡 Testing Santiment Integration...")
    
    try:
        from src.social_media import create_social_integration
        
        # Initialize social integration
        social_integration = create_social_integration()
        
        # Check configuration
        status = social_integration.get_configuration_status()
        print(f"  Social Integration Enabled: {status['enabled']}")
        print(f"  Enabled Sources: {status['enabled_sources']}")
        
        if not status['enabled']:
            print("  ❌ Social integration is disabled in config")
            return False
        
        if 'santiment' not in status['enabled_sources']:
            print("  ❌ Santiment is not enabled in config")
            return False
        
        # Test health check
        print("\n🏥 Health Check:")
        health = await social_integration.health_check()
        print(f"  Overall Status: {health['overall']}")
        
        # Test social signal generation
        print("\n📊 Testing Social Signal Generation:")
        test_coins = ["bitcoin", "ethereum"]
        
        for coin_id in test_coins:
            print(f"\n  Testing {coin_id.upper()}...")
            try:
                signal = await social_integration.get_social_signal(coin_id)
                
                if signal.get('enabled', False):
                    features = signal.get('social_features', {})
                    validation = signal.get('validation', {})
                    quality = signal.get('quality', {})
                    
                    print(f"    ✅ SMS: {features.get('sms', 0):.3f}")
                    print(f"    ✅ Sentiment: {features.get('weighted_sentiment', 0):.3f}")
                    print(f"    ✅ Volume Velocity: {features.get('volume_velocity', 0):.3f}")
                    print(f"    ✅ Bot Likelihood: {features.get('bot_likeness', 0):.3f}")
                    print(f"    ✅ Valid: {validation.get('is_valid', False)}")
                    print(f"    ✅ Quality: {quality.get('quality_score', 0):.3f}")
                    print(f"    ✅ Risk Level: {validation.get('risk_level', 'unknown')}")
                    
                    # Check data sources
                    data_sources = quality.get('data_sources', [])
                    print(f"    ✅ Data Sources: {data_sources}")
                    
                else:
                    print(f"    ⚠️  Social integration disabled or no data available")
                    print(f"    Error: {signal.get('error', 'Unknown error')}")
                    
            except Exception as e:
                print(f"    ❌ Error: {e}")
        
        # Test monitoring dashboard
        print("\n📈 Monitoring Dashboard:")
        try:
            dashboard = social_integration.get_monitoring_dashboard()
            
            if dashboard.get('enabled', False):
                metrics_summary = dashboard.get('metrics_summary', {})
                print(f"  ✅ Total Data Points: {metrics_summary.get('total_data_points', 0)}")
                print(f"  ✅ Coins Tracked: {metrics_summary.get('total_coins_tracked', 0)}")
                print(f"  ✅ Active Alerts: {metrics_summary.get('active_alerts', 0)}")
                print(f"  ✅ Average SMS: {metrics_summary.get('avg_sms', 0):.3f}")
            else:
                print("  ⚠️  Monitoring disabled or no data available")
                
        except Exception as e:
            print(f"  ❌ Dashboard error: {e}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Integration test failed: {e}")
        return False


async def test_enhanced_decision_engine():
    """Test the enhanced decision engine"""
    print("\n🎯 Testing Enhanced Decision Engine...")
    
    try:
        from src.social_media.example_integration import EnhancedDecisionEngine
        
        # Initialize enhanced decision engine
        decision_engine = EnhancedDecisionEngine()
        decision_status = decision_engine.get_social_status()
        
        print(f"  ✅ Social Integration: {decision_status['enabled']}")
        print(f"  ✅ Components Initialized: {decision_status['components_initialized']}")
        
        if decision_status['enabled']:
            print("  ✅ Enhanced decision engine is ready!")
            print("  💡 You can now use it to make trading decisions with social signals")
            
            # Test health check
            health = await decision_engine.health_check()
            print(f"  ✅ Health Status: {health['overall']}")
            
        else:
            print("  ⚠️  Enhanced decision engine will use base decisions only")
            
        return True
        
    except Exception as e:
        print(f"  ❌ Decision engine test failed: {e}")
        return False


def print_next_steps():
    """Print next steps for integration"""
    print("\n🚀 Next Steps for Integration:")
    print("=" * 50)
    print("1. 📊 Paper Trading Integration:")
    print("   - The social media integration is NOT yet integrated into paper trading 24/7")
    print("   - You'll need to modify the paper trading system to use EnhancedDecisionEngine")
    print("   - This would be a separate integration step")
    print()
    print("2. 🔧 Manual Testing:")
    print("   - Use the EnhancedDecisionEngine in your existing strategies")
    print("   - Test with paper trading first before live trading")
    print("   - Monitor the social signals and their impact on decisions")
    print()
    print("3. 📈 Integration Points:")
    print("   - Replace 'make_decision()' calls with 'make_enhanced_decision()'")
    print("   - Add social signal monitoring to your dashboards")
    print("   - Configure alert thresholds based on your risk tolerance")
    print()
    print("4. 🛡️ Safety First:")
    print("   - Start with low social signal weights (max_social_weight: 0.1)")
    print("   - Enable all validation features")
    print("   - Monitor for manipulation alerts")
    print("   - Gradually increase weights as you gain confidence")


async def main():
    """Main test function"""
    print("🧪 Santiment Social Media Integration Test")
    print("=" * 60)
    
    # Check environment
    env_ok = check_environment()
    if not env_ok:
        print("\n❌ Environment setup incomplete. Please set SANTIMENT_API_KEY")
        return
    
    # Test Santiment integration
    integration_ok = await test_santiment_integration()
    
    # Test enhanced decision engine
    decision_ok = await test_enhanced_decision_engine()
    
    # Print results
    print("\n📋 Test Results")
    print("=" * 30)
    print(f"Environment Setup: {'✅ PASS' if env_ok else '❌ FAIL'}")
    print(f"Santiment Integration: {'✅ PASS' if integration_ok else '❌ FAIL'}")
    print(f"Decision Engine: {'✅ PASS' if decision_ok else '❌ FAIL'}")
    
    if env_ok and integration_ok and decision_ok:
        print("\n🎉 All tests passed! Santiment integration is working.")
        print_next_steps()
    else:
        print("\n❌ Some tests failed. Check the output above for issues.")


if __name__ == "__main__":
    # Run the test
    asyncio.run(main())
