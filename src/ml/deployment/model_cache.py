"""
Model Cache for efficient model loading and caching.
Provides intelligent caching strategies and memory management.
"""

import time
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import hashlib
import pickle

logger = logging.getLogger(__name__)


class CachePolicy(Enum):
    """Cache eviction policies."""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    SIZE_BASED = "size_based"


@dataclass
class CacheMetrics:
    """Container for cache metrics."""
    timestamp: datetime
    cache_size: int
    cache_hits: int
    cache_misses: int
    evictions: int
    memory_usage_bytes: int
    hit_rate: float = 0.0
    miss_rate: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'cache_size': self.cache_size,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'evictions': self.evictions,
            'memory_usage_bytes': self.memory_usage_bytes,
            'hit_rate': self.hit_rate,
            'miss_rate': self.miss_rate
        }


@dataclass
class CacheEntry:
    """Container for cache entry."""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 1
    size_bytes: int = 0
    ttl_seconds: Optional[int] = None
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        if self.ttl_seconds is None:
            return False
        
        expiry_time = self.created_at + timedelta(seconds=self.ttl_seconds)
        return datetime.now(timezone.utc) > expiry_time
    
    def update_access(self) -> None:
        """Update access information."""
        self.last_accessed = datetime.now(timezone.utc)
        self.access_count += 1


