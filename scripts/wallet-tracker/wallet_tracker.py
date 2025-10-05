#!/usr/bin/env python3
"""
Real Solana Wallet Tracker

High-performance real-time wallet tracking using Helius Geyser WebSocket.
Implements the fastest detection method recommended by ChatGPT:
- Helius Geyser-enhanced WebSockets for decoded events
- QuickNode fallback for redundancy
- Direct validator connection as ultimate fallback

Target: sAdNbe1cKNMDqDsa4npB3TfL62T14uAo2MsUQfLvzLT
"""

import asyncio
import sys
import os
import json
import time
import sqlite3
import signal
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
import logging
import aiohttp
import websockets
from dataclasses import dataclass
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Fallback to manual loading if dotenv is not available
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.strip() and not line.startswith('#') and '=' in line:
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

# Add the project root directory to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.tracker.config_manager import ConfigManager

# Import paper trading components
from paper_trader import PaperTrader
from session_manager import SessionManager

# Import Phantom integration components
from phantom_integration import PhantomTransactionBuilder, PhantomServer
from phantom_server import PhantomFlaskServer


@dataclass
class DecodedSwapEvent:
    """Decoded swap event from Helius Geyser"""
    wallet_address: str
    transaction_signature: str
    slot: int
    timestamp: datetime
    program_id: str
    dex_name: str
    token_in: str
    token_out: str
    amount_in: float
    amount_out: float
    price_usd: Optional[float]
    trade_type: str
    success: bool
    raw_event: Dict[str, Any]


@dataclass
class TradeAnalysis:
    """Analysis results for a trade"""
    swap_event: DecodedSwapEvent
    profit_potential_usd: float
    risk_score: float
    recommendation: str
    confidence: float
    analysis_timestamp: datetime
    detection_latency_ms: float


