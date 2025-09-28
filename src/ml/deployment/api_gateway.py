"""
API Gateway for ML model serving with authentication, rate limiting, and routing.
Provides unified interface for model inference requests.
"""

import time
import asyncio
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import json
import uuid

logger = logging.getLogger(__name__)


class RateLimit:
    """Rate limiting configuration."""
    
    def __init__(self, 
                 requests_per_minute: int = 100,
                 burst_limit: int = 10,
                 window_size_seconds: int = 60):
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.window_size_seconds = window_size_seconds


class Authentication:
    """Authentication configuration."""
    
    def __init__(self, 
                 enabled: bool = False,
                 api_key_header: str = "X-API-Key",
                 api_keys: Optional[List[str]] = None,
                 require_authentication: bool = True):
        self.enabled = enabled
        self.api_key_header = api_key_header
        self.api_keys = api_keys or []
        self.require_authentication = require_authentication


@dataclass
class GatewayConfig:
    """Configuration for API Gateway."""
    gateway_name: str
    listen_host: str = "0.0.0.0"
    listen_port: int = 8080
    enable_authentication: bool = False
    enable_rate_limiting: bool = True
    enable_logging: bool = True
    enable_metrics: bool = True
    request_timeout_seconds: float = 30.0
    max_request_size_bytes: int = 10 * 1024 * 1024  # 10MB
    rate_limit: RateLimit = field(default_factory=RateLimit)
    authentication: Authentication = field(default_factory=Authentication)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'gateway_name': self.gateway_name,
            'listen_host': self.listen_host,
            'listen_port': self.listen_port,
            'enable_authentication': self.enable_authentication,
            'enable_rate_limiting': self.enable_rate_limiting,
            'enable_logging': self.enable_logging,
            'enable_metrics': self.enable_metrics,
            'request_timeout_seconds': self.request_timeout_seconds,
            'max_request_size_bytes': self.max_request_size_bytes,
            'rate_limit': {
                'requests_per_minute': self.rate_limit.requests_per_minute,
                'burst_limit': self.rate_limit.burst_limit,
                'window_size_seconds': self.rate_limit.window_size_seconds
            },
            'authentication': {
                'enabled': self.authentication.enabled,
                'api_key_header': self.authentication.api_key_header,
                'api_keys': self.authentication.api_keys,
                'require_authentication': self.authentication.require_authentication
            }
        }


@dataclass
class GatewayRequest:
    """Container for gateway request."""
    request_id: str
    client_ip: str
    user_agent: str
    endpoint: str
    method: str
    headers: Dict[str, str]
    body: Dict[str, Any]
    timestamp: datetime
    api_key: Optional[str] = None
    client_id: Optional[str] = None


@dataclass
class GatewayResponse:
    """Container for gateway response."""
    request_id: str
    status_code: int
    response_data: Any
    headers: Dict[str, str] = field(default_factory=dict)
    latency_ms: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'request_id': self.request_id,
            'status_code': self.status_code,
            'response_data': self.response_data,
            'headers': self.headers,
            'latency_ms': self.latency_ms,
            'timestamp': self.timestamp.isoformat(),
            'error': self.error
        }


