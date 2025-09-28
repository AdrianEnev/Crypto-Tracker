#!/usr/bin/env python3
"""
Demo script for Advanced Observability & Dashboards (Phase 5D.4).
Demonstrates comprehensive monitoring, alerting, logging, and dashboard capabilities.
"""

import sys
import os
import time
import asyncio
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, str(project_root))

from src.ml.observability import (
    Dashboard, DashboardWidget, DashboardConfig, WidgetType, MetricType,
    AlertManager, AlertRule, AlertChannel, AlertSeverity, AlertStatus,
    StructuredLogger, LogLevel, LogContext, AuditLogger,
    MetricsAggregator, MetricsQuery, TimeSeriesData, AggregationType
)


async def demo_dashboard_system():
    """Demonstrate dashboard system functionality."""
    print("\n" + "="*60)
    print("📊 DEMO: Dashboard System")
    print("="*60)
    
    # Create dashboard configuration
    config = DashboardConfig(
        dashboard_id="ml-observability-dashboard",
        name="ML Observability Dashboard",
        description="Comprehensive dashboard for ML model monitoring",
        layout="grid",
        theme="dark",
        auto_refresh=True,
        refresh_interval=30,
        time_range="1h",
        timezone="UTC"
    )
    
    # Create dashboard
    dashboard = Dashboard(config)
    
    print(f"Dashboard created: {config.name}")
    print(f"  Layout: {config.layout}")
    print(f"  Theme: {config.theme}")
    print(f"  Auto refresh: {config.auto_refresh} ({config.refresh_interval}s)")
    
    # Create various widget types
    widgets = [
        DashboardWidget(
            widget_id="cpu-usage",
            widget_type=WidgetType.METRIC_CARD,
            title="CPU Usage",
            description="Current CPU utilization",
            position={"x": 0, "y": 0, "w": 2, "h": 1},
            config={"unit": "%", "color": "blue"},
            data_source="cpu_metrics"
        ),
        DashboardWidget(
            widget_id="response-time-chart",
            widget_type=WidgetType.LINE_CHART,
            title="Response Time",
            description="Model response time over time",
            position={"x": 2, "y": 0, "w": 4, "h": 2},
            config={"y_axis_label": "ms", "color": "green"},
            data_source="response_time_metrics"
        ),
        DashboardWidget(
            widget_id="model-accuracy",
            widget_type=WidgetType.BAR_CHART,
            title="Model Accuracy Comparison",
            description="Accuracy comparison across models",
            position={"x": 0, "y": 1, "w": 3, "h": 2},
            data_source="model_metrics"
        ),
        DashboardWidget(
            widget_id="error-distribution",
            widget_type=WidgetType.PIE_CHART,
            title="Error Distribution",
            description="Distribution of error types",
            position={"x": 3, "y": 1, "w": 3, "h": 2},
            data_source="error_metrics"
        ),
        DashboardWidget(
            widget_id="model-status-table",
            widget_type=WidgetType.TABLE,
            title="Model Status",
            description="Current status of all models",
            position={"x": 0, "y": 3, "w": 4, "h": 2},
            data_source="model_status"
        ),
        DashboardWidget(
            widget_id="memory-gauge",
            widget_type=WidgetType.GAUGE,
            title="Memory Usage",
            description="Current memory utilization",
            position={"x": 4, "y": 3, "w": 2, "h": 2},
            config={"min": 0, "max": 100, "unit": "%"},
            data_source="memory_metrics"
        ),
        DashboardWidget(
            widget_id="alerts-list",
            widget_type=WidgetType.ALERT_LIST,
            title="Active Alerts",
            description="Current system alerts",
            position={"x": 0, "y": 5, "w": 3, "h": 2},
            data_source="alerts"
        ),
        DashboardWidget(
            widget_id="service-status",
            widget_type=WidgetType.STATUS_GRID,
            title="Service Status",
            description="Status of all services",
            position={"x": 3, "y": 5, "w": 3, "h": 2},
            data_source="service_status"
        )
    ]
    
    # Add widgets to dashboard
    for widget in widgets:
        dashboard.add_widget(widget)
        print(f"  Added widget: {widget.title} ({widget.widget_type.value})")
    
    # Register data providers
    def cpu_metrics_provider(widget, time_range):
        return {"value": 65.5, "unit": "%", "trend": "up", "trend_value": 2.1}
    
    def response_time_provider(widget, time_range):
        points = []
        now = datetime.now(timezone.utc)
        for i in range(20):
            timestamp = now - timedelta(minutes=20-i)
            value = 100 + 50 * np.sin(i * 0.5) + np.random.normal(0, 10)
            points.append({"timestamp": timestamp.isoformat(), "value": max(0, value)})
        
        return {"series": [{"name": "Response Time", "data": points}]}
    
    def model_metrics_provider(widget, time_range):
        return {
            "categories": ["Model A", "Model B", "Model C", "Model D"],
            "series": [
                {"name": "Accuracy", "data": [0.92, 0.89, 0.85, 0.91]},
                {"name": "Precision", "data": [0.90, 0.87, 0.83, 0.89]}
            ]
        }
    
    dashboard.register_data_provider("cpu_metrics", cpu_metrics_provider)
    dashboard.register_data_provider("response_time_metrics", response_time_provider)
    dashboard.register_data_provider("model_metrics", model_metrics_provider)
    
    print(f"\nRegistered {len(dashboard.data_providers)} data providers")
    
    # Get dashboard data
    print(f"\nGenerating dashboard data...")
    dashboard_data = dashboard.get_dashboard_data("1h")
    
    print(f"Dashboard data generated:")
    print(f"  Dashboard: {dashboard_data['name']}")
    print(f"  Time range: {dashboard_data['time_range']}")
    print(f"  Widgets: {len(dashboard_data['widgets'])}")
    
    # Show widget data samples
    for widget_id, widget_data in list(dashboard_data['widgets'].items())[:3]:
        widget = dashboard.widgets[widget_id]
        print(f"  {widget.title}: {type(widget_data.get('data', {})).__name__}")
    
    # Export and import dashboard
    export_data = dashboard.export_dashboard()
    print(f"\nDashboard exported: {len(export_data['widgets'])} widgets")
    
    # Get dashboard summary
    summary = dashboard.get_dashboard_summary()
    print(f"\nDashboard Summary:")
    print(f"  Total widgets: {summary['total_widgets']}")
    print(f"  Widget types: {summary['widget_types']}")
    print(f"  Layout: {summary['layout']}")
    print(f"  Theme: {summary['theme']}")
    
    print(f"\n✅ Dashboard system demo completed!")


