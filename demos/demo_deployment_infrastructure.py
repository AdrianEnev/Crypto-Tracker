#!/usr/bin/env python3
"""
Demo script for Production Deployment Infrastructure (Phase 5D.3).
Demonstrates model serving, load balancing, auto-scaling, and deployment management.
"""

import sys
import os
import time
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Callable

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, str(project_root))

from src.ml.deployment import (
    ModelServer, ServerConfig, InferenceRequest, InferenceResponse,
    ModelRegistry, ModelVersion, DeploymentStatus,
    LoadBalancer, LoadBalancingStrategy, HealthCheck,
    AutoScaler, ScalingPolicy, ScalingRule, ScalingAction,
    DeploymentManager, DeploymentConfig, DeploymentStrategy,
    ModelCache, CachePolicy,
    APIGateway, GatewayConfig, RateLimit, Authentication
)


class MockMLModel:
    """Mock ML model for demonstration."""
    
    def __init__(self, model_name: str, model_version: str):
        self.model_name = model_name
        self.model_version = model_version
        self.is_loaded = False
        self.load_time = None
        self.metadata = {
            'model_type': 'mock_model',
            'input_shape': [10],
            'output_shape': [1],
            'accuracy': 0.85
        }
    
    def load(self) -> None:
        """Mock model loading."""
        self.is_loaded = True
        self.load_time = datetime.now(timezone.utc)
        time.sleep(0.1)  # Simulate loading time
    
    def predict(self, input_data: Dict[str, Any]) -> Any:
        """Mock prediction."""
        if not self.is_loaded:
            raise ValueError("Model not loaded")
        
        # Mock prediction logic
        features = input_data.get('features', [0] * 10)
        prediction = sum(features) * 0.1 + np.random.normal(0, 0.05)
        confidence = max(0, min(1, 1 - abs(prediction)))
        
        return {
            'prediction': prediction,
            'confidence': confidence,
            'model_info': self.metadata
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        return self.metadata


async def demo_model_server():
    """Demonstrate model server functionality."""
    print("\n" + "="*60)
    print("🚀 DEMO: Model Server")
    print("="*60)
    
    # Create server config
    config = ServerConfig(
        server_name="demo_server",
        max_concurrent_requests=50,
        request_timeout_seconds=30.0,
        enable_batching=True,
        enable_caching=True,
        cache_size=100
    )
    
    # Create and start server
    server = ModelServer(config)
    await server.start()
    
    # Register mock model
    mock_model = MockMLModel("demo_model", "1.0.0")
    mock_model.load()
    
    # Register model with server (using a simple wrapper)
    class ModelWrapper:
        def __init__(self, model):
            self.model_name = model.model_name
            self.model_version = model.model_version
            self.is_loaded = model.is_loaded
            self.load_time = model.load_time
            self.metadata = model.metadata
        
        def load(self):
            pass
        
        def predict(self, input_data):
            return self.model.predict(input_data)
        
        def get_model_info(self):
            return self.model.metadata
        
        def unload(self):
            pass
    
    # Create wrapper and register
    wrapper = ModelWrapper(mock_model)
    wrapper.model = mock_model
    server.register_model(wrapper)
    
    print(f"Server started: {config.server_name}")
    print(f"Max concurrent requests: {config.max_concurrent_requests}")
    print(f"Caching enabled: {config.enable_caching}")
    
    # Make some predictions
    print(f"\nMaking predictions...")
    for i in range(5):
        input_data = {
            'features': [np.random.random() for _ in range(10)]
        }
        
        response = await server.predict(
            model_name="demo_model",
            model_version="1.0.0",
            input_data=input_data
        )
        
        print(f"  Request {i+1}: Prediction = {response.prediction['prediction']:.4f}, "
              f"Confidence = {response.prediction['confidence']:.4f}, "
              f"Latency = {response.latency_ms:.2f}ms")
    
    # Get server metrics
    metrics = server.get_metrics()
    print(f"\nServer Metrics:")
    print(f"  Total requests: {metrics['total_requests']}")
    print(f"  Success rate: {metrics['success_rate']:.2%}")
    print(f"  Avg latency: {metrics['avg_latency_ms']:.2f}ms")
    print(f"  Cache hit rate: {metrics['cache_hit_rate']:.2%}")
    
    # Get health status
    health = server.get_health_status()
    print(f"\nHealth Status:")
    print(f"  Healthy: {health['healthy']}")
    print(f"  Uptime: {health['uptime_seconds']:.1f}s")
    print(f"  Loaded models: {health['loaded_models']}")
    
    await server.stop()
    print(f"\n✅ Model server demo completed!")


async def demo_load_balancer():
    """Demonstrate load balancer functionality."""
    print("\n" + "="*60)
    print("⚖️  DEMO: Load Balancer")
    print("="*60)
    
    # Create load balancer
    health_check = HealthCheck(
        interval_seconds=10,
        timeout_seconds=2.0,
        failure_threshold=2
    )
    
    lb = LoadBalancer(
        strategy=LoadBalancingStrategy.ROUND_ROBIN,
        health_check=health_check,
        enable_sticky_sessions=True
    )
    
    await lb.start()
    
    # Add servers
    servers = [
        ("server-1", "http://localhost:8001", 1),
        ("server-2", "http://localhost:8002", 1),
        ("server-3", "http://localhost:8003", 2),  # Higher weight
    ]
    
    for server_id, endpoint, weight in servers:
        lb.add_server(server_id, endpoint, weight)
        print(f"Added server: {server_id} at {endpoint} (weight: {weight})")
    
    print(f"\nLoad balancing strategy: {lb.strategy.value}")
    print(f"Health check interval: {health_check.interval_seconds}s")
    
    # Test server selection
    print(f"\nTesting server selection...")
    selected_servers = []
    for i in range(10):
        server = lb.select_server(f"client-{i % 3}")  # 3 different clients
        if server:
            selected_servers.append(server.server_id)
            print(f"  Request {i+1}: Selected {server.server_id}")
            
            # Record request metrics
            lb.record_request(server.server_id, True, 50.0 + np.random.random() * 20)
        else:
            print(f"  Request {i+1}: No healthy servers available")
    
    # Show selection distribution
    from collections import Counter
    selection_counts = Counter(selected_servers)
    print(f"\nSelection distribution:")
    for server_id, count in selection_counts.items():
        print(f"  {server_id}: {count} requests")
    
    # Get server stats
    stats = lb.get_server_stats()
    print(f"\nServer Statistics:")
    print(f"  Total servers: {stats['total_servers']}")
    print(f"  Healthy servers: {stats['healthy_servers']}")
    print(f"  Total requests: {stats['total_requests']}")
    print(f"  Failure rate: {stats['failure_rate']:.2%}")
    print(f"  Avg response time: {stats['avg_response_time_ms']:.2f}ms")
    
    # Test different strategies
    print(f"\nTesting different load balancing strategies...")
    strategies = [
        LoadBalancingStrategy.LEAST_CONNECTIONS,
        LoadBalancingStrategy.LEAST_RESPONSE_TIME,
        LoadBalancingStrategy.RANDOM
    ]
    
    for strategy in strategies:
        lb.strategy = strategy
        print(f"\n  Strategy: {strategy.value}")
        
        selections = []
        for _ in range(5):
            server = lb.select_server()
            if server:
                selections.append(server.server_id)
        
        if selections:
            selection_counts = Counter(selections)
            for server_id, count in selection_counts.items():
                print(f"    {server_id}: {count} selections")
    
    await lb.stop()
    print(f"\n✅ Load balancer demo completed!")


async def demo_auto_scaler():
    """Demonstrate auto scaler functionality."""
    print("\n" + "="*60)
    print("📈 DEMO: Auto Scaler")
    print("="*60)
    
    # Create auto scaler
    scaler = AutoScaler(
        min_replicas=1,
        max_replicas=5,
        initial_replicas=2,
        metrics_collection_interval=10,
        scaling_evaluation_interval=30
    )
    
    # Mock scaling callbacks
    def scale_up(count: int) -> bool:
        print(f"  🔺 Scaling UP by {count} replicas")
        return True
    
    def scale_down(count: int) -> bool:
        print(f"  🔻 Scaling DOWN by {count} replicas")
        return True
    
    scaler.set_scaling_callbacks(scale_up, scale_down)
    
    # Add scaling rules
    cpu_rule = ScalingRule(
        policy=ScalingPolicy.CPU_BASED,
        metric_name='cpu_percent',
        threshold=70.0,
        comparison_operator='gt',
        action=ScalingAction.SCALE_UP,
        scale_amount=1,
        cooldown_seconds=60
    )
    
    memory_rule = ScalingRule(
        policy=ScalingPolicy.MEMORY_BASED,
        metric_name='memory_percent',
        threshold=80.0,
        comparison_operator='gt',
        action=ScalingAction.SCALE_UP,
        scale_amount=1,
        cooldown_seconds=120
    )
    
    low_cpu_rule = ScalingRule(
        policy=ScalingPolicy.CPU_BASED,
        metric_name='cpu_percent',
        threshold=20.0,
        comparison_operator='lt',
        action=ScalingAction.SCALE_DOWN,
        scale_amount=1,
        cooldown_seconds=300
    )
    
    scaler.add_scaling_rule(cpu_rule)
    scaler.add_scaling_rule(memory_rule)
    scaler.add_scaling_rule(low_cpu_rule)
    
    print(f"Auto scaler initialized:")
    print(f"  Min replicas: {scaler.min_replicas}")
    print(f"  Max replicas: {scaler.max_replicas}")
    print(f"  Initial replicas: {scaler.current_replicas}")
    print(f"  Scaling rules: {len(scaler.scaling_rules)}")
    
    # Start auto scaler
    await scaler.start()
    
    # Simulate some scaling events
    print(f"\nSimulating scaling events...")
    
    # Wait for initial metrics collection
    await asyncio.sleep(15)
    
    # Check status
    status = scaler.get_scaling_status()
    print(f"\nCurrent Status:")
    print(f"  Current replicas: {status['current_replicas']}")
    print(f"  Active rules: {status['active_scaling_rules']}")
    print(f"  Active cooldowns: {status['active_cooldowns']}")
    print(f"  Metrics collected: {status['total_metrics_collected']}")
    
    if status['metrics_summary']:
        print(f"  Recent metrics:")
        for metric, value in status['metrics_summary'].items():
            print(f"    {metric}: {value:.2f}")
    
    # Manual scaling
    print(f"\nTesting manual scaling...")
    success = scaler.manual_scale(4)
    print(f"  Manual scale to 4 replicas: {'Success' if success else 'Failed'}")
    
    # Get scaling rules
    rules = scaler.get_scaling_rules()
    print(f"\nScaling Rules:")
    for i, rule in enumerate(rules):
        print(f"  Rule {i+1}: {rule['policy']} {rule['comparison_operator']} {rule['threshold']}")
        print(f"    Action: {rule['action']}, Cooldown: {rule['cooldown_seconds']}s")
    
    await scaler.stop()
    print(f"\n✅ Auto scaler demo completed!")


async def demo_model_registry():
    """Demonstrate model registry functionality."""
    print("\n" + "="*60)
    print("📚 DEMO: Model Registry")
    print("="*60)
    
    # Create model registry
    registry = ModelRegistry("./demo_registry")
    
    print(f"Model registry initialized at: {registry.registry_path}")
    
    # Register some mock models
    print(f"\nRegistering models...")
    
    # Create mock model files
    model_files = []
    for i in range(3):
        model_path = f"./mock_model_{i+1}.pkl"
        with open(model_path, 'wb') as f:
            import pickle
            pickle.dump({'model_data': f'model_{i+1}', 'weights': np.random.random(100)}, f)
        model_files.append(model_path)
    
    # Register models
    for i, model_path in enumerate(model_files):
        version = f"1.{i}.0"
        model_version = registry.register_model(
            model_name="demo_model",
            model_path=model_path,
            version=version,
            description=f"Demo model version {version}",
            tags=["demo", "ml", f"v{i+1}"],
            created_by="demo_user",
            performance_metrics={
                'accuracy': 0.85 + i * 0.05,
                'precision': 0.82 + i * 0.03,
                'recall': 0.88 + i * 0.02
            },
            training_config={
                'algorithm': 'random_forest',
                'max_depth': 10 + i,
                'n_estimators': 100 + i * 50
            }
        )
        
        print(f"  Registered {model_version.model_name}:{model_version.version}")
        print(f"    Size: {model_version.size_bytes} bytes")
        print(f"    Checksum: {model_version.checksum[:8]}...")
    
    # List models
    models = registry.list_models()
    print(f"\nRegistered models: {models}")
    
    # List versions
    versions = registry.list_model_versions("demo_model")
    print(f"\nModel versions for 'demo_model':")
    for version in versions:
        print(f"  {version.version}: {version.description}")
        print(f"    Created: {version.created_at.strftime('%Y-%m-%d %H:%M')}")
        print(f"    Performance: accuracy={version.performance_metrics['accuracy']:.3f}")
    
    # Get latest version
    latest = registry.get_latest_version("demo_model")
    if latest:
        print(f"\nLatest version: {latest.version}")
        print(f"  Accuracy: {latest.performance_metrics['accuracy']:.3f}")
    
    # Create deployments
    print(f"\nCreating deployments...")
    
    for i, version in enumerate(versions):
        deployment = registry.create_deployment(
            model_name="demo_model",
            model_version=version.version,
            environment=f"env_{i+1}",
            replicas=2 + i,
            endpoint_url=f"http://localhost:800{i+1}",
            deployed_by="demo_user"
        )
        
        print(f"  Created deployment: {deployment.deployment_id}")
        print(f"    Environment: {deployment.environment}")
        print(f"    Replicas: {deployment.replicas}")
        
        # Update deployment status
        registry.update_deployment_status(
            deployment.deployment_id,
            DeploymentStatus.ACTIVE,
            endpoint_url=f"http://localhost:800{i+1}/predict"
        )
    
    # List deployments
    deployments = registry.list_deployments()
    print(f"\nActive deployments:")
    for deployment in deployments:
        print(f"  {deployment.deployment_id}")
        print(f"    Status: {deployment.status.value}")
        print(f"    Environment: {deployment.environment}")
        print(f"    Endpoint: {deployment.endpoint_url}")
    
    # Get registry summary
    summary = registry.get_registry_summary()
    print(f"\nRegistry Summary:")
    print(f"  Total models: {summary['total_models']}")
    print(f"  Total versions: {summary['total_versions']}")
    print(f"  Total deployments: {summary['total_deployments']}")
    print(f"  Active deployments: {summary['active_deployments']}")
    
    # Cleanup
    import shutil
    shutil.rmtree("./demo_registry", ignore_errors=True)
    for model_file in model_files:
        os.remove(model_file)
    
    print(f"\n✅ Model registry demo completed!")


async def demo_deployment_manager():
    """Demonstrate deployment manager functionality."""
    print("\n" + "="*60)
    print("🚀 DEMO: Deployment Manager")
    print("="*60)
    
    # Create components
    registry = ModelRegistry("./demo_deployment_registry")
    lb = LoadBalancer(strategy=LoadBalancingStrategy.ROUND_ROBIN)
    dm = DeploymentManager(registry, lb)
    
    # Mock instance callbacks
    def create_instance(config):
        # Mock server creation
        class MockServer:
            def __init__(self, config):
                self.config = config
                self.is_running = False
            
            async def start(self):
                self.is_running = True
            
            async def stop(self):
                self.is_running = False
        
        return MockServer(config)
    
    def destroy_instance(instance_id):
        return True
    
    dm.set_instance_callbacks(create_instance, destroy_instance)
    
    print(f"Deployment manager initialized")
    
    # Register a model first
    model_path = "./demo_model.pkl"
    with open(model_path, 'wb') as f:
        import pickle
        pickle.dump({'model_data': 'demo'}, f)
    
    registry.register_model(
        model_name="demo_model",
        model_path=model_path,
        version="1.0.0",
        description="Demo model for deployment"
    )
    
    # Create deployment configs for different strategies
    strategies = [
        DeploymentStrategy.IMMEDIATE,
        DeploymentStrategy.ROLLING,
        DeploymentStrategy.BLUE_GREEN,
        DeploymentStrategy.CANARY
    ]
    
    for i, strategy in enumerate(strategies):
        config = DeploymentConfig(
            deployment_id=f"demo-deployment-{i+1}",
            model_name="demo_model",
            model_version="1.0.0",
            environment="demo",
            strategy=strategy,
            replicas=2,
            health_check_interval=10,
            deployment_timeout=60
        )
        
        print(f"\nDeploying with {strategy.value} strategy...")
        success = await dm.deploy(config)
        
        if success:
            print(f"  ✅ Deployment successful")
            
            # Get deployment status
            status = dm.get_deployment_status(config.deployment_id)
            if status:
                print(f"  Total instances: {status['total_instances']}")
                print(f"  Healthy instances: {status['healthy_instances']}")
        else:
            print(f"  ❌ Deployment failed")
    
    # List active deployments
    deployments = dm.list_deployments()
    print(f"\nActive deployments: {len(deployments)}")
    for deployment_id in deployments:
        print(f"  {deployment_id}")
    
    # Cleanup
    import shutil
    shutil.rmtree("./demo_deployment_registry", ignore_errors=True)
    os.remove(model_path)
    
    print(f"\n✅ Deployment manager demo completed!")


async def demo_model_cache():
    """Demonstrate model cache functionality."""
    print("\n" + "="*60)
    print("💾 DEMO: Model Cache")
    print("="*60)
    
    # Create cache with different policies
    policies = [
        CachePolicy.LRU,
        CachePolicy.LFU,
        CachePolicy.TTL,
        CachePolicy.SIZE_BASED
    ]
    
    for policy in policies:
        print(f"\nTesting {policy.value} cache policy...")
        
        cache = ModelCache(
            max_size=5,
            max_memory_bytes=1024 * 1024,  # 1MB
            eviction_policy=policy,
            default_ttl_seconds=30 if policy == CachePolicy.TTL else None
        )
        
        # Add some entries
        test_data = [
            ("model_1", {"weights": np.random.random(1000)}, 1000),
            ("model_2", {"weights": np.random.random(2000)}, 2000),
            ("model_3", {"weights": np.random.random(500)}, 500),
            ("model_4", {"weights": np.random.random(1500)}, 1500),
            ("model_5", {"weights": np.random.random(800)}, 800),
            ("model_6", {"weights": np.random.random(1200)}, 1200),  # Should trigger eviction
        ]
        
        print(f"  Adding entries...")
        for key, value, size in test_data:
            success = cache.put(key, value, size_bytes=size)
            print(f"    {key}: {'✅' if success else '❌'} (size: {size} bytes)")
        
        # Test cache hits
        print(f"  Testing cache access...")
        for i in range(3):
            for key, _, _ in test_data[:3]:  # Access first 3 entries multiple times
                result = cache.get(key)
                if result:
                    print(f"    Cache hit for {key}")
        
        # Get cache stats
        stats = cache.get_stats()
        print(f"  Cache Statistics:")
        print(f"    Size: {stats['cache_size']}/{stats['max_size']}")
        print(f"    Memory: {stats['memory_usage_bytes']}/{stats['max_memory_bytes']} bytes")
        print(f"    Hit rate: {stats['hit_rate']:.2%}")
        print(f"    Evictions: {stats['evictions']}")
        
        # Get cache keys
        keys = cache.get_cache_keys()
        print(f"    Cached keys: {keys}")
        
        cache.close()
    
    print(f"\n✅ Model cache demo completed!")


async def demo_api_gateway():
    """Demonstrate API gateway functionality."""
    print("\n" + "="*60)
    print("🌐 DEMO: API Gateway")
    print("="*60)
    
    # Create gateway config
    config = GatewayConfig(
        gateway_name="demo_gateway",
        listen_host="0.0.0.0",
        listen_port=8080,
        enable_authentication=True,
        enable_rate_limiting=True,
        rate_limit=RateLimit(
            requests_per_minute=60,
            burst_limit=10
        ),
        authentication=Authentication(
            enabled=True,
            api_keys=["demo-api-key-1", "demo-api-key-2"],
            require_authentication=True
        )
    )
    
    # Create gateway
    gateway = APIGateway(config)
    await gateway.start()
    
    print(f"API Gateway started: {config.gateway_name}")
    print(f"  Host: {config.listen_host}:{config.listen_port}")
    print(f"  Authentication: {config.enable_authentication}")
    print(f"  Rate limiting: {config.enable_rate_limiting}")
    print(f"  Rate limit: {config.rate_limit.requests_per_minute} req/min")
    
    # Add routes
    async def predict_handler(request):
        return {
            "prediction": np.random.random(),
            "confidence": 0.85,
            "model": "demo_model"
        }
    
    async def health_handler(request):
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}
    
    gateway.add_route("/predict", predict_handler)
    gateway.add_route("/health", health_handler)
    
    print(f"\nAdded routes: /predict, /health")
    
    # Test requests
    print(f"\nTesting requests...")
    
    # Valid requests
    valid_headers = {"X-API-Key": "demo-api-key-1"}
    
    for i in range(5):
        response = await gateway.handle_request(
            endpoint="/predict",
            method="POST",
            headers=valid_headers,
            body={"features": [1, 2, 3, 4, 5]},
            client_ip=f"192.168.1.{i+1}"
        )
        
        print(f"  Request {i+1}: Status {response.status_code}, "
              f"Latency {response.latency_ms:.2f}ms")
        if response.error:
            print(f"    Error: {response.error}")
    
    # Invalid API key
    invalid_headers = {"X-API-Key": "invalid-key"}
    response = await gateway.handle_request(
        endpoint="/predict",
        method="POST",
        headers=invalid_headers,
        body={"features": [1, 2, 3, 4, 5]}
    )
    print(f"  Invalid API key: Status {response.status_code}")
    
    # Rate limiting test
    print(f"\nTesting rate limiting...")
    for i in range(15):  # Exceed rate limit
        response = await gateway.handle_request(
            endpoint="/predict",
            method="POST",
            headers=valid_headers,
            body={"features": [1, 2, 3, 4, 5]},
            client_ip="192.168.1.100"
        )
        if response.status_code == 429:
            print(f"  Rate limited at request {i+1}")
            break
    
    # Get metrics
    metrics = gateway.get_metrics()
    print(f"\nGateway Metrics:")
    print(f"  Total requests: {metrics['total_requests']}")
    print(f"  Success rate: {metrics['success_rate']:.2%}")
    print(f"  Avg response time: {metrics['avg_response_time_ms']:.2f}ms")
    print(f"  Rate limited requests: {metrics['rate_limited_requests']}")
    print(f"  Authentication failures: {metrics['authentication_failures']}")
    
    # Get client stats
    client_stats = gateway.get_client_stats()
    print(f"\nClient Statistics:")
    for client_id, stats in client_stats.items():
        print(f"  {client_id}: {stats['recent_requests']} recent requests")
    
    await gateway.stop()
    print(f"\n✅ API gateway demo completed!")


