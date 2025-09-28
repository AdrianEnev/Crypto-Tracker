#!/usr/bin/env python3
"""
Demo script for ML Monitoring System (Phase 5D.1).
Demonstrates model performance monitoring, drift detection, and health checking.
"""

import sys
import os
import time
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, str(project_root))

from src.ml.monitoring import (
    ModelPerformanceMonitor, PerformanceMetrics,
    ConceptDriftDetector, DataDriftDetector, DriftAlert,
    ModelHealthChecker, HealthStatus,
    MetricsCollector, SystemMetrics, TradingMetrics
)


def generate_mock_market_data(n_points: int = 1000) -> pd.DataFrame:
    """Generate mock market data for testing."""
    np.random.seed(42)
    dates = pd.date_range(start=datetime(2020, 1, 1, tzinfo=timezone.utc), periods=n_points, freq='4h')
    
    # Generate realistic price data with some drift
    base_price = 100.0
    returns = np.random.normal(0.001, 0.02, n_points)  # 0.1% mean return, 2% volatility
    
    # Add some drift after point 600
    returns[600:] += 0.005  # Increase mean return
    
    prices = [base_price]
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    data = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
        'close': prices,
        'volume': np.random.exponential(1000, n_points),
        'rsi': 50 + np.random.normal(0, 15, n_points),
        'macd': np.random.normal(0, 0.5, n_points),
        'bb_position': np.random.uniform(0, 1, n_points)
    })
    
    return data


def demo_performance_monitoring():
    """Demonstrate model performance monitoring."""
    print("\n" + "="*60)
    print("🚀 DEMO: Model Performance Monitoring")
    print("="*60)
    
    # Initialize performance monitor
    monitor = ModelPerformanceMonitor(
        model_name="demo_trading_model",
        window_size=100,
        enable_alerts=True
    )
    
    print(f"Initialized performance monitor for: {monitor.model_name}")
    
    # Simulate model predictions with varying performance
    np.random.seed(42)
    
    for i in range(150):
        # Simulate prediction latency
        latency = np.random.exponential(50)  # Average 50ms
        
        # Simulate prediction accuracy (degradation over time)
        if i < 50:
            accuracy = 0.85 + np.random.normal(0, 0.05)  # High accuracy initially
        elif i < 100:
            accuracy = 0.80 + np.random.normal(0, 0.05)  # Slight degradation
        else:
            accuracy = 0.70 + np.random.normal(0, 0.05)  # Significant degradation
        
        # Generate prediction and actual
        prediction = 1 if np.random.random() < accuracy else 0
        actual = 1 if np.random.random() < 0.8 else 0
        
        # Simulate occasional errors
        error = None
        if np.random.random() < 0.02:  # 2% error rate
            error = Exception("Mock prediction error")
        
        # Record prediction
        monitor.record_prediction(
            prediction=prediction,
            actual=actual,
            latency_ms=latency,
            error=error
        )
        
        # Print progress every 25 predictions
        if (i + 1) % 25 == 0:
            current_metrics = monitor.get_current_metrics()
            if current_metrics:
                print(f"  Predictions {i+1}: Accuracy={current_metrics.accuracy:.3f}, "
                      f"Latency={current_metrics.latency_ms:.1f}ms, "
                      f"Errors={current_metrics.error_count}")
    
    # Get performance summary
    summary = monitor.get_performance_summary()
    print(f"\n📊 Performance Summary:")
    print(f"  Total Predictions: {summary['total_predictions']}")
    print(f"  Error Rate: {summary['error_rate']:.3f}")
    print(f"  Current Accuracy: {summary.get('current_accuracy', 'N/A')}")
    print(f"  Current Latency: {summary.get('current_latency_ms', 'N/A')}ms")
    print(f"  Active Alerts: {summary['active_alerts']}")
    print(f"  Uptime: {summary['uptime_hours']:.2f} hours")
    
    # Show alerts
    alerts = monitor.get_alerts()
    if alerts:
        print(f"\n⚠️  Performance Alerts ({len(alerts)}):")
        for alert in alerts[:5]:  # Show first 5 alerts
            print(f"  {alert['severity'].upper()}: {alert['message']}")
    
    print(f"\n✅ Performance monitoring demo completed!")