async def demo_alerting_system():
    """Demonstrate alerting system functionality."""
    print("\n" + "="*60)
    print("🚨 DEMO: Alerting System")
    print("="*60)
    
    # Create alert manager
    alert_manager = AlertManager()
    await alert_manager.start()
    
    print("Alert manager started")
    
    # Configure notification channels
    alert_manager.configure_channel(AlertChannel.EMAIL, {
        'smtp_server': 'smtp.example.com',
        'smtp_port': 587,
        'username': 'alerts@company.com',
        'recipients': ['admin@company.com', 'ops@company.com']
    })
    
    alert_manager.configure_channel(AlertChannel.WEBHOOK, {
        'url': 'https://hooks.slack.com/services/...',
        'headers': {'Content-Type': 'application/json'}
    })
    
    print("Configured notification channels: email, webhook")
    
    # Create alert rules
    alert_rules = [
        AlertRule(
            rule_id="high-cpu-usage",
            name="High CPU Usage",
            description="CPU usage exceeds 80%",
            condition="cpu_percent > 80",
            severity=AlertSeverity.WARNING,
            channels=[AlertChannel.EMAIL, AlertChannel.WEBHOOK],
            cooldown_seconds=300,
            evaluation_interval=60,
            threshold=80.0,
            tags=["infrastructure", "performance"]
        ),
        AlertRule(
            rule_id="high-error-rate",
            name="High Error Rate",
            description="Error rate exceeds 5%",
            condition="error_rate > 0.05",
            severity=AlertSeverity.ERROR,
            channels=[AlertChannel.EMAIL, AlertChannel.WEBHOOK, AlertChannel.LOG],
            cooldown_seconds=180,
            evaluation_interval=30,
            threshold=0.05,
            tags=["application", "reliability"]
        ),
        AlertRule(
            rule_id="slow-response-time",
            name="Slow Response Time",
            description="Response time exceeds 200ms",
            condition="response_time > 200",
            severity=AlertSeverity.WARNING,
            channels=[AlertChannel.WEBHOOK],
            cooldown_seconds=600,
            evaluation_interval=120,
            threshold=200.0,
            tags=["performance", "user-experience"]
        ),
        AlertRule(
            rule_id="model-accuracy-drop",
            name="Model Accuracy Drop",
            description="Model accuracy below 85%",
            condition="model_accuracy < 0.85",
            severity=AlertSeverity.CRITICAL,
            channels=[AlertChannel.EMAIL, AlertChannel.WEBHOOK, AlertChannel.PAGERDUTY],
            cooldown_seconds=900,
            evaluation_interval=300,
            threshold=0.85,
            tags=["ml", "model-performance"]
        )
    ]
    
    # Add alert rules
    for rule in alert_rules:
        alert_manager.add_alert_rule(rule)
        print(f"  Added rule: {rule.name} ({rule.severity.value})")
    
    # Wait for some evaluations
    print(f"\nWaiting for alert evaluations...")
    await asyncio.sleep(5)
    
    # Get active alerts
    active_alerts = alert_manager.get_active_alerts()
    print(f"\nActive alerts: {len(active_alerts)}")
    
    for alert in active_alerts:
        print(f"  {alert.title} - {alert.severity.value} - {alert.status.value}")
        print(f"    Triggered: {alert.triggered_at.strftime('%H:%M:%S')}")
        print(f"    Message: {alert.message}")
    
    # Acknowledge and resolve some alerts
    if active_alerts:
        alert_to_ack = active_alerts[0]
        alert_manager.acknowledge_alert(alert_to_ack.alert_id, "admin")
        print(f"\nAcknowledged alert: {alert_to_ack.alert_id}")
        
        # Resolve after a moment
        await asyncio.sleep(1)
        alert_manager.resolve_alert(alert_to_ack.alert_id, "admin")
        print(f"Resolved alert: {alert_to_ack.alert_id}")
    
    # Get alert statistics
    stats = alert_manager.get_alert_statistics()
    print(f"\nAlert Statistics:")
    print(f"  Total alerts: {stats['total_alerts']}")
    print(f"  Active alerts: {stats['active_alerts']}")
    print(f"  Resolved alerts: {stats['resolved_alerts']}")
    print(f"  Acknowledged alerts: {stats['acknowledged_alerts']}")
    print(f"  Total rules: {stats['total_rules']}")
    print(f"  Enabled rules: {stats['enabled_rules']}")
    print(f"  Severity distribution: {stats['severity_distribution']}")
    
    # Get alert history
    history = alert_manager.get_alert_history(limit=10)
    print(f"\nRecent alert history: {len(history)} alerts")
    
    await alert_manager.stop()
    print(f"\n✅ Alerting system demo completed!")


