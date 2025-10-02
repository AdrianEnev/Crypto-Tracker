"""
Intelligence System Monitoring

Integrates monitoring and observability with the intelligence system
to track performance, accuracy, and system health.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
import json
from pathlib import Path

from ..ml.monitoring import ModelPerformanceMonitor, MetricsCollector, ConceptDriftDetector
from ..intelligence.models import TradingDecision
from ..intelligence.orchestrator import IntelligenceOrchestrator


@dataclass
class IntelligenceMetrics:
    """Intelligence system performance metrics."""
    timestamp: datetime
    total_decisions: int
    successful_decisions: int
    failed_decisions: int
    avg_decision_time: float
    avg_confidence: float
    tier_distribution: Dict[str, int]
    action_distribution: Dict[str, int]
    error_rate: float
    system_health: str


@dataclass
class DecisionMetrics:
    """Individual decision performance metrics."""
    decision_id: str
    timestamp: datetime
    coin_id: str
    action: str
    confidence: float
    tier_reached: int
    decision_time: float
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class IntelligenceMonitor:
    """
    Monitors the intelligence system performance and health.
    
    Features:
    - Real-time decision tracking
    - Performance metrics collection
    - System health monitoring
    - Alert generation
    - Historical analysis
    - Integration with ML monitoring
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Monitoring configuration
        self.metrics_retention_days = config.get('metrics_retention_days', 30)
        self.alert_thresholds = config.get('alert_thresholds', {})
        self.enable_real_time = config.get('enable_real_time', True)
        self.enable_historical = config.get('enable_historical', True)
        
        # Data storage
        self.decisions: List[DecisionMetrics] = []
        self.metrics_history: List[IntelligenceMetrics] = []
        self.alerts: List[Dict[str, Any]] = []
        
        # Performance tracking
        self.decision_times: List[float] = []
        self.confidence_scores: List[float] = []
        self.error_counts: Dict[str, int] = {}
        
        # ML monitoring integration
        self.ml_monitor = None
        self.metrics_collector = None
        self.drift_detector = None
        
        # Monitoring tasks
        self._monitoring_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.stats = {
            'total_decisions': 0,
            'successful_decisions': 0,
            'failed_decisions': 0,
            'avg_decision_time': 0.0,
            'avg_confidence': 0.0,
            'error_rate': 0.0,
            'system_health': 'healthy'
        }
    
    async def initialize(self):
        """Initialize the intelligence monitor."""
        try:
            # Initialize ML monitoring components
            if self.config.get('enable_ml_monitoring', True):
                self.ml_monitor = ModelPerformanceMonitor('intelligence_system')
                self.metrics_collector = MetricsCollector()
                self.drift_detector = ConceptDriftDetector('intelligence_system')
                
                self.logger.info("ML monitoring components initialized")
            
            # Start monitoring tasks
            if self.enable_real_time:
                self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            
            if self.enable_historical:
                self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            self.logger.info("Intelligence monitor initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize intelligence monitor: {e}")
            raise
    
    async def close(self):
        """Close the intelligence monitor."""
        try:
            # Cancel monitoring tasks
            if self._monitoring_task:
                self._monitoring_task.cancel()
                try:
                    await self._monitoring_task
                except asyncio.CancelledError:
                    pass
            
            if self._cleanup_task:
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass
            
            self.logger.info("Intelligence monitor closed")
            
        except Exception as e:
            self.logger.error(f"Error closing intelligence monitor: {e}")
    
    async def track_decision(
        self, 
        decision: TradingDecision, 
        decision_time: float,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """Track a trading decision."""
        try:
            # Create decision metrics
            coin_id = decision.metadata.get('coin_id', 'unknown') if decision.metadata else 'unknown'
            decision_metrics = DecisionMetrics(
                decision_id=f"{decision.timestamp.isoformat()}_{coin_id}",
                timestamp=decision.timestamp,
                coin_id=coin_id,
                action=decision.action,
                confidence=decision.confidence,
                tier_reached=decision.tier_reached,
                decision_time=decision_time,
                success=success,
                error_message=error_message,
                metadata=decision.metadata or {}
            )
            
            # Store decision
            self.decisions.append(decision_metrics)
            
            # Update performance tracking
            self.decision_times.append(decision_time)
            self.confidence_scores.append(decision.confidence)
            
            if not success:
                self.error_counts[error_message or 'unknown'] = self.error_counts.get(error_message or 'unknown', 0) + 1
            
            # Update statistics
            self._update_stats()
            
            # Check for alerts
            await self._check_alerts(decision_metrics)
            
            # ML monitoring integration
            if self.ml_monitor:
                await self._update_ml_monitoring(decision_metrics)
            
        except Exception as e:
            self.logger.error(f"Failed to track decision: {e}")
    
    def _update_stats(self):
        """Update monitoring statistics."""
        try:
            # Basic statistics
            self.stats['total_decisions'] = len(self.decisions)
            self.stats['successful_decisions'] = sum(1 for d in self.decisions if d.success)
            self.stats['failed_decisions'] = sum(1 for d in self.decisions if not d.success)
            
            # Performance statistics
            if self.decision_times:
                self.stats['avg_decision_time'] = sum(self.decision_times) / len(self.decision_times)
            
            if self.confidence_scores:
                self.stats['avg_confidence'] = sum(self.confidence_scores) / len(self.confidence_scores)
            
            # Error rate
            if self.stats['total_decisions'] > 0:
                self.stats['error_rate'] = self.stats['failed_decisions'] / self.stats['total_decisions']
            
            # System health
            self.stats['system_health'] = self._calculate_system_health()
            
        except Exception as e:
            self.logger.error(f"Failed to update stats: {e}")
    
    def _calculate_system_health(self) -> str:
        """Calculate overall system health."""
        try:
            # Health criteria
            error_rate = self.stats['error_rate']
            avg_decision_time = self.stats['avg_decision_time']
            avg_confidence = self.stats['avg_confidence']
            
            # Health thresholds
            error_threshold = self.alert_thresholds.get('error_rate', 0.1)
            time_threshold = self.alert_thresholds.get('decision_time', 5.0)
            confidence_threshold = self.alert_thresholds.get('confidence', 0.3)
            
            # Determine health status
            if error_rate > error_threshold or avg_decision_time > time_threshold or avg_confidence < confidence_threshold:
                return 'unhealthy'
            elif error_rate > error_threshold * 0.5 or avg_decision_time > time_threshold * 0.7:
                return 'degraded'
            else:
                return 'healthy'
                
        except Exception as e:
            self.logger.error(f"Failed to calculate system health: {e}")
            return 'unknown'
    
    async def _check_alerts(self, decision_metrics: DecisionMetrics):
        """Check for alert conditions."""
        try:
            # High error rate alert
            if self.stats['error_rate'] > self.alert_thresholds.get('error_rate', 0.1):
                await self._create_alert(
                    'high_error_rate',
                    f"Error rate is {self.stats['error_rate']:.2%}",
                    'warning'
                )
            
            # Slow decision time alert
            if decision_metrics.decision_time > self.alert_thresholds.get('decision_time', 5.0):
                await self._create_alert(
                    'slow_decision',
                    f"Decision took {decision_metrics.decision_time:.2f}s",
                    'warning'
                )
            
            # Low confidence alert
            if decision_metrics.confidence < self.alert_thresholds.get('confidence', 0.3):
                await self._create_alert(
                    'low_confidence',
                    f"Decision confidence is {decision_metrics.confidence:.2f}",
                    'info'
                )
            
            # System health alert
            if self.stats['system_health'] == 'unhealthy':
                await self._create_alert(
                    'system_unhealthy',
                    "System health is unhealthy",
                    'critical'
                )
            
        except Exception as e:
            self.logger.error(f"Failed to check alerts: {e}")
    
    async def _create_alert(self, alert_type: str, message: str, severity: str):
        """Create an alert."""
        try:
            alert = {
                'id': f"{alert_type}_{datetime.now().isoformat()}",
                'type': alert_type,
                'message': message,
                'severity': severity,
                'timestamp': datetime.now(timezone.utc),
                'resolved': False
            }
            
            self.alerts.append(alert)
            
            # Log alert
            if severity == 'critical':
                self.logger.critical(f"ALERT: {message}")
            elif severity == 'warning':
                self.logger.warning(f"ALERT: {message}")
            else:
                self.logger.info(f"ALERT: {message}")
            
        except Exception as e:
            self.logger.error(f"Failed to create alert: {e}")
    
    async def _update_ml_monitoring(self, decision_metrics: DecisionMetrics):
        """Update ML monitoring with decision data."""
        try:
            if not self.ml_monitor:
                return
            
            # Create performance metrics for ML monitoring
            ml_metrics = {
                'timestamp': decision_metrics.timestamp,
                'model_name': 'intelligence_system',
                'accuracy': 1.0 if decision_metrics.success else 0.0,
                'precision': decision_metrics.confidence,
                'recall': decision_metrics.confidence,
                'f1_score': decision_metrics.confidence,
                'latency_ms': decision_metrics.decision_time * 1000,
                'throughput_per_sec': 1.0 / max(decision_metrics.decision_time, 0.001),
                'memory_usage_mb': 0.0,  # Would need actual memory monitoring
                'cpu_usage_percent': 0.0  # Would need actual CPU monitoring
            }
            
            # Update ML monitor
            await self.ml_monitor.record_metrics(ml_metrics)
            
        except Exception as e:
            self.logger.error(f"Failed to update ML monitoring: {e}")
    
    async def _monitoring_loop(self):
        """Background monitoring loop."""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                
                # Collect system metrics
                await self._collect_system_metrics()
                
                # Check for drift
                if self.drift_detector:
                    await self._check_drift()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
    
    async def _collect_system_metrics(self):
        """Collect system metrics."""
        try:
            if not self.metrics_collector:
                return
            
            # Get system metrics
            system_metrics = self.metrics_collector.get_system_metrics()
            trading_metrics = self.metrics_collector.get_trading_metrics()
            
            # Create intelligence metrics
            intelligence_metrics = IntelligenceMetrics(
                timestamp=datetime.now(timezone.utc),
                total_decisions=self.stats['total_decisions'],
                successful_decisions=self.stats['successful_decisions'],
                failed_decisions=self.stats['failed_decisions'],
                avg_decision_time=self.stats['avg_decision_time'],
                avg_confidence=self.stats['avg_confidence'],
                tier_distribution=self._get_tier_distribution(),
                action_distribution=self._get_action_distribution(),
                error_rate=self.stats['error_rate'],
                system_health=self.stats['system_health']
            )
            
            # Store metrics
            self.metrics_history.append(intelligence_metrics)
            
        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")
    
    def _get_tier_distribution(self) -> Dict[str, int]:
        """Get distribution of tiers reached."""
        distribution = {}
        for decision in self.decisions:
            tier = f"tier_{decision.tier_reached}"
            distribution[tier] = distribution.get(tier, 0) + 1
        return distribution
    
    def _get_action_distribution(self) -> Dict[str, int]:
        """Get distribution of actions taken."""
        distribution = {}
        for decision in self.decisions:
            action = decision.action
            distribution[action] = distribution.get(action, 0) + 1
        return distribution
    
    async def _check_drift(self):
        """Check for concept drift in decisions."""
        try:
            if len(self.decisions) < 100:  # Need sufficient data
                return
            
            # Get recent decisions (last 100)
            recent_decisions = self.decisions[-100:]
            
            # Calculate drift metrics
            recent_confidence = [d.confidence for d in recent_decisions]
            recent_success_rate = sum(1 for d in recent_decisions if d.success) / len(recent_decisions)
            
            # Compare with historical baseline
            if len(self.decisions) >= 200:
                baseline_decisions = self.decisions[-200:-100]
                baseline_confidence = [d.confidence for d in baseline_decisions]
                baseline_success_rate = sum(1 for d in baseline_decisions if d.success) / len(baseline_decisions)
                
                # Check for significant drift
                confidence_drift = abs(sum(recent_confidence) / len(recent_confidence) - 
                                     sum(baseline_confidence) / len(baseline_confidence))
                success_drift = abs(recent_success_rate - baseline_success_rate)
                
                if confidence_drift > 0.2 or success_drift > 0.1:
                    await self._create_alert(
                        'concept_drift',
                        f"Concept drift detected: confidence={confidence_drift:.2f}, success={success_drift:.2f}",
                        'warning'
                    )
            
        except Exception as e:
            self.logger.error(f"Failed to check drift: {e}")
    
    async def _cleanup_loop(self):
        """Background cleanup loop."""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                # Clean up old data
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.metrics_retention_days)
                
                # Remove old decisions
                self.decisions = [d for d in self.decisions if d.timestamp > cutoff_date]
                
                # Remove old metrics
                self.metrics_history = [m for m in self.metrics_history if m.timestamp > cutoff_date]
                
                # Remove resolved alerts
                self.alerts = [a for a in self.alerts if not a.get('resolved', False)]
                
                self.logger.info(f"Cleaned up data older than {cutoff_date}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Cleanup loop error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        return {
            'stats': self.stats.copy(),
            'total_decisions': len(self.decisions),
            'total_metrics': len(self.metrics_history),
            'total_alerts': len(self.alerts),
            'active_alerts': len([a for a in self.alerts if not a.get('resolved', False)]),
            'error_counts': self.error_counts.copy(),
            'tier_distribution': self._get_tier_distribution(),
            'action_distribution': self._get_action_distribution()
        }
    
    def get_recent_decisions(self, limit: int = 100) -> List[DecisionMetrics]:
        """Get recent decisions."""
        return self.decisions[-limit:] if self.decisions else []
    
    def get_recent_metrics(self, limit: int = 100) -> List[IntelligenceMetrics]:
        """Get recent metrics."""
        return self.metrics_history[-limit:] if self.metrics_history else []
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get active alerts."""
        return [a for a in self.alerts if not a.get('resolved', False)]
    
    async def resolve_alert(self, alert_id: str):
        """Resolve an alert."""
        for alert in self.alerts:
            if alert['id'] == alert_id:
                alert['resolved'] = True
                alert['resolved_at'] = datetime.now(timezone.utc)
                break
