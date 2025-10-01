"""
Exchange API Data Source Implementation

Fetches funding rates, open interest, and exchange flows from major exchanges.
Replaces CryptoQuant features with free exchange APIs.
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .config import SocialMediaConfig
from .base import BaseSocialDataSource, SocialDataPoint, SocialDataBatch, RateLimiter


@dataclass
class ExchangeData:
    """Exchange data structure"""
    exchange: str
    symbol: str
    funding_rate: Optional[float] = None
    open_interest: Optional[float] = None
    long_short_ratio: Optional[float] = None
    volume_24h: Optional[float] = None
    timestamp: Optional[datetime] = None


class ExchangeAPISource(BaseSocialDataSource):
    """Exchange API data source for funding rates and derivatives"""
    
    def __init__(self, config: SocialMediaConfig):
        super().__init__(config, "exchange_api")
        self.exchanges = config.exchange_api.exchanges
        self.update_interval = config.exchange_api.update_interval
        
        # Initialize rate limiter (conservative limits)
        self.rate_limiter = RateLimiter(120, 60)  # 120 requests per minute
        
        # Exchange API endpoints
        self.endpoints = {
            "binance": {
                "funding_rate": "https://fapi.binance.com/fapi/v1/premiumIndex",
                "open_interest": "https://fapi.binance.com/fapi/v1/openInterest",
                "long_short_ratio": "https://fapi.binance.com/fapi/v1/globalLongShortAccountRatio"
            },
            "bybit": {
                "funding_rate": "https://api.bybit.com/v5/market/funding/history",
                "open_interest": "https://api.bybit.com/v5/market/open-interest",
                "long_short_ratio": "https://api.bybit.com/v5/market/account-ratio"
            },
            "okx": {
                "funding_rate": "https://www.okx.com/api/v5/public/funding-rate",
                "open_interest": "https://www.okx.com/api/v5/public/open-interest",
                "long_short_ratio": "https://www.okx.com/api/v5/public/position-tiers"
            },
            "deribit": {
                "funding_rate": "https://www.deribit.com/api/v2/public/get_funding_rate_value",
                "open_interest": "https://www.deribit.com/api/v2/public/get_book_summary_by_currency"
            },
            "bitmex": {
                "funding_rate": "https://www.bitmex.com/api/v1/funding",
                "open_interest": "https://www.bitmex.com/api/v1/instrument"
            }
        }
        
        # Symbol mapping for different exchanges
        self.symbol_mapping = {
            "bitcoin": {
                "binance": "BTCUSDT",
                "bybit": "BTCUSDT",
                "okx": "BTC-USDT-SWAP",
                "deribit": "BTC-PERPETUAL",
                "bitmex": "XBTUSD"
            },
            "ethereum": {
                "binance": "ETHUSDT",
                "bybit": "ETHUSDT",
                "okx": "ETH-USDT-SWAP",
                "deribit": "ETH-PERPETUAL",
                "bitmex": "ETHUSD"
            }
        }
    
    async def fetch_data(self, coin_id: str, data_types: List[str]) -> SocialDataBatch:
        """Fetch exchange data for a coin"""
        # Skip if no exchanges configured
        if not self.config.exchange_api.exchanges:
            logger.debug("Exchange API not configured, skipping...")
            return SocialDataBatch(coin_id, [], self.source_name, datetime.now())
            
        try:
            await self.rate_limiter.acquire()
            
            # Check cache first
            cache_key = f"exchange_api_{coin_id}_{datetime.now().strftime('%Y%m%d%H%M')}"
            cached_data = await self._get_smart_cached_data(coin_id, "exchange_api", {"data_types": data_types})
            if cached_data:
                return cached_data
            
            # Fetch data from all exchanges
            exchange_data = await self._fetch_all_exchanges(coin_id)
            
            # Process data into data points
            data_points = []
            
            if exchange_data:
                # Calculate average funding rate
                funding_rates = [data.funding_rate for data in exchange_data if data.funding_rate is not None]
                if funding_rates:
                    avg_funding_rate = sum(funding_rates) / len(funding_rates)
                    data_points.append(SocialDataPoint(
                        timestamp=datetime.now(),
                        source=self.source_name,
                        coin_id=coin_id,
                        data_type="funding_rate",
                        value=avg_funding_rate,
                        confidence=0.9,
                        metadata={"exchanges": len(funding_rates), "rates": funding_rates}
                    ))
                
                # Calculate total open interest
                open_interests = [data.open_interest for data in exchange_data if data.open_interest is not None]
                if open_interests:
                    total_open_interest = sum(open_interests)
                    data_points.append(SocialDataPoint(
                        timestamp=datetime.now(),
                        source=self.source_name,
                        coin_id=coin_id,
                        data_type="open_interest",
                        value=total_open_interest,
                        confidence=0.8,
                        metadata={"exchanges": len(open_interests), "interests": open_interests}
                    ))
                
                # Calculate average long/short ratio
                ratios = [data.long_short_ratio for data in exchange_data if data.long_short_ratio is not None]
                if ratios:
                    avg_ratio = sum(ratios) / len(ratios)
                    data_points.append(SocialDataPoint(
                        timestamp=datetime.now(),
                        source=self.source_name,
                        coin_id=coin_id,
                        data_type="long_short_ratio",
                        value=avg_ratio,
                        confidence=0.7,
                        metadata={"exchanges": len(ratios), "ratios": ratios}
                    ))
                
                # Calculate exchange flows (simplified)
                exchange_flows = self._calculate_exchange_flows(exchange_data)
                data_points.append(SocialDataPoint(
                    timestamp=datetime.now(),
                    source=self.source_name,
                    coin_id=coin_id,
                    data_type="exchange_flows",
                    value=exchange_flows,
                    confidence=0.6,
                    metadata={"exchanges_monitored": len(exchange_data)}
                ))
            
            batch = SocialDataBatch(
                coin_id=coin_id,
                data_points=data_points,
                source=self.source_name,
                timestamp=datetime.now(),
                quality_score=0.8 if exchange_data else 0.3
            )
            
            # Cache the data using smart cache
            await self._cache_smart_data(coin_id, "exchange_api", batch, {"data_types": data_types})
            return batch
            
        except Exception as e:
            logger.error(f"Exchange API fetch failed for {coin_id}: {e}")
            return SocialDataBatch(coin_id, [], self.source_name, datetime.now())
    
    async def _fetch_all_exchanges(self, coin_id: str) -> List[ExchangeData]:
        """Fetch data from all configured exchanges"""
        exchange_data = []
        
        # Get symbol for the coin
        coin_symbols = self.symbol_mapping.get(coin_id.lower(), {})
        
        for exchange in self.exchanges:
            try:
                if exchange in coin_symbols:
                    symbol = coin_symbols[exchange]
                    data = await self._fetch_exchange_data(exchange, symbol)
                    if data:
                        exchange_data.append(data)
            except Exception as e:
                logger.error(f"Error fetching data from {exchange}: {e}")
                continue
        
        return exchange_data
    
    async def _fetch_exchange_data(self, exchange: str, symbol: str) -> Optional[ExchangeData]:
        """Fetch data from a specific exchange"""
        try:
            exchange_data = ExchangeData(exchange=exchange, symbol=symbol)
            
            if exchange == "binance":
                await self._fetch_binance_data(exchange_data, symbol)
            elif exchange == "bybit":
                await self._fetch_bybit_data(exchange_data, symbol)
            elif exchange == "okx":
                await self._fetch_okx_data(exchange_data, symbol)
            elif exchange == "deribit":
                await self._fetch_deribit_data(exchange_data, symbol)
            elif exchange == "bitmex":
                await self._fetch_bitmex_data(exchange_data, symbol)
            
            return exchange_data
            
        except Exception as e:
            logger.error(f"Error fetching {exchange} data: {e}")
            return None
    
    async def _fetch_binance_data(self, exchange_data: ExchangeData, symbol: str):
        """Fetch data from Binance"""
        try:
            async with aiohttp.ClientSession() as session:
                # Funding rate
                async with session.get(
                    f"{self.endpoints['binance']['funding_rate']}?symbol={symbol}",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        exchange_data.funding_rate = float(data.get('lastFundingRate', 0))
                
                # Open interest
                async with session.get(
                    f"{self.endpoints['binance']['open_interest']}?symbol={symbol}",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        exchange_data.open_interest = float(data.get('openInterest', 0))
                
                # Long/Short ratio
                async with session.get(
                    f"{self.endpoints['binance']['long_short_ratio']}?symbol={symbol}&period=5m&limit=1",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data:
                            exchange_data.long_short_ratio = float(data[0].get('longShortRatio', 1.0))
                            
        except Exception as e:
            logger.error(f"Binance API error: {e}")
    
    async def _fetch_bybit_data(self, exchange_data: ExchangeData, symbol: str):
        """Fetch data from Bybit"""
        try:
            async with aiohttp.ClientSession() as session:
                # Funding rate
                async with session.get(
                    f"{self.endpoints['bybit']['funding_rate']}?category=linear&symbol={symbol}&limit=1",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('result', {}).get('list'):
                            exchange_data.funding_rate = float(data['result']['list'][0].get('fundingRate', 0))
                
                # Open interest
                async with session.get(
                    f"{self.endpoints['bybit']['open_interest']}?category=linear&symbol={symbol}",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('result', {}).get('list'):
                            exchange_data.open_interest = float(data['result']['list'][0].get('openInterest', 0))
                
                # Long/Short ratio
                async with session.get(
                    f"{self.endpoints['bybit']['long_short_ratio']}?category=linear&symbol={symbol}&period=5m&limit=1",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('result', {}).get('list'):
                            ratio_data = data['result']['list'][0]
                            long_account = float(ratio_data.get('longAccount', 0))
                            short_account = float(ratio_data.get('shortAccount', 0))
                            if short_account > 0:
                                exchange_data.long_short_ratio = long_account / short_account
                            
        except Exception as e:
            logger.error(f"Bybit API error: {e}")
    
    async def _fetch_okx_data(self, exchange_data: ExchangeData, symbol: str):
        """Fetch data from OKX"""
        try:
            async with aiohttp.ClientSession() as session:
                # Funding rate
                async with session.get(
                    f"{self.endpoints['okx']['funding_rate']}?instId={symbol}",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('data'):
                            exchange_data.funding_rate = float(data['data'][0].get('fundingRate', 0))
                
                # Open interest
                async with session.get(
                    f"{self.endpoints['okx']['open_interest']}?instId={symbol}",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('data'):
                            exchange_data.open_interest = float(data['data'][0].get('oi', 0))
                            
        except Exception as e:
            logger.error(f"OKX API error: {e}")
    
    async def _fetch_deribit_data(self, exchange_data: ExchangeData, symbol: str):
        """Fetch data from Deribit"""
        try:
            async with aiohttp.ClientSession() as session:
                # Funding rate
                async with session.get(
                    f"{self.endpoints['deribit']['funding_rate']}?instrument_name={symbol}",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        exchange_data.funding_rate = float(data.get('result', 0))
                
                # Open interest (simplified)
                async with session.get(
                    f"{self.endpoints['deribit']['open_interest']}?currency=BTC&kind=future",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('result'):
                            total_oi = sum(float(item.get('open_interest', 0)) for item in data['result'])
                            exchange_data.open_interest = total_oi
                            
        except Exception as e:
            logger.error(f"Deribit API error: {e}")
    
    async def _fetch_bitmex_data(self, exchange_data: ExchangeData, symbol: str):
        """Fetch data from BitMEX"""
        try:
            async with aiohttp.ClientSession() as session:
                # Funding rate
                async with session.get(
                    f"{self.endpoints['bitmex']['funding_rate']}?symbol={symbol}&count=1&reverse=true",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data:
                            exchange_data.funding_rate = float(data[0].get('fundingRate', 0))
                
                # Open interest
                async with session.get(
                    f"{self.endpoints['bitmex']['open_interest']}?symbol={symbol}",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data:
                            exchange_data.open_interest = float(data[0].get('openInterest', 0))
                            
        except Exception as e:
            logger.error(f"BitMEX API error: {e}")
    
    def _calculate_exchange_flows(self, exchange_data: List[ExchangeData]) -> float:
        """Calculate exchange flows (simplified)"""
        if not exchange_data:
            return 0.0
        
        # Simple flow calculation based on funding rates
        # Positive funding rates indicate long bias, negative indicate short bias
        total_flow = 0.0
        valid_rates = 0
        
        for data in exchange_data:
            if data.funding_rate is not None:
                total_flow += data.funding_rate
                valid_rates += 1
        
        if valid_rates == 0:
            return 0.0
        
        # Return average flow (normalized)
        avg_flow = total_flow / valid_rates
        return max(-1.0, min(1.0, avg_flow * 100))  # Scale and clamp


# Import logger
import logging
logger = logging.getLogger(__name__)