async def demo_logging_system():
    """Demonstrate structured logging system."""
    print("\n" + "="*60)
    print("📝 DEMO: Structured Logging System")
    print("="*60)
    
    # Create structured logger
    logger = StructuredLogger(
        name="ml-observability",
        log_file="demo_ml_observability.log",
        level=LogLevel.INFO,
        format_type="json"
    )
    
    print(f"Structured logger created:")
    print(f"  Name: {logger.name}")
    print(f"  Level: {logger.level.value}")
    print(f"  Format: {logger.format_type}")
    
    # Set logging context
    context = LogContext(
        user_id="demo_user",
        session_id="session_123",
        request_id="req_456",
        model_name="demo_model",
        model_version="1.0.0",
        environment="demo",
        tags=["demo", "observability"],
        metadata={"region": "us-east-1", "cluster": "prod"}
    )
    
    logger.set_context(context)
    print(f"Set logging context with user_id and model info")
    
    # Log various types of events
    print(f"\nLogging various events...")
    
    # Basic logging
    logger.info("System initialized successfully")
    logger.warning("High memory usage detected", memory_percent=85.5)
    logger.error("Failed to connect to database", exception=Exception("Connection timeout"))
    
    # Metric logging
    logger.log_metric("cpu_usage_percent", 75.5, {"host": "server-1", "service": "api"})
    logger.log_metric("response_time_ms", 125.3, {"endpoint": "/predict", "method": "POST"})
    logger.log_metric("error_count", 5, {"error_type": "validation_error"})
    
    # Event logging
    logger.log_event("user_login", {"user_id": "user123", "ip_address": "192.168.1.100"})
    logger.log_event("model_deployed", {"model_name": "sentiment_model", "version": "2.1.0"})
    
    # Model inference logging
    logger.log_model_inference(
        model_name="sentiment_model",
        model_version="2.1.0",
        input_data={"text": "This is a sample text"},
        output_data={"sentiment": "positive", "confidence": 0.92},
        latency_ms=45.2,
        success=True
    )
    
    # Model training logging
    logger.log_model_training(
        model_name="recommendation_model",
        training_data_size=100000,
        training_time_seconds=3600,
        metrics={"accuracy": 0.89, "precision": 0.87, "recall": 0.91},
        success=True
    )
    
    # Deployment logging
    logger.log_deployment(
        deployment_id="deploy_789",
        model_name="recommendation_model",
        model_version="3.0.0",
        environment="production",
        action="deploy",
        success=True
    )
    
    # Performance logging
    logger.log_performance(
        component="model_server",
        operation="predict",
        duration_ms=23.5,
        success=True,
        metadata={"batch_size": 32, "queue_depth": 5}
    )
    
    print(f"Logged various types of events with structured data")
    
    # Create audit logger
    audit_logger = AuditLogger("demo_audit.log")
    print(f"\nCreated audit logger: {audit_logger.audit_file}")
    
    # Audit logging examples
    audit_logger.log_user_action(
        user_id="admin_user",
        action="deploy_model",
        resource="model",
        resource_id="model_123",
        success=True,
        metadata={"environment": "production", "rollback_enabled": True}
    )
    
    audit_logger.log_system_event(
        event="service_restart",
        component="model_server",
        severity=LogLevel.WARNING,
        metadata={"reason": "configuration_change", "downtime_seconds": 30}
    )
    
    audit_logger.log_security_event(
        event="failed_login",
        user_id="suspicious_user",
        ip_address="192.168.1.999",
        severity=LogLevel.ERROR,
        metadata={"attempts": 5, "blocked": True}
    )
    
    audit_logger.log_data_access(
        user_id="analyst_1",
        data_type="training_data",
        operation="read",
        success=True,
        metadata={"dataset": "user_behavior", "rows_accessed": 10000}
    )
    
    print(f"Logged audit events for user actions, system events, security, and data access")
    
    # Update context and log with new context
    logger.update_context(model_name="updated_model", new_tag="updated")
    logger.info("Context updated, logging with new model name")
    
    print(f"Updated logging context and logged with new information")
    
    print(f"\n✅ Structured logging system demo completed!")


