"""
Bias Detection and Fairness Monitoring system for ML models.
Provides comprehensive bias assessment and fairness constraint monitoring.
"""

import time
import uuid
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
import json

logger = logging.getLogger(__name__)


class BiasMetric(Enum):
    """Bias and fairness metrics."""
    DEMOGRAPHIC_PARITY = "demographic_parity"
    EQUALIZED_ODDS = "equalized_odds"
    EQUAL_OPPORTUNITY = "equal_opportunity"
    DISPARATE_IMPACT = "disparate_impact"
    STATISTICAL_PARITY = "statistical_parity"
    PREDICTIVE_PARITY = "predictive_parity"
    CALIBRATION = "calibration"
    INDIVIDUAL_FAIRNESS = "individual_fairness"


class FairnessConstraint(Enum):
    """Fairness constraints for model optimization."""
    DEMOGRAPHIC_PARITY_CONSTRAINT = "demographic_parity_constraint"
    EQUALIZED_ODDS_CONSTRAINT = "equalized_odds_constraint"
    EQUAL_OPPORTUNITY_CONSTRAINT = "equal_opportunity_constraint"
    DISPARATE_IMPACT_CONSTRAINT = "disparate_impact_constraint"


@dataclass
class BiasReport:
    """Container for bias assessment report."""
    report_id: str
    model_name: str
    model_version: str
    generated_at: datetime
    protected_attributes: List[str]
    bias_metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)
    fairness_assessment: str = "pending"  # "fair", "biased", "unfair", "pending"
    bias_severity: str = "none"  # "none", "low", "medium", "high", "critical"
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'report_id': self.report_id,
            'model_name': self.model_name,
            'model_version': self.model_version,
            'generated_at': self.generated_at.isoformat(),
            'protected_attributes': self.protected_attributes,
            'bias_metrics': self.bias_metrics,
            'fairness_assessment': self.fairness_assessment,
            'bias_severity': self.bias_severity,
            'recommendations': self.recommendations,
            'metadata': self.metadata
        }


