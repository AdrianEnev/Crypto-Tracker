"""
Audit Trail system for ML operations.
Provides comprehensive audit logging and compliance auditing capabilities.
"""

import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AuditEvent:
    """Container for audit event information."""
    
    def __init__(self,
                 event_id: str,
                 event_type: str,
                 user_id: str,
                 action: str,
                 resource: str,
                 resource_id: Optional[str] = None,
                 timestamp: Optional[datetime] = None,
                 ip_address: Optional[str] = None,
                 user_agent: Optional[str] = None,
                 success: bool = True,
                 details: Optional[Dict[str, Any]] = None):
        self.event_id = event_id
        self.event_type = event_type
        self.user_id = user_id
        self.action = action
        self.resource = resource
        self.resource_id = resource_id
        self.timestamp = timestamp or datetime.now(timezone.utc)
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.success = success
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'user_id': self.user_id,
            'action': self.action,
            'resource': self.resource,
            'resource_id': self.resource_id,
            'timestamp': self.timestamp.isoformat(),
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'success': self.success,
            'details': self.details
        }


@dataclass
class AuditLog:
    """Container for audit log information."""
    log_id: str
    events: List[AuditEvent]
    created_at: datetime
    retention_period_days: int = 2555  # 7 years default
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'log_id': self.log_id,
            'events': [event.to_dict() for event in self.events],
            'created_at': self.created_at.isoformat(),
            'retention_period_days': self.retention_period_days
        }


@dataclass
class ComplianceAudit:
    """Container for compliance audit information."""
    audit_id: str
    audit_type: str
    framework: str
    scope: List[str]
    start_date: datetime
    end_date: Optional[datetime] = None
    status: str = "in_progress"  # "in_progress", "completed", "failed"
    findings: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    auditor: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'audit_id': self.audit_id,
            'audit_type': self.audit_type,
            'framework': self.framework,
            'scope': self.scope,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'status': self.status,
            'findings': self.findings,
            'recommendations': self.recommendations,
            'auditor': self.auditor,
            'metadata': self.metadata
        }


