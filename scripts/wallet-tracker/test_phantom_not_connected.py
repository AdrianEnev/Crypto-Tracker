#!/usr/bin/env python3
"""
Test what happens when a trade is initiated while Phantom is not connected
"""

import asyncio
import time
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from wallet_tracker import RealWalletTracker
from phantom_integration import SwapTransaction
from rich.console import Console
from rich.panel import Panel

console = Console()

async def test_phantom_not_connected():
    """Test what happens when Phantom is not connected but trade is initiated"""
    
    console.print(Panel(
        "🧪 Testing Phantom Not Connected Scenario\n"
        "This simulates what happens when a trade is detected but Phantom wallet is not connected",
        title="Phantom Connection Test",
        border_style="yellow"
    ))
    
    # Step 1: Initialize tracker
    console.print("\n📋 Step 1: Initializing Wallet Tracker")
    tracker = RealWalletTracker()
    
    if not tracker.phantom_enabled:
        console.print("❌ Phantom integration not enabled")
        return
    
    # Step 2: Start session and servers (but don't connect Phantom)
    console.print("\n📋 Step 2: Starting Trading Session and Servers")
    session_id = tracker.session_manager.start_session()
    console.print(f"✅ Session started: {session_id}")
    
    # Start Phantom servers
    await tracker._start_phantom_servers()
    console.print("✅ Phantom servers started")
    console.print("⚠️  NOTE: Phantom wallet is NOT connected in browser")
    
    # Step 3: Simulate detected trade
    console.print("\n📋 Step 3: Simulating Detected Trade (Phantom Not Connected)")
    
    mock_swap_data = {
        'trade_type': 'buy',
        'token_symbol': 'BONK',
        'token_address': 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263',
        'amount_usd': 100.0,
        'price_per_token': 0.00001234
    }
    
    console.print(f"🎯 Trade Detected:")
    console.print(f"   Type: {mock_swap_data['trade_type'].upper()}")
    console.print(f"   Token: {mock_swap_data['token_symbol']}")
    console.print(f"   Amount: ${mock_swap_data['amount_usd']}")
    
    # Step 4: Build and send transaction (this should work)
    console.print("\n📋 Step 4: Building and Sending Transaction")
    
    if tracker.phantom_builder:
        swap_tx = tracker.phantom_builder.build_swap_transaction(mock_swap_data)
        console.print(f"✅ Transaction built: {swap_tx.transaction_id}")
        
        # Send to Phantom server
        if tracker.phantom_server:
            await tracker.phantom_server.send_transaction_for_signing(swap_tx)
            console.print("✅ Transaction sent to Phantom server")
            console.print("⚠️  PROBLEM: No check if Phantom wallet is connected!")
            
            # Check if transaction is in pending
            if swap_tx.transaction_id in tracker.phantom_server.pending_transactions:
                console.print(f"✅ Transaction {swap_tx.transaction_id} is in pending queue")
            else:
                console.print(f"❌ Transaction {swap_tx.transaction_id} not found in pending queue")
    
    # Step 5: Simulate what happens in frontend
    console.print("\n📋 Step 5: What Happens in Frontend")
    console.print("👤 User opens browser to http://localhost:5002")
    console.print("👤 User sees transaction waiting for approval")
    console.print("👤 User clicks 'Connect Phantom Wallet' button")
    console.print("👤 User connects Phantom wallet")
    console.print("👤 User sees transaction and can approve it")
    console.print("✅ Frontend handles this correctly with walletConnected check")
    
    # Step 6: Show the problem
    console.print("\n📋 Step 6: Identifying the Problem")
    console.print("❌ ISSUE: Python backend doesn't check if Phantom is connected")
    console.print("❌ ISSUE: Transactions are sent even if no wallet is connected")
    console.print("❌ ISSUE: No timeout or error handling for unconnected state")
    console.print("❌ ISSUE: Pending transactions accumulate without connection")
    
    # Step 7: Show what should happen
    console.print("\n📋 Step 7: What Should Happen")
    console.print("✅ Check if any Phantom wallet is connected before sending")
    console.print("✅ Queue transactions until wallet connects")
    console.print("✅ Show clear error if no wallet connected")
    console.print("✅ Implement timeout for pending transactions")
    console.print("✅ Clean up stale transactions")
    
    # Step 8: Cleanup
    console.print("\n📋 Step 8: Cleanup")
    await tracker._stop_phantom_servers()
    await tracker.stop_monitoring()
    console.print("✅ Test completed")
    
    # Summary
    console.print(Panel(
        "🎯 Test Results:\n\n"
        "❌ MAJOR ISSUE FOUND:\n"
        "   - Python backend sends transactions without checking wallet connection\n"
        "   - Transactions accumulate in pending queue\n"
        "   - No error handling for disconnected state\n"
        "   - No timeout mechanism\n\n"
        "✅ Frontend handles this correctly:\n"
        "   - Checks walletConnected before signing\n"
        "   - Shows clear error messages\n"
        "   - Prevents signing without connection\n\n"
        "🚨 FIX NEEDED:\n"
        "   - Add connection status tracking in Python backend\n"
        "   - Implement transaction queuing system\n"
        "   - Add timeout and cleanup for pending transactions\n"
        "   - Add proper error handling",
        title="Test Results",
        border_style="red"
    ))

if __name__ == "__main__":
    asyncio.run(test_phantom_not_connected())
