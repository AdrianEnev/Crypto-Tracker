#!/usr/bin/env python3
"""
Phantom Config Generator

Generates trading configurations specifically optimized for Phantom memecoins.
These configurations are designed for ultra-fast volatile trading with no historical data.
"""

import asyncio
import sys
import os
import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging

# Add the project root directory to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.phantom_memecoin_monitor import PhantomMemecoinMonitor


class PhantomConfigGenerator:
    """Generates Phantom-specific trading configurations for memecoins."""
    
    def __init__(self, base_config_path: str):
        self.base_config_path = Path(base_config_path)
        self.monitor = PhantomMemecoinMonitor()
        self.logger = logging.getLogger(__name__)
        
        # Phantom-specific trading parameters
        self.phantom_config = {
            'max_lifecycle_hours': 20,  # Maximum trading duration per memecoin
            'check_interval': 10,       # Check every 10 seconds for changes
            'volatile_strategy': True,  # Enable volatile-based trading
            'no_historical_data': True, # Disable historical analysis
            'aggressive_entry': True,   # Aggressive entry strategies
            'fast_exit': True,          # Fast exit strategies
            'position_sizing': 'dynamic', # Dynamic position sizing based on volatility
            'risk_multiplier': 2.0,     # Higher risk tolerance for memecoins
        }
    
    async def generate_phantom_config(self) -> str:
        """Generate a Phantom-specific configuration file."""
        try:
            # Get current trending memecoins
            trending_tokens = self.monitor.fetch_trending_memecoins()
            
            if not trending_tokens:
                raise Exception("No trending memecoins found")
            
            # Take top 3 memecoins initially
            top_memecoins = trending_tokens[:3]
            
            # Load base configuration
            with open(self.base_config_path, 'r') as f:
                base_config = yaml.safe_load(f) or {}
            
            # Create Phantom-specific configuration
            phantom_config = self._create_phantom_config(base_config, top_memecoins)
            
            # Save configuration
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            config_filename = f"phantom_config_{timestamp}.yaml"
            config_path = self.base_config_path.parent / config_filename
            
            with open(config_path, 'w') as f:
                yaml.dump(phantom_config, f, default_flow_style=False, sort_keys=False)
            
            self.logger.info(f"Phantom configuration generated: {config_path}")
            return str(config_path)
            
        except Exception as e:
            self.logger.error(f"Error generating Phantom config: {e}")
            raise
    
    def _create_phantom_config(self, base_config: Dict[str, Any], memecoins: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create Phantom-specific configuration from base config and memecoins."""
        
        # Start with base configuration
        phantom_config = base_config.copy()
        
        # Remove default tracked_coins (we'll replace with Phantom memecoins)
        phantom_config.pop('tracked_coins', None)
        
        # Add Phantom-specific settings
        phantom_config['phantom_mode'] = {
            'enabled': True,
            'max_lifecycle_hours': self.phantom_config['max_lifecycle_hours'],
            'check_interval': self.phantom_config['check_interval'],
            'volatile_strategy': self.phantom_config['volatile_strategy'],
            'no_historical_data': self.phantom_config['no_historical_data'],
            'aggressive_entry': self.phantom_config['aggressive_entry'],
            'fast_exit': self.phantom_config['fast_exit'],
            'position_sizing': self.phantom_config['position_sizing'],
            'risk_multiplier': self.phantom_config['risk_multiplier'],
            'generated_at': datetime.now().isoformat(),
            'source': 'phantom_trending'
        }
        
        # Create tracked_coins section with Phantom memecoins
        tracked_coins = {}
        
        for i, token in enumerate(memecoins, 1):
            coin_id = token['name'].lower().replace(' ', '-').replace('$', '')
            
            tracked_coins[coin_id] = {
                'symbol': token['name'],
                'name': token['name'],
                'threshold': 0.001,  # Very low threshold for memecoins
                'check_interval': 10,  # Check every 10 seconds
                'phantom_mode': True,
                'discovered_at': datetime.now().isoformat(),
                'trending_rank': i,
                'initial_price': token.get('price', 0.001),
                'initial_change': token.get('change_24h', 0),
                
                # Volatile-based strategy configuration
                'strategy': {
                    'name': 'volatile_memecoin',
                    'params': {
                        'volatility_threshold': 0.05,  # 5% volatility threshold
                        'momentum_window': 5,          # 5-minute momentum window
                        'entry_aggression': 0.8,       # 80% aggression on entry signals
                        'exit_speed': 0.9,             # 90% speed on exit signals
                        'max_position_size': 0.1,     # Max 0.1 SOL per position
                        'stop_loss_pct': 0.3,         # 30% stop loss
                        'take_profit_pct': 2.0,       # 200% take profit
                        'trailing_stop': True,        # Enable trailing stop
                        'trailing_distance': 0.15,   # 15% trailing distance
                    }
                },
                
                # Risk management for memecoins
                'risk': {
                    'max_position_pct': 0.05,         # Max 5% of portfolio per memecoin
                    'max_daily_loss_pct': 0.1,       # Max 10% daily loss
                    'volatility_multiplier': 2.0,    # 2x volatility multiplier
                    'liquidity_check': True,         # Check liquidity before trading
                    'min_liquidity': 1000,           # Minimum $1000 liquidity
                },
                
                # Market configuration (Solana-based)
                'market': f"{token['name']}/SOL",
                'exchange': 'raydium',  # Use Raydium for Solana memecoins
                'chain': 'solana',
                
                # Disable historical analysis
                'historical_analysis': False,
                'backtest_period': 0,  # No backtesting for memecoins
                'technical_indicators': {
                    'enabled': False,  # Disable traditional technical analysis
                    'rsi': False,
                    'macd': False,
                    'bollinger_bands': False,
                },
                
                # Enable only volatility-based indicators
                'volatility_indicators': {
                    'enabled': True,
                    'price_velocity': True,      # Rate of price change
                    'volume_spike': True,        # Volume spike detection
                    'momentum_shift': True,     # Momentum shift detection
                    'trending_strength': True,  # Trending strength
                },
                
                # Fast execution settings
                'execution': {
                    'priority_fee': 'high',      # High priority for fast execution
                    'slippage_tolerance': 0.05, # 5% slippage tolerance
                    'max_gas_price': 0.001,     # Max gas price
                    'retry_attempts': 3,        # Retry failed transactions
                    'timeout_seconds': 30,      # 30-second timeout
                },
                
                # Notification settings
                'notifications': {
                    'entry': True,
                    'exit': True,
                    'stop_loss': True,
                    'take_profit': True,
                    'trending_change': True,
                    'volume_spike': True,
                },
                
                'disabled': False,
                'added_by': 'phantom_generator',
                'added_at': datetime.now().isoformat(),
            }
        
        phantom_config['tracked_coins'] = tracked_coins
        
        # Update global settings for Phantom mode
        if 'global_settings' not in phantom_config:
            phantom_config['global_settings'] = {}
        
        phantom_config['global_settings'].update({
            'phantom_mode': True,
            'max_concurrent_positions': 5,      # Max 5 concurrent memecoin positions
            'portfolio_allocation': 0.2,        # 20% of portfolio for memecoins
            'daily_loss_limit': 0.15,          # 15% daily loss limit
            'position_size_base': 0.05,        # Base position size (5% of allocation)
            'volatility_scaling': True,        # Scale position size by volatility
        })
        
        return phantom_config
    
    def update_config_with_new_memecoins(self, config_path: str, new_memecoins: List[Dict[str, Any]]) -> str:
        """Update existing Phantom config with new memecoins."""
        try:
            # Load existing config
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f) or {}
            
            # Add new memecoins to tracked_coins
            tracked_coins = config.get('tracked_coins', {})
            
            for token in new_memecoins:
                coin_id = token['name'].lower().replace(' ', '-').replace('$', '')
                
                # Skip if already tracked
                if coin_id in tracked_coins:
                    continue
                
                # Add new memecoin with same configuration as others
                tracked_coins[coin_id] = self._create_memecoin_config(token, len(tracked_coins) + 1)
            
            config['tracked_coins'] = tracked_coins
            
            # Save updated config
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            
            self.logger.info(f"Updated Phantom config with {len(new_memecoins)} new memecoins")
            return config_path
            
        except Exception as e:
            self.logger.error(f"Error updating Phantom config: {e}")
            raise
    
    def _create_memecoin_config(self, token: Dict[str, Any], rank: int) -> Dict[str, Any]:
        """Create configuration for a single memecoin."""
        return {
            'symbol': token['name'],
            'name': token['name'],
            'threshold': 0.001,
            'check_interval': 10,
            'phantom_mode': True,
            'discovered_at': datetime.now().isoformat(),
            'trending_rank': rank,
            'initial_price': token.get('price', 0.001),
            'initial_change': token.get('change_24h', 0),
            
            'strategy': {
                'name': 'volatile_memecoin',
                'params': {
                    'volatility_threshold': 0.05,
                    'momentum_window': 5,
                    'entry_aggression': 0.8,
                    'exit_speed': 0.9,
                    'max_position_size': 0.1,
                    'stop_loss_pct': 0.3,
                    'take_profit_pct': 2.0,
                    'trailing_stop': True,
                    'trailing_distance': 0.15,
                }
            },
            
            'risk': {
                'max_position_pct': 0.05,
                'max_daily_loss_pct': 0.1,
                'volatility_multiplier': 2.0,
                'liquidity_check': True,
                'min_liquidity': 1000,
            },
            
            'market': f"{token['name']}/SOL",
            'exchange': 'raydium',
            'chain': 'solana',
            
            'historical_analysis': False,
            'backtest_period': 0,
            'technical_indicators': {
                'enabled': False,
                'rsi': False,
                'macd': False,
                'bollinger_bands': False,
            },
            
            'volatility_indicators': {
                'enabled': True,
                'price_velocity': True,
                'volume_spike': True,
                'momentum_shift': True,
                'trending_strength': True,
            },
            
            'execution': {
                'priority_fee': 'high',
                'slippage_tolerance': 0.05,
                'max_gas_price': 0.001,
                'retry_attempts': 3,
                'timeout_seconds': 30,
            },
            
            'notifications': {
                'entry': True,
                'exit': True,
                'stop_loss': True,
                'take_profit': True,
                'trending_change': True,
                'volume_spike': True,
            },
            
            'disabled': False,
            'added_by': 'phantom_generator',
            'added_at': datetime.now().isoformat(),
        }


async def main():
    """Test the Phantom config generator."""
    generator = PhantomConfigGenerator('config/config.yaml')
    
    try:
        config_path = await generator.generate_phantom_config()
        print(f"✅ Phantom configuration generated: {config_path}")
        
        # Test updating with new memecoins
        new_memecoins = [
            {'name': 'TESTCOIN', 'price': 0.001, 'change_24h': 50.0},
            {'name': 'NEWMEME', 'price': 0.002, 'change_24h': 100.0}
        ]
        
        updated_path = generator.update_config_with_new_memecoins(config_path, new_memecoins)
        print(f"✅ Configuration updated: {updated_path}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
