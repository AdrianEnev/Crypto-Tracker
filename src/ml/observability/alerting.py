"""
Alerting system for ML observability.
Provides intelligent alerting with multiple channels and severity levels.
"""

import time
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class AlertChannel(Enum):
    """Alert notification channels."""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"
    PAGERDUTY = "pagerduty"
    LOG = "log"


@dataclass
class AlertRule:
    """Container for alert rule configuration."""
    rule_id: str
    name: str
    description: str
    condition: str  # Expression to evaluate
    severity: AlertSeverity
    channels: List[AlertChannel]
    enabled: bool = True
    cooldown_seconds: int = 300  # 5 minutes
    evaluation_interval: int = 60  # 1 minute
    threshold: Optional[float] = None
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = "system"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'rule_id': self.rule_id,
            'name': self.name,
            'description': self.description,
            'condition': self.condition,
            'severity': self.severity.value,
            'channels': [ch.value for ch in self.channels],
            'enabled': self.enabled,
            'cooldown_seconds': self.cooldown_seconds,
            'evaluation_interval': self.evaluation_interval,
            'threshold': self.threshold,
            'tags': self.tags,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by
        }


@dataclass
class Alert:
    """Container for alert instance."""
    alert_id: str
    rule_id: str
    title: str
    message: str
    severity: AlertSeverity
    status: AlertStatus
    triggered_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    notifications_sent: List[AlertChannel] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'alert_id': self.alert_id,
            'rule_id': self.rule_id,
            'title': self.title,
            'message': self.message,
            'severity': self.severity.value,
            'status': self.status.value,
            'triggered_at': self.triggered_at.isoformat(),
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'acknowledged_by': self.acknowledged_by,
            'resolved_by': self.resolved_by,
            'metadata': self.metadata,
            'notifications_sent': [ch.value for ch in self.notifications_sent]
        }


