"""
Phantom Wallet Integration

This module handles building Solana transactions for Phantom wallet signing
and managing the communication between Python backend and web frontend.
"""

import asyncio
import base64
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
import aiohttp
import websockets
from dataclasses import dataclass

from rich.console import Console

console = Console()

@dataclass
class SwapTransaction:
    """Represents a swap transaction for Phantom signing"""
    transaction_id: str
    trade_type: str  # 'buy' or 'sell'
    token_symbol: str
    token_address: str
    amount_usd: float
    price_per_token: float
    unsigned_transaction: str  # base64 encoded
    timestamp: datetime
    status: str  # 'pending', 'signed', 'broadcast', 'confirmed', 'failed'

class PhantomTransactionBuilder:
    """Builds Solana transactions for Phantom wallet signing"""
    
    def __init__(self, rpc_client, phantom_wallet_address: str):
        self.rpc_client = rpc_client
        self.phantom_wallet = phantom_wallet_address
        self.logger = logging.getLogger(__name__)
        
        # Known DEX program IDs
        self.dex_programs = {
            "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": "Raydium",
            "JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB": "Jupiter",
            "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM": "Orca",
            "9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin": "Serum",
        }
        
        # Known token addresses
        self.known_tokens = {
            "So11111111111111111111111111111111111111112": "SOL",
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC",
            "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": "USDT",
            "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So": "mSOL",
            "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs": "ETH",
        }
    
    def build_swap_transaction(self, trade_data: dict) -> SwapTransaction:
        """Build unsigned swap transaction for Phantom signing"""
        try:
            transaction_id = str(uuid.uuid4())
            
            # Extract trade information
            trade_type = trade_data.get('trade_type', '').lower()
            token_symbol = trade_data.get('token_symbol', 'UNKNOWN')
            token_address = trade_data.get('token_address', '')
            amount_usd = trade_data.get('amount_usd', 0.0)
            price_per_token = trade_data.get('price_per_token', 0.0)
            
            # For now, create a simple transfer transaction as placeholder
            # In production, this would build actual swap instructions
            unsigned_tx = self._create_placeholder_transaction(
                trade_type, token_symbol, token_address, amount_usd, price_per_token
            )
            
            swap_tx = SwapTransaction(
                transaction_id=transaction_id,
                trade_type=trade_type,
                token_symbol=token_symbol,
                token_address=token_address,
                amount_usd=amount_usd,
                price_per_token=price_per_token,
                unsigned_transaction=unsigned_tx,
                timestamp=datetime.now(timezone.utc),
                status='pending'
            )
            
            self.logger.info(f"Built swap transaction {transaction_id} for {token_symbol}")
            return swap_tx
            
        except Exception as e:
            self.logger.error(f"Failed to build swap transaction: {e}")
            raise
    
    def _create_placeholder_transaction(self, trade_type: str, token_symbol: str, 
                                      token_address: str, amount_usd: float, 
                                      price_per_token: float) -> str:
        """Create a placeholder transaction (replace with actual Solana transaction building)"""
        try:
            # This is a placeholder - in production, you would:
            # 1. Create actual Solana transaction with swap instructions
            # 2. Set fee payer to phantom wallet
            # 3. Get recent blockhash
            # 4. Serialize to base64
            
            transaction_data = {
                "type": "swap",
                "trade_type": trade_type,
                "token_symbol": token_symbol,
                "token_address": token_address,
                "amount_usd": amount_usd,
                "price_per_token": price_per_token,
                "phantom_wallet": self.phantom_wallet,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Encode as base64 for frontend
            json_str = json.dumps(transaction_data)
            base64_tx = base64.b64encode(json_str.encode()).decode()
            
            return base64_tx
            
        except Exception as e:
            self.logger.error(f"Failed to create placeholder transaction: {e}")
            raise
    
    async def broadcast_signed_transaction(self, signed_tx_b64: str) -> Optional[str]:
        """Broadcast signed transaction to Solana network"""
        try:
            # Decode base64 transaction
            signed_bytes = base64.b64decode(signed_tx_b64)
            
            # In production, this would:
            # 1. Deserialize the signed transaction
            # 2. Send to Solana RPC
            # 3. Return transaction signature
            
            # For now, simulate successful broadcast
            tx_signature = f"simulated_tx_{uuid.uuid4().hex[:8]}"
            
            self.logger.info(f"Broadcasted transaction: {tx_signature}")
            return tx_signature
            
        except Exception as e:
            self.logger.error(f"Failed to broadcast transaction: {e}")
            return None

class PhantomServer:
    """Flask server for Phantom wallet integration"""
    
    def __init__(self, wallet_tracker, port: int = 5001):
        self.wallet_tracker = wallet_tracker
        self.port = port
        self.pending_transactions: Dict[str, SwapTransaction] = {}
        self.logger = logging.getLogger(__name__)
        self.server_task = None
        
        # Connection status tracking
        self.phantom_connected = False
        self.connected_wallet_address = None
        self.connection_time = None
        self.max_pending_transactions = 10  # Limit pending transactions
        self.transaction_timeout_minutes = 5  # Timeout for pending transactions
        
    async def start_server(self):
        """Start the Phantom integration server"""
        try:
            self.logger.info(f"Starting Phantom server on port {self.port}")
            
            # Start WebSocket server for real-time communication
            self.server_task = asyncio.create_task(
                self._start_websocket_server()
            )
            
            self.logger.info("✅ Phantom server started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start Phantom server: {e}")
            raise
    
    async def _start_websocket_server(self):
        """Start WebSocket server for real-time communication"""
        try:
            async def handle_client(websocket, path):
                self.logger.info(f"Client connected: {websocket.remote_address}")
                
                try:
                    async for message in websocket:
                        try:
                            await self._handle_websocket_message(websocket, message)
                        except Exception as e:
                            self.logger.error(f"Error handling message: {e}")
                            # Send error response to client
                            error_response = {
                                'type': 'error',
                                'message': f'Error processing message: {str(e)}'
                            }
                            try:
                                await websocket.send(json.dumps(error_response))
                            except:
                                pass
                            
                except websockets.exceptions.ConnectionClosed:
                    self.logger.info(f"Client disconnected: {websocket.remote_address}")
                except Exception as e:
                    self.logger.error(f"WebSocket client error: {e}")
            
            server = await websockets.serve(handle_client, "localhost", self.port)
            self.logger.info(f"WebSocket server listening on localhost:{self.port}")
            await server.wait_closed()
            
        except Exception as e:
            self.logger.error(f"WebSocket server error: {e}")
            raise
    
    async def _handle_websocket_message(self, websocket, message: str):
        """Handle incoming WebSocket messages"""
        try:
            self.logger.info(f"Received WebSocket message: {message}")
            data = json.loads(message)
            message_type = data.get('type')
            
            self.logger.info(f"Processing message type: {message_type}")
            
            if message_type == 'test':
                await self._handle_test_message(websocket, data)
            elif message_type == 'phantom_connected':
                await self._handle_phantom_connected(websocket, data)
            elif message_type == 'phantom_disconnected':
                await self._handle_phantom_disconnected(websocket, data)
            elif message_type == 'sign_transaction':
                await self._handle_sign_request(websocket, data)
            elif message_type == 'transaction_signed':
                await self._handle_signed_transaction(websocket, data)
            elif message_type == 'transaction_rejected':
                await self._handle_rejected_transaction(websocket, data)
            else:
                self.logger.warning(f"Unknown message type: {message_type}")
                # Send unknown message type response
                response = {
                    'type': 'unknown_message',
                    'message': f'Unknown message type: {message_type}'
                }
                await websocket.send(json.dumps(response))
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON message: {e}")
            error_response = {
                'type': 'error',
                'message': 'Invalid JSON message'
            }
            await websocket.send(json.dumps(error_response))
        except Exception as e:
            self.logger.error(f"Failed to handle WebSocket message: {e}")
            error_response = {
                'type': 'error',
                'message': f'Message handling error: {str(e)}'
            }
            await websocket.send(json.dumps(error_response))
    
    async def _handle_phantom_connected(self, websocket, data: dict):
        """Handle Phantom wallet connection"""
        try:
            wallet_address = data.get('wallet_address')
            self.phantom_connected = True
            self.connected_wallet_address = wallet_address
            self.connection_time = datetime.now(timezone.utc)
            
            self.logger.info(f"Phantom wallet connected: {wallet_address}")
            
            # Send any pending transactions to the newly connected wallet
            if self.pending_transactions:
                self.logger.info(f"Sending {len(self.pending_transactions)} pending transactions")
                for tx_id, tx in list(self.pending_transactions.items()):
                    await self._send_transaction_to_frontend(websocket, tx)
            
            # Send connection acknowledgment
            response = {
                'type': 'phantom_connected_ack',
                'message': 'Connection acknowledged',
                'pending_transactions': len(self.pending_transactions)
            }
            await websocket.send(json.dumps(response))
            
        except Exception as e:
            self.logger.error(f"Failed to handle Phantom connection: {e}")
    
    async def _handle_phantom_disconnected(self, websocket, data: dict):
        """Handle Phantom wallet disconnection"""
        try:
            self.phantom_connected = False
            self.connected_wallet_address = None
            self.connection_time = None
            
            self.logger.info("Phantom wallet disconnected")
            
            # Send disconnection acknowledgment
            response = {
                'type': 'phantom_disconnected_ack',
                'message': 'Disconnection acknowledged'
            }
            await websocket.send(json.dumps(response))
            
        except Exception as e:
            self.logger.error(f"Failed to handle Phantom disconnection: {e}")
    
    async def _send_transaction_to_frontend(self, websocket, tx: SwapTransaction):
        """Send transaction to frontend for signing"""
        try:
            response = {
                'type': 'sign_transaction',
                'tx_id': tx.transaction_id,
                'transaction': tx.unsigned_transaction,
                'trade_info': {
                    'trade_type': tx.trade_type,
                    'token_symbol': tx.token_symbol,
                    'amount_usd': tx.amount_usd,
                    'price_per_token': tx.price_per_token
                }
            }
            
            await websocket.send(json.dumps(response))
            self.logger.info(f"Sent transaction {tx.transaction_id} to frontend")
            
        except Exception as e:
            self.logger.error(f"Failed to send transaction to frontend: {e}")
    
    async def _handle_test_message(self, websocket, data: dict):
        """Handle test messages"""
        try:
            self.logger.info(f"Received test message: {data}")
            response = {
                'type': 'test_response',
                'message': 'Test successful',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'original_data': data
            }
            response_json = json.dumps(response)
            self.logger.info(f"Sending response: {response_json}")
            await websocket.send(response_json)
            self.logger.info("Test response sent successfully")
        except Exception as e:
            self.logger.error(f"Failed to handle test message: {e}")
            # Try to send error response
            try:
                error_response = {
                    'type': 'error',
                    'message': f'Test message error: {str(e)}'
                }
                await websocket.send(json.dumps(error_response))
            except:
                self.logger.error("Failed to send error response")
    
    async def _handle_sign_request(self, websocket, data: dict):
        """Handle transaction signing request"""
        try:
            tx_id = data.get('tx_id')
            if tx_id in self.pending_transactions:
                tx = self.pending_transactions[tx_id]
                
                # Send transaction to frontend for signing
                response = {
                    'type': 'sign_transaction',
                    'tx_id': tx_id,
                    'transaction': tx.unsigned_transaction,
                    'trade_info': {
                        'trade_type': tx.trade_type,
                        'token_symbol': tx.token_symbol,
                        'amount_usd': tx.amount_usd,
                        'price_per_token': tx.price_per_token
                    }
                }
                
                await websocket.send(json.dumps(response))
                self.logger.info(f"Sent transaction {tx_id} for signing")
                
        except Exception as e:
            self.logger.error(f"Failed to handle sign request: {e}")
    
    async def _handle_signed_transaction(self, websocket, data: dict):
        """Handle signed transaction from frontend"""
        try:
            tx_id = data.get('tx_id')
            signed_tx = data.get('signed_transaction')
            
            if tx_id in self.pending_transactions:
                tx = self.pending_transactions[tx_id]
                tx.status = 'signed'
                
                # Broadcast the signed transaction
                if self.wallet_tracker.phantom_builder:
                    tx_signature = await self.wallet_tracker.phantom_builder.broadcast_signed_transaction(signed_tx)
                    
                    if tx_signature:
                        tx.status = 'broadcast'
                        self.logger.info(f"Transaction {tx_id} broadcasted: {tx_signature}")
                        
                        # Send confirmation to frontend
                        response = {
                            'type': 'transaction_broadcast',
                            'tx_id': tx_id,
                            'signature': tx_signature,
                            'status': 'success'
                        }
                        await websocket.send(json.dumps(response))
                    else:
                        tx.status = 'failed'
                        self.logger.error(f"Failed to broadcast transaction {tx_id}")
                        
                        response = {
                            'type': 'transaction_broadcast',
                            'tx_id': tx_id,
                            'status': 'failed'
                        }
                        await websocket.send(json.dumps(response))
                
        except Exception as e:
            self.logger.error(f"Failed to handle signed transaction: {e}")
    
    async def _handle_rejected_transaction(self, websocket, data: dict):
        """Handle rejected transaction from frontend"""
        try:
            tx_id = data.get('tx_id')
            
            if tx_id in self.pending_transactions:
                tx = self.pending_transactions[tx_id]
                tx.status = 'rejected'
                
                self.logger.info(f"Transaction {tx_id} rejected by user")
                
                # Send acknowledgment
                response = {
                    'type': 'transaction_rejected',
                    'tx_id': tx_id,
                    'status': 'acknowledged'
                }
                await websocket.send(json.dumps(response))
                
        except Exception as e:
            self.logger.error(f"Failed to handle rejected transaction: {e}")
    
    async def send_transaction_for_signing(self, swap_tx: SwapTransaction):
        """Send transaction to frontend for Phantom signing"""
        try:
            # Check if we have too many pending transactions
            if len(self.pending_transactions) >= self.max_pending_transactions:
                self.logger.warning(f"Too many pending transactions ({len(self.pending_transactions)}), rejecting new transaction")
                console.print(f"❌ Transaction rejected: Too many pending transactions ({len(self.pending_transactions)})")
                return False
            
            # Check for timeout on existing transactions
            await self._cleanup_expired_transactions()
            
            # Add transaction to pending queue
            self.pending_transactions[swap_tx.transaction_id] = swap_tx
            
            # Display transaction info
            console.print(f"\n🔗 Transaction {swap_tx.transaction_id} queued for Phantom signing")
            console.print(f"   Trade: {swap_tx.trade_type.upper()} {swap_tx.token_symbol}")
            console.print(f"   Amount: ${swap_tx.amount_usd:,.2f}")
            console.print(f"   Price: ${swap_tx.price_per_token:.8f}")
            
            if self.phantom_connected:
                console.print(f"   Status: ✅ Phantom connected - Ready for approval")
                self.logger.info(f"Transaction {swap_tx.transaction_id} ready for signing (Phantom connected)")
            else:
                console.print(f"   Status: ⏳ Phantom not connected - Waiting for connection")
                console.print(f"   💡 Connect your Phantom wallet at http://localhost:5002 to approve")
                self.logger.info(f"Transaction {swap_tx.transaction_id} queued (Phantom not connected)")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send transaction for signing: {e}")
            return False
    
    async def _cleanup_expired_transactions(self):
        """Clean up expired pending transactions"""
        try:
            current_time = datetime.now(timezone.utc)
            expired_txs = []
            
            for tx_id, tx in self.pending_transactions.items():
                time_diff = current_time - tx.timestamp
                if time_diff.total_seconds() > (self.transaction_timeout_minutes * 60):
                    expired_txs.append(tx_id)
            
            for tx_id in expired_txs:
                del self.pending_transactions[tx_id]
                self.logger.info(f"Cleaned up expired transaction: {tx_id}")
            
            if expired_txs:
                console.print(f"🧹 Cleaned up {len(expired_txs)} expired transactions")
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup expired transactions: {e}")
    
    def get_connection_status(self) -> dict:
        """Get current connection status"""
        return {
            'phantom_connected': self.phantom_connected,
            'connected_wallet_address': self.connected_wallet_address,
            'connection_time': self.connection_time.isoformat() if self.connection_time else None,
            'pending_transactions_count': len(self.pending_transactions),
            'max_pending_transactions': self.max_pending_transactions
        }
    
    async def stop_server(self):
        """Stop the Phantom server"""
        try:
            if self.server_task and not self.server_task.done():
                self.logger.info("Stopping WebSocket server...")
                self.server_task.cancel()
                try:
                    await asyncio.wait_for(self.server_task, timeout=2.0)
                except asyncio.CancelledError:
                    self.logger.info("WebSocket server cancelled")
                except asyncio.TimeoutError:
                    self.logger.warning("WebSocket server did not stop within timeout")
                except Exception as e:
                    self.logger.error(f"Error stopping WebSocket server: {e}")
            
            # Clear the server task
            self.server_task = None
            self.logger.info("✅ Phantom server stopped")
            
        except Exception as e:
            self.logger.error(f"Failed to stop Phantom server: {e}")
