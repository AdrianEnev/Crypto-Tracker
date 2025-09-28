"""
Security Monitoring system for ML operations.
Provides security event detection, threat assessment, and incident management.
"""

import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    """Threat severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityEvent:
    """Container for security event information."""
    event_id: str
    event_type: str
    threat_level: ThreatLevel
    description: str
    detected_at: datetime
    source_ip: Optional[str] = None
    user_id: Optional[str] = None
    resource: Optional[str] = None
    status: str = "active"  # "active", "investigating", "contained", "resolved"
    assigned_to: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    evidence: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'threat_level': self.threat_level.value,
            'description': self.description,
            'detected_at': self.detected_at.isoformat(),
            'source_ip': self.source_ip,
            'user_id': self.user_id,
            'resource': self.resource,
            'status': self.status,
            'assigned_to': self.assigned_to,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolved_by': self.resolved_by,
            'evidence': self.evidence,
            'metadata': self.metadata
        }


@dataclass
class SecurityIncident:
    """Container for security incident information."""
    incident_id: str
    title: str
    description: str
    threat_level: ThreatLevel
    events: List[str]  # List of event IDs
    created_at: datetime
    status: str = "open"  # "open", "investigating", "contained", "resolved"
    assigned_to: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    impact_assessment: Optional[str] = None
    remediation_steps: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'incident_id': self.incident_id,
            'title': self.title,
            'description': self.description,
            'threat_level': self.threat_level.value,
            'events': self.events,
            'created_at': self.created_at.isoformat(),
            'status': self.status,
            'assigned_to': self.assigned_to,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolved_by': self.resolved_by,
            'impact_assessment': self.impact_assessment,
            'remediation_steps': self.remediation_steps,
            'metadata': self.metadata
        }


class SecurityMonitor:
    """
    Security monitoring system for ML operations.
    """
    
    def __init__(self):
        self.security_events: Dict[str, SecurityEvent] = {}
        self.incidents: Dict[str, SecurityIncident] = {}
        self.threat_patterns: Dict[str, Dict[str, Any]] = {}
        self.blocked_ips: List[str] = []
        self.blocked_users: List[str] = []
        
        # Initialize default threat patterns
        self._initialize_threat_patterns()
        
        logger.info("Initialized security monitor")
    
    def _initialize_threat_patterns(self) -> None:
        """Initialize default threat detection patterns."""
        self.threat_patterns = {
            "brute_force": {
                "description": "Multiple failed login attempts",
                "threshold": 5,
                "time_window_minutes": 10,
                "threat_level": ThreatLevel.HIGH
            },
            "suspicious_access": {
                "description": "Unusual access patterns",
                "threshold": 3,
                "time_window_minutes": 30,
                "threat_level": ThreatLevel.MEDIUM
            },
            "data_exfiltration": {
                "description": "Large data downloads",
                "threshold": 1000000,  # 1MB
                "time_window_minutes": 60,
                "threat_level": ThreatLevel.CRITICAL
            },
            "model_tampering": {
                "description": "Unauthorized model modifications",
                "threshold": 1,
                "time_window_minutes": 0,
                "threat_level": ThreatLevel.CRITICAL
            }
        }
    
    def detect_security_event(self,
                            event_type: str,
                            description: str,
                            threat_level: ThreatLevel,
                            source_ip: Optional[str] = None,
                            user_id: Optional[str] = None,
                            resource: Optional[str] = None,
                            evidence: List[str] = None,
                            metadata: Optional[Dict[str, Any]] = None) -> SecurityEvent:
        """Detect and record a security event."""
        
        event = SecurityEvent(
            event_id=f"security-event-{int(time.time())}-{uuid.uuid4().hex[:8]}",
            event_type=event_type,
            threat_level=threat_level,
            description=description,
            detected_at=datetime.now(timezone.utc),
            source_ip=source_ip,
            user_id=user_id,
            resource=resource,
            evidence=evidence or [],
            metadata=metadata or {}
        )
        
        self.security_events[event.event_id] = event
        
        # Check if event matches known threat patterns
        self._check_threat_patterns(event)
        
        # Auto-block if critical threat
        if threat_level == ThreatLevel.CRITICAL:
            self._auto_block_threat(event)
        
        logger.warning(f"Security event detected: {event_type} - {threat_level.value}")
        return event
    
    def _check_threat_patterns(self, event: SecurityEvent) -> None:
        """Check if event matches known threat patterns."""
        for pattern_name, pattern_config in self.threat_patterns.items():
            if self._matches_pattern(event, pattern_name, pattern_config):
                self._create_incident_from_pattern(event, pattern_name, pattern_config)
    
    def _matches_pattern(self, event: SecurityEvent, pattern_name: str, pattern_config: Dict[str, Any]) -> bool:
        """Check if event matches a specific threat pattern."""
        if pattern_name == "brute_force":
            return self._check_brute_force_pattern(event, pattern_config)
        elif pattern_name == "suspicious_access":
            return self._check_suspicious_access_pattern(event, pattern_config)
        elif pattern_name == "data_exfiltration":
            return self._check_data_exfiltration_pattern(event, pattern_config)
        elif pattern_name == "model_tampering":
            return self._check_model_tampering_pattern(event, pattern_config)
        
        return False
    
    def _check_brute_force_pattern(self, event: SecurityEvent, pattern_config: Dict[str, Any]) -> bool:
        """Check for brute force attack pattern."""
        if event.event_type != "failed_login":
            return False
        
        # Count failed logins from same IP in time window
        threshold = pattern_config["threshold"]
        time_window = timedelta(minutes=pattern_config["time_window_minutes"])
        cutoff_time = datetime.now(timezone.utc) - time_window
        
        failed_logins = [
            e for e in self.security_events.values()
            if (e.event_type == "failed_login" and
                e.source_ip == event.source_ip and
                e.detected_at >= cutoff_time)
        ]
        
        return len(failed_logins) >= threshold
    
    def _check_suspicious_access_pattern(self, event: SecurityEvent, pattern_config: Dict[str, Any]) -> bool:
        """Check for suspicious access pattern."""
        if event.event_type not in ["unusual_access", "off_hours_access"]:
            return False
        
        # Count suspicious access events from same user
        threshold = pattern_config["threshold"]
        time_window = timedelta(minutes=pattern_config["time_window_minutes"])
        cutoff_time = datetime.now(timezone.utc) - time_window
        
        suspicious_events = [
            e for e in self.security_events.values()
            if (e.event_type in ["unusual_access", "off_hours_access"] and
                e.user_id == event.user_id and
                e.detected_at >= cutoff_time)
        ]
        
        return len(suspicious_events) >= threshold
    
    def _check_data_exfiltration_pattern(self, event: SecurityEvent, pattern_config: Dict[str, Any]) -> bool:
        """Check for data exfiltration pattern."""
        if event.event_type != "large_data_access":
            return False
        
        # Check if data access exceeds threshold
        data_size = event.metadata.get("data_size", 0)
        threshold = pattern_config["threshold"]
        
        return data_size >= threshold
    
    def _check_model_tampering_pattern(self, event: SecurityEvent, pattern_config: Dict[str, Any]) -> bool:
        """Check for model tampering pattern."""
        return event.event_type == "model_tampering"
    
    def _create_incident_from_pattern(self, event: SecurityEvent, pattern_name: str, pattern_config: Dict[str, Any]) -> None:
        """Create security incident from detected threat pattern."""
        incident = SecurityIncident(
            incident_id=f"incident-{int(time.time())}-{uuid.uuid4().hex[:8]}",
            title=f"{pattern_name.replace('_', ' ').title()} Detected",
            description=pattern_config["description"],
            threat_level=pattern_config["threat_level"],
            events=[event.event_id],
            created_at=datetime.now(timezone.utc),
            status="open"
        )
        
        self.incidents[incident.incident_id] = incident
        logger.warning(f"Security incident created: {incident.title}")
    
    def _auto_block_threat(self, event: SecurityEvent) -> None:
        """Automatically block critical threats."""
        if event.source_ip and event.source_ip not in self.blocked_ips:
            self.blocked_ips.append(event.source_ip)
            logger.warning(f"Auto-blocked IP: {event.source_ip}")
        
        if event.user_id and event.user_id not in self.blocked_users:
            self.blocked_users.append(event.user_id)
            logger.warning(f"Auto-blocked user: {event.user_id}")
    
    def create_incident(self,
                       title: str,
                       description: str,
                       threat_level: ThreatLevel,
                       events: List[str],
                       assigned_to: Optional[str] = None) -> SecurityIncident:
        """Create a security incident."""
        incident = SecurityIncident(
            incident_id=f"incident-{int(time.time())}-{uuid.uuid4().hex[:8]}",
            title=title,
            description=description,
            threat_level=threat_level,
            events=events,
            created_at=datetime.now(timezone.utc),
            status="open",
            assigned_to=assigned_to
        )
        
        self.incidents[incident.incident_id] = incident
        logger.info(f"Created security incident: {title}")
        return incident
    
    def assign_incident(self, incident_id: str, assigned_to: str) -> bool:
        """Assign incident to security team member."""
        if incident_id not in self.incidents:
            return False
        
        incident = self.incidents[incident_id]
        incident.assigned_to = assigned_to
        incident.status = "investigating"
        
        logger.info(f"Incident {incident_id} assigned to {assigned_to}")
        return True
    
    def resolve_incident(self, incident_id: str, resolved_by: str, remediation_steps: List[str] = None) -> bool:
        """Resolve a security incident."""
        if incident_id not in self.incidents:
            return False
        
        incident = self.incidents[incident_id]
        incident.status = "resolved"
        incident.resolved_at = datetime.now(timezone.utc)
        incident.resolved_by = resolved_by
        
        if remediation_steps:
            incident.remediation_steps = remediation_steps
        
        logger.info(f"Incident {incident_id} resolved by {resolved_by}")
        return True
    
    def get_active_events(self, threat_level: Optional[ThreatLevel] = None) -> List[SecurityEvent]:
        """Get active security events."""
        events = [e for e in self.security_events.values() if e.status == "active"]
        
        if threat_level:
            events = [e for e in events if e.threat_level == threat_level]
        
        return sorted(events, key=lambda e: e.detected_at, reverse=True)
    
    def get_open_incidents(self) -> List[SecurityIncident]:
        """Get open security incidents."""
        return [
            incident for incident in self.incidents.values()
            if incident.status in ["open", "investigating", "contained"]
        ]
    
    def get_security_statistics(self) -> Dict[str, Any]:
        """Get security monitoring statistics."""
        total_events = len(self.security_events)
        active_events = len([e for e in self.security_events.values() if e.status == "active"])
        
        # Threat level distribution
        threat_counts = {}
        for level in ThreatLevel:
            threat_counts[level.value] = len([
                e for e in self.security_events.values()
                if e.threat_level == level and e.status == "active"
            ])
        
        # Event type distribution
        event_type_counts = {}
        for event in self.security_events.values():
            if event.status == "active":
                event_type_counts[event.event_type] = event_type_counts.get(event.event_type, 0) + 1
        
        return {
            'total_events': total_events,
            'active_events': active_events,
            'resolved_events': len([e for e in self.security_events.values() if e.status == "resolved"]),
            'threat_level_distribution': threat_counts,
            'event_type_distribution': event_type_counts,
            'total_incidents': len(self.incidents),
            'open_incidents': len([i for i in self.incidents.values() if i.status in ["open", "investigating", "contained"]]),
            'blocked_ips': len(self.blocked_ips),
            'blocked_users': len(self.blocked_users),
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
    
    def unblock_ip(self, ip_address: str) -> bool:
        """Unblock a previously blocked IP address."""
        if ip_address in self.blocked_ips:
            self.blocked_ips.remove(ip_address)
            logger.info(f"Unblocked IP: {ip_address}")
            return True
        return False
    
    def unblock_user(self, user_id: str) -> bool:
        """Unblock a previously blocked user."""
        if user_id in self.blocked_users:
            self.blocked_users.remove(user_id)
            logger.info(f"Unblocked user: {user_id}")
            return True
        return False
