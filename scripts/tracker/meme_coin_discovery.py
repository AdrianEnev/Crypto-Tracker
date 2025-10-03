#!/usr/bin/env python3
"""
Meme Coin Discovery Scanner

Discovers potential meme coins using DexScreener API with configurable filters.
Includes DexScreener links for easy access to token analysis and trading data.
"""

import asyncio
import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
import aiohttp

# Add the project root directory to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.tracker.config_manager import ConfigManager


class MemeCoinScanner:
    """Working meme coin discovery scanner."""
    
    def __init__(self):
        self.base_url = "https://api.dexscreener.com/latest"
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        config_path = str(Path(__file__).parent.parent.parent / "config" / "config.yaml")
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.load_full_config()
        self.meme_config = self.config.get('meme_coin_discovery', {})
        self.filters = self.meme_config.get('meme_coin_filters', {})
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'CryptoTracker/1.0'}
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def search_tokens(self, query: str) -> List[Dict[str, Any]]:
        """Search for tokens."""
        try:
            url = f"{self.base_url}/dex/search"
            params = {'q': query}
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('pairs', [])
                else:
                    self.logger.error(f"API error: {response.status}")
                    return []
        except Exception as e:
            self.logger.error(f"Error: {e}")
            return []
    
    def check_meme_criteria(self, token: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Check if token meets meme coin criteria."""
        try:
            # Extract data
            token_info = token.get('baseToken', {})
            symbol = token_info.get('symbol', '').upper()
            name = token_info.get('name', '')
            
            price_usd = float(token.get('priceUsd', 0))
            volume_24h = float(token.get('volume', {}).get('h24', 0))
            liquidity_usd = float(token.get('liquidity', {}).get('usd', 0))
            fdv = float(token.get('fdv', 0))
            price_change_24h = float(token.get('priceChange', {}).get('h24', 0))
            
            # Get criteria from config
            min_liquidity = self.filters.get('min_liquidity_usd', 10000)
            min_volume = self.filters.get('min_volume_24h_usd', 100000)
            min_market_cap = self.filters.get('min_market_cap_usd', 100000)
            max_market_cap = self.filters.get('max_market_cap_usd', 1000000)
            min_price_change = self.filters.get('min_price_change_24h_pct', 5.0)
            
            # Check criteria
            # Create DexScreener search link
            search_query = symbol.lower()
            dexscreener_link = f"https://dexscreener.com/search?q={search_query}"
            
            criteria_results = {
                'symbol': symbol,
                'name': name,
                'price_usd': price_usd,
                'volume_24h': volume_24h,
                'liquidity_usd': liquidity_usd,
                'market_cap': fdv,
                'price_change_24h': price_change_24h,
                'dexscreener_link': dexscreener_link,
                'passed_criteria': [],
                'failed_criteria': []
            }
            
            # Check each criterion
            if liquidity_usd >= min_liquidity:
                criteria_results['passed_criteria'].append('liquidity')
            else:
                criteria_results['failed_criteria'].append('liquidity')
            
            if volume_24h >= min_volume:
                criteria_results['passed_criteria'].append('volume')
            else:
                criteria_results['failed_criteria'].append('volume')
            
            if min_market_cap <= fdv <= max_market_cap:
                criteria_results['passed_criteria'].append('market_cap')
            else:
                criteria_results['failed_criteria'].append('market_cap')
            
            if price_change_24h >= min_price_change:
                criteria_results['passed_criteria'].append('price_change')
            else:
                criteria_results['failed_criteria'].append('price_change')
            
            # Calculate scores
            pass_rate = len(criteria_results['passed_criteria']) / 4.0
            
            # Calculate potential score
            potential_score = 0.0
            if liquidity_usd > 0:
                potential_score += min(0.3, liquidity_usd / 1000000)  # Liquidity component
            if volume_24h > 0:
                potential_score += min(0.3, volume_24h / 10000000)  # Volume component
            if price_change_24h > 0:
                potential_score += min(0.2, price_change_24h / 100)  # Price change component
            if fdv > 0:
                potential_score += min(0.2, fdv / 10000000)  # Market cap component
            
            criteria_results['pass_rate'] = pass_rate
            criteria_results['potential_score'] = potential_score
            
            # Determine if it's a potential meme coin (relaxed criteria for testing)
            is_potential = pass_rate >= 0.5 and potential_score > 0.1
            
            return is_potential, criteria_results
            
        except Exception as e:
            self.logger.error(f"Error checking criteria: {e}")
            return False, {'error': str(e)}
    
    async def scan_meme_coins(self) -> List[Dict[str, Any]]:
        """Scan for potential meme coins."""
        print("🚀 Meme Coin Discovery Scanner")
        print("=" * 50)
        
        # Search terms for meme coins
        search_terms = ['dogecoin', 'shiba', 'pepe', 'floki', 'bonk', 'wif', 'cat', 'moon', 'doge', 'shib']
        
        all_tokens = []
        potential_meme_coins = []
        
        for query in search_terms:
            print(f"🔍 Searching for: {query}")
            tokens = await self.search_tokens(query)
            
            # Filter for active tokens
            active_tokens = []
            for token in tokens:
                liquidity = token.get('liquidity', {}).get('usd', 0)
                volume = token.get('volume', {}).get('h24', 0)
                price = float(token.get('priceUsd', 0))
                
                if liquidity > 1000 and volume > 10000 and price > 0:
                    active_tokens.append(token)
            
            print(f"  Found {len(active_tokens)} active tokens")
            all_tokens.extend(active_tokens)
            
            # Check criteria for each token
            for token in active_tokens:
                is_potential, criteria = self.check_meme_criteria(token)
                if is_potential:
                    criteria['scan_timestamp'] = datetime.now().isoformat()
                    criteria['source_query'] = query
                    potential_meme_coins.append(criteria)
                    print(f"  ✅ Found potential meme coin: {criteria['symbol']} "
                          f"(Pass rate: {criteria['pass_rate']:.2f}, "
                          f"Potential: {criteria['potential_score']:.2f})")
        
        # Remove duplicates
        unique_coins = []
        seen_symbols = set()
        for coin in potential_meme_coins:
            symbol = coin['symbol']
            if symbol not in seen_symbols:
                seen_symbols.add(symbol)
                unique_coins.append(coin)
        
        # Sort by potential score
        unique_coins.sort(key=lambda x: x['potential_score'], reverse=True)
        
        return unique_coins
    
    def print_results(self, results: List[Dict[str, Any]]):
        """Print scan results."""
        if not results:
            print("\n❌ No potential meme coins found.")
            print("💡 Try adjusting the filter criteria in config.yaml")
            return
        
        print(f"\n🎯 FOUND {len(results)} POTENTIAL MEME COINS")
        print("=" * 80)
        print(f"{'Rank':<4} {'Symbol':<12} {'Name':<25} {'Price':<12} {'24h Vol':<15} {'Liquidity':<15} {'Score':<8}")
        print("=" * 80)
        
        for i, coin in enumerate(results[:10], 1):
            symbol = coin['symbol'][:11]
            name = coin['name'][:24]
            price = f"${coin['price_usd']:.6f}"
            volume = f"${coin['volume_24h']:,.0f}"
            liquidity = f"${coin['liquidity_usd']:,.0f}"
            score = f"{coin['potential_score']:.2f}"
            
            print(f"{i:<4} {symbol:<12} {name:<25} {price:<12} {volume:<15} {liquidity:<15} {score:<8}")
        
        # Print DexScreener links
        print(f"\n🔗 DEXSCREENER LINKS")
        print("-" * 80)
        for i, coin in enumerate(results[:10], 1):
            print(f"{i}. {coin['symbol']}: {coin['dexscreener_link']}")
        
        # Show detailed info for top 3
        print(f"\n📊 DETAILED ANALYSIS - TOP 3")
        print("-" * 80)
        
        for i, coin in enumerate(results[:3], 1):
            print(f"\n{i}. {coin['symbol']} ({coin['name']})")
            print(f"   Price: ${coin['price_usd']:.6f}")
            print(f"   24h Volume: ${coin['volume_24h']:,.0f}")
            print(f"   Liquidity: ${coin['liquidity_usd']:,.0f}")
            print(f"   Market Cap: ${coin['market_cap']:,.0f}")
            print(f"   24h Change: {coin['price_change_24h']:+.1f}%")
            print(f"   Pass Rate: {coin['pass_rate']:.1%}")
            print(f"   Potential Score: {coin['potential_score']:.2f}")
            print(f"   Passed Criteria: {', '.join(coin['passed_criteria'])}")
            if coin['failed_criteria']:
                print(f"   Failed Criteria: {', '.join(coin['failed_criteria'])}")
            print(f"   DexScreener Link: {coin['dexscreener_link']}")
    
    def export_results(self, results: List[Dict[str, Any]]) -> str:
        """Export results to JSON."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"meme_coin_results_{timestamp}.json"
        
        export_path = Path(__file__).parent.parent / "reports" / filename
        export_path.parent.mkdir(exist_ok=True)
        
        export_data = {
            "scan_timestamp": datetime.now().isoformat(),
            "total_found": len(results),
            "results": results,
            "config_used": self.filters
        }
        
        with open(export_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        return str(export_path)


async def main():
    """Main function."""
    try:
        async with MemeCoinScanner() as scanner:
            results = await scanner.scan_meme_coins()
            scanner.print_results(results)
            
            if results:
                export_path = scanner.export_results(results)
                print(f"\n💾 Results exported to: {export_path}")
            
            print(f"\n⚠️  DISCLAIMER: This is for research purposes only!")
            print(f"🚨 Meme coins are highly volatile and risky!")
            
    except KeyboardInterrupt:
        print("\n🛑 Scan interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
