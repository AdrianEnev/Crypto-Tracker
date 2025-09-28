"""
Demo script for data validation pipeline and quality assessment.
Shows comprehensive data validation, outlier detection, and quality scoring.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from src.data_validation.validator import DataValidator, ValidationResult
from src.data_validation.outlier_detector import OutlierDetector, OutlierResult
from src.data_validation.quality_scorer import DataQualityScorer, QualityScore
from src.data_validation.anomaly_detector import AnomalyDetector, AnomalyResult


def generate_clean_market_data():
    """Generate clean, realistic market data."""
    np.random.seed(42)
    
    # Generate 1000 data points (about 4 years of daily data)
    n_points = 1000
    dates = pd.date_range('2020-01-01', periods=n_points, freq='D')
    
    # Generate realistic price data with trend and volatility
    base_price = 50000
    trend = np.linspace(0, 0.5, n_points)  # 50% upward trend over period
    volatility = np.random.normal(0, 0.02, n_points)  # 2% daily volatility
    
    # Generate prices with trend and volatility
    price_changes = trend + volatility
    prices = base_price * np.cumprod(1 + price_changes)
    
    # Generate realistic volume data
    base_volume = 1000000
    volume_trend = np.linspace(0, 0.3, n_points)  # 30% volume increase
    volume_volatility = np.random.normal(0, 0.3, n_points)
    
    volumes = base_volume * np.cumprod(1 + volume_trend + volume_volatility)
    volumes = np.maximum(volumes, 100000)  # Minimum volume
    
    # Create DataFrame
    data = pd.DataFrame({
        'timestamp': dates,
        'close': prices,
        'volume': volumes,
        'open': prices * np.random.uniform(0.995, 1.005, n_points),
        'high': prices * np.random.uniform(1.001, 1.02, n_points),
        'low': prices * np.random.uniform(0.98, 0.999, n_points)
    })
    
    # Ensure high >= max(open, close) and low <= min(open, close)
    data['high'] = np.maximum(data['high'], np.maximum(data['open'], data['close']))
    data['low'] = np.minimum(data['low'], np.minimum(data['open'], data['close']))
    
    return data


def generate_contaminated_market_data():
    """Generate market data with various data quality issues."""
    # Start with clean data
    clean_data = generate_clean_market_data()
    data = clean_data.copy()
    
    # Introduce data quality issues
    n_points = len(data)
    
    # 1. Missing data (5% missing values)
    missing_indices = np.random.choice(n_points, size=int(0.05 * n_points), replace=False)
    data.loc[missing_indices, 'close'] = np.nan
    
    # 2. Outliers (2% outliers)
    outlier_indices = np.random.choice(n_points, size=int(0.02 * n_points), replace=False)
    data.loc[outlier_indices, 'close'] *= np.random.uniform(0.5, 2.0, len(outlier_indices))
    
    # 3. Volume spikes (1% volume spikes)
    volume_spike_indices = np.random.choice(n_points, size=int(0.01 * n_points), replace=False)
    data.loc[volume_spike_indices, 'volume'] *= np.random.uniform(5, 20, len(volume_spike_indices))
    
    # 4. Price gaps (0.5% large price jumps)
    gap_indices = np.random.choice(n_points, size=int(0.005 * n_points), replace=False)
    for idx in gap_indices:
        if idx > 0:
            data.loc[idx, 'close'] = data.loc[idx-1, 'close'] * np.random.uniform(0.8, 1.2)
    
    # 5. Time gaps (remove some timestamps)
    time_gap_indices = np.random.choice(n_points, size=int(0.01 * n_points), replace=False)
    data = data.drop(time_gap_indices)
    data = data.reset_index(drop=True)
    
    # 6. Negative volumes (0.1% negative volumes)
    negative_volume_indices = np.random.choice(len(data), size=int(0.001 * len(data)), replace=False)
    data.loc[negative_volume_indices, 'volume'] = -np.abs(data.loc[negative_volume_indices, 'volume'])
    
    return data


def demo_basic_data_validation():
    """Demo basic data validation with clean data."""
    print("=== Basic Data Validation Demo (Clean Data) ===\n")
    
    # Generate clean data
    print("Generating clean market data...")
    clean_data = generate_clean_market_data()
    
    print(f"Generated {len(clean_data)} data points")
    print(f"Date range: {clean_data['timestamp'].min()} to {clean_data['timestamp'].max()}")
    print(f"Price range: ${clean_data['close'].min():,.0f} to ${clean_data['close'].max():,.0f}")
    print(f"Volume range: {clean_data['volume'].min():,.0f} to {clean_data['volume'].max():,.0f}")
    print()
    
    # Create validator
    validator_config = {
        "max_missing_pct": 0.05,
        "max_outlier_pct": 0.02,
        "max_price_change_pct": 0.5,
        "min_volume_ratio": 0.1,
        "price_deviation_threshold": 0.02
    }
    
    validator = DataValidator(validator_config)
    
    # Validate data
    print("Running comprehensive data validation...")
    result = validator.validate_price_data(clean_data, "BTC-USDT")
    
    # Display results
    print("Validation Results:")
    print(f"  Overall Quality Score: {result.overall_quality_score:.1f}/100")
    print(f"  Data Issues Found: {len(result.data_issues)}")
    print()
    
    print("Validation Layer Results:")
    for layer in result.validation_layers:
        status = "PASSED" if layer.passed else "FAILED"
        print(f"  {layer.layer_name}: {status} (Score: {layer.confidence_score:.3f})")
        if layer.issues:
            for issue in layer.issues[:3]:  # Show first 3 issues
                print(f"    - {issue}")
        print()
    
    print("Recommendations:")
    for i, rec in enumerate(result.recommendations, 1):
        print(f"  {i}. {rec}")
    print()


def demo_contaminated_data_validation():
    """Demo data validation with contaminated data."""
    print("=== Contaminated Data Validation Demo ===\n")
    
    # Generate contaminated data
    print("Generating contaminated market data...")
    contaminated_data = generate_contaminated_market_data()
    
    print(f"Generated {len(contaminated_data)} data points with various quality issues")
    print()
    
    # Create validator with stricter settings
    validator_config = {
        "max_missing_pct": 0.03,
        "max_outlier_pct": 0.01,
        "max_price_change_pct": 0.3,
        "min_volume_ratio": 0.2,
        "price_deviation_threshold": 0.01
    }
    
    validator = DataValidator(validator_config)
    
    # Validate data
    print("Running comprehensive data validation...")
    result = validator.validate_price_data(contaminated_data, "BTC-USDT")
    
    # Display results
    print("Validation Results:")
    print(f"  Overall Quality Score: {result.overall_quality_score:.1f}/100")
    print(f"  Data Issues Found: {len(result.data_issues)}")
    print()
    
    print("Validation Layer Results:")
    for layer in result.validation_layers:
        status = "PASSED" if layer.passed else "FAILED"
        print(f"  {layer.layer_name}: {status} (Score: {layer.confidence_score:.3f})")
        if layer.issues:
            for issue in layer.issues[:3]:  # Show first 3 issues
                print(f"    - {issue}")
        print()
    
    print("Recommendations:")
    for i, rec in enumerate(result.recommendations, 1):
        print(f"  {i}. {rec}")
    print()


def demo_outlier_detection():
    """Demo advanced outlier detection."""
    print("=== Advanced Outlier Detection Demo ===\n")
    
    # Generate contaminated data
    print("Generating data with outliers...")
    data = generate_contaminated_market_data()
    
    # Create outlier detector
    outlier_config = {
        "detection_methods": ["statistical", "isolation_forest", "lof", "domain_specific"],
        "z_score_threshold": 3.0,
        "iqr_multiplier": 1.5,
        "consensus_threshold": 0.5,
        "price_change_threshold": 0.1,
        "volume_spike_threshold": 5.0
    }
    
    outlier_detector = OutlierDetector(outlier_config)
    
    # Detect outliers
    print("Running outlier detection...")
    result = outlier_detector.detect_outliers(data, "BTC-USDT")
    
    # Display results
    print("Outlier Detection Results:")
    print(f"  Total outliers detected: {len(result.outlier_indices)}")
    print(f"  Outlier percentage: {result.outlier_statistics.get('outlier_percentage', 0)*100:.2f}%")
    print()
    
    print("Outlier Detection Methods:")
    for method, outliers in result.detection_methods.items():
        print(f"  {method}: {len(outliers)} outliers")
    print()
    
    print("Outlier Categories:")
    for category, outliers in result.outlier_types.items():
        if outliers:
            print(f"  {category}: {len(outliers)} outliers")
    print()
    
    print("Confidence Scores:")
    for method, confidence in result.confidence_scores.items():
        print(f"  {method}: {confidence:.3f}")
    print()
    
    print("Recommendations:")
    for i, rec in enumerate(result.recommendations, 1):
        print(f"  {i}. {rec}")
    print()


def demo_anomaly_detection():
    """Demo advanced anomaly detection."""
    print("=== Advanced Anomaly Detection Demo ===\n")
    
    # Generate data with anomalies
    print("Generating data with anomalies...")
    data = generate_contaminated_market_data()
    
    # Create anomaly detector
    anomaly_config = {
        "correlation_threshold": 0.95,
        "volume_spike_threshold": 5.0,
        "price_gap_threshold": 0.02,
        "time_gap_threshold_hours": 2.0,
        "pattern_window": 20,
        "anomaly_score_threshold": 0.7
    }
    
    anomaly_detector = AnomalyDetector(anomaly_config)
    
    # Detect anomalies
    print("Running anomaly detection...")
    result = anomaly_detector.detect_anomalies(data, "BTC-USDT")
    
    # Display results
    print("Anomaly Detection Results:")
    print(f"  Total anomalies detected: {len(result.anomaly_indices)}")
    print(f"  Anomaly percentage: {result.anomaly_statistics.get('anomaly_percentage', 0)*100:.2f}%")
    print()
    
    print("Anomaly Types:")
    for anomaly_type, anomalies in result.anomaly_types.items():
        if anomalies:
            print(f"  {anomaly_type}: {len(anomalies)} anomalies")
    print()
    
    print("Confidence Scores:")
    for anomaly_type, confidence in result.confidence_scores.items():
        print(f"  {anomaly_type}: {confidence:.3f}")
    print()
    
    print("Recommendations:")
    for i, rec in enumerate(result.recommendations, 1):
        print(f"  {i}. {rec}")
    print()


def demo_quality_scoring():
    """Demo data quality scoring system."""
    print("=== Data Quality Scoring Demo ===\n")
    
    # Generate both clean and contaminated data
    print("Generating clean and contaminated datasets...")
    clean_data = generate_clean_market_data()
    contaminated_data = generate_contaminated_market_data()
    
    # Create validator and quality scorer
    validator_config = {
        "max_missing_pct": 0.05,
        "max_outlier_pct": 0.02,
        "max_price_change_pct": 0.5,
        "min_volume_ratio": 0.1
    }
    
    quality_config = {
        "quality_weights": {
            'schema_validation': 0.20,
            'statistical_validation': 0.25,
            'outlier_detection': 0.20,
            'anomaly_detection': 0.15,
            'cross_validation': 0.10,
            'consistency_check': 0.10
        },
        "quality_thresholds": {
            'acceptable': 70.0,
            'good': 80.0,
            'excellent': 90.0
        }
    }
    
    validator = DataValidator(validator_config)
    quality_scorer = DataQualityScorer(quality_config)
    
    # Test both datasets
    datasets = [
        ("Clean Data", clean_data),
        ("Contaminated Data", contaminated_data)
    ]
    
    for dataset_name, dataset in datasets:
        print(f"Analyzing {dataset_name}...")
        
        # Validate data
        validation_result = validator.validate_price_data(dataset, "BTC-USDT")
        
        # Calculate quality score
        quality_score = quality_scorer.calculate_quality_score(validation_result.validation_layers)
        
        # Display results
        print(f"  Overall Quality Score: {quality_score.overall_score:.1f}/100")
        print(f"  Quality Grade: {quality_score.quality_grade}")
        print(f"  Acceptable: {'Yes' if quality_score.is_acceptable else 'No'}")
        print()
        
        print("  Quality Breakdown:")
        for dimension, score in quality_score.quality_breakdown.items():
            print(f"    {dimension.title()}: {score:.1f}/100")
        print()
        
        print("  Improvement Suggestions:")
        for i, suggestion in enumerate(quality_score.improvement_suggestions[:3], 1):
            print(f"    {i}. {suggestion}")
        print()


def demo_comprehensive_validation():
    """Demo comprehensive validation pipeline."""
    print("=== Comprehensive Validation Pipeline Demo ===\n")
    
    # Generate multiple datasets with different quality levels
    print("Generating datasets with different quality levels...")
    
    datasets = {
        "Excellent Quality": generate_clean_market_data(),
        "Good Quality": generate_contaminated_market_data(),
        "Poor Quality": generate_extremely_contaminated_data()
    }
    
    # Create comprehensive validation pipeline
    validator_config = {
        "max_missing_pct": 0.05,
        "max_outlier_pct": 0.02,
        "max_price_change_pct": 0.5,
        "min_volume_ratio": 0.1,
        "cross_validation_sources": ["source1", "source2"]
    }
    
    outlier_config = {
        "detection_methods": ["statistical", "domain_specific"],
        "consensus_threshold": 0.5
    }
    
    anomaly_config = {
        "correlation_threshold": 0.95,
        "volume_spike_threshold": 5.0,
        "pattern_window": 20
    }
    
    quality_config = {
        "quality_thresholds": {
            'acceptable': 70.0,
            'good': 80.0,
            'excellent': 90.0
        }
    }
    
    validator = DataValidator(validator_config)
    outlier_detector = OutlierDetector(outlier_config)
    anomaly_detector = AnomalyDetector(anomaly_config)
    quality_scorer = DataQualityScorer(quality_config)
    
    # Analyze each dataset
    results = {}
    
    for dataset_name, dataset in datasets.items():
        print(f"Analyzing {dataset_name}...")
        
        # Run validation pipeline
        validation_result = validator.validate_price_data(dataset, "BTC-USDT")
        outlier_result = outlier_detector.detect_outliers(dataset, "BTC-USDT")
        anomaly_result = anomaly_detector.detect_anomalies(dataset, "BTC-USDT")
        quality_score = quality_scorer.calculate_quality_score(validation_result.validation_layers)
        
        results[dataset_name] = {
            'validation': validation_result,
            'outliers': outlier_result,
            'anomalies': anomaly_result,
            'quality': quality_score
        }
        
        print(f"  Quality Score: {quality_score.overall_score:.1f}/100 ({quality_score.quality_grade})")
        print(f"  Outliers: {len(outlier_result.outlier_indices)}")
        print(f"  Anomalies: {len(anomaly_result.anomaly_indices)}")
        print(f"  Issues: {len(validation_result.data_issues)}")
        print()
    
    # Compare results
    print("Quality Comparison Summary:")
    print("-" * 50)
    print(f"{'Dataset':<20} {'Score':<8} {'Grade':<6} {'Outliers':<10} {'Anomalies':<10}")
    print("-" * 50)
    
    for dataset_name, result in results.items():
        print(f"{dataset_name:<20} {result['quality'].overall_score:<8.1f} {result['quality'].quality_grade:<6} "
              f"{len(result['outliers'].outlier_indices):<10} {len(result['anomalies'].anomaly_indices):<10}")
    
    print("-" * 50)
    print()
    
    # Generate comprehensive recommendations
    print("Comprehensive Recommendations:")
    
    # Find worst dataset
    worst_dataset = min(results.keys(), key=lambda k: results[k]['quality'].overall_score)
    worst_result = results[worst_dataset]
    
    print(f"1. Priority: Improve {worst_dataset} (Score: {worst_result['quality'].overall_score:.1f})")
    
    # Specific recommendations
    if worst_result['quality'].overall_score < 70:
        print("2. Critical: Data quality below acceptable threshold - immediate action required")
    
    if len(worst_result['outliers'].outlier_indices) > 10:
        print("3. High: Excessive outliers detected - review data collection process")
    
    if len(worst_result['anomalies'].anomaly_indices) > 5:
        print("4. Medium: Multiple anomalies detected - investigate data integrity")
    
    print("5. Implement automated data quality monitoring")
    print("6. Set up alerts for quality degradation")
    print("7. Regular validation of data sources")


def generate_extremely_contaminated_data():
    """Generate extremely contaminated data for testing."""
    data = generate_clean_market_data()
    
    # Add severe contamination
    n_points = len(data)
    
    # 20% missing data
    missing_indices = np.random.choice(n_points, size=int(0.2 * n_points), replace=False)
    data.loc[missing_indices, 'close'] = np.nan
    
    # 10% extreme outliers
    outlier_indices = np.random.choice(n_points, size=int(0.1 * n_points), replace=False)
    data.loc[outlier_indices, 'close'] *= np.random.uniform(0.1, 10.0, len(outlier_indices))
    
    # 5% negative prices
    negative_indices = np.random.choice(n_points, size=int(0.05 * n_points), replace=False)
    data.loc[negative_indices, 'close'] = -np.abs(data.loc[negative_indices, 'close'])
    
    # 15% zero volumes
    zero_volume_indices = np.random.choice(n_points, size=int(0.15 * n_points), replace=False)
    data.loc[zero_volume_indices, 'volume'] = 0
    
    return data


if __name__ == "__main__":
    demo_basic_data_validation()
    demo_contaminated_data_validation()
    demo_outlier_detection()
    demo_anomaly_detection()
    demo_quality_scoring()
    demo_comprehensive_validation()
    
    print("\n=== Demo Complete ===")
    print("\nKey Features of Data Validation Pipeline:")
    print("1. MULTI-LAYER VALIDATION: Schema, statistical, outlier, anomaly, and consistency checks")
    print("2. ADVANCED OUTLIER DETECTION: Statistical, ML-based, and domain-specific methods")
    print("3. ANOMALY DETECTION: Pattern-based and microstructure anomaly detection")
    print("4. QUALITY SCORING: Comprehensive quality assessment with grading system")
    print("5. CROSS-VALIDATION: Data validation against multiple sources")
    print("6. RECOMMENDATIONS: Actionable improvement suggestions")
    print("\nBenefits:")
    print("- Ensures data integrity and reliability")
    print("- Identifies data quality issues before they impact trading")
    print("- Provides automated quality monitoring and alerting")
    print("- Enables data-driven quality improvement decisions")
    print("- Supports regulatory compliance and audit requirements")