async def demo_metrics_system():
    """Demonstrate metrics aggregation system."""
    print("\n" + "="*60)
    print("📈 DEMO: Metrics Aggregation System")
    print("="*60)
    
    # Create metrics aggregator
    metrics = MetricsAggregator(
        max_retention_hours=1,
        aggregation_interval=60,
        max_points_per_metric=1000
    )
    
    print(f"Metrics aggregator created:")
    print(f"  Max retention: {metrics.max_retention_hours}h")
    print(f"  Aggregation interval: {metrics.aggregation_interval}s")
    print(f"  Max points per metric: {metrics.max_points_per_metric}")
    
    # Record various metrics
    print(f"\nRecording metrics...")
    
    now = datetime.now(timezone.utc)
    
    # Record CPU usage metrics
    for i in range(20):
        timestamp = now - timedelta(minutes=20-i)
        cpu_usage = 60 + 20 * np.sin(i * 0.3) + np.random.normal(0, 5)
        metrics.record_gauge(
            "cpu_usage_percent",
            max(0, min(100, cpu_usage)),
            tags={"host": "server-1", "service": "api"},
            timestamp=timestamp
        )
    
    # Record response time metrics
    for i in range(20):
        timestamp = now - timedelta(minutes=20-i)
        response_time = 100 + 50 * np.cos(i * 0.2) + np.random.normal(0, 15)
        metrics.record_timing(
            "response_time_ms",
            max(0, response_time),
            tags={"endpoint": "/predict", "method": "POST"},
            timestamp=timestamp
        )
    
    # Record error count metrics
    for i in range(20):
        timestamp = now - timedelta(minutes=20-i)
        error_count = np.random.poisson(2)  # Poisson distribution for counts
        metrics.record_counter(
            "error_count",
            error_count,
            tags={"error_type": "validation_error", "service": "api"},
            timestamp=timestamp
        )
    
    # Record model accuracy metrics
    for i in range(10):
        timestamp = now - timedelta(hours=1-i*6)
        accuracy = 0.85 + 0.1 * np.sin(i * 0.5) + np.random.normal(0, 0.02)
        metrics.record_gauge(
            "model_accuracy",
            max(0, min(1, accuracy)),
            tags={"model_name": "sentiment_model", "version": "2.1.0"},
            timestamp=timestamp
        )
    
    print(f"Recorded metrics for CPU usage, response time, error count, and model accuracy")
    
    # Query metrics
    print(f"\nQuerying metrics...")
    
    # Query CPU usage with different aggregations
    cpu_query = MetricsQuery(
        metric_name="cpu_usage_percent",
        start_time=now - timedelta(minutes=20),
        end_time=now,
        aggregation=AggregationType.AVG,
        interval_seconds=300  # 5-minute buckets
    )
    
    cpu_data = metrics.query_metrics(cpu_query)
    print(f"CPU usage query returned {len(cpu_data)} data points")
    
    if cpu_data:
        avg_cpu = sum(dp.value for dp in cpu_data) / len(cpu_data)
        print(f"  Average CPU usage: {avg_cpu:.2f}%")
    
    # Query response time with max aggregation
    response_query = MetricsQuery(
        metric_name="response_time_ms",
        start_time=now - timedelta(minutes=20),
        end_time=now,
        aggregation=AggregationType.MAX,
        interval_seconds=600  # 10-minute buckets
    )
    
    response_data = metrics.query_metrics(response_query)
    print(f"Response time query returned {len(response_data)} data points")
    
    if response_data:
        max_response = max(dp.value for dp in response_data)
        print(f"  Maximum response time: {max_response:.2f}ms")
    
    # Query with tags filter
    error_query = MetricsQuery(
        metric_name="error_count",
        start_time=now - timedelta(minutes=20),
        end_time=now,
        aggregation=AggregationType.SUM,
        tags_filter={"error_type": "validation_error"}
    )
    
    error_data = metrics.query_metrics(error_query)
    print(f"Error count query returned {len(error_data)} data points")
    
    if error_data:
        total_errors = sum(dp.value for dp in error_data)
        print(f"  Total validation errors: {total_errors}")
    
    # Get metric summaries
    print(f"\nMetric summaries:")
    for metric_name in metrics.list_metrics():
        summary = metrics.get_metric_summary(metric_name)
        if summary:
            print(f"  {metric_name}:")
            print(f"    Points: {summary['total_points']}")
            print(f"    Range: {summary['min_value']:.2f} - {summary['max_value']:.2f}")
            print(f"    Average: {summary['avg_value']:.2f}")
            print(f"    Median: {summary['median_value']:.2f}")
    
    # Get metrics overview
    overview = metrics.get_metrics_overview()
    print(f"\nMetrics Overview:")
    print(f"  Total metrics: {overview['total_metrics']}")
    print(f"  Total data points: {overview['total_data_points']}")
    print(f"  Generated at: {overview['generated_at']}")
    
    # Close metrics aggregator
    metrics.close()
    print(f"\n✅ Metrics aggregation system demo completed!")


