"""
Auto Scaler for dynamic scaling of model server instances.
Provides intelligent scaling based on metrics and policies.
"""

import time
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import statistics

logger = logging.getLogger(__name__)


class ScalingPolicy(Enum):
    """Scaling policy types."""
    CPU_BASED = "cpu_based"
    MEMORY_BASED = "memory_based"
    REQUEST_RATE_BASED = "request_rate_based"
    RESPONSE_TIME_BASED = "response_time_based"
    QUEUE_SIZE_BASED = "queue_size_based"
    CUSTOM_METRIC_BASED = "custom_metric_based"


class ScalingAction(Enum):
    """Scaling actions."""
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    NO_ACTION = "no_action"


@dataclass
class ScalingMetrics:
    """Container for scaling metrics."""
    timestamp: datetime
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    request_rate_per_second: float = 0.0
    response_time_ms: float = 0.0
    queue_size: int = 0
    active_connections: int = 0
    error_rate: float = 0.0
    custom_metrics: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'cpu_percent': self.cpu_percent,
            'memory_percent': self.memory_percent,
            'request_rate_per_second': self.request_rate_per_second,
            'response_time_ms': self.response_time_ms,
            'queue_size': self.queue_size,
            'active_connections': self.active_connections,
            'error_rate': self.error_rate,
            'custom_metrics': self.custom_metrics
        }


@dataclass
class ScalingRule:
    """Scaling rule configuration."""
    policy: ScalingPolicy
    metric_name: str
    threshold: float
    comparison_operator: str  # 'gt', 'lt', 'gte', 'lte', 'eq'
    action: ScalingAction
    scale_amount: int = 1
    cooldown_seconds: int = 300  # 5 minutes
    evaluation_periods: int = 3
    min_replicas: int = 1
    max_replicas: int = 10
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'policy': self.policy.value,
            'metric_name': self.metric_name,
            'threshold': self.threshold,
            'comparison_operator': self.comparison_operator,
            'action': self.action.value,
            'scale_amount': self.scale_amount,
            'cooldown_seconds': self.cooldown_seconds,
            'evaluation_periods': self.evaluation_periods,
            'min_replicas': self.min_replicas,
            'max_replicas': self.max_replicas
        }


