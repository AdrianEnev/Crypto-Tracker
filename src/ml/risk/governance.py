"""
ML Governance system for policy management and lineage tracking.
Provides governance policies, data lineage, and model lineage capabilities.
"""

import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


@dataclass
class DataLineage:
    """Container for data lineage information."""
    lineage_id: str
    dataset_name: str
    source_datasets: List[str]
    transformations: List[Dict[str, Any]]
    created_at: datetime
    created_by: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'lineage_id': self.lineage_id,
            'dataset_name': self.dataset_name,
            'source_datasets': self.source_datasets,
            'transformations': self.transformations,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by,
            'metadata': self.metadata
        }


@dataclass
class ModelLineage:
    """Container for model lineage information."""
    lineage_id: str
    model_name: str
    model_version: str
    training_data: List[str]
    features: List[str]
    algorithms: List[str]
    hyperparameters: Dict[str, Any]
    created_at: datetime
    created_by: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'lineage_id': self.lineage_id,
            'model_name': self.model_name,
            'model_version': self.model_version,
            'training_data': self.training_data,
            'features': self.features,
            'algorithms': self.algorithms,
            'hyperparameters': self.hyperparameters,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by,
            'metadata': self.metadata
        }


@dataclass
class GovernancePolicy:
    """Container for governance policy configuration."""
    policy_id: str
    name: str
    description: str
    category: str  # "data", "model", "deployment", "security", "compliance"
    rules: List[Dict[str, Any]]
    severity: str  # "low", "medium", "high", "critical"
    enabled: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = "system"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'policy_id': self.policy_id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'rules': self.rules,
            'severity': self.severity,
            'enabled': self.enabled,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by
        }


@dataclass
class PolicyViolation:
    """Container for policy violation information."""
    violation_id: str
    policy_id: str
    violation_type: str
    description: str
    detected_at: datetime
    detected_by: str
    severity: str
    status: str = "open"  # "open", "acknowledged", "resolved"
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'violation_id': self.violation_id,
            'policy_id': self.policy_id,
            'violation_type': self.violation_type,
            'description': self.description,
            'detected_at': self.detected_at.isoformat(),
            'detected_by': self.detected_by,
            'severity': self.severity,
            'status': self.status,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolved_by': self.resolved_by,
            'metadata': self.metadata
        }


