"""
Data quality scoring system with comprehensive metrics and grading.
Provides quality assessment and improvement recommendations.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np


@dataclass
class QualityScore:
    """Comprehensive data quality score result."""
    overall_score: float  # 0-100
    quality_grade: str  # A, B, C, D, F
    layer_scores: Dict[str, float]  # Scores for each validation layer
    improvement_suggestions: List[str]
    is_acceptable: bool  # Whether quality meets minimum standards
    quality_breakdown: Dict[str, float]  # Detailed breakdown by quality dimensions


class DataQualityScorer:
    """
    Comprehensive data quality scoring system.
    
    Features:
    - Multi-dimensional quality assessment
    - Weighted scoring across validation layers
    - Quality grading (A-F scale)
    - Improvement recommendations
    - Acceptability thresholds
    - Quality trend analysis
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # Quality dimensions and weights
        self.quality_weights = self.config.get("quality_weights", {
            'schema_validation': 0.20,
            'statistical_validation': 0.25,
            'outlier_detection': 0.20,
            'anomaly_detection': 0.15,
            'cross_validation': 0.10,
            'consistency_check': 0.10
        })
        
        # Quality thresholds
        self.quality_thresholds = self.config.get("quality_thresholds", {
            'acceptable': 70.0,  # Minimum acceptable score
            'good': 80.0,        # Good quality threshold
            'excellent': 90.0    # Excellent quality threshold
        })
        
        # Grade boundaries
        self.grade_boundaries = self.config.get("grade_boundaries", {
            'A': 90.0,
            'B': 80.0,
            'C': 70.0,
            'D': 60.0,
            'F': 0.0
        })
        
        # Quality dimension weights for breakdown
        self.dimension_weights = self.config.get("dimension_weights", {
            'completeness': 0.25,    # Data completeness
            'accuracy': 0.25,        # Data accuracy
            'consistency': 0.20,     # Data consistency
            'timeliness': 0.15,      # Data timeliness
            'validity': 0.15         # Data validity
        })
        
    def calculate_quality_score(self, validation_results: List) -> QualityScore:
        """
        Calculate comprehensive data quality score.
        
        Args:
            validation_results: List of validation layer results
            
        Returns:
            Comprehensive quality score with recommendations
        """
        # Extract scores from each validation layer
        layer_scores = {}
        
        for result in validation_results:
            layer_name = result.layer_name
            layer_score = result.confidence_score
            
            # Apply layer-specific adjustments
            adjusted_score = self._adjust_score_for_layer(layer_name, layer_score, result)
            layer_scores[layer_name] = adjusted_score
        
        # Calculate weighted overall score
        overall_score = self._calculate_weighted_score(layer_scores)
        
        # Determine quality grade
        quality_grade = self._determine_quality_grade(overall_score)
        
        # Calculate quality breakdown by dimensions
        quality_breakdown = self._calculate_quality_breakdown(validation_results)
        
        # Generate improvement suggestions
        improvements = self._suggest_improvements(layer_scores, quality_breakdown)
        
        # Determine acceptability
        is_acceptable = overall_score >= self.quality_thresholds['acceptable']
        
        return QualityScore(
            overall_score=overall_score,
            quality_grade=quality_grade,
            layer_scores=layer_scores,
            improvement_suggestions=improvements,
            is_acceptable=is_acceptable,
            quality_breakdown=quality_breakdown
        )
    
    def _adjust_score_for_layer(self, layer_name: str, layer_score: float, result) -> float:
        """Apply layer-specific adjustments to scores."""
        adjusted_score = layer_score
        
        # Schema validation adjustments
        if layer_name == 'schema_validation':
            # Penalize heavily for schema issues
            if not result.passed:
                adjusted_score *= 0.5  # 50% penalty for schema failures
        
        # Statistical validation adjustments
        elif layer_name == 'statistical_validation':
            # Check for critical statistical issues
            critical_issues = ['negative prices', 'infinite values', 'empty dataset']
            has_critical_issues = any(issue in str(result.issues).lower() for issue in critical_issues)
            
            if has_critical_issues:
                adjusted_score *= 0.3  # 70% penalty for critical issues
        
        # Outlier detection adjustments
        elif layer_name == 'outlier_detection':
            # Moderate penalty for high outlier rates
            if hasattr(result, 'metadata') and result.metadata:
                outlier_pct = result.metadata.get('outlier_percentage', 0)
                if outlier_pct > 0.05:  # More than 5% outliers
                    adjusted_score *= 0.8  # 20% penalty
        
        # Anomaly detection adjustments
        elif layer_name == 'anomaly_detection':
            # Penalize for data gaps and suspicious patterns
            if hasattr(result, 'metadata') and result.metadata:
                data_gaps = result.metadata.get('data_gaps', 0)
                if data_gaps > 0:
                    adjusted_score *= 0.9  # 10% penalty per gap
        
        # Cross-validation adjustments
        elif layer_name == 'cross_validation':
            # Bonus for good cross-validation results
            if result.passed and layer_score > 0.9:
                adjusted_score = min(1.0, adjusted_score * 1.1)  # 10% bonus
        
        return max(0.0, min(1.0, adjusted_score))
    
    def _calculate_weighted_score(self, layer_scores: Dict[str, float]) -> float:
        """Calculate weighted overall score."""
        weighted_score = 0.0
        total_weight = 0.0
        
        for layer, score in layer_scores.items():
            weight = self.quality_weights.get(layer, 1.0)
            weighted_score += score * weight
            total_weight += weight
        
        # Convert to 0-100 scale
        overall_score = (weighted_score / total_weight) * 100 if total_weight > 0 else 0.0
        
        return overall_score
    
    def _determine_quality_grade(self, score: float) -> str:
        """Determine quality grade based on score."""
        if score >= self.grade_boundaries['A']:
            return 'A'
        elif score >= self.grade_boundaries['B']:
            return 'B'
        elif score >= self.grade_boundaries['C']:
            return 'C'
        elif score >= self.grade_boundaries['D']:
            return 'D'
        else:
            return 'F'
    
    def _calculate_quality_breakdown(self, validation_results: List) -> Dict[str, float]:
        """Calculate quality breakdown by dimensions."""
        breakdown = {
            'completeness': 0.0,
            'accuracy': 0.0,
            'consistency': 0.0,
            'timeliness': 0.0,
            'validity': 0.0
        }
        
        # Map validation layers to quality dimensions
        for result in validation_results:
            layer_name = result.layer_name
            score = result.confidence_score
            
            if layer_name == 'schema_validation':
                breakdown['completeness'] += score * 0.4  # Schema affects completeness
                breakdown['validity'] += score * 0.6      # Schema affects validity
            
            elif layer_name == 'statistical_validation':
                breakdown['accuracy'] += score * 0.5      # Statistical checks affect accuracy
                breakdown['completeness'] += score * 0.3  # Missing data affects completeness
                breakdown['validity'] += score * 0.2      # Statistical validity
            
            elif layer_name == 'outlier_detection':
                breakdown['accuracy'] += score * 0.7      # Outliers affect accuracy
                breakdown['consistency'] += score * 0.3   # Outliers affect consistency
            
            elif layer_name == 'anomaly_detection':
                breakdown['accuracy'] += score * 0.4      # Anomalies affect accuracy
                breakdown['consistency'] += score * 0.4   # Anomalies affect consistency
                breakdown['timeliness'] += score * 0.2    # Data gaps affect timeliness
            
            elif layer_name == 'cross_validation':
                breakdown['accuracy'] += score * 0.6      # Cross-validation affects accuracy
                breakdown['validity'] += score * 0.4      # Cross-validation affects validity
            
            elif layer_name == 'consistency_check':
                breakdown['consistency'] += score * 0.8   # Consistency checks
                breakdown['validity'] += score * 0.2      # Consistency affects validity
        
        # Normalize scores
        for dimension in breakdown:
            breakdown[dimension] = min(100.0, breakdown[dimension] * 100)
        
        return breakdown
    
    def _suggest_improvements(self, layer_scores: Dict[str, float], 
                            quality_breakdown: Dict[str, float]) -> List[str]:
        """Generate improvement suggestions based on quality analysis."""
        suggestions = []
        
        # Overall quality suggestions
        overall_score = sum(layer_scores.values()) / len(layer_scores) * 100
        
        if overall_score < 50:
            suggestions.append("Data quality is critically low - immediate attention required")
        elif overall_score < 70:
            suggestions.append("Data quality needs significant improvement")
        elif overall_score < 80:
            suggestions.append("Data quality is acceptable but could be improved")
        elif overall_score < 90:
            suggestions.append("Data quality is good with room for optimization")
        else:
            suggestions.append("Data quality is excellent - maintain current standards")
        
        # Layer-specific suggestions
        for layer, score in layer_scores.items():
            if score < 0.6:  # Low score threshold
                if layer == 'schema_validation':
                    suggestions.append("Fix data schema issues: ensure proper column types and structure")
                elif layer == 'statistical_validation':
                    suggestions.append("Address statistical issues: check for missing data and extreme values")
                elif layer == 'outlier_detection':
                    suggestions.append("Investigate outliers: verify extreme values or clean data")
                elif layer == 'anomaly_detection':
                    suggestions.append("Review data anomalies: check for suspicious patterns and gaps")
                elif layer == 'cross_validation':
                    suggestions.append("Improve cross-validation: verify data against multiple sources")
                elif layer == 'consistency_check':
                    suggestions.append("Fix consistency issues: resolve internal data contradictions")
        
        # Dimension-specific suggestions
        for dimension, score in quality_breakdown.items():
            if score < 60:  # Low dimension score
                if dimension == 'completeness':
                    suggestions.append("Improve data completeness: reduce missing values and gaps")
                elif dimension == 'accuracy':
                    suggestions.append("Enhance data accuracy: address outliers and measurement errors")
                elif dimension == 'consistency':
                    suggestions.append("Strengthen data consistency: resolve conflicting values")
                elif dimension == 'timeliness':
                    suggestions.append("Improve data timeliness: reduce delays and gaps")
                elif dimension == 'validity':
                    suggestions.append("Ensure data validity: verify against business rules and constraints")
        
        # Remove duplicates and return
        return list(set(suggestions))
    
    def get_quality_trend(self, historical_scores: List[float]) -> Dict[str, any]:
        """
        Analyze quality trend over time.
        
        Args:
            historical_scores: List of quality scores over time
            
        Returns:
            Trend analysis results
        """
        if len(historical_scores) < 2:
            return {
                'trend_direction': 'insufficient_data',
                'trend_strength': 0.0,
                'trend_consistency': 0.0,
                'recent_trend': 0.0,
                'volatility': 0.0
            }
        
        scores = np.array(historical_scores)
        
        # Calculate trend direction and strength
        x = np.arange(len(scores))
        slope, intercept = np.polyfit(x, scores, 1)
        
        # Determine trend direction
        if abs(slope) < 0.1:
            trend_direction = 'stable'
        elif slope > 0:
            trend_direction = 'improving'
        else:
            trend_direction = 'declining'
        
        # Calculate trend strength (R-squared)
        y_pred = slope * x + intercept
        ss_res = np.sum((scores - y_pred) ** 2)
        ss_tot = np.sum((scores - np.mean(scores)) ** 2)
        trend_strength = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        # Calculate trend consistency (how consistent the trend is)
        differences = np.diff(scores)
        trend_consistency = 1 - (np.std(differences) / np.mean(np.abs(differences))) if np.mean(np.abs(differences)) > 0 else 1
        
        # Recent trend (last 25% of data)
        recent_length = max(1, len(scores) // 4)
        recent_scores = scores[-recent_length:]
        recent_slope = np.polyfit(np.arange(len(recent_scores)), recent_scores, 1)[0]
        
        # Volatility
        volatility = np.std(scores)
        
        return {
            'trend_direction': trend_direction,
            'trend_strength': trend_strength,
            'trend_consistency': trend_consistency,
            'recent_trend': recent_slope,
            'volatility': volatility,
            'average_score': np.mean(scores),
            'score_range': np.max(scores) - np.min(scores)
        }
    
    def generate_quality_report(self, quality_score: QualityScore, 
                              historical_trend: Optional[Dict] = None) -> str:
        """Generate human-readable quality report."""
        report = []
        report.append("=" * 60)
        report.append("DATA QUALITY REPORT")
        report.append("=" * 60)
        
        # Overall assessment
        report.append(f"Overall Quality Score: {quality_score.overall_score:.1f}/100")
        report.append(f"Quality Grade: {quality_score.quality_grade}")
        report.append(f"Acceptable: {'Yes' if quality_score.is_acceptable else 'No'}")
        report.append("")
        
        # Layer scores
        report.append("Validation Layer Scores:")
        for layer, score in quality_score.layer_scores.items():
            score_100 = score * 100
            report.append(f"  {layer.replace('_', ' ').title()}: {score_100:.1f}/100")
        report.append("")
        
        # Quality breakdown
        report.append("Quality Dimension Breakdown:")
        for dimension, score in quality_score.quality_breakdown.items():
            report.append(f"  {dimension.title()}: {score:.1f}/100")
        report.append("")
        
        # Improvement suggestions
        if quality_score.improvement_suggestions:
            report.append("Improvement Suggestions:")
            for i, suggestion in enumerate(quality_score.improvement_suggestions, 1):
                report.append(f"  {i}. {suggestion}")
            report.append("")
        
        # Historical trend
        if historical_trend:
            report.append("Quality Trend Analysis:")
            report.append(f"  Trend Direction: {historical_trend['trend_direction'].title()}")
            report.append(f"  Trend Strength: {historical_trend['trend_strength']:.2f}")
            report.append(f"  Recent Trend: {historical_trend['recent_trend']:+.2f} points/period")
            report.append(f"  Volatility: {historical_trend['volatility']:.2f}")
            report.append("")
        
        report.append("=" * 60)
        
        return "\n".join(report)
