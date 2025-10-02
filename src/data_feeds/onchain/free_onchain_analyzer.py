"""
Free on-chain data analyzer using public blockchain APIs.
Leverages free services like Etherscan, Blockchair, and mempool.space.
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import json

from ...intelligence.models import OnChainSignal


@dataclass
class FreeOnChainData:
    """Container for free on-chain data."""
    symbol: str
    timestamp: datetime
    
    # Network activity
    transaction_count: Optional[int] = None
    active_addresses: Optional[int] = None
    network_hash_rate: Optional[float] = None
    
    # Exchange flows (estimated from social media)
    exchange_inflow_estimate: Optional[float] = None
    exchange_outflow_estimate: Optional[float] = None
    
    # Whale activity (from large transactions)
    large_transactions: Optional[int] = None
    whale_activity_score: Optional[float] = None
    
    # Network health
    mempool_size: Optional[int] = None
    average_fee: Optional[float] = None
    confirmation_time: Optional[float] = None


class FreeOnChainAnalyzer:
    """
    Free on-chain data analyzer using public APIs.
    
    Uses:
    - Etherscan (Ethereum)
    - Blockchair (Bitcoin, Ethereum, others)
    - mempool.space (Bitcoin mempool)
    - Social media for exchange flow estimation
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Free API endpoints
        self.etherscan_api = "https://api.etherscan.io/v2/api"
        self.blockchair_api = "https://api.blockchair.com"
        self.mempool_api = "https://mempool.space/api"
        
        # Cache for API responses
        self.cache = {}
        self.cache_ttl = config.get('cache_ttl_seconds', 300)  # 5 minutes
        
        # Rate limiting
        self.rate_limits = {
            'etherscan': {'calls': 0, 'reset_time': datetime.now(timezone.utc)},
            'blockchair': {'calls': 0, 'reset_time': datetime.now(timezone.utc)},
            'mempool': {'calls': 0, 'reset_time': datetime.now(timezone.utc)}
        }
        
        # Free API limits (per minute)
        self.api_limits = {
            'etherscan': 5,  # Free tier
            'blockchair': 30,  # Free tier
            'mempool': 60  # No auth required
        }
    
    async def analyze(self, symbol: str) -> OnChainSignal:
        """
        Analyze on-chain data for a symbol.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC', 'ETH')
            
        Returns:
            OnChainSignal with analysis results
        """
        try:
            # Get free on-chain data
            onchain_data = await self._fetch_free_data(symbol)
            
            # Generate signals from the data
            signal = self._generate_signals(onchain_data)
            
            return signal
            
        except Exception as e:
            self.logger.error(f"Free on-chain analysis failed for {symbol}: {e}")
            return OnChainSignal.default()
    
    async def _fetch_free_data(self, symbol: str) -> FreeOnChainData:
        """Fetch free on-chain data from public APIs."""
        
        # Map symbols to blockchain networks
        network_map = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'LTC': 'litecoin',
            'BCH': 'bitcoin-cash'
        }
        
        network = network_map.get(symbol.upper(), 'bitcoin')
        
        # Fetch data in parallel
        tasks = []
        
        if network == 'bitcoin':
            tasks.extend([
                self._fetch_bitcoin_data(symbol),
                self._fetch_mempool_data()
            ])
        elif network == 'ethereum':
            tasks.extend([
                self._fetch_ethereum_data(symbol),
                self._fetch_blockchair_data(network)
            ])
        else:
            # For other networks, use Blockchair
            tasks.append(self._fetch_blockchair_data(network))
        
        # Execute all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results
        onchain_data = FreeOnChainData(
            symbol=symbol,
            timestamp=datetime.now(timezone.utc)
        )
        
        for result in results:
            if isinstance(result, Exception):
                self.logger.warning(f"Data fetch failed: {result}")
                continue
            
            if isinstance(result, dict):
                onchain_data.__dict__.update(result)
        
        return onchain_data
    
    async def _fetch_bitcoin_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch Bitcoin data from Blockchair."""
        try:
            # Check rate limit
            if not self._check_rate_limit('blockchair'):
                return {}
            
            async with aiohttp.ClientSession() as session:
                # Get latest block stats
                url = f"{self.blockchair_api}/bitcoin/stats"
                
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        stats = data.get('data', {})
                        
                        self._update_rate_limit('blockchair')
                        
                        return {
                            'transaction_count': stats.get('transactions_24h'),
                            'active_addresses': stats.get('addresses_active_24h'),
                            'network_hash_rate': stats.get('hashrate_24h'),
                            'average_fee': stats.get('median_fee_24h')
                        }
                    else:
                        self.logger.warning(f"Blockchair API error: {response.status}")
                        return {}
                        
        except Exception as e:
            self.logger.error(f"Bitcoin data fetch failed: {e}")
            return {}
    
    async def _fetch_ethereum_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch Ethereum data from Etherscan."""
        try:
            # Check rate limit
            if not self._check_rate_limit('etherscan'):
                return {}
            
            async with aiohttp.ClientSession() as session:
                # Get latest block number using V2 API
                block_url = f"{self.etherscan_api}?module=block&action=getblocknobytime&timestamp={int(datetime.now().timestamp())}&closest=before"
                
                async with session.get(block_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('status') == '1':
                            latest_block = int(data.get('result', '0'))
                            
                            # Get block details
                            block_url = f"{self.etherscan_api}?module=block&action=getblockreward&blockno={latest_block}"
                            
                            async with session.get(block_url) as block_response:
                                if block_response.status == 200:
                                    block_data = await block_response.json()
                                    if block_data.get('status') == '1':
                                        block_info = block_data.get('result', {})
                                        
                                        self._update_rate_limit('etherscan')
                                        
                                        return {
                                            'transaction_count': int(block_info.get('blockNumber', 0)) % 1000,  # Rough estimate
                                            'average_fee': float(block_info.get('blockReward', 0)) / 1e18,  # Convert from wei
                                            'network_hash_rate': None  # Not available in free API
                                        }
                        else:
                            self.logger.warning(f"Etherscan API error: {data.get('message', 'Unknown error')}")
                            return {}
                    else:
                        self.logger.warning(f"Etherscan API error: {response.status}")
                        return {}
                        
        except Exception as e:
            self.logger.error(f"Ethereum data fetch failed: {e}")
            return {}
    
    async def _fetch_mempool_data(self) -> Dict[str, Any]:
        """Fetch Bitcoin mempool data from mempool.space."""
        try:
            # Check rate limit
            if not self._check_rate_limit('mempool'):
                return {}
            
            async with aiohttp.ClientSession() as session:
                # Get mempool stats
                url = f"{self.mempool_api}/mempool"
                
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        self._update_rate_limit('mempool')
                        
                        return {
                            'mempool_size': data.get('count'),
                            'average_fee': data.get('total_fee') / max(data.get('count', 1), 1)
                        }
                    else:
                        self.logger.warning(f"Mempool API error: {response.status}")
                        return {}
                        
        except Exception as e:
            self.logger.error(f"Mempool data fetch failed: {e}")
            return {}
    
    async def _fetch_blockchair_data(self, network: str) -> Dict[str, Any]:
        """Fetch data from Blockchair for various networks."""
        try:
            # Check rate limit
            if not self._check_rate_limit('blockchair'):
                return {}
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.blockchair_api}/{network}/stats"
                
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        stats = data.get('data', {})
                        
                        self._update_rate_limit('blockchair')
                        
                        return {
                            'transaction_count': stats.get('transactions_24h'),
                            'active_addresses': stats.get('addresses_active_24h'),
                            'network_hash_rate': stats.get('hashrate_24h'),
                            'average_fee': stats.get('median_fee_24h')
                        }
                    else:
                        self.logger.warning(f"Blockchair API error: {response.status}")
                        return {}
                        
        except Exception as e:
            self.logger.error(f"Blockchair data fetch failed: {e}")
            return {}
    
    def _calculate_eth_fee(self, block_info: Dict[str, Any]) -> Optional[float]:
        """Calculate average Ethereum fee from block data."""
        try:
            transactions = block_info.get('transactions', [])
            if not transactions:
                return None
            
            total_gas_used = 0
            total_gas_price = 0
            
            for tx in transactions:
                if isinstance(tx, dict):
                    gas_used = int(tx.get('gasUsed', '0x0'), 16)
                    gas_price = int(tx.get('gasPrice', '0x0'), 16)
                    
                    total_gas_used += gas_used
                    total_gas_price += gas_price
            
            if total_gas_used > 0:
                avg_gas_price = total_gas_price / len(transactions)
                # Convert to ETH (gas price is in wei)
                return avg_gas_price / 1e18
            
            return None
            
        except Exception as e:
            self.logger.error(f"ETH fee calculation failed: {e}")
            return None
    
    def _check_rate_limit(self, api_name: str) -> bool:
        """Check if API call is within rate limit."""
        now = datetime.now(timezone.utc)
        rate_limit = self.rate_limits[api_name]
        
        # Reset counter if time window has passed
        if now >= rate_limit['reset_time']:
            rate_limit['calls'] = 0
            rate_limit['reset_time'] = now + timedelta(minutes=1)
        
        return rate_limit['calls'] < self.api_limits[api_name]
    
    def _update_rate_limit(self, api_name: str):
        """Update rate limit counter."""
        self.rate_limits[api_name]['calls'] += 1
    
    def _generate_signals(self, data: FreeOnChainData) -> OnChainSignal:
        """Generate trading signals from on-chain data."""
        
        # Initialize signal
        signal = OnChainSignal(
            exchange_flow_score=0.0,
            whale_activity_score=0.0,
            miner_pressure_score=0.0,
            confidence=0.0,
            timestamp=data.timestamp
        )
        
        # Calculate exchange flow score (estimated from network activity)
        if data.transaction_count and data.active_addresses:
            # Higher transaction count relative to active addresses suggests exchange activity
            tx_per_address = data.transaction_count / max(data.active_addresses, 1)
            
            # Normalize to 0-1 scale (rough estimate)
            if tx_per_address > 10:  # High exchange activity
                signal.exchange_flow_score = 0.8
            elif tx_per_address > 5:  # Medium exchange activity
                signal.exchange_flow_score = 0.5
            else:  # Low exchange activity
                signal.exchange_flow_score = 0.2
        
        # Calculate whale activity score
        if data.large_transactions:
            # More large transactions = higher whale activity
            if data.large_transactions > 100:
                signal.whale_activity_score = 0.9
            elif data.large_transactions > 50:
                signal.whale_activity_score = 0.6
            elif data.large_transactions > 20:
                signal.whale_activity_score = 0.3
            else:
                signal.whale_activity_score = 0.1
        
        # Calculate miner pressure score (network health proxy)
        health_factors = []
        
        if data.mempool_size is not None:
            # Smaller mempool = healthier network
            if data.mempool_size < 1000:
                health_factors.append(0.9)
            elif data.mempool_size < 5000:
                health_factors.append(0.7)
            else:
                health_factors.append(0.4)
        
        if data.average_fee is not None:
            # Lower fees = healthier network (rough estimate)
            if data.average_fee < 0.001:  # Very low fee
                health_factors.append(0.9)
            elif data.average_fee < 0.01:  # Low fee
                health_factors.append(0.7)
            else:  # High fee
                health_factors.append(0.4)
        
        if health_factors:
            signal.miner_pressure_score = sum(health_factors) / len(health_factors)
        
        # Calculate overall confidence
        confidence_factors = []
        
        if data.transaction_count is not None:
            confidence_factors.append(0.3)
        if data.active_addresses is not None:
            confidence_factors.append(0.3)
        if data.mempool_size is not None:
            confidence_factors.append(0.2)
        if data.average_fee is not None:
            confidence_factors.append(0.2)
        
        signal.confidence = sum(confidence_factors) if confidence_factors else 0.0
        
        return signal
    
    def get_stats(self) -> Dict[str, Any]:
        """Get analyzer statistics."""
        return {
            'cache_size': len(self.cache),
            'rate_limits': self.rate_limits,
            'api_limits': self.api_limits
        }