class AlertManager:
    """
    Alert manager for ML observability.
    """
    
    def __init__(self):
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.channel_configs: Dict[AlertChannel, Dict[str, Any]] = {}
        self.evaluation_tasks: Dict[str, asyncio.Task] = {}
        self.last_evaluations: Dict[str, datetime] = {}
        self.is_running = False
        
        logger.info("Initialized alert manager")
    
    async def start(self) -> None:
        """Start the alert manager."""
        if self.is_running:
            logger.warning("Alert manager is already running")
            return
        
        self.is_running = True
        
        # Start evaluation tasks for all enabled rules
        for rule_id, rule in self.alert_rules.items():
            if rule.enabled:
                await self._start_rule_evaluation(rule)
        
        logger.info("Alert manager started")
    
    async def stop(self) -> None:
        """Stop the alert manager."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Cancel all evaluation tasks
        for task in self.evaluation_tasks.values():
            task.cancel()
        
        await asyncio.gather(*self.evaluation_tasks.values(), return_exceptions=True)
        self.evaluation_tasks.clear()
        
        logger.info("Alert manager stopped")
    
    def add_alert_rule(self, rule: AlertRule) -> None:
        """Add an alert rule."""
        self.alert_rules[rule.rule_id] = rule
        
        # Start evaluation if manager is running and rule is enabled
        if self.is_running and rule.enabled:
            asyncio.create_task(self._start_rule_evaluation(rule))
        
        logger.info(f"Added alert rule: {rule.name}")
    
    def remove_alert_rule(self, rule_id: str) -> bool:
        """Remove an alert rule."""
        if rule_id not in self.alert_rules:
            return False
        
        # Stop evaluation task
        if rule_id in self.evaluation_tasks:
            self.evaluation_tasks[rule_id].cancel()
            del self.evaluation_tasks[rule_id]
        
        del self.alert_rules[rule_id]
        logger.info(f"Removed alert rule: {rule_id}")
        return True
    
    def update_alert_rule(self, rule_id: str, updates: Dict[str, Any]) -> bool:
        """Update an alert rule."""
        if rule_id not in self.alert_rules:
            return False
        
        rule = self.alert_rules[rule_id]
        
        # Update fields
        for key, value in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        
        # Restart evaluation if enabled status changed
        if 'enabled' in updates:
            if updates['enabled'] and rule_id not in self.evaluation_tasks:
                if self.is_running:
                    asyncio.create_task(self._start_rule_evaluation(rule))
            elif not updates['enabled'] and rule_id in self.evaluation_tasks:
                self.evaluation_tasks[rule_id].cancel()
                del self.evaluation_tasks[rule_id]
        
        logger.info(f"Updated alert rule: {rule_id}")
        return True
    
    async def _start_rule_evaluation(self, rule: AlertRule) -> None:
        """Start evaluation task for a rule."""
        if rule.rule_id in self.evaluation_tasks:
            return
        
        async def evaluate_rule():
            while self.is_running and rule.enabled:
                try:
                    await self._evaluate_rule(rule)
                    await asyncio.sleep(rule.evaluation_interval)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error evaluating rule {rule.rule_id}: {e}")
                    await asyncio.sleep(rule.evaluation_interval)
        
        task = asyncio.create_task(evaluate_rule())
        self.evaluation_tasks[rule.rule_id] = task
    
    async def _evaluate_rule(self, rule: AlertRule) -> None:
        """Evaluate a single alert rule."""
        try:
            # Check cooldown
            if rule.rule_id in self.last_evaluations:
                last_eval = self.last_evaluations[rule.rule_id]
                if datetime.now(timezone.utc) - last_eval < timedelta(seconds=rule.cooldown_seconds):
                    return
            
            # Evaluate condition (mock evaluation)
            condition_met = await self._evaluate_condition(rule.condition, rule.threshold)
            
            if condition_met:
                # Check if alert already exists
                existing_alert = self._get_active_alert_for_rule(rule.rule_id)
                
                if existing_alert:
                    # Update existing alert
                    existing_alert.metadata['last_triggered'] = datetime.now(timezone.utc).isoformat()
                else:
                    # Create new alert
                    await self._create_alert(rule)
            
            self.last_evaluations[rule.rule_id] = datetime.now(timezone.utc)
            
        except Exception as e:
            logger.error(f"Error evaluating rule {rule.rule_id}: {e}")
    
    async def _evaluate_condition(self, condition: str, threshold: Optional[float]) -> bool:
        """Evaluate alert condition (mock implementation)."""
        # In a real implementation, this would evaluate actual metrics
        # For demo purposes, we'll simulate some conditions
        
        if "cpu_percent" in condition:
            # Mock CPU usage
            import random
            cpu_usage = random.uniform(20, 90)
            if threshold:
                return cpu_usage > threshold
            return cpu_usage > 80
        
        elif "error_rate" in condition:
            # Mock error rate
            import random
            error_rate = random.uniform(0, 0.1)
            if threshold:
                return error_rate > threshold
            return error_rate > 0.05
        
        elif "response_time" in condition:
            # Mock response time
            import random
            response_time = random.uniform(50, 500)
            if threshold:
                return response_time > threshold
            return response_time > 200
        
        else:
            # Default: random condition
            import random
            return random.random() < 0.1  # 10% chance of triggering
    
    async def _create_alert(self, rule: AlertRule) -> None:
        """Create a new alert."""
        alert_id = f"alert-{int(time.time())}"
        
        alert = Alert(
            alert_id=alert_id,
            rule_id=rule.rule_id,
            title=f"Alert: {rule.name}",
            message=rule.description,
            severity=rule.severity,
            status=AlertStatus.ACTIVE,
            triggered_at=datetime.now(timezone.utc),
            metadata={
                'condition': rule.condition,
                'threshold': rule.threshold,
                'tags': rule.tags
            }
        )
        
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        
        # Send notifications
        await self._send_notifications(alert, rule.channels)
        
        logger.info(f"Created alert: {alert_id}")
    
    def _get_active_alert_for_rule(self, rule_id: str) -> Optional[Alert]:
        """Get active alert for a rule."""
        for alert in self.active_alerts.values():
            if alert.rule_id == rule_id and alert.status == AlertStatus.ACTIVE:
                return alert
        return None
    
    async def _send_notifications(self, alert: Alert, channels: List[AlertChannel]) -> None:
        """Send notifications through specified channels."""
        for channel in channels:
            try:
                await self._send_notification(alert, channel)
                alert.notifications_sent.append(channel)
            except Exception as e:
                logger.error(f"Failed to send notification via {channel.value}: {e}")
    
    async def _send_notification(self, alert: Alert, channel: AlertChannel) -> None:
        """Send notification through a specific channel."""
        if channel == AlertChannel.LOG:
            logger.warning(f"ALERT [{alert.severity.value.upper()}] {alert.title}: {alert.message}")
        
        elif channel == AlertChannel.EMAIL:
            await self._send_email_notification(alert)
        
        elif channel == AlertChannel.WEBHOOK:
            await self._send_webhook_notification(alert)
        
        else:
            logger.info(f"Notification sent via {channel.value}: {alert.title}")
    
    async def _send_email_notification(self, alert: Alert) -> None:
        """Send email notification."""
        if AlertChannel.EMAIL not in self.channel_configs:
            logger.warning("Email channel not configured")
            return
        
        config = self.channel_configs[AlertChannel.EMAIL]
        
        # Mock email sending
        logger.info(f"Email notification sent to {config.get('recipients', 'default')}: {alert.title}")
    
    async def _send_webhook_notification(self, alert: Alert) -> None:
        """Send webhook notification."""
        if AlertChannel.WEBHOOK not in self.channel_configs:
            logger.warning("Webhook channel not configured")
            return
        
        config = self.channel_configs[AlertChannel.WEBHOOK]
        
        # Mock webhook sending
        logger.info(f"Webhook notification sent to {config.get('url', 'default')}: {alert.title}")
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert."""
        if alert_id not in self.active_alerts:
            return False
        
        alert = self.active_alerts[alert_id]
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.acknowledged_by = acknowledged_by
        
        logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
        return True
    
    def resolve_alert(self, alert_id: str, resolved_by: str) -> bool:
        """Resolve an alert."""
        if alert_id not in self.active_alerts:
            return False
        
        alert = self.active_alerts[alert_id]
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.now(timezone.utc)
        alert.resolved_by = resolved_by
        
        # Move to history
        del self.active_alerts[alert_id]
        
        logger.info(f"Alert {alert_id} resolved by {resolved_by}")
        return True
    
    def configure_channel(self, channel: AlertChannel, config: Dict[str, Any]) -> None:
        """Configure a notification channel."""
        self.channel_configs[channel] = config
        logger.info(f"Configured {channel.value} channel")
    
    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """Get active alerts, optionally filtered by severity."""
        alerts = list(self.active_alerts.values())
        
        if severity:
            alerts = [alert for alert in alerts if alert.severity == severity]
        
        return sorted(alerts, key=lambda a: a.triggered_at, reverse=True)
    
    def get_alert_history(self, 
                         limit: int = 100,
                         severity: Optional[AlertSeverity] = None,
                         status: Optional[AlertStatus] = None) -> List[Alert]:
        """Get alert history with optional filtering."""
        alerts = self.alert_history.copy()
        
        if severity:
            alerts = [alert for alert in alerts if alert.severity == severity]
        
        if status:
            alerts = [alert for alert in alerts if alert.status == status]
        
        return sorted(alerts, key=lambda a: a.triggered_at, reverse=True)[:limit]
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics."""
        total_alerts = len(self.alert_history)
        active_alerts = len(self.active_alerts)
        
        severity_counts = {}
        status_counts = {}
        
        for alert in self.alert_history:
            severity = alert.severity.value
            status = alert.status.value
            
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            'total_alerts': total_alerts,
            'active_alerts': active_alerts,
            'resolved_alerts': status_counts.get('resolved', 0),
            'acknowledged_alerts': status_counts.get('acknowledged', 0),
            'severity_distribution': severity_counts,
            'status_distribution': status_counts,
            'total_rules': len(self.alert_rules),
            'enabled_rules': sum(1 for rule in self.alert_rules.values() if rule.enabled)
        }