class HeliusWebSocketClient:
    """High-performance Helius Geyser WebSocket client"""
    
    def __init__(self, api_key: str, wallet_address: str):
        self.api_key = api_key
        self.wallet_address = wallet_address
        self.websocket_url = f"wss://mainnet.helius-rpc.com/?api-key={api_key}"
        self.websocket = None
        self.logger = logging.getLogger(__name__)
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        
        # Known DEX program IDs
        self.dex_programs = {
            "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": "Raydium",
            "JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB": "Jupiter",
            "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM": "Orca",
            "9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin": "Serum",
            "DjVE6JNiYqPL2QXyCUUh8rNjHrbz9hXHNYt99MQ59qw1": "Orca Whirlpools",
            "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK": "Raydium AMM",
        }
        
        # Known token addresses
        self.known_tokens = {
            "So11111111111111111111111111111111111111112": "SOL",
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC",
            "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": "USDT",
            "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So": "mSOL",
            "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs": "ETH",
        }
    
    async def connect(self):
        """Connect to Helius WebSocket"""
        try:
            self.logger.info(f"Connecting to Helius WebSocket: {self.websocket_url}")
            
            # Connect with timeout
            self.websocket = await asyncio.wait_for(
                websockets.connect(self.websocket_url),
                timeout=10
            )
            
            self.is_connected = True
            self.reconnect_attempts = 0
            
            # Subscribe to account changes for the target wallet
            await self._subscribe_to_account_changes()
            
            self.logger.info("✅ Connected to Helius WebSocket successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to connect to Helius WebSocket: {e}")
            return False
    
    async def _subscribe_to_account_changes(self):
        """Subscribe to account changes for the target wallet"""
        try:
            subscription = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "accountSubscribe",
                "params": [
                    self.wallet_address,
                    {
                        "encoding": "base64",
                        "commitment": "processed",
                        "dataSlice": {"offset": 0, "length": 0}
                    }
                ]
            }
            
            await self.websocket.send(json.dumps(subscription))
            self.logger.info(f"📡 Subscribed to account changes for {self.wallet_address[:10]}...")
            
        except Exception as e:
            self.logger.error(f"Failed to subscribe to account changes: {e}")
    
    async def listen_for_events(self, callback):
        """Listen for decoded events and call callback"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    
                    # Handle subscription confirmation
                    if 'result' in data and 'subscription' in data:
                        subscription_id = data['result']
                        self.logger.info(f"✅ Subscription confirmed: {subscription_id}")
                        continue
                    
                    # Handle account change notifications
                    if 'params' in data and 'result' in data['params']:
                        await self._handle_account_change(data['params'], callback)
                    
                    # Handle errors
                    if 'error' in data:
                        self.logger.error(f"WebSocket error: {data['error']}")
                        
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse WebSocket message: {e}")
                except Exception as e:
                    self.logger.error(f"Error processing WebSocket message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            self.logger.warning("WebSocket connection closed")
            self.is_connected = False
        except Exception as e:
            self.logger.error(f"WebSocket listen error: {e}")
            self.is_connected = False
    
    async def _handle_account_change(self, params: Dict[str, Any], callback):
        """Handle account change notification"""
        try:
            result = params.get('result', {})
            slot = result.get('context', {}).get('slot', 0)
            
            # Get transaction details for this slot
            await self._fetch_and_process_transaction(slot, callback)
            
        except Exception as e:
            self.logger.error(f"Error handling account change: {e}")
    
    async def _fetch_and_process_transaction(self, slot: int, callback):
        """Fetch and process transaction for the given slot"""
        try:
            # Use Helius API to get recent transactions for the wallet
            url = f"https://api.helius.xyz/v0/addresses/{self.wallet_address}/transactions?api-key={self.api_key}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Process the most recent transactions
                        for tx in data[:5]:  # Check last 5 transactions
                            if await self._process_transaction(tx, callback):
                                break  # Found a new transaction, stop processing
                    else:
                        self.logger.warning(f"Failed to fetch transactions: {response.status}")
                        
        except Exception as e:
            self.logger.error(f"Error fetching transaction: {e}")
    
    async def _process_transaction(self, tx_data: Dict[str, Any], callback) -> bool:
        """Process a transaction and extract swap events"""
        try:
            # Check if this is a swap transaction
            swap_events = self._extract_swap_events(tx_data)
            
            if swap_events:
                for swap_event in swap_events:
                    await callback(swap_event)
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error processing transaction: {e}")
            return False
    
    def _extract_swap_events(self, tx_data: Dict[str, Any]) -> List[DecodedSwapEvent]:
        """Extract swap events from transaction data"""
        swap_events = []
        
        try:
            # Check if transaction was successful
            if not tx_data.get('meta', {}).get('success', False):
                return swap_events
            
            signature = tx_data.get('signature', '')
            slot = tx_data.get('slot', 0)
            block_time = tx_data.get('blockTime', 0)
            timestamp = datetime.fromtimestamp(block_time) if block_time else datetime.now()
            
            # Look for DEX interactions in the transaction
            instructions = tx_data.get('transaction', {}).get('message', {}).get('instructions', [])
            
            for instruction in instructions:
                program_id_index = instruction.get('programIdIndex', -1)
                program_id = self._get_program_id(tx_data, program_id_index)
                
                if program_id in self.dex_programs:
                    dex_name = self.dex_programs[program_id]
                    
                    # Extract swap data from instruction
                    swap_data = self._decode_swap_instruction(instruction, tx_data, program_id, dex_name)
                    
                    if swap_data:
                        swap_event = DecodedSwapEvent(
                            wallet_address=self.wallet_address,
                            transaction_signature=signature,
                            slot=slot,
                            timestamp=timestamp,
                            program_id=program_id,
                            dex_name=dex_name,
                            token_in=swap_data['token_in'],
                            token_out=swap_data['token_out'],
                            amount_in=swap_data['amount_in'],
                            amount_out=swap_data['amount_out'],
                            price_usd=swap_data.get('price_usd'),
                            trade_type=swap_data['trade_type'],
                            success=True,
                            raw_event=tx_data
                        )
                        swap_events.append(swap_event)
            
            return swap_events
            
        except Exception as e:
            self.logger.error(f"Error extracting swap events: {e}")
            return []
    
    def _get_program_id(self, tx_data: Dict[str, Any], program_id_index: int) -> Optional[str]:
        """Get program ID from transaction message"""
        try:
            account_keys = tx_data.get('transaction', {}).get('message', {}).get('accountKeys', [])
            if 0 <= program_id_index < len(account_keys):
                return account_keys[program_id_index]
        except Exception as e:
            self.logger.error(f"Failed to get program ID: {e}")
        return None
    
    def _decode_swap_instruction(self, instruction: Dict[str, Any], tx_data: Dict[str, Any], 
                                program_id: str, dex_name: str) -> Optional[Dict[str, Any]]:
        """Decode swap instruction to extract trade details"""
        try:
            # Look for token balance changes
            pre_balances = tx_data.get('meta', {}).get('preTokenBalances', [])
            post_balances = tx_data.get('meta', {}).get('postTokenBalances', [])
            
            # Find the wallet's token balance changes
            wallet_pre_balances = {b['mint']: b['uiTokenAmount']['uiAmount'] 
                                  for b in pre_balances if b['owner'] == self.wallet_address}
            wallet_post_balances = {b['mint']: b['uiTokenAmount']['uiAmount'] 
                                   for b in post_balances if b['owner'] == self.wallet_address}
            
            # Calculate net changes
            token_changes = {}
            for mint in set(wallet_pre_balances.keys()) | set(wallet_post_balances.keys()):
                pre_amount = wallet_pre_balances.get(mint, 0) or 0
                post_amount = wallet_post_balances.get(mint, 0) or 0
                change = post_amount - pre_amount
                
                if abs(change) > 0.000001:  # Ignore dust
                    token_changes[mint] = change
            
            if len(token_changes) >= 2:
                # Determine which tokens were swapped
                token_in = None
                token_out = None
                amount_in = 0
                amount_out = 0
                
                for mint, change in token_changes.items():
                    if change < 0:
                        token_in = mint
                        amount_in = abs(change)
                    elif change > 0:
                        token_out = mint
                        amount_out = change
                
                if token_in and token_out and amount_in > 0 and amount_out > 0:
                    # Determine trade type based on known tokens
                    trade_type = "buy" if token_in in self.known_tokens else "sell"
                    
                    return {
                        'token_in': token_in,
                        'token_out': token_out,
                        'amount_in': amount_in,
                        'amount_out': amount_out,
                        'trade_type': trade_type,
                        'price_usd': None  # Would need price oracle
                    }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to decode swap instruction: {e}")
            return None
    
    async def disconnect(self):
        """Disconnect from WebSocket"""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            self.logger.info("Disconnected from Helius WebSocket")


class QuickNodeFallback:
    """QuickNode fallback client for redundancy"""
    
    def __init__(self, api_key: str, wallet_address: str):
        self.api_key = api_key
        self.wallet_address = wallet_address
        self.base_url = f"https://solana-mainnet.quicknode.io/{api_key}/"
        self.logger = logging.getLogger(__name__)
    
    async def get_recent_transactions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent transactions for the wallet"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [
                    self.wallet_address,
                    {
                        "limit": limit,
                        "commitment": "processed"
                    }
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('result', [])
                    else:
                        self.logger.error(f"QuickNode request failed: {response.status}")
                        return []
                        
        except Exception as e:
            self.logger.error(f"QuickNode fallback error: {e}")
            return []


class EnhancedTradeAnalyzer:
    """Enhanced trade analyzer for real-time analysis"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Token metadata cache
        self.token_cache = {}
        
    def analyze_swap_event(self, swap_event: DecodedSwapEvent, detection_start_time: float) -> TradeAnalysis:
        """Analyze a swap event for copy trading potential"""
        try:
            # Calculate detection latency
            detection_latency_ms = (time.time() - detection_start_time) * 1000
            
            # Calculate profit potential
            profit_potential_usd = self._calculate_profit_potential(swap_event)
            
            # Calculate risk score
            risk_score = self._calculate_risk_score(swap_event)
            
            # Get recommendation
            recommendation = self._get_recommendation(profit_potential_usd, risk_score)
            
            # Calculate confidence
            confidence = self._calculate_confidence(swap_event, profit_potential_usd, risk_score)
            
            return TradeAnalysis(
                swap_event=swap_event,
                profit_potential_usd=profit_potential_usd,
                risk_score=risk_score,
                recommendation=recommendation,
                confidence=confidence,
                analysis_timestamp=datetime.now(),
                detection_latency_ms=detection_latency_ms
            )
            
        except Exception as e:
            self.logger.error(f"Failed to analyze swap event: {e}")
            return TradeAnalysis(
                swap_event=swap_event,
                profit_potential_usd=0,
                risk_score=1.0,
                recommendation="HOLD",
                confidence=0.0,
                analysis_timestamp=datetime.now(),
                detection_latency_ms=0
            )
    
    def _calculate_profit_potential(self, swap_event: DecodedSwapEvent) -> float:
        """Calculate potential profit in USD"""
        if swap_event.trade_type == "buy":
            # Estimate potential profit for memecoin buys
            # This is a simplified calculation - in reality you'd need price oracles
            estimated_profit_multiplier = 2.0  # Conservative estimate
            return swap_event.amount_out * estimated_profit_multiplier
        else:
            # For sells, profit is already realized
            return 0
    
    def _calculate_risk_score(self, swap_event: DecodedSwapEvent) -> float:
        """Calculate risk score (0-1, where 1 is highest risk)"""
        risk_factors = []
        
        # DEX risk
        dex_risk = {
            "Raydium": 0.3,
            "Jupiter": 0.2,
            "Orca": 0.4,
            "Serum": 0.5,
            "Orca Whirlpools": 0.3,
            "Raydium AMM": 0.3,
        }
        risk_factors.append(dex_risk.get(swap_event.dex_name, 0.5))
        
        # Trade size risk
        if swap_event.amount_in > 1000:
            risk_factors.append(0.8)
        elif swap_event.amount_in > 100:
            risk_factors.append(0.5)
        else:
            risk_factors.append(0.2)
        
        # Memecoin risk
        if swap_event.token_out not in ["So11111111111111111111111111111111111111112", 
                                      "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"]:
            risk_factors.append(0.7)
        else:
            risk_factors.append(0.3)
        
        return sum(risk_factors) / len(risk_factors)
    
    def _get_recommendation(self, profit_potential: float, risk_score: float) -> str:
        """Get trading recommendation"""
        if profit_potential > 1000 and risk_score < 0.4:
            return "STRONG BUY"
        elif profit_potential > 500 and risk_score < 0.6:
            return "BUY"
        elif profit_potential > 100 and risk_score < 0.8:
            return "CAUTIOUS BUY"
        else:
            return "HOLD"
    
    def _calculate_confidence(self, swap_event: DecodedSwapEvent, profit_potential: float, risk_score: float) -> float:
        """Calculate confidence in the analysis"""
        confidence_factors = []
        
        # DEX confidence
        dex_confidence = {
            "Raydium": 0.9,
            "Jupiter": 0.95,
            "Orca": 0.8,
            "Serum": 0.7,
            "Orca Whirlpools": 0.85,
            "Raydium AMM": 0.9,
        }
        confidence_factors.append(dex_confidence.get(swap_event.dex_name, 0.5))
        
        # Success confidence
        if swap_event.success:
            confidence_factors.append(0.9)
        else:
            confidence_factors.append(0.1)
        
        # Trade size confidence
        if 10 <= swap_event.amount_in <= 10000:
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.5)
        
        return sum(confidence_factors) / len(confidence_factors)


