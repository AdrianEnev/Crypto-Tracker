#!/usr/bin/env python3
"""
Simple test for graceful shutdown fixes
"""

import asyncio
import time
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from wallet_tracker import RealWalletTracker
from rich.console import Console

console = Console()

async def test_shutdown_fixes():
    """Test the shutdown fixes"""
    
    console.print("🧪 Testing Graceful Shutdown Fixes")
    
    # Initialize tracker
    tracker = RealWalletTracker()
    
    if not tracker.phantom_enabled:
        console.print("❌ Phantom integration not enabled")
        return
    
    # Start servers
    console.print("🔄 Starting servers...")
    await tracker._start_phantom_servers()
    console.print("✅ Servers started")
    
    # Wait a moment
    await asyncio.sleep(1)
    
    # Stop servers
    console.print("🔄 Stopping servers...")
    await tracker._stop_phantom_servers()
    console.print("✅ Servers stopped")
    
    # Check ports
    import socket
    def check_port(port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result == 0
    
    ports = [5001, 5002]
    for port in ports:
        if check_port(port):
            console.print(f"❌ Port {port} still in use")
        else:
            console.print(f"✅ Port {port} is free")
    
    console.print("✅ Test completed")

if __name__ == "__main__":
    asyncio.run(test_shutdown_fixes())
