#!/usr/bin/env python3
"""
Test Crypto Discovery Scanner

Quick test to verify the scanner is working with the new lower standards.
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.social_media import create_social_integration


async def test_scanner():
    """Test the crypto discovery scanner."""
    print("🧪 Testing Crypto Discovery Scanner")
    print("=" * 40)
    
    # Check if social integration is enabled
    social_integration = create_social_integration()
    social_status = social_integration.get_configuration_status()
    
    if not social_status['enabled']:
        print("❌ Social media integration is disabled!")
        print("💡 Enable it in config/social_media.yaml")
        return False
    
    print(f"✅ Social integration enabled")
    print(f"📡 Data sources: {social_status['enabled_sources']}")
    
    # Test with a few coins
    test_coins = ["bitcoin", "ethereum", "solana"]
    
    print(f"\n🔍 Testing with {len(test_coins)} coins...")
    
    results = []
    for coin_id in test_coins:
        try:
            print(f"  Testing {coin_id}...")
            social_signal = await social_integration.get_social_signal(coin_id)
            
            if social_signal.get('enabled', False):
                features = social_signal.get('social_features', {})
                validation = social_signal.get('validation', {})
                quality = social_signal.get('quality', {})
                
                # Simple score calculation
                sms = features.get('sms', 0)
                sentiment = features.get('weighted_sentiment', 0)
                volume_velocity = features.get('volume_velocity', 0)
                
                # Calculate score using the new formula
                base_score = abs(sms) * 0.4 + abs(sentiment) * 0.3 + volume_velocity * 0.2
                quality_multiplier = max(0.8, quality.get('quality_score', 0))
                validation_multiplier = max(0.6, validation.get('validation_score', 0))
                
                discovery_score = base_score * quality_multiplier * validation_multiplier * 200
                discovery_score = min(100.0, max(0.0, discovery_score))
                
                results.append({
                    'coin_id': coin_id,
                    'score': discovery_score,
                    'sms': sms,
                    'sentiment': sentiment,
                    'volume_velocity': volume_velocity,
                    'risk_level': validation.get('risk_level', 'unknown'),
                    'is_valid': validation.get('is_valid', False)
                })
                
                print(f"    ✅ Score: {discovery_score:.1f}, SMS: {sms:.3f}, Sentiment: {sentiment:.3f}")
            else:
                print(f"    ⚠️  Social integration disabled for {coin_id}")
                
        except Exception as e:
            print(f"    ❌ Error: {e}")
    
    if results:
        print(f"\n📊 TEST RESULTS:")
        print("-" * 40)
        
        # Sort by score
        results.sort(key=lambda x: x['score'], reverse=True)
        
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['coin_id'].upper()}: {result['score']:.1f}")
            print(f"   SMS: {result['sms']:.3f}, Sentiment: {result['sentiment']:.3f}")
            print(f"   Risk: {result['risk_level']}, Valid: {result['is_valid']}")
        
        # Check if we have any reasonable scores
        high_scores = [r for r in results if r['score'] >= 5.0]
        if high_scores:
            print(f"\n✅ SUCCESS: Found {len(high_scores)} coins with scores ≥ 5.0")
            print("The scanner should now work properly!")
        else:
            print(f"\n⚠️  WARNING: No coins scored ≥ 5.0")
            print("Scores might still be too low. Check debug scanner.")
        
        return True
    else:
        print(f"\n❌ FAILED: No valid results found")
        return False


async def main():
    """Main test function."""
    success = await test_scanner()
    
    if success:
        print(f"\n🎉 Test completed successfully!")
        print("You can now run:")
        print("  python3 quick_crypto_scanner.py")
        print("  python3 crypto_discovery_scanner.py")
        print("  python3 debug_crypto_scanner.py")
    else:
        print(f"\n❌ Test failed. Check your configuration.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
