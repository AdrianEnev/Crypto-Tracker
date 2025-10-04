#!/usr/bin/env python3
"""
Meme Config Generator

Generates dynamic configuration for meme coin mode by running meme_coin_discovery
and converting the results into a format compatible with the main crypto tracker.
"""

import asyncio
import json
import sys
import tempfile
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add the project root directory to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.tracker.config_manager import ConfigManager


class MemeConfigGenerator:
    """Generates meme-specific configuration by running discovery scripts."""
    
    def __init__(self, base_config_path: str):
        """Initialize the meme config generator."""
        self.base_config_path = base_config_path
        self.config_manager = ConfigManager(base_config_path)
        self.base_config = self.config_manager.load_full_config()
        self.meme_config = self.base_config.get('meme_mode', {})
        
        # Setup paths
        self.temp_dir = Path(self.meme_config.get('config', {}).get('temp_config_dir', './temp_configs'))
        self.temp_dir.mkdir(exist_ok=True)
        
        # Discovery settings
        self.discovery_config = self.meme_config.get('discovery', {})
        self.trading_config = self.meme_config.get('trading', {})
        
    async def generate_meme_config(self) -> str:
        """Generate a meme-specific configuration file."""
        try:
            print("🚀 Generating meme coin configuration...")
            
            # Run meme coin discovery
            meme_coins = await self._run_meme_discovery()
            
            if not meme_coins:
                print("❌ No meme coins found. Using fallback configuration.")
                return self._create_fallback_config()
            
            # Convert discovery results to tracked_coins format
            tracked_coins = self._convert_to_tracked_coins(meme_coins)
            
            # Create meme-specific config
            meme_config_path = self._create_meme_config_file(tracked_coins)
            
            print(f"✅ Generated meme config with {len(tracked_coins)} coins")
            print(f"📁 Config saved to: {meme_config_path}")
            
            return str(meme_config_path)
            
        except Exception as e:
            print(f"❌ Error generating meme config: {e}")
            return self._create_fallback_config()
    
    async def _run_meme_discovery(self) -> List[Dict[str, Any]]:
        """Run the meme coin discovery script."""
        try:
            print("🔍 Running meme coin discovery...")
            
            # Import and run the discovery scanner
            from scripts.tracker.meme_coin_discovery import MemeCoinScanner
            
            async with MemeCoinScanner() as scanner:
                # Run the meme coin scan
                tokens = await scanner.scan_meme_coins()
                
                if not tokens:
                    print("⚠️  No tokens found from discovery script")
                    return []
                
                print(f"📊 Found {len(tokens)} potential meme coins")
                return tokens
                
        except Exception as e:
            print(f"❌ Error running meme discovery: {e}")
            return []
    
    def _convert_to_tracked_coins(self, meme_coins: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert meme coin discovery results to tracked_coins format."""
        tracked_coins = {}
        
        max_coins = self.discovery_config.get('max_coins', 20)
        min_score = self.discovery_config.get('min_potential_score', 0.3)
        
        # Sort by potential score and take top coins
        sorted_coins = sorted(meme_coins, key=lambda x: x.get('potential_score', 0), reverse=True)
        selected_coins = [coin for coin in sorted_coins[:max_coins] if coin.get('potential_score', 0) >= min_score]
        
        for i, coin in enumerate(selected_coins):
            symbol = coin.get('symbol', f'UNKNOWN_{i}')
            name = coin.get('name', f'Unknown Coin {i}')
            price = coin.get('price_usd', 0.001)
            
            # Create coin ID (sanitized)
            coin_id = symbol.lower().replace('-', '_').replace(' ', '_')
            
            # Calculate threshold based on price and trading config
            default_threshold = self.trading_config.get('default_threshold', 0.01)
            threshold = max(price * 1.1, default_threshold)  # 10% above current price
            
            tracked_coins[coin_id] = {
                'symbol': symbol,
                'name': name,
                'threshold': threshold,
                'check_interval': self.trading_config.get('check_interval', 60),
                'disabled': False,
                'meme_mode': True,
                'discovery_data': {
                    'potential_score': coin.get('potential_score', 0),
                    'risk_score': coin.get('risk_score', 0),
                    'pass_rate': coin.get('pass_rate', 0),
                    'price_usd': coin.get('price_usd', 0),
                    'volume_24h': coin.get('volume_24h', 0),
                    'liquidity': coin.get('liquidity', 0),
                    'market_cap': coin.get('market_cap', 0),
                    'price_change_24h': coin.get('price_change_24h', 0),
                    'dex_link': coin.get('dex_link', ''),
                    'discovered_at': datetime.now().isoformat()
                }
            }
        
        return tracked_coins
    
    def _create_meme_config_file(self, tracked_coins: Dict[str, Any]) -> Path:
        """Create a meme-specific configuration file."""
        # Create a copy of the base config
        meme_config = self.base_config.copy()
        
        # Replace tracked_coins with meme coins
        meme_config['tracked_coins'] = tracked_coins
        
        # Add meme mode indicators
        meme_config['meme_mode_active'] = True
        meme_config['meme_mode_generated_at'] = datetime.now().isoformat()
        meme_config['meme_mode_source'] = 'discovery_script'
        
        # Adjust trading parameters for meme mode
        trading_config = self.meme_config.get('trading', {})
        if 'trade' not in meme_config:
            meme_config['trade'] = {}
        
        meme_config['trade']['default_size_usd'] = trading_config.get('position_size_usd', 25.0)
        meme_config['trade']['max_position_size_usd'] = trading_config.get('max_position_size_usd', 100.0)
        
        # Adjust risk parameters
        risk_multiplier = trading_config.get('risk_multiplier', 1.5)
        if 'risk' in meme_config:
            meme_config['risk']['stop_loss_pct'] *= risk_multiplier
            meme_config['risk']['take_profit_pct'] *= risk_multiplier
        
        # Create dynamic config file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        config_filename = f"dynamic_meme_config_{timestamp}.yaml"
        config_path = self.temp_dir / config_filename
        
        # Write config file
        with open(config_path, 'w') as f:
            yaml.dump(meme_config, f, default_flow_style=False, sort_keys=False)
        
        return config_path
    
    def _create_fallback_config(self) -> str:
        """Create a fallback configuration with some default meme coins."""
        print("🔄 Creating fallback meme configuration...")
        
        # Default meme coins as fallback
        fallback_coins = {
            'dogecoin': {
                'symbol': 'DOGE',
                'name': 'Dogecoin',
                'threshold': 0.1,
                'check_interval': 60,
                'disabled': False,
                'meme_mode': True
            },
            'shiba_inu': {
                'symbol': 'SHIB',
                'name': 'Shiba Inu',
                'threshold': 0.001,
                'check_interval': 60,
                'disabled': False,
                'meme_mode': True
            },
            'pepe': {
                'symbol': 'PEPE',
                'name': 'Pepe',
                'threshold': 0.00001,
                'check_interval': 60,
                'disabled': False,
                'meme_mode': True
            }
        }
        
        return self._create_meme_config_file(fallback_coins)
    
    def cleanup_temp_configs(self, keep_latest: bool = True):
        """Clean up temporary configuration files."""
        try:
            if self.meme_config.get('config', {}).get('cleanup_on_exit', True):
                config_files = list(self.temp_dir.glob("dynamic_meme_config_*.yaml"))
                
                if keep_latest and len(config_files) > 1:
                    # Keep the latest file, remove others
                    config_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                    for config_file in config_files[1:]:
                        config_file.unlink()
                    print(f"🧹 Cleaned up {len(config_files)-1} temporary config files (kept latest)")
                elif not keep_latest:
                    for config_file in config_files:
                        config_file.unlink()
                    print(f"🧹 Cleaned up {len(config_files)} temporary config files")
        except Exception as e:
            print(f"⚠️  Warning: Could not cleanup temp configs: {e}")


async def main():
    """Test the meme config generator."""
    config_path = str(Path(__file__).parent.parent / "config" / "config.yaml")
    generator = MemeConfigGenerator(config_path)
    
    try:
        meme_config_path = await generator.generate_meme_config()
        print(f"\n✅ Meme config generated successfully!")
        print(f"📁 Path: {meme_config_path}")
        
        # Show a preview of the generated config
        with open(meme_config_path, 'r') as f:
            config = yaml.safe_load(f)
            print(f"\n📊 Generated config preview:")
            print(f"  Tracked coins: {len(config.get('tracked_coins', {}))}")
            print(f"  Meme mode active: {config.get('meme_mode_active', False)}")
            print(f"  Generated at: {config.get('meme_mode_generated_at', 'Unknown')}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Cleanup
        generator.cleanup_temp_configs()


if __name__ == "__main__":
    asyncio.run(main())