class AutoScaler:
    """
    Auto scaler for dynamic scaling of model server instances.
    """
    
    def __init__(self, 
                 min_replicas: int = 1,
                 max_replicas: int = 10,
                 initial_replicas: int = 1,
                 metrics_collection_interval: int = 30,
                 scaling_evaluation_interval: int = 60):
        self.min_replicas = min_replicas
        self.max_replicas = max_replicas
        self.current_replicas = initial_replicas
        self.metrics_collection_interval = metrics_collection_interval
        self.scaling_evaluation_interval = scaling_evaluation_interval
        
        # Scaling rules
        self.scaling_rules: List[ScalingRule] = []
        
        # Metrics history
        self.metrics_history: List[ScalingMetrics] = []
        self.max_metrics_history = 100
        
        # Scaling state
        self.last_scaling_action: Optional[ScalingAction] = None
        self.last_scaling_time: Optional[datetime] = None
        self.scaling_cooldowns: Dict[str, datetime] = {}
        
        # Tasks
        self.metrics_task: Optional[asyncio.Task] = None
        self.scaling_task: Optional[asyncio.Task] = None
        
        # Custom metrics provider
        self.custom_metrics_provider: Optional[Callable[[], Dict[str, float]]] = None
        
        # Scaling callbacks
        self.scale_up_callback: Optional[Callable[[int], bool]] = None
        self.scale_down_callback: Optional[Callable[[int], bool]] = None
        
        logger.info(f"Initialized auto scaler: {initial_replicas} replicas, range [{min_replicas}, {max_replicas}]")
    
    async def start(self) -> None:
        """Start the auto scaler."""
        if self.metrics_task is None:
            self.metrics_task = asyncio.create_task(self._metrics_collection_loop())
        
        if self.scaling_task is None:
            self.scaling_task = asyncio.create_task(self._scaling_evaluation_loop())
        
        logger.info("Auto scaler started")
    
    async def stop(self) -> None:
        """Stop the auto scaler."""
        if self.metrics_task:
            self.metrics_task.cancel()
            await asyncio.gather(self.metrics_task, return_exceptions=True)
            self.metrics_task = None
        
        if self.scaling_task:
            self.scaling_task.cancel()
            await asyncio.gather(self.scaling_task, return_exceptions=True)
            self.scaling_task = None
        
        logger.info("Auto scaler stopped")
    
    def add_scaling_rule(self, rule: ScalingRule) -> None:
        """Add a scaling rule."""
        self.scaling_rules.append(rule)
        logger.info(f"Added scaling rule: {rule.policy.value} {rule.comparison_operator} {rule.threshold}")
    
    def remove_scaling_rule(self, policy: ScalingPolicy, metric_name: str) -> bool:
        """Remove a scaling rule."""
        for i, rule in enumerate(self.scaling_rules):
            if rule.policy == policy and rule.metric_name == metric_name:
                del self.scaling_rules[i]
                logger.info(f"Removed scaling rule: {policy.value} {metric_name}")
                return True
        return False
    
    def set_custom_metrics_provider(self, provider: Callable[[], Dict[str, float]]) -> None:
        """Set custom metrics provider function."""
        self.custom_metrics_provider = provider
        logger.info("Set custom metrics provider")
    
    def set_scaling_callbacks(self, 
                            scale_up_callback: Callable[[int], bool],
                            scale_down_callback: Callable[[int], bool]) -> None:
        """Set scaling callback functions."""
        self.scale_up_callback = scale_up_callback
        self.scale_down_callback = scale_down_callback
        logger.info("Set scaling callbacks")
    
    async def _metrics_collection_loop(self) -> None:
        """Metrics collection loop."""
        while True:
            try:
                metrics = await self._collect_metrics()
                self.metrics_history.append(metrics)
                
                # Keep only recent metrics
                if len(self.metrics_history) > self.max_metrics_history:
                    self.metrics_history = self.metrics_history[-self.max_metrics_history:]
                
                await asyncio.sleep(self.metrics_collection_interval)
                
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                await asyncio.sleep(self.metrics_collection_interval)
    
    async def _scaling_evaluation_loop(self) -> None:
        """Scaling evaluation loop."""
        while True:
            try:
                await self._evaluate_scaling()
                await asyncio.sleep(self.scaling_evaluation_interval)
                
            except Exception as e:
                logger.error(f"Scaling evaluation error: {e}")
                await asyncio.sleep(self.scaling_evaluation_interval)
    
    async def _collect_metrics(self) -> ScalingMetrics:
        """Collect current metrics."""
        # Mock metrics collection - in reality, this would collect from monitoring systems
        
        # Simulate some realistic metrics
        cpu_percent = 20.0 + (time.time() % 100) * 0.5  # Varying CPU usage
        memory_percent = 40.0 + (time.time() % 50) * 0.3  # Varying memory usage
        request_rate = 10.0 + (time.time() % 20) * 2.0  # Varying request rate
        response_time = 50.0 + (time.time() % 100) * 1.0  # Varying response time
        queue_size = int(5 + (time.time() % 10))  # Varying queue size
        active_connections = int(3 + (time.time() % 8))  # Varying connections
        error_rate = max(0, 0.01 + (time.time() % 50) * 0.001)  # Varying error rate
        
        # Collect custom metrics if provider is set
        custom_metrics = {}
        if self.custom_metrics_provider:
            try:
                custom_metrics = self.custom_metrics_provider()
            except Exception as e:
                logger.error(f"Error collecting custom metrics: {e}")
        
        return ScalingMetrics(
            timestamp=datetime.now(timezone.utc),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            request_rate_per_second=request_rate,
            response_time_ms=response_time,
            queue_size=queue_size,
            active_connections=active_connections,
            error_rate=error_rate,
            custom_metrics=custom_metrics
        )
    
    async def _evaluate_scaling(self) -> None:
        """Evaluate scaling based on rules and metrics."""
        if len(self.metrics_history) < 2:
            return  # Need at least 2 metrics for evaluation
        
        # Get recent metrics
        recent_metrics = self.metrics_history[-self.scaling_evaluation_interval:]
        
        for rule in self.scaling_rules:
            if self._is_in_cooldown(rule):
                continue
            
            # Check if rule should trigger
            if self._should_trigger_rule(rule, recent_metrics):
                await self._execute_scaling_action(rule)
    
    def _is_in_cooldown(self, rule: ScalingRule) -> bool:
        """Check if rule is in cooldown period."""
        cooldown_key = f"{rule.policy.value}:{rule.metric_name}"
        
        if cooldown_key not in self.scaling_cooldowns:
            return False
        
        last_action_time = self.scaling_cooldowns[cooldown_key]
        cooldown_duration = timedelta(seconds=rule.cooldown_seconds)
        
        return datetime.now(timezone.utc) - last_action_time < cooldown_duration
    
    def _should_trigger_rule(self, rule: ScalingRule, metrics: List[ScalingMetrics]) -> bool:
        """Check if a scaling rule should trigger."""
        if len(metrics) < rule.evaluation_periods:
            return False
        
        # Get metric values for evaluation periods
        metric_values = []
        for metric in metrics[-rule.evaluation_periods:]:
            value = self._get_metric_value(metric, rule.metric_name)
            if value is not None:
                metric_values.append(value)
        
        if len(metric_values) < rule.evaluation_periods:
            return False
        
        # Check if all evaluation periods meet the condition
        for value in metric_values:
            if not self._compare_metric(value, rule.threshold, rule.comparison_operator):
                return False
        
        return True
    
    def _get_metric_value(self, metrics: ScalingMetrics, metric_name: str) -> Optional[float]:
        """Get metric value from metrics object."""
        if metric_name == 'cpu_percent':
            return metrics.cpu_percent
        elif metric_name == 'memory_percent':
            return metrics.memory_percent
        elif metric_name == 'request_rate_per_second':
            return metrics.request_rate_per_second
        elif metric_name == 'response_time_ms':
            return metrics.response_time_ms
        elif metric_name == 'queue_size':
            return float(metrics.queue_size)
        elif metric_name == 'active_connections':
            return float(metrics.active_connections)
        elif metric_name == 'error_rate':
            return metrics.error_rate
        elif metric_name in metrics.custom_metrics:
            return metrics.custom_metrics[metric_name]
        else:
            return None
    
    def _compare_metric(self, value: float, threshold: float, operator: str) -> bool:
        """Compare metric value with threshold."""
        if operator == 'gt':
            return value > threshold
        elif operator == 'lt':
            return value < threshold
        elif operator == 'gte':
            return value >= threshold
        elif operator == 'lte':
            return value <= threshold
        elif operator == 'eq':
            return abs(value - threshold) < 0.001  # Small tolerance for equality
        else:
            return False
    
    async def _execute_scaling_action(self, rule: ScalingRule) -> None:
        """Execute scaling action."""
        current_replicas = self.current_replicas
        new_replicas = current_replicas
        
        if rule.action == ScalingAction.SCALE_UP:
            new_replicas = min(current_replicas + rule.scale_amount, rule.max_replicas)
            new_replicas = min(new_replicas, self.max_replicas)
        elif rule.action == ScalingAction.SCALE_DOWN:
            new_replicas = max(current_replicas - rule.scale_amount, rule.min_replicas)
            new_replicas = max(new_replicas, self.min_replicas)
        else:
            return  # No action
        
        if new_replicas == current_replicas:
            return  # No change needed
        
        # Execute scaling
        success = False
        if new_replicas > current_replicas and self.scale_up_callback:
            success = self.scale_up_callback(new_replicas - current_replicas)
        elif new_replicas < current_replicas and self.scale_down_callback:
            success = self.scale_down_callback(current_replicas - new_replicas)
        
        if success:
            self.current_replicas = new_replicas
            self.last_scaling_action = rule.action
            self.last_scaling_time = datetime.now(timezone.utc)
            
            # Set cooldown
            cooldown_key = f"{rule.policy.value}:{rule.metric_name}"
            self.scaling_cooldowns[cooldown_key] = datetime.now(timezone.utc)
            
            action_type = "scale up" if new_replicas > current_replicas else "scale down"
            logger.info(f"Executed {action_type}: {current_replicas} -> {new_replicas} replicas "
                       f"(rule: {rule.policy.value} {rule.comparison_operator} {rule.threshold})")
        else:
            logger.error(f"Failed to execute scaling action: {rule.action.value}")
    
    def get_scaling_status(self) -> Dict[str, Any]:
        """Get current scaling status."""
        # Calculate metrics statistics
        recent_metrics = self.metrics_history[-10:] if self.metrics_history else []
        
        metrics_summary = {}
        if recent_metrics:
            metrics_summary = {
                'avg_cpu_percent': statistics.mean([m.cpu_percent for m in recent_metrics]),
                'avg_memory_percent': statistics.mean([m.memory_percent for m in recent_metrics]),
                'avg_request_rate': statistics.mean([m.request_rate_per_second for m in recent_metrics]),
                'avg_response_time': statistics.mean([m.response_time_ms for m in recent_metrics]),
                'avg_queue_size': statistics.mean([m.queue_size for m in recent_metrics]),
                'avg_error_rate': statistics.mean([m.error_rate for m in recent_metrics])
            }
        
        # Check cooldowns
        active_cooldowns = []
        for cooldown_key, cooldown_time in self.scaling_cooldowns.items():
            remaining_seconds = max(0, 300 - (datetime.now(timezone.utc) - cooldown_time).total_seconds())
            if remaining_seconds > 0:
                active_cooldowns.append({
                    'rule': cooldown_key,
                    'remaining_seconds': remaining_seconds
                })
        
        return {
            'current_replicas': self.current_replicas,
            'min_replicas': self.min_replicas,
            'max_replicas': self.max_replicas,
            'last_scaling_action': self.last_scaling_action.value if self.last_scaling_action else None,
            'last_scaling_time': self.last_scaling_time.isoformat() if self.last_scaling_time else None,
            'active_scaling_rules': len(self.scaling_rules),
            'active_cooldowns': len(active_cooldowns),
            'cooldowns': active_cooldowns,
            'metrics_summary': metrics_summary,
            'total_metrics_collected': len(self.metrics_history)
        }
    
    def get_scaling_rules(self) -> List[Dict[str, Any]]:
        """Get all scaling rules."""
        return [rule.to_dict() for rule in self.scaling_rules]
    
    def get_metrics_history(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get metrics history."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        recent_metrics = [
            m for m in self.metrics_history 
            if m.timestamp > cutoff_time
        ]
        return [m.to_dict() for m in recent_metrics]
    
    def manual_scale(self, target_replicas: int) -> bool:
        """Manually scale to target replicas."""
        target_replicas = max(self.min_replicas, min(target_replicas, self.max_replicas))
        
        if target_replicas == self.current_replicas:
            return True
        
        current_replicas = self.current_replicas
        success = False
        
        if target_replicas > current_replicas and self.scale_up_callback:
            success = self.scale_up_callback(target_replicas - current_replicas)
        elif target_replicas < current_replicas and self.scale_down_callback:
            success = self.scale_down_callback(current_replicas - target_replicas)
        
        if success:
            self.current_replicas = target_replicas
            self.last_scaling_action = ScalingAction.SCALE_UP if target_replicas > current_replicas else ScalingAction.SCALE_DOWN
            self.last_scaling_time = datetime.now(timezone.utc)
            logger.info(f"Manual scaling: {current_replicas} -> {target_replicas} replicas")
        
        return success