class ModelCache:
    """
    Intelligent model cache with multiple eviction policies.
    """
    
    def __init__(self, 
                 max_size: int = 100,
                 max_memory_bytes: int = 1024 * 1024 * 1024,  # 1GB
                 eviction_policy: CachePolicy = CachePolicy.LRU,
                 default_ttl_seconds: Optional[int] = None,
                 cleanup_interval_seconds: int = 300):  # 5 minutes
        
        self.max_size = max_size
        self.max_memory_bytes = max_memory_bytes
        self.eviction_policy = eviction_policy
        self.default_ttl_seconds = default_ttl_seconds
        self.cleanup_interval_seconds = cleanup_interval_seconds
        
        # Cache storage
        self.cache: Dict[str, CacheEntry] = {}
        self.access_order: List[str] = []  # For LRU
        self.frequency_counter: Dict[str, int] = {}  # For LFU
        
        # Metrics
        self.cache_hits = 0
        self.cache_misses = 0
        self.evictions = 0
        self.total_memory_usage = 0
        
        # Threading
        self._lock = threading.RLock()
        
        # Cleanup task
        self._cleanup_task: Optional[threading.Timer] = None
        self._start_cleanup_task()
        
        logger.info(f"Initialized model cache: max_size={max_size}, max_memory={max_memory_bytes}, policy={eviction_policy.value}")
    
    def _start_cleanup_task(self) -> None:
        """Start the cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        self._cleanup_task = threading.Timer(
            self.cleanup_interval_seconds,
            self._cleanup_expired_entries
        )
        self._cleanup_task.daemon = True
        self._cleanup_task.start()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            if key not in self.cache:
                self.cache_misses += 1
                return None
            
            entry = self.cache[key]
            
            # Check if expired
            if entry.is_expired():
                self._remove_entry(key)
                self.cache_misses += 1
                return None
            
            # Update access information
            entry.update_access()
            self.cache_hits += 1
            
            # Update access order for LRU
            if self.eviction_policy == CachePolicy.LRU:
                self.access_order.remove(key)
                self.access_order.append(key)
            
            # Update frequency for LFU
            if self.eviction_policy == CachePolicy.LFU:
                self.frequency_counter[key] = entry.access_count
            
            return entry.value
    
    def put(self, 
           key: str, 
           value: Any, 
           ttl_seconds: Optional[int] = None,
           size_bytes: Optional[int] = None) -> bool:
        """
        Put value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live in seconds
            size_bytes: Size of the value in bytes
            
        Returns:
            True if successfully cached, False otherwise
        """
        with self._lock:
            # Calculate size if not provided
            if size_bytes is None:
                try:
                    size_bytes = len(pickle.dumps(value))
                except Exception:
                    size_bytes = 0  # Fallback
            
            # Check if we need to evict entries
            self._evict_if_needed(key, size_bytes)
            
            # Create cache entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=datetime.now(timezone.utc),
                last_accessed=datetime.now(timezone.utc),
                size_bytes=size_bytes,
                ttl_seconds=ttl_seconds or self.default_ttl_seconds
            )
            
            # Add to cache
            self.cache[key] = entry
            self.total_memory_usage += size_bytes
            
            # Update access order for LRU
            if self.eviction_policy == CachePolicy.LRU:
                if key in self.access_order:
                    self.access_order.remove(key)
                self.access_order.append(key)
            
            # Update frequency for LFU
            if self.eviction_policy == CachePolicy.LFU:
                self.frequency_counter[key] = 1
            
            logger.debug(f"Cached entry {key} (size: {size_bytes} bytes)")
            return True
    
    def remove(self, key: str) -> bool:
        """
        Remove entry from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if entry was removed, False if not found
        """
        with self._lock:
            return self._remove_entry(key)
    
    def _remove_entry(self, key: str) -> bool:
        """Remove entry from cache (internal method)."""
        if key not in self.cache:
            return False
        
        entry = self.cache[key]
        
        # Update memory usage
        self.total_memory_usage -= entry.size_bytes
        
        # Remove from cache
        del self.cache[key]
        
        # Remove from access order
        if key in self.access_order:
            self.access_order.remove(key)
        
        # Remove from frequency counter
        if key in self.frequency_counter:
            del self.frequency_counter[key]
        
        logger.debug(f"Removed cache entry {key}")
        return True
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self.cache.clear()
            self.access_order.clear()
            self.frequency_counter.clear()
            self.total_memory_usage = 0
            logger.info("Cache cleared")
    
    def _evict_if_needed(self, new_key: str, new_size: int) -> None:
        """Evict entries if cache is full."""
        # Check size limit
        while len(self.cache) >= self.max_size:
            if not self._evict_entry():
                break
        
        # Check memory limit
        while self.total_memory_usage + new_size > self.max_memory_bytes:
            if not self._evict_entry():
                break
    
    def _evict_entry(self) -> bool:
        """Evict an entry based on eviction policy."""
        if not self.cache:
            return False
        
        # Select entry to evict based on policy
        key_to_evict = None
        
        if self.eviction_policy == CachePolicy.LRU:
            # Evict least recently used
            if self.access_order:
                key_to_evict = self.access_order[0]
        
        elif self.eviction_policy == CachePolicy.LFU:
            # Evict least frequently used
            if self.frequency_counter:
                key_to_evict = min(self.frequency_counter.keys(), 
                                 key=lambda k: self.frequency_counter[k])
        
        elif self.eviction_policy == CachePolicy.TTL:
            # Evict oldest entry
            oldest_key = None
            oldest_time = None
            for key, entry in self.cache.items():
                if oldest_time is None or entry.created_at < oldest_time:
                    oldest_time = entry.created_at
                    oldest_key = key
            key_to_evict = oldest_key
        
        elif self.eviction_policy == CachePolicy.SIZE_BASED:
            # Evict largest entry
            largest_key = None
            largest_size = 0
            for key, entry in self.cache.items():
                if entry.size_bytes > largest_size:
                    largest_size = entry.size_bytes
                    largest_key = key
            key_to_evict = largest_key
        
        # Evict the selected entry
        if key_to_evict:
            self._remove_entry(key_to_evict)
            self.evictions += 1
            logger.debug(f"Evicted cache entry {key_to_evict} (policy: {self.eviction_policy.value})")
            return True
        
        return False
    
    def _cleanup_expired_entries(self) -> None:
        """Clean up expired entries."""
        with self._lock:
            expired_keys = []
            for key, entry in self.cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
            
            for key in expired_keys:
                self._remove_entry(key)
                self.evictions += 1
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired entries")
        
        # Restart cleanup task
        self._start_cleanup_task()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self.cache_hits + self.cache_misses
            hit_rate = self.cache_hits / total_requests if total_requests > 0 else 0.0
            miss_rate = self.cache_misses / total_requests if total_requests > 0 else 0.0
            
            return {
                'cache_size': len(self.cache),
                'max_size': self.max_size,
                'memory_usage_bytes': self.total_memory_usage,
                'max_memory_bytes': self.max_memory_bytes,
                'cache_hits': self.cache_hits,
                'cache_misses': self.cache_misses,
                'evictions': self.evictions,
                'hit_rate': hit_rate,
                'miss_rate': miss_rate,
                'eviction_policy': self.eviction_policy.value,
                'memory_usage_percent': (self.total_memory_usage / self.max_memory_bytes) * 100
            }
    
    def get_metrics(self) -> CacheMetrics:
        """Get cache metrics."""
        stats = self.get_stats()
        return CacheMetrics(
            timestamp=datetime.now(timezone.utc),
            cache_size=stats['cache_size'],
            cache_hits=stats['cache_hits'],
            cache_misses=stats['cache_misses'],
            evictions=stats['evictions'],
            memory_usage_bytes=stats['memory_usage_bytes'],
            hit_rate=stats['hit_rate'],
            miss_rate=stats['miss_rate']
        )
    
    def contains(self, key: str) -> bool:
        """Check if key exists in cache and is not expired."""
        with self._lock:
            if key not in self.cache:
                return False
            
            entry = self.cache[key]
            if entry.is_expired():
                self._remove_entry(key)
                return False
            
            return True
    
    def get_cache_keys(self) -> List[str]:
        """Get all cache keys (excluding expired)."""
        with self._lock:
            keys = []
            expired_keys = []
            
            for key, entry in self.cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
                else:
                    keys.append(key)
            
            # Clean up expired keys
            for key in expired_keys:
                self._remove_entry(key)
            
            return keys
    
    def get_entry_info(self, key: str) -> Optional[Dict[str, Any]]:
        """Get information about a cache entry."""
        with self._lock:
            if key not in self.cache:
                return None
            
            entry = self.cache[key]
            if entry.is_expired():
                self._remove_entry(key)
                return None
            
            return {
                'key': entry.key,
                'created_at': entry.created_at.isoformat(),
                'last_accessed': entry.last_accessed.isoformat(),
                'access_count': entry.access_count,
                'size_bytes': entry.size_bytes,
                'ttl_seconds': entry.ttl_seconds,
                'is_expired': entry.is_expired()
            }
    
    def warm_cache(self, key_value_pairs: List[Tuple[str, Any]]) -> int:
        """
        Warm cache with multiple entries.
        
        Args:
            key_value_pairs: List of (key, value) tuples
            
        Returns:
            Number of entries successfully cached
        """
        success_count = 0
        for key, value in key_value_pairs:
            if self.put(key, value):
                success_count += 1
        
        logger.info(f"Warmed cache with {success_count}/{len(key_value_pairs)} entries")
        return success_count
    
    def close(self) -> None:
        """Close the cache and cleanup resources."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        with self._lock:
            self.cache.clear()
            self.access_order.clear()
            self.frequency_counter.clear()
        
        logger.info("Cache closed")
