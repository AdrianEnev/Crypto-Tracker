#!/usr/bin/env python3
"""
Manual Insider Wallet Manager

Allows you to manually add, remove, and manage insider wallets in the config.
This script provides a simple interface to manage the tracked wallets list.
"""

import sys
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Add the project root directory to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class InsiderWalletManager:
    """Manages insider wallets in the config file."""
    
    def __init__(self):
        self.config_path = str(Path(__file__).parent.parent.parent / "config" / "config.yaml")
    
    def load_config(self) -> Dict[str, Any]:
        """Load the current config."""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            return {}
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """Save the config."""
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            return True
        except Exception as e:
            print(f"❌ Error saving config: {e}")
            return False
    
    def get_tracked_wallets(self) -> List[Dict[str, Any]]:
        """Get all tracked wallets."""
        config = self.load_config()
        tracked_wallets = config.get('insider_tracking', {}).get('tracked_wallets', []) or []
        manual_wallets = config.get('insider_tracking', {}).get('manual_wallets', []) or []
        return tracked_wallets + manual_wallets
    
    def add_wallet(self, wallet_address: str, nickname: str = None, confidence_score: float = 0.8) -> bool:
        """Add a new wallet to track."""
        config = self.load_config()
        
        # Ensure insider_tracking section exists
        if 'insider_tracking' not in config:
            config['insider_tracking'] = {}
        
        if 'manual_wallets' not in config['insider_tracking']:
            config['insider_tracking']['manual_wallets'] = []
        
        # Ensure manual_wallets is a list
        if config['insider_tracking']['manual_wallets'] is None:
            config['insider_tracking']['manual_wallets'] = []
        
        # Check if wallet already exists
        all_wallets = self.get_tracked_wallets()
        existing_addresses = [wallet.get('wallet_address', '') for wallet in all_wallets]
        
        if wallet_address in existing_addresses:
            print(f"❌ Wallet {wallet_address} is already being tracked")
            return False
        
        # Create wallet entry
        wallet_entry = {
            'wallet_address': wallet_address,
            'nickname': nickname or f"Manual {wallet_address[:8]}...",
            'confidence_score': confidence_score,
            'total_profits_usd': 0,
            'successful_trades': 0,
            'avg_profit_multiplier': 0,
            'added_by': 'manual',
            'added_at': datetime.now().isoformat(),
            'is_active': True
        }
        
        config['insider_tracking']['manual_wallets'].append(wallet_entry)
        
        if self.save_config(config):
            print(f"✅ Added wallet: {wallet_entry['nickname']}")
            print(f"   Address: {wallet_address}")
            print(f"   Confidence: {confidence_score:.1%}")
            return True
        else:
            return False
    
    def remove_wallet(self, wallet_address: str) -> bool:
        """Remove a wallet from tracking."""
        config = self.load_config()
        
        # Remove from tracked_wallets
        tracked_wallets = config.get('insider_tracking', {}).get('tracked_wallets', [])
        config['insider_tracking']['tracked_wallets'] = [
            w for w in tracked_wallets if w.get('wallet_address') != wallet_address
        ]
        
        # Remove from manual_wallets
        manual_wallets = config.get('insider_tracking', {}).get('manual_wallets', [])
        config['insider_tracking']['manual_wallets'] = [
            w for w in manual_wallets if w.get('wallet_address') != wallet_address
        ]
        
        if self.save_config(config):
            print(f"✅ Removed wallet: {wallet_address}")
            return True
        else:
            return False
    
    def toggle_wallet_status(self, wallet_address: str) -> bool:
        """Toggle wallet active/inactive status."""
        config = self.load_config()
        
        # Find wallet in tracked_wallets
        tracked_wallets = config.get('insider_tracking', {}).get('tracked_wallets', [])
        for wallet in tracked_wallets:
            if wallet.get('wallet_address') == wallet_address:
                wallet['is_active'] = not wallet.get('is_active', True)
                if self.save_config(config):
                    status = "activated" if wallet['is_active'] else "deactivated"
                    print(f"✅ Wallet {wallet_address} {status}")
                    return True
        
        # Find wallet in manual_wallets
        manual_wallets = config.get('insider_tracking', {}).get('manual_wallets', [])
        for wallet in manual_wallets:
            if wallet.get('wallet_address') == wallet_address:
                wallet['is_active'] = not wallet.get('is_active', True)
                if self.save_config(config):
                    status = "activated" if wallet['is_active'] else "deactivated"
                    print(f"✅ Wallet {wallet_address} {status}")
                    return True
        
        print(f"❌ Wallet {wallet_address} not found")
        return False
    
    def list_wallets(self):
        """List all tracked wallets."""
        wallets = self.get_tracked_wallets()
        
        if not wallets:
            print("📝 No wallets are currently being tracked")
            return
        
        print(f"📝 Tracked Wallets ({len(wallets)} total)")
        print("=" * 80)
        print(f"{'Nickname':<20} {'Address':<20} {'Status':<8} {'Confidence':<10} {'Added By':<15}")
        print("=" * 80)
        
        for wallet in wallets:
            nickname = wallet.get('nickname', 'Unknown')[:19]
            address = wallet.get('wallet_address', 'Unknown')[:19]
            status = "Active" if wallet.get('is_active', True) else "Inactive"
            confidence = f"{wallet.get('confidence_score', 0):.1%}"
            added_by = wallet.get('added_by', 'Unknown')
            
            print(f"{nickname:<20} {address:<20} {status:<8} {confidence:<10} {added_by:<15}")
    
    def interactive_add(self):
        """Interactive wallet addition."""
        print("➕ Add New Insider Wallet")
        print("-" * 30)
        
        wallet_address = input("Enter wallet address: ").strip()
        if not wallet_address:
            print("❌ Wallet address cannot be empty")
            return
        
        nickname = input("Enter nickname (optional): ").strip()
        if not nickname:
            nickname = None
        
        try:
            confidence_input = input("Enter confidence score (0.0-1.0, default 0.8): ").strip()
            confidence_score = float(confidence_input) if confidence_input else 0.8
        except ValueError:
            confidence_score = 0.8
        
        self.add_wallet(wallet_address, nickname, confidence_score)


def main():
    """Main function."""
    manager = InsiderWalletManager()
    
    print("🔧 Insider Wallet Manager")
    print("=" * 30)
    
    while True:
        print("\nOptions:")
        print("1. List tracked wallets")
        print("2. Add wallet manually")
        print("3. Remove wallet")
        print("4. Toggle wallet status")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == '1':
            manager.list_wallets()
        
        elif choice == '2':
            manager.interactive_add()
        
        elif choice == '3':
            wallet_address = input("Enter wallet address to remove: ").strip()
            if wallet_address:
                manager.remove_wallet(wallet_address)
        
        elif choice == '4':
            wallet_address = input("Enter wallet address to toggle: ").strip()
            if wallet_address:
                manager.toggle_wallet_status(wallet_address)
        
        elif choice == '5':
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice. Please enter 1-5.")


if __name__ == "__main__":
    main()
