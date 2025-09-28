"""
Model Server for production ML model serving.
Provides high-performance inference serving with monitoring and management.
"""

import time
import asyncio
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging
import json
import uuid

logger = logging.getLogger(__name__)


@dataclass
class InferenceRequest:
    """Container for inference requests."""
    request_id: str
    model_name: str
    model_version: str
    input_data: Dict[str, Any]
    timestamp: datetime
    client_id: Optional[str] = None
    priority: int = 0  # Higher number = higher priority
    timeout_seconds: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'request_id': self.request_id,
            'model_name': self.model_name,
            'model_version': self.model_version,
            'input_data': self.input_data,
            'timestamp': self.timestamp.isoformat(),
            'client_id': self.client_id,
            'priority': self.priority,
            'timeout_seconds': self.timeout_seconds
        }


@dataclass
class InferenceResponse:
    """Container for inference responses."""
    request_id: str
    model_name: str
    model_version: str
    prediction: Any
    confidence: Optional[float] = None
    latency_ms: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'request_id': self.request_id,
            'model_name': self.model_name,
            'model_version': self.model_version,
            'prediction': self.prediction,
            'confidence': self.confidence,
            'latency_ms': self.latency_ms,
            'timestamp': self.timestamp.isoformat(),
            'error': self.error,
            'metadata': self.metadata
        }


@dataclass
class ServerConfig:
    """Configuration for model server."""
    server_name: str
    max_concurrent_requests: int = 100
    request_timeout_seconds: float = 30.0
    model_load_timeout_seconds: float = 60.0
    health_check_interval_seconds: int = 30
    metrics_collection_interval_seconds: int = 10
    enable_batching: bool = True
    batch_size: int = 32
    batch_timeout_seconds: float = 0.1
    enable_caching: bool = True
    cache_size: int = 1000
    cache_ttl_seconds: int = 3600
    enable_profiling: bool = False
    log_level: str = "INFO"
    enable_async_processing: bool = True
    
    # Performance tuning
    worker_threads: int = 4
    max_queue_size: int = 1000
    enable_request_prioritization: bool = True
    
    # Security
    enable_authentication: bool = False
    api_key: Optional[str] = None
    enable_rate_limiting: bool = True
    max_requests_per_minute: int = 1000


class BaseModel(ABC):
    """Base class for models that can be served."""
    
    def __init__(self, model_name: str, model_version: str):
        self.model_name = model_name
        self.model_version = model_version
        self.is_loaded = False
        self.load_time: Optional[datetime] = None
        self.metadata: Dict[str, Any] = {}
    
    @abstractmethod
    def load(self) -> None:
        """Load the model."""
        pass
    
    @abstractmethod
    def predict(self, input_data: Dict[str, Any]) -> Any:
        """Make prediction on input data."""
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        pass
    
    def unload(self) -> None:
        """Unload the model."""
        self.is_loaded = False
        self.load_time = None


