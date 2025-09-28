"""
Compliance Monitoring system for ML operations.
Provides regulatory compliance tracking and violation detection.
"""

import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import json

logger = logging.getLogger(__name__)


class ComplianceFramework(Enum):
    """Compliance frameworks and regulations."""
    GDPR = "gdpr"  # General Data Protection Regulation
    CCPA = "ccpa"  # California Consumer Privacy Act
    HIPAA = "hipaa"  # Health Insurance Portability and Accountability Act
    SOX = "sox"  # Sarbanes-Oxley Act
    PCI_DSS = "pci_dss"  # Payment Card Industry Data Security Standard
    ISO27001 = "iso27001"  # Information Security Management
    FERPA = "ferpa"  # Family Educational Rights and Privacy Act
    COPPA = "coppa"  # Children's Online Privacy Protection Act
    AI_ACT = "ai_act"  # EU AI Act
    CUSTOM = "custom"  # Custom compliance framework


@dataclass
class ComplianceRule:
    """Container for compliance rule configuration."""
    rule_id: str
    framework: ComplianceFramework
    rule_name: str
    description: str
    requirement: str
    severity: str  # "critical", "high", "medium", "low"
    automated_check: bool = True
    check_function: Optional[str] = None  # Function name for automated checking
    manual_review_required: bool = False
    review_frequency: str = "monthly"  # "daily", "weekly", "monthly", "quarterly", "annually"
    last_reviewed: Optional[datetime] = None
    next_review_due: Optional[datetime] = None
    enabled: bool = True
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'rule_id': self.rule_id,
            'framework': self.framework.value,
            'rule_name': self.rule_name,
            'description': self.description,
            'requirement': self.requirement,
            'severity': self.severity,
            'automated_check': self.automated_check,
            'check_function': self.check_function,
            'manual_review_required': self.manual_review_required,
            'review_frequency': self.review_frequency,
            'last_reviewed': self.last_reviewed.isoformat() if self.last_reviewed else None,
            'next_review_due': self.next_review_due.isoformat() if self.next_review_due else None,
            'enabled': self.enabled,
            'tags': self.tags,
            'created_at': self.created_at.isoformat()
        }


@dataclass
class ComplianceViolation:
    """Container for compliance violation information."""
    violation_id: str
    rule_id: str
    framework: ComplianceFramework
    violation_type: str  # "automated_check_failed", "manual_review_failed", "deadline_missed"
    severity: str
    description: str
    detected_at: datetime
    detected_by: str  # "system", "manual_review", "audit"
    status: str = "open"  # "open", "acknowledged", "in_remediation", "resolved", "false_positive"
    remediation_plan: Optional[str] = None
    remediation_deadline: Optional[datetime] = None
    assigned_to: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    evidence: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'violation_id': self.violation_id,
            'rule_id': self.rule_id,
            'framework': self.framework.value,
            'violation_type': self.violation_type,
            'severity': self.severity,
            'description': self.description,
            'detected_at': self.detected_at.isoformat(),
            'detected_by': self.detected_by,
            'status': self.status,
            'remediation_plan': self.remediation_plan,
            'remediation_deadline': self.remediation_deadline.isoformat() if self.remediation_deadline else None,
            'assigned_to': self.assigned_to,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolved_by': self.resolved_by,
            'evidence': self.evidence,
            'metadata': self.metadata
        }