class APIGateway:
    """
    API Gateway for ML model serving with authentication and rate limiting.
    """
    
    def __init__(self, config: GatewayConfig):
        self.config = config
        
        # Request tracking
        self.client_requests: Dict[str, List[datetime]] = {}
        self.client_burst_counts: Dict[str, int] = {}
        
        # Metrics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.rate_limited_requests = 0
        self.authentication_failures = 0
        self.request_times: List[float] = []
        
        # Routing
        self.routes: Dict[str, Callable] = {}
        self.default_route: Optional[Callable] = None
        
        # Middleware
        self.preprocessors: List[Callable] = []
        self.postprocessors: List[Callable] = []
        
        # Server state
        self.is_running = False
        self.start_time: Optional[datetime] = None
        
        logger.info(f"Initialized API Gateway: {config.gateway_name}")
    
    async def start(self) -> None:
        """Start the API Gateway."""
        if self.is_running:
            logger.warning("API Gateway is already running")
            return
        
        logger.info(f"Starting API Gateway on {self.config.listen_host}:{self.config.listen_port}")
        
        self.is_running = True
        self.start_time = datetime.now(timezone.utc)
        
        # In a real implementation, this would start an HTTP server
        # For demo purposes, we'll just mark it as running
        logger.info("API Gateway started")
    
    async def stop(self) -> None:
        """Stop the API Gateway."""
        if not self.is_running:
            return
        
        logger.info("Stopping API Gateway...")
        self.is_running = False
        logger.info("API Gateway stopped")
    
    def add_route(self, endpoint: str, handler: Callable) -> None:
        """Add a route handler."""
        self.routes[endpoint] = handler
        logger.info(f"Added route: {endpoint}")
    
    def set_default_route(self, handler: Callable) -> None:
        """Set default route handler."""
        self.default_route = handler
        logger.info("Set default route handler")
    
    def add_preprocessor(self, preprocessor: Callable) -> None:
        """Add request preprocessor."""
        self.preprocessors.append(preprocessor)
        logger.info("Added request preprocessor")
    
    def add_postprocessor(self, postprocessor: Callable) -> None:
        """Add response postprocessor."""
        self.postprocessors.append(postprocessor)
        logger.info("Added response postprocessor")
    
    async def handle_request(self, 
                           endpoint: str,
                           method: str,
                           headers: Dict[str, str],
                           body: Dict[str, Any],
                           client_ip: str = "127.0.0.1",
                           user_agent: str = "API-Client") -> GatewayResponse:
        """
        Handle an incoming request.
        
        Args:
            endpoint: Request endpoint
            method: HTTP method
            headers: Request headers
            body: Request body
            client_ip: Client IP address
            user_agent: User agent string
            
        Returns:
            Gateway response
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Create request object
        request = GatewayRequest(
            request_id=request_id,
            client_ip=client_ip,
            user_agent=user_agent,
            endpoint=endpoint,
            method=method,
            headers=headers,
            body=body,
            timestamp=datetime.now(timezone.utc)
        )
        
        try:
            # Run preprocessors
            for preprocessor in self.preprocessors:
                request = await preprocessor(request)
                if request is None:
                    return self._create_error_response(
                        request_id, 400, "Request rejected by preprocessor"
                    )
            
            # Authentication
            if self.config.enable_authentication:
                if not await self._authenticate_request(request):
                    self.authentication_failures += 1
                    return self._create_error_response(
                        request_id, 401, "Authentication failed"
                    )
            
            # Rate limiting
            if self.config.enable_rate_limiting:
                if not await self._check_rate_limit(request):
                    self.rate_limited_requests += 1
                    return self._create_error_response(
                        request_id, 429, "Rate limit exceeded"
                    )
            
            # Route to handler
            response_data = await self._route_request(request)
            
            # Create response
            response = GatewayResponse(
                request_id=request_id,
                status_code=200,
                response_data=response_data
            )
            
            # Run postprocessors
            for postprocessor in self.postprocessors:
                response = await postprocessor(response)
                if response is None:
                    return self._create_error_response(
                        request_id, 500, "Response processing failed"
                    )
            
            # Update metrics
            self._update_metrics(start_time, True)
            
            return response
            
        except Exception as e:
            logger.error(f"Error handling request {request_id}: {e}")
            self._update_metrics(start_time, False)
            return self._create_error_response(
                request_id, 500, f"Internal server error: {str(e)}"
            )
    
    async def _authenticate_request(self, request: GatewayRequest) -> bool:
        """Authenticate the request."""
        if not self.config.authentication.enabled:
            return True
        
        # Extract API key from headers
        api_key = request.headers.get(self.config.authentication.api_key_header)
        if not api_key:
            if self.config.authentication.require_authentication:
                return False
            return True
        
        # Validate API key
        if api_key in self.config.authentication.api_keys:
            request.api_key = api_key
            return True
        
        return False
    
    async def _check_rate_limit(self, request: GatewayRequest) -> bool:
        """Check rate limit for the request."""
        client_id = request.client_ip
        if request.api_key:
            client_id = request.api_key
        
        request.client_id = client_id
        
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=self.config.rate_limit.window_size_seconds)
        
        # Get client request history
        if client_id not in self.client_requests:
            self.client_requests[client_id] = []
            self.client_burst_counts[client_id] = 0
        
        client_requests = self.client_requests[client_id]
        burst_count = self.client_burst_counts[client_id]
        
        # Remove old requests outside the window
        client_requests[:] = [req_time for req_time in client_requests if req_time > window_start]
        
        # Check rate limit
        if len(client_requests) >= self.config.rate_limit.requests_per_minute:
            return False
        
        # Check burst limit
        recent_requests = [req_time for req_time in client_requests 
                          if (now - req_time).total_seconds() < 1.0]  # Last 1 second
        if len(recent_requests) >= self.config.rate_limit.burst_limit:
            return False
        
        # Add current request
        client_requests.append(now)
        
        return True
    
    async def _route_request(self, request: GatewayRequest) -> Any:
        """Route request to appropriate handler."""
        # Find route handler
        handler = self.routes.get(request.endpoint)
        if not handler and self.default_route:
            handler = self.default_route
        
        if not handler:
            raise ValueError(f"No handler found for endpoint: {request.endpoint}")
        
        # Call handler
        if asyncio.iscoroutinefunction(handler):
            return await handler(request)
        else:
            return handler(request)
    
    def _create_error_response(self, request_id: str, status_code: int, error_message: str) -> GatewayResponse:
        """Create error response."""
        return GatewayResponse(
            request_id=request_id,
            status_code=status_code,
            response_data={"error": error_message},
            error=error_message
        )
    
    def _update_metrics(self, start_time: float, success: bool) -> None:
        """Update gateway metrics."""
        latency_ms = (time.time() - start_time) * 1000
        
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        # Track request times
        self.request_times.append(latency_ms)
        if len(self.request_times) > 1000:  # Keep last 1000 requests
            self.request_times = self.request_times[-1000:]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get gateway metrics."""
        total_requests = self.total_requests
        
        metrics = {
            'total_requests': total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'rate_limited_requests': self.rate_limited_requests,
            'authentication_failures': self.authentication_failures,
            'active_clients': len(self.client_requests),
            'routes_registered': len(self.routes)
        }
        
        if total_requests > 0:
            metrics.update({
                'success_rate': self.successful_requests / total_requests,
                'failure_rate': self.failed_requests / total_requests,
                'rate_limit_rate': self.rate_limited_requests / total_requests,
                'auth_failure_rate': self.authentication_failures / total_requests
            })
        else:
            metrics.update({
                'success_rate': 0.0,
                'failure_rate': 0.0,
                'rate_limit_rate': 0.0,
                'auth_failure_rate': 0.0
            })
        
        if self.request_times:
            metrics.update({
                'avg_response_time_ms': sum(self.request_times) / len(self.request_times),
                'min_response_time_ms': min(self.request_times),
                'max_response_time_ms': max(self.request_times)
            })
        else:
            metrics.update({
                'avg_response_time_ms': 0.0,
                'min_response_time_ms': 0.0,
                'max_response_time_ms': 0.0
            })
        
        # Add uptime
        if self.start_time:
            uptime_seconds = (datetime.now(timezone.utc) - self.start_time).total_seconds()
            metrics['uptime_seconds'] = uptime_seconds
            metrics['requests_per_second'] = total_requests / uptime_seconds if uptime_seconds > 0 else 0.0
        else:
            metrics['uptime_seconds'] = 0.0
            metrics['requests_per_second'] = 0.0
        
        return metrics
    
    def get_client_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get client statistics."""
        client_stats = {}
        now = datetime.now(timezone.utc)
        
        for client_id, requests in self.client_requests.items():
            window_start = now - timedelta(seconds=self.config.rate_limit.window_size_seconds)
            recent_requests = [req_time for req_time in requests if req_time > window_start]
            
            client_stats[client_id] = {
                'total_requests': len(requests),
                'recent_requests': len(recent_requests),
                'requests_per_minute': len(recent_requests),
                'burst_count': self.client_burst_counts.get(client_id, 0),
                'last_request': requests[-1].isoformat() if requests else None
            }
        
        return client_stats
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get gateway health status."""
        return {
            'healthy': self.is_running,
            'uptime_seconds': (datetime.now(timezone.utc) - self.start_time).total_seconds() if self.start_time else 0,
            'total_requests': self.total_requests,
            'active_clients': len(self.client_requests),
            'routes_registered': len(self.routes),
            'config': self.config.to_dict()
        }
    
    def reset_metrics(self) -> None:
        """Reset all metrics."""
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.rate_limited_requests = 0
        self.authentication_failures = 0
        self.request_times.clear()
        self.client_requests.clear()
        self.client_burst_counts.clear()
        
        logger.info("Gateway metrics reset")
    
    def add_api_key(self, api_key: str) -> None:
        """Add an API key for authentication."""
        if api_key not in self.config.authentication.api_keys:
            self.config.authentication.api_keys.append(api_key)
            logger.info("Added API key for authentication")
    
    def remove_api_key(self, api_key: str) -> bool:
        """Remove an API key."""
        if api_key in self.config.authentication.api_keys:
            self.config.authentication.api_keys.remove(api_key)
            logger.info("Removed API key")
            return True
        return False
    
    def update_rate_limit(self, 
                         requests_per_minute: int,
                         burst_limit: int,
                         window_size_seconds: int = 60) -> None:
        """Update rate limiting configuration."""
        self.config.rate_limit.requests_per_minute = requests_per_minute
        self.config.rate_limit.burst_limit = burst_limit
        self.config.rate_limit.window_size_seconds = window_size_seconds
        
        logger.info(f"Updated rate limit: {requests_per_minute} req/min, burst: {burst_limit}")
