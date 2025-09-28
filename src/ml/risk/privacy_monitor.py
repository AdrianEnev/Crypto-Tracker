"""
Privacy Monitoring system for ML operations.
Provides privacy violation detection, data classification, and consent management.
"""

import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DataClassification(Enum):
    """Data classification levels."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    PII = "pii"  # Personally Identifiable Information
    PHI = "phi"  # Protected Health Information
    FINANCIAL = "financial"


@dataclass
class PrivacyViolation:
    """Container for privacy violation information."""
    violation_id: str
    violation_type: str
    description: str
    detected_at: datetime
    severity: str  # "low", "medium", "high", "critical"
    data_type: Optional[str] = None
    user_id: Optional[str] = None
    data_subject: Optional[str] = None
    status: str = "open"  # "open", "investigating", "resolved"
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    remediation_steps: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'violation_id': self.violation_id,
            'violation_type': self.violation_type,
            'description': self.description,
            'detected_at': self.detected_at.isoformat(),
            'severity': self.severity,
            'data_type': self.data_type,
            'user_id': self.user_id,
            'data_subject': self.data_subject,
            'status': self.status,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolved_by': self.resolved_by,
            'remediation_steps': self.remediation_steps,
            'metadata': self.metadata
        }


@dataclass
class ConsentManager:
    """Container for consent management information."""
    consent_id: str
    data_subject_id: str
    purpose: str
    data_types: List[str]
    granted_at: datetime
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    status: str = "active"  # "active", "expired", "revoked"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'consent_id': self.consent_id,
            'data_subject_id': self.data_subject_id,
            'purpose': self.purpose,
            'data_types': self.data_types,
            'granted_at': self.granted_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'revoked_at': self.revoked_at.isoformat() if self.revoked_at else None,
            'status': self.status,
            'metadata': self.metadata
        }


class PrivacyMonitor:
    """
    Privacy monitoring system for ML operations.
    """
    
    def __init__(self):
        self.privacy_violations: Dict[str, PrivacyViolation] = {}
        self.consent_records: Dict[str, ConsentManager] = {}
        self.data_classifications: Dict[str, DataClassification] = {}
        self.pii_patterns: List[str] = [
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
            r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',  # Credit card
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # Phone number
            r'\b[A-Z]{2}\d{6}\b'  # Driver's license (example pattern)
        ]
        
        logger.info("Initialized privacy monitor")
    
    def classify_data(self, data_name: str, data_content: str = None, classification: DataClassification = None) -> DataClassification:
        """Classify data based on content or explicit classification."""
        if classification:
            self.data_classifications[data_name] = classification
            return classification
        
        # Auto-classify based on content
        if data_content:
            if self._contains_pii(data_content):
                self.data_classifications[data_name] = DataClassification.PII
                return DataClassification.PII
            elif self._contains_financial_data(data_content):
                self.data_classifications[data_name] = DataClassification.FINANCIAL
                return DataClassification.FINANCIAL
            elif self._contains_health_data(data_content):
                self.data_classifications[data_name] = DataClassification.PHI
                return DataClassification.PHI
            else:
                self.data_classifications[data_name] = DataClassification.INTERNAL
                return DataClassification.INTERNAL
        
        # Default classification
        self.data_classifications[data_name] = DataClassification.INTERNAL
        return DataClassification.INTERNAL
    
    def _contains_pii(self, content: str) -> bool:
        """Check if content contains PII patterns."""
        import re
        for pattern in self.pii_patterns:
            if re.search(pattern, content):
                return True
        return False
    
    def _contains_financial_data(self, content: str) -> bool:
        """Check if content contains financial data."""
        financial_keywords = ['account', 'balance', 'transaction', 'payment', 'credit', 'debit']
        return any(keyword in content.lower() for keyword in financial_keywords)
    
    def _contains_health_data(self, content: str) -> bool:
        """Check if content contains health data."""
        health_keywords = ['medical', 'health', 'diagnosis', 'treatment', 'prescription', 'patient']
        return any(keyword in content.lower() for keyword in health_keywords)
    
    def detect_privacy_violation(self,
                                violation_type: str,
                                description: str,
                                severity: str,
                                data_type: Optional[str] = None,
                                user_id: Optional[str] = None,
                                data_subject: Optional[str] = None,
                                metadata: Optional[Dict[str, Any]] = None) -> PrivacyViolation:
        """Detect and record a privacy violation."""
        
        violation = PrivacyViolation(
            violation_id=f"privacy-violation-{int(time.time())}-{uuid.uuid4().hex[:8]}",
            violation_type=violation_type,
            description=description,
            detected_at=datetime.now(timezone.utc),
            severity=severity,
            data_type=data_type,
            user_id=user_id,
            data_subject=data_subject,
            metadata=metadata or {}
        )
        
        self.privacy_violations[violation.violation_id] = violation
        
        logger.warning(f"Privacy violation detected: {violation_type} - {severity}")
        return violation
    
    def check_data_access_compliance(self,
                                   data_name: str,
                                   user_id: str,
                                   purpose: str,
                                   data_subject_id: Optional[str] = None) -> bool:
        """Check if data access complies with privacy requirements."""
        
        # Check data classification
        classification = self.data_classifications.get(data_name, DataClassification.INTERNAL)
        
        # Check consent for PII/PHI data
        if classification in [DataClassification.PII, DataClassification.PHI] and data_subject_id:
            if not self._has_valid_consent(data_subject_id, purpose, [data_name]):
                self.detect_privacy_violation(
                    violation_type="unauthorized_data_access",
                    description=f"Access to {classification.value} data without valid consent",
                    severity="high",
                    data_type=data_name,
                    user_id=user_id,
                    data_subject=data_subject_id,
                    metadata={"classification": classification.value, "purpose": purpose}
                )
                return False
        
        # Check data retention
        if not self._check_data_retention(data_name):
            self.detect_privacy_violation(
                violation_type="data_retention_violation",
                description=f"Access to data beyond retention period",
                severity="medium",
                data_type=data_name,
                user_id=user_id,
                metadata={"classification": classification.value}
            )
            return False
        
        return True
    
    def _has_valid_consent(self, data_subject_id: str, purpose: str, data_types: List[str]) -> bool:
        """Check if valid consent exists for data subject."""
        for consent in self.consent_records.values():
            if (consent.data_subject_id == data_subject_id and
                consent.purpose == purpose and
                consent.status == "active" and
                any(data_type in consent.data_types for data_type in data_types)):
                
                # Check if consent is expired
                if consent.expires_at and consent.expires_at < datetime.now(timezone.utc):
                    consent.status = "expired"
                    continue
                
                return True
        
        return False
    
    def _check_data_retention(self, data_name: str) -> bool:
        """Check if data access is within retention period."""
        # Mock implementation - in reality, this would check actual retention policies
        classification = self.data_classifications.get(data_name, DataClassification.INTERNAL)
        
        # Define retention periods by classification
        retention_periods = {
            DataClassification.PUBLIC: timedelta(days=365 * 10),  # 10 years
            DataClassification.INTERNAL: timedelta(days=365 * 3),  # 3 years
            DataClassification.CONFIDENTIAL: timedelta(days=365 * 2),  # 2 years
            DataClassification.RESTRICTED: timedelta(days=365),  # 1 year
            DataClassification.PII: timedelta(days=365),  # 1 year
            DataClassification.PHI: timedelta(days=365 * 6),  # 6 years (HIPAA)
            DataClassification.FINANCIAL: timedelta(days=365 * 7)  # 7 years
        }
        
        retention_period = retention_periods.get(classification, timedelta(days=365))
        
        # Mock data creation date - in reality, this would be stored with the data
        mock_creation_date = datetime.now(timezone.utc) - timedelta(days=200)
        
        return datetime.now(timezone.utc) - mock_creation_date <= retention_period
    
    def grant_consent(self,
                     data_subject_id: str,
                     purpose: str,
                     data_types: List[str],
                     expires_at: Optional[datetime] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> ConsentManager:
        """Grant consent for data processing."""
        
        consent = ConsentManager(
            consent_id=f"consent-{int(time.time())}-{uuid.uuid4().hex[:8]}",
            data_subject_id=data_subject_id,
            purpose=purpose,
            data_types=data_types,
            granted_at=datetime.now(timezone.utc),
            expires_at=expires_at,
            metadata=metadata or {}
        )
        
        self.consent_records[consent.consent_id] = consent
        
        logger.info(f"Consent granted for {data_subject_id}: {purpose}")
        return consent
    
    def revoke_consent(self, consent_id: str) -> bool:
        """Revoke a consent record."""
        if consent_id not in self.consent_records:
            return False
        
        consent = self.consent_records[consent_id]
        consent.status = "revoked"
        consent.revoked_at = datetime.now(timezone.utc)
        
        logger.info(f"Consent revoked: {consent_id}")
        return True
    
    def resolve_privacy_violation(self, violation_id: str, resolved_by: str, remediation_steps: List[str] = None) -> bool:
        """Resolve a privacy violation."""
        if violation_id not in self.privacy_violations:
            return False
        
        violation = self.privacy_violations[violation_id]
        violation.status = "resolved"
        violation.resolved_at = datetime.now(timezone.utc)
        violation.resolved_by = resolved_by
        
        if remediation_steps:
            violation.remediation_steps = remediation_steps
        
        logger.info(f"Privacy violation resolved: {violation_id} by {resolved_by}")
        return True
    
    def get_active_violations(self) -> List[PrivacyViolation]:
        """Get active privacy violations."""
        return [
            violation for violation in self.privacy_violations.values()
            if violation.status == "open"
        ]
    
    def get_consent_records(self, data_subject_id: Optional[str] = None) -> List[ConsentManager]:
        """Get consent records, optionally filtered by data subject."""
        records = list(self.consent_records.values())
        
        if data_subject_id:
            records = [r for r in records if r.data_subject_id == data_subject_id]
        
        return sorted(records, key=lambda r: r.granted_at, reverse=True)
    
    def get_privacy_statistics(self) -> Dict[str, Any]:
        """Get privacy monitoring statistics."""
        total_violations = len(self.privacy_violations)
        active_violations = len([v for v in self.privacy_violations.values() if v.status == "open"])
        
        # Violation type distribution
        violation_type_counts = {}
        for violation in self.privacy_violations.values():
            if violation.status == "open":
                violation_type_counts[violation.violation_type] = violation_type_counts.get(violation.violation_type, 0) + 1
        
        # Data classification distribution
        classification_counts = {}
        for classification in DataClassification:
            classification_counts[classification.value] = sum(
                1 for name, cls in self.data_classifications.items()
                if cls == classification
            )
        
        # Consent statistics
        active_consents = len([c for c in self.consent_records.values() if c.status == "active"])
        expired_consents = len([c for c in self.consent_records.values() if c.status == "expired"])
        revoked_consents = len([c for c in self.consent_records.values() if c.status == "revoked"])
        
        return {
            'total_violations': total_violations,
            'active_violations': active_violations,
            'resolved_violations': len([v for v in self.privacy_violations.values() if v.status == "resolved"]),
            'violation_type_distribution': violation_type_counts,
            'data_classification_distribution': classification_counts,
            'total_consent_records': len(self.consent_records),
            'active_consents': active_consents,
            'expired_consents': expired_consents,
            'revoked_consents': revoked_consents,
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
