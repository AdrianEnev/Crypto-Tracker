"""
Smart Caching System for Social Media Data

Implements intelligent caching strategies to reduce API calls and improve performance.
Features:
- Multi-level caching (memory, disk, Redis)
- Adaptive TTL based on data volatility
- Cache warming and prefetching
- Cache invalidation strategies
- Performance monitoring
"""

import asyncio
import json
import time
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
import logging
import pickle
import threading
from collections import defaultdict, deque

logger = logging.getLogger(__name__)
# Reduce default logging verbosity
logger.setLevel(logging.WARNING)


@dataclass
class CacheEntry:
    """Single cache entry with metadata"""
    data: Any
    timestamp: float
    ttl: int
    access_count: int = 0
    last_access: float = field(default_factory=time.time)
    source: str = ""
    coin_id: str = ""
    data_type: str = ""
    quality_score: float = 1.0
    volatility_score: float = 0.0
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        return time.time() - self.timestamp > self.ttl
    
    def is_stale(self, staleness_threshold: float = 0.5) -> bool:
        """Check if cache entry is stale based on volatility"""
        age = time.time() - self.timestamp
        max_age = self.ttl * staleness_threshold
        return age > max_age and self.volatility_score > 0.3
    
    def should_refresh(self) -> bool:
        """Determine if entry should be refreshed based on access patterns"""
        if self.access_count < 2:
            return False
        
        # Refresh if frequently accessed and not too recent
        time_since_access = time.time() - self.last_access
        return time_since_access < 300 and self.access_count > 5


@dataclass
class CacheStats:
    """Cache performance statistics"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    refreshes: int = 0
    total_requests: int = 0
    hit_rate: float = 0.0
    avg_response_time: float = 0.0
    cache_size: int = 0
    memory_usage: float = 0.0
    
    def update_hit_rate(self):
        """Update hit rate calculation"""
        if self.total_requests > 0:
            self.hit_rate = self.hits / self.total_requests


class CacheBackend(ABC):
    """Abstract base class for cache backends"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[CacheEntry]:
        """Get cache entry by key"""
        pass
    
    @abstractmethod
    async def set(self, key: str, entry: CacheEntry) -> bool:
        """Set cache entry"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete cache entry"""
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cache entries"""
        pass
    
    @abstractmethod
    async def size(self) -> int:
        """Get cache size"""
        pass


class MemoryCacheBackend(CacheBackend):
    """In-memory cache backend with LRU eviction"""
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.cache: Dict[str, CacheEntry] = {}
        self.access_order: deque = deque()
        self.lock = threading.RLock()
    
    async def get(self, key: str) -> Optional[CacheEntry]:
        """Get cache entry with LRU update"""
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                if not entry.is_expired():
                    # Update LRU order
                    if key in self.access_order:
                        self.access_order.remove(key)
                    self.access_order.append(key)
                    
                    # Update access stats
                    entry.access_count += 1
                    entry.last_access = time.time()
                    return entry
                else:
                    # Remove expired entry
                    del self.cache[key]
                    if key in self.access_order:
                        self.access_order.remove(key)
            return None
    
    async def set(self, key: str, entry: CacheEntry) -> bool:
        """Set cache entry with LRU eviction if needed"""
        with self.lock:
            # Evict if at capacity
            if len(self.cache) >= self.max_size and key not in self.cache:
                await self._evict_lru()
            
            self.cache[key] = entry
            if key in self.access_order:
                self.access_order.remove(key)
            self.access_order.append(key)
            return True
    
    async def delete(self, key: str) -> bool:
        """Delete cache entry"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                if key in self.access_order:
                    self.access_order.remove(key)
                return True
            return False
    
    async def clear(self) -> bool:
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
            self.access_order.clear()
            return True
    
    async def size(self) -> int:
        """Get cache size"""
        with self.lock:
            return len(self.cache)
    
    async def _evict_lru(self):
        """Evict least recently used entry"""
        if self.access_order:
            lru_key = self.access_order.popleft()
            if lru_key in self.cache:
                del self.cache[lru_key]


