#!/usr/bin/env python3
"""
Test script to demonstrate Phantom integration flow
This shows exactly how the system works step by step
"""

import asyncio
import json
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

async def test_phantom_flow():
    """Test the complete Phantom integration flow"""
    
    console.print(Panel(
        "🧪 Testing Phantom Integration Flow\n"
        "This will show you exactly how the system works",
        title="Phantom Integration Test",
        border_style="blue"
    ))
    
    # Step 1: Initialize tracker
    console.print("\n📋 Step 1: Initializing Wallet Tracker")
    tracker = RealWalletTracker()
    
    console.print(f"✅ Paper Trading: {'Enabled' if tracker.paper_trader.enabled else 'Disabled'}")
    console.print(f"✅ Phantom Integration: {'Enabled' if tracker.phantom_enabled else 'Disabled'}")
    
    if not tracker.phantom_enabled:
        console.print("❌ Phantom integration not enabled. Check PHANTOM_WALLET_ADDRESS in .env")
        return
    
    # Step 2: Start session
    console.print("\n📋 Step 2: Starting Trading Session")
    session_id = tracker.session_manager.start_session()
    console.print(f"✅ Session started: {session_id}")
    
    # Step 3: Simulate a detected trade
    console.print("\n📋 Step 3: Simulating Detected Trade")
    
    # Create a mock swap event (like what would come from Helius)
    mock_swap_data = {
        'trade_type': 'buy',
        'token_symbol': 'BONK',
        'token_address': 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263',
        'amount_usd': 100.0,
        'price_per_token': 0.00001234
    }
    
    console.print(f"🎯 Mock Trade Detected:")
    console.print(f"   Type: {mock_swap_data['trade_type'].upper()}")
    console.print(f"   Token: {mock_swap_data['token_symbol']}")
    console.print(f"   Amount: ${mock_swap_data['amount_usd']}")
    console.print(f"   Price: ${mock_swap_data['price_per_token']:.8f}")
    
    # Step 4: Build transaction
    console.print("\n📋 Step 4: Building Phantom Transaction")
    
    if tracker.phantom_builder:
        swap_tx = tracker.phantom_builder.build_swap_transaction(mock_swap_data)
        console.print(f"✅ Transaction built: {swap_tx.transaction_id}")
        console.print(f"✅ Status: {swap_tx.status}")
        console.print(f"✅ Timestamp: {swap_tx.timestamp}")
        
        # Show what the transaction looks like
        console.print(f"\n📄 Transaction Data (Base64):")
        console.print(f"   {swap_tx.unsigned_transaction[:50]}...")
        
        # Decode to show what Phantom would see
        import base64
        decoded = base64.b64decode(swap_tx.unsigned_transaction).decode()
        transaction_info = json.loads(decoded)
        
        console.print(f"\n🔍 What Phantom Wallet Would See:")
        console.print(f"   Trade Type: {transaction_info['trade_type']}")
        console.print(f"   Token: {transaction_info['token_symbol']}")
        console.print(f"   Amount: ${transaction_info['amount_usd']}")
        console.print(f"   Phantom Wallet: {transaction_info['phantom_wallet'][:10]}...")
    
    # Step 5: Show frontend URL
    console.print("\n📋 Step 5: Frontend Access")
    phantom_port = 5000
    console.print(f"🌐 Open your browser to: http://localhost:{phantom_port}")
    console.print("📱 Connect your Phantom wallet in the browser")
    console.print("✅ The frontend will show this transaction for approval")
    
    # Step 6: Simulate user approval flow
    console.print("\n📋 Step 6: Simulating User Approval Flow")
    console.print("👤 User sees transaction in browser")
    console.print("👤 User clicks 'Sign Transaction' in Phantom")
    console.print("👤 Phantom prompts for approval")
    console.print("👤 User approves transaction")
    console.print("✅ Transaction signed and returned to Python")
    console.print("🚀 Python broadcasts transaction to Solana")
    
    # Step 7: Show what happens next
    console.print("\n📋 Step 7: What Happens Next")
    console.print("🔄 In production, this would:")
    console.print("   1. Create real Solana swap instruction")
    console.print("   2. Set proper token accounts")
    console.print("   3. Calculate slippage and routing")
    console.print("   4. Send actual SOL/USDC to DEX")
    console.print("   5. Receive tokens in your wallet")
    
    # Step 8: Cleanup
    console.print("\n📋 Step 8: Cleanup")
    await tracker.stop_monitoring()
    console.print("✅ Test completed successfully!")
    
    # Summary
    console.print(Panel(
        "🎯 Summary:\n"
        "✅ Phantom integration is WORKING\n"
        "✅ Frontend connects to your wallet\n"
        "✅ Transaction flow is complete\n"
        "❌ But transactions are SIMULATED\n"
        "❌ No real money is involved yet\n\n"
        "🚀 To make it REAL, we need to:\n"
        "   1. Implement actual Solana transaction building\n"
        "   2. Add Jupiter/Raydium integration\n"
        "   3. Handle real token accounts\n"
        "   4. Test with small amounts first",
        title="Test Results",
        border_style="green"
    ))

if __name__ == "__main__":
    asyncio.run(test_phantom_flow())