def demo_concept_drift_detection():
    """Demonstrate concept drift detection."""
    print("\n" + "="*60)
    print("🔍 DEMO: Concept Drift Detection")
    print("="*60)
    
    # Initialize concept drift detector
    detector = ConceptDriftDetector(
        model_name="demo_trading_model",
        window_size=100,
        significance_level=0.05,
        enable_alerts=True
    )
    
    print(f"Initialized concept drift detector for: {detector.model_name}")
    
    # Generate mock predictions with concept drift
    np.random.seed(42)
    n_predictions = 200
    
    for i in range(n_predictions):
        # Simulate concept drift after prediction 100
        if i < 100:
            # Baseline concept: 80% accuracy
            prediction = 1 if np.random.random() < 0.8 else 0
            actual = 1 if np.random.random() < 0.75 else 0
        else:
            # Drift: accuracy drops to 60%
            prediction = 1 if np.random.random() < 0.6 else 0
            actual = 1 if np.random.random() < 0.75 else 0
        
        # Add prediction to detector
        alert = detector.add_prediction(prediction, actual)
        
        if alert:
            print(f"  🚨 Drift Alert at prediction {i+1}: {alert.message}")
        
        # Print progress
        if (i + 1) % 50 == 0:
            summary = detector.get_drift_summary()
            print(f"  Predictions {i+1}: Samples={summary['total_samples']}, "
                  f"Baseline={summary['baseline_established']}")
    
    # Final summary
    summary = detector.get_drift_summary()
    print(f"\n📊 Drift Detection Summary:")
    print(f"  Total Samples: {summary['total_samples']}")
    print(f"  Baseline Established: {summary['baseline_established']}")
    print(f"  Baseline Accuracy: {summary.get('baseline_accuracy', 'N/A')}")
    print(f"  Active Alerts: {summary['active_alerts']}")
    
    print(f"\n✅ Concept drift detection demo completed!")


def demo_data_drift_detection():
    """Demonstrate data drift detection."""
    print("\n" + "="*60)
    print("📈 DEMO: Data Drift Detection")
    print("="*60)
    
    # Initialize data drift detector
    feature_names = ['close', 'volume', 'rsi', 'macd', 'bb_position']
    detector = DataDriftDetector(
        model_name="demo_trading_model",
        feature_names=feature_names,
        window_size=200,
        significance_level=0.05,
        enable_alerts=True
    )
    
    print(f"Initialized data drift detector for features: {feature_names}")
    
    # Generate mock market data with drift
    market_data = generate_mock_market_data(300)
    
    alerts_count = 0
    for i, row in market_data.iterrows():
        # Create feature dictionary
        features = {
            'close': row['close'],
            'volume': row['volume'],
            'rsi': row['rsi'],
            'macd': row['macd'],
            'bb_position': row['bb_position']
        }
        
        # Add features to detector
        alerts = detector.add_features(features, row['timestamp'])
        
        if alerts:
            alerts_count += len(alerts)
            for alert in alerts:
                print(f"  🚨 Data Drift Alert at row {i+1}: {alert.message}")
        
        # Print progress
        if (i + 1) % 100 == 0:
            summary = detector.get_drift_summary()
            print(f"  Rows processed {i+1}: Samples={summary['total_samples']}, "
                  f"Baseline={summary['baseline_established']}")
    
    # Final summary
    summary = detector.get_drift_summary()
    print(f"\n📊 Data Drift Detection Summary:")
    print(f"  Total Samples: {summary['total_samples']}")
    print(f"  Baseline Established: {summary['baseline_established']}")
    print(f"  Features with Baseline: {summary['features_with_baseline']}")
    print(f"  Total Alerts Generated: {alerts_count}")
    
    print(f"\n✅ Data drift detection demo completed!")


