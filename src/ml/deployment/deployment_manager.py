"""
Deployment Manager for orchestrating ML model deployments.
Provides blue-green deployments, rollbacks, and deployment strategies.
"""

import time
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import uuid

from .model_registry import ModelRegistry, ModelVersion, DeploymentStatus
from .model_server import ModelServer, ServerConfig
from .load_balancer import LoadBalancer, LoadBalancingStrategy

logger = logging.getLogger(__name__)


class DeploymentStrategy(Enum):
    """Deployment strategies."""
    BLUE_GREEN = "blue_green"
    ROLLING = "rolling"
    CANARY = "canary"
    IMMEDIATE = "immediate"


@dataclass
class DeploymentConfig:
    """Configuration for deployments."""
    deployment_id: str
    model_name: str
    model_version: str
    environment: str
    strategy: DeploymentStrategy
    replicas: int = 1
    health_check_interval: int = 30
    health_check_timeout: int = 5
    max_unhealthy_instances: int = 0
    deployment_timeout: int = 600  # 10 minutes
    rollback_enabled: bool = True
    rollback_threshold: float = 0.1  # 10% error rate
    rollback_evaluation_period: int = 300  # 5 minutes
    
    # Blue-green specific
    blue_green_switch_time: int = 60  # 1 minute
    
    # Canary specific
    canary_percentage: float = 0.1  # 10%
    canary_evaluation_time: int = 300  # 5 minutes
    
    # Rolling specific
    rolling_max_surge: int = 1
    rolling_max_unavailable: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'deployment_id': self.deployment_id,
            'model_name': self.model_name,
            'model_version': self.model_version,
            'environment': self.environment,
            'strategy': self.strategy.value,
            'replicas': self.replicas,
            'health_check_interval': self.health_check_interval,
            'health_check_timeout': self.health_check_timeout,
            'max_unhealthy_instances': self.max_unhealthy_instances,
            'deployment_timeout': self.deployment_timeout,
            'rollback_enabled': self.rollback_enabled,
            'rollback_threshold': self.rollback_threshold,
            'rollback_evaluation_period': self.rollback_evaluation_period,
            'blue_green_switch_time': self.blue_green_switch_time,
            'canary_percentage': self.canary_percentage,
            'canary_evaluation_time': self.canary_evaluation_time,
            'rolling_max_surge': self.rolling_max_surge,
            'rolling_max_unavailable': self.rolling_max_unavailable
        }


@dataclass
class DeploymentInstance:
    """Container for deployment instance information."""
    instance_id: str
    server_config: ServerConfig
    model_server: Optional[ModelServer]
    is_healthy: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_health_check: Optional[datetime] = None
    request_count: int = 0
    error_count: int = 0
    endpoint: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'instance_id': self.instance_id,
            'server_config': self.server_config.__dict__,
            'is_healthy': self.is_healthy,
            'created_at': self.created_at.isoformat(),
            'last_health_check': self.last_health_check.isoformat() if self.last_health_check else None,
            'request_count': self.request_count,
            'error_count': self.error_count,
            'endpoint': self.endpoint
        }


