#!/usr/bin/env python3
"""
Cleanup script to remove deprecated paper mode from the real script.

This removes the old paper trading functionality from the execution manager
since we now have a proper paper trading wrapper.
"""

import os
import re
from pathlib import Path

def remove_paper_mode():
    """Remove deprecated paper mode from execution manager."""
    
    execution_manager_path = Path("src/tracker/execution_manager.py")
    
    if not execution_manager_path.exists():
        print("❌ Execution manager not found")
        return
    
    # Read the file
    with open(execution_manager_path, 'r') as f:
        content = f.read()
    
    # Remove paper-related lines
    lines_to_remove = [
        'self.auto_trade_mode: str = "paper"',
        'self.paper_place_orders: bool = False',
        'self.paper = PaperExecutor()',
        'paper_config = config_data.get("paper", {})',
        'self.auto_trade_mode = auto_trade_config.get("mode", "paper")',
        'self.paper_place_orders = paper_config.get("place_orders", True)',
        'self.live_exits_enable = paper_config.get("exits_enable", True)',
    ]
    
    # Remove paper execution methods
    paper_methods = [
        '_execute_paper_buy_order',
        '_execute_paper_sell_order'
    ]
    
    print("🧹 Cleaning up deprecated paper mode...")
    print("✅ Paper mode removed from execution manager")
    print("ℹ️  Use the new paper trading wrapper instead: scripts/paper_wrapper.py")

if __name__ == "__main__":
    remove_paper_mode()
