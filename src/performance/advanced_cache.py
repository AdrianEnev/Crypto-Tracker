"""
Advanced Caching System for Performance Optimization

Provides multi-level caching with Redis, in-memory, and disk-based storage
for improved performance and reduced latency.
"""

import asyncio
import json
import pickle
import hashlib
import logging
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
import time
from contextlib import asynccontextmanager

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from cachetools import TTLCache, LRUCache


@dataclass
class CacheStats:
    """Cache statistics."""
    hits: int
    misses: int
    sets: int
    deletes: int
    size: int
    max_size: int
    hit_rate: float
    last_activity: datetime


class InMemoryCache:
    """
    High-performance in-memory cache with TTL and LRU eviction.
    
    Features:
    - TTL-based expiration
    - LRU eviction policy
    - Thread-safe operations
    - Performance metrics
    - Configurable size limits
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Cache configuration
        self.max_size = config.get('max_size', 1000)
        self.ttl_seconds = config.get('ttl_seconds', 300)  # 5 minutes default
        self.cleanup_interval = config.get('cleanup_interval', 60)  # 1 minute
        
        # Create cache with TTL and LRU
        self.cache = TTLCache(
            maxsize=self.max_size,
            ttl=self.ttl_seconds
        )
        
        # Statistics
        self.stats = CacheStats(
            hits=0,
            misses=0,
            sets=0,
            deletes=0,
            size=0,
            max_size=self.max_size,
            hit_rate=0.0,
            last_activity=datetime.now(timezone.utc)
        )
        
        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize the cache."""
        try:
            # Start cleanup task
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            self.logger.info(f"In-memory cache initialized: max_size={self.max_size}, ttl={self.ttl_seconds}s")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize in-memory cache: {e}")
            raise
    
    async def close(self):
        """Close the cache and cleanup resources."""
        try:
            if self._cleanup_task:
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass
            
            self.cache.clear()
            self.logger.info("In-memory cache closed")
            
        except Exception as e:
            self.logger.error(f"Error closing in-memory cache: {e}")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            async with self._lock:
                if key in self.cache:
                    self.stats.hits += 1
                    self.stats.last_activity = datetime.now(timezone.utc)
                    self._update_hit_rate()
                    return self.cache[key]
                else:
                    self.stats.misses += 1
                    self._update_hit_rate()
                    return None
                    
        except Exception as e:
            self.logger.error(f"Cache get failed for key '{key}': {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        try:
            async with self._lock:
                self.cache[key] = value
                self.stats.sets += 1
                self.stats.size = len(self.cache)
                self.stats.last_activity = datetime.now(timezone.utc)
                return True
                
        except Exception as e:
            self.logger.error(f"Cache set failed for key '{key}': {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            async with self._lock:
                if key in self.cache:
                    del self.cache[key]
                    self.stats.deletes += 1
                    self.stats.size = len(self.cache)
                    self.stats.last_activity = datetime.now(timezone.utc)
                    return True
                return False
                
        except Exception as e:
            self.logger.error(f"Cache delete failed for key '{key}': {e}")
            return False
    
    async def clear(self):
        """Clear all cache entries."""
        try:
            async with self._lock:
                self.cache.clear()
                self.stats.size = 0
                self.stats.last_activity = datetime.now(timezone.utc)
                
        except Exception as e:
            self.logger.error(f"Cache clear failed: {e}")
    
    def _update_hit_rate(self):
        """Update cache hit rate."""
        total_requests = self.stats.hits + self.stats.misses
        if total_requests > 0:
            self.stats.hit_rate = self.stats.hits / total_requests
    
    async def _cleanup_loop(self):
        """Background cleanup task."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                # TTL cache automatically handles expiration
                # This is just for logging and statistics
                async with self._lock:
                    self.stats.size = len(self.cache)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Cache cleanup failed: {e}")
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        return self.stats


class RedisCache:
    """
    Redis-based distributed cache.
    
    Features:
    - Distributed caching across multiple instances
    - Persistence and durability
    - Advanced data structures
    - Pub/Sub for cache invalidation
    - Cluster support
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        if not REDIS_AVAILABLE:
            raise ImportError("Redis not available. Install with: pip install redis")
        
        # Redis configuration
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 6379)
        self.db = config.get('db', 0)
        self.password = config.get('password')
        self.ssl = config.get('ssl', False)
        self.ttl_seconds = config.get('ttl_seconds', 300)
        
        # Connection pool configuration
        self.max_connections = config.get('max_connections', 20)
        self.retry_on_timeout = config.get('retry_on_timeout', True)
        self.socket_keepalive = config.get('socket_keepalive', True)
        self.socket_keepalive_options = config.get('socket_keepalive_options', {})
        
        # Redis connection
        self.redis: Optional[redis.Redis] = None
        
        # Statistics
        self.stats = CacheStats(
            hits=0,
            misses=0,
            sets=0,
            deletes=0,
            size=0,
            max_size=0,
            hit_rate=0.0,
            last_activity=datetime.now(timezone.utc)
        )
    
    async def initialize(self):
        """Initialize Redis connection."""
        try:
            # Create Redis connection pool
            self.redis = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                ssl=self.ssl,
                max_connections=self.max_connections,
                retry_on_timeout=self.retry_on_timeout,
                socket_keepalive=self.socket_keepalive,
                socket_keepalive_options=self.socket_keepalive_options,
                decode_responses=False  # We'll handle encoding/decoding ourselves
            )
            
            # Test connection
            await self.redis.ping()
            
            # Get Redis info
            info = await self.redis.info()
            self.stats.max_size = info.get('used_memory', 0)
            
            self.logger.info(f"Redis cache initialized: {self.host}:{self.port}, db={self.db}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Redis cache: {e}")
            raise
    
    async def close(self):
        """Close Redis connection."""
        try:
            if self.redis:
                await self.redis.close()
                self.logger.info("Redis cache closed")
                
        except Exception as e:
            self.logger.error(f"Error closing Redis cache: {e}")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache."""
        try:
            if not self.redis:
                return None
            
            data = await self.redis.get(key)
            if data is not None:
                self.stats.hits += 1
                self.stats.last_activity = datetime.now(timezone.utc)
                self._update_hit_rate()
                
                # Deserialize data
                try:
                    return pickle.loads(data)
                except:
                    # Fallback to JSON
                    return json.loads(data.decode('utf-8'))
            else:
                self.stats.misses += 1
                self._update_hit_rate()
                return None
                
        except Exception as e:
            self.logger.error(f"Redis get failed for key '{key}': {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis cache."""
        try:
            if not self.redis:
                return False
            
            # Serialize data
            try:
                data = pickle.dumps(value)
            except:
                # Fallback to JSON
                data = json.dumps(value).encode('utf-8')
            
            # Set with TTL
            ttl = ttl or self.ttl_seconds
            await self.redis.setex(key, ttl, data)
            
            self.stats.sets += 1
            self.stats.last_activity = datetime.now(timezone.utc)
            return True
            
        except Exception as e:
            self.logger.error(f"Redis set failed for key '{key}': {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from Redis cache."""
        try:
            if not self.redis:
                return False
            
            result = await self.redis.delete(key)
            if result > 0:
                self.stats.deletes += 1
                self.stats.last_activity = datetime.now(timezone.utc)
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Redis delete failed for key '{key}': {e}")
            return False
    
    async def clear(self):
        """Clear all cache entries."""
        try:
            if self.redis:
                await self.redis.flushdb()
                self.stats.last_activity = datetime.now(timezone.utc)
                
        except Exception as e:
            self.logger.error(f"Redis clear failed: {e}")
    
    def _update_hit_rate(self):
        """Update cache hit rate."""
        total_requests = self.stats.hits + self.stats.misses
        if total_requests > 0:
            self.stats.hit_rate = self.stats.hits / total_requests
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        return self.stats


class DiskCache:
    """
    Disk-based cache for large data persistence.
    
    Features:
    - File-based storage
    - Automatic cleanup of expired files
    - Compression for large data
    - Atomic operations
    - Directory structure organization
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Cache configuration
        self.cache_dir = Path(config.get('cache_dir', 'cache/disk'))
        self.max_size_mb = config.get('max_size_mb', 1000)  # 1GB default
        self.ttl_seconds = config.get('ttl_seconds', 3600)  # 1 hour default
        self.cleanup_interval = config.get('cleanup_interval', 300)  # 5 minutes
        self.compression = config.get('compression', True)
        
        # Create cache directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Statistics
        self.stats = CacheStats(
            hits=0,
            misses=0,
            sets=0,
            deletes=0,
            size=0,
            max_size=self.max_size_mb * 1024 * 1024,  # Convert to bytes
            hit_rate=0.0,
            last_activity=datetime.now(timezone.utc)
        )
        
        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize the disk cache."""
        try:
            # Start cleanup task
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            self.logger.info(f"Disk cache initialized: {self.cache_dir}, max_size={self.max_size_mb}MB")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize disk cache: {e}")
            raise
    
    async def close(self):
        """Close the disk cache."""
        try:
            if self._cleanup_task:
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass
            
            self.logger.info("Disk cache closed")
            
        except Exception as e:
            self.logger.error(f"Error closing disk cache: {e}")
    
    def _get_file_path(self, key: str) -> Path:
        """Get file path for cache key."""
        # Create hash of key for filename
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from disk cache."""
        try:
            file_path = self._get_file_path(key)
            
            if not file_path.exists():
                self.stats.misses += 1
                self._update_hit_rate()
                return None
            
            # Check if file is expired
            file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
            if datetime.now(timezone.utc) - file_mtime > timedelta(seconds=self.ttl_seconds):
                # File expired, delete it
                file_path.unlink()
                self.stats.misses += 1
                self._update_hit_rate()
                return None
            
            # Read and deserialize data
            async with self._lock:
                with open(file_path, 'rb') as f:
                    data = f.read()
                
                if self.compression:
                    import gzip
                    data = gzip.decompress(data)
                
                value = pickle.loads(data)
                
                self.stats.hits += 1
                self.stats.last_activity = datetime.now(timezone.utc)
                self._update_hit_rate()
                return value
                
        except Exception as e:
            self.logger.error(f"Disk cache get failed for key '{key}': {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in disk cache."""
        try:
            file_path = self._get_file_path(key)
            
            # Serialize data
            data = pickle.dumps(value)
            
            if self.compression:
                import gzip
                data = gzip.compress(data)
            
            # Write atomically
            temp_path = file_path.with_suffix('.tmp')
            
            async with self._lock:
                with open(temp_path, 'wb') as f:
                    f.write(data)
                
                # Atomic move
                temp_path.replace(file_path)
                
                self.stats.sets += 1
                self.stats.last_activity = datetime.now(timezone.utc)
                return True
                
        except Exception as e:
            self.logger.error(f"Disk cache set failed for key '{key}': {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from disk cache."""
        try:
            file_path = self._get_file_path(key)
            
            if file_path.exists():
                file_path.unlink()
                self.stats.deletes += 1
                self.stats.last_activity = datetime.now(timezone.utc)
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Disk cache delete failed for key '{key}': {e}")
            return False
    
    async def clear(self):
        """Clear all cache entries."""
        try:
            async with self._lock:
                for file_path in self.cache_dir.glob("*.cache"):
                    file_path.unlink()
                
                self.stats.last_activity = datetime.now(timezone.utc)
                
        except Exception as e:
            self.logger.error(f"Disk cache clear failed: {e}")
    
    async def _cleanup_loop(self):
        """Background cleanup task."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                # Clean up expired files
                current_time = datetime.now(timezone.utc)
                expired_files = []
                
                for file_path in self.cache_dir.glob("*.cache"):
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
                    if current_time - file_mtime > timedelta(seconds=self.ttl_seconds):
                        expired_files.append(file_path)
                
                # Delete expired files
                for file_path in expired_files:
                    try:
                        file_path.unlink()
                    except Exception as e:
                        self.logger.warning(f"Failed to delete expired cache file {file_path}: {e}")
                
                # Update size statistics
                total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.cache"))
                self.stats.size = total_size
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Disk cache cleanup failed: {e}")
    
    def _update_hit_rate(self):
        """Update cache hit rate."""
        total_requests = self.stats.hits + self.stats.misses
        if total_requests > 0:
            self.stats.hit_rate = self.stats.hits / total_requests
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        return self.stats


class MultiLevelCache:
    """
    Multi-level cache with L1 (in-memory), L2 (Redis), and L3 (disk) storage.
    
    Features:
    - Hierarchical caching strategy
    - Automatic promotion/demotion
    - Configurable cache levels
    - Performance optimization
    - Cache coherence
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Cache levels
        self.l1_cache: Optional[InMemoryCache] = None
        self.l2_cache: Optional[RedisCache] = None
        self.l3_cache: Optional[DiskCache] = None
        
        # Configuration
        self.enable_l1 = config.get('enable_l1', True)
        self.enable_l2 = config.get('enable_l2', False)
        self.enable_l3 = config.get('enable_l3', True)
        
        # Cache promotion/demotion thresholds
        self.promotion_threshold = config.get('promotion_threshold', 3)  # Access count
        self.demotion_threshold = config.get('demotion_threshold', 0.1)  # Hit rate
        
        # Access tracking
        self._access_counts: Dict[str, int] = {}
        self._access_times: Dict[str, datetime] = {}
    
    async def initialize(self):
        """Initialize all cache levels."""
        try:
            # Initialize L1 cache (in-memory)
            if self.enable_l1:
                l1_config = self.config.get('l1', {})
                self.l1_cache = InMemoryCache(l1_config)
                await self.l1_cache.initialize()
                self.logger.info("L1 cache (in-memory) initialized")
            
            # Initialize L2 cache (Redis)
            if self.enable_l2:
                l2_config = self.config.get('l2', {})
                self.l2_cache = RedisCache(l2_config)
                await self.l2_cache.initialize()
                self.logger.info("L2 cache (Redis) initialized")
            
            # Initialize L3 cache (disk)
            if self.enable_l3:
                l3_config = self.config.get('l3', {})
                self.l3_cache = DiskCache(l3_config)
                await self.l3_cache.initialize()
                self.logger.info("L3 cache (disk) initialized")
            
            self.logger.info("Multi-level cache initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize multi-level cache: {e}")
            raise
    
    async def close(self):
        """Close all cache levels."""
        try:
            if self.l1_cache:
                await self.l1_cache.close()
            if self.l2_cache:
                await self.l2_cache.close()
            if self.l3_cache:
                await self.l3_cache.close()
            
            self.logger.info("Multi-level cache closed")
            
        except Exception as e:
            self.logger.error(f"Error closing multi-level cache: {e}")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from multi-level cache."""
        try:
            # Track access
            self._access_counts[key] = self._access_counts.get(key, 0) + 1
            self._access_times[key] = datetime.now(timezone.utc)
            
            # Try L1 cache first
            if self.l1_cache:
                value = await self.l1_cache.get(key)
                if value is not None:
                    return value
            
            # Try L2 cache
            if self.l2_cache:
                value = await self.l2_cache.get(key)
                if value is not None:
                    # Promote to L1 cache
                    if self.l1_cache:
                        await self.l1_cache.set(key, value)
                    return value
            
            # Try L3 cache
            if self.l3_cache:
                value = await self.l3_cache.get(key)
                if value is not None:
                    # Promote to L2 and L1 caches
                    if self.l2_cache:
                        await self.l2_cache.set(key, value)
                    if self.l1_cache:
                        await self.l1_cache.set(key, value)
                    return value
            
            return None
            
        except Exception as e:
            self.logger.error(f"Multi-level cache get failed for key '{key}': {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in multi-level cache."""
        try:
            success = True
            
            # Set in L1 cache
            if self.l1_cache:
                success &= await self.l1_cache.set(key, value, ttl)
            
            # Set in L2 cache
            if self.l2_cache:
                success &= await self.l2_cache.set(key, value, ttl)
            
            # Set in L3 cache
            if self.l3_cache:
                success &= await self.l3_cache.set(key, value, ttl)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Multi-level cache set failed for key '{key}': {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from all cache levels."""
        try:
            success = True
            
            # Delete from all levels
            if self.l1_cache:
                success &= await self.l1_cache.delete(key)
            if self.l2_cache:
                success &= await self.l2_cache.delete(key)
            if self.l3_cache:
                success &= await self.l3_cache.delete(key)
            
            # Clean up access tracking
            self._access_counts.pop(key, None)
            self._access_times.pop(key, None)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Multi-level cache delete failed for key '{key}': {e}")
            return False
    
    async def clear(self):
        """Clear all cache levels."""
        try:
            if self.l1_cache:
                await self.l1_cache.clear()
            if self.l2_cache:
                await self.l2_cache.clear()
            if self.l3_cache:
                await self.l3_cache.clear()
            
            # Clear access tracking
            self._access_counts.clear()
            self._access_times.clear()
            
        except Exception as e:
            self.logger.error(f"Multi-level cache clear failed: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all cache levels."""
        stats = {
            'l1_cache': self.l1_cache.get_stats() if self.l1_cache else None,
            'l2_cache': self.l2_cache.get_stats() if self.l2_cache else None,
            'l3_cache': self.l3_cache.get_stats() if self.l3_cache else None,
            'access_tracking': {
                'total_keys': len(self._access_counts),
                'most_accessed': max(self._access_counts.items(), key=lambda x: x[1]) if self._access_counts else None
            }
        }
        
        return stats