def demo_health_monitoring():
    """Demonstrate model health monitoring."""
    print("\n" + "="*60)
    print("🏥 DEMO: Model Health Monitoring")
    print("="*60)
    
    # Initialize health checker
    health_checker = ModelHealthChecker(
        model_name="demo_trading_model",
        check_interval_seconds=5,
        enable_system_monitoring=True
    )
    
    print(f"Initialized health checker for: {health_checker.model_name}")
    
    # Simulate model metrics updates
    for i in range(10):
        # Simulate varying model performance
        metrics = {
            'latency_ms': np.random.exponential(50) + i * 5,  # Increasing latency
            'accuracy': 0.85 - i * 0.02,  # Decreasing accuracy
            'error_rate': min(0.1, i * 0.01),  # Increasing error rate
            'memory_mb': 100 + i * 10,  # Increasing memory usage
            'last_data_update': datetime.now(timezone.utc) - timedelta(minutes=i)
        }
        
        # Update model metrics
        health_checker.update_model_metrics(metrics)
        
        # Run health checks
        checks = health_checker.run_health_checks()
        
        # Print results
        print(f"\n  Health Check {i+1}:")
        for check_name, check in checks.items():
            status_emoji = {
                HealthStatus.HEALTHY: "✅",
                HealthStatus.WARNING: "⚠️",
                HealthStatus.CRITICAL: "🚨",
                HealthStatus.UNKNOWN: "❓"
            }.get(check.status, "❓")
            
            print(f"    {status_emoji} {check.name}: {check.message}")
        
        # Wait between checks
        time.sleep(1)
    
    # Get overall health summary
    summary = health_checker.get_health_summary()
    print(f"\n📊 Health Summary:")
    print(f"  Overall Status: {summary['overall_status'].upper()}")
    print(f"  Recent Checks: {summary['recent_check_count']}")
    print(f"  Status Counts: {summary['status_counts']}")
    print(f"  Total Checks: {summary['total_checks_performed']}")
    print(f"  Uptime: {summary['uptime_hours']:.2f} hours")
    
    print(f"\n✅ Health monitoring demo completed!")


def demo_metrics_collection():
    """Demonstrate comprehensive metrics collection."""
    print("\n" + "="*60)
    print("📊 DEMO: Metrics Collection")
    print("="*60)
    
    # Initialize metrics collector
    collector = MetricsCollector(
        collection_interval=2,
        max_history_size=1000,
        enable_system_metrics=True,
        enable_trading_metrics=True
    )
    
    print(f"Initialized metrics collector")
    
    # Register a custom metric
    def get_model_confidence():
        return np.random.uniform(0.7, 0.95)
    
    collector.register_custom_metric("model_confidence", get_model_confidence)
    
    # Start collection
    collector.start_collection()
    print("Started metrics collection...")
    
    # Simulate some trading activity
    print("Simulating trading activity...")
    for i in range(5):
        # Record some trades
        success = np.random.random() > 0.3  # 70% success rate
        volume = np.random.uniform(100, 1000)
        pnl = np.random.normal(10, 50) if success else np.random.normal(-20, 30)
        duration = np.random.uniform(10, 300)
        
        collector.record_trade(success, volume, pnl, duration)
        
        print(f"  Trade {i+1}: {'✅' if success else '❌'} "
              f"Volume={volume:.1f}, PnL={pnl:.2f}, Duration={duration:.1f}s")
        
        time.sleep(3)  # Wait between trades
    
    # Stop collection
    collector.stop_collection()
    print("Stopped metrics collection")
    
    # Get metrics summary
    summary = collector.get_metrics_summary()
    print(f"\n📊 Metrics Collection Summary:")
    print(f"  Collection Status: {'Active' if summary['collection_status']['is_collecting'] else 'Stopped'}")
    print(f"  System Metrics: {summary['collection_status']['total_system_metrics']}")
    print(f"  Trading Metrics: {summary['collection_status']['total_trading_metrics']}")
    print(f"  Custom Metrics: {summary['collection_status']['custom_metrics_count']}")
    
    trading_summary = summary['trading_summary']
    print(f"\n💰 Trading Summary:")
    print(f"  Total Trades: {trading_summary['total_trades']}")
    print(f"  Win Rate: {trading_summary['win_rate']:.1%}")
    print(f"  Total Volume: {trading_summary['total_volume']:.1f}")
    print(f"  Total PnL: {trading_summary['total_pnl']:.2f}")
    print(f"  Daily PnL: {trading_summary['daily_pnl']:.2f}")
    print(f"  Max Drawdown: {trading_summary['max_drawdown']:.1%}")
    
    # Show current system status
    if 'current_system_status' in summary:
        system_status = summary['current_system_status']
        print(f"\n💻 Current System Status:")
        print(f"  CPU: {system_status['cpu_percent']:.1f}%")
        print(f"  Memory: {system_status['memory_percent']:.1f}%")
        print(f"  Disk: {system_status['disk_usage_percent']:.1f}%")
    
    print(f"\n✅ Metrics collection demo completed!")


