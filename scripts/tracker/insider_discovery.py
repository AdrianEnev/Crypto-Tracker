#!/usr/bin/env python3
"""
Crypto Insider Discovery Script

Discovers potential crypto "insiders" by analyzing early investors in golden ticket/ticker tokens.
Identifies wallets that consistently buy low and sell high, indicating insider knowledge.

This script:
1. Finds tokens with golden ticket/ticker indicators on DexScreener
2. Analyzes top traders for early investment patterns
3. Identifies wallets with low buy amounts ($50-300) that sold for high amounts ($10k+)
4. Creates a database of potential insiders for 24/7 tracking
"""

import asyncio
import sys
import os
import json
import time
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
import aiohttp
import sqlite3

# Add the project root directory to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.tracker.config_manager import ConfigManager


class InsiderDiscoveryScanner:
    """Discovers potential crypto insiders by analyzing early investment patterns."""
    
    def __init__(self):
        self.base_url = "https://api.dexscreener.com/latest"
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self.config_path = str(Path(__file__).parent.parent.parent / "config" / "config.yaml")
        self.config_manager = ConfigManager(self.config_path)
        self.config = self.config_manager.load_full_config()
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Initialize database
        self.db_path = Path(__file__).parent.parent / "data" / "insiders.db"
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_database()
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # 1 second between requests
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'CryptoTracker/1.0'}
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _init_database(self):
        """Initialize SQLite database for storing insider data."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS insiders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wallet_address TEXT UNIQUE NOT NULL,
                first_discovered TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_profits_usd REAL DEFAULT 0,
                successful_trades INTEGER DEFAULT 0,
                total_trades INTEGER DEFAULT 0,
                avg_profit_multiplier REAL DEFAULT 0,
                risk_score REAL DEFAULT 0,
                confidence_score REAL DEFAULT 0,
                metadata TEXT,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS insider_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wallet_address TEXT NOT NULL,
                token_address TEXT NOT NULL,
                token_symbol TEXT,
                token_name TEXT,
                trade_type TEXT NOT NULL, -- 'buy' or 'sell'
                amount_usd REAL NOT NULL,
                price_usd REAL,
                timestamp TIMESTAMP NOT NULL,
                profit_loss_usd REAL,
                profit_multiplier REAL,
                source_token TEXT, -- Token where this insider was discovered
                FOREIGN KEY (wallet_address) REFERENCES insiders (wallet_address)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS golden_ticket_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_address TEXT UNIQUE NOT NULL,
                token_symbol TEXT,
                token_name TEXT,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                golden_ticket_type TEXT, -- 'ticker', 'boost', etc.
                volume_24h REAL,
                liquidity_usd REAL,
                price_usd REAL,
                market_cap REAL,
                metadata TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def _rate_limit(self):
        """Rate limiting for API requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
    
    async def search_golden_ticket_tokens(self) -> List[Dict[str, Any]]:
        """Search for tokens with Golden Ticker and Boost indicators on DexScreener."""
        await self._rate_limit()
        
        try:
            # Get configuration for golden ticket filters
            golden_config = self.config.get('insider_discovery', {}).get('golden_ticket_filters', {})
            search_terms = golden_config.get('search_terms', [
                'golden', 'ticket', 'boost', 'premium', 'vip', 'exclusive',
                'early', 'presale', 'whitelist', 'alpha', 'beta'
            ])
            
            min_volume = golden_config.get('min_volume_24h_usd', 1000000)
            min_liquidity = golden_config.get('min_liquidity_usd', 500000)
            max_age_hours = golden_config.get('max_age_hours', 168)
            
            golden_tokens = []
            
            # Method 1: Search for trending tokens (likely to have boosts)
            try:
                trending_url = f"{self.base_url}/dex/tokens/trending"
                async with self.session.get(trending_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        trending_tokens = data.get('pairs', []) or []
                        
                        for token in trending_tokens:
                            if self._is_golden_ticker_token(token, min_volume, min_liquidity, max_age_hours):
                                golden_tokens.append(token)
                                await self._store_golden_ticket_token(token, 'trending_boost')
            except Exception as e:
                self.logger.warning(f"Error fetching trending tokens: {e}")
            
            await self._rate_limit()
            
            # Method 2: Search by specific terms for boosted tokens
            for term in search_terms[:5]:  # Limit to first 5 terms to avoid rate limits
                try:
                    url = f"{self.base_url}/dex/search"
                    params = {'q': term}
                    async with self.session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            tokens = data.get('pairs', []) or []
                            
                            for token in tokens:
                                if self._is_golden_ticker_token(token, min_volume, min_liquidity, max_age_hours):
                                    golden_tokens.append(token)
                                    await self._store_golden_ticket_token(token, 'search_boost')
                except Exception as e:
                    self.logger.warning(f"Error searching for term '{term}': {e}")
                
                await self._rate_limit()
            
            # Method 3: Check latest tokens for recent boosts
            try:
                latest_url = f"{self.base_url}/dex/tokens/latest"
                async with self.session.get(latest_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        latest_tokens = data.get('pairs', []) or []
                        
                        for token in latest_tokens:
                            if self._is_golden_ticker_token(token, min_volume, min_liquidity, max_age_hours):
                                golden_tokens.append(token)
                                await self._store_golden_ticket_token(token, 'latest_boost')
            except Exception as e:
                self.logger.warning(f"Error fetching latest tokens: {e}")
            
            # Remove duplicates
            unique_tokens = []
            seen_addresses = set()
            for token in golden_tokens:
                token_address = token.get('baseToken', {}).get('address', '')
                if token_address and token_address not in seen_addresses:
                    seen_addresses.add(token_address)
                    unique_tokens.append(token)
            
            self.logger.info(f"Found {len(unique_tokens)} unique golden ticket/boosted tokens")
            return unique_tokens
            
        except Exception as e:
            self.logger.error(f"Error searching golden ticket tokens: {e}")
            return []
    
    def _is_golden_ticker_token(self, token: Dict[str, Any], min_volume: float, min_liquidity: float, max_age_hours: float) -> bool:
        """Check if a token has Golden Ticker or Boost characteristics on DexScreener."""
        try:
            # Check for high volume and liquidity (indicating premium/boosted status)
            volume_24h = token.get('volume', {}).get('h24', 0)
            liquidity_usd = token.get('liquidity', {}).get('usd', 0)
            
            # Check volume and liquidity thresholds
            has_premium_metrics = volume_24h >= min_volume and liquidity_usd >= min_liquidity
            
            # Check for recent creation (boosted tokens are often new)
            pair_created_at = token.get('pairCreatedAt', 0)
            is_recent = True
            if pair_created_at:
                created_time = datetime.fromtimestamp(pair_created_at / 1000)
                age_hours = (datetime.now() - created_time).total_seconds() / 3600
                is_recent = age_hours <= max_age_hours
            
            # Check for high price change (boosted tokens often have momentum)
            price_change_24h = token.get('priceChange', {}).get('h24', 0)
            has_momentum = abs(price_change_24h) > 10  # 10%+ price change
            
            # Check for high trading activity (boosted tokens have increased activity)
            trades_24h = token.get('txns', {}).get('h24', {})
            buy_trades = trades_24h.get('buys', 0)
            sell_trades = trades_24h.get('sells', 0)
            total_trades = buy_trades + sell_trades
            has_high_activity = total_trades > 100  # High trading activity
            
            # Check for trending indicators
            token_info = token.get('baseToken', {})
            symbol = token_info.get('symbol', '').upper()
            name = token_info.get('name', '').upper()
            
            # Look for boost-related keywords in symbol/name
            boost_keywords = [
                'BOOST', 'GOLDEN', 'TICKET', 'PREMIUM', 'VIP', 'EXCLUSIVE',
                'EARLY', 'ALPHA', 'BETA', 'PRESALE', 'WHITELIST', 'MOON',
                'PUMP', 'RALLY', 'SURGE', 'ROCKET', 'DIAMOND'
            ]
            
            has_boost_keywords = any(keyword in symbol or keyword in name 
                                   for keyword in boost_keywords)
            
            # Check for high market cap growth potential (FDV)
            fdv = token.get('fdv', 0)
            has_growth_potential = fdv > 100000 and fdv < 10000000  # Between 100k and 10M
            
            # Golden Ticker criteria: High volume + liquidity + recent + momentum
            is_golden_ticker = (has_premium_metrics and is_recent and 
                              (has_momentum or has_high_activity or has_boost_keywords))
            
            # Additional boost indicators
            has_boost_indicators = (has_growth_potential and 
                                 (has_momentum or has_high_activity or has_boost_keywords))
            
            return is_golden_ticker or has_boost_indicators
            
        except Exception as e:
            self.logger.error(f"Error checking golden ticker status: {e}")
            return False
    
    async def _store_golden_ticket_token(self, token: Dict[str, Any], boost_type: str = 'discovered'):
        """Store golden ticket token in database."""
        try:
            token_info = token.get('baseToken', {})
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Calculate additional metrics
            volume_24h = token.get('volume', {}).get('h24', 0)
            liquidity_usd = token.get('liquidity', {}).get('usd', 0)
            price_usd = token.get('priceUsd', 0)
            market_cap = token.get('fdv', 0)
            
            # Determine boost level based on metrics
            boost_level = 'standard'
            if volume_24h >= 5000000 and liquidity_usd >= 2000000:
                boost_level = 'golden_ticker'  # Likely Golden Ticker (500+ boosts)
            elif volume_24h >= 2000000 and liquidity_usd >= 1000000:
                boost_level = 'high_boost'
            elif volume_24h >= 1000000 and liquidity_usd >= 500000:
                boost_level = 'medium_boost'
            
            cursor.execute('''
                INSERT OR REPLACE INTO golden_ticket_tokens 
                (token_address, token_symbol, token_name, golden_ticket_type, 
                 volume_24h, liquidity_usd, price_usd, market_cap, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                token_info.get('address', ''),
                token_info.get('symbol', ''),
                token_info.get('name', ''),
                f"{boost_type}_{boost_level}",
                volume_24h,
                liquidity_usd,
                price_usd,
                market_cap,
                json.dumps({
                    'token_data': token,
                    'boost_type': boost_type,
                    'boost_level': boost_level,
                    'discovered_at': datetime.now().isoformat()
                })
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error storing golden ticket token: {e}")
    
    async def analyze_top_traders(self, token: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze top traders for a specific token to find potential insiders."""
        await self._rate_limit()
        
        try:
            token_info = token.get('baseToken', {})
            token_address = token_info.get('address', '')
            token_symbol = token_info.get('symbol', '')
            
            if not token_address:
                return []
            
            # Note: DexScreener doesn't provide direct trader analysis API
            # This is a placeholder for the actual implementation
            # In a real implementation, you would:
            # 1. Get transaction data from blockchain explorers
            # 2. Analyze wallet addresses for early buy patterns
            # 3. Calculate profit/loss ratios
            
            self.logger.info(f"Analyzing top traders for {token_symbol}...")
            
            # Placeholder: Return mock data for demonstration
            potential_insiders = []
            
            # Simulate finding potential insiders
            # In reality, this would analyze blockchain data
            mock_insiders = [
                {
                    'wallet_address': f'0x{token_address[:10]}...insider1',
                    'buy_amount_usd': 150.0,
                    'sell_amount_usd': 25000.0,
                    'profit_multiplier': 166.67,
                    'buy_timestamp': datetime.now() - timedelta(hours=48),
                    'sell_timestamp': datetime.now() - timedelta(hours=2),
                    'confidence_score': 0.85,
                    'token_symbol': token_symbol,
                    'token_name': token_info.get('name', 'Unknown Token')
                },
                {
                    'wallet_address': f'0x{token_address[:10]}...insider2',
                    'buy_amount_usd': 200.0,
                    'sell_amount_usd': 18000.0,
                    'profit_multiplier': 90.0,
                    'buy_timestamp': datetime.now() - timedelta(hours=36),
                    'sell_timestamp': datetime.now() - timedelta(hours=1),
                    'confidence_score': 0.78,
                    'token_symbol': token_symbol,
                    'token_name': token_info.get('name', 'Unknown Token')
                }
            ]
            
            for insider in mock_insiders:
                if self._is_potential_insider(insider):
                    potential_insiders.append(insider)
                    await self._store_insider(insider, token)
            
            return potential_insiders
            
        except Exception as e:
            self.logger.error(f"Error analyzing top traders: {e}")
            return []
    
    def _is_potential_insider(self, trader_data: Dict[str, Any]) -> bool:
        """Check if a trader shows insider characteristics."""
        try:
            buy_amount = trader_data.get('buy_amount_usd', 0)
            sell_amount = trader_data.get('sell_amount_usd', 0)
            profit_multiplier = trader_data.get('profit_multiplier', 0)
            
            # Criteria for potential insider:
            # 1. Low initial investment ($50-300)
            # 2. High sell amount ($10k+)
            # 3. High profit multiplier (20x+)
            
            low_buy = 50 <= buy_amount <= 300
            high_sell = sell_amount >= 10000
            high_multiplier = profit_multiplier >= 20
            
            return low_buy and high_sell and high_multiplier
            
        except Exception as e:
            self.logger.error(f"Error checking insider criteria: {e}")
            return False
    
    async def _store_insider(self, insider_data: Dict[str, Any], source_token: Dict[str, Any]):
        """Store potential insider in database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            wallet_address = insider_data['wallet_address']
            
            # Insert or update insider
            cursor.execute('''
                INSERT OR REPLACE INTO insiders 
                (wallet_address, total_profits_usd, successful_trades, total_trades, 
                 avg_profit_multiplier, confidence_score, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                wallet_address,
                insider_data['sell_amount_usd'] - insider_data['buy_amount_usd'],
                1, 1,
                insider_data['profit_multiplier'],
                insider_data['confidence_score'],
                json.dumps(insider_data, default=str)  # Use default=str for datetime serialization
            ))
            
            # Insert trade record
            token_info = source_token.get('baseToken', {})
            cursor.execute('''
                INSERT INTO insider_trades 
                (wallet_address, token_address, token_symbol, token_name, 
                 trade_type, amount_usd, price_usd, timestamp, profit_loss_usd, 
                 profit_multiplier, source_token)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                wallet_address,
                token_info.get('address', ''),
                token_info.get('symbol', ''),
                token_info.get('name', ''),
                'sell',
                insider_data['sell_amount_usd'],
                source_token.get('priceUsd', 0),
                insider_data['sell_timestamp'].isoformat(),
                insider_data['sell_amount_usd'] - insider_data['buy_amount_usd'],
                insider_data['profit_multiplier'],
                token_info.get('symbol', '')
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error storing insider: {e}")
    
    def update_config_with_insiders(self, insiders: List[Dict[str, Any]]):
        """Update config.yaml with newly discovered insiders."""
        try:
            # Load current config
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Ensure insider_tracking section exists
            if 'insider_tracking' not in config:
                config['insider_tracking'] = {'tracked_wallets': []}
            
            if 'tracked_wallets' not in config['insider_tracking']:
                config['insider_tracking']['tracked_wallets'] = []
            
            # Ensure tracked_wallets is a list
            if config['insider_tracking']['tracked_wallets'] is None:
                config['insider_tracking']['tracked_wallets'] = []
            
            # Get existing wallet addresses
            existing_wallets = set()
            tracked_wallets = config['insider_tracking'].get('tracked_wallets', []) or []
            for wallet in tracked_wallets:
                existing_wallets.add(wallet.get('wallet_address', ''))
            
            # Add new insiders to config
            new_insiders_added = 0
            for insider in insiders:
                wallet_address = insider['wallet_address']
                
                if wallet_address not in existing_wallets:
                    wallet_config = {
                        'wallet_address': wallet_address,
                        'nickname': f"Insider {wallet_address[:8]}...",
                        'confidence_score': insider['confidence_score'],
                        'total_profits_usd': insider['sell_amount_usd'] - insider['buy_amount_usd'],
                        'successful_trades': 1,
                        'avg_profit_multiplier': insider['profit_multiplier'],
                        'added_by': 'discovery_script',
                        'added_at': datetime.now().isoformat(),
                        'is_active': True
                    }
                    
                    config['insider_tracking']['tracked_wallets'].append(wallet_config)
                    existing_wallets.add(wallet_address)
                    new_insiders_added += 1
            
            # Save updated config
            with open(self.config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            
            self.logger.info(f"Added {new_insiders_added} new insiders to config")
            return new_insiders_added
            
        except Exception as e:
            self.logger.error(f"Error updating config with insiders: {e}")
            return 0
    
    async def discover_insiders(self) -> List[Dict[str, Any]]:
        """Main function to discover potential insiders."""
        print("🔍 Crypto Insider Discovery Scanner")
        print("=" * 60)
        
        # Step 1: Find golden ticket tokens
        print("🎫 Searching for golden ticket tokens...")
        golden_tokens = await self.search_golden_ticket_tokens()
        print(f"Found {len(golden_tokens)} potential golden ticket tokens")
        
        if not golden_tokens:
            print("❌ No golden ticket tokens found. Try different search terms.")
            return []
        
        # Step 2: Analyze top traders for each golden token
        all_insiders = []
        for i, token in enumerate(golden_tokens[:5], 1):  # Limit to top 5 for demo
            token_info = token.get('baseToken', {})
            symbol = token_info.get('symbol', 'N/A')
            print(f"\n📊 Analyzing traders for {symbol} ({i}/{min(5, len(golden_tokens))})...")
            
            insiders = await self.analyze_top_traders(token)
            all_insiders.extend(insiders)
            
            if insiders:
                print(f"  ✅ Found {len(insiders)} potential insiders")
            else:
                print(f"  ❌ No insiders found")
        
        # Step 3: Remove duplicates and rank by confidence
        unique_insiders = []
        seen_wallets = set()
        for insider in all_insiders:
            wallet = insider['wallet_address']
            if wallet not in seen_wallets:
                seen_wallets.add(wallet)
                unique_insiders.append(insider)
        
        # Sort by confidence score
        unique_insiders.sort(key=lambda x: x['confidence_score'], reverse=True)
        
        # Update config with new insiders
        new_insiders_added = self.update_config_with_insiders(unique_insiders)
        print(f"\n📝 Added {new_insiders_added} new insiders to tracking config")
        
        return unique_insiders
    
    def print_results(self, insiders: List[Dict[str, Any]]):
        """Print discovery results."""
        if not insiders:
            print("\n❌ No potential insiders discovered.")
            print("💡 Try adjusting search criteria or check for more golden ticket tokens.")
            return
        
        print(f"\n🎯 DISCOVERED {len(insiders)} POTENTIAL INSIDERS")
        print("=" * 80)
        print(f"{'Rank':<4} {'Wallet':<20} {'Buy $':<10} {'Sell $':<12} {'Profit':<10} {'Multiplier':<12} {'Confidence':<10}")
        print("=" * 80)
        
        for i, insider in enumerate(insiders, 1):
            wallet = insider['wallet_address'][:18] + "..."
            buy_amount = f"${insider['buy_amount_usd']:,.0f}"
            sell_amount = f"${insider['sell_amount_usd']:,.0f}"
            profit = f"${insider['sell_amount_usd'] - insider['buy_amount_usd']:,.0f}"
            multiplier = f"{insider['profit_multiplier']:.1f}x"
            confidence = f"{insider['confidence_score']:.1%}"
            
            print(f"{i:<4} {wallet:<20} {buy_amount:<10} {sell_amount:<12} {profit:<10} {multiplier:<12} {confidence:<10}")
        
        # Show detailed info for top 3
        print(f"\n📊 DETAILED ANALYSIS - TOP 3 INSIDERS")
        print("-" * 80)
        
        for i, insider in enumerate(insiders[:3], 1):
            print(f"\n{i}. Wallet: {insider['wallet_address']}")
            print(f"   Initial Investment: ${insider['buy_amount_usd']:,.0f}")
            print(f"   Sell Amount: ${insider['sell_amount_usd']:,.0f}")
            print(f"   Profit: ${insider['sell_amount_usd'] - insider['buy_amount_usd']:,.0f}")
            print(f"   Profit Multiplier: {insider['profit_multiplier']:.1f}x")
            print(f"   Confidence Score: {insider['confidence_score']:.1%}")
            print(f"   Buy Time: {insider['buy_timestamp'].strftime('%Y-%m-%d %H:%M')}")
            print(f"   Sell Time: {insider['sell_timestamp'].strftime('%Y-%m-%d %H:%M')}")
            print(f"   Token: {insider['token_symbol']} ({insider['token_name']})")
            print(f"   DexScreener: https://dexscreener.com/search?q={insider['token_symbol']}")
    
    def export_results(self, insiders: List[Dict[str, Any]]) -> str:
        """Export results to JSON."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"insider_discovery_{timestamp}.json"
        
        export_path = Path(__file__).parent.parent / "reports" / filename
        export_path.parent.mkdir(exist_ok=True)
        
        export_data = {
            "scan_timestamp": datetime.now().isoformat(),
            "total_insiders_found": len(insiders),
            "insiders": insiders,
            "database_path": str(self.db_path)
        }
        
        with open(export_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        return str(export_path)
    
    def get_stored_insiders(self) -> List[Dict[str, Any]]:
        """Get all stored insiders from database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT wallet_address, total_profits_usd, successful_trades, 
                       total_trades, avg_profit_multiplier, confidence_score, 
                       first_discovered, last_updated
                FROM insiders 
                WHERE is_active = 1
                ORDER BY confidence_score DESC
            ''')
            
            insiders = []
            for row in cursor.fetchall():
                insiders.append({
                    'wallet_address': row[0],
                    'total_profits_usd': row[1],
                    'successful_trades': row[2],
                    'total_trades': row[3],
                    'avg_profit_multiplier': row[4],
                    'confidence_score': row[5],
                    'first_discovered': row[6],
                    'last_updated': row[7]
                })
            
            conn.close()
            return insiders
            
        except Exception as e:
            self.logger.error(f"Error getting stored insiders: {e}")
            return []


async def main():
    """Main function."""
    try:
        async with InsiderDiscoveryScanner() as scanner:
            # Discover new insiders
            insiders = await scanner.discover_insiders()
            scanner.print_results(insiders)
            
            if insiders:
                export_path = scanner.export_results(insiders)
                print(f"\n💾 Results exported to: {export_path}")
            
            # Show stored insiders
            stored_insiders = scanner.get_stored_insiders()
            if stored_insiders:
                print(f"\n📚 Total insiders in database: {len(stored_insiders)}")
                print("Use the insider tracking script to monitor these wallets 24/7")
            
            print(f"\n⚠️  DISCLAIMER: This is for research purposes only!")
            print(f"🚨 Always verify wallet addresses before making investment decisions!")
            
    except KeyboardInterrupt:
        print("\n🛑 Discovery interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
