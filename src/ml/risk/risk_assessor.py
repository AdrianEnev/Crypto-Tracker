"""
Risk Assessment system for ML operations.
Provides comprehensive risk evaluation and mitigation strategies.
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


class RiskLevel(Enum):
    """Risk severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskCategory(Enum):
    """Risk categories for ML systems."""
    DATA_QUALITY = "data_quality"
    MODEL_PERFORMANCE = "model_performance"
    SECURITY = "security"
    PRIVACY = "privacy"
    BIAS_FAIRNESS = "bias_fairness"
    COMPLIANCE = "compliance"
    OPERATIONAL = "operational"
    FINANCIAL = "financial"
    REPUTATIONAL = "reputational"
    TECHNICAL = "technical"


@dataclass
class RiskEvent:
    """Container for risk event information."""
    risk_id: str
    category: RiskCategory
    level: RiskLevel
    title: str
    description: str
    detected_at: datetime
    source: str  # Component or system that detected the risk
    probability: float  # 0.0 to 1.0
    impact_score: float  # 0.0 to 10.0
    risk_score: float  # Calculated from probability * impact
    metadata: Dict[str, Any] = field(default_factory=dict)
    mitigation_strategies: List[str] = field(default_factory=list)
    status: str = "active"  # active, mitigated, resolved, false_positive
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'risk_id': self.risk_id,
            'category': self.category.value,
            'level': self.level.value,
            'title': self.title,
            'description': self.description,
            'detected_at': self.detected_at.isoformat(),
            'source': self.source,
            'probability': self.probability,
            'impact_score': self.impact_score,
            'risk_score': self.risk_score,
            'metadata': self.metadata,
            'mitigation_strategies': self.mitigation_strategies,
            'status': self.status,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolved_by': self.resolved_by
        }


@dataclass
class RiskMitigation:
    """Container for risk mitigation strategy."""
    mitigation_id: str
    risk_id: str
    strategy: str
    description: str
    effectiveness: float  # 0.0 to 1.0
    cost: float  # Implementation cost
    timeframe: str  # Implementation timeframe
    responsible_party: str
    status: str = "pending"  # pending, in_progress, completed, failed
    implemented_at: Optional[datetime] = None
    implemented_by: Optional[str] = None
    verification_required: bool = True
    verification_status: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'mitigation_id': self.mitigation_id,
            'risk_id': self.risk_id,
            'strategy': self.strategy,
            'description': self.description,
            'effectiveness': self.effectiveness,
            'cost': self.cost,
            'timeframe': self.timeframe,
            'responsible_party': self.responsible_party,
            'status': self.status,
            'implemented_at': self.implemented_at.isoformat() if self.implemented_at else None,
            'implemented_by': self.implemented_by,
            'verification_required': self.verification_required,
            'verification_status': self.verification_status
        }


