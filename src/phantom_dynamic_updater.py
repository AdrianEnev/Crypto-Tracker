#!/usr/bin/env python3
"""
Phantom Memecoin Dynamic Updater

Monitors Phantom trending memecoins and dynamically updates the trading configuration
to include new trending memecoins and remove outdated ones.
"""

import asyncio
import sys
import os
import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
import logging

# Add the project root directory to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.phantom_memecoin_monitor import PhantomMemecoinMonitor
from src.phantom_config_generator import PhantomConfigGenerator


class PhantomMemecoinDynamicUpdater:
    """Dynamically updates Phantom memecoin trading configuration."""
    
    def __init__(self, base_config_path: str, tracker):
        self.base_config_path = Path(base_config_path)
        self.tracker = tracker
        self.monitor = PhantomMemecoinMonitor()
        self.config_generator = PhantomConfigGenerator(str(base_config_path))
        
        self.logger = logging.getLogger(__name__)
        
        # Current state
        self.current_coins: Set[str] = set()
        self.current_config_path: Optional[str] = None
        self.last_update: Optional[datetime] = None
        
        # Phantom-specific settings
        self.check_interval = 30  # Check every 30 seconds
        self.max_coins = 10       # Maximum number of coins to track
        self.min_lifecycle_hours = 1  # Minimum lifecycle before removal
        self.max_lifecycle_hours = 20 # Maximum lifecycle before forced removal
        
        # Tracking data
        self.coin_lifecycle: Dict[str, datetime] = {}  # When each coin was added
        self.coin_performance: Dict[str, Dict[str, Any]] = {}  # Performance tracking
        
    def update_current_coins(self, coins: List[str]):
        """Update the current list of tracked coins."""
        self.current_coins = set(coins)
        self.logger.info(f"Updated current coins: {self.current_coins}")
    
    async def start_monitoring(self):
        """Start monitoring Phantom trending memecoins."""
        self.logger.info("🔥 Starting Phantom memecoin dynamic monitoring")
        
        while True:
            try:
                await self._check_and_update_memecoins()
                await asyncio.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                self.logger.info("🛑 Phantom monitoring stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Error in Phantom monitoring: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _check_and_update_memecoins(self):
        """Check for new trending memecoins and update configuration."""
        try:
            # Get current trending memecoins
            trending_tokens = self.monitor.fetch_trending_memecoins()
            
            if not trending_tokens:
                self.logger.warning("No trending memecoins found")
                return
            
            # Extract token names
            trending_names = {token['name'] for token in trending_tokens}
            
            # Check for new memecoins
            new_coins = trending_names - self.current_coins
            
            # Check for removed memecoins
            removed_coins = self.current_coins - trending_names
            
            # Update lifecycle tracking
            self._update_lifecycle_tracking(trending_names)
            
            # Check for coins that have exceeded maximum lifecycle
            expired_coins = self._get_expired_coins()
            
            # Determine if we need to update the configuration
            needs_update = False
            update_reason = []
            
            if new_coins:
                needs_update = True
                update_reason.append(f"New coins: {new_coins}")
            
            if removed_coins:
                needs_update = True
                update_reason.append(f"Removed coins: {removed_coins}")
            
            if expired_coins:
                needs_update = True
                update_reason.append(f"Expired coins: {expired_coins}")
            
            # Check if we need to expand beyond top 3
            if len(self.current_coins) < 3 and len(trending_tokens) >= 3:
                needs_update = True
                update_reason.append("Expanding to top 3")
            
            # Check if we need to expand beyond current count
            if len(self.current_coins) < self.max_coins and len(trending_tokens) > len(self.current_coins):
                needs_update = True
                update_reason.append(f"Expanding to {min(len(trending_tokens), self.max_coins)} coins")
            
            if needs_update:
                await self._update_configuration(trending_tokens, update_reason)
            
            # Log current status
            self._log_status(trending_tokens, new_coins, removed_coins, expired_coins)
            
        except Exception as e:
            self.logger.error(f"Error checking memecoins: {e}")
    
    def _update_lifecycle_tracking(self, trending_names: Set[str]):
        """Update lifecycle tracking for coins."""
        current_time = datetime.now()
        
        # Add new coins to lifecycle tracking
        for coin in trending_names:
            if coin not in self.coin_lifecycle:
                self.coin_lifecycle[coin] = current_time
                self.logger.info(f"🆕 New memecoin detected: {coin}")
        
        # Remove coins that are no longer trending
        for coin in list(self.coin_lifecycle.keys()):
            if coin not in trending_names:
                del self.coin_lifecycle[coin]
                if coin in self.coin_performance:
                    del self.coin_performance[coin]
    
    def _get_expired_coins(self) -> Set[str]:
        """Get coins that have exceeded maximum lifecycle."""
        current_time = datetime.now()
        expired = set()
        
        for coin, added_time in self.coin_lifecycle.items():
            lifecycle_hours = (current_time - added_time).total_seconds() / 3600
            
            if lifecycle_hours >= self.max_lifecycle_hours:
                expired.add(coin)
                self.logger.warning(f"⏰ Memecoin {coin} has exceeded maximum lifecycle ({lifecycle_hours:.1f}h)")
        
        return expired
    
    async def _update_configuration(self, trending_tokens: List[Dict[str, Any]], update_reason: List[str]):
        """Update the trading configuration with new memecoins."""
        try:
            self.logger.info(f"🔄 Updating configuration: {', '.join(update_reason)}")
            
            # Determine how many coins to track
            target_count = min(len(trending_tokens), self.max_coins)
            target_tokens = trending_tokens[:target_count]
            
            # Generate new configuration
            if not self.current_config_path:
                # First time - generate new config
                self.current_config_path = await self.config_generator.generate_phantom_config()
            else:
                # Update existing config
                self.current_config_path = self.config_generator.update_config_with_new_memecoins(
                    self.current_config_path, target_tokens
                )
            
            # Update current coins tracking
            new_coins = {token['name'] for token in target_tokens}
            self.current_coins = new_coins
            
            # Update tracker configuration
            await self._update_tracker_config()
            
            self.last_update = datetime.now()
            self.logger.info(f"✅ Configuration updated with {len(target_tokens)} memecoins")
            
        except Exception as e:
            self.logger.error(f"Error updating configuration: {e}")
    
    async def _update_tracker_config(self):
        """Update the tracker's configuration."""
        try:
            if hasattr(self.tracker, 'reload_config'):
                self.tracker.reload_config(self.current_config_path)
                self.logger.info("🔄 Tracker configuration reloaded")
            else:
                self.logger.warning("Tracker does not support config reloading")
        except Exception as e:
            self.logger.error(f"Error updating tracker config: {e}")
    
    def _log_status(self, trending_tokens: List[Dict[str, Any]], new_coins: Set[str], 
                   removed_coins: Set[str], expired_coins: Set[str]):
        """Log current status."""
        current_time = datetime.now()
        
        # Calculate lifecycle info
        lifecycle_info = []
        for coin in self.current_coins:
            if coin in self.coin_lifecycle:
                lifecycle_hours = (current_time - self.coin_lifecycle[coin]).total_seconds() / 3600
                lifecycle_info.append(f"{coin}({lifecycle_hours:.1f}h)")
        
        status_msg = f"📊 Status: {len(self.current_coins)} coins tracked"
        if lifecycle_info:
            status_msg += f" - {', '.join(lifecycle_info)}"
        
        if new_coins:
            status_msg += f" | 🆕 New: {', '.join(new_coins)}"
        
        if removed_coins:
            status_msg += f" | ❌ Removed: {', '.join(removed_coins)}"
        
        if expired_coins:
            status_msg += f" | ⏰ Expired: {', '.join(expired_coins)}"
        
        self.logger.info(status_msg)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary of tracked memecoins."""
        current_time = datetime.now()
        
        summary = {
            'total_coins_tracked': len(self.current_coins),
            'coins_by_lifecycle': {},
            'average_lifecycle_hours': 0,
            'longest_lifecycle_hours': 0,
            'shortest_lifecycle_hours': float('inf'),
        }
        
        if not self.coin_lifecycle:
            return summary
        
        lifecycles = []
        for coin, added_time in self.coin_lifecycle.items():
            lifecycle_hours = (current_time - added_time).total_seconds() / 3600
            lifecycles.append(lifecycle_hours)
            
            # Categorize by lifecycle
            if lifecycle_hours < 1:
                category = 'new'
            elif lifecycle_hours < 6:
                category = 'early'
            elif lifecycle_hours < 12:
                category = 'mid'
            elif lifecycle_hours < 20:
                category = 'late'
            else:
                category = 'expired'
            
            if category not in summary['coins_by_lifecycle']:
                summary['coins_by_lifecycle'][category] = 0
            summary['coins_by_lifecycle'][category] += 1
        
        if lifecycles:
            summary['average_lifecycle_hours'] = sum(lifecycles) / len(lifecycles)
            summary['longest_lifecycle_hours'] = max(lifecycles)
            summary['shortest_lifecycle_hours'] = min(lifecycles)
        
        return summary


async def main():
    """Test the Phantom dynamic updater."""
    from src.tracker.core import CryptoTracker
    
    # Create a mock tracker
    tracker = CryptoTracker('config/config.yaml')
    
    # Create updater
    updater = PhantomMemecoinDynamicUpdater('config/config.yaml', tracker)
    
    try:
        # Test monitoring for a short period
        print("🔥 Testing Phantom dynamic updater...")
        await asyncio.wait_for(updater.start_monitoring(), timeout=60)
        
    except asyncio.TimeoutError:
        print("✅ Test completed successfully")
        
        # Show performance summary
        summary = updater.get_performance_summary()
        print(f"📊 Performance Summary: {summary}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