class MLGovernance:
    """
    ML Governance system for policy management and lineage tracking.
    """
    
    def __init__(self):
        self.policies: Dict[str, GovernancePolicy] = {}
        self.violations: Dict[str, PolicyViolation] = {}
        self.data_lineage: Dict[str, DataLineage] = {}
        self.model_lineage: Dict[str, ModelLineage] = {}
        
        # Initialize default policies
        self._initialize_default_policies()
        
        logger.info("Initialized ML governance system")
    
    def _initialize_default_policies(self) -> None:
        """Initialize default governance policies."""
        default_policies = [
            GovernancePolicy(
                policy_id="data-retention-policy",
                name="Data Retention Policy",
                description="Enforce data retention periods",
                category="data",
                rules=[
                    {"type": "retention_period", "max_days": 365},
                    {"type": "deletion_requirement", "auto_delete": True}
                ],
                severity="medium"
            ),
            GovernancePolicy(
                policy_id="model-versioning-policy",
                name="Model Versioning Policy",
                description="Enforce model versioning standards",
                category="model",
                rules=[
                    {"type": "version_format", "pattern": "semantic"},
                    {"type": "change_log", "required": True}
                ],
                severity="high"
            ),
            GovernancePolicy(
                policy_id="deployment-approval-policy",
                name="Deployment Approval Policy",
                description="Require approval for model deployments",
                category="deployment",
                rules=[
                    {"type": "approval_required", "min_approvers": 2},
                    {"type": "testing_required", "test_coverage": 0.8}
                ],
                severity="critical"
            )
        ]
        
        for policy in default_policies:
            self.policies[policy.policy_id] = policy
    
    def add_policy(self, policy: GovernancePolicy) -> None:
        """Add a governance policy."""
        self.policies[policy.policy_id] = policy
        logger.info(f"Added governance policy: {policy.name}")
    
    def remove_policy(self, policy_id: str) -> bool:
        """Remove a governance policy."""
        if policy_id in self.policies:
            del self.policies[policy_id]
            logger.info(f"Removed governance policy: {policy_id}")
            return True
        return False
    
    def create_data_lineage(self,
                           dataset_name: str,
                           source_datasets: List[str],
                           transformations: List[Dict[str, Any]],
                           created_by: str,
                           metadata: Optional[Dict[str, Any]] = None) -> DataLineage:
        """Create data lineage record."""
        lineage = DataLineage(
            lineage_id=f"data-lineage-{int(time.time())}-{uuid.uuid4().hex[:8]}",
            dataset_name=dataset_name,
            source_datasets=source_datasets,
            transformations=transformations,
            created_at=datetime.now(timezone.utc),
            created_by=created_by,
            metadata=metadata or {}
        )
        
        self.data_lineage[lineage.lineage_id] = lineage
        logger.info(f"Created data lineage: {dataset_name}")
        return lineage
    
    def create_model_lineage(self,
                            model_name: str,
                            model_version: str,
                            training_data: List[str],
                            features: List[str],
                            algorithms: List[str],
                            hyperparameters: Dict[str, Any],
                            created_by: str,
                            metadata: Optional[Dict[str, Any]] = None) -> ModelLineage:
        """Create model lineage record."""
        lineage = ModelLineage(
            lineage_id=f"model-lineage-{int(time.time())}-{uuid.uuid4().hex[:8]}",
            model_name=model_name,
            model_version=model_version,
            training_data=training_data,
            features=features,
            algorithms=algorithms,
            hyperparameters=hyperparameters,
            created_at=datetime.now(timezone.utc),
            created_by=created_by,
            metadata=metadata or {}
        )
        
        self.model_lineage[lineage.lineage_id] = lineage
        logger.info(f"Created model lineage: {model_name}:{model_version}")
        return lineage
    
    def check_policy_compliance(self, entity_type: str, entity_data: Dict[str, Any]) -> List[PolicyViolation]:
        """Check policy compliance for an entity."""
        violations = []
        
        # Get relevant policies for entity type
        relevant_policies = [
            policy for policy in self.policies.values()
            if policy.enabled and policy.category == entity_type
        ]
        
        for policy in relevant_policies:
            try:
                policy_violations = self._check_policy_rules(policy, entity_data)
                violations.extend(policy_violations)
            except Exception as e:
                logger.error(f"Error checking policy {policy.policy_id}: {e}")
        
        # Store violations
        for violation in violations:
            self.violations[violation.violation_id] = violation
        
        return violations
    
    def _check_policy_rules(self, policy: GovernancePolicy, entity_data: Dict[str, Any]) -> List[PolicyViolation]:
        """Check specific policy rules."""
        violations = []
        
        for rule in policy.rules:
            rule_type = rule.get("type")
            
            if rule_type == "retention_period":
                violation = self._check_retention_period(rule, entity_data, policy)
                if violation:
                    violations.append(violation)
            
            elif rule_type == "version_format":
                violation = self._check_version_format(rule, entity_data, policy)
                if violation:
                    violations.append(violation)
            
            elif rule_type == "approval_required":
                violation = self._check_approval_required(rule, entity_data, policy)
                if violation:
                    violations.append(violation)
            
            # Add more rule types as needed
        
        return violations
    
    def _check_retention_period(self, rule: Dict[str, Any], entity_data: Dict[str, Any], policy: GovernancePolicy) -> Optional[PolicyViolation]:
        """Check data retention period compliance."""
        max_days = rule.get("max_days", 365)
        created_date = entity_data.get("created_at")
        
        if created_date:
            if isinstance(created_date, str):
                from datetime import datetime
                created_date = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
            
            days_old = (datetime.now(timezone.utc) - created_date).days
            
            if days_old > max_days:
                return PolicyViolation(
                    violation_id=f"violation-{int(time.time())}-{uuid.uuid4().hex[:8]}",
                    policy_id=policy.policy_id,
                    violation_type="retention_period_exceeded",
                    description=f"Data retention period exceeded: {days_old} days > {max_days} days",
                    detected_at=datetime.now(timezone.utc),
                    detected_by="system",
                    severity=policy.severity,
                    metadata={"days_old": days_old, "max_days": max_days}
                )
        
        return None
    
    def _check_version_format(self, rule: Dict[str, Any], entity_data: Dict[str, Any], policy: GovernancePolicy) -> Optional[PolicyViolation]:
        """Check version format compliance."""
        version = entity_data.get("version")
        pattern = rule.get("pattern", "semantic")
        
        if version:
            if pattern == "semantic":
                # Check semantic versioning (e.g., 1.0.0)
                import re
                if not re.match(r'^\d+\.\d+\.\d+', version):
                    return PolicyViolation(
                        violation_id=f"violation-{int(time.time())}-{uuid.uuid4().hex[:8]}",
                        policy_id=policy.policy_id,
                        violation_type="invalid_version_format",
                        description=f"Version format does not match semantic versioning: {version}",
                        detected_at=datetime.now(timezone.utc),
                        detected_by="system",
                        severity=policy.severity,
                        metadata={"version": version, "expected_pattern": pattern}
                    )
        
        return None
    
    def _check_approval_required(self, rule: Dict[str, Any], entity_data: Dict[str, Any], policy: GovernancePolicy) -> Optional[PolicyViolation]:
        """Check approval requirement compliance."""
        min_approvers = rule.get("min_approvers", 2)
        approvers = entity_data.get("approvers", [])
        
        if len(approvers) < min_approvers:
            return PolicyViolation(
                violation_id=f"violation-{int(time.time())}-{uuid.uuid4().hex[:8]}",
                policy_id=policy.policy_id,
                violation_type="insufficient_approvals",
                description=f"Insufficient approvals: {len(approvers)} < {min_approvers}",
                detected_at=datetime.now(timezone.utc),
                detected_by="system",
                severity=policy.severity,
                metadata={"approvers_count": len(approvers), "min_approvers": min_approvers}
            )
        
        return None
    
    def resolve_violation(self, violation_id: str, resolved_by: str) -> bool:
        """Resolve a policy violation."""
        if violation_id not in self.violations:
            return False
        
        violation = self.violations[violation_id]
        violation.status = "resolved"
        violation.resolved_at = datetime.now(timezone.utc)
        violation.resolved_by = resolved_by
        
        logger.info(f"Policy violation resolved: {violation_id} by {resolved_by}")
        return True
    
    def get_open_violations(self) -> List[PolicyViolation]:
        """Get open policy violations."""
        return [
            violation for violation in self.violations.values()
            if violation.status == "open"
        ]
    
    def get_lineage_trace(self, entity_name: str, entity_type: str = "model") -> List[Dict[str, Any]]:
        """Get lineage trace for an entity."""
        trace = []
        
        if entity_type == "model":
            # Find model lineage
            for lineage in self.model_lineage.values():
                if lineage.model_name == entity_name:
                    trace.append({
                        "type": "model",
                        "data": lineage.to_dict()
                    })
                    
                    # Find related data lineage
                    for data_lineage in self.data_lineage.values():
                        if data_lineage.dataset_name in lineage.training_data:
                            trace.append({
                                "type": "data",
                                "data": data_lineage.to_dict()
                            })
        
        elif entity_type == "data":
            # Find data lineage
            for lineage in self.data_lineage.values():
                if lineage.dataset_name == entity_name:
                    trace.append({
                        "type": "data",
                        "data": lineage.to_dict()
                    })
        
        return trace
    
    def get_governance_statistics(self) -> Dict[str, Any]:
        """Get governance system statistics."""
        return {
            'total_policies': len(self.policies),
            'enabled_policies': len([p for p in self.policies.values() if p.enabled]),
            'total_violations': len(self.violations),
            'open_violations': len([v for v in self.violations.values() if v.status == "open"]),
            'data_lineage_records': len(self.data_lineage),
            'model_lineage_records': len(self.model_lineage),
            'policy_categories': list(set(p.category for p in self.policies.values())),
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