class DeploymentManager:
    """
    Deployment manager for orchestrating ML model deployments.
    """
    
    def __init__(self, 
                 model_registry: ModelRegistry,
                 load_balancer: LoadBalancer,
                 base_port: int = 8000):
        self.model_registry = model_registry
        self.load_balancer = load_balancer
        self.base_port = base_port
        
        # Deployment tracking
        self.active_deployments: Dict[str, Dict[str, DeploymentInstance]] = {}
        self.deployment_configs: Dict[str, DeploymentConfig] = {}
        self.deployment_tasks: Dict[str, asyncio.Task] = {}
        
        # Health check tasks
        self.health_check_tasks: Dict[str, asyncio.Task] = {}
        
        # Callbacks
        self.instance_creator: Optional[Callable[[ServerConfig], ModelServer]] = None
        self.instance_destroyer: Optional[Callable[[str], bool]] = None
        
        logger.info("Initialized deployment manager")
    
    def set_instance_callbacks(self, 
                              creator: Callable[[ServerConfig], ModelServer],
                              destroyer: Callable[[str], bool]) -> None:
        """Set instance creation and destruction callbacks."""
        self.instance_creator = creator
        self.instance_destroyer = destroyer
        logger.info("Set instance callbacks")
    
    async def deploy(self, config: DeploymentConfig) -> bool:
        """
        Deploy a model version.
        
        Args:
            config: Deployment configuration
            
        Returns:
            True if deployment successful, False otherwise
        """
        logger.info(f"Starting deployment {config.deployment_id} for {config.model_name}:{config.model_version}")
        
        # Check if model version exists
        model_version = self.model_registry.get_model_version(config.model_name, config.model_version)
        if not model_version:
            logger.error(f"Model version {config.model_name}:{config.model_version} not found")
            return False
        
        # Create deployment record
        deployment = self.model_registry.create_deployment(
            model_name=config.model_name,
            model_version=config.model_version,
            environment=config.environment,
            replicas=config.replicas,
            deployment_config=config.to_dict()
        )
        
        # Store deployment config
        self.deployment_configs[config.deployment_id] = config
        
        # Initialize deployment instances
        self.active_deployments[config.deployment_id] = {}
        
        try:
            # Execute deployment based on strategy
            success = False
            if config.strategy == DeploymentStrategy.BLUE_GREEN:
                success = await self._deploy_blue_green(config)
            elif config.strategy == DeploymentStrategy.ROLLING:
                success = await self._deploy_rolling(config)
            elif config.strategy == DeploymentStrategy.CANARY:
                success = await self._deploy_canary(config)
            elif config.strategy == DeploymentStrategy.IMMEDIATE:
                success = await self._deploy_immediate(config)
            else:
                logger.error(f"Unsupported deployment strategy: {config.strategy}")
                return False
            
            if success:
                # Update deployment status
                self.model_registry.update_deployment_status(
                    deployment.deployment_id,
                    DeploymentStatus.ACTIVE,
                    endpoint_url=f"http://localhost:{self.base_port}/{config.deployment_id}"
                )
                
                # Start monitoring
                await self._start_deployment_monitoring(config)
                
                logger.info(f"Deployment {config.deployment_id} completed successfully")
                return True
            else:
                # Mark deployment as failed
                self.model_registry.update_deployment_status(
                    deployment.deployment_id,
                    DeploymentStatus.FAILED
                )
                
                # Clean up instances
                await self._cleanup_deployment(config.deployment_id)
                
                logger.error(f"Deployment {config.deployment_id} failed")
                return False
                
        except Exception as e:
            logger.error(f"Deployment {config.deployment_id} error: {e}")
            
            # Mark deployment as failed
            self.model_registry.update_deployment_status(
                deployment.deployment_id,
                DeploymentStatus.FAILED
            )
            
            # Clean up instances
            await self._cleanup_deployment(config.deployment_id)
            
            return False
    
    async def _deploy_blue_green(self, config: DeploymentConfig) -> bool:
        """Execute blue-green deployment."""
        logger.info(f"Starting blue-green deployment for {config.deployment_id}")
        
        # Create new (green) instances
        green_instances = await self._create_instances(config, "green")
        if not green_instances:
            return False
        
        # Wait for green instances to be healthy
        if not await self._wait_for_instances_healthy(green_instances, config):
            await self._cleanup_instances(green_instances)
            return False
        
        # Switch traffic to green instances
        await self._switch_traffic_to_instances(green_instances, config)
        
        # Wait for switch time
        await asyncio.sleep(config.blue_green_switch_time)
        
        # Remove old (blue) instances if they exist
        if config.deployment_id in self.active_deployments:
            old_instances = list(self.active_deployments[config.deployment_id].values())
            await self._cleanup_instances(old_instances)
        
        # Store new instances
        self.active_deployments[config.deployment_id] = {
            instance.instance_id: instance for instance in green_instances
        }
        
        return True
    
    async def _deploy_rolling(self, config: DeploymentConfig) -> bool:
        """Execute rolling deployment."""
        logger.info(f"Starting rolling deployment for {config.deployment_id}")
        
        existing_instances = list(self.active_deployments.get(config.deployment_id, {}).values())
        new_instances = []
        
        # Calculate deployment steps
        max_surge = config.rolling_max_surge
        max_unavailable = config.rolling_max_unavailable
        
        # Deploy new instances
        for i in range(config.replicas):
            new_instance = await self._create_single_instance(config, f"rolling-{i}")
            if not new_instance:
                # Rollback on failure
                await self._cleanup_instances(new_instances)
                return False
            
            new_instances.append(new_instance)
            
            # Wait for instance to be healthy
            if not await self._wait_for_instance_healthy(new_instance, config):
                await self._cleanup_instances(new_instances)
                return False
            
            # Add to load balancer
            self.load_balancer.add_server(
                new_instance.instance_id,
                new_instance.endpoint or f"http://localhost:{self.base_port + i}"
            )
        
        # Remove old instances
        await self._cleanup_instances(existing_instances)
        
        # Store new instances
        self.active_deployments[config.deployment_id] = {
            instance.instance_id: instance for instance in new_instances
        }
        
        return True
    
    async def _deploy_canary(self, config: DeploymentConfig) -> bool:
        """Execute canary deployment."""
        logger.info(f"Starting canary deployment for {config.deployment_id}")
        
        # Calculate canary instances
        canary_replicas = max(1, int(config.replicas * config.canary_percentage))
        main_replicas = config.replicas - canary_replicas
        
        # Deploy canary instances
        canary_instances = await self._create_instances(config, "canary", canary_replicas)
        if not canary_instances:
            return False
        
        # Wait for canary instances to be healthy
        if not await self._wait_for_instances_healthy(canary_instances, config):
            await self._cleanup_instances(canary_instances)
            return False
        
        # Add canary instances to load balancer with limited traffic
        for instance in canary_instances:
            self.load_balancer.add_server(
                instance.instance_id,
                instance.endpoint or f"http://localhost:{self.base_port}",
                weight=1  # Lower weight for canary
            )
        
        # Evaluate canary performance
        await asyncio.sleep(config.canary_evaluation_time)
        
        # Check if canary is performing well
        if await self._evaluate_canary_performance(canary_instances, config):
            # Deploy remaining instances
            main_instances = await self._create_instances(config, "main", main_replicas)
            if main_instances:
                # Wait for main instances to be healthy
                if await self._wait_for_instances_healthy(main_instances, config):
                    # Add main instances to load balancer
                    for instance in main_instances:
                        self.load_balancer.add_server(
                            instance.instance_id,
                            instance.endpoint or f"http://localhost:{self.base_port}",
                            weight=10  # Higher weight for main instances
                        )
                    
                    # Store all instances
                    all_instances = canary_instances + main_instances
                    self.active_deployments[config.deployment_id] = {
                        instance.instance_id: instance for instance in all_instances
                    }
                    
                    return True
        
        # Canary failed or main deployment failed
        await self._cleanup_instances(canary_instances)
        return False
    
    async def _deploy_immediate(self, config: DeploymentConfig) -> bool:
        """Execute immediate deployment."""
        logger.info(f"Starting immediate deployment for {config.deployment_id}")
        
        # Create all instances at once
        instances = await self._create_instances(config, "immediate")
        if not instances:
            return False
        
        # Wait for all instances to be healthy
        if not await self._wait_for_instances_healthy(instances, config):
            await self._cleanup_instances(instances)
            return False
        
        # Add all instances to load balancer
        for instance in instances:
            self.load_balancer.add_server(
                instance.instance_id,
                instance.endpoint or f"http://localhost:{self.base_port}"
            )
        
        # Store instances
        self.active_deployments[config.deployment_id] = {
            instance.instance_id: instance for instance in instances
        }
        
        return True
    
    async def _create_instances(self, 
                              config: DeploymentConfig, 
                              instance_type: str, 
                              count: Optional[int] = None) -> List[DeploymentInstance]:
        """Create deployment instances."""
        if count is None:
            count = config.replicas
        
        instances = []
        for i in range(count):
            instance = await self._create_single_instance(config, f"{instance_type}-{i}")
            if instance:
                instances.append(instance)
            else:
                # If any instance creation fails, clean up all created instances
                await self._cleanup_instances(instances)
                return []
        
        return instances
    
    async def _create_single_instance(self, 
                                    config: DeploymentConfig, 
                                    instance_id: str) -> Optional[DeploymentInstance]:
        """Create a single deployment instance."""
        try:
            # Create server config
            server_config = ServerConfig(
                server_name=f"{config.deployment_id}-{instance_id}",
                max_concurrent_requests=100,
                request_timeout_seconds=30.0,
                enable_batching=True,
                enable_caching=True
            )
            
            # Create model server
            if self.instance_creator:
                model_server = self.instance_creator(server_config)
            else:
                # Mock server for demo
                model_server = None
            
            # Create deployment instance
            instance = DeploymentInstance(
                instance_id=instance_id,
                server_config=server_config,
                model_server=model_server,
                endpoint=f"http://localhost:{self.base_port}"
            )
            
            # Start server if it exists
            if model_server:
                await model_server.start()
                
                # Register model
                model_version = self.model_registry.get_model_version(
                    config.model_name, config.model_version
                )
                if model_version:
                    # In a real implementation, load the actual model
                    # For now, we'll use a mock
                    pass
            
            logger.info(f"Created instance {instance_id} for deployment {config.deployment_id}")
            return instance
            
        except Exception as e:
            logger.error(f"Failed to create instance {instance_id}: {e}")
            return None
    
    async def _wait_for_instances_healthy(self, 
                                        instances: List[DeploymentInstance], 
                                        config: DeploymentConfig) -> bool:
        """Wait for instances to become healthy."""
        timeout = config.deployment_timeout
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            healthy_count = 0
            for instance in instances:
                if await self._check_instance_health(instance, config):
                    healthy_count += 1
            
            if healthy_count >= len(instances) - config.max_unhealthy_instances:
                return True
            
            await asyncio.sleep(config.health_check_interval)
        
        logger.error(f"Timeout waiting for instances to become healthy")
        return False
    
    async def _wait_for_instance_healthy(self, 
                                       instance: DeploymentInstance, 
                                       config: DeploymentConfig) -> bool:
        """Wait for a single instance to become healthy."""
        timeout = config.deployment_timeout
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if await self._check_instance_health(instance, config):
                return True
            await asyncio.sleep(config.health_check_interval)
        
        return False
    
    async def _check_instance_health(self, 
                                   instance: DeploymentInstance, 
                                   config: DeploymentConfig) -> bool:
        """Check health of a deployment instance."""
        try:
            # Mock health check - in reality, this would check the actual server
            await asyncio.sleep(0.01)  # Simulate health check delay
            
            # Simulate health check result
            instance.is_healthy = True  # Mock: assume healthy
            instance.last_health_check = datetime.now(timezone.utc)
            
            return instance.is_healthy
            
        except Exception as e:
            logger.error(f"Health check failed for instance {instance.instance_id}: {e}")
            instance.is_healthy = False
            return False
    
    async def _evaluate_canary_performance(self, 
                                         canary_instances: List[DeploymentInstance], 
                                         config: DeploymentConfig) -> bool:
        """Evaluate canary deployment performance."""
        # Mock canary evaluation - in reality, this would analyze metrics
        # For demo purposes, we'll assume canary performs well 80% of the time
        
        import random
        return random.random() > 0.2  # 80% success rate
    
    async def _switch_traffic_to_instances(self, 
                                         instances: List[DeploymentInstance], 
                                         config: DeploymentConfig) -> None:
        """Switch traffic to new instances."""
        # Remove old instances from load balancer
        if config.deployment_id in self.active_deployments:
            old_instances = self.active_deployments[config.deployment_id]
            for instance_id in old_instances.keys():
                self.load_balancer.remove_server(instance_id)
        
        # Add new instances to load balancer
        for instance in instances:
            self.load_balancer.add_server(
                instance.instance_id,
                instance.endpoint or f"http://localhost:{self.base_port}"
            )
    
    async def _cleanup_instances(self, instances: List[DeploymentInstance]) -> None:
        """Clean up deployment instances."""
        for instance in instances:
            await self._cleanup_single_instance(instance)
    
    async def _cleanup_single_instance(self, instance: DeploymentInstance) -> None:
        """Clean up a single deployment instance."""
        try:
            # Remove from load balancer
            self.load_balancer.remove_server(instance.instance_id)
            
            # Stop server
            if instance.model_server:
                await instance.model_server.stop()
            
            # Destroy instance
            if self.instance_destroyer:
                self.instance_destroyer(instance.instance_id)
            
            logger.info(f"Cleaned up instance {instance.instance_id}")
            
        except Exception as e:
            logger.error(f"Error cleaning up instance {instance.instance_id}: {e}")
    
    async def _cleanup_deployment(self, deployment_id: str) -> None:
        """Clean up a deployment."""
        if deployment_id in self.active_deployments:
            instances = list(self.active_deployments[deployment_id].values())
            await self._cleanup_instances(instances)
            del self.active_deployments[deployment_id]
        
        if deployment_id in self.deployment_configs:
            del self.deployment_configs[deployment_id]
        
        if deployment_id in self.deployment_tasks:
            self.deployment_tasks[deployment_id].cancel()
            del self.deployment_tasks[deployment_id]
    
    async def _start_deployment_monitoring(self, config: DeploymentConfig) -> None:
        """Start monitoring for a deployment."""
        task = asyncio.create_task(self._monitor_deployment(config))
        self.deployment_tasks[config.deployment_id] = task
    
    async def _monitor_deployment(self, config: DeploymentConfig) -> None:
        """Monitor deployment health and performance."""
        while config.deployment_id in self.active_deployments:
            try:
                # Check instance health
                instances = list(self.active_deployments[config.deployment_id].values())
                unhealthy_instances = [i for i in instances if not i.is_healthy]
                
                # Replace unhealthy instances
                if len(unhealthy_instances) > config.max_unhealthy_instances:
                    logger.warning(f"Too many unhealthy instances in deployment {config.deployment_id}")
                    
                    # Replace unhealthy instances
                    for instance in unhealthy_instances:
                        new_instance = await self._create_single_instance(config, instance.instance_id)
                        if new_instance:
                            await self._cleanup_single_instance(instance)
                            self.active_deployments[config.deployment_id][new_instance.instance_id] = new_instance
                
                # Check for rollback conditions
                if config.rollback_enabled and await self._should_rollback(config):
                    logger.warning(f"Rollback conditions met for deployment {config.deployment_id}")
                    await self.rollback(config.deployment_id)
                    break
                
                await asyncio.sleep(config.health_check_interval)
                
            except Exception as e:
                logger.error(f"Error monitoring deployment {config.deployment_id}: {e}")
                await asyncio.sleep(config.health_check_interval)
    
    async def _should_rollback(self, config: DeploymentConfig) -> bool:
        """Check if deployment should be rolled back."""
        # Mock rollback evaluation - in reality, this would analyze metrics
        # For demo purposes, we'll randomly trigger rollback 5% of the time
        
        import random
        return random.random() < 0.05  # 5% rollback rate
    
    async def rollback(self, deployment_id: str) -> bool:
        """Rollback a deployment."""
        logger.info(f"Rolling back deployment {deployment_id}")
        
        if deployment_id not in self.deployment_configs:
            logger.error(f"Deployment {deployment_id} not found")
            return False
        
        config = self.deployment_configs[deployment_id]
        
        # Get previous version
        model_versions = self.model_registry.list_model_versions(config.model_name)
        if len(model_versions) < 2:
            logger.error(f"No previous version available for {config.model_name}")
            return False
        
        previous_version = model_versions[1]  # Second most recent version
        
        # Create rollback deployment
        rollback_config = DeploymentConfig(
            deployment_id=f"{deployment_id}-rollback",
            model_name=config.model_name,
            model_version=previous_version.version,
            environment=config.environment,
            strategy=DeploymentStrategy.IMMEDIATE,
            replicas=config.replicas
        )
        
        # Deploy previous version
        success = await self.deploy(rollback_config)
        
        if success:
            # Update original deployment status
            self.model_registry.update_deployment_status(
                deployment_id,
                DeploymentStatus.ROLLING_BACK
            )
            
            logger.info(f"Rollback completed for deployment {deployment_id}")
        
        return success
    
    def get_deployment_status(self, deployment_id: str) -> Optional[Dict[str, Any]]:
        """Get deployment status."""
        if deployment_id not in self.active_deployments:
            return None
        
        instances = self.active_deployments[deployment_id]
        healthy_instances = sum(1 for i in instances.values() if i.is_healthy)
        
        return {
            'deployment_id': deployment_id,
            'total_instances': len(instances),
            'healthy_instances': healthy_instances,
            'unhealthy_instances': len(instances) - healthy_instances,
            'instances': {iid: instance.to_dict() for iid, instance in instances.items()}
        }
    
    def list_deployments(self) -> List[str]:
        """List active deployments."""
        return list(self.active_deployments.keys())
