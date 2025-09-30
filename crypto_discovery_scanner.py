#!/usr/bin/env python3
"""
Crypto Discovery Scanner

Uses social media signals to identify cryptocurrencies that might be trending
or about to spike in growth. Scans multiple coins and ranks them by social momentum.

This script helps you discover new trading opportunities based on social signals.
"""

import asyncio
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.social_media import create_social_integration


class CryptoDiscoveryScanner:
    """Scans cryptocurrencies for potential growth based on social media signals."""
    
    def __init__(self):
        self.social_integration = create_social_integration()
        self.discovery_coins = self._get_discovery_coin_list()
        self.scan_results: List[Dict[str, Any]] = []
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def _get_discovery_coin_list(self) -> List[str]:
        """Get list of coins to scan for discovery."""
        return [
            # Major coins
            "bitcoin", "ethereum", "binancecoin", "cardano", "solana", 
            "polkadot", "chainlink", "litecoin", "bitcoin-cash", "dogecoin",
            
            # Popular altcoins
            "avalanche-2", "polygon", "cosmos", "algorand", "stellar",
            "vechain", "filecoin", "monero", "tron", "eos",
            
            # DeFi tokens
            "uniswap", "aave", "compound-governance-token", "maker", "sushi",
            "curve-dao-token", "yearn-finance", "1inch", "pancakeswap-token",
            
            # Layer 2 & Scaling
            "arbitrum", "optimism", "polygon", "loopring", "immutable-x",
            
            # Meme coins (often have high social activity)
            "shiba-inu", "dogecoin", "pepe", "floki", "bonk",
            
            # AI & Emerging sectors
            "fetch-ai", "singularitynet", "ocean-protocol", "the-graph",
            "render-token", "akash-network", "numerai",
            
            # Gaming & Metaverse
            "axie-infinity", "sandbox", "decentraland", "gala", "enjincoin",
            "illuvium", "star-atlas", "alien-worlds",
            
            # Storage & Infrastructure
            "filecoin", "arweave", "sia", "storj", "internet-computer",
            
            # Privacy coins
            "monero", "zcash", "dash", "horizen", "secret",
            
            # Stablecoins (for reference)
            "tether", "usd-coin", "binance-usd", "dai"
        ]
    
    async def scan_crypto(self, coin_id: str, debug: bool = False) -> Optional[Dict[str, Any]]:
        """Scan a single cryptocurrency for social signals."""
        try:
            # Get social signal
            social_signal = await self.social_integration.get_social_signal(coin_id)
            
            if not social_signal.get('enabled', False):
                if debug:
                    print(f"  ⚠️  {coin_id}: Social integration disabled")
                return None
            
            # Extract key metrics
            features = social_signal.get('social_features', {})
            validation = social_signal.get('validation', {})
            quality = social_signal.get('quality', {})
            
            # Calculate discovery score
            discovery_score = self._calculate_discovery_score(features, validation, quality)
            
            if debug:
                print(f"  🔍 {coin_id}: SMS={features.get('sms', 0):.3f}, "
                      f"Sentiment={features.get('weighted_sentiment', 0):.3f}, "
                      f"Score={discovery_score:.1f}")
            
            return {
                'coin_id': coin_id,
                'discovery_score': discovery_score,
                'sms': features.get('sms', 0),
                'sentiment': features.get('weighted_sentiment', 0),
                'volume_velocity': features.get('volume_velocity', 0),
                'influencer_activity': features.get('influencer_activity', 0),
                'bot_likeness': features.get('bot_likeness', 0),
                'validation_score': validation.get('validation_score', 0),
                'risk_level': validation.get('risk_level', 'unknown'),
                'quality_score': quality.get('quality_score', 0),
                'is_valid': validation.get('is_valid', False),
                'data_sources': quality.get('data_sources', []),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error scanning {coin_id}: {e}")
            return None
    
    def _calculate_discovery_score(self, features: Dict[str, Any], 
                                 validation: Dict[str, Any], 
                                 quality: Dict[str, Any]) -> float:
        """Calculate discovery score based on social signals."""
        try:
            # Base score from social momentum
            sms = features.get('sms', 0)
            sentiment = features.get('weighted_sentiment', 0)
            volume_velocity = features.get('volume_velocity', 0)
            influencer_activity = features.get('influencer_activity', 0)
            
            # Penalty for bot activity
            bot_likeness = features.get('bot_likeness', 0)
            bot_penalty = bot_likeness * 0.2  # Reduced penalty
            
            # More lenient quality multiplier
            quality_score = quality.get('quality_score', 0)
            quality_multiplier = max(0.8, quality_score)  # More lenient minimum
            
            # More lenient validation multiplier
            validation_score = validation.get('validation_score', 0)
            validation_multiplier = max(0.6, validation_score)  # More lenient minimum
            
            # Calculate weighted discovery score (more generous)
            base_score = (
                abs(sms) * 0.4 +           # Social momentum
                abs(sentiment) * 0.3 +     # Sentiment strength
                volume_velocity * 0.2 +    # Volume growth
                influencer_activity * 0.1  # Influencer activity
            )
            
            # Apply penalties and multipliers
            discovery_score = (base_score - bot_penalty) * quality_multiplier * validation_multiplier
            
            # More generous scaling to 0-100
            return min(100.0, max(0.0, discovery_score * 200))  # Doubled the multiplier
            
        except Exception as e:
            self.logger.error(f"Error calculating discovery score: {e}")
            return 0.0
    
    async def scan_all_cryptos(self, max_coins: int = 50, debug: bool = False) -> List[Dict[str, Any]]:
        """Scan multiple cryptocurrencies for discovery opportunities."""
        self.logger.info(f"🔍 Scanning {min(max_coins, len(self.discovery_coins))} cryptocurrencies for discovery opportunities...")
        
        # Limit the number of coins to scan
        coins_to_scan = self.discovery_coins[:max_coins]
        
        if debug:
            print(f"Scanning {len(coins_to_scan)} coins...")
        
        # Scan coins concurrently
        tasks = [self.scan_crypto(coin_id, debug) for coin_id in coins_to_scan]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out None results and exceptions
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.warning(f"Error scanning {coins_to_scan[i]}: {result}")
            elif result is not None:
                valid_results.append(result)
        
        # Sort by discovery score (highest first)
        valid_results.sort(key=lambda x: x['discovery_score'], reverse=True)
        
        if debug:
            print(f"Found {len(valid_results)} valid results")
            for result in valid_results[:5]:  # Show top 5
                print(f"  {result['coin_id']}: {result['discovery_score']:.1f}")
        
        self.scan_results = valid_results
        return valid_results
    
    def get_top_opportunities(self, limit: int = 10, min_score: float = 5.0) -> List[Dict[str, Any]]:
        """Get top discovery opportunities above minimum score."""
        return [
            result for result in self.scan_results 
            if result['discovery_score'] >= min_score
        ][:limit]
    
    def get_high_risk_opportunities(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get high-risk but potentially high-reward opportunities."""
        return [
            result for result in self.scan_results 
            if result['risk_level'] == 'high' and result['discovery_score'] > 10
        ][:limit]
    
    def get_safe_opportunities(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get safe, validated opportunities."""
        return [
            result for result in self.scan_results 
            if result['risk_level'] == 'low' and result['discovery_score'] > 5
        ][:limit]
    
    def print_discovery_report(self, limit: int = 15):
        """Print a comprehensive discovery report."""
        print("\n" + "="*80)
        print("🚀 CRYPTO DISCOVERY SCANNER REPORT")
        print("="*80)
        print(f"📅 Scan Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔍 Coins Scanned: {len(self.scan_results)}")
        print(f"✅ Valid Signals: {len([r for r in self.scan_results if r['is_valid']])}")
        
        # Top opportunities
        print(f"\n🏆 TOP DISCOVERY OPPORTUNITIES (Score ≥ 5)")
        print("-" * 80)
        top_opportunities = self.get_top_opportunities(limit, min_score=5.0)
        
        if not top_opportunities:
            print("No high-scoring opportunities found. Try lowering the minimum score.")
        else:
            for i, opp in enumerate(top_opportunities, 1):
                print(f"{i:2d}. {opp['coin_id'].upper():<20} | Score: {opp['discovery_score']:5.1f} | "
                      f"SMS: {opp['sms']:6.3f} | Sentiment: {opp['sentiment']:6.3f} | "
                      f"Risk: {opp['risk_level']:<6} | Valid: {opp['is_valid']}")
        
        # Safe opportunities
        print(f"\n🛡️  SAFE OPPORTUNITIES (Low Risk)")
        print("-" * 80)
        safe_opportunities = self.get_safe_opportunities(10)
        
        if not safe_opportunities:
            print("No safe opportunities found.")
        else:
            for i, opp in enumerate(safe_opportunities, 1):
                print(f"{i:2d}. {opp['coin_id'].upper():<20} | Score: {opp['discovery_score']:5.1f} | "
                      f"SMS: {opp['sms']:6.3f} | Sentiment: {opp['sentiment']:6.3f} | "
                      f"Quality: {opp['quality_score']:5.3f}")
        
        # High-risk opportunities
        print(f"\n⚠️  HIGH-RISK OPPORTUNITIES (High Risk, High Reward)")
        print("-" * 80)
        high_risk_opportunities = self.get_high_risk_opportunities(5)
        
        if not high_risk_opportunities:
            print("No high-risk opportunities found.")
        else:
            for i, opp in enumerate(high_risk_opportunities, 1):
                print(f"{i:2d}. {opp['coin_id'].upper():<20} | Score: {opp['discovery_score']:5.1f} | "
                      f"SMS: {opp['sms']:6.3f} | Sentiment: {opp['sentiment']:6.3f} | "
                      f"Bot Risk: {opp['bot_likeness']:5.3f}")
        
        # Summary statistics
        print(f"\n📊 SCAN SUMMARY")
        print("-" * 80)
        avg_score = sum(r['discovery_score'] for r in self.scan_results) / len(self.scan_results) if self.scan_results else 0
        high_sentiment = len([r for r in self.scan_results if abs(r['sentiment']) > 0.5])
        high_volume = len([r for r in self.scan_results if r['volume_velocity'] > 1.0])
        
        print(f"Average Discovery Score: {avg_score:.1f}")
        print(f"High Sentiment Coins: {high_sentiment}")
        print(f"High Volume Velocity Coins: {high_volume}")
        print(f"Validated Signals: {len([r for r in self.scan_results if r['is_valid']])}")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS")
        print("-" * 80)
        if top_opportunities:
            print("1. Research the top-scoring coins above")
            print("2. Check their fundamentals and recent news")
            print("3. Consider adding them to your trading watchlist")
            print("4. Start with small positions if trading")
        
        if safe_opportunities:
            print("5. Focus on 'Safe Opportunities' for lower-risk investments")
        
        if high_risk_opportunities:
            print("6. 'High-Risk Opportunities' may have higher rewards but require careful monitoring")
        
        print("\n⚠️  DISCLAIMER: This is for research purposes only. Always do your own research!")
        print("="*80)
    
    def export_results(self, filename: str = None) -> str:
        """Export scan results to JSON file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"crypto_discovery_scan_{timestamp}.json"
        
        import json
        
        export_data = {
            "scan_timestamp": datetime.now().isoformat(),
            "total_coins_scanned": len(self.scan_results),
            "top_opportunities": self.get_top_opportunities(20),
            "safe_opportunities": self.get_safe_opportunities(20),
            "high_risk_opportunities": self.get_high_risk_opportunities(10),
            "all_results": self.scan_results
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        return filename


async def main():
    """Main function for crypto discovery scanning."""
    print("🚀 Crypto Discovery Scanner")
    print("=" * 50)
    
    # Check if social integration is enabled
    scanner = CryptoDiscoveryScanner()
    social_status = scanner.social_integration.get_configuration_status()
    
    if not social_status['enabled']:
        print("❌ Social media integration is disabled!")
        print("💡 Enable it in config/social_media.yaml:")
        print("   enabled: true")
        print("   santiment:")
        print("     enabled: true")
        return
    
    print(f"✅ Social integration enabled")
    print(f"📡 Data sources: {social_status['enabled_sources']}")
    
    # Perform health check
    print("\n🏥 Performing health check...")
    health = await scanner.social_integration.health_check()
    print(f"Health status: {health['overall']}")
    
    if health['overall'] != 'healthy':
        print("⚠️  Some components may not be working properly")
        print("Continuing with scan anyway...")
    
    # Scan cryptocurrencies
    print(f"\n🔍 Starting crypto discovery scan...")
    results = await scanner.scan_all_cryptos(max_coins=30, debug=True)  # Start with 30 coins, debug mode
    
    if not results:
        print("❌ No results found. Check your API keys and configuration.")
        return
    
    # Print discovery report
    scanner.print_discovery_report(limit=15)
    
    # Export results
    export_file = scanner.export_results()
    print(f"\n💾 Results exported to: {export_file}")
    
    # Interactive suggestions
    print(f"\n🎯 INTERACTIVE SUGGESTIONS")
    print("-" * 50)
    
    top_opportunities = scanner.get_top_opportunities(5, min_score=5.0)
    if top_opportunities:
        print("Top coins to research:")
        for i, opp in enumerate(top_opportunities, 1):
            print(f"{i}. {opp['coin_id'].upper()} (Score: {opp['discovery_score']:.1f})")
            print(f"   - Social Momentum: {opp['sms']:.3f}")
            print(f"   - Sentiment: {opp['sentiment']:.3f}")
            print(f"   - Risk Level: {opp['risk_level']}")
            print(f"   - Validated: {opp['is_valid']}")
            print()
    
    print("💡 Next steps:")
    print("1. Research the suggested coins")
    print("2. Check their fundamentals and recent news")
    print("3. Add promising ones to your trading watchlist")
    print("4. Consider paper trading them first")
    print("5. Run this scanner regularly to find new opportunities")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Scan interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
