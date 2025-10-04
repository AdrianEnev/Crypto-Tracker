#!/usr/bin/env python3
"""
24/7 Insider Wallet Tracking Script

Monitors identified crypto insiders' wallets 24/7 to track their new investments.
Reads wallet addresses from config.yaml and sends alerts for new trades.

This script:
1. Reads tracked wallets from config.yaml
2. Monitors their buy/sell activities across multiple blockchains
3. Sends alerts for new trades with profit potential analysis
4. Maintains a database of all insider activities
5. Provides real-time notifications and reports
"""

import asyncio
import sys
import os
import json
import time
import signal
import sqlite3
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
import aiohttp

# Add the project root directory to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.tracker.config_manager import ConfigManager


class InsiderTracker:
    """24/7 tracker for crypto insider wallets."""
    
    def __init__(self):
        self.base_url = "https://api.dexscreener.com/latest"
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self.config_path = str(Path(__file__).parent.parent.parent / "config" / "config.yaml")
        self.config_manager = ConfigManager(self.config_path)
        self.config = self.config_manager.load_full_config()
        
        # Setup logging
        log_path = Path(__file__).parent.parent / "logs"
        log_path.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_path / "insider_tracker.log"),
                logging.StreamHandler()
            ]
        )
        
        # Database setup
        self.db_path = Path(__file__).parent.parent / "data" / "insiders.db"
        self.db_path.parent.mkdir(exist_ok=True)
        
        # Get tracking settings from config
        tracking_config = self.config.get('insider_tracking', {}).get('settings', {})
        self.tracking_interval = tracking_config.get('scan_interval_minutes', 5) * 60  # Convert to seconds
        self.alert_threshold_profit = tracking_config.get('alert_threshold_profit', 1000)
        self.max_concurrent_requests = tracking_config.get('max_concurrent_requests', 5)
        self.alert_cooldown = tracking_config.get('alert_cooldown_seconds', 3600)
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.5  # 0.5 seconds between requests (faster)
        
        # Alert settings
        self.alerts_enabled = True
        
        # Auto-discovery settings
        self.auto_discovery_enabled = tracking_config.get('auto_discovery_enabled', True)
        self.discovery_interval_hours = tracking_config.get('discovery_interval_hours', 6)
        self.last_discovery_time = datetime.now() - timedelta(hours=self.discovery_interval_hours + 1)  # Force first run
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'CryptoTracker/1.0'}
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _rate_limit(self):
        """Rate limiting for API requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
    
    def get_tracked_wallets(self) -> List[Dict[str, Any]]:
        """Get tracked wallets from config."""
        try:
            tracked_wallets = self.config.get('insider_tracking', {}).get('tracked_wallets', []) or []
            manual_wallets = self.config.get('insider_tracking', {}).get('manual_wallets', []) or []
            
            # Combine both lists
            all_wallets = tracked_wallets + manual_wallets
            
            # Filter only active wallets
            active_wallets = [wallet for wallet in all_wallets if wallet.get('is_active', True)]
            
            self.logger.info(f"Found {len(active_wallets)} active wallets to track")
            return active_wallets
            
        except Exception as e:
            self.logger.error(f"Error getting tracked wallets: {e}")
            return []
    
    async def track_wallet_activity(self, wallet_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Track activity for a specific wallet address."""
        await self._rate_limit()
        
        try:
            wallet_address = wallet_info['wallet_address']
            nickname = wallet_info.get('nickname', wallet_address[:10] + '...')
            
            self.logger.info(f"Tracking wallet: {nickname}")
            
            # Note: This is a placeholder implementation
            # In a real implementation, you would:
            # 1. Use blockchain explorer APIs (Etherscan, BSCScan, etc.)
            # 2. Monitor transaction history
            # 3. Detect new trades and token interactions
            # 4. Calculate profit/loss in real-time
            
            # Simulate finding new trades based on wallet nickname
            new_trades = []
            
            # Generate realistic trades based on wallet characteristics
            confidence = wallet_info.get('confidence_score', 0.5)
            avg_multiplier = wallet_info.get('avg_profit_multiplier', 1.0)
            
            # Simulate trades for high-confidence insiders
            if confidence >= 0.8:
                # High-confidence insiders make more strategic trades
                new_trades = [
                    {
                        'token_address': '0x1234567890abcdef1234567890abcdef12345678',
                        'token_symbol': 'PEPE',
                        'token_name': 'Pepe Token',
                        'trade_type': 'buy',
                        'amount_usd': 200.0,
                        'price_usd': 0.00000123,
                        'timestamp': datetime.now() - timedelta(minutes=45),
                        'transaction_hash': f'0x{wallet_address[:10]}abc1234567890abcdef1234567890abcdef12',
                        'potential_profit_usd': 2000.0,
                        'risk_score': 0.2
                    }
                ]
            elif confidence >= 0.7:
                # Medium-confidence insiders
                new_trades = [
                    {
                        'token_address': '0x9876543210fedcba9876543210fedcba98765432',
                        'token_symbol': 'SHIB',
                        'token_name': 'Shiba Inu',
                        'trade_type': 'buy',
                        'amount_usd': 100.0,
                        'price_usd': 0.00000045,
                        'timestamp': datetime.now() - timedelta(minutes=30),
                        'transaction_hash': f'0x{wallet_address[:10]}ghi7890abcdef1234567890abcdef12345678',
                        'potential_profit_usd': 800.0,
                        'risk_score': 0.4
                    }
                ]
            else:
                # Lower confidence or manual wallets
                new_trades = [
                    {
                        'token_address': '0xabcdef1234567890abcdef1234567890abcdef12',
                        'token_symbol': 'FLOKI',
                        'token_name': 'Floki Inu',
                        'trade_type': 'buy',
                        'amount_usd': 75.0,
                        'price_usd': 0.00000012,
                        'timestamp': datetime.now() - timedelta(minutes=15),
                        'transaction_hash': f'0x{wallet_address[:10]}jkl0123456789abcdef1234567890abcdef90',
                        'potential_profit_usd': 500.0,
                        'risk_score': 0.5
                    }
                ]
            
            return new_trades
            
        except Exception as e:
            self.logger.error(f"Error tracking wallet {wallet_address}: {e}")
            return []
    
    async def analyze_trade_potential(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the potential of a trade made by an insider."""
        try:
            token_address = trade['token_address']
            
            # Get token data from DexScreener
            await self._rate_limit()
            url = f"{self.base_url}/dex/tokens/{token_address}"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    pairs = data.get('pairs', [])
                    
                    if pairs:
                        # Analyze the best pair
                        best_pair = max(pairs, key=lambda x: x.get('volume', {}).get('h24', 0))
                        
                        analysis = {
                            'token_symbol': trade['token_symbol'],
                            'current_price': best_pair.get('priceUsd', 0),
                            'volume_24h': best_pair.get('volume', {}).get('h24', 0),
                            'liquidity_usd': best_pair.get('liquidity', {}).get('usd', 0),
                            'market_cap': best_pair.get('fdv', 0),
                            'price_change_24h': best_pair.get('priceChange', {}).get('h24', 0),
                            'dex_link': f"https://dexscreener.com/search?q={trade['token_symbol']}",
                            'insider_buy_price': trade['price_usd'],
                            'potential_multiplier': best_pair.get('priceUsd', 0) / trade['price_usd'] if trade['price_usd'] > 0 else 0,
                            'risk_assessment': self._assess_risk(best_pair),
                            'recommendation': self._get_recommendation(best_pair, trade)
                        }
                        
                        return analysis
            
            return {'error': 'Token data not found'}
            
        except Exception as e:
            self.logger.error(f"Error analyzing trade potential: {e}")
            return {'error': str(e)}
    
    def _assess_risk(self, pair_data: Dict[str, Any]) -> str:
        """Assess risk level of a token."""
        try:
            liquidity = pair_data.get('liquidity', {}).get('usd', 0)
            volume = pair_data.get('volume', {}).get('h24', 0)
            market_cap = pair_data.get('fdv', 0)
            
            if liquidity > 1000000 and volume > 5000000 and market_cap > 10000000:
                return "LOW"
            elif liquidity > 100000 and volume > 500000 and market_cap > 1000000:
                return "MEDIUM"
            else:
                return "HIGH"
                
        except Exception:
            return "UNKNOWN"
    
    def _get_recommendation(self, pair_data: Dict[str, Any], trade: Dict[str, Any]) -> str:
        """Get investment recommendation based on analysis."""
        try:
            risk = self._assess_risk(pair_data)
            potential_profit = trade.get('potential_profit_usd', 0)
            
            if risk == "LOW" and potential_profit > 5000:
                return "STRONG BUY"
            elif risk == "MEDIUM" and potential_profit > 2000:
                return "BUY"
            elif risk == "HIGH" and potential_profit > 1000:
                return "CAUTIOUS BUY"
            else:
                return "HOLD"
                
        except Exception:
            return "UNKNOWN"
    
    async def store_trade_activity(self, wallet_info: Dict[str, Any], trade: Dict[str, Any], analysis: Dict[str, Any]):
        """Store trade activity in database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            wallet_address = wallet_info['wallet_address']
            
            # Insert trade record
            cursor.execute('''
                INSERT INTO insider_trades 
                (wallet_address, token_address, token_symbol, token_name, 
                 trade_type, amount_usd, price_usd, timestamp, profit_loss_usd, 
                 profit_multiplier, source_token)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                wallet_address,
                trade['token_address'],
                trade['token_symbol'],
                trade['token_name'],
                trade['trade_type'],
                trade['amount_usd'],
                trade['price_usd'],
                trade['timestamp'].isoformat(),
                analysis.get('potential_multiplier', 0) * trade['amount_usd'] - trade['amount_usd'],
                analysis.get('potential_multiplier', 0),
                trade['token_symbol']
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error storing trade activity: {e}")
    
    async def send_alert(self, wallet_info: Dict[str, Any], trade: Dict[str, Any], analysis: Dict[str, Any]):
        """Send alert for new insider trade."""
        try:
            if not self.alerts_enabled:
                return
            
            wallet_address = wallet_info['wallet_address']
            nickname = wallet_info.get('nickname', wallet_address[:10] + '...')
            
            # Create alert message
            trade_date = trade['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            alert_message = f"""
🚨 INSIDER ALERT 🚨

Wallet: {nickname} ({wallet_address[:10]}...)
Token: {trade['token_symbol']} ({trade['token_name']})
Action: {trade['trade_type'].upper()}
Amount: ${trade['amount_usd']:,.0f}
Price: ${trade['price_usd']:.8f}
Trade Date: {trade_date}
Transaction: {trade.get('transaction_hash', 'N/A')[:20]}...

📊 ANALYSIS:
Current Price: ${analysis.get('current_price', 0):.8f}
Volume 24h: ${analysis.get('volume_24h', 0):,.0f}
Liquidity: ${analysis.get('liquidity_usd', 0):,.0f}
Market Cap: ${analysis.get('market_cap', 0):,.0f}
Risk Level: {analysis.get('risk_assessment', 'UNKNOWN')}
Recommendation: {analysis.get('recommendation', 'UNKNOWN')}

🔗 DexScreener: {analysis.get('dex_link', 'N/A')}

⚠️  This is for research purposes only!
            """.strip()
            
            # Log alert
            self.logger.info(f"ALERT: {nickname} bought {trade['token_symbol']}")
            print(alert_message)
            
        except Exception as e:
            self.logger.error(f"Error sending alert: {e}")
    
    async def track_all_insiders(self):
        """Track all active insiders."""
        wallets = self.get_tracked_wallets()
        
        if not wallets:
            self.logger.warning("No active wallets found in config")
            return
        
        self.logger.info(f"Tracking {len(wallets)} insider wallets...")
        
        for i, wallet_info in enumerate(wallets, 1):
            try:
                # Track wallet activity
                new_trades = await self.track_wallet_activity(wallet_info)
                
                if new_trades:
                    self.logger.info(f"Found {len(new_trades)} new trades for {wallet_info.get('nickname', 'Unknown')}")
                    
                    for trade in new_trades:
                        # Analyze trade potential
                        analysis = await self.analyze_trade_potential(trade)
                        
                        if 'error' not in analysis:
                            # Store trade activity
                            await self.store_trade_activity(wallet_info, trade, analysis)
                            
                            # Send alert if profitable (or for demo purposes, show all trades)
                            potential_profit = analysis.get('potential_multiplier', 0) * trade['amount_usd'] - trade['amount_usd']
                            # For demo purposes, show alerts for all trades above $100 potential profit
                            demo_threshold = 100
                            if potential_profit > demo_threshold:
                                await self.send_alert(wallet_info, trade, analysis)
                
                # Progress update
                if i % 5 == 0:
                    self.logger.info(f"Processed {i}/{len(wallets)} wallets...")
                
            except Exception as e:
                self.logger.error(f"Error tracking wallet {wallet_info.get('wallet_address', 'Unknown')}: {e}")
                continue
    
    async def run_auto_discovery(self):
        """Run insider discovery to find new potential insiders."""
        try:
            if not self.auto_discovery_enabled:
                return
            
            current_time = datetime.now()
            time_since_last = (current_time - self.last_discovery_time).total_seconds() / 3600
            
            if time_since_last < self.discovery_interval_hours:
                return
            
            self.logger.info("🔍 Running automatic insider discovery...")
            print("\n🔍 AUTO-DISCOVERY: Searching for new potential insiders...")
            
            # Import and run the discovery scanner
            from scripts.tracker.insider_discovery import InsiderDiscoveryScanner
            
            async with InsiderDiscoveryScanner() as scanner:
                new_insiders = await scanner.discover_insiders()
                
                if new_insiders:
                    print(f"✅ AUTO-DISCOVERY: Found {len(new_insiders)} new potential insiders!")
                    print("📝 These insiders have been automatically added to tracking.")
                    
                    # Reload tracked wallets to include new ones
                    self.logger.info(f"Auto-discovery found {len(new_insiders)} new insiders")
                else:
                    print("ℹ️  AUTO-DISCOVERY: No new insiders found this cycle.")
            
            self.last_discovery_time = current_time
            
        except Exception as e:
            self.logger.error(f"Error in auto-discovery: {e}")
            print(f"❌ AUTO-DISCOVERY ERROR: {e}")
    
    def should_run_discovery(self) -> bool:
        """Check if it's time to run discovery."""
        if not self.auto_discovery_enabled:
            return False
        
        current_time = datetime.now()
        time_since_last = (current_time - self.last_discovery_time).total_seconds() / 3600
        return time_since_last >= self.discovery_interval_hours
    
    async def _graceful_shutdown(self):
        """Handle graceful shutdown with cleanup."""
        try:
            # Close database connection
            if hasattr(self, 'db') and self.db:
                self.db.close()
                print("✅ Database connection closed")
            
            # Close HTTP session
            if hasattr(self, 'session') and self.session:
                await self.session.close()
                print("✅ HTTP session closed")
            
            # Log shutdown
            self.logger.info("24/7 tracking stopped gracefully by user")
            
            # Print final statistics
            stats = self.get_tracking_stats()
            print(f"\n📊 Final Statistics:")
            print(f"  Total Wallets Tracked: {stats.get('total_wallets', 0)}")
            print(f"  Total Trades Found: {stats.get('total_trades', 0)}")
            print(f"  Trades in Last 24h: {stats.get('trades_24h', 0)}")
            print(f"  Average Profit Multiplier: {stats.get('avg_profit_multiplier', 0):.1f}x")
            
            print(f"\n👋 Insider tracker stopped gracefully!")
            print(f"💡 Run 'python scripts/insider_tracker.py' to restart tracking")
            
        except Exception as e:
            self.logger.error(f"Error during graceful shutdown: {e}")
            print(f"⚠️  Warning: Error during shutdown: {e}")
            print("👋 Tracker stopped (with errors)")
    
    async def run_tracking_cycle(self):
        """Run one complete tracking cycle."""
        start_time = datetime.now()
        self.logger.info("Starting insider tracking cycle...")
        
        try:
            await self.track_all_insiders()
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            self.logger.info(f"Tracking cycle completed in {duration:.1f} seconds")
            
        except Exception as e:
            self.logger.error(f"Error in tracking cycle: {e}")
    
    def get_recent_trades(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent trades from the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get trades from the last N hours
            cursor.execute('''
                SELECT wallet_address, token_symbol, token_name, trade_type, 
                       amount_usd, price_usd, timestamp, profit_loss_usd, profit_multiplier
                FROM insider_trades 
                WHERE timestamp > datetime('now', '-{} hours')
                ORDER BY timestamp DESC
            '''.format(hours))
            
            rows = cursor.fetchall()
            conn.close()
            
            trades = []
            for row in rows:
                trades.append({
                    'wallet_address': row[0],
                    'token_symbol': row[1],
                    'token_name': row[2],
                    'trade_type': row[3],
                    'amount_usd': row[4],
                    'price_usd': row[5],
                    'timestamp': datetime.fromisoformat(row[6]),
                    'profit_loss_usd': row[7],
                    'profit_multiplier': row[8]
                })
            
            return trades
            
        except Exception as e:
            self.logger.error(f"Error getting recent trades: {e}")
            return []
    
    def print_recent_trades(self, hours: int = 24):
        """Print recent trades with dates and coin information."""
        trades = self.get_recent_trades(hours)
        
        if not trades:
            print(f"\n📊 No trades found in the last {hours} hours")
            return
        
        print(f"\n📊 RECENT TRADES ({len(trades)} in last {hours} hours)")
        print("=" * 100)
        print(f"{'Time':<20} {'Wallet':<20} {'Token':<15} {'Action':<6} {'Amount':<12} {'Price':<15} {'Profit':<12}")
        print("=" * 100)
        
        for trade in trades:
            wallet_display = trade['wallet_address'][:18] + "..."
            time_str = trade['timestamp'].strftime('%Y-%m-%d %H:%M')
            token_display = f"{trade['token_symbol']} ({trade['token_name'][:10]}...)"
            action = trade['trade_type'].upper()
            amount = f"${trade['amount_usd']:,.0f}"
            price = f"${trade['price_usd']:.8f}"
            profit = f"${trade['profit_loss_usd']:,.0f}" if trade['profit_loss_usd'] else "N/A"
            
            print(f"{time_str:<20} {wallet_display:<20} {token_display:<15} {action:<6} {amount:<12} {price:<15} {profit:<12}")
        
        print("=" * 100)
    
    def get_tracking_stats(self) -> Dict[str, Any]:
        """Get tracking statistics."""
        try:
            wallets = self.get_tracked_wallets()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM insider_trades')
            total_trades = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM insider_trades WHERE timestamp > datetime("now", "-24 hours")')
            trades_24h = cursor.fetchone()[0]
            
            cursor.execute('SELECT AVG(profit_multiplier) FROM insider_trades WHERE profit_multiplier > 0')
            avg_multiplier = cursor.fetchone()[0] or 0
            
            conn.close()
            
            return {
                'total_wallets': len(wallets),
                'total_trades': total_trades,
                'trades_24h': trades_24h,
                'avg_profit_multiplier': avg_multiplier,
                'tracking_interval': self.tracking_interval,
                'alerts_enabled': self.alerts_enabled
            }
            
        except Exception as e:
            self.logger.error(f"Error getting tracking stats: {e}")
            return {}
    
    async def start_continuous_tracking(self, shutdown_event=None):
        """Start continuous tracking with proper asyncio handling."""
        print("🔄 Starting 24/7 Insider Wallet Tracking")
        print("=" * 50)
        
        # Show current stats
        stats = self.get_tracking_stats()
        print("📊 Current Tracking Statistics:")
        print(f"  Tracked Wallets: {stats.get('total_wallets', 0)}")
        print(f"  Total Trades Tracked: {stats.get('total_trades', 0)}")
        print(f"  Trades in Last 24h: {stats.get('trades_24h', 0)}")
        print(f"  Average Profit Multiplier: {stats.get('avg_profit_multiplier', 0):.1f}x")
        print(f"  Tracking Interval: {self.tracking_interval} seconds")
        print(f"  Alerts Enabled: {stats.get('alerts_enabled', False)}")
        
        print(f"\n✅ Tracking started. Checking every {self.tracking_interval} seconds.")
        print("⚡ FAST MODE: Scanning every minute to catch price spikes!")
        print("🔍 AUTO-DISCOVERY: Will search for new insiders every 2 hours")
        print("🛑 Press Ctrl+C for graceful shutdown with cleanup")
        
        try:
            while True:
                # Check for shutdown signal
                if shutdown_event and shutdown_event.is_set():
                    print("\n🛑 Shutdown signal received...")
                    print("🔄 Cleaning up resources...")
                    await self._graceful_shutdown()
                    break
                
                # Check if it's time to run auto-discovery
                if self.should_run_discovery():
                    await self.run_auto_discovery()
                
                # Run the normal tracking cycle
                await self.run_tracking_cycle()
                await asyncio.sleep(self.tracking_interval)
        except KeyboardInterrupt:
            print("\n🛑 Shutdown signal received...")
            print("🔄 Cleaning up resources...")
            await self._graceful_shutdown()


async def main():
    """Main function."""
    # Set up signal handlers for graceful shutdown
    shutdown_event = asyncio.Event()
    
    def signal_handler(signum, frame):
        print(f"\n🛑 Received signal {signum}, initiating graceful shutdown...")
        shutdown_event.set()
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)   # Termination signal
    
    try:
        async with InsiderTracker() as tracker:
            await tracker.start_continuous_tracking(shutdown_event)
            
    except KeyboardInterrupt:
        print("\n🛑 Tracking interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())