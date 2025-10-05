#!/usr/bin/env python3
"""
Simple WebSocket server test to isolate the issue
"""

import asyncio
import json
import websockets
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def handle_client(websocket, path):
    logger.info(f"Client connected: {websocket.remote_address}")
    
    try:
        async for message in websocket:
            logger.info(f"Received message: {message}")
            
            try:
                data = json.loads(message)
                message_type = data.get('type')
                
                if message_type == 'test':
                    response = {
                        'type': 'test_response',
                        'message': 'Test successful',
                        'data': data
                    }
                    await websocket.send(json.dumps(response))
                    logger.info("Sent test response")
                else:
                    response = {
                        'type': 'unknown',
                        'message': f'Unknown message type: {message_type}'
                    }
                    await websocket.send(json.dumps(response))
                    
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                error_response = {
                    'type': 'error',
                    'message': 'Invalid JSON'
                }
                await websocket.send(json.dumps(error_response))
            except Exception as e:
                logger.error(f"Message handling error: {e}")
                error_response = {
                    'type': 'error',
                    'message': f'Error: {str(e)}'
                }
                await websocket.send(json.dumps(error_response))
                
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Client disconnected: {websocket.remote_address}")
    except Exception as e:
        logger.error(f"Client error: {e}")

async def start_test_server():
    logger.info("Starting test WebSocket server on localhost:5001")
    server = await websockets.serve(handle_client, "localhost", 5001)
    logger.info("Test server started successfully")
    
    try:
        await server.wait_closed()
    except KeyboardInterrupt:
        logger.info("Stopping test server...")
        server.close()
        await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(start_test_server())
