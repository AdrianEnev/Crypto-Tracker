"""
Machine Learning module for intelligent trading strategies.
Provides ML-enhanced trading capabilities while preserving existing algorithms.
"""

from .feature_engineering import FeaturePipeline, TechnicalFeatures, OnChainFeatures
from .models import BaseModel, ModelMetadata, ParameterOptimizer, RegimeDetector, SignalEnhancer, PricePredictor
from .integration import MLEnhancedStrategy, MLStrategyConfig, StrategyEnsemble, EnsembleConfig, MLStrategyManager
from .monitoring import ModelPerformanceMonitor, PerformanceMetrics, ConceptDriftDetector, DataDriftDetector, DriftAlert, ModelHealthChecker, HealthStatus, MetricsCollector, SystemMetrics, TradingMetrics
from .optimization import HyperparameterOptimizer, OptimizationConfig, OptimizationResult, BayesianOptimizer, AcquisitionFunction, MultiObjectiveOptimizer, ParetoFront, Objective, CrossValidator, ValidationStrategy, ModelOptimizer, ModelOptimizationConfig, OptimizationObjective
from .deployment import ModelServer, ServerConfig, InferenceRequest, InferenceResponse, ModelRegistry, ModelVersion, DeploymentStatus, LoadBalancer, LoadBalancingStrategy, HealthCheck, AutoScaler, ScalingPolicy, ScalingRule, ScalingAction, DeploymentManager, DeploymentConfig, DeploymentStrategy, ModelCache, CachePolicy, APIGateway, GatewayConfig, RateLimit, Authentication
from .observability import Dashboard, DashboardWidget, DashboardConfig, WidgetType, MetricType, AlertManager, AlertRule, AlertChannel, AlertSeverity, AlertStatus, StructuredLogger, LogLevel, LogContext, AuditLogger, MetricsAggregator, MetricsQuery, TimeSeriesData, AggregationType
from .risk import RiskAssessor, RiskLevel, RiskCategory, RiskEvent, RiskMitigation, ComplianceMonitor, ComplianceRule, ComplianceViolation, ComplianceFramework, BiasDetector, BiasMetric, BiasReport, FairnessConstraint

# Phase 5D.5: Risk management and compliance monitoring implemented
# Phase 5D is now complete with comprehensive ML observability and risk management

__all__ = [
    'FeaturePipeline', 'TechnicalFeatures', 'OnChainFeatures',
    'BaseModel', 'ModelMetadata', 'ParameterOptimizer', 'RegimeDetector', 'SignalEnhancer', 'PricePredictor',
    'MLEnhancedStrategy', 'MLStrategyConfig', 'StrategyEnsemble', 'EnsembleConfig', 'MLStrategyManager',
    'ModelPerformanceMonitor', 'PerformanceMetrics', 'ConceptDriftDetector', 'DataDriftDetector', 'DriftAlert',
    'ModelHealthChecker', 'HealthStatus', 'MetricsCollector', 'SystemMetrics', 'TradingMetrics',
    'HyperparameterOptimizer', 'OptimizationConfig', 'OptimizationResult', 'BayesianOptimizer', 'AcquisitionFunction',
    'MultiObjectiveOptimizer', 'ParetoFront', 'Objective', 'CrossValidator', 'ValidationStrategy', 'ModelOptimizer', 'ModelOptimizationConfig', 'OptimizationObjective',
    'ModelServer', 'ServerConfig', 'InferenceRequest', 'InferenceResponse', 'ModelRegistry', 'ModelVersion', 'DeploymentStatus',
    'LoadBalancer', 'LoadBalancingStrategy', 'HealthCheck', 'AutoScaler', 'ScalingPolicy', 'ScalingRule', 'ScalingAction',
    'DeploymentManager', 'DeploymentConfig', 'DeploymentStrategy', 'ModelCache', 'CachePolicy', 'APIGateway', 'GatewayConfig', 'RateLimit', 'Authentication',
    'Dashboard', 'DashboardWidget', 'DashboardConfig', 'WidgetType', 'MetricType', 'AlertManager', 'AlertRule', 'AlertChannel', 'AlertSeverity', 'AlertStatus',
    'StructuredLogger', 'LogLevel', 'LogContext', 'AuditLogger', 'MetricsAggregator', 'MetricsQuery', 'TimeSeriesData', 'AggregationType',
    'RiskAssessor', 'RiskLevel', 'RiskCategory', 'RiskEvent', 'RiskMitigation', 'ComplianceMonitor', 'ComplianceRule', 'ComplianceViolation', 'ComplianceFramework',
    'BiasDetector', 'BiasMetric', 'BiasReport', 'FairnessConstraint'
]
