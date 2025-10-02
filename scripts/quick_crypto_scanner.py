#!/usr/bin/env python3
"""
DEPRECATED: Quick Crypto Discovery Scanner

⚠️  WARNING: This script is DEPRECATED but preserved for safety.
    Use crypto_discovery_scanner.py for full functionality.

This script is a simplified version of crypto_discovery_scanner.py.
The full scanner provides more comprehensive functionality and better integration.

PRESERVED FOR SAFETY: Contains quick scanning patterns that could be useful.
TODO: Integrate quick scanning features into main scanner, then remove this script.
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


class QuickCryptoScanner:
    """Quick scanner for popular cryptocurrencies."""
    
    def __init__(self):
        self.social_integration = create_social_integration()
        
        # Focus on most popular/tradeable coins
        self.popular_coins = [
            "bitcoin", "ethereum", "binancecoin", "cardano", "solana",
            "polkadot", "chainlink", "litecoin", "bitcoin-cash", "dogecoin",
            "avalanche-2", "polygon", "cosmos", "algorand", "stellar",
            "uniswap", "aave", "shiba-inu", "monero", "tron"
        ]
    
    async def quick_scan(self) -> List[Dict[str, Any]]:
        """Perform a quick scan of popular cryptocurrencies."""
        print("🔍 Quick scanning popular cryptocurrencies...")
        
        results = []
        
        for coin_id in self.popular_coins:
            try:
                # Get social signal
                social_signal = await self.social_integration.get_social_signal(coin_id)
                
                if not social_signal.get('enabled', False):
                    continue
                
                # Extract key metrics
                features = social_signal.get('social_features', {})
                validation = social_signal.get('validation', {})
                
                # Calculate quick score
                sms = features.get('sms', 0)
                sentiment = features.get('weighted_sentiment', 0)
                volume_velocity = features.get('volume_velocity', 0)
                
                # Simple scoring: combine SMS, sentiment, and volume (realistic)
                quick_score = (abs(sms) + abs(sentiment) + volume_velocity) * 25  # Back to realistic multiplier
                
                results.append({
                    'coin_id': coin_id,
                    'score': quick_score,
                    'sms': sms,
                    'sentiment': sentiment,
                    'volume_velocity': volume_velocity,
                    'risk_level': validation.get('risk_level', 'unknown'),
                    'is_valid': validation.get('is_valid', False)
                })
                
                print(f"  ✅ {coin_id}: Score {quick_score:.1f}")
                
            except Exception as e:
                print(f"  ❌ {coin_id}: Error - {e}")
                continue
        
        # Sort by score
        results.sort(key=lambda x: x['score'], reverse=True)
        return results
    
    def print_quick_report(self, results: List[Dict[str, Any]]):
        """Print a quick discovery report."""
        print("\n" + "="*60)
        print("🚀 QUICK CRYPTO DISCOVERY SCAN")
        print("="*60)
        print(f"📅 Scan Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔍 Coins Scanned: {len(results)}")
        
        # Top opportunities
        print(f"\n🏆 TOP OPPORTUNITIES")
        print("-" * 60)
        
        for i, result in enumerate(results[:10], 1):
            coin_id = result['coin_id'].upper()
            score = result['score']
            sms = result['sms']
            sentiment = result['sentiment']
            risk = result['risk_level']
            valid = result['is_valid']
            
            # Add emoji based on score (realistic thresholds)
            if score > 15:
                emoji = "🔥"
            elif score > 8:
                emoji = "📈"
            elif score > 3:
                emoji = "👀"
            else:
                emoji = "📊"
            
            print(f"{emoji} {i:2d}. {coin_id:<15} | Score: {score:5.1f} | "
                  f"SMS: {sms:6.3f} | Sentiment: {sentiment:6.3f} | "
                  f"Risk: {risk:<6} | Valid: {valid}")
        
        # Recommendations
        print(f"\n💡 QUICK RECOMMENDATIONS")
        print("-" * 60)
        
        top_3 = results[:3]
        if top_3:
            print("Research these top 3 coins:")
            for i, result in enumerate(top_3, 1):
                print(f"{i}. {result['coin_id'].upper()} (Score: {result['score']:.1f})")
        
        # Safe picks
        safe_picks = [r for r in results if r['risk_level'] == 'low' and r['is_valid']][:3]
        if safe_picks:
            print(f"\nSafe picks (low risk, validated):")
            for i, result in enumerate(safe_picks, 1):
                print(f"{i}. {result['coin_id'].upper()} (Score: {result['score']:.1f})")
        
        print(f"\n⚠️  Always do your own research before trading!")
        print("="*60)


async def main():
    """Main function for quick crypto scanning."""
    print("🚀 Quick Crypto Discovery Scanner")
    print("=" * 40)
    
    # Check social integration
    scanner = QuickCryptoScanner()
    social_status = scanner.social_integration.get_configuration_status()
    
    if not social_status['enabled']:
        print("❌ Social media integration is disabled!")
        print("💡 Enable it in config/social_media.yaml")
        return
    
    print(f"✅ Social integration enabled")
    print(f"📡 Data sources: {social_status['enabled_sources']}")
    
    # Quick scan
    results = await scanner.quick_scan()
    
    if not results:
        print("❌ No results found. Check your configuration.")
        return
    
    # Print report
    scanner.print_quick_report(results)
    
    # Interactive suggestions
    print(f"\n🎯 WHAT TO DO NEXT:")
    print("1. Research the top-scoring coins")
    print("2. Check their recent news and developments")
    print("3. Add promising ones to your watchlist")
    print("4. Consider paper trading them")
    print("5. Run this scanner regularly")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Scan interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
