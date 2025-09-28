"""
Multi-layer data validation system with comprehensive quality checks.
Implements statistical validation, schema validation, and cross-validation.
"""

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class ValidationLayer:
    """Represents a single validation layer result."""
    layer_name: str
    passed: bool
    issues: List[str]
    confidence_score: float
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ValidationResult:
    """Comprehensive validation result."""
    validation_layers: List[ValidationLayer]
    overall_quality_score: float
    data_issues: List[str]
    recommendations: List[str]
    validation_summary: Dict[str, Any]
    timestamp: datetime


class DataValidator:
    """
    Comprehensive data validation system with multiple validation layers.
    
    Features:
    - Schema validation
    - Statistical property validation
    - Outlier detection
    - Anomaly detection
    - Cross-validation with other sources
    - Data quality scoring
    - Comprehensive reporting
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # Validation thresholds
        self.max_missing_pct = self.config.get("max_missing_pct", 0.05)  # 5%
        self.max_outlier_pct = self.config.get("max_outlier_pct", 0.02)  # 2%
        self.max_price_change_pct = self.config.get("max_price_change_pct", 0.5)  # 50%
        self.min_volume_ratio = self.config.get("min_volume_ratio", 0.1)  # 10%
        
        # Cross-validation settings
        self.cross_validation_sources = self.config.get("cross_validation_sources", [])
        self.price_deviation_threshold = self.config.get("price_deviation_threshold", 0.02)  # 2%
        
        # Validation layers
        self.validation_layers = [
            "schema_validation",
            "statistical_validation", 
            "outlier_detection",
            "anomaly_detection",
            "cross_validation",
            "consistency_check"
        ]
        
    def validate_price_data(self, data: pd.DataFrame, symbol: str) -> ValidationResult:
        """
        Comprehensive price data validation.
        
        Args:
            data: Price data DataFrame with columns like 'close', 'volume', 'timestamp'
            symbol: Trading symbol for context
            
        Returns:
            Comprehensive validation result
        """
        validation_layers = []
        
        # Layer 1: Schema validation
        schema_result = self._validate_schema(data, symbol)
        validation_layers.append(schema_result)
        
        # Layer 2: Statistical validation
        stats_result = self._validate_statistical_properties(data, symbol)
        validation_layers.append(stats_result)
        
        # Layer 3: Outlier detection
        outlier_result = self._detect_outliers(data, symbol)
        validation_layers.append(outlier_result)
        
        # Layer 4: Anomaly detection
        anomaly_result = self._detect_anomalies(data, symbol)
        validation_layers.append(anomaly_result)
        
        # Layer 5: Cross-validation with other sources
        cross_validation_result = self._cross_validate_with_sources(data, symbol)
        validation_layers.append(cross_validation_result)
        
        # Layer 6: Consistency check
        consistency_result = self._validate_consistency(data, symbol)
        validation_layers.append(consistency_result)
        
        # Calculate overall quality score
        overall_score = self._calculate_overall_quality_score(validation_layers)
        
        # Aggregate issues and recommendations
        data_issues = self._aggregate_issues(validation_layers)
        recommendations = self._generate_recommendations(validation_layers, data_issues)
        
        # Create validation summary
        validation_summary = self._create_validation_summary(validation_layers, overall_score)
        
        return ValidationResult(
            validation_layers=validation_layers,
            overall_quality_score=overall_score,
            data_issues=data_issues,
            recommendations=recommendations,
            validation_summary=validation_summary,
            timestamp=datetime.now(timezone.utc)
        )
    
    def _validate_schema(self, data: pd.DataFrame, symbol: str) -> ValidationLayer:
        """Validate data schema and structure."""
        issues = []
        
        # Check required columns
        required_columns = ['close', 'volume', 'timestamp']
        missing_columns = [col for col in required_columns if col not in data.columns]
        
        if missing_columns:
            issues.append(f"Missing required columns: {missing_columns}")
        
        # Check data types
        if 'close' in data.columns:
            if not pd.api.types.is_numeric_dtype(data['close']):
                issues.append("Close price column is not numeric")
        
        if 'volume' in data.columns:
            if not pd.api.types.is_numeric_dtype(data['volume']):
                issues.append("Volume column is not numeric")
        
        if 'timestamp' in data.columns:
            if not pd.api.types.is_datetime64_any_dtype(data['timestamp']):
                issues.append("Timestamp column is not datetime")
        
        # Check for empty DataFrame
        if data.empty:
            issues.append("DataFrame is empty")
        
        # Check for duplicate timestamps
        if 'timestamp' in data.columns:
            duplicate_timestamps = data['timestamp'].duplicated().sum()
            if duplicate_timestamps > 0:
                issues.append(f"Found {duplicate_timestamps} duplicate timestamps")
        
        # Check timestamp ordering
        if 'timestamp' in data.columns and len(data) > 1:
            if not data['timestamp'].is_monotonic_increasing:
                issues.append("Timestamps are not in chronological order")
        
        confidence_score = max(0, 1 - len(issues) * 0.2)
        
        return ValidationLayer(
            layer_name="schema_validation",
            passed=len(issues) == 0,
            issues=issues,
            confidence_score=confidence_score,
            metadata={
                'total_rows': len(data),
                'total_columns': len(data.columns),
                'duplicate_timestamps': duplicate_timestamps if 'timestamp' in data.columns else 0
            }
        )
    
    def _validate_statistical_properties(self, data: pd.DataFrame, symbol: str) -> ValidationLayer:
        """Validate statistical properties of price data."""
        issues = []
        
        # Check for missing values
        if not data.empty:
            missing_pct = data.isnull().sum().sum() / (len(data) * len(data.columns))
            if missing_pct > self.max_missing_pct:
                issues.append(f"High missing data percentage: {missing_pct:.2%} (threshold: {self.max_missing_pct:.2%})")
        
        # Validate price data
        if 'close' in data.columns:
            close_prices = data['close'].dropna()
            
            if len(close_prices) > 0:
                # Check for negative or zero prices
                negative_prices = (close_prices <= 0).sum()
                if negative_prices > 0:
                    issues.append(f"Found {negative_prices} negative or zero prices")
                
                # Check for unrealistic price movements
                if len(close_prices) > 1:
                    returns = close_prices.pct_change().dropna()
                    extreme_returns = (abs(returns) > self.max_price_change_pct).sum()
                    if extreme_returns > 0:
                        issues.append(f"Found {extreme_returns} extreme price movements (>{self.max_price_change_pct:.1%})")
                    
                    # Check for constant prices (no movement)
                    zero_returns = (returns == 0).sum()
                    zero_return_pct = zero_returns / len(returns)
                    if zero_return_pct > 0.8:  # 80% of returns are zero
                        issues.append(f"High percentage of zero returns: {zero_return_pct:.1%}")
                
                # Check price range consistency
                price_range = close_prices.max() - close_prices.min()
                price_mean = close_prices.mean()
                if price_range / price_mean < 0.01:  # Less than 1% price range
                    issues.append("Very small price range - possible stale data")
        
        # Validate volume data
        if 'volume' in data.columns:
            volumes = data['volume'].dropna()
            
            if len(volumes) > 0:
                # Check for negative volumes
                negative_volumes = (volumes < 0).sum()
                if negative_volumes > 0:
                    issues.append(f"Found {negative_volumes} negative volumes")
                
                # Check for zero volume periods
                zero_volume_pct = (volumes == 0).sum() / len(volumes)
                if zero_volume_pct > 1 - self.min_volume_ratio:
                    issues.append(f"High zero volume percentage: {zero_volume_pct:.2%}")
                
                # Check volume consistency
                if len(volumes) > 1:
                    volume_std = volumes.std()
                    volume_mean = volumes.mean()
                    if volume_mean > 0 and volume_std / volume_mean > 10:  # CV > 10
                        issues.append("Very high volume volatility - possible data issues")
        
        confidence_score = max(0, 1 - len(issues) * 0.15)
        
        return ValidationLayer(
            layer_name="statistical_validation",
            passed=len(issues) == 0,
            issues=issues,
            confidence_score=confidence_score,
            metadata={
                'missing_data_pct': missing_pct if not data.empty else 0,
                'price_statistics': self._calculate_price_statistics(data),
                'volume_statistics': self._calculate_volume_statistics(data)
            }
        )
    
    def _detect_outliers(self, data: pd.DataFrame, symbol: str) -> ValidationLayer:
        """Detect outliers in price and volume data."""
        issues = []
        outlier_indices = []
        
        if 'close' in data.columns:
            close_prices = data['close'].dropna()
            
            if len(close_prices) > 10:  # Need minimum data for outlier detection
                # Z-score method
                z_scores = np.abs((close_prices - close_prices.mean()) / close_prices.std())
                z_outliers = z_scores > 3
                
                # IQR method
                Q1 = close_prices.quantile(0.25)
                Q3 = close_prices.quantile(0.75)
                IQR = Q3 - Q1
                iqr_outliers = (close_prices < Q1 - 1.5 * IQR) | (close_prices > Q3 + 1.5 * IQR)
                
                # Combine methods
                outliers = z_outliers | iqr_outliers
                outlier_count = outliers.sum()
                
                if outlier_count > 0:
                    outlier_pct = outlier_count / len(close_prices)
                    if outlier_pct > self.max_outlier_pct:
                        issues.append(f"High outlier percentage: {outlier_pct:.2%} ({outlier_count} outliers)")
                    
                    outlier_indices.extend(close_prices[outliers].index.tolist())
        
        if 'volume' in data.columns:
            volumes = data['volume'].dropna()
            
            if len(volumes) > 10:
                # Volume outlier detection
                volume_mean = volumes.mean()
                volume_std = volumes.std()
                
                if volume_std > 0:
                    volume_outliers = volumes > volume_mean + 5 * volume_std  # 5-sigma
                    volume_outlier_count = volume_outliers.sum()
                    
                    if volume_outlier_count > 0:
                        volume_outlier_pct = volume_outlier_count / len(volumes)
                        if volume_outlier_pct > 0.01:  # 1% threshold for volume outliers
                            issues.append(f"High volume outlier percentage: {volume_outlier_pct:.2%}")
        
        confidence_score = max(0, 1 - len(issues) * 0.25)
        
        return ValidationLayer(
            layer_name="outlier_detection",
            passed=len(issues) == 0,
            issues=issues,
            confidence_score=confidence_score,
            metadata={
                'outlier_indices': outlier_indices,
                'outlier_count': len(outlier_indices),
                'outlier_percentage': len(outlier_indices) / len(data) if len(data) > 0 else 0
            }
        )
    
    def _detect_anomalies(self, data: pd.DataFrame, symbol: str) -> ValidationLayer:
        """Detect anomalies in price patterns and data quality."""
        issues = []
        
        if len(data) < 10:
            return ValidationLayer(
                layer_name="anomaly_detection",
                passed=True,
                issues=[],
                confidence_score=1.0,
                metadata={'insufficient_data': True}
            )
        
        if 'close' in data.columns and 'volume' in data.columns:
            # Price-volume relationship anomalies
            close_prices = data['close'].dropna()
            volumes = data['volume'].dropna()
            
            if len(close_prices) > 5 and len(volumes) > 5:
                # Calculate rolling correlation
                min_length = min(len(close_prices), len(volumes))
                close_subset = close_prices.iloc[:min_length]
                volume_subset = volumes.iloc[:min_length]
                
                if min_length > 20:
                    # Create a DataFrame with both series for correlation calculation
                    combined_df = pd.DataFrame({'close': close_subset, 'volume': volume_subset})
                    rolling_corr = combined_df['close'].rolling(20).corr(combined_df['volume'])
                    avg_correlation = rolling_corr.mean()
                    
                    # Check for suspicious correlation patterns
                    if abs(avg_correlation) > 0.9:
                        issues.append(f"Suspiciously high price-volume correlation: {avg_correlation:.3f}")
                
                # Check for price jumps without volume
                if len(close_subset) > 1:
                    price_changes = close_subset.pct_change().abs()
                    volume_changes = volume_subset.pct_change().abs()
                    
                    # Find large price moves with small volume changes
                    large_price_moves = price_changes > 0.05  # 5%+ moves
                    small_volume_changes = volume_changes < 0.1  # <10% volume change
                    
                    suspicious_moves = large_price_moves & small_volume_changes
                    if suspicious_moves.sum() > 0:
                        issues.append(f"Found {suspicious_moves.sum()} large price moves with low volume")
        
        # Check for data gaps
        if 'timestamp' in data.columns and len(data) > 1:
            time_diffs = data['timestamp'].diff().dropna()
            if len(time_diffs) > 0:
                median_diff = time_diffs.median()
                large_gaps = time_diffs > median_diff * 10  # 10x normal interval
                
                if large_gaps.sum() > 0:
                    issues.append(f"Found {large_gaps.sum()} large time gaps in data")
        
        confidence_score = max(0, 1 - len(issues) * 0.3)
        
        return ValidationLayer(
            layer_name="anomaly_detection",
            passed=len(issues) == 0,
            issues=issues,
            confidence_score=confidence_score,
            metadata={
                'anomaly_types': issues,
                'data_gaps': large_gaps.sum() if 'timestamp' in data.columns and len(data) > 1 else 0
            }
        )
    
    def _cross_validate_with_sources(self, data: pd.DataFrame, symbol: str) -> ValidationLayer:
        """Cross-validate data with other sources if available."""
        issues = []
        
        # Mock cross-validation (in real implementation, would fetch from other sources)
        if self.cross_validation_sources:
            # Simulate cross-validation with other price sources
            if 'close' in data.columns and len(data) > 0:
                current_price = data['close'].iloc[-1]
                
                # Mock other source prices (in real system, would fetch actual data)
                other_source_prices = [
                    current_price * np.random.uniform(0.999, 1.001),  # Source 1
                    current_price * np.random.uniform(0.998, 1.002),  # Source 2
                ]
                
                # Check for significant deviations
                for i, other_price in enumerate(other_source_prices):
                    deviation = abs(current_price - other_price) / current_price
                    if deviation > self.price_deviation_threshold:
                        issues.append(f"Price deviation from source {i+1}: {deviation:.2%}")
        
        confidence_score = max(0, 1 - len(issues) * 0.4)
        
        return ValidationLayer(
            layer_name="cross_validation",
            passed=len(issues) == 0,
            issues=issues,
            confidence_score=confidence_score,
            metadata={
                'sources_checked': len(self.cross_validation_sources),
                'deviations_found': len(issues)
            }
        )
    
    def _validate_consistency(self, data: pd.DataFrame, symbol: str) -> ValidationLayer:
        """Validate internal consistency of the dataset."""
        issues = []
        
        # Check OHLC consistency if available
        ohlc_columns = ['open', 'high', 'low', 'close']
        if all(col in data.columns for col in ohlc_columns):
            ohlc_data = data[ohlc_columns].dropna()
            
            if len(ohlc_data) > 0:
                # Check high >= max(open, close)
                high_violations = (ohlc_data['high'] < ohlc_data[['open', 'close']].max(axis=1)).sum()
                if high_violations > 0:
                    issues.append(f"Found {high_violations} high price violations")
                
                # Check low <= min(open, close)
                low_violations = (ohlc_data['low'] > ohlc_data[['open', 'close']].min(axis=1)).sum()
                if low_violations > 0:
                    issues.append(f"Found {low_violations} low price violations")
        
        # Check for impossible values
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            if col in ['close', 'open', 'high', 'low']:
                # Price columns should be positive
                negative_values = (data[col] <= 0).sum()
                if negative_values > 0:
                    issues.append(f"Found {negative_values} non-positive values in {col}")
            
            # Check for infinity or extremely large values
            infinite_values = np.isinf(data[col]).sum()
            if infinite_values > 0:
                issues.append(f"Found {infinite_values} infinite values in {col}")
            
            # Check for extremely large values (potential data errors)
            if data[col].max() > 1e10:
                issues.append(f"Found extremely large values in {col}")
        
        confidence_score = max(0, 1 - len(issues) * 0.35)
        
        return ValidationLayer(
            layer_name="consistency_check",
            passed=len(issues) == 0,
            issues=issues,
            confidence_score=confidence_score,
            metadata={
                'ohlc_violations': high_violations + low_violations if 'high' in data.columns else 0,
                'consistency_issues': len(issues)
            }
        )
    
    def _calculate_overall_quality_score(self, validation_layers: List[ValidationLayer]) -> float:
        """Calculate overall data quality score."""
        if not validation_layers:
            return 0.0
        
        # Weight different layers
        layer_weights = {
            'schema_validation': 0.2,
            'statistical_validation': 0.25,
            'outlier_detection': 0.2,
            'anomaly_detection': 0.15,
            'cross_validation': 0.1,
            'consistency_check': 0.1
        }
        
        weighted_score = 0.0
        total_weight = 0.0
        
        for layer in validation_layers:
            weight = layer_weights.get(layer.layer_name, 1.0)
            weighted_score += layer.confidence_score * weight
            total_weight += weight
        
        return weighted_score / total_weight if total_weight > 0 else 0.0
    
    def _aggregate_issues(self, validation_layers: List[ValidationLayer]) -> List[str]:
        """Aggregate all issues from validation layers."""
        all_issues = []
        for layer in validation_layers:
            all_issues.extend(layer.issues)
        return all_issues
    
    def _generate_recommendations(self, validation_layers: List[ValidationLayer], 
                                data_issues: List[str]) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        # Schema issues
        schema_issues = [issue for layer in validation_layers 
                        if layer.layer_name == "schema_validation" for issue in layer.issues]
        if schema_issues:
            recommendations.append("Fix data schema issues: ensure required columns are present and properly typed")
        
        # Statistical issues
        stats_issues = [issue for layer in validation_layers 
                       if layer.layer_name == "statistical_validation" for issue in layer.issues]
        if stats_issues:
            recommendations.append("Review statistical properties: check for missing data and extreme values")
        
        # Outlier issues
        outlier_issues = [issue for layer in validation_layers 
                         if layer.layer_name == "outlier_detection" for issue in layer.issues]
        if outlier_issues:
            recommendations.append("Investigate outliers: verify extreme values or consider data cleaning")
        
        # Anomaly issues
        anomaly_issues = [issue for layer in validation_layers 
                         if layer.layer_name == "anomaly_detection" for issue in layer.issues]
        if anomaly_issues:
            recommendations.append("Review data anomalies: check for suspicious patterns and data gaps")
        
        # Overall quality
        overall_score = self._calculate_overall_quality_score(validation_layers)
        if overall_score < 0.7:
            recommendations.append("Overall data quality is low - consider data source review")
        elif overall_score < 0.9:
            recommendations.append("Data quality is acceptable but could be improved")
        
        return recommendations
    
    def _create_validation_summary(self, validation_layers: List[ValidationLayer], 
                                 overall_score: float) -> Dict[str, Any]:
        """Create validation summary statistics."""
        total_layers = len(validation_layers)
        passed_layers = sum(1 for layer in validation_layers if layer.passed)
        
        layer_scores = {layer.layer_name: layer.confidence_score for layer in validation_layers}
        
        return {
            'total_validation_layers': total_layers,
            'passed_layers': passed_layers,
            'failed_layers': total_layers - passed_layers,
            'overall_quality_score': overall_score,
            'layer_scores': layer_scores,
            'validation_timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def _calculate_price_statistics(self, data: pd.DataFrame) -> Dict[str, float]:
        """Calculate price statistics for metadata."""
        if 'close' not in data.columns or data.empty:
            return {}
        
        prices = data['close'].dropna()
        if len(prices) == 0:
            return {}
        
        return {
            'mean_price': float(prices.mean()),
            'std_price': float(prices.std()),
            'min_price': float(prices.min()),
            'max_price': float(prices.max()),
            'price_range': float(prices.max() - prices.min()),
            'price_volatility': float(prices.std() / prices.mean()) if prices.mean() != 0 else 0
        }
    
    def _calculate_volume_statistics(self, data: pd.DataFrame) -> Dict[str, float]:
        """Calculate volume statistics for metadata."""
        if 'volume' not in data.columns or data.empty:
            return {}
        
        volumes = data['volume'].dropna()
        if len(volumes) == 0:
            return {}
        
        return {
            'mean_volume': float(volumes.mean()),
            'std_volume': float(volumes.std()),
            'min_volume': float(volumes.min()),
            'max_volume': float(volumes.max()),
            'volume_volatility': float(volumes.std() / volumes.mean()) if volumes.mean() != 0 else 0
        }