class ModelServer:
    """
    High-performance model server for production inference.
    """
    
    def __init__(self, config: ServerConfig):
        self.config = config
        self.models: Dict[str, BaseModel] = {}
        self.request_queue = asyncio.Queue(maxsize=config.max_queue_size)
        self.response_cache: Dict[str, InferenceResponse] = {}
        self.metrics: Dict[str, Any] = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'avg_latency_ms': 0.0,
            'requests_per_second': 0.0,
            'cache_hits': 0,
            'cache_misses': 0,
            'model_loads': 0,
            'model_unloads': 0
        }
        
        # Server state
        self.is_running = False
        self.start_time: Optional[datetime] = None
        self.worker_tasks: List[asyncio.Task] = []
        self.health_check_task: Optional[asyncio.Task] = None
        self.metrics_task: Optional[asyncio.Task] = None
        
        # Threading
        self._lock = threading.Lock()
        
        logger.info(f"Initialized model server: {config.server_name}")
    
    async def start(self) -> None:
        """Start the model server."""
        if self.is_running:
            logger.warning("Server is already running")
            return
        
        logger.info(f"Starting model server: {self.config.server_name}")
        
        self.is_running = True
        self.start_time = datetime.now(timezone.utc)
        
        # Start worker tasks
        for i in range(self.config.worker_threads):
            task = asyncio.create_task(self._worker(f"worker-{i}"))
            self.worker_tasks.append(task)
        
        # Start health check task
        if self.config.health_check_interval_seconds > 0:
            self.health_check_task = asyncio.create_task(self._health_check_loop())
        
        # Start metrics collection task
        if self.config.metrics_collection_interval_seconds > 0:
            self.metrics_task = asyncio.create_task(self._metrics_collection_loop())
        
        logger.info(f"Model server started with {len(self.worker_tasks)} workers")
    
    async def stop(self) -> None:
        """Stop the model server."""
        if not self.is_running:
            return
        
        logger.info("Stopping model server...")
        
        self.is_running = False
        
        # Cancel all tasks
        for task in self.worker_tasks:
            task.cancel()
        
        if self.health_check_task:
            self.health_check_task.cancel()
        
        if self.metrics_task:
            self.metrics_task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        
        if self.health_check_task:
            await asyncio.gather(self.health_check_task, return_exceptions=True)
        
        if self.metrics_task:
            await asyncio.gather(self.metrics_task, return_exceptions=True)
        
        # Unload all models
        for model in self.models.values():
            model.unload()
        
        logger.info("Model server stopped")
    
    def register_model(self, model: BaseModel) -> None:
        """Register a model for serving."""
        model_key = f"{model.model_name}:{model.model_version}"
        
        with self._lock:
            if model_key in self.models:
                logger.warning(f"Model {model_key} already registered, replacing...")
                self.models[model_key].unload()
            
            self.models[model_key] = model
            self.metrics['model_loads'] += 1
        
        logger.info(f"Registered model: {model_key}")
    
    def unregister_model(self, model_name: str, model_version: str) -> None:
        """Unregister a model."""
        model_key = f"{model_name}:{model_version}"
        
        with self._lock:
            if model_key in self.models:
                self.models[model_key].unload()
                del self.models[model_key]
                self.metrics['model_unloads'] += 1
                logger.info(f"Unregistered model: {model_key}")
            else:
                logger.warning(f"Model {model_key} not found")
    
    async def predict(self, 
                     model_name: str, 
                     model_version: str, 
                     input_data: Dict[str, Any],
                     client_id: Optional[str] = None,
                     priority: int = 0,
                     timeout_seconds: Optional[float] = None) -> InferenceResponse:
        """
        Make a prediction request.
        
        Args:
            model_name: Name of the model
            model_version: Version of the model
            input_data: Input data for prediction
            client_id: Optional client identifier
            priority: Request priority (higher = more important)
            timeout_seconds: Request timeout
            
        Returns:
            InferenceResponse with prediction results
        """
        request_id = str(uuid.uuid4())
        timeout = timeout_seconds or self.config.request_timeout_seconds
        
        # Create request
        request = InferenceRequest(
            request_id=request_id,
            model_name=model_name,
            model_version=model_version,
            input_data=input_data,
            timestamp=datetime.now(timezone.utc),
            client_id=client_id,
            priority=priority,
            timeout_seconds=timeout
        )
        
        # Check cache if enabled
        if self.config.enable_caching:
            cache_key = self._generate_cache_key(request)
            if cache_key in self.response_cache:
                cached_response = self.response_cache[cache_key]
                self.metrics['cache_hits'] += 1
                logger.debug(f"Cache hit for request {request_id}")
                return cached_response
            else:
                self.metrics['cache_misses'] += 1
        
        # Submit request to queue
        try:
            await asyncio.wait_for(
                self.request_queue.put(request), 
                timeout=timeout
            )
        except asyncio.TimeoutError:
            return InferenceResponse(
                request_id=request_id,
                model_name=model_name,
                model_version=model_version,
                prediction=None,
                error=f"Request queue timeout after {timeout} seconds",
                timestamp=datetime.now(timezone.utc)
            )
        
        # Wait for response (in a real implementation, this would use a response queue)
        # For now, we'll process synchronously
        return await self._process_request(request)
    
    async def _process_request(self, request: InferenceRequest) -> InferenceResponse:
        """Process a single inference request."""
        start_time = time.time()
        
        try:
            # Get model
            model_key = f"{request.model_name}:{request.model_version}"
            model = self.models.get(model_key)
            
            if not model:
                return InferenceResponse(
                    request_id=request.request_id,
                    model_name=request.model_name,
                    model_version=request.model_version,
                    prediction=None,
                    error=f"Model {model_key} not found",
                    timestamp=datetime.now(timezone.utc)
                )
            
            # Load model if not loaded
            if not model.is_loaded:
                try:
                    model.load()
                except Exception as e:
                    return InferenceResponse(
                        request_id=request.request_id,
                        model_name=request.model_name,
                        model_version=request.model_version,
                        prediction=None,
                        error=f"Failed to load model: {str(e)}",
                        timestamp=datetime.now(timezone.utc)
                    )
            
            # Make prediction
            prediction = model.predict(request.input_data)
            
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            
            # Create response
            response = InferenceResponse(
                request_id=request.request_id,
                model_name=request.model_name,
                model_version=request.model_version,
                prediction=prediction,
                latency_ms=latency_ms,
                timestamp=datetime.now(timezone.utc),
                metadata=model.get_model_info()
            )
            
            # Update metrics
            with self._lock:
                self.metrics['total_requests'] += 1
                self.metrics['successful_requests'] += 1
                
                # Update average latency
                total_requests = self.metrics['total_requests']
                current_avg = self.metrics['avg_latency_ms']
                self.metrics['avg_latency_ms'] = (current_avg * (total_requests - 1) + latency_ms) / total_requests
            
            # Cache response if enabled
            if self.config.enable_caching:
                cache_key = self._generate_cache_key(request)
                self.response_cache[cache_key] = response
                
                # Clean cache if it's too large
                if len(self.response_cache) > self.config.cache_size:
                    self._clean_cache()
            
            return response
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            
            with self._lock:
                self.metrics['total_requests'] += 1
                self.metrics['failed_requests'] += 1
            
            return InferenceResponse(
                request_id=request.request_id,
                model_name=request.model_name,
                model_version=request.model_version,
                prediction=None,
                error=str(e),
                latency_ms=latency_ms,
                timestamp=datetime.now(timezone.utc)
            )
    
    async def _worker(self, worker_name: str) -> None:
        """Worker task for processing requests."""
        logger.info(f"Worker {worker_name} started")
        
        while self.is_running:
            try:
                # Get request from queue
                request = await asyncio.wait_for(
                    self.request_queue.get(), 
                    timeout=1.0
                )
                
                # Process request
                await self._process_request(request)
                
                # Mark task as done
                self.request_queue.task_done()
                
            except asyncio.TimeoutError:
                # No requests in queue, continue
                continue
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {e}")
        
        logger.info(f"Worker {worker_name} stopped")
    
    async def _health_check_loop(self) -> None:
        """Health check loop."""
        while self.is_running:
            try:
                # Check server health
                health_status = self.get_health_status()
                
                if not health_status['healthy']:
                    logger.warning(f"Health check failed: {health_status['issues']}")
                
                await asyncio.sleep(self.config.health_check_interval_seconds)
                
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(self.config.health_check_interval_seconds)
    
    async def _metrics_collection_loop(self) -> None:
        """Metrics collection loop."""
        while self.is_running:
            try:
                # Calculate requests per second
                if self.start_time:
                    uptime_seconds = (datetime.now(timezone.utc) - self.start_time).total_seconds()
                    if uptime_seconds > 0:
                        self.metrics['requests_per_second'] = self.metrics['total_requests'] / uptime_seconds
                
                await asyncio.sleep(self.config.metrics_collection_interval_seconds)
                
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                await asyncio.sleep(self.config.metrics_collection_interval_seconds)
    
    def _generate_cache_key(self, request: InferenceRequest) -> str:
        """Generate cache key for request."""
        # Simple hash-based cache key
        import hashlib
        content = f"{request.model_name}:{request.model_version}:{json.dumps(request.input_data, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _clean_cache(self) -> None:
        """Clean old entries from cache."""
        if not self.response_cache:
            return
        
        # Simple LRU-style cleanup (remove oldest entries)
        sorted_items = sorted(
            self.response_cache.items(),
            key=lambda x: x[1].timestamp
        )
        
        # Remove oldest 25% of entries
        remove_count = len(sorted_items) // 4
        for i in range(remove_count):
            key, _ = sorted_items[i]
            del self.response_cache[key]
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get server health status."""
        issues = []
        
        # Check if server is running
        if not self.is_running:
            issues.append("Server not running")
        
        # Check queue size
        if self.request_queue.qsize() > self.config.max_queue_size * 0.9:
            issues.append("Request queue nearly full")
        
        # Check model availability
        loaded_models = sum(1 for model in self.models.values() if model.is_loaded)
        if loaded_models == 0:
            issues.append("No models loaded")
        
        # Check error rate
        total_requests = self.metrics['total_requests']
        if total_requests > 100:  # Only check if we have enough requests
            error_rate = self.metrics['failed_requests'] / total_requests
            if error_rate > 0.1:  # 10% error rate threshold
                issues.append(f"High error rate: {error_rate:.2%}")
        
        return {
            'healthy': len(issues) == 0,
            'issues': issues,
            'uptime_seconds': (datetime.now(timezone.utc) - self.start_time).total_seconds() if self.start_time else 0,
            'loaded_models': loaded_models,
            'total_models': len(self.models),
            'queue_size': self.request_queue.qsize(),
            'cache_size': len(self.response_cache)
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get server metrics."""
        metrics = self.metrics.copy()
        
        # Add additional metrics
        metrics.update({
            'uptime_seconds': (datetime.now(timezone.utc) - self.start_time).total_seconds() if self.start_time else 0,
            'queue_size': self.request_queue.qsize(),
            'cache_size': len(self.response_cache),
            'loaded_models': sum(1 for model in self.models.values() if model.is_loaded),
            'total_models': len(self.models)
        })
        
        # Calculate derived metrics
        if metrics['total_requests'] > 0:
            metrics['success_rate'] = metrics['successful_requests'] / metrics['total_requests']
            metrics['error_rate'] = metrics['failed_requests'] / metrics['total_requests']
        else:
            metrics['success_rate'] = 0.0
            metrics['error_rate'] = 0.0
        
        if metrics['cache_hits'] + metrics['cache_misses'] > 0:
            metrics['cache_hit_rate'] = metrics['cache_hits'] / (metrics['cache_hits'] + metrics['cache_misses'])
        else:
            metrics['cache_hit_rate'] = 0.0
        
        return metrics
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about registered models."""
        model_info = {}
        
        for model_key, model in self.models.items():
            model_info[model_key] = {
                'name': model.model_name,
                'version': model.model_version,
                'is_loaded': model.is_loaded,
                'load_time': model.load_time.isoformat() if model.load_time else None,
                'metadata': model.metadata
            }
        
        return model_info
