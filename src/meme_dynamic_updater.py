#!/usr/bin/env python3
"""
Meme Coin Dynamic Updater

Integrates with insider tracker to dynamically update meme coin list
when insiders trade new coins that aren't yet in the meme list.
"""

import asyncio
import json
import sys
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Set

# Add the project root directory to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.tracker.config_manager import ConfigManager
from src.meme_config_generator import MemeConfigGenerator


class MemeCoinDynamicUpdater:
    """Dynamically updates meme coin list based on insider trading activity."""
    
    def __init__(self, config_path: str, tracker_instance=None):
        """Initialize the dynamic updater."""
        self.config_path = config_path
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.load_full_config()
        self.meme_config = self.config.get('meme_mode', {})
        
        # Insider integration settings
        self.insider_config = self.meme_config.get('insider_integration', {})
        self.enabled = self.insider_config.get('enabled', True)
        self.update_interval = self.insider_config.get('update_interval_minutes', 5)
        self.auto_add = self.insider_config.get('auto_add_new_coins', True)
        self.min_confidence = self.insider_config.get('min_confidence_score', 0.7)
        self.max_new_coins = self.insider_config.get('max_new_coins_per_update', 5)
        
        # Current meme coins tracking
        self.current_meme_coins: Set[str] = set()
        self.last_update_time = datetime.now()
        
        # Tracker instance for updates
        self.tracker = tracker_instance
        
        # Meme generator for adding new coins
        self.meme_generator = MemeConfigGenerator(config_path)
        
    async def start_monitoring(self):
        """Start monitoring insider trades for new meme coins."""
        if not self.enabled:
            print("ℹ️  Insider integration disabled in config")
            return
        
        print("🔍 Starting insider monitoring for meme coin updates...")
        print(f"⏰ Update interval: {self.update_interval} minutes")
        print(f"🎯 Min confidence: {self.min_confidence}")
        print(f"📊 Max new coins per update: {self.max_new_coins}")
        
        try:
            # Import insider tracker
            from scripts.tracker.insider_tracker import InsiderTracker
            
            async with InsiderTracker() as insider_tracker:
                # Get initial tracked wallets
                tracked_wallets = insider_tracker.get_tracked_wallets()
                print(f"👥 Monitoring {len(tracked_wallets)} insider wallets")
                
                # Start monitoring loop
                while True:
                    try:
                        await self._check_for_new_coins(insider_tracker)
                        await asyncio.sleep(self.update_interval * 60)  # Convert minutes to seconds
                    except asyncio.CancelledError:
                        print("🛑 Insider monitoring cancelled")
                        break
                    except Exception as e:
                        print(f"⚠️  Error in monitoring loop: {e}")
                        await asyncio.sleep(60)  # Wait 1 minute before retrying
                        
        except Exception as e:
            print(f"❌ Error starting insider monitoring: {e}")
    
    async def _check_for_new_coins(self, insider_tracker):
        """Check for new coins traded by insiders."""
        try:
            # Get recent trades from insider tracker
            recent_trades = insider_tracker.get_recent_trades(hours=1)  # Last hour
            
            if not recent_trades:
                return
            
            # Extract unique token symbols from trades
            new_tokens = set()
            for trade in recent_trades:
                token_symbol = trade.get('token_symbol', '').upper()
                if token_symbol and token_symbol not in self.current_meme_coins:
                    # Check if this is a high-confidence insider trade
                    wallet_confidence = trade.get('wallet_confidence', 0)
                    profit_multiplier = trade.get('profit_multiplier', 0)
                    
                    if (wallet_confidence >= self.min_confidence and 
                        profit_multiplier >= 2.0):  # At least 2x profit
                        new_tokens.add(token_symbol)
            
            if new_tokens:
                print(f"🆕 Found {len(new_tokens)} new potential meme coins from insider trades:")
                for token in list(new_tokens)[:self.max_new_coins]:
                    print(f"  - {token}")
                
                # Add new coins to meme list
                await self._add_new_coins_to_tracker(list(new_tokens)[:self.max_new_coins])
                
        except Exception as e:
            print(f"⚠️  Error checking for new coins: {e}")
    
    async def _add_new_coins_to_tracker(self, new_tokens: List[str]):
        """Add new coins to the tracker's meme coin list."""
        try:
            if not self.tracker:
                print("⚠️  No tracker instance available for updates")
                return
            
            print(f"🔄 Adding {len(new_tokens)} new coins to meme tracker...")
            
            # Create new coin configurations
            new_coins = {}
            for i, token in enumerate(new_tokens):
                coin_id = token.lower().replace('-', '_')
                
                new_coins[coin_id] = {
                    'symbol': token,
                    'name': f'{token} (Insider Detected)',
                    'threshold': 0.01,  # Default threshold
                    'check_interval': 60,
                    'disabled': False,
                    'meme_mode': True,
                    'insider_detected': True,
                    'discovery_data': {
                        'potential_score': 0.8,  # High score for insider-detected coins
                        'risk_score': 0.3,
                        'pass_rate': 0.9,
                        'price_usd': 0.001,  # Placeholder
                        'volume_24h': 0,
                        'liquidity': 0,
                        'market_cap': 0,
                        'price_change_24h': 0,
                        'dex_link': f'https://dexscreener.com/search?q={token.lower()}',
                        'discovered_at': datetime.now().isoformat(),
                        'discovery_method': 'insider_trading'
                    }
                }
            
            # Update tracker's tracked coins
            if hasattr(self.tracker, 'config') and hasattr(self.tracker.config, 'tracked_coins'):
                # Add to existing tracked coins
                for coin_id, coin_config in new_coins.items():
                    self.tracker.config.tracked_coins[coin_id] = coin_config
                    self.current_meme_coins.add(coin_config['symbol'])
                
                print(f"✅ Added {len(new_coins)} new coins to tracker")
                
                # Log the update
                self._log_coin_addition(new_coins)
                
            else:
                print("⚠️  Tracker doesn't support dynamic coin updates")
                
        except Exception as e:
            print(f"❌ Error adding new coins: {e}")
    
    def _log_coin_addition(self, new_coins: Dict[str, Any]):
        """Log the addition of new coins."""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'action': 'coins_added',
                'count': len(new_coins),
                'coins': list(new_coins.keys()),
                'method': 'insider_detection'
            }
            
            # Save to log file
            log_path = Path(self.config_path).parent / "logs" / "meme_updates.log"
            log_path.parent.mkdir(exist_ok=True)
            
            with open(log_path, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
                
        except Exception as e:
            print(f"⚠️  Could not log coin addition: {e}")
    
    def update_current_coins(self, coin_symbols: List[str]):
        """Update the current meme coins list."""
        self.current_meme_coins = set(coin_symbols)
        print(f"📊 Updated current meme coins: {len(self.current_meme_coins)} coins")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get updater statistics."""
        return {
            'enabled': self.enabled,
            'update_interval_minutes': self.update_interval,
            'current_coins_count': len(self.current_meme_coins),
            'last_update': self.last_update_time.isoformat(),
            'auto_add_enabled': self.auto_add,
            'min_confidence': self.min_confidence,
            'max_new_coins_per_update': self.max_new_coins
        }


async def main():
    """Test the dynamic updater."""
    config_path = str(Path(__file__).parent.parent / "config" / "config.yaml")
    updater = MemeCoinDynamicUpdater(config_path)
    
    print("🧪 Testing Meme Coin Dynamic Updater")
    print("=" * 50)
    
    # Show configuration
    stats = updater.get_stats()
    print(f"📊 Configuration:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Test with some initial coins
    initial_coins = ['PEPE', 'DOGE', 'SHIB', 'FLOKI', 'BONK']
    updater.update_current_coins(initial_coins)
    
    print(f"\n✅ Dynamic updater initialized successfully!")
    print(f"💡 Run with tracker instance for full functionality")


if __name__ == "__main__":
    asyncio.run(main())