class AuditTrail:
    """
    Audit trail system for ML operations.
    """
    
    def __init__(self):
        self.audit_events: Dict[str, AuditEvent] = {}
        self.audit_logs: Dict[str, AuditLog] = {}
        self.compliance_audits: Dict[str, ComplianceAudit] = {}
        
        logger.info("Initialized audit trail system")
    
    def log_event(self,
                  event_type: str,
                  user_id: str,
                  action: str,
                  resource: str,
                  resource_id: Optional[str] = None,
                  ip_address: Optional[str] = None,
                  user_agent: Optional[str] = None,
                  success: bool = True,
                  details: Optional[Dict[str, Any]] = None) -> AuditEvent:
        """Log an audit event."""
        
        event = AuditEvent(
            event_id=f"audit-event-{int(time.time())}-{uuid.uuid4().hex[:8]}",
            event_type=event_type,
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            details=details
        )
        
        self.audit_events[event.event_id] = event
        
        logger.info(f"Audit event logged: {action} on {resource} by {user_id}")
        return event
    
    def log_data_access(self,
                       user_id: str,
                       dataset_name: str,
                       operation: str,
                       ip_address: Optional[str] = None,
                       success: bool = True,
                       record_count: Optional[int] = None) -> AuditEvent:
        """Log data access event."""
        details = {}
        if record_count is not None:
            details['record_count'] = record_count
        
        return self.log_event(
            event_type="data_access",
            user_id=user_id,
            action=operation,
            resource="dataset",
            resource_id=dataset_name,
            ip_address=ip_address,
            success=success,
            details=details
        )
    
    def log_model_operation(self,
                           user_id: str,
                           model_name: str,
                           model_version: str,
                           operation: str,
                           ip_address: Optional[str] = None,
                           success: bool = True,
                           inference_count: Optional[int] = None) -> AuditEvent:
        """Log model operation event."""
        details = {}
        if inference_count is not None:
            details['inference_count'] = inference_count
        
        return self.log_event(
            event_type="model_operation",
            user_id=user_id,
            action=operation,
            resource="model",
            resource_id=f"{model_name}:{model_version}",
            ip_address=ip_address,
            success=success,
            details=details
        )
    
    def log_deployment_event(self,
                            user_id: str,
                            deployment_id: str,
                            action: str,
                            environment: str,
                            ip_address: Optional[str] = None,
                            success: bool = True) -> AuditEvent:
        """Log deployment event."""
        return self.log_event(
            event_type="deployment",
            user_id=user_id,
            action=action,
            resource="deployment",
            resource_id=deployment_id,
            ip_address=ip_address,
            success=success,
            details={"environment": environment}
        )
    
    def log_security_event(self,
                          user_id: str,
                          event_type: str,
                          action: str,
                          ip_address: Optional[str] = None,
                          success: bool = True,
                          threat_level: Optional[str] = None) -> AuditEvent:
        """Log security event."""
        details = {}
        if threat_level:
            details['threat_level'] = threat_level
        
        return self.log_event(
            event_type=f"security_{event_type}",
            user_id=user_id,
            action=action,
            resource="security",
            ip_address=ip_address,
            success=success,
            details=details
        )
    
    def create_audit_log(self, events: List[str], retention_period_days: int = 2555) -> AuditLog:
        """Create an audit log from a list of event IDs."""
        audit_events = []
        for event_id in events:
            if event_id in self.audit_events:
                audit_events.append(self.audit_events[event_id])
        
        audit_log = AuditLog(
            log_id=f"audit-log-{int(time.time())}-{uuid.uuid4().hex[:8]}",
            events=audit_events,
            created_at=datetime.now(timezone.utc),
            retention_period_days=retention_period_days
        )
        
        self.audit_logs[audit_log.log_id] = audit_log
        
        logger.info(f"Created audit log with {len(audit_events)} events")
        return audit_log
    
    def start_compliance_audit(self,
                              audit_type: str,
                              framework: str,
                              scope: List[str],
                              auditor: Optional[str] = None) -> ComplianceAudit:
        """Start a compliance audit."""
        audit = ComplianceAudit(
            audit_id=f"compliance-audit-{int(time.time())}-{uuid.uuid4().hex[:8]}",
            audit_type=audit_type,
            framework=framework,
            scope=scope,
            start_date=datetime.now(timezone.utc),
            auditor=auditor
        )
        
        self.compliance_audits[audit.audit_id] = audit
        
        logger.info(f"Started compliance audit: {audit_type} for {framework}")
        return audit
    
    def add_audit_finding(self,
                         audit_id: str,
                         finding_type: str,
                         severity: str,
                         description: str,
                         recommendation: str,
                         evidence: List[str] = None) -> bool:
        """Add a finding to a compliance audit."""
        if audit_id not in self.compliance_audits:
            return False
        
        audit = self.compliance_audits[audit_id]
        
        finding = {
            'finding_id': f"finding-{int(time.time())}-{uuid.uuid4().hex[:8]}",
            'finding_type': finding_type,
            'severity': severity,
            'description': description,
            'recommendation': recommendation,
            'evidence': evidence or [],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        audit.findings.append(finding)
        audit.recommendations.append(recommendation)
        
        logger.info(f"Added audit finding: {finding_type} - {severity}")
        return True
    
    def complete_compliance_audit(self, audit_id: str, auditor: Optional[str] = None) -> bool:
        """Complete a compliance audit."""
        if audit_id not in self.compliance_audits:
            return False
        
        audit = self.compliance_audits[audit_id]
        audit.status = "completed"
        audit.end_date = datetime.now(timezone.utc)
        if auditor:
            audit.auditor = auditor
        
        logger.info(f"Completed compliance audit: {audit_id}")
        return True
    
    def query_audit_events(self,
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None,
                          user_id: Optional[str] = None,
                          event_type: Optional[str] = None,
                          resource: Optional[str] = None,
                          success_only: bool = False) -> List[AuditEvent]:
        """Query audit events with filters."""
        events = list(self.audit_events.values())
        
        if start_date:
            events = [e for e in events if e.timestamp >= start_date]
        
        if end_date:
            events = [e for e in events if e.timestamp <= end_date]
        
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if resource:
            events = [e for e in events if e.resource == resource]
        
        if success_only:
            events = [e for e in events if e.success]
        
        return sorted(events, key=lambda e: e.timestamp, reverse=True)
    
    def get_user_activity_summary(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get user activity summary for the specified period."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        user_events = self.query_audit_events(
            start_date=cutoff_date,
            user_id=user_id
        )
        
        # Activity statistics
        total_actions = len(user_events)
        successful_actions = len([e for e in user_events if e.success])
        failed_actions = total_actions - successful_actions
        
        # Resource access summary
        resource_access = {}
        for event in user_events:
            resource = event.resource
            if resource not in resource_access:
                resource_access[resource] = {'count': 0, 'success': 0, 'failed': 0}
            
            resource_access[resource]['count'] += 1
            if event.success:
                resource_access[resource]['success'] += 1
            else:
                resource_access[resource]['failed'] += 1
        
        # Action type summary
        action_types = {}
        for event in user_events:
            action = event.action
            action_types[action] = action_types.get(action, 0) + 1
        
        return {
            'user_id': user_id,
            'period_days': days,
            'total_actions': total_actions,
            'successful_actions': successful_actions,
            'failed_actions': failed_actions,
            'success_rate': successful_actions / total_actions if total_actions > 0 else 0,
            'resource_access': resource_access,
            'action_types': action_types,
            'last_activity': user_events[0].timestamp.isoformat() if user_events else None
        }
    
    def get_audit_statistics(self) -> Dict[str, Any]:
        """Get audit trail statistics."""
        total_events = len(self.audit_events)
        successful_events = len([e for e in self.audit_events.values() if e.success])
        failed_events = total_events - successful_events
        
        # Event type distribution
        event_type_counts = {}
        for event in self.audit_events.values():
            event_type_counts[event.event_type] = event_type_counts.get(event.event_type, 0) + 1
        
        # Resource access distribution
        resource_counts = {}
        for event in self.audit_events.values():
            resource_counts[event.resource] = resource_counts.get(event.resource, 0) + 1
        
        # User activity distribution
        user_counts = {}
        for event in self.audit_events.values():
            user_counts[event.user_id] = user_counts.get(event.user_id, 0) + 1
        
        return {
            'total_events': total_events,
            'successful_events': successful_events,
            'failed_events': failed_events,
            'success_rate': successful_events / total_events if total_events > 0 else 0,
            'event_type_distribution': event_type_counts,
            'resource_access_distribution': resource_counts,
            'user_activity_distribution': dict(sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            'total_audit_logs': len(self.audit_logs),
            'total_compliance_audits': len(self.compliance_audits),
            'active_audits': len([a for a in self.compliance_audits.values() if a.status == "in_progress"]),
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