class RiskAssessor:
    """
    Risk assessment system for ML operations.
    """
    
    def __init__(self):
        self.risk_events: Dict[str, RiskEvent] = {}
        self.mitigations: Dict[str, RiskMitigation] = {}
        self.risk_assessors: Dict[RiskCategory, Callable] = {}
        self.risk_thresholds: Dict[RiskLevel, float] = {
            RiskLevel.LOW: 2.0,
            RiskLevel.MEDIUM: 5.0,
            RiskLevel.HIGH: 7.0,
            RiskLevel.CRITICAL: 9.0
        }
        
        # Initialize default risk assessors
        self._initialize_default_assessors()
        
        logger.info("Initialized risk assessor")
    
    def _initialize_default_assessors(self) -> None:
        """Initialize default risk assessment functions."""
        self.risk_assessors[RiskCategory.DATA_QUALITY] = self._assess_data_quality_risk
        self.risk_assessors[RiskCategory.MODEL_PERFORMANCE] = self._assess_model_performance_risk
        self.risk_assessors[RiskCategory.SECURITY] = self._assess_security_risk
        self.risk_assessors[RiskCategory.PRIVACY] = self._assess_privacy_risk
        self.risk_assessors[RiskCategory.BIAS_FAIRNESS] = self._assess_bias_risk
        self.risk_assessors[RiskCategory.OPERATIONAL] = self._assess_operational_risk
        self.risk_assessors[RiskCategory.FINANCIAL] = self._assess_financial_risk
    
    def register_risk_assessor(self, category: RiskCategory, assessor: Callable) -> None:
        """Register a custom risk assessor function."""
        self.risk_assessors[category] = assessor
        logger.info(f"Registered risk assessor for category: {category.value}")
    
    def assess_risk(self, 
                   category: RiskCategory,
                   context: Dict[str, Any],
                   source: str = "system") -> Optional[RiskEvent]:
        """Assess risk for a specific category and context."""
        if category not in self.risk_assessors:
            logger.warning(f"No risk assessor registered for category: {category.value}")
            return None
        
        try:
            risk_data = self.risk_assessors[category](context)
            if risk_data is None:
                return None
            
            # Calculate risk score
            probability = risk_data.get('probability', 0.0)
            impact_score = risk_data.get('impact_score', 0.0)
            risk_score = probability * impact_score
            
            # Determine risk level
            risk_level = self._determine_risk_level(risk_score)
            
            # Create risk event
            risk_event = RiskEvent(
                risk_id=f"risk-{int(time.time())}-{uuid.uuid4().hex[:8]}",
                category=category,
                level=risk_level,
                title=risk_data.get('title', f"{category.value} risk detected"),
                description=risk_data.get('description', 'Risk assessment completed'),
                detected_at=datetime.now(timezone.utc),
                source=source,
                probability=probability,
                impact_score=impact_score,
                risk_score=risk_score,
                metadata=context,
                mitigation_strategies=risk_data.get('mitigation_strategies', [])
            )
            
            # Store risk event
            self.risk_events[risk_event.risk_id] = risk_event
            
            logger.info(f"Risk assessed: {risk_event.title} (Level: {risk_level.value}, Score: {risk_score:.2f})")
            return risk_event
            
        except Exception as e:
            logger.error(f"Error assessing risk for category {category.value}: {e}")
            return None
    
    def _determine_risk_level(self, risk_score: float) -> RiskLevel:
        """Determine risk level based on risk score."""
        if risk_score >= self.risk_thresholds[RiskLevel.CRITICAL]:
            return RiskLevel.CRITICAL
        elif risk_score >= self.risk_thresholds[RiskLevel.HIGH]:
            return RiskLevel.HIGH
        elif risk_score >= self.risk_thresholds[RiskLevel.MEDIUM]:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _assess_data_quality_risk(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Assess data quality risks."""
        missing_data_percent = context.get('missing_data_percent', 0.0)
        outlier_percent = context.get('outlier_percent', 0.0)
        data_age_days = context.get('data_age_days', 0)
        
        risk_score = 0.0
        issues = []
        
        # Missing data risk
        if missing_data_percent > 20:
            risk_score += 0.7
            issues.append(f"High missing data: {missing_data_percent:.1f}%")
        elif missing_data_percent > 10:
            risk_score += 0.4
            issues.append(f"Moderate missing data: {missing_data_percent:.1f}%")
        
        # Outlier risk
        if outlier_percent > 15:
            risk_score += 0.6
            issues.append(f"High outlier rate: {outlier_percent:.1f}%")
        elif outlier_percent > 5:
            risk_score += 0.3
            issues.append(f"Moderate outlier rate: {outlier_percent:.1f}%")
        
        # Data staleness risk
        if data_age_days > 30:
            risk_score += 0.5
            issues.append(f"Stale data: {data_age_days} days old")
        elif data_age_days > 7:
            risk_score += 0.2
            issues.append(f"Data age: {data_age_days} days")
        
        if risk_score == 0:
            return None
        
        return {
            'probability': min(risk_score, 1.0),
            'impact_score': 7.0,  # Data quality issues can significantly impact model performance
            'title': 'Data Quality Risk Detected',
            'description': '; '.join(issues),
            'mitigation_strategies': [
                'Implement data validation pipeline',
                'Add data freshness monitoring',
                'Create data quality alerts',
                'Establish data cleaning procedures'
            ]
        }
    
    def _assess_model_performance_risk(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Assess model performance risks."""
        accuracy = context.get('accuracy', 1.0)
        precision = context.get('precision', 1.0)
        recall = context.get('recall', 1.0)
        f1_score = context.get('f1_score', 1.0)
        prediction_drift = context.get('prediction_drift', 0.0)
        
        risk_score = 0.0
        issues = []
        
        # Performance degradation risk
        if accuracy < 0.7:
            risk_score += 0.8
            issues.append(f"Low accuracy: {accuracy:.3f}")
        elif accuracy < 0.8:
            risk_score += 0.5
            issues.append(f"Moderate accuracy: {accuracy:.3f}")
        
        if precision < 0.7:
            risk_score += 0.6
            issues.append(f"Low precision: {precision:.3f}")
        
        if recall < 0.7:
            risk_score += 0.6
            issues.append(f"Low recall: {recall:.3f}")
        
        if f1_score < 0.7:
            risk_score += 0.7
            issues.append(f"Low F1 score: {f1_score:.3f}")
        
        # Model drift risk
        if prediction_drift > 0.3:
            risk_score += 0.9
            issues.append(f"High prediction drift: {prediction_drift:.3f}")
        elif prediction_drift > 0.2:
            risk_score += 0.6
            issues.append(f"Moderate prediction drift: {prediction_drift:.3f}")
        
        if risk_score == 0:
            return None
        
        return {
            'probability': min(risk_score, 1.0),
            'impact_score': 8.0,  # Model performance directly impacts business outcomes
            'title': 'Model Performance Risk Detected',
            'description': '; '.join(issues),
            'mitigation_strategies': [
                'Retrain model with fresh data',
                'Implement model monitoring',
                'Add performance alerts',
                'Consider ensemble methods',
                'Review feature engineering'
            ]
        }
    
    def _assess_security_risk(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Assess security risks."""
        failed_logins = context.get('failed_logins', 0)
        suspicious_requests = context.get('suspicious_requests', 0)
        data_access_anomalies = context.get('data_access_anomalies', 0)
        model_tampering_detected = context.get('model_tampering_detected', False)
        
        risk_score = 0.0
        issues = []
        
        # Authentication risk
        if failed_logins > 10:
            risk_score += 0.8
            issues.append(f"Multiple failed logins: {failed_logins}")
        
        # Suspicious activity risk
        if suspicious_requests > 5:
            risk_score += 0.7
            issues.append(f"Suspicious requests detected: {suspicious_requests}")
        
        # Data access risk
        if data_access_anomalies > 3:
            risk_score += 0.9
            issues.append(f"Data access anomalies: {data_access_anomalies}")
        
        # Model integrity risk
        if model_tampering_detected:
            risk_score += 1.0
            issues.append("Model tampering detected")
        
        if risk_score == 0:
            return None
        
        return {
            'probability': min(risk_score, 1.0),
            'impact_score': 9.0,  # Security breaches can have severe consequences
            'title': 'Security Risk Detected',
            'description': '; '.join(issues),
            'mitigation_strategies': [
                'Implement additional authentication',
                'Review access controls',
                'Monitor system logs',
                'Deploy intrusion detection',
                'Update security policies'
            ]
        }
    
    def _assess_privacy_risk(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Assess privacy risks."""
        pii_detected = context.get('pii_detected', False)
        data_retention_violation = context.get('data_retention_violation', False)
        consent_expired = context.get('consent_expired', False)
        cross_border_transfer = context.get('cross_border_transfer', False)
        
        risk_score = 0.0
        issues = []
        
        # PII exposure risk
        if pii_detected:
            risk_score += 0.8
            issues.append("PII detected in model data")
        
        # Data retention risk
        if data_retention_violation:
            risk_score += 0.7
            issues.append("Data retention policy violation")
        
        # Consent risk
        if consent_expired:
            risk_score += 0.9
            issues.append("User consent expired")
        
        # Cross-border transfer risk
        if cross_border_transfer:
            risk_score += 0.6
            issues.append("Cross-border data transfer detected")
        
        if risk_score == 0:
            return None
        
        return {
            'probability': min(risk_score, 1.0),
            'impact_score': 8.5,  # Privacy violations can lead to regulatory fines
            'title': 'Privacy Risk Detected',
            'description': '; '.join(issues),
            'mitigation_strategies': [
                'Implement data anonymization',
                'Review data retention policies',
                'Update consent management',
                'Add privacy controls',
                'Conduct privacy impact assessment'
            ]
        }
    
    def _assess_bias_risk(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Assess bias and fairness risks."""
        demographic_parity = context.get('demographic_parity', 1.0)
        equalized_odds = context.get('equalized_odds', 1.0)
        disparate_impact = context.get('disparate_impact', 1.0)
        
        risk_score = 0.0
        issues = []
        
        # Bias detection
        if demographic_parity < 0.8 or demographic_parity > 1.2:
            risk_score += 0.8
            issues.append(f"Demographic parity violation: {demographic_parity:.3f}")
        
        if equalized_odds < 0.8 or equalized_odds > 1.2:
            risk_score += 0.7
            issues.append(f"Equalized odds violation: {equalized_odds:.3f}")
        
        if disparate_impact < 0.8:
            risk_score += 0.9
            issues.append(f"Disparate impact detected: {disparate_impact:.3f}")
        
        if risk_score == 0:
            return None
        
        return {
            'probability': min(risk_score, 1.0),
            'impact_score': 7.5,  # Bias can lead to unfair outcomes and reputational damage
            'title': 'Bias and Fairness Risk Detected',
            'description': '; '.join(issues),
            'mitigation_strategies': [
                'Implement bias detection monitoring',
                'Use fairness-aware algorithms',
                'Regular bias auditing',
                'Diverse training data collection',
                'Fairness constraint optimization'
            ]
        }
    
    def _assess_operational_risk(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Assess operational risks."""
        system_uptime = context.get('system_uptime', 1.0)
        response_time = context.get('response_time', 0.0)
        error_rate = context.get('error_rate', 0.0)
        resource_utilization = context.get('resource_utilization', 0.0)
        
        risk_score = 0.0
        issues = []
        
        # Availability risk
        if system_uptime < 0.95:
            risk_score += 0.8
            issues.append(f"Low system uptime: {system_uptime:.3f}")
        
        # Performance risk
        if response_time > 1000:  # milliseconds
            risk_score += 0.6
            issues.append(f"High response time: {response_time:.0f}ms")
        
        # Error rate risk
        if error_rate > 0.05:
            risk_score += 0.7
            issues.append(f"High error rate: {error_rate:.3f}")
        
        # Resource risk
        if resource_utilization > 0.9:
            risk_score += 0.5
            issues.append(f"High resource utilization: {resource_utilization:.3f}")
        
        if risk_score == 0:
            return None
        
        return {
            'probability': min(risk_score, 1.0),
            'impact_score': 6.0,  # Operational issues affect service quality
            'title': 'Operational Risk Detected',
            'description': '; '.join(issues),
            'mitigation_strategies': [
                'Implement auto-scaling',
                'Add performance monitoring',
                'Improve error handling',
                'Optimize resource allocation',
                'Create incident response plan'
            ]
        }
    
    def _assess_financial_risk(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Assess financial risks."""
        trading_loss = context.get('trading_loss', 0.0)
        max_drawdown = context.get('max_drawdown', 0.0)
        var_violation = context.get('var_violation', False)
        position_concentration = context.get('position_concentration', 0.0)
        
        risk_score = 0.0
        issues = []
        
        # Trading loss risk
        if trading_loss > 10000:  # Assuming USD
            risk_score += 0.8
            issues.append(f"Significant trading loss: ${trading_loss:.2f}")
        
        # Drawdown risk
        if max_drawdown > 0.15:  # 15% drawdown
            risk_score += 0.7
            issues.append(f"High drawdown: {max_drawdown:.3f}")
        
        # VaR violation risk
        if var_violation:
            risk_score += 0.9
            issues.append("VaR limit violated")
        
        # Concentration risk
        if position_concentration > 0.3:  # 30% in single position
            risk_score += 0.6
            issues.append(f"High position concentration: {position_concentration:.3f}")
        
        if risk_score == 0:
            return None
        
        return {
            'probability': min(risk_score, 1.0),
            'impact_score': 9.5,  # Financial risks directly impact profitability
            'title': 'Financial Risk Detected',
            'description': '; '.join(issues),
            'mitigation_strategies': [
                'Implement position limits',
                'Add real-time risk monitoring',
                'Diversify portfolio',
                'Set stop-loss orders',
                'Review risk parameters'
            ]
        }
    
    def create_mitigation(self, 
                         risk_id: str,
                         strategy: str,
                         description: str,
                         effectiveness: float,
                         cost: float,
                         timeframe: str,
                         responsible_party: str) -> Optional[RiskMitigation]:
        """Create a risk mitigation strategy."""
        if risk_id not in self.risk_events:
            logger.error(f"Risk ID not found: {risk_id}")
            return None
        
        mitigation = RiskMitigation(
            mitigation_id=f"mitigation-{int(time.time())}-{uuid.uuid4().hex[:8]}",
            risk_id=risk_id,
            strategy=strategy,
            description=description,
            effectiveness=effectiveness,
            cost=cost,
            timeframe=timeframe,
            responsible_party=responsible_party
        )
        
        self.mitigations[mitigation.mitigation_id] = mitigation
        
        # Add to risk event
        self.risk_events[risk_id].mitigation_strategies.append(strategy)
        
        logger.info(f"Created mitigation: {strategy} for risk {risk_id}")
        return mitigation
    
    def resolve_risk(self, risk_id: str, resolved_by: str) -> bool:
        """Resolve a risk event."""
        if risk_id not in self.risk_events:
            return False
        
        risk_event = self.risk_events[risk_id]
        risk_event.status = "resolved"
        risk_event.resolved_at = datetime.now(timezone.utc)
        risk_event.resolved_by = resolved_by
        
        logger.info(f"Risk resolved: {risk_id} by {resolved_by}")
        return True
    
    def get_active_risks(self, category: Optional[RiskCategory] = None) -> List[RiskEvent]:
        """Get active risk events."""
        risks = [risk for risk in self.risk_events.values() if risk.status == "active"]
        
        if category:
            risks = [risk for risk in risks if risk.category == category]
        
        return sorted(risks, key=lambda r: r.risk_score, reverse=True)
    
    def get_risk_statistics(self) -> Dict[str, Any]:
        """Get risk assessment statistics."""
        total_risks = len(self.risk_events)
        active_risks = len([r for r in self.risk_events.values() if r.status == "active"])
        
        # Risk level distribution
        level_counts = {}
        for level in RiskLevel:
            level_counts[level.value] = len([
                r for r in self.risk_events.values() 
                if r.level == level and r.status == "active"
            ])
        
        # Risk category distribution
        category_counts = {}
        for category in RiskCategory:
            category_counts[category.value] = len([
                r for r in self.risk_events.values() 
                if r.category == category and r.status == "active"
            ])
        
        # Average risk scores
        active_risk_scores = [r.risk_score for r in self.risk_events.values() if r.status == "active"]
        avg_risk_score = sum(active_risk_scores) / len(active_risk_scores) if active_risk_scores else 0.0
        
        return {
            'total_risks': total_risks,
            'active_risks': active_risks,
            'resolved_risks': len([r for r in self.risk_events.values() if r.status == "resolved"]),
            'risk_level_distribution': level_counts,
            'risk_category_distribution': category_counts,
            'average_risk_score': avg_risk_score,
            'total_mitigations': len(self.mitigations),
            'completed_mitigations': len([m for m in self.mitigations.values() if m.status == "completed"])
        }
