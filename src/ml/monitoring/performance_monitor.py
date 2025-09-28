"""
Model Performance Monitoring for ML trading systems.
Tracks model accuracy, latency, and performance degradation over time.
"""

import time
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from collections import deque
import logging

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Container for model performance metrics."""
    timestamp: datetime
    model_name: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    latency_ms: float
    throughput_per_sec: float
    memory_usage_mb: float
    cpu_usage_percent: float
    prediction_count: int
    error_count: int
    error_rate: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'model_name': self.model_name,
            'accuracy': self.accuracy,
            'precision': self.precision,
            'recall': self.recall,
            'f1_score': self.f1_score,
            'latency_ms': self.latency_ms,
            'throughput_per_sec': self.throughput_per_sec,
            'memory_usage_mb': self.memory_usage_mb,
            'cpu_usage_percent': self.cpu_usage_percent,
            'prediction_count': self.prediction_count,
            'error_count': self.error_count,
            'error_rate': self.error_rate
        }


class ModelPerformanceMonitor:
    """
    Monitors model performance in real-time and detects degradation.
    """
    
    def __init__(self, 
                 model_name: str,
                 window_size: int = 1000,
                 alert_thresholds: Optional[Dict[str, float]] = None,
                 enable_alerts: bool = True):
        """
        Initialize performance monitor.
        
        Args:
            model_name: Name of the model being monitored
            window_size: Number of recent predictions to keep in memory
            alert_thresholds: Thresholds for performance alerts
            enable_alerts: Whether to enable alert generation
        """
        self.model_name = model_name
        self.window_size = window_size
        self.enable_alerts = enable_alerts
        
        # Default alert thresholds
        self.alert_thresholds = alert_thresholds or {
            'accuracy_drop': 0.05,  # 5% drop in accuracy
            'latency_increase': 2.0,  # 2x increase in latency
            'error_rate_threshold': 0.1,  # 10% error rate
            'memory_increase': 1.5,  # 50% increase in memory usage
            'cpu_threshold': 80.0  # 80% CPU usage
        }
        
        # Performance tracking
        self.performance_history: deque = deque(maxlen=window_size)
        self.prediction_times: deque = deque(maxlen=window_size)
        self.error_count = 0
        self.total_predictions = 0
        self.start_time = datetime.now(timezone.utc)
        
        # Baseline metrics (established during initial monitoring period)
        self.baseline_metrics: Optional[PerformanceMetrics] = None
        self.baseline_established = False
        self.baseline_samples_needed = 100  # Minimum samples for baseline
        
        # Alert tracking
        self.active_alerts: List[Dict[str, Any]] = []
        self.alert_history: deque = deque(maxlen=100)
        
        logger.info(f"Initialized performance monitor for model: {model_name}")
    
    def record_prediction(self, 
                         prediction: Any,
                         actual: Optional[Any] = None,
                         latency_ms: Optional[float] = None,
                         error: Optional[Exception] = None) -> None:
        """
        Record a single prediction for performance tracking.
        
        Args:
            prediction: Model prediction
            actual: Actual value (if available for accuracy calculation)
            latency_ms: Prediction latency in milliseconds
            error: Exception if prediction failed
        """
        self.total_predictions += 1
        
        if error is not None:
            self.error_count += 1
            logger.warning(f"Prediction error recorded for {self.model_name}: {error}")
        
        if latency_ms is not None:
            self.prediction_times.append(latency_ms)
        
        # Calculate current performance metrics
        current_metrics = self._calculate_current_metrics(prediction, actual, latency_ms, error)
        
        # Store metrics
        self.performance_history.append(current_metrics)
        
        # Check for performance degradation
        if self.enable_alerts:
            self._check_performance_alerts(current_metrics)
    
    def _calculate_current_metrics(self, 
                                  prediction: Any,
                                  actual: Optional[Any],
                                  latency_ms: Optional[float],
                                  error: Optional[Exception]) -> PerformanceMetrics:
        """Calculate current performance metrics."""
        now = datetime.now(timezone.utc)
        
        # Calculate accuracy metrics if actual values are available
        accuracy = precision = recall = f1_score = 0.0
        
        if actual is not None and len(self.performance_history) > 0:
            # Simple accuracy calculation for binary classification
            if isinstance(prediction, (int, float, bool)) and isinstance(actual, (int, float, bool)):
                correct = int(prediction == actual)
                accuracy = correct
                precision = recall = f1_score = correct
            # For regression, calculate RMSE-based accuracy
            elif isinstance(prediction, (int, float)) and isinstance(actual, (int, float)):
                error_ratio = abs(prediction - actual) / (abs(actual) + 1e-8)
                accuracy = max(0, 1 - error_ratio)
                precision = recall = f1_score = accuracy
        
        # Calculate latency metrics
        if latency_ms is not None:
            avg_latency = latency_ms
        elif self.prediction_times:
            avg_latency = np.mean(list(self.prediction_times))
        else:
            avg_latency = 0.0
        
        # Calculate throughput
        if len(self.prediction_times) > 1:
            time_span = (now - self.start_time).total_seconds()
            throughput = self.total_predictions / max(time_span, 1.0)
        else:
            throughput = 0.0
        
        # System resource usage (mock values for now)
        memory_usage = self._get_memory_usage()
        cpu_usage = self._get_cpu_usage()
        
        return PerformanceMetrics(
            timestamp=now,
            model_name=self.model_name,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            latency_ms=avg_latency,
            throughput_per_sec=throughput,
            memory_usage_mb=memory_usage,
            cpu_usage_percent=cpu_usage,
            prediction_count=self.total_predictions,
            error_count=self.error_count,
            error_rate=self.error_count / max(self.total_predictions, 1)
        )
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage (mock implementation)."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # MB
        except ImportError:
            return 0.0  # Mock value
    
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage (mock implementation)."""
        try:
            import psutil
            return psutil.cpu_percent()
        except ImportError:
            return 0.0  # Mock value
    
    def _check_performance_alerts(self, current_metrics: PerformanceMetrics) -> None:
        """Check for performance degradation and generate alerts."""
        if not self.baseline_established:
            if len(self.performance_history) >= self.baseline_samples_needed:
                self._establish_baseline()
            return
        
        alerts = []
        
        # Check accuracy degradation
        accuracy_drop = self.baseline_metrics.accuracy - current_metrics.accuracy
        if accuracy_drop > self.alert_thresholds['accuracy_drop']:
            alerts.append({
                'type': 'accuracy_degradation',
                'severity': 'high',
                'message': f"Accuracy dropped by {accuracy_drop:.3f} from baseline",
                'current': current_metrics.accuracy,
                'baseline': self.baseline_metrics.accuracy,
                'threshold': self.alert_thresholds['accuracy_drop']
            })
        
        # Check latency increase
        if self.baseline_metrics.latency_ms > 0:
            latency_ratio = current_metrics.latency_ms / self.baseline_metrics.latency_ms
            if latency_ratio > self.alert_thresholds['latency_increase']:
                alerts.append({
                    'type': 'latency_increase',
                    'severity': 'medium',
                    'message': f"Latency increased by {latency_ratio:.2f}x from baseline",
                    'current': current_metrics.latency_ms,
                    'baseline': self.baseline_metrics.latency_ms,
                    'threshold': self.alert_thresholds['latency_increase']
                })
        
        # Check error rate
        if current_metrics.error_rate > self.alert_thresholds['error_rate_threshold']:
            alerts.append({
                'type': 'high_error_rate',
                'severity': 'critical',
                'message': f"Error rate {current_metrics.error_rate:.3f} exceeds threshold",
                'current': current_metrics.error_rate,
                'threshold': self.alert_thresholds['error_rate_threshold']
            })
        
        # Check memory usage
        if self.baseline_metrics.memory_usage_mb > 0:
            memory_ratio = current_metrics.memory_usage_mb / self.baseline_metrics.memory_usage_mb
            if memory_ratio > self.alert_thresholds['memory_increase']:
                alerts.append({
                    'type': 'memory_increase',
                    'severity': 'medium',
                    'message': f"Memory usage increased by {memory_ratio:.2f}x",
                    'current': current_metrics.memory_usage_mb,
                    'baseline': self.baseline_metrics.memory_usage_mb,
                    'threshold': self.alert_thresholds['memory_increase']
                })
        
        # Check CPU usage
        if current_metrics.cpu_usage_percent > self.alert_thresholds['cpu_threshold']:
            alerts.append({
                'type': 'high_cpu_usage',
                'severity': 'medium',
                'message': f"CPU usage {current_metrics.cpu_usage_percent:.1f}% exceeds threshold",
                'current': current_metrics.cpu_usage_percent,
                'threshold': self.alert_thresholds['cpu_threshold']
            })
        
        # Store and log alerts
        for alert in alerts:
            alert['timestamp'] = current_metrics.timestamp.isoformat()
            alert['model_name'] = self.model_name
            self.active_alerts.append(alert)
            self.alert_history.append(alert)
            
            logger.warning(f"Performance alert for {self.model_name}: {alert['message']}")
    
    def _establish_baseline(self) -> None:
        """Establish baseline performance metrics."""
        if len(self.performance_history) < self.baseline_samples_needed:
            return
        
        # Calculate average metrics from recent history
        recent_metrics = list(self.performance_history)[-self.baseline_samples_needed:]
        
        self.baseline_metrics = PerformanceMetrics(
            timestamp=datetime.now(timezone.utc),
            model_name=self.model_name,
            accuracy=np.mean([m.accuracy for m in recent_metrics]),
            precision=np.mean([m.precision for m in recent_metrics]),
            recall=np.mean([m.recall for m in recent_metrics]),
            f1_score=np.mean([m.f1_score for m in recent_metrics]),
            latency_ms=np.mean([m.latency_ms for m in recent_metrics]),
            throughput_per_sec=np.mean([m.throughput_per_sec for m in recent_metrics]),
            memory_usage_mb=np.mean([m.memory_usage_mb for m in recent_metrics]),
            cpu_usage_percent=np.mean([m.cpu_usage_percent for m in recent_metrics]),
            prediction_count=len(recent_metrics),
            error_count=sum([m.error_count for m in recent_metrics]),
            error_rate=np.mean([m.error_rate for m in recent_metrics])
        )
        
        self.baseline_established = True
        logger.info(f"Baseline established for {self.model_name}: accuracy={self.baseline_metrics.accuracy:.3f}")
    
    def get_current_metrics(self) -> Optional[PerformanceMetrics]:
        """Get the most recent performance metrics."""
        if not self.performance_history:
            return None
        return self.performance_history[-1]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get a summary of current performance status."""
        current = self.get_current_metrics()
        
        summary = {
            'model_name': self.model_name,
            'total_predictions': self.total_predictions,
            'error_count': self.error_count,
            'error_rate': self.error_count / max(self.total_predictions, 1),
            'active_alerts': len(self.active_alerts),
            'baseline_established': self.baseline_established,
            'uptime_hours': (datetime.now(timezone.utc) - self.start_time).total_seconds() / 3600
        }
        
        if current:
            summary.update({
                'current_accuracy': current.accuracy,
                'current_latency_ms': current.latency_ms,
                'current_throughput_per_sec': current.throughput_per_sec,
                'current_memory_mb': current.memory_usage_mb,
                'current_cpu_percent': current.cpu_usage_percent
            })
        
        if self.baseline_metrics:
            summary['baseline_accuracy'] = self.baseline_metrics.accuracy
            summary['baseline_latency_ms'] = self.baseline_metrics.latency_ms
        
        return summary
    
    def get_alerts(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get performance alerts."""
        if active_only:
            return self.active_alerts.copy()
        return list(self.alert_history)
    
    def clear_alerts(self) -> None:
        """Clear active alerts."""
        self.active_alerts.clear()
        logger.info(f"Cleared {len(self.active_alerts)} alerts for {self.model_name}")
    
    def export_metrics(self, format: str = 'json') -> str:
        """Export performance metrics in specified format."""
        if format == 'json':
            import json
            metrics_data = [m.to_dict() for m in self.performance_history]
            return json.dumps(metrics_data, indent=2)
        elif format == 'csv':
            if not self.performance_history:
                return ""
            
            df = pd.DataFrame([m.to_dict() for m in self.performance_history])
            return df.to_csv(index=False)
        else:
            raise ValueError(f"Unsupported format: {format}")
