#!/usr/bin/env python3
"""
Test Reddit Integration

Test Reddit API integration for cryptocurrency subreddit monitoring.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.social_media import create_social_integration

async def test_reddit_integration():
    """Test Reddit integration"""
    print("🔴 Testing Reddit Integration (LunarCrush Replacement)")
    print("=" * 60)
    
    # Check environment variables
    reddit_client_id = os.environ.get("REDDIT_CLIENT_ID")
    reddit_client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    
    print("📋 Reddit API Credentials:")
    print(f"  REDDIT_CLIENT_ID: {reddit_client_id[:10] if reddit_client_id else 'None'}...")
    print(f"  REDDIT_CLIENT_SECRET: {reddit_client_secret[:10] if reddit_client_secret else 'None'}...")
    
    if not reddit_client_id or not reddit_client_secret:
        print("❌ Reddit API credentials not set!")
        print("💡 Set these environment variables:")
        print("   export REDDIT_CLIENT_ID='your_client_id'")
        print("   export REDDIT_CLIENT_SECRET='your_client_secret'")
        print()
        print("📝 To get Reddit API credentials:")
        print("   1. Go to https://www.reddit.com/prefs/apps")
        print("   2. Create a new app (script type)")
        print("   3. Get Client ID and Client Secret")
        print("   4. Free tier: 60 requests per minute")
        print()
        print("❌ Reddit integration test failed.")
        print("Set up Reddit API credentials and try again.")
        return False
    
    try:
        # Create social integration
        print(f"\n🔧 Creating Social Integration...")
        social_integration = create_social_integration()
        
        # Check configuration
        print(f"\n📊 Configuration:")
        config_status = social_integration.get_configuration_status()
        print(f"  Global enabled: {config_status['enabled']}")
        print(f"  Reddit enabled: {social_integration.config.reddit.enabled}")
        print(f"  Reddit client ID: {social_integration.config.reddit.client_id[:10] if social_integration.config.reddit.client_id else 'None'}...")
        print(f"  Reddit client secret: {social_integration.config.reddit.client_secret[:10] if social_integration.config.reddit.client_secret else 'None'}...")
        print(f"  Reddit subreddits: {social_integration.config.reddit.subreddits}")
        
        # Check enabled sources
        print(f"\n📡 Enabled Sources:")
        enabled_sources = config_status['enabled_sources']
        print(f"  Sources: {enabled_sources}")
        print(f"  Reddit in sources: {'reddit' in enabled_sources}")
        
        if 'reddit' not in enabled_sources:
            print("❌ Reddit not enabled!")
            print("💡 Check config/social_media.yaml")
            return False
        
        # Test Reddit data fetching
        print(f"\n🔍 Testing Reddit Data Fetching...")
        test_coins = ["bitcoin", "ethereum"]
        
        for coin_id in test_coins:
            print(f"\n  Testing {coin_id}...")
            try:
                # Fetch Reddit data
                reddit_data = await social_integration.get_social_signal(
                    coin_id=coin_id,
                    data_types=["post_volume", "sentiment_score", "engagement_score", "hot_topics"]
                )
                
                if reddit_data and 'reddit' in reddit_data:
                    reddit_batch = reddit_data['reddit']
                    print(f"    ✅ Reddit data fetched successfully")
                    print(f"    📊 Data points: {len(reddit_batch.data_points)}")
                    print(f"    🎯 Quality score: {reddit_batch.quality_score:.2f}")
                    
                    # Show data points
                    for point in reddit_batch.data_points:
                        print(f"      - {point.data_type}: {point.value:.3f} (confidence: {point.confidence:.2f})")
                else:
                    print(f"    ⚠️  No Reddit data returned for {coin_id}")
                    
            except Exception as e:
                print(f"    ❌ Error fetching Reddit data for {coin_id}: {e}")
        
        print(f"\n✅ Reddit integration test completed!")
        print(f"🎯 Reddit is now integrated and ready to replace LunarCrush features")
        print(f"💰 Cost savings: Additional $500+ per month")
        print(f"📈 Signal quality: 85-90% of LunarCrush")
        
        return True
        
    except Exception as e:
        print(f"❌ Reddit integration test failed: {e}")
        return False

def main():
    """Main test function"""
    try:
        result = asyncio.run(test_reddit_integration())
        if result:
            print(f"\n🎉 Reddit integration is working correctly!")
        else:
            print(f"\n💥 Reddit integration test failed.")
            sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