async def demo_comprehensive_deployment():
    """Demonstrate comprehensive deployment workflow."""
    print("\n" + "="*60)
    print("🎯 DEMO: Comprehensive Deployment Workflow")
    print("="*60)
    
    print("This demo showcases a complete ML deployment pipeline:")
    print("1. Model Registry - Version control and metadata management")
    print("2. Model Server - High-performance inference serving")
    print("3. Load Balancer - Traffic distribution and health monitoring")
    print("4. Auto Scaler - Dynamic scaling based on metrics")
    print("5. Deployment Manager - Blue-green, rolling, and canary deployments")
    print("6. Model Cache - Intelligent caching for performance")
    print("7. API Gateway - Authentication, rate limiting, and routing")
    
    # Create all components
    registry = ModelRegistry("./comprehensive_demo_registry")
    
    # Register a model
    model_path = "./comprehensive_demo_model.pkl"
    with open(model_path, 'wb') as f:
        import pickle
        pickle.dump({'model_data': 'comprehensive_demo', 'weights': np.random.random(1000)}, f)
    
    model_version = registry.register_model(
        model_name="production_model",
        model_path=model_path,
        version="1.0.0",
        description="Production-ready ML model",
        tags=["production", "ml", "trading"],
        created_by="ml_engineer",
        performance_metrics={
            'accuracy': 0.92,
            'precision': 0.89,
            'recall': 0.94,
            'f1_score': 0.91
        }
    )
    
    print(f"\n✅ Model registered: {model_version.model_name}:{model_version.version}")
    
    # Create deployment
    deployment = registry.create_deployment(
        model_name="production_model",
        model_version="1.0.0",
        environment="production",
        replicas=3,
        endpoint_url="http://production-ml-api.company.com",
        deployed_by="ml_engineer"
    )
    
    print(f"✅ Deployment created: {deployment.deployment_id}")
    
    # Setup load balancer
    lb = LoadBalancer(
        strategy=LoadBalancingStrategy.LEAST_RESPONSE_TIME,
        health_check=HealthCheck(interval_seconds=30)
    )
    
    # Add servers to load balancer
    for i in range(3):
        lb.add_server(
            f"prod-server-{i+1}",
            f"http://prod-server-{i+1}.company.com:8000",
            weight=1
        )
    
    print(f"✅ Load balancer configured with {len(lb.servers)} servers")
    
    # Setup auto scaler
    scaler = AutoScaler(
        min_replicas=2,
        max_replicas=10,
        initial_replicas=3
    )
    
    # Add scaling rules
    scaler.add_scaling_rule(ScalingRule(
        policy=ScalingPolicy.REQUEST_RATE_BASED,
        metric_name='request_rate_per_second',
        threshold=100.0,
        comparison_operator='gt',
        action=ScalingAction.SCALE_UP,
        scale_amount=1,
        cooldown_seconds=300
    ))
    
    print(f"✅ Auto scaler configured with {len(scaler.scaling_rules)} rules")
    
    # Setup API gateway
    gateway = APIGateway(GatewayConfig(
        gateway_name="production_gateway",
        enable_authentication=True,
        enable_rate_limiting=True,
        rate_limit=RateLimit(requests_per_minute=1000, burst_limit=50),
        authentication=Authentication(
            enabled=True,
            api_keys=["prod-api-key-1", "prod-api-key-2"]
        )
    ))
    
    print(f"✅ API gateway configured with authentication and rate limiting")
    
    # Get comprehensive status
    print(f"\n📊 Production System Status:")
    
    # Registry status
    registry_summary = registry.get_registry_summary()
    print(f"  Model Registry:")
    print(f"    Models: {registry_summary['total_models']}")
    print(f"    Versions: {registry_summary['total_versions']}")
    print(f"    Deployments: {registry_summary['total_deployments']}")
    
    # Load balancer status
    lb_stats = lb.get_server_stats()
    print(f"  Load Balancer:")
    print(f"    Healthy servers: {lb_stats['healthy_servers']}/{lb_stats['total_servers']}")
    print(f"    Total requests: {lb_stats['total_requests']}")
    print(f"    Avg response time: {lb_stats['avg_response_time_ms']:.2f}ms")
    
    # Auto scaler status
    scaler_status = scaler.get_scaling_status()
    print(f"  Auto Scaler:")
    print(f"    Current replicas: {scaler_status['current_replicas']}")
    print(f"    Active rules: {scaler_status['active_scaling_rules']}")
    print(f"    Metrics collected: {scaler_status['total_metrics_collected']}")
    
    # API gateway status
    gateway_metrics = gateway.get_metrics()
    print(f"  API Gateway:")
    print(f"    Total requests: {gateway_metrics['total_requests']}")
    print(f"    Success rate: {gateway_metrics['success_rate']:.2%}")
    print(f"    Active clients: {gateway_metrics['active_clients']}")
    
    print(f"\n🎉 Comprehensive deployment workflow completed!")
    print(f"   The system is ready for production ML model serving!")
    
    # Cleanup
    import shutil
    shutil.rmtree("./comprehensive_demo_registry", ignore_errors=True)
    os.remove(model_path)


async def main():
    """Run all deployment infrastructure demos."""
    print("🚀 Production Deployment Infrastructure Demo (Phase 5D.3)")
    print("=" * 60)
    
    try:
        # Run individual demos
        await demo_model_server()
        await demo_load_balancer()
        await demo_auto_scaler()
        await demo_model_registry()
        await demo_deployment_manager()
        await demo_model_cache()
        await demo_api_gateway()
        
        # Run comprehensive integration demo
        await demo_comprehensive_deployment()
        
        print("\n" + "="*60)
        print("🎉 All deployment infrastructure demos completed successfully!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error running deployment demos: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