class DiskCacheBackend(CacheBackend):
    """Disk-based cache backend with compression"""
    
    def __init__(self, cache_dir: str = "./cache", max_size_mb: int = 1000):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.lock = threading.RLock()
    
    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path for key"""
        # Create hash to avoid filesystem issues with special characters
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"
    
    async def get(self, key: str) -> Optional[CacheEntry]:
        """Get cache entry from disk"""
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            return None
        
        try:
            with self.lock:
                with open(cache_path, 'rb') as f:
                    entry = pickle.load(f)
                
                if entry.is_expired():
                    cache_path.unlink()
                    return None
                
                # Update access stats
                entry.access_count += 1
                entry.last_access = time.time()
                
                # Save updated entry
                with open(cache_path, 'wb') as f:
                    pickle.dump(entry, f)
                
                return entry
                
        except Exception as e:
            logger.error(f"Error reading cache file {cache_path}: {e}")
            # Remove corrupted file
            try:
                cache_path.unlink()
            except:
                pass
            return None
    
    async def set(self, key: str, entry: CacheEntry) -> bool:
        """Set cache entry to disk"""
        cache_path = self._get_cache_path(key)
        
        try:
            with self.lock:
                with open(cache_path, 'wb') as f:
                    pickle.dump(entry, f)
                
                # Check size limit and evict if needed
                await self._check_size_limit()
                return True
                
        except Exception as e:
            logger.error(f"Error writing cache file {cache_path}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete cache entry from disk"""
        cache_path = self._get_cache_path(key)
        
        try:
            with self.lock:
                if cache_path.exists():
                    cache_path.unlink()
                    return True
            return False
        except Exception as e:
            logger.error(f"Error deleting cache file {cache_path}: {e}")
            return False
    
    async def clear(self) -> bool:
        """Clear all cache files"""
        try:
            with self.lock:
                for cache_file in self.cache_dir.glob("*.cache"):
                    cache_file.unlink()
            return True
        except Exception as e:
            logger.error(f"Error clearing cache directory: {e}")
            return False
    
    async def size(self) -> int:
        """Get cache size (number of files)"""
        try:
            return len(list(self.cache_dir.glob("*.cache")))
        except:
            return 0
    
    async def _check_size_limit(self):
        """Check and enforce size limit"""
        try:
            total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.cache"))
            if total_size > self.max_size_bytes:
                # Remove oldest files
                files = [(f, f.stat().st_mtime) for f in self.cache_dir.glob("*.cache")]
                files.sort(key=lambda x: x[1])  # Sort by modification time
                
                # Remove oldest files until under limit
                for file_path, _ in files:
                    total_size -= file_path.stat().st_size
                    file_path.unlink()
                    if total_size <= self.max_size_bytes:
                        break
        except Exception as e:
            logger.error(f"Error checking size limit: {e}")


