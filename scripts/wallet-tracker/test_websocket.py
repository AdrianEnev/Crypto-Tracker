#!/usr/bin/env python3
"""
Test WebSocket server for Phantom integration
"""

import asyncio
import websockets
import json

async def test_websocket_connection():
    """Test WebSocket connection to Phantom server"""
    try:
        print("🔍 Testing WebSocket connection to ws://localhost:5001")
        
        async with websockets.connect("ws://localhost:5001") as websocket:
            print("✅ WebSocket connected successfully!")
            
            # Send a test message
            test_message = {
                "type": "test",
                "message": "Hello from test client"
            }
            
            await websocket.send(json.dumps(test_message))
            print("📤 Test message sent")
            
            # Wait for response (with timeout)
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"📨 Response received: {response}")
                
                # Try to parse the response
                try:
                    response_data = json.loads(response)
                    print(f"📋 Parsed response: {response_data}")
                except json.JSONDecodeError:
                    print("⚠️ Response is not valid JSON")
                    
            except asyncio.TimeoutError:
                print("⏰ No response received (timeout)")
            except websockets.exceptions.ConnectionClosed as e:
                print(f"🔌 Connection closed: {e.code} - {e.reason}")
            except Exception as e:
                print(f"⚠️ Error receiving response: {e}")
            
            print("✅ WebSocket test completed!")
            
    except ConnectionRefusedError:
        print("❌ WebSocket connection refused - is the wallet tracker running?")
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket_connection())