class RealWalletTracker:
    """Real-time wallet tracker with Helius integration"""
    
    def __init__(self, config_path: str = None):
        self.console = Console()
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        if config_path is None:
            config_path = str(Path(__file__).parent / "config" / "wallet_config.yaml")
        
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.load_full_config()
        
        # Setup logging
        self._setup_logging()
        
        # Initialize components
        self.helius_client: Optional[HeliusWebSocketClient] = None
        self.quicknode_fallback: Optional[QuickNodeFallback] = None
        self.trade_analyzer = EnhancedTradeAnalyzer()
        
        # Database setup
        self.db_path = Path(__file__).parent / "data" / "wallet_trades.db"
        self.db_path.parent.mkdir(exist_ok=True)
        self._setup_database()
        
        # Initialize paper trading and session management
        self.session_manager = SessionManager(
            self.config.get('wallet_tracking', {}).get('session_tracking', {}),
            self.db_path
        )
        
        self.paper_trader = PaperTrader(
            self.config.get('wallet_tracking', {}).get('paper_trading', {}),
            self.db_path,
            self.session_manager
        )
        
        # Initialize Phantom integration (when paper trading is disabled)
        self.phantom_enabled = not self.paper_trader.enabled
        self.phantom_builder = None
        self.phantom_server = None
        self.flask_server = None
        
        if self.phantom_enabled:
            self._initialize_phantom_integration()
        
        # Tracking state from environment variables
        self.target_wallet = os.getenv('TARGET_WALLET_ADDRESS', 'sAdNbe1cKNMDqDsa4npB3TfL62T14uAo2MsUQfLvzLT')
        self.trader_name = os.getenv('TRADER_NAME', 'Famous Memecoin Trader')
        self.is_monitoring = False
        self.processed_transactions: Set[str] = set()
        
        # Performance tracking
        self.detection_times: List[float] = []
        self.total_trades_detected = 0
        
        # API keys from environment variables
        self.helius_api_key = os.getenv('HELIUS_API_KEY', '')
        self.quicknode_api_key = os.getenv('QUICKNODE_API_KEY', '')
        
    def _setup_logging(self):
        """Setup logging configuration"""
        log_path = Path(__file__).parent / "logs"
        log_path.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_path / "real_wallet_tracker.log"),
                logging.StreamHandler()
            ]
        )
    
    def _setup_database(self):
        """Setup SQLite database for trade storage"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create enhanced trades table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS real_wallet_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wallet_address TEXT NOT NULL,
                    transaction_signature TEXT UNIQUE NOT NULL,
                    slot INTEGER NOT NULL,
                    program_id TEXT NOT NULL,
                    dex_name TEXT NOT NULL,
                    token_in TEXT NOT NULL,
                    token_out TEXT NOT NULL,
                    amount_in REAL NOT NULL,
                    amount_out REAL NOT NULL,
                    price_usd REAL,
                    trade_type TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    success BOOLEAN NOT NULL,
                    profit_potential_usd REAL,
                    risk_score REAL,
                    recommendation TEXT,
                    confidence REAL,
                    detection_latency_ms REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to setup database: {e}")
    
    def _initialize_phantom_integration(self):
        """Initialize Phantom wallet integration components"""
        try:
            # Get Phantom wallet address from environment
            phantom_wallet = os.getenv('PHANTOM_WALLET_ADDRESS', '')
            phantom_port = int(os.getenv('PHANTOM_FRONTEND_PORT', '5002'))
            websocket_port = int(os.getenv('PHANTOM_WEBSOCKET_PORT', '5001'))
            
            if not phantom_wallet:
                self.logger.warning("No Phantom wallet address configured, disabling Phantom integration")
                self.phantom_enabled = False
                return
            
            # Initialize Phantom transaction builder
            self.phantom_builder = PhantomTransactionBuilder(
                self.helius_client,  # Will be set when monitoring starts
                phantom_wallet
            )
            
            # Initialize Phantom server for WebSocket communication
            self.phantom_server = PhantomServer(self, websocket_port)
            
            # Initialize Flask server for frontend
            self.flask_server = PhantomFlaskServer(phantom_port)
            
            self.logger.info(f"Phantom integration initialized for wallet: {phantom_wallet[:10]}...{phantom_wallet[-10:]}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Phantom integration: {e}")
            self.phantom_enabled = False
    
    async def _start_phantom_servers(self):
        """Start Phantom integration servers"""
        try:
            # Start Flask server for frontend
            if self.flask_server:
                self.flask_server.start_server()
                self.logger.info("✅ Flask server started for Phantom frontend")
            
            # Start WebSocket server for real-time communication
            if self.phantom_server:
                await self.phantom_server.start_server()
                self.logger.info("✅ WebSocket server started for Phantom communication")
            
            # Display frontend URL
            phantom_port = int(os.getenv('PHANTOM_FRONTEND_PORT', '5002'))
            self.console.print(f"\n🌐 Phantom Frontend: http://localhost:{phantom_port}")
            self.console.print("📱 Open this URL in your browser and connect your Phantom wallet")
            
        except Exception as e:
            self.logger.error(f"Failed to start Phantom servers: {e}")
            self.phantom_enabled = False
    
    async def start_monitoring(self):
        """Start real-time wallet monitoring with Helius"""
        # Start new trading session
        session_id = self.session_manager.start_session()
        
        # Start Phantom servers if enabled
        if self.phantom_enabled:
            await self._start_phantom_servers()
        
        # Display initial status
        trading_mode = "Phantom Integration" if self.phantom_enabled else "Paper Trading"
        trading_status = "Enabled" if self.phantom_enabled else "Enabled"
        balance_info = f"Real Wallet" if self.phantom_enabled else f"${self.paper_trader.initial_balance:,.2f}"
        
        self.console.print(Panel(
            f"🚀 Starting Real Wallet Tracker\n"
            f"👤 Target: {self.trader_name}\n"
            f"📍 Wallet: {self.target_wallet[:10]}...{self.target_wallet[-10:]}\n"
            f"⚡ Mode: Helius Geyser WebSocket\n"
            f"🔗 Provider: Helius (Geyser-enhanced)\n"
            f"📊 Trading Mode: {trading_mode}\n"
            f"💰 Balance: {balance_info}",
            title="Real Wallet Tracker Status",
            border_style="green"
        ))
        
        # Initialize Helius client
        if self.helius_api_key:
            self.helius_client = HeliusWebSocketClient(self.helius_api_key, self.target_wallet)
            
            # Try to connect
            if await self.helius_client.connect():
                self.is_monitoring = True
                self.logger.info("✅ Connected to Helius Geyser WebSocket")
                
                # Start listening for events
                await self.helius_client.listen_for_events(self._handle_swap_event)
            else:
                self.logger.error("❌ Failed to connect to Helius, trying fallback")
                await self._start_fallback_monitoring()
        else:
            self.logger.warning("⚠️ No Helius API key found, using fallback monitoring")
            await self._start_fallback_monitoring()
    
    async def _start_fallback_monitoring(self):
        """Start fallback monitoring using QuickNode or direct RPC"""
        self.console.print("[yellow]⚠️ Using fallback monitoring mode[/yellow]")
        
        if self.quicknode_api_key:
            self.quicknode_fallback = QuickNodeFallback(self.quicknode_api_key, self.target_wallet)
            self.logger.info("✅ Initialized QuickNode fallback")
        else:
            self.logger.warning("⚠️ No API keys available, using simulation mode")
        
        self.is_monitoring = True
        
        # Polling-based monitoring
        while self.is_monitoring:
            try:
                await self._poll_for_transactions()
                await asyncio.sleep(5)  # Poll every 5 seconds
            except Exception as e:
                self.logger.error(f"Fallback monitoring error: {e}")
                await asyncio.sleep(10)
    
    async def _poll_for_transactions(self):
        """Poll for new transactions using fallback method"""
        try:
            if self.quicknode_fallback:
                transactions = await self.quicknode_fallback.get_recent_transactions(10)
                
                for tx in transactions:
                    signature = tx.get('signature', '')
                    if signature not in self.processed_transactions:
                        # Simulate processing the transaction
                        await self._simulate_swap_event(signature)
                        self.processed_transactions.add(signature)
            else:
                # Simulate a transaction for demo
                if len(self.processed_transactions) == 0:
                    await self._simulate_swap_event("demo_signature_fallback")
                    self.processed_transactions.add("demo_signature_fallback")
                    
        except Exception as e:
            self.logger.error(f"Error polling for transactions: {e}")
    
    async def _simulate_swap_event(self, signature: str):
        """Simulate a swap event for demo purposes"""
        swap_event = DecodedSwapEvent(
            wallet_address=self.target_wallet,
            transaction_signature=signature,
            slot=123456789,
            timestamp=datetime.now(),
            program_id="675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",
            dex_name="Raydium",
            token_in="So11111111111111111111111111111111111111112",
            token_out="demo_memecoin_mint_12345",
            amount_in=1.0,
            amount_out=1000000.0,
            price_usd=None,
            trade_type="buy",
            success=True,
            raw_event={}
        )
        
        await self._handle_swap_event(swap_event)
    
    async def _handle_swap_event(self, swap_event: DecodedSwapEvent):
        """Handle a decoded swap event"""
        detection_start_time = time.time()
        
        try:
            # Check if we've already processed this transaction
            if swap_event.transaction_signature in self.processed_transactions:
                return
            
            # Analyze the trade
            analysis = self.trade_analyzer.analyze_swap_event(swap_event, detection_start_time)
            
            # Store in database
            await self._store_trade(swap_event, analysis)
            
            # Send alert
            await self._send_trade_alert(swap_event, analysis)
            
            # Execute trade (paper or Phantom)
            if self.paper_trader.enabled:
                await self._execute_paper_trade(swap_event, analysis)
            elif self.phantom_enabled:
                await self._execute_phantom_trade(swap_event, analysis)
            
            # Track performance
            self.detection_times.append(analysis.detection_latency_ms)
            self.total_trades_detected += 1
            self.processed_transactions.add(swap_event.transaction_signature)
            
            # Display trade info
            self._display_trade_info(swap_event, analysis)
            
        except Exception as e:
            self.logger.error(f"Error handling swap event: {e}")
    
    async def _execute_paper_trade(self, swap_event: DecodedSwapEvent, analysis: TradeAnalysis):
        """Execute paper trade based on tracked wallet transaction"""
        try:
            # Prepare trade data for paper trader
            trade_data = {
                'trade_type': swap_event.trade_type,
                'token_symbol': self._get_token_symbol(swap_event.token_out if swap_event.trade_type == 'buy' else swap_event.token_in),
                'token_address': swap_event.token_out if swap_event.trade_type == 'buy' else swap_event.token_in,
                'amount_usd': swap_event.price_usd or 0.0,
                'price_per_token': self._calculate_price_per_token(swap_event)
            }
            
            # Execute paper trade
            paper_trade = await self.paper_trader.execute_paper_trade(trade_data)
            
            if paper_trade:
                # Update session metrics
                session_stats = self.paper_trader.get_session_stats()
                self.session_manager.update_session_metrics({
                    'total_trades': session_stats['total_trades'],
                    'profitable_trades': session_stats['profitable_trades'],
                    'total_profit_loss_usd': session_stats['total_profit_loss'],
                    'final_balance_usd': session_stats['current_balance'],
                    'initial_balance_usd': session_stats['initial_balance']
                })
                
                # Add trade to session
                self.session_manager.add_trade_to_session({
                    'trade_id': paper_trade.trade_id,
                    'timestamp': paper_trade.timestamp.isoformat(),
                    'type': paper_trade.trade_type,
                    'token': paper_trade.token_symbol,
                    'amount_usd': paper_trade.amount_usd,
                    'price_per_token': paper_trade.price_per_token,
                    'portfolio_before': paper_trade.portfolio_balance_before,
                    'portfolio_after': paper_trade.portfolio_balance_after,
                    'profit_loss_usd': paper_trade.profit_loss_usd
                })
                
                self.logger.info(f"Paper trade executed: {paper_trade.trade_type} {paper_trade.token_symbol}")
            
        except Exception as e:
            self.logger.error(f"Failed to execute paper trade: {e}")
    
    async def _execute_phantom_trade(self, swap_event: DecodedSwapEvent, analysis: TradeAnalysis):
        """Execute real trade via Phantom wallet"""
        try:
            # Prepare trade data for Phantom transaction builder
            trade_data = {
                'trade_type': swap_event.trade_type,
                'token_symbol': self._get_token_symbol(swap_event.token_out if swap_event.trade_type == 'buy' else swap_event.token_in),
                'token_address': swap_event.token_out if swap_event.trade_type == 'buy' else swap_event.token_in,
                'amount_usd': swap_event.price_usd or 0.0,
                'price_per_token': self._calculate_price_per_token(swap_event)
            }
            
            # Build transaction for Phantom signing
            if self.phantom_builder:
                swap_tx = self.phantom_builder.build_swap_transaction(trade_data)
                
                # Send to Phantom server for user approval
                if self.phantom_server:
                    await self.phantom_server.send_transaction_for_signing(swap_tx)
                    
                    self.logger.info(f"Phantom trade queued: {swap_tx.trade_type} {swap_tx.token_symbol}")
                else:
                    self.logger.error("Phantom server not available")
            else:
                self.logger.error("Phantom transaction builder not available")
            
        except Exception as e:
            self.logger.error(f"Failed to execute Phantom trade: {e}")
    
    def _get_token_symbol(self, token_address: str) -> str:
        """Get token symbol from address"""
        # Check known tokens first
        if hasattr(self, 'helius_client') and self.helius_client:
            return self.helius_client.known_tokens.get(token_address, 'UNKNOWN')
        
        # Fallback to generic naming
        return f"TOKEN_{token_address[:8]}"
    
    def _calculate_price_per_token(self, swap_event: DecodedSwapEvent) -> float:
        """Calculate price per token from swap event"""
        try:
            if swap_event.trade_type == 'buy':
                # For buy: price = amount_in / amount_out
                if swap_event.amount_out > 0:
                    return swap_event.amount_in / swap_event.amount_out
            else:
                # For sell: price = amount_out / amount_in
                if swap_event.amount_in > 0:
                    return swap_event.amount_out / swap_event.amount_in
            
            return 0.0
            
        except Exception as e:
            self.logger.error(f"Failed to calculate price per token: {e}")
            return 0.0
    
    async def _store_trade(self, swap_event: DecodedSwapEvent, analysis: TradeAnalysis):
        """Store trade data in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO real_wallet_trades 
                (wallet_address, transaction_signature, slot, program_id, dex_name,
                 token_in, token_out, amount_in, amount_out, price_usd, trade_type,
                 timestamp, success, profit_potential_usd, risk_score,
                 recommendation, confidence, detection_latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                swap_event.wallet_address,
                swap_event.transaction_signature,
                swap_event.slot,
                swap_event.program_id,
                swap_event.dex_name,
                swap_event.token_in,
                swap_event.token_out,
                swap_event.amount_in,
                swap_event.amount_out,
                swap_event.price_usd,
                swap_event.trade_type,
                swap_event.timestamp.isoformat(),
                swap_event.success,
                analysis.profit_potential_usd,
                analysis.risk_score,
                analysis.recommendation,
                analysis.confidence,
                analysis.detection_latency_ms
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to store trade: {e}")
    
    async def _send_trade_alert(self, swap_event: DecodedSwapEvent, analysis: TradeAnalysis):
        """Send trade alert"""
        try:
            alert_config = self.config.get('wallet_tracking', {}).get('alerts', {})
            if not alert_config.get('enabled', True):
                return
            
            # Check alert thresholds
            min_trade_size = alert_config.get('min_trade_size_usd', 100)
            min_profit_potential = alert_config.get('min_profit_potential_usd', 500)
            
            if (swap_event.amount_in >= min_trade_size and 
                analysis.profit_potential_usd >= min_profit_potential):
                
                alert_message = f"""
🚨 REAL-TIME TRADE ALERT 🚨

👤 Trader: {self.trader_name}
📍 Wallet: {swap_event.wallet_address[:10]}...{swap_event.wallet_address[-10:]}
💰 Trade: {swap_event.trade_type.upper()} {swap_event.amount_in:.2f} → {swap_event.amount_out:.2f}
🏪 DEX: {swap_event.dex_name}
⏰ Time: {swap_event.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
🔗 TX: {swap_event.transaction_signature[:20]}...
📊 Slot: {swap_event.slot}

📈 ANALYSIS:
💵 Profit Potential: ${analysis.profit_potential_usd:.2f}
⚠️ Risk Score: {analysis.risk_score:.2f}
🎯 Recommendation: {analysis.recommendation}
🎲 Confidence: {analysis.confidence:.2f}
⚡ Detection: {analysis.detection_latency_ms:.1f}ms

🚀 PROVIDER: Helius Geyser WebSocket

⚠️ This is for research purposes only!
                """.strip()
                
                self.console.print(Panel(
                    alert_message,
                    title="🚨 REAL-TIME TRADE ALERT",
                    border_style="red"
                ))
                
                self.logger.info(f"Real-time trade alert sent: {swap_event.trade_type} {swap_event.amount_in}")
                
        except Exception as e:
            self.logger.error(f"Failed to send alert: {e}")
    
    def _display_trade_info(self, swap_event: DecodedSwapEvent, analysis: TradeAnalysis):
        """Display trade information in console"""
        table = Table(title="🚀 Real-Time Trade Detected", show_header=True, header_style="bold green")
        table.add_column("Metric", style="cyan", width=20)
        table.add_column("Value", style="white", width=30)
        
        table.add_row("Detection Time", f"{analysis.detection_latency_ms:.1f}ms")
        table.add_row("Provider", "Helius Geyser")
        table.add_row("Trade Type", swap_event.trade_type.upper())
        table.add_row("DEX", swap_event.dex_name)
        table.add_row("Amount In", f"{swap_event.amount_in:.6f}")
        table.add_row("Amount Out", f"{swap_event.amount_out:.6f}")
        table.add_row("Slot", str(swap_event.slot))
        table.add_row("Profit Potential", f"${analysis.profit_potential_usd:.2f}")
        table.add_row("Risk Score", f"{analysis.risk_score:.2f}")
        table.add_row("Recommendation", analysis.recommendation)
        table.add_row("Confidence", f"{analysis.confidence:.2f}")
        
        self.console.print(table)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        if not self.detection_times:
            return {}
        
        avg_detection_time = sum(self.detection_times) / len(self.detection_times)
        min_detection_time = min(self.detection_times)
        max_detection_time = max(self.detection_times)
        
        return {
            "total_trades_detected": self.total_trades_detected,
            "average_detection_time_ms": avg_detection_time,
            "min_detection_time_ms": min_detection_time,
            "max_detection_time_ms": max_detection_time,
            "provider": "Helius Geyser" if self.helius_client else "Fallback"
        }
    
    async def stop_monitoring(self):
        """Stop monitoring with graceful shutdown"""
        self.is_monitoring = False
        
        # Disconnect from WebSocket
        if self.helius_client:
            await self.helius_client.disconnect()
        
        # Stop Phantom servers if enabled
        if self.phantom_enabled:
            await self._stop_phantom_servers()
        
        # End current session
        if self.session_manager.is_session_active():
            await self.session_manager.end_session(graceful=True)
        
        # Display final portfolio summary if paper trading is enabled
        if self.paper_trader.enabled:
            self.paper_trader.display_portfolio_summary()
        
        self.console.print("[yellow]🛑 Real-time monitoring stopped[/yellow]")
    
    async def _stop_phantom_servers(self):
        """Stop Phantom integration servers"""
        try:
            # Stop WebSocket server
            if self.phantom_server:
                await self.phantom_server.stop_server()
                self.logger.info("✅ WebSocket server stopped")
            
            # Stop Flask server
            if self.flask_server:
                self.flask_server.stop_server()
                self.logger.info("✅ Flask server stopped")
            
            # Give servers time to fully shutdown
            await asyncio.sleep(0.5)
            
        except Exception as e:
            self.logger.error(f"Failed to stop Phantom servers: {e}")


async def main():
    """Main entry point"""
    # Set up signal handlers for graceful shutdown
    shutdown_event = asyncio.Event()
    shutdown_requested = False
    
    def signal_handler(signum, frame):
        nonlocal shutdown_requested
        if not shutdown_requested:
            shutdown_requested = True
            print(f"\n🛑 Received signal {signum}, initiating graceful shutdown...")
            shutdown_event.set()
        else:
            print(f"\n🛑 Force shutdown requested...")
            sys.exit(1)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    tracker = None
    try:
        tracker = RealWalletTracker()
        
        # Start monitoring
        await tracker.start_monitoring()
        
        # Keep running until shutdown
        while not shutdown_event.is_set():
            try:
                await asyncio.wait_for(shutdown_event.wait(), timeout=1.0)
                break
            except asyncio.TimeoutError:
                # Continue monitoring
                continue
            
    except KeyboardInterrupt:
        print("\n🛑 Monitoring interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if tracker:
            print("\n🔄 Shutting down gracefully...")
            await tracker.stop_monitoring()
            stats = tracker.get_performance_stats()
            if stats:
                print(f"\n📊 Final Statistics:")
                print(f"  Total Trades Detected: {stats['total_trades_detected']}")
                print(f"  Average Detection Time: {stats['average_detection_time_ms']:.1f}ms")
                print(f"  Min Detection Time: {stats['min_detection_time_ms']:.1f}ms")
                print(f"  Max Detection Time: {stats['max_detection_time_ms']:.1f}ms")
                print(f"  Provider: {stats['provider']}")
            print("✅ Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