async def demo_comprehensive_observability():
    """Demonstrate comprehensive observability workflow."""
    print("\n" + "="*60)
    print("🎯 DEMO: Comprehensive Observability Workflow")
    print("="*60)
    
    print("This demo showcases a complete ML observability pipeline:")
    print("1. Structured Logging - Comprehensive event and audit logging")
    print("2. Metrics Collection - Time series data aggregation and querying")
    print("3. Alerting System - Intelligent alerting with multiple channels")
    print("4. Dashboard System - Real-time visualization and monitoring")
    
    # Create all observability components
    logger = StructuredLogger("comprehensive-observability", format_type="json")
    metrics = MetricsAggregator(max_retention_hours=2)
    alert_manager = AlertManager()
    dashboard = Dashboard(DashboardConfig(
        dashboard_id="comprehensive-dashboard",
        name="Comprehensive ML Observability Dashboard"
    ))
    
    print(f"\n✅ All observability components initialized")
    
    # Set up comprehensive logging context
    context = LogContext(
        user_id="ml_engineer",
        session_id="obs_session_123",
        model_name="production_model",
        model_version="3.0.0",
        environment="production",
        tags=["production", "observability", "comprehensive"]
    )
    logger.set_context(context)
    
    # Configure alerting
    alert_manager.configure_channel(AlertChannel.EMAIL, {
        'recipients': ['ml-team@company.com']
    })
    alert_manager.configure_channel(AlertChannel.WEBHOOK, {
        'url': 'https://hooks.slack.com/services/...'
    })
    
    # Add comprehensive alert rules
    rules = [
        AlertRule(
            rule_id="comprehensive-cpu-alert",
            name="Production CPU Alert",
            description="CPU usage in production environment",
            condition="cpu_percent > 75",
            severity=AlertSeverity.WARNING,
            channels=[AlertChannel.EMAIL, AlertChannel.WEBHOOK],
            tags=["production", "infrastructure"]
        ),
        AlertRule(
            rule_id="comprehensive-model-alert",
            name="Model Performance Alert",
            description="Model accuracy degradation",
            condition="model_accuracy < 0.90",
            severity=AlertSeverity.CRITICAL,
            channels=[AlertChannel.EMAIL, AlertChannel.WEBHOOK, AlertChannel.PAGERDUTY],
            tags=["production", "ml", "model-performance"]
        )
    ]
    
    for rule in rules:
        alert_manager.add_alert_rule(rule)
    
    print(f"✅ Configured {len(rules)} alert rules")
    
    # Start alert manager
    await alert_manager.start()
    
    # Create comprehensive dashboard widgets
    widgets = [
        DashboardWidget(
            widget_id="prod-cpu-card",
            widget_type=WidgetType.METRIC_CARD,
            title="Production CPU",
            position={"x": 0, "y": 0, "w": 2, "h": 1}
        ),
        DashboardWidget(
            widget_id="model-accuracy-chart",
            widget_type=WidgetType.LINE_CHART,
            title="Model Accuracy Trend",
            position={"x": 2, "y": 0, "w": 4, "h": 2}
        ),
        DashboardWidget(
            widget_id="production-alerts",
            widget_type=WidgetType.ALERT_LIST,
            title="Production Alerts",
            position={"x": 0, "y": 2, "w": 3, "h": 2}
        )
    ]
    
    for widget in widgets:
        dashboard.add_widget(widget)
    
    print(f"✅ Created {len(widgets)} dashboard widgets")
    
    # Simulate comprehensive monitoring workflow
    print(f"\nSimulating comprehensive monitoring workflow...")
    
    # Log system startup
    logger.info("Comprehensive observability system started")
    logger.log_event("system_startup", {
        "components": ["logging", "metrics", "alerting", "dashboard"],
        "environment": "production"
    })
    
    # Record baseline metrics
    baseline_metrics = {
        "cpu_usage_percent": 45.2,
        "memory_usage_percent": 62.8,
        "model_accuracy": 0.94,
        "response_time_ms": 89.3,
        "throughput_rps": 125.7
    }
    
    for metric_name, value in baseline_metrics.items():
        metrics.record_gauge(
            metric_name,
            value,
            tags={"environment": "production", "component": "baseline"}
        )
        logger.log_metric(metric_name, value, {"component": "baseline"})
    
    print(f"✅ Recorded baseline metrics: {len(baseline_metrics)} metrics")
    
    # Simulate some activity and log it
    activities = [
        ("model_inference", {"model": "sentiment_model", "requests": 1000, "avg_latency": 45}),
        ("data_processing", {"records_processed": 50000, "processing_time": 120}),
        ("model_retraining", {"training_samples": 100000, "accuracy_improvement": 0.02}),
        ("deployment", {"model_version": "3.1.0", "environment": "production"})
    ]
    
    for activity, data in activities:
        logger.log_event(activity, data)
        logger.info(f"Completed {activity} activity", **data)
    
    print(f"✅ Logged {len(activities)} system activities")
    
    # Get comprehensive status
    print(f"\n📊 Comprehensive Observability Status:")
    
    # Metrics overview
    metrics_overview = metrics.get_metrics_overview()
    print(f"  Metrics: {metrics_overview['total_metrics']} metrics, {metrics_overview['total_data_points']} data points")
    
    # Alert statistics
    alert_stats = alert_manager.get_alert_statistics()
    print(f"  Alerts: {alert_stats['active_alerts']} active, {alert_stats['total_alerts']} total")
    print(f"  Rules: {alert_stats['enabled_rules']}/{alert_stats['total_rules']} enabled")
    
    # Dashboard summary
    dashboard_summary = dashboard.get_dashboard_summary()
    print(f"  Dashboard: {dashboard_summary['total_widgets']} widgets, {dashboard_summary['layout']} layout")
    
    # Cleanup
    metrics.close()
    await alert_manager.stop()
    
    print(f"\n🎉 Comprehensive observability workflow completed!")
    print(f"   The system provides end-to-end observability for ML operations!")
    
    # Clean up log files
    import os
    for log_file in ["demo_ml_observability.log", "demo_audit.log", "audit.log"]:
        if os.path.exists(log_file):
            os.remove(log_file)


async def main():
    """Run all observability demos."""
    print("📊 Advanced Observability & Dashboards Demo (Phase 5D.4)")
    print("=" * 60)
    
    try:
        # Run individual demos
        await demo_dashboard_system()
        await demo_alerting_system()
        await demo_logging_system()
        await demo_metrics_system()
        
        # Run comprehensive integration demo
        await demo_comprehensive_observability()
        
        print("\n" + "="*60)
        print("🎉 All observability demos completed successfully!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error running observability demos: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
