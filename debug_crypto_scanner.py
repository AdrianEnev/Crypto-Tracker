#!/usr/bin/env python3
"""
Debug Crypto Discovery Scanner

A debug version that shows detailed information about what's happening
with the social media signals and scoring.

Usage: python3 debug_crypto_scanner.py
"""

import asyncio
import sys
import os
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import logging

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.social_media import create_social_integration


class DebugCryptoScanner:
    """Debug scanner that shows detailed social signal information."""
    
    def __init__(self):
        self.social_integration = create_social_integration()
        
        # Test with a few popular coins first
        self.test_coins = [
            "bitcoin", "ethereum", "solana", "cardano", "polkadot",
            "chainlink", "avalanche-2", "polygon", "dogecoin", "shiba-inu"
        ]
    
    async def debug_scan_coin(self, coin_id: str) -> Dict[str, Any]:
        """Debug scan a single cryptocurrency."""
        print(f"\n🔍 DEBUG SCANNING: {coin_id.upper()}")
        print("-" * 50)
        
        try:
            # Get social signal
            social_signal = await self.social_integration.get_social_signal(coin_id)
            
            print(f"✅ Social signal received")
            print(f"📊 Enabled: {social_signal.get('enabled', False)}")
            
            if not social_signal.get('enabled', False):
                print(f"❌ Social integration disabled for {coin_id}")
                return None
            
            # Extract detailed metrics
            features = social_signal.get('social_features', {})
            validation = social_signal.get('validation', {})
            quality = social_signal.get('quality', {})
            
            print(f"\n📈 SOCIAL FEATURES:")
            print(f"  SMS (Social Momentum Score): {features.get('sms', 0):.6f}")
            print(f"  Weighted Sentiment: {features.get('weighted_sentiment', 0):.6f}")
            print(f"  Volume Velocity: {features.get('volume_velocity', 0):.6f}")
            print(f"  Influencer Activity: {features.get('influencer_activity', 0):.6f}")
            print(f"  Bot Likeness: {features.get('bot_likeness', 0):.6f}")
            
            print(f"\n🛡️  VALIDATION:")
            print(f"  Validation Score: {validation.get('validation_score', 0):.6f}")
            print(f"  Risk Level: {validation.get('risk_level', 'unknown')}")
            print(f"  Is Valid: {validation.get('is_valid', False)}")
            
            print(f"\n⭐ QUALITY:")
            print(f"  Quality Score: {quality.get('quality_score', 0):.6f}")
            print(f"  Data Sources: {quality.get('data_sources', [])}")
            
            # Calculate discovery score step by step
            sms = features.get('sms', 0)
            sentiment = features.get('weighted_sentiment', 0)
            volume_velocity = features.get('volume_velocity', 0)
            influencer_activity = features.get('influencer_activity', 0)
            bot_likeness = features.get('bot_likeness', 0)
            
            quality_score = quality.get('quality_score', 0)
            validation_score = validation.get('validation_score', 0)
            
            # Step-by-step calculation
            print(f"\n🧮 SCORE CALCULATION:")
            
            base_score = (
                abs(sms) * 0.4 +
                abs(sentiment) * 0.3 +
                volume_velocity * 0.2 +
                influencer_activity * 0.1
            )
            print(f"  Base Score: {base_score:.6f}")
            print(f"    SMS component: {abs(sms) * 0.4:.6f}")
            print(f"    Sentiment component: {abs(sentiment) * 0.3:.6f}")
            print(f"    Volume component: {volume_velocity * 0.2:.6f}")
            print(f"    Influencer component: {influencer_activity * 0.1:.6f}")
            
            bot_penalty = bot_likeness * 0.2
            print(f"  Bot Penalty: {bot_penalty:.6f}")
            
            quality_multiplier = max(0.8, quality_score)
            print(f"  Quality Multiplier: {quality_multiplier:.6f}")
            
            validation_multiplier = max(0.6, validation_score)
            print(f"  Validation Multiplier: {validation_multiplier:.6f}")
            
            discovery_score = (base_score - bot_penalty) * quality_multiplier * validation_multiplier
            print(f"  Final Score (before scaling): {discovery_score:.6f}")
            
            final_score = min(100.0, max(0.0, discovery_score * 200))
            print(f"  Final Discovery Score: {final_score:.1f}")
            
            return {
                'coin_id': coin_id,
                'discovery_score': final_score,
                'sms': sms,
                'sentiment': sentiment,
                'volume_velocity': volume_velocity,
                'influencer_activity': influencer_activity,
                'bot_likeness': bot_likeness,
                'validation_score': validation_score,
                'risk_level': validation.get('risk_level', 'unknown'),
                'quality_score': quality_score,
                'is_valid': validation.get('is_valid', False),
                'data_sources': quality.get('data_sources', []),
                'base_score': base_score,
                'bot_penalty': bot_penalty,
                'quality_multiplier': quality_multiplier,
                'validation_multiplier': validation_multiplier
            }
            
        except Exception as e:
            print(f"❌ Error scanning {coin_id}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def debug_scan_all(self) -> List[Dict[str, Any]]:
        """Debug scan all test coins."""
        print("🚀 DEBUG CRYPTO DISCOVERY SCANNER")
        print("=" * 60)
        print(f"📅 Scan Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔍 Testing {len(self.test_coins)} coins")
        
        results = []
        
        for coin_id in self.test_coins:
            result = await self.debug_scan_coin(coin_id)
            if result:
                results.append(result)
        
        # Sort by discovery score
        results.sort(key=lambda x: x['discovery_score'], reverse=True)
        
        print(f"\n🏆 DEBUG RESULTS SUMMARY")
        print("=" * 60)
        
        if not results:
            print("❌ No valid results found!")
            return results
        
        print(f"✅ Found {len(results)} valid results")
        print(f"\n📊 TOP RESULTS:")
        
        for i, result in enumerate(results[:5], 1):
            print(f"{i}. {result['coin_id'].upper()}: {result['discovery_score']:.1f}")
            print(f"   SMS: {result['sms']:.3f}, Sentiment: {result['sentiment']:.3f}")
            print(f"   Risk: {result['risk_level']}, Valid: {result['is_valid']}")
        
        return results


async def main():
    """Main function for debug scanning."""
    scanner = DebugCryptoScanner()
    
    # Check social integration
    social_status = scanner.social_integration.get_configuration_status()
    
    if not social_status['enabled']:
        print("❌ Social media integration is disabled!")
        print("💡 Enable it in config/social_media.yaml")
        return
    
    print(f"✅ Social integration enabled")
    print(f"📡 Data sources: {social_status['enabled_sources']}")
    
    # Perform health check
    print(f"\n🏥 Performing health check...")
    health = await scanner.social_integration.health_check()
    print(f"Health status: {health['overall']}")
    
    if health['overall'] != 'healthy':
        print("⚠️  Some components may not be working properly")
        print("Continuing with debug scan anyway...")
    
    # Debug scan
    results = await scanner.debug_scan_all()
    
    if results:
        print(f"\n💡 DEBUG INSIGHTS:")
        print("-" * 40)
        print("1. Check if SMS values are reasonable (0.001-0.1 range)")
        print("2. Sentiment should be between -1 and +1")
        print("3. Volume velocity should be positive for trending coins")
        print("4. Quality and validation scores should be > 0.5")
        print("5. Bot likeness should be low (< 0.3) for good signals")
        
        # Find the best opportunity
        best = results[0]
        print(f"\n🎯 BEST OPPORTUNITY: {best['coin_id'].upper()}")
        print(f"   Discovery Score: {best['discovery_score']:.1f}")
        print(f"   Social Momentum: {best['sms']:.3f}")
        print(f"   Sentiment: {best['sentiment']:.3f}")
        print(f"   Risk Level: {best['risk_level']}")
    
    print(f"\n⚠️  This is debug information for development purposes only!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Debug scan interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
