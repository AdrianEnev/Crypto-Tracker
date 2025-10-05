#!/usr/bin/env python3
"""
Simplified WebSocket test
"""

import asyncio
import websockets
import json

async def simple_test():
    try:
        print("🔍 Testing WebSocket connection...")
        
        async with websockets.connect("ws://localhost:5001") as websocket:
            print("✅ Connected!")
            
            # Send simple message
            await websocket.send('{"type": "test", "message": "hello"}')
            print("📤 Message sent")
            
            # Just wait a bit and close
            await asyncio.sleep(1)
            print("✅ Test completed")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(simple_test())
