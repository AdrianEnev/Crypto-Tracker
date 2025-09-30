#!/usr/bin/env python3
"""
Social Media Integration Test Script

This script demonstrates the social media integration features.
Run this to test the integration and see how it works.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.social_media import create_social_integration
from src.social_media.example_integration import EnhancedDecisionEngine


async def test_social_integration():
    """Test the social media integration"""
    print("🚀 Testing Social Media Integration")
    print("=" * 50)
    
    # Initialize social integration
    print("📡 Initializing social media integration...")
    social_integration = create_social_integration()
    
    # Check configuration status
    print("\n📋 Configuration Status:")
    status = social_integration.get_configuration_status()
    print(f"  Enabled: {status['enabled']}")
    print(f"  Enabled Sources: {status['enabled_sources']}")
    print(f"  Features Enabled: {status['feature_status']['features_enabled']}")
    print(f"  Validation Enabled: {status['feature_status']['validation_enabled']}")
    print(f"  Monitoring Enabled: {status['feature_status']['monitoring_enabled']}")
    
    if not status['enabled']:
        print("\n⚠️  Social integration is disabled!")
        print("   To enable it, set 'enabled: true' in config/social_media.yaml")
        print("   You can also enable individual data sources like Google Trends (free)")
        return
    
    # Perform health check
    print("\n🏥 Health Check:")
    health = await social_integration.health_check()
    print(f"  Overall Status: {health['overall']}")
    
    for component, info in health['components'].items():
        print(f"  {component}: {info['status']}")
    
    # Test social signal generation
    print("\n📊 Testing Social Signal Generation:")
    test_coins = ["bitcoin", "ethereum", "dogecoin"]
    
    for coin_id in test_coins:
        print(f"\n  Testing {coin_id.upper()}...")
        try:
            signal = await social_integration.get_social_signal(coin_id)
            
            if signal.get('enabled', False):
                features = signal.get('social_features', {})
                validation = signal.get('validation', {})
                quality = signal.get('quality', {})
                
                print(f"    SMS: {features.get('sms', 0):.3f}")
                print(f"    Sentiment: {features.get('weighted_sentiment', 0):.3f}")
                print(f"    Volume Velocity: {features.get('volume_velocity', 0):.3f}")
                print(f"    Bot Likelihood: {features.get('bot_likeness', 0):.3f}")
                print(f"    Valid: {validation.get('is_valid', False)}")
                print(f"    Quality: {quality.get('quality_score', 0):.3f}")
                print(f"    Risk Level: {validation.get('risk_level', 'unknown')}")
            else:
                print(f"    Social integration disabled or no data available")
                
        except Exception as e:
            print(f"    Error: {e}")
    
    # Test batch processing
    print("\n🔄 Testing Batch Processing:")
    try:
        batch_signals = await social_integration.get_batch_signals(test_coins)
        print(f"  Processed {len(batch_signals)} coins")
        
        for coin_id, signal in batch_signals.items():
            if signal.get('enabled', False):
                sms = signal.get('social_features', {}).get('sms', 0)
                print(f"    {coin_id}: SMS = {sms:.3f}")
            else:
                print(f"    {coin_id}: No data")
                
    except Exception as e:
        print(f"  Batch processing error: {e}")
    
    # Test monitoring dashboard
    print("\n📈 Monitoring Dashboard:")
    try:
        dashboard = social_integration.get_monitoring_dashboard()
        
        if dashboard.get('enabled', False):
            metrics_summary = dashboard.get('metrics_summary', {})
            print(f"  Total Data Points: {metrics_summary.get('total_data_points', 0)}")
            print(f"  Coins Tracked: {metrics_summary.get('total_coins_tracked', 0)}")
            print(f"  Active Alerts: {metrics_summary.get('active_alerts', 0)}")
            print(f"  Average SMS: {metrics_summary.get('avg_sms', 0):.3f}")
            print(f"  Average Sentiment: {metrics_summary.get('avg_sentiment', 0):.3f}")
            
            top_narratives = dashboard.get('top_narratives', [])
            if top_narratives:
                print(f"  Top Narratives: {len(top_narratives)}")
                for i, narrative in enumerate(top_narratives[:3]):
                    print(f"    {i+1}. {narrative['coin_id']}: SMS = {narrative['sms']:.3f}")
        else:
            print("  Monitoring disabled or no data available")
            
    except Exception as e:
        print(f"  Dashboard error: {e}")
    
    # Test enhanced decision engine
    print("\n🎯 Testing Enhanced Decision Engine:")
    try:
        decision_engine = EnhancedDecisionEngine()
        decision_status = decision_engine.get_social_status()
        
        print(f"  Social Integration: {decision_status['enabled']}")
        print(f"  Components Initialized: {decision_status['components_initialized']}")
        
        if decision_status['enabled']:
            print("  Enhanced decision engine is ready!")
            print("  You can now use it to make trading decisions with social signals")
        else:
            print("  Enhanced decision engine will use base decisions only")
            
    except Exception as e:
        print(f"  Decision engine error: {e}")
    
    print("\n✅ Test completed!")
    print("\n📝 Next Steps:")
    print("  1. Enable data sources in config/social_media.yaml")
    print("  2. Set API keys in environment variables")
    print("  3. Enable features and validation")
    print("  4. Integrate with your trading strategies")
    print("  5. Monitor performance and adjust settings")


async def test_individual_features():
    """Test individual features in detail"""
    print("\n🔬 Detailed Feature Testing")
    print("=" * 50)
    
    social_integration = create_social_integration()
    
    if not social_integration.enabled:
        print("Social integration disabled, skipping detailed tests")
        return
    
    # Test data sources
    print("\n📡 Data Sources:")
    enabled_sources = social_integration.get_enabled_sources()
    print(f"  Enabled: {enabled_sources}")
    
    for source in enabled_sources:
        print(f"  {source}: Available")
    
    # Test feature engineering
    print("\n⚙️  Feature Engineering:")
    if social_integration.feature_engine:
        feature_names = social_integration.feature_engine.get_feature_names()
        print(f"  Available Features: {feature_names}")
    else:
        print("  Feature engine not initialized")
    
    # Test validation
    print("\n🛡️  Validation:")
    if social_integration.validator:
        print("  Validator initialized")
        print("  Cross-validation: Available")
        print("  Manipulation detection: Available")
    else:
        print("  Validator not initialized")
    
    # Test monitoring
    print("\n📊 Monitoring:")
    if social_integration.monitoring:
        print("  Monitoring dashboard: Available")
        print("  Alert system: Available")
        print("  Data export: Available")
    else:
        print("  Monitoring not initialized")


def print_configuration_help():
    """Print configuration help"""
    print("\n📖 Configuration Help")
    print("=" * 50)
    print("To enable social media integration:")
    print()
    print("1. Edit config/social_media.yaml:")
    print("   enabled: true")
    print()
    print("2. Enable data sources (at least one):")
    print("   google_trends:")
    print("     enabled: true  # Free, no API key needed")
    print()
    print("   lunarcrush:")
    print("     enabled: true")
    print("     api_key: \"${LUNARCRUSH_API_KEY}\"")
    print()
    print("3. Set environment variables:")
    print("   export LUNARCRUSH_API_KEY=\"your_key\"")
    print("   export SANTIMENT_API_KEY=\"your_key\"")
    print("   # etc...")
    print()
    print("4. Enable features:")
    print("   features:")
    print("     enabled: true")
    print()
    print("5. Enable validation:")
    print("   validation:")
    print("     enabled: true")
    print()
    print("6. Enable monitoring:")
    print("   monitoring:")
    print("     enabled: true")


async def main():
    """Main test function"""
    print("🧪 Social Media Integration Test Suite")
    print("=" * 60)
    
    # Run basic tests
    await test_social_integration()
    
    # Run detailed tests
    await test_individual_features()
    
    # Print configuration help
    print_configuration_help()
    
    print("\n🎉 All tests completed!")
    print("Check the output above for any issues or configuration needs.")


if __name__ == "__main__":
    # Run the test suite
    asyncio.run(main())