class BiasDetector:
    """
    Bias detection and fairness monitoring system for ML models.
    """
    
    def __init__(self):
        self.bias_reports: Dict[str, BiasReport] = {}
        self.fairness_thresholds: Dict[BiasMetric, float] = {
            BiasMetric.DEMOGRAPHIC_PARITY: 0.8,  # 80% rule
            BiasMetric.EQUALIZED_ODDS: 0.8,
            BiasMetric.EQUAL_OPPORTUNITY: 0.8,
            BiasMetric.DISPARATE_IMPACT: 0.8,
            BiasMetric.STATISTICAL_PARITY: 0.8,
            BiasMetric.PREDICTIVE_PARITY: 0.8,
            BiasMetric.CALIBRATION: 0.8,
            BiasMetric.INDIVIDUAL_FAIRNESS: 0.8
        }
        
        logger.info("Initialized bias detector")
    
    def assess_bias(self,
                   model_name: str,
                   model_version: str,
                   predictions: np.ndarray,
                   ground_truth: np.ndarray,
                   protected_attributes: Dict[str, np.ndarray],
                   metadata: Optional[Dict[str, Any]] = None) -> BiasReport:
        """Assess bias in model predictions."""
        
        report_id = f"bias-report-{int(time.time())}-{uuid.uuid4().hex[:8]}"
        
        # Calculate bias metrics for each protected attribute
        bias_metrics = {}
        protected_attr_names = list(protected_attributes.keys())
        
        for attr_name, attr_values in protected_attributes.items():
            attr_metrics = self._calculate_bias_metrics(
                predictions, ground_truth, attr_values
            )
            bias_metrics[attr_name] = attr_metrics
        
        # Determine overall fairness assessment
        fairness_assessment, bias_severity = self._assess_overall_fairness(bias_metrics)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(bias_metrics, bias_severity)
        
        # Create bias report
        report = BiasReport(
            report_id=report_id,
            model_name=model_name,
            model_version=model_version,
            generated_at=datetime.now(timezone.utc),
            protected_attributes=protected_attr_names,
            bias_metrics=bias_metrics,
            fairness_assessment=fairness_assessment,
            bias_severity=bias_severity,
            recommendations=recommendations,
            metadata=metadata or {}
        )
        
        # Store report
        self.bias_reports[report_id] = report
        
        logger.info(f"Bias assessment completed for {model_name}:{model_version} - {fairness_assessment}")
        return report
    
    def _calculate_bias_metrics(self,
                               predictions: np.ndarray,
                               ground_truth: np.ndarray,
                               protected_attr: np.ndarray) -> Dict[str, float]:
        """Calculate bias metrics for a protected attribute."""
        metrics = {}
        
        # Get unique groups in protected attribute
        unique_groups = np.unique(protected_attr)
        
        if len(unique_groups) < 2:
            logger.warning("Protected attribute has less than 2 groups")
            return metrics
        
        # Calculate metrics for each pair of groups
        for i, group_a in enumerate(unique_groups):
            for group_b in unique_groups[i+1:]:
                mask_a = protected_attr == group_a
                mask_b = protected_attr == group_b
                
                pred_a = predictions[mask_a]
                pred_b = predictions[mask_b]
                truth_a = ground_truth[mask_a]
                truth_b = ground_truth[mask_b]
                
                if len(pred_a) == 0 or len(pred_b) == 0:
                    continue
                
                # Calculate demographic parity
                dp = self._demographic_parity(pred_a, pred_b)
                metrics[f"demographic_parity_{group_a}_vs_{group_b}"] = dp
                
                # Calculate equalized odds
                eo = self._equalized_odds(pred_a, pred_b, truth_a, truth_b)
                metrics[f"equalized_odds_{group_a}_vs_{group_b}"] = eo
                
                # Calculate equal opportunity
                eopp = self._equal_opportunity(pred_a, pred_b, truth_a, truth_b)
                metrics[f"equal_opportunity_{group_a}_vs_{group_b}"] = eopp
                
                # Calculate disparate impact
                di = self._disparate_impact(pred_a, pred_b)
                metrics[f"disparate_impact_{group_a}_vs_{group_b}"] = di
                
                # Calculate statistical parity
                sp = self._statistical_parity(pred_a, pred_b)
                metrics[f"statistical_parity_{group_a}_vs_{group_b}"] = sp
                
                # Calculate predictive parity
                pp = self._predictive_parity(pred_a, pred_b, truth_a, truth_b)
                metrics[f"predictive_parity_{group_a}_vs_{group_b}"] = pp
        
        return metrics
    
    def _demographic_parity(self, pred_a: np.ndarray, pred_b: np.ndarray) -> float:
        """Calculate demographic parity between two groups."""
        rate_a = np.mean(pred_a > 0.5)  # Assuming binary classification
        rate_b = np.mean(pred_b > 0.5)
        
        if rate_b == 0:
            return 1.0 if rate_a == 0 else 0.0
        
        return min(rate_a / rate_b, rate_b / rate_a)
    
    def _equalized_odds(self,
                       pred_a: np.ndarray, pred_b: np.ndarray,
                       truth_a: np.ndarray, truth_b: np.ndarray) -> float:
        """Calculate equalized odds between two groups."""
        # True Positive Rate
        tpr_a = self._true_positive_rate(pred_a, truth_a)
        tpr_b = self._true_positive_rate(pred_b, truth_b)
        
        # False Positive Rate
        fpr_a = self._false_positive_rate(pred_a, truth_a)
        fpr_b = self._false_positive_rate(pred_b, truth_b)
        
        # Equalized odds is the minimum of TPR ratio and FPR ratio
        tpr_ratio = min(tpr_a / tpr_b, tpr_b / tpr_a) if tpr_b > 0 and tpr_a > 0 else 1.0
        fpr_ratio = min(fpr_a / fpr_b, fpr_b / fpr_a) if fpr_b > 0 and fpr_a > 0 else 1.0
        
        return min(tpr_ratio, fpr_ratio)
    
    def _equal_opportunity(self,
                          pred_a: np.ndarray, pred_b: np.ndarray,
                          truth_a: np.ndarray, truth_b: np.ndarray) -> float:
        """Calculate equal opportunity between two groups."""
        tpr_a = self._true_positive_rate(pred_a, truth_a)
        tpr_b = self._true_positive_rate(pred_b, truth_b)
        
        if tpr_b == 0:
            return 1.0 if tpr_a == 0 else 0.0
        
        return min(tpr_a / tpr_b, tpr_b / tpr_a)
    
    def _disparate_impact(self, pred_a: np.ndarray, pred_b: np.ndarray) -> float:
        """Calculate disparate impact between two groups."""
        rate_a = np.mean(pred_a > 0.5)
        rate_b = np.mean(pred_b > 0.5)
        
        if rate_b == 0:
            return 1.0 if rate_a == 0 else 0.0
        
        return min(rate_a / rate_b, rate_b / rate_a)
    
    def _statistical_parity(self, pred_a: np.ndarray, pred_b: np.ndarray) -> float:
        """Calculate statistical parity between two groups."""
        return self._demographic_parity(pred_a, pred_b)  # Same as demographic parity
    
    def _predictive_parity(self,
                          pred_a: np.ndarray, pred_b: np.ndarray,
                          truth_a: np.ndarray, truth_b: np.ndarray) -> float:
        """Calculate predictive parity between two groups."""
        # Positive Predictive Value
        ppv_a = self._positive_predictive_value(pred_a, truth_a)
        ppv_b = self._positive_predictive_value(pred_b, truth_b)
        
        if ppv_b == 0:
            return 1.0 if ppv_a == 0 else 0.0
        
        return min(ppv_a / ppv_b, ppv_b / ppv_a)
    
    def _true_positive_rate(self, predictions: np.ndarray, ground_truth: np.ndarray) -> float:
        """Calculate true positive rate."""
        tp = np.sum((predictions > 0.5) & (ground_truth == 1))
        fn = np.sum((predictions <= 0.5) & (ground_truth == 1))
        
        return tp / (tp + fn) if (tp + fn) > 0 else 0.0
    
    def _false_positive_rate(self, predictions: np.ndarray, ground_truth: np.ndarray) -> float:
        """Calculate false positive rate."""
        fp = np.sum((predictions > 0.5) & (ground_truth == 0))
        tn = np.sum((predictions <= 0.5) & (ground_truth == 0))
        
        return fp / (fp + tn) if (fp + tn) > 0 else 0.0
    
    def _positive_predictive_value(self, predictions: np.ndarray, ground_truth: np.ndarray) -> float:
        """Calculate positive predictive value (precision)."""
        tp = np.sum((predictions > 0.5) & (ground_truth == 1))
        fp = np.sum((predictions > 0.5) & (ground_truth == 0))
        
        return tp / (tp + fp) if (tp + fp) > 0 else 0.0
    
    def _assess_overall_fairness(self, bias_metrics: Dict[str, Dict[str, float]]) -> Tuple[str, str]:
        """Assess overall fairness based on bias metrics."""
        if not bias_metrics:
            return "pending", "none"
        
        # Collect all metric values
        all_metrics = []
        for attr_name, metrics in bias_metrics.items():
            for metric_name, value in metrics.items():
                if not np.isnan(value) and not np.isinf(value):
                    all_metrics.append(value)
        
        if not all_metrics:
            return "pending", "none"
        
        # Calculate average fairness score
        avg_fairness = np.mean(all_metrics)
        min_fairness = np.min(all_metrics)
        
        # Determine bias severity based on minimum fairness score
        if min_fairness >= 0.8:
            bias_severity = "none"
            fairness_assessment = "fair"
        elif min_fairness >= 0.6:
            bias_severity = "low"
            fairness_assessment = "fair"
        elif min_fairness >= 0.4:
            bias_severity = "medium"
            fairness_assessment = "biased"
        elif min_fairness >= 0.2:
            bias_severity = "high"
            fairness_assessment = "biased"
        else:
            bias_severity = "critical"
            fairness_assessment = "unfair"
        
        return fairness_assessment, bias_severity
    
    def _generate_recommendations(self,
                                 bias_metrics: Dict[str, Dict[str, float]],
                                 bias_severity: str) -> List[str]:
        """Generate bias mitigation recommendations."""
        recommendations = []
        
        if bias_severity == "none":
            recommendations.append("Model shows good fairness characteristics. Continue monitoring.")
            return recommendations
        
        recommendations.append("Consider implementing bias mitigation techniques:")
        
        if bias_severity in ["medium", "high", "critical"]:
            recommendations.extend([
                "Use fairness-aware algorithms (e.g., Fairlearn, AIF360)",
                "Implement preprocessing techniques to reduce bias in training data",
                "Apply in-processing constraints during model training",
                "Use post-processing techniques to adjust predictions"
            ])
        
        if bias_severity in ["high", "critical"]:
            recommendations.extend([
                "Conduct comprehensive bias audit with domain experts",
                "Review data collection and labeling processes",
                "Consider alternative model architectures",
                "Implement human-in-the-loop validation for critical decisions"
            ])
        
        # Add specific recommendations based on problematic metrics
        for attr_name, metrics in bias_metrics.items():
            problematic_metrics = [
                name for name, value in metrics.items()
                if value < 0.6 and not np.isnan(value) and not np.isinf(value)
            ]
            
            if problematic_metrics:
                recommendations.append(f"Address bias issues for {attr_name}: {', '.join(problematic_metrics)}")
        
        return recommendations
    
    def get_bias_report(self, report_id: str) -> Optional[BiasReport]:
        """Get a specific bias report."""
        return self.bias_reports.get(report_id)
    
    def list_bias_reports(self, model_name: Optional[str] = None) -> List[BiasReport]:
        """List bias reports, optionally filtered by model name."""
        reports = list(self.bias_reports.values())
        
        if model_name:
            reports = [r for r in reports if r.model_name == model_name]
        
        return sorted(reports, key=lambda r: r.generated_at, reverse=True)
    
    def get_bias_statistics(self) -> Dict[str, Any]:
        """Get bias detection statistics."""
        total_reports = len(self.bias_reports)
        
        # Fairness assessment distribution
        assessment_counts = {}
        for assessment in ["fair", "biased", "unfair", "pending"]:
            assessment_counts[assessment] = len([
                r for r in self.bias_reports.values() if r.fairness_assessment == assessment
            ])
        
        # Bias severity distribution
        severity_counts = {}
        for severity in ["none", "low", "medium", "high", "critical"]:
            severity_counts[severity] = len([
                r for r in self.bias_reports.values() if r.bias_severity == severity
            ])
        
        # Protected attributes coverage
        all_attributes = set()
        for report in self.bias_reports.values():
            all_attributes.update(report.protected_attributes)
        
        return {
            'total_reports': total_reports,
            'fairness_assessment_distribution': assessment_counts,
            'bias_severity_distribution': severity_counts,
            'protected_attributes_covered': list(all_attributes),
            'total_protected_attributes': len(all_attributes),
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
    
    def update_fairness_threshold(self, metric: BiasMetric, threshold: float) -> None:
        """Update fairness threshold for a specific metric."""
        self.fairness_thresholds[metric] = threshold
        logger.info(f"Updated fairness threshold for {metric.value}: {threshold}")
    
    def check_fairness_constraint(self,
                                 constraint: FairnessConstraint,
                                 predictions: np.ndarray,
                                 ground_truth: np.ndarray,
                                 protected_attr: np.ndarray,
                                 threshold: float = 0.8) -> bool:
        """Check if a fairness constraint is satisfied."""
        
        if constraint == FairnessConstraint.DEMOGRAPHIC_PARITY_CONSTRAINT:
            return self._check_demographic_parity_constraint(predictions, protected_attr, threshold)
        elif constraint == FairnessConstraint.EQUALIZED_ODDS_CONSTRAINT:
            return self._check_equalized_odds_constraint(predictions, ground_truth, protected_attr, threshold)
        elif constraint == FairnessConstraint.EQUAL_OPPORTUNITY_CONSTRAINT:
            return self._check_equal_opportunity_constraint(predictions, ground_truth, protected_attr, threshold)
        elif constraint == FairnessConstraint.DISPARATE_IMPACT_CONSTRAINT:
            return self._check_disparate_impact_constraint(predictions, protected_attr, threshold)
        else:
            logger.warning(f"Unknown fairness constraint: {constraint}")
            return True
    
    def _check_demographic_parity_constraint(self,
                                           predictions: np.ndarray,
                                           protected_attr: np.ndarray,
                                           threshold: float) -> bool:
        """Check demographic parity constraint."""
        unique_groups = np.unique(protected_attr)
        if len(unique_groups) < 2:
            return True
        
        rates = []
        for group in unique_groups:
            mask = protected_attr == group
            rate = np.mean(predictions[mask] > 0.5)
            rates.append(rate)
        
        min_rate = min(rates)
        max_rate = max(rates)
        
        return min_rate / max_rate >= threshold if max_rate > 0 else True
    
    def _check_equalized_odds_constraint(self,
                                       predictions: np.ndarray,
                                       ground_truth: np.ndarray,
                                       protected_attr: np.ndarray,
                                       threshold: float) -> bool:
        """Check equalized odds constraint."""
        unique_groups = np.unique(protected_attr)
        if len(unique_groups) < 2:
            return True
        
        group_metrics = []
        for group in unique_groups:
            mask = protected_attr == group
            tpr = self._true_positive_rate(predictions[mask], ground_truth[mask])
            fpr = self._false_positive_rate(predictions[mask], ground_truth[mask])
            group_metrics.append((tpr, fpr))
        
        # Check TPR and FPR differences
        tprs = [m[0] for m in group_metrics]
        fprs = [m[1] for m in group_metrics]
        
        tpr_ratio = min(tprs) / max(tprs) if max(tprs) > 0 else 1.0
        fpr_ratio = min(fprs) / max(fprs) if max(fprs) > 0 else 1.0
        
        return min(tpr_ratio, fpr_ratio) >= threshold
    
    def _check_equal_opportunity_constraint(self,
                                          predictions: np.ndarray,
                                          ground_truth: np.ndarray,
                                          protected_attr: np.ndarray,
                                          threshold: float) -> bool:
        """Check equal opportunity constraint."""
        unique_groups = np.unique(protected_attr)
        if len(unique_groups) < 2:
            return True
        
        tprs = []
        for group in unique_groups:
            mask = protected_attr == group
            tpr = self._true_positive_rate(predictions[mask], ground_truth[mask])
            tprs.append(tpr)
        
        return min(tprs) / max(tprs) >= threshold if max(tprs) > 0 else True
    
    def _check_disparate_impact_constraint(self,
                                         predictions: np.ndarray,
                                         protected_attr: np.ndarray,
                                         threshold: float) -> bool:
        """Check disparate impact constraint."""
        return self._check_demographic_parity_constraint(predictions, protected_attr, threshold)
