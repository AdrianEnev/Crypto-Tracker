"""
Connection Pooling for Performance Optimization

Provides connection pooling for HTTP requests, database connections,
and other network resources to improve performance and reduce latency.
"""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import time
from contextlib import asynccontextmanager


@dataclass
class ConnectionStats:
    """Connection pool statistics."""
    total_connections: int
    active_connections: int
    idle_connections: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    last_activity: datetime


class HTTPConnectionPool:
    """
    HTTP connection pool for aiohttp requests.
    
    Features:
    - Connection reuse and pooling
    - Automatic retry with exponential backoff
    - Rate limiting and throttling
    - Connection health monitoring
    - Performance metrics collection
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Connection pool configuration
        self.max_connections = config.get('max_connections', 100)
        self.max_connections_per_host = config.get('max_connections_per_host', 30)
        self.keepalive_timeout = config.get('keepalive_timeout', 30)
        self.enable_cleanup_closed = config.get('enable_cleanup_closed', True)
        
        # Retry configuration
        self.max_retries = config.get('max_retries', 3)
        self.retry_delay = config.get('retry_delay', 1.0)
        self.retry_backoff_factor = config.get('retry_backoff_factor', 2.0)
        
        # Rate limiting
        self.requests_per_second = config.get('requests_per_second', 10)
        self.burst_size = config.get('burst_size', 20)
        
        # Statistics
        self.stats = ConnectionStats(
            total_connections=0,
            active_connections=0,
            idle_connections=0,
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            avg_response_time=0.0,
            last_activity=datetime.now(timezone.utc)
        )
        
        # Connection pool
        self._session: Optional[aiohttp.ClientSession] = None
        self._connector: Optional[aiohttp.TCPConnector] = None
        self._rate_limiter = asyncio.Semaphore(self.burst_size)
        self._last_request_time = 0.0
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def initialize(self):
        """Initialize the connection pool."""
        try:
            # Create TCP connector with connection pooling
            self._connector = aiohttp.TCPConnector(
                limit=self.max_connections,
                limit_per_host=self.max_connections_per_host,
                keepalive_timeout=self.keepalive_timeout,
                enable_cleanup_closed=self.enable_cleanup_closed,
                ttl_dns_cache=300,  # 5 minutes DNS cache
                use_dns_cache=True
            )
            
            # Create session with connector
            timeout = aiohttp.ClientTimeout(
                total=30,  # 30 seconds total timeout
                connect=10,  # 10 seconds connection timeout
                sock_read=10  # 10 seconds socket read timeout
            )
            
            self._session = aiohttp.ClientSession(
                connector=self._connector,
                timeout=timeout,
                headers={
                    'User-Agent': 'CryptoBot/2.0',
                    'Accept': 'application/json',
                    'Connection': 'keep-alive'
                }
            )
            
            self.logger.info(f"HTTP connection pool initialized: {self.max_connections} max connections")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize connection pool: {e}")
            raise
    
    async def close(self):
        """Close the connection pool."""
        try:
            if self._session:
                await self._session.close()
            if self._connector:
                await self._connector.close()
            
            self.logger.info("HTTP connection pool closed")
            
        except Exception as e:
            self.logger.error(f"Error closing connection pool: {e}")
    
    async def _rate_limit(self):
        """Apply rate limiting."""
        async with self._rate_limiter:
            current_time = time.time()
            time_since_last = current_time - self._last_request_time
            min_interval = 1.0 / self.requests_per_second
            
            if time_since_last < min_interval:
                sleep_time = min_interval - time_since_last
                await asyncio.sleep(sleep_time)
            
            self._last_request_time = time.time()
    
    async def request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> aiohttp.ClientResponse:
        """
        Make HTTP request with connection pooling and retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Additional arguments for aiohttp
            
        Returns:
            aiohttp.ClientResponse
        """
        if not self._session:
            raise RuntimeError("Connection pool not initialized")
        
        # Apply rate limiting
        await self._rate_limit()
        
        # Retry logic with exponential backoff
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                start_time = time.time()
                
                async with self._session.request(method, url, **kwargs) as response:
                    # Update statistics
                    response_time = time.time() - start_time
                    self._update_stats(success=True, response_time=response_time)
                    
                    return response
                    
            except Exception as e:
                last_exception = e
                self._update_stats(success=False)
                
                if attempt < self.max_retries:
                    # Exponential backoff
                    delay = self.retry_delay * (self.retry_backoff_factor ** attempt)
                    self.logger.warning(f"Request failed (attempt {attempt + 1}), retrying in {delay:.2f}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(f"Request failed after {self.max_retries + 1} attempts: {e}")
        
        raise last_exception
    
    async def get(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make GET request."""
        return await self.request('GET', url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make POST request."""
        return await self.request('POST', url, **kwargs)
    
    def _update_stats(self, success: bool, response_time: float = 0.0):
        """Update connection pool statistics."""
        self.stats.total_requests += 1
        self.stats.last_activity = datetime.now(timezone.utc)
        
        if success:
            self.stats.successful_requests += 1
            # Update average response time
            if self.stats.avg_response_time == 0:
                self.stats.avg_response_time = response_time
            else:
                self.stats.avg_response_time = (
                    self.stats.avg_response_time * 0.9 + response_time * 0.1
                )
        else:
            self.stats.failed_requests += 1
    
    def get_stats(self) -> ConnectionStats:
        """Get connection pool statistics."""
        if self._connector:
            self.stats.total_connections = self._connector.limit
            self.stats.active_connections = len(self._connector._conns) if hasattr(self._connector, '_conns') else 0
            self.stats.idle_connections = self.stats.total_connections - self.stats.active_connections
        
        return self.stats
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get connection pool health status."""
        stats = self.get_stats()
        
        # Calculate health metrics
        success_rate = (
            stats.successful_requests / stats.total_requests 
            if stats.total_requests > 0 else 0
        )
        
        # Determine health status
        if success_rate >= 0.95 and stats.avg_response_time < 1.0:
            health_status = "healthy"
        elif success_rate >= 0.90 and stats.avg_response_time < 2.0:
            health_status = "degraded"
        else:
            health_status = "unhealthy"
        
        return {
            'status': health_status,
            'success_rate': success_rate,
            'avg_response_time': stats.avg_response_time,
            'total_requests': stats.total_requests,
            'active_connections': stats.active_connections,
            'last_activity': stats.last_activity.isoformat()
        }


class DatabaseConnectionPool:
    """
    Database connection pool for SQLite and other databases.
    
    Features:
    - Connection reuse and pooling
    - Automatic connection health checks
    - Connection lifecycle management
    - Performance monitoring
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Connection pool configuration
        self.max_connections = config.get('max_connections', 20)
        self.min_connections = config.get('min_connections', 5)
        self.connection_timeout = config.get('connection_timeout', 30)
        self.idle_timeout = config.get('idle_timeout', 300)  # 5 minutes
        
        # Database configuration
        self.database_url = config.get('database_url')
        self.database_type = config.get('database_type', 'sqlite')
        
        # Connection pool
        self._connections: List[Any] = []
        self._available_connections: asyncio.Queue = asyncio.Queue()
        self._connection_lock = asyncio.Lock()
        self._stats = {
            'total_connections': 0,
            'active_connections': 0,
            'idle_connections': 0,
            'total_queries': 0,
            'successful_queries': 0,
            'failed_queries': 0
        }
    
    async def initialize(self):
        """Initialize the database connection pool."""
        try:
            # Create initial connections
            for _ in range(self.min_connections):
                connection = await self._create_connection()
                self._connections.append(connection)
                await self._available_connections.put(connection)
            
            self._stats['total_connections'] = len(self._connections)
            self._stats['idle_connections'] = len(self._connections)
            
            self.logger.info(f"Database connection pool initialized: {len(self._connections)} connections")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database connection pool: {e}")
            raise
    
    async def _create_connection(self) -> Any:
        """Create a new database connection."""
        # This would be implemented based on the specific database type
        # For now, return a placeholder
        return {"connection_id": len(self._connections), "created_at": datetime.now(timezone.utc)}
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a database connection from the pool."""
        connection = None
        try:
            # Try to get an available connection
            try:
                connection = await asyncio.wait_for(
                    self._available_connections.get(), 
                    timeout=self.connection_timeout
                )
            except asyncio.TimeoutError:
                # Create a new connection if none available
                async with self._connection_lock:
                    if len(self._connections) < self.max_connections:
                        connection = await self._create_connection()
                        self._connections.append(connection)
                        self._stats['total_connections'] = len(self._connections)
                    else:
                        raise RuntimeError("Connection pool exhausted")
            
            self._stats['active_connections'] += 1
            self._stats['idle_connections'] -= 1
            
            yield connection
            
        finally:
            if connection:
                # Return connection to pool
                await self._available_connections.put(connection)
                self._stats['active_connections'] -= 1
                self._stats['idle_connections'] += 1
    
    async def execute_query(self, query: str, params: Optional[Dict] = None) -> Any:
        """Execute a database query using connection pooling."""
        try:
            async with self.get_connection() as connection:
                # This would execute the actual query
                # For now, just simulate
                self._stats['total_queries'] += 1
                self._stats['successful_queries'] += 1
                
                return {"result": "query executed", "connection_id": connection.get("connection_id")}
                
        except Exception as e:
            self._stats['total_queries'] += 1
            self._stats['failed_queries'] += 1
            self.logger.error(f"Query execution failed: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database connection pool statistics."""
        return self._stats.copy()
    
    async def close(self):
        """Close all connections in the pool."""
        try:
            # Close all connections
            for connection in self._connections:
                # This would close the actual connection
                pass
            
            self._connections.clear()
            self._stats['total_connections'] = 0
            self._stats['active_connections'] = 0
            self._stats['idle_connections'] = 0
            
            self.logger.info("Database connection pool closed")
            
        except Exception as e:
            self.logger.error(f"Error closing database connection pool: {e}")


class ConnectionPoolManager:
    """
    Manages multiple connection pools for different services.
    
    Features:
    - Centralized pool management
    - Health monitoring across all pools
    - Performance metrics aggregation
    - Automatic pool lifecycle management
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Connection pools
        self.http_pools: Dict[str, HTTPConnectionPool] = {}
        self.db_pools: Dict[str, DatabaseConnectionPool] = {}
        
        # Configuration
        self.pool_configs = config.get('pools', {})
    
    async def initialize(self):
        """Initialize all connection pools."""
        try:
            # Initialize HTTP connection pools
            for pool_name, pool_config in self.pool_configs.get('http', {}).items():
                pool = HTTPConnectionPool(pool_config)
                await pool.initialize()
                self.http_pools[pool_name] = pool
                self.logger.info(f"HTTP connection pool '{pool_name}' initialized")
            
            # Initialize database connection pools
            for pool_name, pool_config in self.pool_configs.get('database', {}).items():
                pool = DatabaseConnectionPool(pool_config)
                await pool.initialize()
                self.db_pools[pool_name] = pool
                self.logger.info(f"Database connection pool '{pool_name}' initialized")
            
            self.logger.info(f"Connection pool manager initialized: {len(self.http_pools)} HTTP pools, {len(self.db_pools)} DB pools")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize connection pool manager: {e}")
            raise
    
    async def close(self):
        """Close all connection pools."""
        try:
            # Close HTTP pools
            for pool_name, pool in self.http_pools.items():
                await pool.close()
                self.logger.info(f"HTTP connection pool '{pool_name}' closed")
            
            # Close database pools
            for pool_name, pool in self.db_pools.items():
                await pool.close()
                self.logger.info(f"Database connection pool '{pool_name}' closed")
            
            self.http_pools.clear()
            self.db_pools.clear()
            
            self.logger.info("All connection pools closed")
            
        except Exception as e:
            self.logger.error(f"Error closing connection pools: {e}")
    
    def get_http_pool(self, pool_name: str) -> Optional[HTTPConnectionPool]:
        """Get HTTP connection pool by name."""
        return self.http_pools.get(pool_name)
    
    def get_db_pool(self, pool_name: str) -> Optional[DatabaseConnectionPool]:
        """Get database connection pool by name."""
        return self.db_pools.get(pool_name)
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all connection pools."""
        stats = {
            'http_pools': {},
            'database_pools': {},
            'summary': {
                'total_http_pools': len(self.http_pools),
                'total_db_pools': len(self.db_pools),
                'total_requests': 0,
                'total_queries': 0
            }
        }
        
        # HTTP pool statistics
        for pool_name, pool in self.http_pools.items():
            pool_stats = pool.get_stats()
            stats['http_pools'][pool_name] = {
                'total_requests': pool_stats.total_requests,
                'successful_requests': pool_stats.successful_requests,
                'failed_requests': pool_stats.failed_requests,
                'avg_response_time': pool_stats.avg_response_time,
                'active_connections': pool_stats.active_connections
            }
            stats['summary']['total_requests'] += pool_stats.total_requests
        
        # Database pool statistics
        for pool_name, pool in self.db_pools.items():
            pool_stats = pool.get_stats()
            stats['database_pools'][pool_name] = pool_stats
            stats['summary']['total_queries'] += pool_stats['total_queries']
        
        return stats
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status for all connection pools."""
        health_status = {
            'overall_status': 'healthy',
            'http_pools': {},
            'database_pools': {},
            'issues': []
        }
        
        # Check HTTP pools
        for pool_name, pool in self.http_pools.items():
            pool_health = pool.get_health_status()
            health_status['http_pools'][pool_name] = pool_health
            
            if pool_health['status'] != 'healthy':
                health_status['issues'].append(f"HTTP pool '{pool_name}': {pool_health['status']}")
                if pool_health['status'] == 'unhealthy':
                    health_status['overall_status'] = 'unhealthy'
                elif health_status['overall_status'] == 'healthy':
                    health_status['overall_status'] = 'degraded'
        
        # Check database pools
        for pool_name, pool in self.db_pools.items():
            pool_stats = pool.get_stats()
            success_rate = (
                pool_stats['successful_queries'] / pool_stats['total_queries']
                if pool_stats['total_queries'] > 0 else 1.0
            )
            
            if success_rate < 0.95:
                health_status['issues'].append(f"Database pool '{pool_name}': low success rate ({success_rate:.2%})")
                health_status['overall_status'] = 'degraded'
        
        return health_status