class ComplianceMonitor:
    """
    Compliance monitoring system for ML operations.
    """
    
    def __init__(self):
        self.compliance_rules: Dict[str, ComplianceRule] = {}
        self.violations: Dict[str, ComplianceViolation] = {}
        self.check_functions: Dict[str, Callable] = {}
        self.framework_requirements: Dict[ComplianceFramework, Dict[str, Any]] = {}
        
        # Initialize default compliance frameworks
        self._initialize_default_frameworks()
        self._initialize_default_rules()
        
        logger.info("Initialized compliance monitor")
    
    def _initialize_default_frameworks(self) -> None:
        """Initialize default compliance frameworks."""
        self.framework_requirements[ComplianceFramework.GDPR] = {
            'data_protection_officer': True,
            'privacy_by_design': True,
            'data_minimization': True,
            'consent_management': True,
            'right_to_be_forgotten': True,
            'data_portability': True,
            'breach_notification': True,
            'privacy_impact_assessment': True
        }
        
        self.framework_requirements[ComplianceFramework.CCPA] = {
            'privacy_notice': True,
            'opt_out_mechanism': True,
            'data_collection_disclosure': True,
            'third_party_sharing': True,
            'consumer_rights': True
        }
        
        self.framework_requirements[ComplianceFramework.AI_ACT] = {
            'risk_assessment': True,
            'transparency_requirements': True,
            'human_oversight': True,
            'accuracy_robustness': True,
            'data_governance': True,
            'documentation_requirements': True
        }
    
    def _initialize_default_rules(self) -> None:
        """Initialize default compliance rules."""
        default_rules = [
            ComplianceRule(
                rule_id="gdpr-data-minimization",
                framework=ComplianceFramework.GDPR,
                rule_name="Data Minimization",
                description="Ensure only necessary data is collected and processed",
                requirement="Collect only data that is adequate, relevant and limited to what is necessary",
                severity="high",
                automated_check=True,
                check_function="check_data_minimization",
                review_frequency="monthly"
            ),
            ComplianceRule(
                rule_id="gdpr-consent-management",
                framework=ComplianceFramework.GDPR,
                rule_name="Consent Management",
                description="Verify proper consent mechanisms are in place",
                requirement="Obtain clear and explicit consent for data processing",
                severity="critical",
                automated_check=True,
                check_function="check_consent_management",
                review_frequency="weekly"
            ),
            ComplianceRule(
                rule_id="ai-act-risk-assessment",
                framework=ComplianceFramework.AI_ACT,
                rule_name="AI Risk Assessment",
                description="Conduct risk assessment for AI systems",
                requirement="Assess and document risks associated with AI system deployment",
                severity="high",
                automated_check=False,
                manual_review_required=True,
                review_frequency="quarterly"
            ),
            ComplianceRule(
                rule_id="ai-act-transparency",
                framework=ComplianceFramework.AI_ACT,
                rule_name="AI Transparency",
                description="Ensure AI system transparency and explainability",
                requirement="Provide clear information about AI system operation and decisions",
                severity="medium",
                automated_check=True,
                check_function="check_ai_transparency",
                review_frequency="monthly"
            ),
            ComplianceRule(
                rule_id="ccpa-privacy-notice",
                framework=ComplianceFramework.CCPA,
                rule_name="Privacy Notice",
                description="Maintain comprehensive privacy notices",
                requirement="Provide clear privacy notices to consumers",
                severity="high",
                automated_check=False,
                manual_review_required=True,
                review_frequency="monthly"
            )
        ]
        
        for rule in default_rules:
            self.compliance_rules[rule.rule_id] = rule
        
        # Initialize default check functions
        self._initialize_default_check_functions()
    
    def _initialize_default_check_functions(self) -> None:
        """Initialize default compliance check functions."""
        self.check_functions["check_data_minimization"] = self._check_data_minimization
        self.check_functions["check_consent_management"] = self._check_consent_management
        self.check_functions["check_ai_transparency"] = self._check_ai_transparency
    
    def add_compliance_rule(self, rule: ComplianceRule) -> None:
        """Add a compliance rule."""
        self.compliance_rules[rule.rule_id] = rule
        logger.info(f"Added compliance rule: {rule.rule_name}")
    
    def remove_compliance_rule(self, rule_id: str) -> bool:
        """Remove a compliance rule."""
        if rule_id in self.compliance_rules:
            del self.compliance_rules[rule_id]
            logger.info(f"Removed compliance rule: {rule_id}")
            return True
        return False
    
    def register_check_function(self, function_name: str, check_function: Callable) -> None:
        """Register a compliance check function."""
        self.check_functions[function_name] = check_function
        logger.info(f"Registered compliance check function: {function_name}")
    
    def run_compliance_checks(self) -> List[ComplianceViolation]:
        """Run all automated compliance checks."""
        violations = []
        
        for rule_id, rule in self.compliance_rules.items():
            if not rule.enabled or not rule.automated_check:
                continue
            
            try:
                if rule.check_function and rule.check_function in self.check_functions:
                    check_result = self.check_functions[rule.check_function](rule)
                    if not check_result.get('compliant', True):
                        violation = self._create_violation(
                            rule=rule,
                            violation_type="automated_check_failed",
                            description=check_result.get('description', f"Failed automated check for {rule.rule_name}"),
                            evidence=check_result.get('evidence', []),
                            metadata=check_result.get('metadata', {})
                        )
                        violations.append(violation)
                        self.violations[violation.violation_id] = violation
                
            except Exception as e:
                logger.error(f"Error running compliance check for rule {rule_id}: {e}")
        
        logger.info(f"Compliance checks completed: {len(violations)} violations found")
        return violations
    
    def _check_data_minimization(self, rule: ComplianceRule) -> Dict[str, Any]:
        """Check data minimization compliance."""
        # Mock implementation - in reality, this would check actual data collection practices
        import random
        
        # Simulate random compliance check
        compliant = random.random() > 0.1  # 90% compliance rate
        
        if not compliant:
            return {
                'compliant': False,
                'description': 'Excessive data collection detected',
                'evidence': ['Data collection exceeds stated purpose', 'Unnecessary personal data fields found'],
                'metadata': {'data_fields_count': 15, 'required_fields': 8}
            }
        
        return {'compliant': True}
    
    def _check_consent_management(self, rule: ComplianceRule) -> Dict[str, Any]:
        """Check consent management compliance."""
        import random
        
        compliant = random.random() > 0.05  # 95% compliance rate
        
        if not compliant:
            return {
                'compliant': False,
                'description': 'Consent management issues detected',
                'evidence': ['Missing consent records', 'Expired consent not handled'],
                'metadata': {'missing_consent_count': 25, 'expired_consent_count': 12}
            }
        
        return {'compliant': True}
    
    def _check_ai_transparency(self, rule: ComplianceRule) -> Dict[str, Any]:
        """Check AI transparency compliance."""
        import random
        
        compliant = random.random() > 0.15  # 85% compliance rate
        
        if not compliant:
            return {
                'compliant': False,
                'description': 'AI transparency requirements not met',
                'evidence': ['Missing model documentation', 'No explainability features'],
                'metadata': {'documentation_completeness': 0.6, 'explainability_score': 0.3}
            }
        
        return {'compliant': True}
    
    def _create_violation(self,
                         rule: ComplianceRule,
                         violation_type: str,
                         description: str,
                         evidence: List[str] = None,
                         metadata: Dict[str, Any] = None) -> ComplianceViolation:
        """Create a compliance violation."""
        violation = ComplianceViolation(
            violation_id=f"violation-{int(time.time())}-{uuid.uuid4().hex[:8]}",
            rule_id=rule.rule_id,
            framework=rule.framework,
            violation_type=violation_type,
            severity=rule.severity,
            description=description,
            detected_at=datetime.now(timezone.utc),
            detected_by="system",
            evidence=evidence or [],
            metadata=metadata or {}
        )
        
        return violation
    
    def create_manual_violation(self,
                               rule_id: str,
                               description: str,
                               severity: str,
                               detected_by: str,
                               evidence: List[str] = None) -> Optional[ComplianceViolation]:
        """Create a manual compliance violation."""
        if rule_id not in self.compliance_rules:
            logger.error(f"Compliance rule not found: {rule_id}")
            return None
        
        rule = self.compliance_rules[rule_id]
        
        violation = ComplianceViolation(
            violation_id=f"violation-{int(time.time())}-{uuid.uuid4().hex[:8]}",
            rule_id=rule_id,
            framework=rule.framework,
            violation_type="manual_review_failed",
            severity=severity,
            description=description,
            detected_at=datetime.now(timezone.utc),
            detected_by=detected_by,
            evidence=evidence or [],
            metadata={}
        )
        
        self.violations[violation.violation_id] = violation
        
        logger.info(f"Created manual violation: {description}")
        return violation
    
    def acknowledge_violation(self, violation_id: str, acknowledged_by: str) -> bool:
        """Acknowledge a compliance violation."""
        if violation_id not in self.violations:
            return False
        
        violation = self.violations[violation_id]
        violation.status = "acknowledged"
        
        logger.info(f"Violation acknowledged: {violation_id} by {acknowledged_by}")
        return True
    
    def assign_violation(self, violation_id: str, assigned_to: str, remediation_plan: str = None) -> bool:
        """Assign a compliance violation for remediation."""
        if violation_id not in self.violations:
            return False
        
        violation = self.violations[violation_id]
        violation.assigned_to = assigned_to
        violation.remediation_plan = remediation_plan
        violation.status = "in_remediation"
        
        logger.info(f"Violation assigned: {violation_id} to {assigned_to}")
        return True
    
    def resolve_violation(self, violation_id: str, resolved_by: str, resolution_notes: str = None) -> bool:
        """Resolve a compliance violation."""
        if violation_id not in self.violations:
            return False
        
        violation = self.violations[violation_id]
        violation.status = "resolved"
        violation.resolved_at = datetime.now(timezone.utc)
        violation.resolved_by = resolved_by
        
        if resolution_notes:
            violation.metadata['resolution_notes'] = resolution_notes
        
        logger.info(f"Violation resolved: {violation_id} by {resolved_by}")
        return True
    
    def get_open_violations(self, framework: Optional[ComplianceFramework] = None) -> List[ComplianceViolation]:
        """Get open compliance violations."""
        violations = [v for v in self.violations.values() if v.status in ["open", "acknowledged", "in_remediation"]]
        
        if framework:
            violations = [v for v in violations if v.framework == framework]
        
        return sorted(violations, key=lambda v: v.detected_at, reverse=True)
    
    def get_violation_statistics(self) -> Dict[str, Any]:
        """Get compliance violation statistics."""
        total_violations = len(self.violations)
        open_violations = len([v for v in self.violations.values() if v.status in ["open", "acknowledged", "in_remediation"]])
        
        # Severity distribution
        severity_counts = {}
        for severity in ["critical", "high", "medium", "low"]:
            severity_counts[severity] = len([
                v for v in self.violations.values() 
                if v.severity == severity and v.status in ["open", "acknowledged", "in_remediation"]
            ])
        
        # Framework distribution
        framework_counts = {}
        for framework in ComplianceFramework:
            framework_counts[framework.value] = len([
                v for v in self.violations.values() 
                if v.framework == framework and v.status in ["open", "acknowledged", "in_remediation"]
            ])
        
        # Violation type distribution
        type_counts = {}
        for violation in self.violations.values():
            if violation.status in ["open", "acknowledged", "in_remediation"]:
                type_counts[violation.violation_type] = type_counts.get(violation.violation_type, 0) + 1
        
        return {
            'total_violations': total_violations,
            'open_violations': open_violations,
            'resolved_violations': len([v for v in self.violations.values() if v.status == "resolved"]),
            'severity_distribution': severity_counts,
            'framework_distribution': framework_counts,
            'violation_type_distribution': type_counts,
            'total_rules': len(self.compliance_rules),
            'enabled_rules': len([r for r in self.compliance_rules.values() if r.enabled])
        }
    
    def get_compliance_status(self, framework: ComplianceFramework) -> Dict[str, Any]:
        """Get compliance status for a specific framework."""
        framework_rules = [r for r in self.compliance_rules.values() if r.framework == framework]
        framework_violations = [v for v in self.violations.values() if v.framework == framework and v.status in ["open", "acknowledged", "in_remediation"]]
        
        # Calculate compliance score
        total_rules = len(framework_rules)
        violated_rules = len(set(v.rule_id for v in framework_violations))
        compliance_score = (total_rules - violated_rules) / total_rules if total_rules > 0 else 1.0
        
        # Determine compliance level
        if compliance_score >= 0.95:
            compliance_level = "excellent"
        elif compliance_score >= 0.85:
            compliance_level = "good"
        elif compliance_score >= 0.70:
            compliance_level = "fair"
        else:
            compliance_level = "poor"
        
        return {
            'framework': framework.value,
            'compliance_score': compliance_score,
            'compliance_level': compliance_level,
            'total_rules': total_rules,
            'violated_rules': violated_rules,
            'open_violations': len(framework_violations),
            'requirements': self.framework_requirements.get(framework, {}),
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
