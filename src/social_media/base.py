"""
Base classes for social media data sources

Defines the abstract base class and data structures used by all social media sources.
"""

import logging
import aiohttp
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SocialDataPoint:
    """Individual data point from a social media source"""
    timestamp: datetime
    source: str
    coin_id: str
    data_type: str
    value: float
    confidence: float
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SocialDataBatch:
    """Batch of social data points from a single source"""
    coin_id: str
    data_points: List[SocialDataPoint]
    source: str
    timestamp: datetime
    quality_score: float = 1.0
    
    def get_latest(self, data_type: str) -> Optional[SocialDataPoint]:
        """Get the latest data point of a specific type"""
        filtered_points = [dp for dp in self.data_points if dp.data_type == data_type]
        if not filtered_points:
            return None
        return max(filtered_points, key=lambda x: x.timestamp)
    
    def get_average(self, data_type: str) -> Optional[float]:
        """Get average value for a specific data type"""
        filtered_points = [dp for dp in self.data_points 
                          if dp.data_type == data_type and isinstance(dp.value, (int, float))]
        if not filtered_points:
            return None
        return sum(dp.value for dp in filtered_points) / len(filtered_points)


class RateLimiter:
    """Simple rate limiter for API calls"""
    
    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    async def acquire(self):
        """Acquire permission to make a request"""
        now = datetime.now()
        
        # Remove old requests outside the time window
        self.requests = [
            req_time for req_time in self.requests
            if (now - req_time).total_seconds() < self.time_window
        ]
        
        # Check if we can make a request
        if len(self.requests) >= self.max_requests:
            # Calculate wait time
            oldest_request = min(self.requests)
            wait_time = self.time_window - (now - oldest_request).total_seconds()
            if wait_time > 0:
                import asyncio
                await asyncio.sleep(wait_time)
                return await self.acquire()
        
        # Record this request
        self.requests.append(now)


class BaseSocialDataSource(ABC):
    """Abstract base class for all social media data sources"""
    
    def __init__(self, config, source_name: str):
        self.config = config
        self.source_name = source_name
        self.cache = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limiter: Optional[RateLimiter] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"User-Agent": "CryptoTracker/1.0"}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    @abstractmethod
    async def fetch_data(self, coin_id: str, data_types: List[str]) -> SocialDataBatch:
        """Fetch data for a specific coin and data types"""
        pass
    
    def _get_cached_data(self, cache_key: str) -> Optional[SocialDataBatch]:
        """Get cached data if available and not expired"""
        if cache_key in self.cache:
            cached_item = self.cache[cache_key]
            if datetime.now() < cached_item['expires']:
                return cached_item['data']
            else:
                # Remove expired cache
                del self.cache[cache_key]
        return None
    
    def _cache_data(self, cache_key: str, data: SocialDataBatch):
        """Cache data with expiration time"""
        cache_ttl = getattr(self.config, 'cache_ttl', 300)  # Default 5 minutes
        expires = datetime.now().timestamp() + cache_ttl
        
        self.cache[cache_key] = {
            'data': data,
            'expires': datetime.fromtimestamp(expires)
        }
        
        # Clean up old cache entries
        now = datetime.now()
        expired_keys = [
            key for key, item in self.cache.items()
            if now >= item['expires']
        ]
        for key in expired_keys:
            del self.cache[key]
    
    async def _get_smart_cached_data(self, coin_id: str, data_type: str, 
                                   params: Dict[str, Any] = None) -> Optional[Any]:
        """Get data from smart cache - fallback to simple cache for now"""
        # For now, use the simple cache until smart cache is fully implemented
        cache_key = f"{self.source_name}_{coin_id}_{data_type}"
        return self._get_cached_data(cache_key)
    
    async def _cache_smart_data(self, coin_id: str, data_type: str, data: Any,
                              params: Dict[str, Any] = None, custom_ttl: int = None) -> bool:
        """Cache data using smart cache - fallback to simple cache for now"""
        # For now, use the simple cache until smart cache is fully implemented
        cache_key = f"{self.source_name}_{coin_id}_{data_type}"
        self._cache_data(cache_key, data)
        return True
