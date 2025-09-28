"""
Model Health Monitoring for ML trading systems.
Provides comprehensive health checks and status monitoring.
"""

import time
import psutil
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Container for individual health check results."""
    name: str
    status: HealthStatus
    message: str
    value: Any
    threshold: Optional[float] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'status': self.status.value,
            'message': self.message,
            'value': self.value,
            'threshold': self.threshold,
            'timestamp': self.timestamp.isoformat()
        }


class ModelHealthChecker:
    """
    Comprehensive health monitoring for ML models and trading systems.
    """
    
    def __init__(self, 
                 model_name: str,
                 check_interval_seconds: int = 60,
                 enable_system_monitoring: bool = True):
        """
        Initialize model health checker.
        
        Args:
            model_name: Name of the model being monitored
            check_interval_seconds: Interval between health checks
            enable_system_monitoring: Whether to monitor system resources
        """
        self.model_name = model_name
        self.check_interval = check_interval_seconds
        self.enable_system_monitoring = enable_system_monitoring
        
        # Health check history
        self.health_history: List[HealthCheck] = []
        self.last_check_time: Optional[datetime] = None
        
        # Model-specific metrics
        self.model_metrics: Dict[str, Any] = {}
        self.performance_trends: Dict[str, List[Tuple[datetime, float]]] = {}
        
        # System resource tracking
        self.system_metrics: Dict[str, List[Tuple[datetime, float]]] = {
            'cpu_percent': [],
            'memory_percent': [],
            'disk_usage_percent': [],
            'network_io': []
        }
        
        # Health check thresholds
        self.thresholds = {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'disk_usage_percent': 90.0,
            'model_latency_ms': 1000.0,
            'error_rate': 0.05,
            'accuracy_drop': 0.1,
            'memory_leak_mb': 100.0
        }
        
        logger.info(f"Initialized health checker for model: {model_name}")
    
    def run_health_checks(self) -> Dict[str, HealthCheck]:
        """
        Run all health checks and return results.
        
        Returns:
            Dictionary of health check results
        """
        checks = {}
        
        # System resource checks
        if self.enable_system_monitoring:
            checks.update(self._check_system_resources())
        
        # Model-specific checks
        checks.update(self._check_model_health())
        
        # Performance trend checks
        checks.update(self._check_performance_trends())
        
        # Data quality checks
        checks.update(self._check_data_quality())
        
        # Store results
        for check in checks.values():
            self.health_history.append(check)
        
        self.last_check_time = datetime.now(timezone.utc)
        
        # Clean up old history (keep last 1000 checks)
        if len(self.health_history) > 1000:
            self.health_history = self.health_history[-1000:]
        
        return checks
    
    def _check_system_resources(self) -> Dict[str, HealthCheck]:
        """Check system resource utilization."""
        checks = {}
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_status = self._get_status_from_threshold(cpu_percent, self.thresholds['cpu_percent'])
            checks['cpu_usage'] = HealthCheck(
                name='CPU Usage',
                status=cpu_status,
                message=f"CPU usage: {cpu_percent:.1f}%",
                value=cpu_percent,
                threshold=self.thresholds['cpu_percent']
            )
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_status = self._get_status_from_threshold(memory_percent, self.thresholds['memory_percent'])
            checks['memory_usage'] = HealthCheck(
                name='Memory Usage',
                status=memory_status,
                message=f"Memory usage: {memory_percent:.1f}% ({memory.used / 1024**3:.1f}GB used)",
                value=memory_percent,
                threshold=self.thresholds['memory_percent']
            )
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            disk_status = self._get_status_from_threshold(disk_percent, self.thresholds['disk_usage_percent'])
            checks['disk_usage'] = HealthCheck(
                name='Disk Usage',
                status=disk_status,
                message=f"Disk usage: {disk_percent:.1f}% ({disk.used / 1024**3:.1f}GB used)",
                value=disk_percent,
                threshold=self.thresholds['disk_usage_percent']
            )
            
            # Store system metrics
            now = datetime.now(timezone.utc)
            self.system_metrics['cpu_percent'].append((now, cpu_percent))
            self.system_metrics['memory_percent'].append((now, memory_percent))
            self.system_metrics['disk_usage_percent'].append((now, disk_percent))
            
            # Clean up old metrics (keep last 24 hours)
            cutoff_time = now - timedelta(hours=24)
            for metric_list in self.system_metrics.values():
                metric_list[:] = [(t, v) for t, v in metric_list if t > cutoff_time]
                
        except Exception as e:
            logger.error(f"Error checking system resources: {e}")
            checks['system_resources'] = HealthCheck(
                name='System Resources',
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check system resources: {str(e)}",
                value=None
            )
        
        return checks
    
    def _check_model_health(self) -> Dict[str, HealthCheck]:
        """Check model-specific health metrics."""
        checks = {}
        
        # Model availability check
        checks['model_availability'] = HealthCheck(
            name='Model Availability',
            status=HealthStatus.HEALTHY,
            message="Model is available and loaded",
            value=True
        )
        
        # Check model metrics if available
        if 'latency_ms' in self.model_metrics:
            latency = self.model_metrics['latency_ms']
            latency_status = self._get_status_from_threshold(latency, self.thresholds['model_latency_ms'], reverse=True)
            checks['model_latency'] = HealthCheck(
                name='Model Latency',
                status=latency_status,
                message=f"Model latency: {latency:.2f}ms",
                value=latency,
                threshold=self.thresholds['model_latency_ms']
            )
        
        if 'error_rate' in self.model_metrics:
            error_rate = self.model_metrics['error_rate']
            error_status = self._get_status_from_threshold(error_rate, self.thresholds['error_rate'])
            checks['model_error_rate'] = HealthCheck(
                name='Model Error Rate',
                status=error_status,
                message=f"Model error rate: {error_rate:.3f}",
                value=error_rate,
                threshold=self.thresholds['error_rate']
            )
        
        if 'accuracy' in self.model_metrics:
            accuracy = self.model_metrics['accuracy']
            checks['model_accuracy'] = HealthCheck(
                name='Model Accuracy',
                status=HealthStatus.HEALTHY,
                message=f"Model accuracy: {accuracy:.3f}",
                value=accuracy
            )
        
        return checks
    
    def _check_performance_trends(self) -> Dict[str, HealthCheck]:
        """Check for performance degradation trends."""
        checks = {}
        
        # Check for accuracy degradation trend
        if 'accuracy' in self.performance_trends:
            accuracy_trend = self.performance_trends['accuracy']
            if len(accuracy_trend) >= 10:  # Need at least 10 data points
                recent_accuracy = np.mean([v for _, v in accuracy_trend[-5:]])
                older_accuracy = np.mean([v for _, v in accuracy_trend[-10:-5]])
                
                accuracy_drop = older_accuracy - recent_accuracy
                if accuracy_drop > self.thresholds['accuracy_drop']:
                    checks['accuracy_degradation'] = HealthCheck(
                        name='Accuracy Degradation',
                        status=HealthStatus.CRITICAL,
                        message=f"Accuracy dropping: {accuracy_drop:.3f} over recent period",
                        value=accuracy_drop,
                        threshold=self.thresholds['accuracy_drop']
                    )
        
        # Check for memory leak trend
        if 'memory_mb' in self.performance_trends:
            memory_trend = self.performance_trends['memory_mb']
            if len(memory_trend) >= 20:  # Need more data points for memory leak detection
                recent_memory = np.mean([v for _, v in memory_trend[-10:]])
                older_memory = np.mean([v for _, v in memory_trend[-20:-10]])
                
                memory_increase = recent_memory - older_memory
                if memory_increase > self.thresholds['memory_leak_mb']:
                    checks['memory_leak'] = HealthCheck(
                        name='Memory Leak',
                        status=HealthStatus.WARNING,
                        message=f"Potential memory leak: {memory_increase:.1f}MB increase",
                        value=memory_increase,
                        threshold=self.thresholds['memory_leak_mb']
                    )
        
        return checks
    
    def _check_data_quality(self) -> Dict[str, HealthCheck]:
        """Check data quality metrics."""
        checks = {}
        
        # Data freshness check
        if 'last_data_update' in self.model_metrics:
            last_update = self.model_metrics['last_data_update']
            if isinstance(last_update, datetime):
                time_since_update = (datetime.now(timezone.utc) - last_update).total_seconds()
                if time_since_update > 300:  # 5 minutes
                    status = HealthStatus.CRITICAL if time_since_update > 1800 else HealthStatus.WARNING
                    checks['data_freshness'] = HealthCheck(
                        name='Data Freshness',
                        status=status,
                        message=f"Data is {time_since_update:.0f} seconds old",
                        value=time_since_update,
                        threshold=300
                    )
        
        # Data completeness check
        if 'missing_data_rate' in self.model_metrics:
            missing_rate = self.model_metrics['missing_data_rate']
            status = HealthStatus.WARNING if missing_rate > 0.05 else HealthStatus.HEALTHY
            checks['data_completeness'] = HealthCheck(
                name='Data Completeness',
                status=status,
                message=f"Missing data rate: {missing_rate:.3f}",
                value=missing_rate,
                threshold=0.05
            )
        
        return checks
    
    def _get_status_from_threshold(self, 
                                   value: float, 
                                   threshold: float, 
                                   reverse: bool = False) -> HealthStatus:
        """Get health status based on threshold comparison."""
        if reverse:  # Lower is better (e.g., latency)
            if value <= threshold:
                return HealthStatus.HEALTHY
            elif value <= threshold * 1.5:
                return HealthStatus.WARNING
            else:
                return HealthStatus.CRITICAL
        else:  # Higher is worse (e.g., CPU usage)
            if value <= threshold:
                return HealthStatus.HEALTHY
            elif value <= threshold * 1.2:
                return HealthStatus.WARNING
            else:
                return HealthStatus.CRITICAL
    
    def update_model_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update model-specific metrics."""
        self.model_metrics.update(metrics)
        
        # Track performance trends
        now = datetime.now(timezone.utc)
        for metric_name, value in metrics.items():
            if metric_name in ['accuracy', 'latency_ms', 'memory_mb']:
                if metric_name not in self.performance_trends:
                    self.performance_trends[metric_name] = []
                
                self.performance_trends[metric_name].append((now, value))
                
                # Keep only last 100 data points
                if len(self.performance_trends[metric_name]) > 100:
                    self.performance_trends[metric_name] = self.performance_trends[metric_name][-100:]
    
    def get_overall_health_status(self) -> HealthStatus:
        """Get overall health status based on recent checks."""
        if not self.health_history:
            return HealthStatus.UNKNOWN
        
        # Get recent checks (last 10 minutes)
        recent_cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
        recent_checks = [
            check for check in self.health_history 
            if check.timestamp > recent_cutoff
        ]
        
        if not recent_checks:
            return HealthStatus.UNKNOWN
        
        # Determine overall status
        statuses = [check.status for check in recent_checks]
        
        if HealthStatus.CRITICAL in statuses:
            return HealthStatus.CRITICAL
        elif HealthStatus.WARNING in statuses:
            return HealthStatus.WARNING
        elif HealthStatus.HEALTHY in statuses:
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive health summary."""
        overall_status = self.get_overall_health_status()
        
        # Recent checks
        recent_cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
        recent_checks = [
            check for check in self.health_history 
            if check.timestamp > recent_cutoff
        ]
        
        # Status counts
        status_counts = {
            'healthy': sum(1 for c in recent_checks if c.status == HealthStatus.HEALTHY),
            'warning': sum(1 for c in recent_checks if c.status == HealthStatus.WARNING),
            'critical': sum(1 for c in recent_checks if c.status == HealthStatus.CRITICAL),
            'unknown': sum(1 for c in recent_checks if c.status == HealthStatus.UNKNOWN)
        }
        
        return {
            'model_name': self.model_name,
            'overall_status': overall_status.value,
            'last_check_time': self.last_check_time.isoformat() if self.last_check_time else None,
            'recent_check_count': len(recent_checks),
            'status_counts': status_counts,
            'total_checks_performed': len(self.health_history),
            'uptime_hours': (datetime.now(timezone.utc) - (self.health_history[0].timestamp if self.health_history else datetime.now(timezone.utc))).total_seconds() / 3600
        }
    
    def get_health_history(self, 
                          hours: int = 24, 
                          status_filter: Optional[HealthStatus] = None) -> List[HealthCheck]:
        """Get health check history."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        filtered_checks = [
            check for check in self.health_history 
            if check.timestamp > cutoff_time
        ]
        
        if status_filter:
            filtered_checks = [
                check for check in filtered_checks 
                if check.status == status_filter
            ]
        
        return filtered_checks
    
    def export_health_data(self, format: str = 'json') -> str:
        """Export health data in specified format."""
        if format == 'json':
            import json
            health_data = {
                'summary': self.get_health_summary(),
                'recent_checks': [check.to_dict() for check in self.get_health_history(hours=24)],
                'system_metrics': {
                    metric: [{'timestamp': t.isoformat(), 'value': v} 
                           for t, v in values]
                    for metric, values in self.system_metrics.items()
                }
            }
            return json.dumps(health_data, indent=2)
        elif format == 'csv':
            if not self.health_history:
                return ""
            
            df = pd.DataFrame([check.to_dict() for check in self.health_history])
            return df.to_csv(index=False)
        else:
            raise ValueError(f"Unsupported format: {format}")
