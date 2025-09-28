"""
SLA monitoring system for ML observability.
Provides Service Level Agreement monitoring and violation detection.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SLAStatus(Enum):
    """SLA status levels."""
    GREEN = "green"      # Within SLA
    YELLOW = "yellow"    # Approaching SLA limit
    RED = "red"          # SLA violation


@dataclass
class SLAViolation:
    """Container for SLA violation information."""
    violation_id: str
    sla_id: str
    metric_name: str
    threshold_value: float
    actual_value: float
    violation_time: datetime
    severity: SLAStatus
    duration_seconds: float
    resolved_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'violation_id': self.violation_id,
            'sla_id': self.sla_id,
            'metric_name': self.metric_name,
            'threshold_value': self.threshold_value,
            'actual_value': self.actual_value,
            'violation_time': self.violation_time.isoformat(),
            'severity': self.severity.value,
            'duration_seconds': self.duration_seconds,
            'resolved_time': self.resolved_time.isoformat() if self.resolved_time else None,
            'metadata': self.metadata
        }


@dataclass
class SLAConfig:
    """Container for SLA configuration."""
    sla_id: str
    name: str
    description: str
    metric_name: str
    threshold_value: float
    threshold_operator: str  # "gt", "gte", "lt", "lte", "eq", "ne"
    evaluation_window_minutes: int = 60
    warning_threshold: Optional[float] = None
    warning_operator: Optional[str] = None
    enabled: bool = True
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'sla_id': self.sla_id,
            'name': self.name,
            'description': self.description,
            'metric_name': self.metric_name,
            'threshold_value': self.threshold_value,
            'threshold_operator': self.threshold_operator,
            'evaluation_window_minutes': self.evaluation_window_minutes,
            'warning_threshold': self.warning_threshold,
            'warning_operator': self.warning_operator,
            'enabled': self.enabled,
            'tags': self.tags,
            'created_at': self.created_at.isoformat()
        }


class SLAMonitor:
    """
    SLA monitor for ML observability.
    """
    
    def __init__(self):
        self.sla_configs: Dict[str, SLAConfig] = {}
        self.active_violations: Dict[str, SLAViolation] = {}
        self.violation_history: List[SLAViolation] = []
        self.metric_values: Dict[str, List[Dict[str, Any]]] = {}
        
        logger.info("Initialized SLA monitor")
    
    def add_sla_config(self, config: SLAConfig) -> None:
        """Add an SLA configuration."""
        self.sla_configs[config.sla_id] = config
        logger.info(f"Added SLA config: {config.name}")
    
    def remove_sla_config(self, sla_id: str) -> bool:
        """Remove an SLA configuration."""
        if sla_id in self.sla_configs:
            del self.sla_configs[sla_id]
            logger.info(f"Removed SLA config: {sla_id}")
            return True
        return False
    
    def update_sla_config(self, sla_id: str, updates: Dict[str, Any]) -> bool:
        """Update an SLA configuration."""
        if sla_id not in self.sla_configs:
            return False
        
        config = self.sla_configs[sla_id]
        
        # Update fields
        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        logger.info(f"Updated SLA config: {sla_id}")
        return True
    
    def record_metric_value(self, 
                           metric_name: str, 
                           value: float, 
                           timestamp: Optional[datetime] = None) -> None:
        """Record a metric value for SLA evaluation."""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        metric_data = {
            'value': value,
            'timestamp': timestamp
        }
        
        if metric_name not in self.metric_values:
            self.metric_values[metric_name] = []
        
        self.metric_values[metric_name].append(metric_data)
        
        # Keep only recent values (last 24 hours)
        cutoff_time = timestamp - timedelta(hours=24)
        self.metric_values[metric_name] = [
            data for data in self.metric_values[metric_name]
            if data['timestamp'] > cutoff_time
        ]
    
    def evaluate_slas(self) -> List[SLAViolation]:
        """Evaluate all SLA configurations and return new violations."""
        new_violations = []
        current_time = datetime.now(timezone.utc)
        
        for sla_id, config in self.sla_configs.items():
            if not config.enabled:
                continue
            
            # Get metric values for evaluation window
            metric_data = self._get_metric_data_for_window(
                config.metric_name,
                config.evaluation_window_minutes,
                current_time
            )
            
            if not metric_data:
                continue
            
            # Calculate aggregated value (e.g., average, max, min)
            aggregated_value = self._calculate_aggregated_value(metric_data)
            
            # Check for violations
            violation = self._check_sla_violation(config, aggregated_value, current_time)
            if violation:
                new_violations.append(violation)
        
        return new_violations
    
    def _get_metric_data_for_window(self, 
                                   metric_name: str, 
                                   window_minutes: int,
                                   current_time: datetime) -> List[Dict[str, Any]]:
        """Get metric data within the evaluation window."""
        if metric_name not in self.metric_values:
            return []
        
        cutoff_time = current_time - timedelta(minutes=window_minutes)
        
        return [
            data for data in self.metric_values[metric_name]
            if data['timestamp'] >= cutoff_time
        ]
    
    def _calculate_aggregated_value(self, metric_data: List[Dict[str, Any]]) -> float:
        """Calculate aggregated value from metric data."""
        if not metric_data:
            return 0.0
        
        values = [data['value'] for data in metric_data]
        
        # Use average as default aggregation
        return sum(values) / len(values)
    
    def _check_sla_violation(self, 
                           config: SLAConfig, 
                           actual_value: float,
                           current_time: datetime) -> Optional[SLAViolation]:
        """Check if an SLA is violated."""
        # Check main threshold
        is_violated = self._compare_values(actual_value, config.threshold_value, config.threshold_operator)
        
        if is_violated:
            # Check if there's already an active violation
            existing_violation = self._get_active_violation(config.sla_id)
            
            if existing_violation:
                # Update existing violation
                existing_violation.duration_seconds = (current_time - existing_violation.violation_time).total_seconds()
                existing_violation.actual_value = actual_value
                return None  # No new violation
            else:
                # Create new violation
                violation = SLAViolation(
                    violation_id=f"violation-{int(current_time.timestamp())}",
                    sla_id=config.sla_id,
                    metric_name=config.metric_name,
                    threshold_value=config.threshold_value,
                    actual_value=actual_value,
                    violation_time=current_time,
                    severity=SLAStatus.RED,
                    duration_seconds=0.0,
                    metadata={
                        'threshold_operator': config.threshold_operator,
                        'evaluation_window_minutes': config.evaluation_window_minutes
                    }
                )
                
                self.active_violations[config.sla_id] = violation
                self.violation_history.append(violation)
                
                return violation
        else:
            # Check if there was an active violation that should be resolved
            existing_violation = self._get_active_violation(config.sla_id)
            if existing_violation:
                existing_violation.resolved_time = current_time
                existing_violation.duration_seconds = (current_time - existing_violation.violation_time).total_seconds()
                del self.active_violations[config.sla_id]
                
                logger.info(f"Resolved SLA violation: {existing_violation.violation_id}")
            
            return None
    
    def _compare_values(self, actual_value: float, threshold_value: float, operator: str) -> bool:
        """Compare values based on operator."""
        if operator == "gt":
            return actual_value > threshold_value
        elif operator == "gte":
            return actual_value >= threshold_value
        elif operator == "lt":
            return actual_value < threshold_value
        elif operator == "lte":
            return actual_value <= threshold_value
        elif operator == "eq":
            return actual_value == threshold_value
        elif operator == "ne":
            return actual_value != threshold_value
        else:
            logger.warning(f"Unknown operator: {operator}")
            return False
    
    def _get_active_violation(self, sla_id: str) -> Optional[SLAViolation]:
        """Get active violation for an SLA."""
        return self.active_violations.get(sla_id)
    
    def get_active_violations(self) -> List[SLAViolation]:
        """Get all active violations."""
        return list(self.active_violations.values())
    
    def get_violation_history(self, 
                            sla_id: Optional[str] = None,
                            limit: int = 100) -> List[SLAViolation]:
        """Get violation history with optional filtering."""
        violations = self.violation_history.copy()
        
        if sla_id:
            violations = [v for v in violations if v.sla_id == sla_id]
        
        return sorted(violations, key=lambda v: v.violation_time, reverse=True)[:limit]
    
    def get_sla_status(self, sla_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of an SLA."""
        if sla_id not in self.sla_configs:
            return None
        
        config = self.sla_configs[sla_id]
        
        # Get current metric value
        metric_data = self._get_metric_data_for_window(
            config.metric_name,
            config.evaluation_window_minutes,
            datetime.now(timezone.utc)
        )
        
        if not metric_data:
            return {
                'sla_id': sla_id,
                'status': 'no_data',
                'message': 'No metric data available'
            }
        
        current_value = self._calculate_aggregated_value(metric_data)
        is_violated = self._compare_values(current_value, config.threshold_value, config.threshold_operator)
        
        # Check warning threshold if configured
        warning_status = None
        if config.warning_threshold and config.warning_operator:
            is_warning = self._compare_values(current_value, config.warning_threshold, config.warning_operator)
            if is_warning:
                warning_status = "warning"
        
        # Determine status
        if is_violated:
            status = SLAStatus.RED.value
        elif warning_status == "warning":
            status = SLAStatus.YELLOW.value
        else:
            status = SLAStatus.GREEN.value
        
        return {
            'sla_id': sla_id,
            'name': config.name,
            'status': status,
            'current_value': current_value,
            'threshold_value': config.threshold_value,
            'threshold_operator': config.threshold_operator,
            'warning_threshold': config.warning_threshold,
            'evaluation_window_minutes': config.evaluation_window_minutes,
            'is_violated': is_violated,
            'has_active_violation': sla_id in self.active_violations,
            'last_evaluated': datetime.now(timezone.utc).isoformat()
        }
    
    def get_all_sla_status(self) -> List[Dict[str, Any]]:
        """Get status of all SLA configurations."""
        statuses = []
        
        for sla_id in self.sla_configs.keys():
            status = self.get_sla_status(sla_id)
            if status:
                statuses.append(status)
        
        return statuses
    
    def get_sla_statistics(self) -> Dict[str, Any]:
        """Get SLA monitoring statistics."""
        total_slas = len(self.sla_configs)
        enabled_slas = sum(1 for config in self.sla_configs.values() if config.enabled)
        active_violations = len(self.active_violations)
        total_violations = len(self.violation_history)
        
        # Calculate violation rates
        violation_rate = 0.0
        if total_violations > 0:
            resolved_violations = sum(1 for v in self.violation_history if v.resolved_time)
            violation_rate = resolved_violations / total_violations if total_violations > 0 else 0.0
        
        # Group violations by severity
        severity_counts = {}
        for violation in self.violation_history:
            severity = violation.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        return {
            'total_slas': total_slas,
            'enabled_slas': enabled_slas,
            'active_violations': active_violations,
            'total_violations': total_violations,
            'violation_rate': violation_rate,
            'severity_distribution': severity_counts,
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
    
    def resolve_violation(self, violation_id: str, resolved_by: str = "system") -> bool:
        """Manually resolve a violation."""
        # Find violation in history
        for violation in self.violation_history:
            if violation.violation_id == violation_id and not violation.resolved_time:
                violation.resolved_time = datetime.now(timezone.utc)
                violation.duration_seconds = (violation.resolved_time - violation.violation_time).total_seconds()
                
                # Remove from active violations if present
                if violation.sla_id in self.active_violations:
                    del self.active_violations[violation.sla_id]
                
                logger.info(f"Manually resolved violation {violation_id} by {resolved_by}")
                return True
        
        return False