class SmartCache:
    """Smart caching system with multiple backends and intelligent strategies"""
    
    def __init__(self, 
                 memory_size: int = 1000,
                 disk_cache_dir: str = "./cache",
                 disk_size_mb: int = 500,
                 enable_redis: bool = False,
                 redis_url: str = "redis://localhost:6379"):
        
        self.memory_backend = MemoryCacheBackend(memory_size)
        self.disk_backend = DiskCacheBackend(disk_cache_dir, disk_size_mb)
        self.redis_backend = None
        
        if enable_redis:
            try:
                import redis.asyncio as redis
                self.redis_backend = redis.from_url(redis_url)
            except ImportError:
                logger.warning("Redis not available, using memory and disk only")
        
        # Cache statistics
        self.stats = CacheStats()
        
        # Volatility tracking for adaptive TTL
        self.volatility_tracker: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10))
        
        # Cache warming tasks
        self.warming_tasks: Dict[str, asyncio.Task] = {}
        
        # Background cleanup task
        self.cleanup_task = None
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """Start background maintenance tasks"""
        if self.cleanup_task is None or self.cleanup_task.done():
            self.cleanup_task = asyncio.create_task(self._background_cleanup())
    
    async def _background_cleanup(self):
        """Background task for cache maintenance"""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                await self._cleanup_expired()
                await self._update_volatility_scores()
            except Exception as e:
                logger.error(f"Error in background cleanup: {e}")
    
    async def _cleanup_expired(self):
        """Remove expired entries from all backends"""
        # Memory backend cleanup is handled by LRU eviction
        # Disk backend cleanup
        cache_dir = Path(self.disk_backend.cache_dir)
        for cache_file in cache_dir.glob("*.cache"):
            try:
                with open(cache_file, 'rb') as f:
                    entry = pickle.load(f)
                if entry.is_expired():
                    cache_file.unlink()
            except:
                # Remove corrupted files
                try:
                    cache_file.unlink()
                except:
                    pass
    
    async def _update_volatility_scores(self):
        """Update volatility scores for adaptive TTL"""
        # This would analyze historical data patterns
        # For now, we'll use a simple heuristic
        pass
    
    def _generate_cache_key(self, source: str, coin_id: str, data_type: str, 
                           params: Dict[str, Any] = None) -> str:
        """Generate cache key with parameters"""
        key_parts = [source, coin_id, data_type]
        if params:
            # Sort params for consistent keys
            sorted_params = sorted(params.items())
            key_parts.append(json.dumps(sorted_params, sort_keys=True))
        return "|".join(key_parts)
    
    def _calculate_adaptive_ttl(self, source: str, coin_id: str, data_type: str) -> int:
        """Calculate adaptive TTL based on data volatility and source"""
        base_ttls = {
            "twitter": 300,      # 5 minutes - high volatility
            "reddit": 600,       # 10 minutes - medium volatility
            "news_api": 1800,    # 30 minutes - lower volatility
            "santiment": 900,    # 15 minutes - medium volatility
            "exchange_api": 300, # 5 minutes - high volatility
            "dune_analytics": 1800, # 30 minutes - lower volatility
            "google_trends": 3600,  # 1 hour - low volatility
        }
        
        base_ttl = base_ttls.get(source, 600)  # Default 10 minutes
        
        # Adjust based on volatility
        volatility_key = f"{source}_{coin_id}_{data_type}"
        if volatility_key in self.volatility_tracker:
            recent_values = list(self.volatility_tracker[volatility_key])
            if len(recent_values) > 3:
                # Calculate volatility (simplified)
                volatility = max(recent_values) - min(recent_values)
                if volatility > 0.5:  # High volatility
                    base_ttl = int(base_ttl * 0.5)  # Reduce TTL
                elif volatility < 0.1:  # Low volatility
                    base_ttl = int(base_ttl * 1.5)  # Increase TTL
        
        return max(60, min(3600, base_ttl))  # Clamp between 1 minute and 1 hour
    
    async def get(self, source: str, coin_id: str, data_type: str, 
                  params: Dict[str, Any] = None) -> Optional[Any]:
        """Get cached data with multi-level fallback"""
        cache_key = self._generate_cache_key(source, coin_id, data_type, params)
        start_time = time.time()
        
        # Try memory cache first
        entry = await self.memory_backend.get(cache_key)
        if entry:
            self.stats.hits += 1
            self.stats.total_requests += 1
            self.stats.update_hit_rate()
            self.stats.avg_response_time = (
                (self.stats.avg_response_time * (self.stats.total_requests - 1) + 
                 (time.time() - start_time)) / self.stats.total_requests
            )
            return entry.data
        
        # Try disk cache
        entry = await self.disk_backend.get(cache_key)
        if entry:
            # Promote to memory cache
            await self.memory_backend.set(cache_key, entry)
            self.stats.hits += 1
            self.stats.total_requests += 1
            self.stats.update_hit_rate()
            return entry.data
        
        # Try Redis cache if available
        if self.redis_backend:
            try:
                cached_data = await self.redis_backend.get(cache_key)
                if cached_data:
                    entry = pickle.loads(cached_data)
                    if not entry.is_expired():
                        # Promote to memory and disk
                        await self.memory_backend.set(cache_key, entry)
                        await self.disk_backend.set(cache_key, entry)
                        self.stats.hits += 1
                        self.stats.total_requests += 1
                        self.stats.update_hit_rate()
                        return entry.data
            except Exception as e:
                logger.warning(f"Redis cache error: {e}")
        
        # Cache miss
        self.stats.misses += 1
        self.stats.total_requests += 1
        self.stats.update_hit_rate()
        return None
    
    async def set(self, source: str, coin_id: str, data_type: str, data: Any,
                  params: Dict[str, Any] = None, custom_ttl: int = None) -> bool:
        """Set cached data with intelligent TTL"""
        cache_key = self._generate_cache_key(source, coin_id, data_type, params)
        
        # Calculate TTL
        ttl = custom_ttl or self._calculate_adaptive_ttl(source, coin_id, data_type)
        
        # Create cache entry
        entry = CacheEntry(
            data=data,
            timestamp=time.time(),
            ttl=ttl,
            source=source,
            coin_id=coin_id,
            data_type=data_type,
            quality_score=self._calculate_quality_score(data),
            volatility_score=self._get_volatility_score(source, coin_id, data_type)
        )
        
        # Store in all backends
        success = True
        
        # Memory cache (always try)
        if not await self.memory_backend.set(cache_key, entry):
            success = False
        
        # Disk cache (for persistence)
        if not await self.disk_backend.set(cache_key, entry):
            success = False
        
        # Redis cache (if available)
        if self.redis_backend:
            try:
                await self.redis_backend.setex(
                    cache_key, 
                    ttl, 
                    pickle.dumps(entry)
                )
            except Exception as e:
                logger.warning(f"Redis set error: {e}")
                success = False
        
        return success
    
    def _calculate_quality_score(self, data: Any) -> float:
        """Calculate quality score for cached data"""
        if data is None:
            return 0.0
        
        if isinstance(data, dict):
            # Check for completeness
            required_fields = ['timestamp', 'value', 'confidence']
            completeness = sum(1 for field in required_fields if field in data) / len(required_fields)
            return completeness
        elif isinstance(data, list):
            # Non-empty list is good
            return 1.0 if data else 0.0
        else:
            return 1.0
    
    def _get_volatility_score(self, source: str, coin_id: str, data_type: str) -> float:
        """Get volatility score for adaptive TTL"""
        volatility_key = f"{source}_{coin_id}_{data_type}"
        if volatility_key in self.volatility_tracker:
            recent_values = list(self.volatility_tracker[volatility_key])
            if len(recent_values) > 1:
                return max(recent_values) - min(recent_values)
        return 0.0
    
    async def invalidate(self, source: str = None, coin_id: str = None, 
                        data_type: str = None) -> int:
        """Invalidate cache entries matching criteria"""
        invalidated = 0
        
        # This is a simplified implementation
        # In practice, you'd need to iterate through all keys
        # For now, we'll clear specific patterns
        
        if source and coin_id and data_type:
            cache_key = self._generate_cache_key(source, coin_id, data_type)
            if await self.memory_backend.delete(cache_key):
                invalidated += 1
            if await self.disk_backend.delete(cache_key):
                invalidated += 1
            if self.redis_backend:
                try:
                    if await self.redis_backend.delete(cache_key):
                        invalidated += 1
                except:
                    pass
        
        return invalidated
    
    async def warm_cache(self, source: str, coin_id: str, data_types: List[str],
                        fetch_func, params: Dict[str, Any] = None):
        """Warm cache with prefetched data"""
        warming_key = f"{source}_{coin_id}_{'_'.join(data_types)}"
        
        if warming_key in self.warming_tasks:
            return  # Already warming
        
        async def warm_task():
            try:
                for data_type in data_types:
                    # Check if already cached
                    cached = await self.get(source, coin_id, data_type, params)
                    if cached is None:
                        # Fetch and cache
                        data = await fetch_func(coin_id, data_type, params)
                        if data:
                            await self.set(source, coin_id, data_type, data, params)
                
                logger.info(f"Cache warming completed for {source}:{coin_id}")
            except Exception as e:
                logger.error(f"Cache warming failed for {source}:{coin_id}: {e}")
            finally:
                if warming_key in self.warming_tasks:
                    del self.warming_tasks[warming_key]
        
        self.warming_tasks[warming_key] = asyncio.create_task(warm_task())
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        return {
            "hits": self.stats.hits,
            "misses": self.stats.misses,
            "hit_rate": self.stats.hit_rate,
            "total_requests": self.stats.total_requests,
            "avg_response_time": self.stats.avg_response_time,
            "memory_size": asyncio.run(self.memory_backend.size()),
            "disk_size": asyncio.run(self.disk_backend.size()),
            "warming_tasks": len(self.warming_tasks)
        }
    
    async def clear_all(self):
        """Clear all caches"""
        await self.memory_backend.clear()
        await self.disk_backend.clear()
        if self.redis_backend:
            try:
                await self.redis_backend.flushdb()
            except:
                pass
        
        # Reset stats
        self.stats = CacheStats()
    
    async def close(self):
        """Close cache and cleanup resources"""
        # Cancel warming tasks
        for task in self.warming_tasks.values():
            task.cancel()
        
        # Cancel cleanup task
        if self.cleanup_task:
            self.cleanup_task.cancel()
        
        # Close Redis connection
        if self.redis_backend:
            try:
                await self.redis_backend.close()
            except:
                pass


# Global cache instance
_global_cache: Optional[SmartCache] = None


def get_global_cache() -> SmartCache:
    """Get or create global cache instance"""
    global _global_cache
    if _global_cache is None:
        _global_cache = SmartCache()
    return _global_cache


async def close_global_cache():
    """Close global cache instance"""
    global _global_cache
    if _global_cache:
        await _global_cache.close()
        _global_cache = None