def demo_comprehensive_monitoring():
    """Demonstrate comprehensive monitoring integration."""
    print("\n" + "="*60)
    print("🎯 DEMO: Comprehensive Monitoring Integration")
    print("="*60)
    
    # Initialize all monitoring components
    performance_monitor = ModelPerformanceMonitor("comprehensive_demo_model")
    concept_drift_detector = ConceptDriftDetector("comprehensive_demo_model")
    data_drift_detector = DataDriftDetector("comprehensive_demo_model", ['close', 'volume', 'rsi'])
    health_checker = ModelHealthChecker("comprehensive_demo_model")
    metrics_collector = MetricsCollector(collection_interval=1)
    
    print("Initialized comprehensive monitoring system")
    
    # Start metrics collection
    metrics_collector.start_collection()
    
    # Simulate a trading session
    print("Simulating trading session with monitoring...")
    
    for i in range(20):
        # Generate mock market data
        close_price = 100 + np.random.normal(0, 2)
        volume = np.random.exponential(1000)
        rsi = 50 + np.random.normal(0, 15)
        
        # Simulate model prediction
        prediction = 1 if np.random.random() > 0.5 else 0
        actual = 1 if np.random.random() > 0.45 else 0
        latency = np.random.exponential(30)
        
        # Update all monitors
        performance_monitor.record_prediction(prediction, actual, latency)
        
        concept_alert = concept_drift_detector.add_prediction(prediction, actual)
        
        feature_data = {'close': close_price, 'volume': volume, 'rsi': rsi}
        data_alerts = data_drift_detector.add_features(feature_data)
        
        # Update health checker with model metrics
        model_metrics = {
            'latency_ms': latency,
            'accuracy': 1.0 if prediction == actual else 0.0,
            'error_rate': 0.0
        }
        health_checker.update_model_metrics(model_metrics)
        health_checks = health_checker.run_health_checks()
        
        # Record trading activity
        if prediction == 1:  # Only record "buy" decisions as trades
            success = prediction == actual
            volume_trade = volume * 0.1  # 10% of market volume
            pnl = np.random.normal(5, 10) if success else np.random.normal(-3, 8)
            metrics_collector.record_trade(success, volume_trade, pnl)
        
        # Print alerts if any
        if concept_alert:
            print(f"  🚨 Concept Drift: {concept_alert.message}")
        
        if data_alerts:
            for alert in data_alerts:
                print(f"  🚨 Data Drift: {alert.message}")
        
        # Print health status every 5 iterations
        if (i + 1) % 5 == 0:
            overall_health = health_checker.get_overall_health_status()
            health_emoji = {
                HealthStatus.HEALTHY: "✅",
                HealthStatus.WARNING: "⚠️",
                HealthStatus.CRITICAL: "🚨"
            }.get(overall_health, "❓")
            
            print(f"  Iteration {i+1}: Health Status: {health_emoji} {overall_health.value}")
        
        time.sleep(0.5)  # Small delay to simulate real-time monitoring
    
    # Stop metrics collection
    metrics_collector.stop_collection()
    
    # Get final summaries
    print(f"\n📊 Final Monitoring Summary:")
    
    perf_summary = performance_monitor.get_performance_summary()
    print(f"  Performance: {perf_summary['total_predictions']} predictions, "
          f"Error rate: {perf_summary['error_rate']:.3f}")
    
    health_summary = health_checker.get_health_summary()
    print(f"  Health: {health_summary['overall_status']}, "
          f"{health_summary['recent_check_count']} recent checks")
    
    metrics_summary = metrics_collector.get_metrics_summary()
    print(f"  Trading: {metrics_summary['trading_summary']['total_trades']} trades, "
          f"Win rate: {metrics_summary['trading_summary']['win_rate']:.1%}")
    
    print(f"\n✅ Comprehensive monitoring demo completed!")


def main():
    """Run all monitoring demos."""
    print("🚀 ML Monitoring System Demo (Phase 5D.1)")
    print("=" * 60)
    
    try:
        # Run individual demos
        demo_performance_monitoring()
        demo_concept_drift_detection()
        demo_data_drift_detection()
        demo_health_monitoring()
        demo_metrics_collection()
        
        # Run comprehensive integration demo
        demo_comprehensive_monitoring()
        
        print("\n" + "="*60)
        print("🎉 All monitoring demos completed successfully!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error running monitoring demos: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
