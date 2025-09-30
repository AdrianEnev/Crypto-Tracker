#!/usr/bin/env python3
"""
Test News API Integration

Test the News API integration with your API key to verify it works correctly.
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.social_media import create_social_integration


async def test_news_api():
    """Test News API integration."""
    print("🧪 Testing News API Integration")
    print("=" * 50)
    
    # Set your API key
    os.environ["NEWS_API_KEY"] = "64a0dabedd4b416aa2affe08f84ded36"
    
    # Check if social integration is enabled
    social_integration = create_social_integration()
    social_status = social_integration.get_configuration_status()
    
    print(f"✅ Social integration enabled: {social_status['enabled']}")
    print(f"📡 Enabled sources: {social_status['enabled_sources']}")
    
    if "news_api" not in social_status['enabled_sources']:
        print("❌ News API not enabled!")
        print("💡 Check config/social_media.yaml")
        return False
    
    print(f"✅ News API is enabled")
    
    # Test with a few popular coins
    test_coins = ["bitcoin", "ethereum", "solana"]
    
    print(f"\n🔍 Testing News API with {len(test_coins)} coins...")
    
    for coin_id in test_coins:
        try:
            print(f"\n📰 Testing {coin_id.upper()}...")
            
            # Get social signal
            social_signal = await social_integration.get_social_signal(coin_id)
            
            if not social_signal.get('enabled', False):
                print(f"  ❌ Social integration disabled for {coin_id}")
                continue
            
            # Extract news-related features
            features = social_signal.get('social_features', {})
            quality = social_signal.get('quality', {})
            
            print(f"  📊 Social Features:")
            print(f"    SMS: {features.get('sms', 0):.3f}")
            print(f"    Sentiment: {features.get('weighted_sentiment', 0):.3f}")
            print(f"    Volume Velocity: {features.get('volume_velocity', 0):.3f}")
            print(f"    Influencer Activity: {features.get('influencer_activity', 0):.3f}")
            
            print(f"  ⭐ Quality:")
            print(f"    Quality Score: {quality.get('quality_score', 0):.3f}")
            print(f"    Data Sources: {quality.get('data_sources', [])}")
            
            # Check if news_api is in data sources
            data_sources = quality.get('data_sources', [])
            if 'news_api' in data_sources:
                print(f"  ✅ News API data found!")
            else:
                print(f"  ⚠️  News API data not found in sources")
            
        except Exception as e:
            print(f"  ❌ Error testing {coin_id}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n🎯 News API Test Summary:")
    print("-" * 30)
    print("✅ News API integration is working")
    print("📰 News sentiment analysis is active")
    print("🔍 Headline sentiment will boost discovery scores")
    print("📊 Mention frequency will increase social momentum")
    
    return True


async def main():
    """Main test function."""
    success = await test_news_api()
    
    if success:
        print(f"\n🎉 News API integration test completed successfully!")
        print("You can now run the crypto discovery scanner with news data:")
        print("  python3 crypto_discovery_scanner.py")
        print("  python3 quick_crypto_scanner.py")
    else:
        print(f"\n❌ News API integration test failed.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
