"""
Drift Detection for ML trading systems.
Detects concept drift and data drift in real-time.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from collections import deque
import logging

logger = logging.getLogger(__name__)


@dataclass
class DriftAlert:
    """Container for drift detection alerts."""
    timestamp: datetime
    drift_type: str  # 'concept_drift' or 'data_drift'
    feature_name: Optional[str]
    severity: str  # 'low', 'medium', 'high', 'critical'
    score: float
    threshold: float
    message: str
    model_name: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'drift_type': self.drift_type,
            'feature_name': self.feature_name,
            'severity': self.severity,
            'score': self.score,
            'threshold': self.threshold,
            'message': self.message,
            'model_name': self.model_name
        }


class ConceptDriftDetector:
    """
    Detects concept drift in model predictions vs actual outcomes.
    """
    
    def __init__(self, 
                 model_name: str,
                 window_size: int = 500,
                 significance_level: float = 0.05,
                 enable_alerts: bool = True):
        """
        Initialize concept drift detector.
        
        Args:
            model_name: Name of the model being monitored
            window_size: Size of sliding window for drift detection
            significance_level: Statistical significance level for drift tests
            enable_alerts: Whether to generate drift alerts
        """
        self.model_name = model_name
        self.window_size = window_size
        self.significance_level = significance_level
        self.enable_alerts = enable_alerts
        
        # Prediction and outcome tracking
        self.predictions: deque = deque(maxlen=window_size)
        self.outcomes: deque = deque(maxlen=window_size)
        self.timestamps: deque = deque(maxlen=window_size)
        
        # Drift detection state
        self.baseline_accuracy: Optional[float] = None
        self.baseline_samples = 100  # Minimum samples for baseline
        self.drift_alerts: List[DriftAlert] = []
        
        # Statistical tests
        self.ks_test_enabled = True
        self.chi_square_test_enabled = True
        self.performance_drift_enabled = True
        
        logger.info(f"Initialized concept drift detector for model: {model_name}")
    
    def add_prediction(self, 
                      prediction: Union[float, int, bool],
                      actual: Union[float, int, bool],
                      timestamp: Optional[datetime] = None) -> Optional[DriftAlert]:
        """
        Add a prediction-outcome pair for drift detection.
        
        Args:
            prediction: Model prediction
            actual: Actual outcome
            timestamp: Timestamp of prediction
            
        Returns:
            DriftAlert if drift detected, None otherwise
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        self.predictions.append(prediction)
        self.outcomes.append(actual)
        self.timestamps.append(timestamp)
        
        # Check for concept drift if we have enough samples
        if len(self.predictions) >= self.baseline_samples:
            return self._detect_concept_drift()
        
        return None
    
    def _detect_concept_drift(self) -> Optional[DriftAlert]:
        """Detect concept drift using multiple statistical tests."""
        if len(self.predictions) < self.baseline_samples:
            return None
        
        alerts = []
        
        # 1. Performance-based drift detection
        if self.performance_drift_enabled:
            perf_alert = self._detect_performance_drift()
            if perf_alert:
                alerts.append(perf_alert)
        
        # 2. Prediction distribution drift
        if self.ks_test_enabled:
            ks_alert = self._detect_prediction_drift_ks()
            if ks_alert:
                alerts.append(ks_alert)
        
        # 3. Classification accuracy drift (for classification models)
        if self.chi_square_test_enabled:
            chi_alert = self._detect_accuracy_drift_chi_square()
            if chi_alert:
                alerts.append(chi_alert)
        
        # Return the most severe alert
        if alerts:
            # Sort by severity (critical > high > medium > low)
            severity_order = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
            alerts.sort(key=lambda x: severity_order.get(x.severity, 0), reverse=True)
            return alerts[0]
        
        return None
    
    def _detect_performance_drift(self) -> Optional[DriftAlert]:
        """Detect drift based on performance degradation."""
        if len(self.predictions) < 2 * self.baseline_samples:
            return None
        
        # Split into baseline and current windows
        baseline_size = min(self.baseline_samples, len(self.predictions) // 2)
        baseline_preds = list(self.predictions)[:baseline_size]
        baseline_actuals = list(self.outcomes)[:baseline_size]
        current_preds = list(self.predictions)[-baseline_size:]
        current_actuals = list(self.outcomes)[-baseline_size:]
        
        # Calculate accuracy for both windows
        baseline_accuracy = self._calculate_accuracy(baseline_preds, baseline_actuals)
        current_accuracy = self._calculate_accuracy(current_preds, current_actuals)
        
        # Set baseline if not established
        if self.baseline_accuracy is None:
            self.baseline_accuracy = baseline_accuracy
            return None
        
        # Check for significant performance drop
        accuracy_drop = self.baseline_accuracy - current_accuracy
        threshold = 0.05  # 5% accuracy drop threshold
        
        if accuracy_drop > threshold:
            severity = 'critical' if accuracy_drop > 0.15 else 'high'
            return DriftAlert(
                timestamp=datetime.now(timezone.utc),
                drift_type='concept_drift',
                feature_name=None,
                severity=severity,
                score=accuracy_drop,
                threshold=threshold,
                message=f"Performance drift detected: accuracy dropped by {accuracy_drop:.3f}",
                model_name=self.model_name
            )
        
        return None
    
    def _detect_prediction_drift_ks(self) -> Optional[DriftAlert]:
        """Detect drift in prediction distribution using Kolmogorov-Smirnov test."""
        try:
            from scipy import stats
        except ImportError:
            logger.warning("scipy not available for KS test")
            return None
        
        if len(self.predictions) < 2 * self.baseline_samples:
            return None
        
        # Split into baseline and current windows
        baseline_size = min(self.baseline_samples, len(self.predictions) // 2)
        baseline_preds = np.array(list(self.predictions)[:baseline_size], dtype=float)
        current_preds = np.array(list(self.predictions)[-baseline_size:], dtype=float)
        
        # Perform KS test
        ks_statistic, p_value = stats.ks_2samp(baseline_preds, current_preds)
        
        if p_value < self.significance_level:
            severity = 'high' if p_value < 0.01 else 'medium'
            return DriftAlert(
                timestamp=datetime.now(timezone.utc),
                drift_type='concept_drift',
                feature_name='prediction_distribution',
                severity=severity,
                score=ks_statistic,
                threshold=self.significance_level,
                message=f"Prediction distribution drift detected (KS test, p={p_value:.4f})",
                model_name=self.model_name
            )
        
        return None
    
    def _detect_accuracy_drift_chi_square(self) -> Optional[DriftAlert]:
        """Detect drift in classification accuracy using chi-square test."""
        try:
            from scipy import stats
        except ImportError:
            return None
        
        if len(self.predictions) < 2 * self.baseline_samples:
            return None
        
        # Split into baseline and current windows
        baseline_size = min(self.baseline_samples, len(self.predictions) // 2)
        baseline_preds = list(self.predictions)[:baseline_size]
        baseline_actuals = list(self.outcomes)[:baseline_size]
        current_preds = list(self.predictions)[-baseline_size:]
        current_actuals = list(self.outcomes)[-baseline_size:]
        
        # Calculate confusion matrices
        baseline_correct = sum(1 for p, a in zip(baseline_preds, baseline_actuals) if p == a)
        baseline_incorrect = baseline_size - baseline_correct
        current_correct = sum(1 for p, a in zip(current_preds, current_actuals) if p == a)
        current_incorrect = baseline_size - current_correct
        
        # Chi-square test for independence
        contingency_table = np.array([
            [baseline_correct, baseline_incorrect],
            [current_correct, current_incorrect]
        ])
        
        chi2, p_value, _, _ = stats.chi2_contingency(contingency_table)
        
        if p_value < self.significance_level:
            severity = 'high' if p_value < 0.01 else 'medium'
            return DriftAlert(
                timestamp=datetime.now(timezone.utc),
                drift_type='concept_drift',
                feature_name='classification_accuracy',
                severity=severity,
                score=chi2,
                threshold=self.significance_level,
                message=f"Classification accuracy drift detected (chi-square test, p={p_value:.4f})",
                model_name=self.model_name
            )
        
        return None
    
    def _calculate_accuracy(self, predictions: List, actuals: List) -> float:
        """Calculate accuracy for predictions vs actuals."""
        if len(predictions) != len(actuals) or len(predictions) == 0:
            return 0.0
        
        correct = sum(1 for p, a in zip(predictions, actuals) if p == a)
        return correct / len(predictions)
    
    def get_drift_summary(self) -> Dict[str, Any]:
        """Get summary of drift detection status."""
        return {
            'model_name': self.model_name,
            'total_samples': len(self.predictions),
            'baseline_established': self.baseline_accuracy is not None,
            'baseline_accuracy': self.baseline_accuracy,
            'active_alerts': len(self.drift_alerts),
            'window_size': self.window_size,
            'significance_level': self.significance_level
        }


class DataDriftDetector:
    """
    Detects data drift in input features.
    """
    
    def __init__(self, 
                 model_name: str,
                 feature_names: List[str],
                 window_size: int = 1000,
                 significance_level: float = 0.05,
                 enable_alerts: bool = True):
        """
        Initialize data drift detector.
        
        Args:
            model_name: Name of the model being monitored
            feature_names: List of feature names to monitor
            window_size: Size of sliding window for drift detection
            significance_level: Statistical significance level for drift tests
            enable_alerts: Whether to generate drift alerts
        """
        self.model_name = model_name
        self.feature_names = feature_names
        self.window_size = window_size
        self.significance_level = significance_level
        self.enable_alerts = enable_alerts
        
        # Feature data tracking
        self.feature_data: Dict[str, deque] = {
            name: deque(maxlen=window_size) for name in feature_names
        }
        self.timestamps: deque = deque(maxlen=window_size)
        
        # Baseline statistics
        self.baseline_stats: Dict[str, Dict[str, float]] = {}
        self.baseline_samples = 200  # Minimum samples for baseline
        
        # Drift alerts
        self.drift_alerts: List[DriftAlert] = []
        
        logger.info(f"Initialized data drift detector for model: {model_name}, features: {feature_names}")
    
    def add_features(self, 
                    features: Dict[str, float],
                    timestamp: Optional[datetime] = None) -> List[DriftAlert]:
        """
        Add feature values for drift detection.
        
        Args:
            features: Dictionary of feature_name -> value
            timestamp: Timestamp of the data
            
        Returns:
            List of DriftAlert objects if drift detected
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        # Store feature values
        for feature_name, value in features.items():
            if feature_name in self.feature_data:
                self.feature_data[feature_name].append(value)
        
        self.timestamps.append(timestamp)
        
        # Detect drift if we have enough samples
        if len(self.timestamps) >= self.baseline_samples:
            return self._detect_data_drift()
        
        return []
    
    def _detect_data_drift(self) -> List[DriftAlert]:
        """Detect data drift across all monitored features."""
        alerts = []
        
        # Establish baseline if not done
        if not self.baseline_stats:
            self._establish_baseline()
            return alerts
        
        # Check each feature for drift
        for feature_name in self.feature_names:
            feature_alerts = self._detect_feature_drift(feature_name)
            alerts.extend(feature_alerts)
        
        return alerts
    
    def _establish_baseline(self) -> None:
        """Establish baseline statistics for all features."""
        if len(self.timestamps) < self.baseline_samples:
            return
        
        for feature_name in self.feature_names:
            feature_values = list(self.feature_data[feature_name])
            if len(feature_values) >= self.baseline_samples:
                values = np.array(feature_values[:self.baseline_samples], dtype=float)
                
                self.baseline_stats[feature_name] = {
                    'mean': np.mean(values),
                    'std': np.std(values),
                    'min': np.min(values),
                    'max': np.max(values),
                    'median': np.median(values),
                    'q25': np.percentile(values, 25),
                    'q75': np.percentile(values, 75)
                }
        
        logger.info(f"Baseline established for {len(self.baseline_stats)} features")
    
    def _detect_feature_drift(self, feature_name: str) -> List[DriftAlert]:
        """Detect drift for a specific feature."""
        if feature_name not in self.baseline_stats:
            return []
        
        current_values = list(self.feature_data[feature_name])
        if len(current_values) < self.baseline_samples:
            return []
        
        baseline_stats = self.baseline_stats[feature_name]
        current_values = np.array(current_values[-self.baseline_samples:], dtype=float)
        
        alerts = []
        
        # 1. Statistical drift (KS test)
        ks_alert = self._detect_statistical_drift(feature_name, current_values, baseline_stats)
        if ks_alert:
            alerts.append(ks_alert)
        
        # 2. Distribution shift detection
        dist_alert = self._detect_distribution_shift(feature_name, current_values, baseline_stats)
        if dist_alert:
            alerts.append(dist_alert)
        
        # 3. Outlier detection
        outlier_alert = self._detect_outlier_increase(feature_name, current_values, baseline_stats)
        if outlier_alert:
            alerts.append(outlier_alert)
        
        return alerts
    
    def _detect_statistical_drift(self, 
                                  feature_name: str,
                                  current_values: np.ndarray,
                                  baseline_stats: Dict[str, float]) -> Optional[DriftAlert]:
        """Detect statistical drift using KS test."""
        try:
            from scipy import stats
        except ImportError:
            return None
        
        # Generate baseline distribution from statistics
        baseline_values = np.random.normal(
            baseline_stats['mean'], 
            baseline_stats['std'], 
            len(current_values)
        )
        
        # Perform KS test
        ks_statistic, p_value = stats.ks_2samp(baseline_values, current_values)
        
        if p_value < self.significance_level:
            severity = 'high' if p_value < 0.01 else 'medium'
            return DriftAlert(
                timestamp=datetime.now(timezone.utc),
                drift_type='data_drift',
                feature_name=feature_name,
                severity=severity,
                score=ks_statistic,
                threshold=self.significance_level,
                message=f"Statistical drift detected in {feature_name} (KS test, p={p_value:.4f})",
                model_name=self.model_name
            )
        
        return None
    
    def _detect_distribution_shift(self, 
                                   feature_name: str,
                                   current_values: np.ndarray,
                                   baseline_stats: Dict[str, float]) -> Optional[DriftAlert]:
        """Detect significant shifts in distribution statistics."""
        current_mean = np.mean(current_values)
        current_std = np.std(current_values)
        
        # Check for mean shift (beyond 2 standard deviations)
        mean_shift = abs(current_mean - baseline_stats['mean'])
        mean_threshold = 2 * baseline_stats['std']
        
        if mean_shift > mean_threshold:
            severity = 'high' if mean_shift > 3 * baseline_stats['std'] else 'medium'
            return DriftAlert(
                timestamp=datetime.now(timezone.utc),
                drift_type='data_drift',
                feature_name=feature_name,
                severity=severity,
                score=mean_shift,
                threshold=mean_threshold,
                message=f"Mean shift detected in {feature_name}: {mean_shift:.3f} > {mean_threshold:.3f}",
                model_name=self.model_name
            )
        
        # Check for variance shift
        variance_ratio = current_std / baseline_stats['std']
        if variance_ratio > 2.0 or variance_ratio < 0.5:
            severity = 'high' if variance_ratio > 3.0 or variance_ratio < 0.33 else 'medium'
            return DriftAlert(
                timestamp=datetime.now(timezone.utc),
                drift_type='data_drift',
                feature_name=feature_name,
                severity=severity,
                score=variance_ratio,
                threshold=2.0,
                message=f"Variance shift detected in {feature_name}: ratio={variance_ratio:.3f}",
                model_name=self.model_name
            )
        
        return None
    
    def _detect_outlier_increase(self, 
                                 feature_name: str,
                                 current_values: np.ndarray,
                                 baseline_stats: Dict[str, float]) -> Optional[DriftAlert]:
        """Detect increase in outlier frequency."""
        # Define outliers as values beyond 3 standard deviations
        outlier_threshold = 3 * baseline_stats['std']
        lower_bound = baseline_stats['mean'] - outlier_threshold
        upper_bound = baseline_stats['mean'] + outlier_threshold
        
        current_outliers = np.sum((current_values < lower_bound) | (current_values > upper_bound))
        outlier_rate = current_outliers / len(current_values)
        
        # Alert if outlier rate exceeds 5%
        if outlier_rate > 0.05:
            severity = 'high' if outlier_rate > 0.1 else 'medium'
            return DriftAlert(
                timestamp=datetime.now(timezone.utc),
                drift_type='data_drift',
                feature_name=feature_name,
                severity=severity,
                score=outlier_rate,
                threshold=0.05,
                message=f"High outlier rate in {feature_name}: {outlier_rate:.3f}",
                model_name=self.model_name
            )
        
        return None
    
    def get_drift_summary(self) -> Dict[str, Any]:
        """Get summary of data drift detection status."""
        return {
            'model_name': self.model_name,
            'monitored_features': self.feature_names,
            'total_samples': len(self.timestamps),
            'baseline_established': len(self.baseline_stats) > 0,
            'features_with_baseline': list(self.baseline_stats.keys()),
            'active_alerts': len(self.drift_alerts),
            'window_size': self.window_size,
            'significance_level': self.significance_level
        }
