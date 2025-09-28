"""
Load Balancer for distributing requests across multiple model servers.
Provides intelligent routing, health checking, and failover capabilities.
"""

import time
import asyncio
import statistics
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
import random

logger = logging.getLogger(__name__)


class LoadBalancingStrategy(Enum):
    """Load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    LEAST_RESPONSE_TIME = "least_response_time"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    RANDOM = "random"
    CONSISTENT_HASH = "consistent_hash"


@dataclass
class ServerNode:
    """Container for server node information."""
    server_id: str
    endpoint: str
    weight: int = 1
    is_healthy: bool = True
    last_health_check: Optional[datetime] = None
    response_time_ms: float = 0.0
    active_connections: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    last_request_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'server_id': self.server_id,
            'endpoint': self.endpoint,
            'weight': self.weight,
            'is_healthy': self.is_healthy,
            'last_health_check': self.last_health_check.isoformat() if self.last_health_check else None,
            'response_time_ms': self.response_time_ms,
            'active_connections': self.active_connections,
            'total_requests': self.total_requests,
            'failed_requests': self.failed_requests,
            'last_request_time': self.last_request_time.isoformat() if self.last_request_time else None,
            'metadata': self.metadata
        }


@dataclass
class HealthCheck:
    """Health check configuration."""
    endpoint: str = "/health"
    interval_seconds: int = 30
    timeout_seconds: float = 5.0
    failure_threshold: int = 3
    success_threshold: int = 2
    expected_status_codes: List[int] = field(default_factory=lambda: [200])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'endpoint': self.endpoint,
            'interval_seconds': self.interval_seconds,
            'timeout_seconds': self.timeout_seconds,
            'failure_threshold': self.failure_threshold,
            'success_threshold': self.success_threshold,
            'expected_status_codes': self.expected_status_codes
        }


class LoadBalancer:
    """
    Load balancer for distributing requests across model servers.
    """
    
    def __init__(self, 
                 strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN,
                 health_check: Optional[HealthCheck] = None,
                 enable_sticky_sessions: bool = False):
        self.strategy = strategy
        self.health_check = health_check or HealthCheck()
        self.enable_sticky_sessions = enable_sticky_sessions
        
        # Server management
        self.servers: Dict[str, ServerNode] = {}
        self.round_robin_index = 0
        self.consistent_hash_ring: Dict[int, str] = {}
        
        # Health check state
        self.health_check_task: Optional[asyncio.Task] = None
        self.server_failure_counts: Dict[str, int] = {}
        self.server_success_counts: Dict[str, int] = {}
        
        # Metrics
        self.total_requests = 0
        self.total_failures = 0
        self.request_times: List[float] = []
        
        # Sticky sessions
        self.client_server_mapping: Dict[str, str] = {}
        
        logger.info(f"Initialized load balancer with strategy: {strategy.value}")
    
    async def start(self) -> None:
        """Start the load balancer."""
        if self.health_check_task is None:
            self.health_check_task = asyncio.create_task(self._health_check_loop())
            logger.info("Load balancer started")
    
    async def stop(self) -> None:
        """Stop the load balancer."""
        if self.health_check_task:
            self.health_check_task.cancel()
            await asyncio.gather(self.health_check_task, return_exceptions=True)
            self.health_check_task = None
            logger.info("Load balancer stopped")
    
    def add_server(self, 
                   server_id: str, 
                   endpoint: str, 
                   weight: int = 1,
                   metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a server to the load balancer."""
        server = ServerNode(
            server_id=server_id,
            endpoint=endpoint,
            weight=weight,
            metadata=metadata or {}
        )
        
        self.servers[server_id] = server
        self.server_failure_counts[server_id] = 0
        self.server_success_counts[server_id] = 0
        
        # Update consistent hash ring if using that strategy
        if self.strategy == LoadBalancingStrategy.CONSISTENT_HASH:
            self._update_hash_ring()
        
        logger.info(f"Added server {server_id} at {endpoint}")
    
    def remove_server(self, server_id: str) -> bool:
        """Remove a server from the load balancer."""
        if server_id not in self.servers:
            return False
        
        del self.servers[server_id]
        del self.server_failure_counts[server_id]
        del self.server_success_counts[server_id]
        
        # Update consistent hash ring if using that strategy
        if self.strategy == LoadBalancingStrategy.CONSISTENT_HASH:
            self._update_hash_ring()
        
        # Remove from sticky sessions
        if self.enable_sticky_sessions:
            self.client_server_mapping = {
                k: v for k, v in self.client_server_mapping.items() if v != server_id
            }
        
        logger.info(f"Removed server {server_id}")
        return True
    
    def update_server_weight(self, server_id: str, weight: int) -> bool:
        """Update server weight."""
        if server_id not in self.servers:
            return False
        
        self.servers[server_id].weight = weight
        logger.info(f"Updated server {server_id} weight to {weight}")
        return True
    
    def select_server(self, client_id: Optional[str] = None) -> Optional[ServerNode]:
        """
        Select a server based on the load balancing strategy.
        
        Args:
            client_id: Client identifier for sticky sessions
            
        Returns:
            Selected server node or None if no healthy servers
        """
        healthy_servers = [server for server in self.servers.values() if server.is_healthy]
        
        if not healthy_servers:
            logger.warning("No healthy servers available")
            return None
        
        # Check sticky sessions first
        if self.enable_sticky_sessions and client_id:
            if client_id in self.client_server_mapping:
                server_id = self.client_server_mapping[client_id]
                if server_id in self.servers and self.servers[server_id].is_healthy:
                    return self.servers[server_id]
        
        # Select server based on strategy
        selected_server = None
        
        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            selected_server = self._round_robin_selection(healthy_servers)
        
        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            selected_server = min(healthy_servers, key=lambda s: s.active_connections)
        
        elif self.strategy == LoadBalancingStrategy.LEAST_RESPONSE_TIME:
            selected_server = min(healthy_servers, key=lambda s: s.response_time_ms)
        
        elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            selected_server = self._weighted_round_robin_selection(healthy_servers)
        
        elif self.strategy == LoadBalancingStrategy.RANDOM:
            selected_server = random.choice(healthy_servers)
        
        elif self.strategy == LoadBalancingStrategy.CONSISTENT_HASH:
            selected_server = self._consistent_hash_selection(client_id or "default")
        
        # Update sticky session mapping
        if self.enable_sticky_sessions and client_id and selected_server:
            self.client_server_mapping[client_id] = selected_server.server_id
        
        return selected_server
    
    def _round_robin_selection(self, servers: List[ServerNode]) -> ServerNode:
        """Round robin server selection."""
        if not servers:
            return None
        
        server = servers[self.round_robin_index % len(servers)]
        self.round_robin_index += 1
        return server
    
    def _weighted_round_robin_selection(self, servers: List[ServerNode]) -> ServerNode:
        """Weighted round robin server selection."""
        if not servers:
            return None
        
        # Calculate total weight
        total_weight = sum(server.weight for server in servers)
        
        # Select based on weight
        target = self.round_robin_index % total_weight
        current_weight = 0
        
        for server in servers:
            current_weight += server.weight
            if target < current_weight:
                self.round_robin_index += 1
                return server
        
        # Fallback to first server
        return servers[0]
    
    def _consistent_hash_selection(self, key: str) -> Optional[ServerNode]:
        """Consistent hash server selection."""
        if not self.consistent_hash_ring:
            return None
        
        # Hash the key
        key_hash = hash(key) % (2**32)
        
        # Find the first server with hash >= key_hash
        for hash_value in sorted(self.consistent_hash_ring.keys()):
            if hash_value >= key_hash:
                server_id = self.consistent_hash_ring[hash_value]
                return self.servers.get(server_id)
        
        # Wrap around to first server
        first_hash = min(self.consistent_hash_ring.keys())
        server_id = self.consistent_hash_ring[first_hash]
        return self.servers.get(server_id)
    
    def _update_hash_ring(self) -> None:
        """Update the consistent hash ring."""
        self.consistent_hash_ring.clear()
        
        for server_id, server in self.servers.items():
            if server.is_healthy:
                # Create multiple virtual nodes for better distribution
                for i in range(server.weight * 100):
                    virtual_key = f"{server_id}:{i}"
                    hash_value = hash(virtual_key) % (2**32)
                    self.consistent_hash_ring[hash_value] = server_id
    
    async def _health_check_loop(self) -> None:
        """Health check loop for all servers."""
        while True:
            try:
                await asyncio.gather(*[
                    self._check_server_health(server_id) 
                    for server_id in self.servers.keys()
                ], return_exceptions=True)
                
                await asyncio.sleep(self.health_check.interval_seconds)
                
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(self.health_check.interval_seconds)
    
    async def _check_server_health(self, server_id: str) -> None:
        """Check health of a specific server."""
        if server_id not in self.servers:
            return
        
        server = self.servers[server_id]
        health_url = f"{server.endpoint.rstrip('/')}{self.health_check.endpoint}"
        
        try:
            # Simple health check (in a real implementation, use HTTP client)
            start_time = time.time()
            
            # Mock health check - in reality, this would make an HTTP request
            await asyncio.sleep(0.01)  # Simulate network delay
            
            response_time = (time.time() - start_time) * 1000
            is_healthy = True  # Mock: assume healthy if no exception
            
            # Update server state
            server.is_healthy = is_healthy
            server.last_health_check = datetime.now(timezone.utc)
            server.response_time_ms = response_time
            
            # Update failure/success counts
            if is_healthy:
                self.server_success_counts[server_id] += 1
                self.server_failure_counts[server_id] = 0
                
                # Mark as healthy if we have enough successes
                if self.server_success_counts[server_id] >= self.health_check.success_threshold:
                    if not server.is_healthy:
                        logger.info(f"Server {server_id} is now healthy")
                    server.is_healthy = True
            else:
                self.server_failure_counts[server_id] += 1
                self.server_success_counts[server_id] = 0
                
                # Mark as unhealthy if we have too many failures
                if self.server_failure_counts[server_id] >= self.health_check.failure_threshold:
                    if server.is_healthy:
                        logger.warning(f"Server {server_id} is now unhealthy")
                    server.is_healthy = False
            
        except Exception as e:
            logger.error(f"Health check failed for server {server_id}: {e}")
            
            self.server_failure_counts[server_id] += 1
            self.server_success_counts[server_id] = 0
            
            if self.server_failure_counts[server_id] >= self.health_check.failure_threshold:
                if server.is_healthy:
                    logger.warning(f"Server {server_id} marked as unhealthy due to health check failures")
                server.is_healthy = False
    
    def record_request(self, server_id: str, success: bool, response_time_ms: float) -> None:
        """Record a request result for metrics."""
        if server_id not in self.servers:
            return
        
        server = self.servers[server_id]
        server.total_requests += 1
        server.last_request_time = datetime.now(timezone.utc)
        
        if success:
            server.active_connections = max(0, server.active_connections - 1)
        else:
            server.failed_requests += 1
            server.active_connections = max(0, server.active_connections - 1)
        
        # Update global metrics
        self.total_requests += 1
        if not success:
            self.total_failures += 1
        
        # Update response time (exponential moving average)
        alpha = 0.1  # Smoothing factor
        if server.response_time_ms == 0:
            server.response_time_ms = response_time_ms
        else:
            server.response_time_ms = alpha * response_time_ms + (1 - alpha) * server.response_time_ms
        
        # Keep recent request times for statistics
        self.request_times.append(response_time_ms)
        if len(self.request_times) > 1000:  # Keep last 1000 requests
            self.request_times = self.request_times[-1000:]
    
    def get_server_stats(self) -> Dict[str, Any]:
        """Get server statistics."""
        healthy_servers = sum(1 for s in self.servers.values() if s.is_healthy)
        total_servers = len(self.servers)
        
        server_stats = {}
        for server_id, server in self.servers.items():
            server_stats[server_id] = {
                'endpoint': server.endpoint,
                'is_healthy': server.is_healthy,
                'weight': server.weight,
                'active_connections': server.active_connections,
                'total_requests': server.total_requests,
                'failed_requests': server.failed_requests,
                'response_time_ms': server.response_time_ms,
                'failure_rate': server.failed_requests / max(server.total_requests, 1)
            }
        
        return {
            'total_servers': total_servers,
            'healthy_servers': healthy_servers,
            'unhealthy_servers': total_servers - healthy_servers,
            'total_requests': self.total_requests,
            'total_failures': self.total_failures,
            'failure_rate': self.total_failures / max(self.total_requests, 1),
            'avg_response_time_ms': statistics.mean(self.request_times) if self.request_times else 0,
            'servers': server_stats
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get load balancer health status."""
        healthy_servers = sum(1 for s in self.servers.values() if s.is_healthy)
        
        return {
            'healthy': healthy_servers > 0,
            'total_servers': len(self.servers),
            'healthy_servers': healthy_servers,
            'strategy': self.strategy.value,
            'sticky_sessions_enabled': self.enable_sticky_sessions,
            'health_check_config': self.health_check.to_dict()
        }
