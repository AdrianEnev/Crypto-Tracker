"""
Dune Analytics Data Source Implementation

Fetches on-chain metrics and whale movement data from Dune Analytics.
Replaces Glassnode features with free Dune Analytics data.
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
class DuneQuery:
    """Dune Analytics query data structure"""
    query_id: str
    name: str
    description: str
    parameters: Optional[Dict[str, Any]] = None


class DuneAnalyticsSource(BaseSocialDataSource):
    """Dune Analytics data source for on-chain metrics"""
    
    def __init__(self, config: SocialMediaConfig):
        super().__init__(config, "dune_analytics")
        self.api_key = config.dune_analytics.api_key
        self.base_url = config.dune_analytics.base_url
        self.dashboards = config.dune_analytics.dashboards
        self.update_interval = config.dune_analytics.update_interval
        
        # Initialize rate limiter (Dune allows 1000 requests per hour)
        self.rate_limiter = RateLimiter(1000, 3600)  # 1000 requests per hour
        
        # Pre-defined queries for major cryptocurrencies
        self.queries = {
            "bitcoin": [
                DuneQuery("191", "Bitcoin Daily Transactions", "Daily transaction count and volume"),
                DuneQuery("192", "Bitcoin Active Addresses", "Daily active addresses"),
                DuneQuery("193", "Bitcoin Whale Movements", "Large holder transactions"),
                DuneQuery("194", "Bitcoin Exchange Flows", "Exchange inflows and outflows")
            ],
            "ethereum": [
                DuneQuery("201", "Ethereum Daily Transactions", "Daily transaction count and volume"),
                DuneQuery("202", "Ethereum Active Addresses", "Daily active addresses"),
                DuneQuery("203", "Ethereum Whale Movements", "Large holder transactions"),
                DuneQuery("204", "Ethereum Exchange Flows", "Exchange inflows and outflows")
            ],
            "defi": [
                DuneQuery("301", "DeFi TVL Overview", "Total Value Locked across protocols"),
                DuneQuery("302", "DeFi Protocol Metrics", "Individual protocol performance"),
                DuneQuery("303", "DeFi Yield Farming", "Yield farming activity and returns"),
                DuneQuery("304", "DeFi Governance", "Governance token activity")
            ]
        }
    
    async def fetch_data(self, coin_id: str, data_types: List[str]) -> SocialDataBatch:
        """Fetch Dune Analytics data for a coin"""
        # Skip if no API key configured
        if not self.api_key:
            logger.debug("Dune Analytics API not configured, skipping...")
            return SocialDataBatch(coin_id, [], self.source_name, datetime.now())
            
        try:
            await self.rate_limiter.acquire()
            
            # Check cache first
            cache_key = f"dune_analytics_{coin_id}_{datetime.now().strftime('%Y%m%d%H%M')}"
            cached_data = await self._get_smart_cached_data(coin_id, "dune_analytics", {"data_types": data_types})
            if cached_data:
                return cached_data
            
            # Get queries for the coin
            coin_queries = self.queries.get(coin_id.lower(), [])
            if not coin_queries:
                # Try to find queries for similar coins
                if coin_id.lower() in ["btc", "bitcoin"]:
                    coin_queries = self.queries["bitcoin"]
                elif coin_id.lower() in ["eth", "ethereum"]:
                    coin_queries = self.queries["ethereum"]
                else:
                    # Use generic queries
                    coin_queries = self.queries.get("bitcoin", [])
            
            # Fetch data from queries
            query_results = await self._fetch_query_data(coin_queries)
            
            # Process data into data points
            data_points = []
            
            if query_results:
                # Calculate transaction volume
                transaction_volume = self._calculate_transaction_volume(query_results)
                if transaction_volume is not None:
                    data_points.append(SocialDataPoint(
                        timestamp=datetime.now(),
                        source=self.source_name,
                        coin_id=coin_id,
                        data_type="transaction_volume",
                        value=transaction_volume,
                        confidence=0.9,
                        metadata={"queries_used": len(query_results)}
                    ))
                
                # Calculate active addresses
                active_addresses = self._calculate_active_addresses(query_results)
                if active_addresses is not None:
                    data_points.append(SocialDataPoint(
                        timestamp=datetime.now(),
                        source=self.source_name,
                        coin_id=coin_id,
                        data_type="active_addresses",
                        value=active_addresses,
                        confidence=0.8,
                        metadata={"queries_used": len(query_results)}
                    ))
                
                # Calculate whale movements
                whale_movements = self._calculate_whale_movements(query_results)
                if whale_movements is not None:
                    data_points.append(SocialDataPoint(
                        timestamp=datetime.now(),
                        source=self.source_name,
                        coin_id=coin_id,
                        data_type="whale_movements",
                        value=whale_movements,
                        confidence=0.7,
                        metadata={"queries_used": len(query_results)}
                    ))
                
                # Calculate DeFi TVL (if applicable)
                defi_tvl = self._calculate_defi_tvl(query_results)
                if defi_tvl is not None:
                    data_points.append(SocialDataPoint(
                        timestamp=datetime.now(),
                        source=self.source_name,
                        coin_id=coin_id,
                        data_type="defi_tvl",
                        value=defi_tvl,
                        confidence=0.8,
                        metadata={"queries_used": len(query_results)}
                    ))
            
            batch = SocialDataBatch(
                coin_id=coin_id,
                data_points=data_points,
                source=self.source_name,
                timestamp=datetime.now(),
                quality_score=0.8 if query_results else 0.3
            )
            
            # Cache the data using smart cache
            await self._cache_smart_data(coin_id, "dune_analytics", batch, {"data_types": data_types})
            return batch
            
        except Exception as e:
            logger.error(f"Dune Analytics fetch failed for {coin_id}: {e}")
            return SocialDataBatch(coin_id, [], self.source_name, datetime.now())
    
    async def _fetch_query_data(self, queries: List[DuneQuery]) -> List[Dict[str, Any]]:
        """Fetch data from Dune Analytics queries"""
        results = []
        
        for query in queries:
            try:
                result = await self._execute_query(query)
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"Error executing query {query.query_id}: {e}")
                continue
        
        return results
    
    async def _execute_query(self, query: DuneQuery) -> Optional[Dict[str, Any]]:
        """Execute a single Dune Analytics query"""
        try:
            headers = {
                "X-Dune-API-Key": self.api_key,
                "Content-Type": "application/json"
            }
            
            # Execute the query
            execute_url = f"{self.base_url}/query/{query.query_id}/execute"
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    execute_url,
                    headers=headers,
                    json=query.parameters or {},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 200:
                        execute_data = await response.json()
                        execution_id = execute_data.get("execution_id")
                        
                        if execution_id:
                            # Wait for query to complete and get results
                            results = await self._get_query_results(execution_id)
                            return {
                                "query_id": query.query_id,
                                "name": query.name,
                                "results": results
                            }
                    else:
                        logger.error(f"Dune query execution failed: {response.status}")
                        
        except Exception as e:
            logger.error(f"Error executing Dune query {query.query_id}: {e}")
        
        return None
    
    async def _get_query_results(self, execution_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get results from a completed query execution"""
        try:
            headers = {
                "X-Dune-API-Key": self.api_key
            }
            
            # Poll for results
            max_attempts = 10
            for attempt in range(max_attempts):
                results_url = f"{self.base_url}/execution/{execution_id}/results"
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        results_url,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        
                        if response.status == 200:
                            data = await response.json()
                            if data.get("state") == "QUERY_STATE_COMPLETED":
                                return data.get("result", {}).get("rows", [])
                            elif data.get("state") == "QUERY_STATE_FAILED":
                                logger.error(f"Query execution failed: {data.get('error')}")
                                return None
                        
                        # Wait before next attempt
                        await asyncio.sleep(2)
                        
        except Exception as e:
            logger.error(f"Error getting query results: {e}")
        
        return None
    
    def _calculate_transaction_volume(self, query_results: List[Dict[str, Any]]) -> Optional[float]:
        """Calculate transaction volume from query results"""
        try:
            total_volume = 0.0
            valid_results = 0
            
            for result in query_results:
                if "transaction" in result["name"].lower() or "volume" in result["name"].lower():
                    rows = result.get("results", [])
                    if rows:
                        # Sum up volume from the most recent data
                        for row in rows[-5:]:  # Last 5 rows
                            volume = self._extract_numeric_value(row, ["volume", "tx_volume", "daily_volume"])
                            if volume is not None:
                                total_volume += volume
                                valid_results += 1
            
            return total_volume / max(1, valid_results) if valid_results > 0 else None
            
        except Exception as e:
            logger.error(f"Error calculating transaction volume: {e}")
            return None
    
    def _calculate_active_addresses(self, query_results: List[Dict[str, Any]]) -> Optional[float]:
        """Calculate active addresses from query results"""
        try:
            total_addresses = 0.0
            valid_results = 0
            
            for result in query_results:
                if "address" in result["name"].lower() or "active" in result["name"].lower():
                    rows = result.get("results", [])
                    if rows:
                        # Get the most recent active address count
                        for row in rows[-3:]:  # Last 3 rows
                            addresses = self._extract_numeric_value(row, ["addresses", "active_addresses", "daily_addresses"])
                            if addresses is not None:
                                total_addresses += addresses
                                valid_results += 1
            
            return total_addresses / max(1, valid_results) if valid_results > 0 else None
            
        except Exception as e:
            logger.error(f"Error calculating active addresses: {e}")
            return None
    
    def _calculate_whale_movements(self, query_results: List[Dict[str, Any]]) -> Optional[float]:
        """Calculate whale movements from query results"""
        try:
            total_movements = 0.0
            valid_results = 0
            
            for result in query_results:
                if "whale" in result["name"].lower() or "large" in result["name"].lower():
                    rows = result.get("results", [])
                    if rows:
                        # Count large transactions
                        for row in rows[-10:]:  # Last 10 rows
                            movements = self._extract_numeric_value(row, ["movements", "large_txs", "whale_txs"])
                            if movements is not None:
                                total_movements += movements
                                valid_results += 1
            
            return total_movements / max(1, valid_results) if valid_results > 0 else None
            
        except Exception as e:
            logger.error(f"Error calculating whale movements: {e}")
            return None
    
    def _calculate_defi_tvl(self, query_results: List[Dict[str, Any]]) -> Optional[float]:
        """Calculate DeFi TVL from query results"""
        try:
            total_tvl = 0.0
            valid_results = 0
            
            for result in query_results:
                if "tvl" in result["name"].lower() or "defi" in result["name"].lower():
                    rows = result.get("results", [])
                    if rows:
                        # Get the most recent TVL
                        for row in rows[-5:]:  # Last 5 rows
                            tvl = self._extract_numeric_value(row, ["tvl", "total_tvl", "defi_tvl"])
                            if tvl is not None:
                                total_tvl += tvl
                                valid_results += 1
            
            return total_tvl / max(1, valid_results) if valid_results > 0 else None
            
        except Exception as e:
            logger.error(f"Error calculating DeFi TVL: {e}")
            return None
    
    def _extract_numeric_value(self, row: Dict[str, Any], possible_keys: List[str]) -> Optional[float]:
        """Extract numeric value from a row using possible key names"""
        try:
            for key in possible_keys:
                if key in row:
                    value = row[key]
                    if isinstance(value, (int, float)):
                        return float(value)
                    elif isinstance(value, str):
                        # Try to parse as float
                        try:
                            return float(value.replace(",", "").replace("$", ""))
                        except ValueError:
                            continue
            
            # If no specific keys found, try to find any numeric value
            for key, value in row.items():
                if isinstance(value, (int, float)) and value > 0:
                    return float(value)
                    
        except Exception as e:
            logger.error(f"Error extracting numeric value: {e}")
        
        return None


# Import logger
import logging
logger = logging.getLogger(__name__)
