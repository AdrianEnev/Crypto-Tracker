#!/usr/bin/env python3
"""
Demo script for Risk Management & Compliance Monitoring (Phase 5D.5).
Demonstrates comprehensive risk assessment, compliance monitoring, and bias detection capabilities.
"""

import sys
import os
import time
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, str(project_root))

from src.ml.risk import (
    RiskAssessor, RiskLevel, RiskCategory, RiskEvent, RiskMitigation,
    ComplianceMonitor, ComplianceRule, ComplianceViolation, ComplianceFramework,
    BiasDetector, BiasMetric, BiasReport, FairnessConstraint
)


def demo_risk_assessment():
    """Demonstrate risk assessment system functionality."""
    print("\n" + "="*60)
    print("⚠️ DEMO: Risk Assessment System")
    print("="*60)
    
    # Create risk assessor
    risk_assessor = RiskAssessor()
    
    print("Risk assessor initialized with default risk categories and thresholds")
    print(f"Risk thresholds: {risk_assessor.risk_thresholds}")
    
    # Demonstrate various risk assessments
    print(f"\nPerforming risk assessments...")
    
    # Data Quality Risk Assessment
    data_quality_context = {
        'missing_data_percent': 25.5,
        'outlier_percent': 18.2,
        'data_age_days': 45
    }
    
    data_quality_risk = risk_assessor.assess_risk(
        RiskCategory.DATA_QUALITY,
        data_quality_context,
        "data_pipeline"
    )
    
    if data_quality_risk:
        print(f"  Data Quality Risk: {data_quality_risk.title}")
        print(f"    Level: {data_quality_risk.level.value}")
        print(f"    Score: {data_quality_risk.risk_score:.2f}")
        print(f"    Description: {data_quality_risk.description}")
    
    # Model Performance Risk Assessment
    model_performance_context = {
        'accuracy': 0.72,
        'precision': 0.68,
        'recall': 0.75,
        'f1_score': 0.71,
        'prediction_drift': 0.25
    }
    
    performance_risk = risk_assessor.assess_risk(
        RiskCategory.MODEL_PERFORMANCE,
        model_performance_context,
        "model_monitor"
    )
    
    if performance_risk:
        print(f"  Model Performance Risk: {performance_risk.title}")
        print(f"    Level: {performance_risk.level.value}")
        print(f"    Score: {performance_risk.risk_score:.2f}")
        print(f"    Description: {performance_risk.description}")
    
    # Security Risk Assessment
    security_context = {
        'failed_logins': 15,
        'suspicious_requests': 8,
        'data_access_anomalies': 5,
        'model_tampering_detected': False
    }
    
    security_risk = risk_assessor.assess_risk(
        RiskCategory.SECURITY,
        security_context,
        "security_monitor"
    )
    
    if security_risk:
        print(f"  Security Risk: {security_risk.title}")
        print(f"    Level: {security_risk.level.value}")
        print(f"    Score: {security_risk.risk_score:.2f}")
        print(f"    Description: {security_risk.description}")
    
    # Privacy Risk Assessment
    privacy_context = {
        'pii_detected': True,
        'data_retention_violation': False,
        'consent_expired': True,
        'cross_border_transfer': False
    }
    
    privacy_risk = risk_assessor.assess_risk(
        RiskCategory.PRIVACY,
        privacy_context,
        "privacy_monitor"
    )
    
    if privacy_risk:
        print(f"  Privacy Risk: {privacy_risk.title}")
        print(f"    Level: {privacy_risk.level.value}")
        print(f"    Score: {privacy_risk.risk_score:.2f}")
        print(f"    Description: {privacy_risk.description}")
    
    # Financial Risk Assessment
    financial_context = {
        'trading_loss': 15000.0,
        'max_drawdown': 0.18,
        'var_violation': True,
        'position_concentration': 0.35
    }
    
    financial_risk = risk_assessor.assess_risk(
        RiskCategory.FINANCIAL,
        financial_context,
        "risk_manager"
    )
    
    if financial_risk:
        print(f"  Financial Risk: {financial_risk.title}")
        print(f"    Level: {financial_risk.level.value}")
        print(f"    Score: {financial_risk.risk_score:.2f}")
        print(f"    Description: {financial_risk.description}")
    
    # Create mitigation strategies
    print(f"\nCreating mitigation strategies...")
    
    active_risks = risk_assessor.get_active_risks()
    for risk in active_risks[:2]:  # Create mitigations for first 2 risks
        if risk.mitigation_strategies:
            strategy = risk.mitigation_strategies[0]
            mitigation = risk_assessor.create_mitigation(
                risk_id=risk.risk_id,
                strategy=strategy,
                description=f"Implement {strategy} to address {risk.title}",
                effectiveness=0.8,
                cost=5000.0,
                timeframe="2 weeks",
                responsible_party="ML Engineering Team"
            )
            
            if mitigation:
                print(f"  Created mitigation: {mitigation.strategy}")
                print(f"    Effectiveness: {mitigation.effectiveness:.1%}")
                print(f"    Cost: ${mitigation.cost:,.2f}")
                print(f"    Timeframe: {mitigation.timeframe}")
    
    # Resolve some risks
    if active_risks:
        resolved_risk = active_risks[0]
        risk_assessor.resolve_risk(resolved_risk.risk_id, "admin")
        print(f"  Resolved risk: {resolved_risk.title}")
    
    # Get risk statistics
    stats = risk_assessor.get_risk_statistics()
    print(f"\nRisk Assessment Statistics:")
    print(f"  Total risks: {stats['total_risks']}")
    print(f"  Active risks: {stats['active_risks']}")
    print(f"  Resolved risks: {stats['resolved_risks']}")
    print(f"  Average risk score: {stats['average_risk_score']:.2f}")
    print(f"  Risk level distribution: {stats['risk_level_distribution']}")
    print(f"  Risk category distribution: {stats['risk_category_distribution']}")
    
    print(f"\n✅ Risk assessment system demo completed!")


def demo_compliance_monitoring():
    """Demonstrate compliance monitoring system functionality."""
    print("\n" + "="*60)
    print("📋 DEMO: Compliance Monitoring System")
    print("="*60)
    
    # Create compliance monitor
    compliance_monitor = ComplianceMonitor()
    
    print("Compliance monitor initialized with default frameworks and rules")
    print(f"Available frameworks: {[f.value for f in ComplianceFramework]}")
    print(f"Total rules: {len(compliance_monitor.compliance_rules)}")
    
    # List some compliance rules
    print(f"\nSample compliance rules:")
    for rule_id, rule in list(compliance_monitor.compliance_rules.items())[:3]:
        print(f"  {rule.rule_name} ({rule.framework.value})")
        print(f"    Severity: {rule.severity}")
        print(f"    Automated: {rule.automated_check}")
        print(f"    Review frequency: {rule.review_frequency}")
    
    # Run automated compliance checks
    print(f"\nRunning automated compliance checks...")
    violations = compliance_monitor.run_compliance_checks()
    
    print(f"Compliance checks completed: {len(violations)} violations found")
    
    for violation in violations:
        print(f"  Violation: {violation.description}")
        print(f"    Framework: {violation.framework.value}")
        print(f"    Severity: {violation.severity}")
        print(f"    Type: {violation.violation_type}")
        if violation.evidence:
            print(f"    Evidence: {', '.join(violation.evidence)}")
    
    # Create manual violation
    if violations:
        manual_violation = compliance_monitor.create_manual_violation(
            rule_id=violations[0].rule_id,
            description="Manual audit discovered additional compliance issues",
            severity="high",
            detected_by="auditor",
            evidence=["Manual review findings", "Policy gap analysis"]
        )
        
        if manual_violation:
            print(f"\nCreated manual violation: {manual_violation.description}")
    
    # Acknowledge and assign violations
    open_violations = compliance_monitor.get_open_violations()
    if open_violations:
        violation = open_violations[0]
        
        # Acknowledge
        compliance_monitor.acknowledge_violation(violation.violation_id, "compliance_officer")
        print(f"\nAcknowledged violation: {violation.violation_id}")
        
        # Assign for remediation
        compliance_monitor.assign_violation(
            violation.violation_id,
            assigned_to="ml_team_lead",
            remediation_plan="Implement automated data validation and consent management system"
        )
        print(f"Assigned violation to: ml_team_lead")
        
        # Resolve
        compliance_monitor.resolve_violation(
            violation.violation_id,
            resolved_by="ml_team_lead",
            resolution_notes="Implemented required controls and validated compliance"
        )
        print(f"Resolved violation with notes")
    
    # Get compliance statistics
    stats = compliance_monitor.get_violation_statistics()
    print(f"\nCompliance Statistics:")
    print(f"  Total violations: {stats['total_violations']}")
    print(f"  Open violations: {stats['open_violations']}")
    print(f"  Resolved violations: {stats['resolved_violations']}")
    print(f"  Severity distribution: {stats['severity_distribution']}")
    print(f"  Framework distribution: {stats['framework_distribution']}")
    
    # Get compliance status for specific frameworks
    print(f"\nCompliance Status by Framework:")
    for framework in [ComplianceFramework.GDPR, ComplianceFramework.AI_ACT, ComplianceFramework.CCPA]:
        status = compliance_monitor.get_compliance_status(framework)
        print(f"  {framework.value}:")
        print(f"    Compliance score: {status['compliance_score']:.2%}")
        print(f"    Compliance level: {status['compliance_level']}")
        print(f"    Total rules: {status['total_rules']}")
        print(f"    Violated rules: {status['violated_rules']}")
    
    print(f"\n✅ Compliance monitoring system demo completed!")


def demo_bias_detection():
    """Demonstrate bias detection and fairness monitoring functionality."""
    print("\n" + "="*60)
    print("⚖️ DEMO: Bias Detection & Fairness Monitoring")
    print("="*60)
    
    # Create bias detector
    bias_detector = BiasDetector()
    
    print("Bias detector initialized with fairness thresholds")
    print(f"Fairness thresholds: {bias_detector.fairness_thresholds}")
    
    # Generate synthetic data for bias assessment
    print(f"\nGenerating synthetic data for bias assessment...")
    
    # Create synthetic predictions and ground truth with bias
    np.random.seed(42)
    n_samples = 1000
    
    # Ground truth (balanced)
    ground_truth = np.random.binomial(1, 0.5, n_samples)
    
    # Protected attributes (gender, race)
    gender = np.random.choice(['male', 'female'], n_samples, p=[0.6, 0.4])
    race = np.random.choice(['white', 'black', 'hispanic', 'asian'], n_samples, p=[0.5, 0.2, 0.2, 0.1])
    
    # Predictions with bias (introduce bias against certain groups)
    predictions = np.zeros(n_samples)
    
    # Bias against female and minority groups
    for i in range(n_samples):
        base_prob = 0.6 if ground_truth[i] == 1 else 0.3
        
        # Reduce probability for female
        if gender[i] == 'female':
            base_prob *= 0.8
        
        # Reduce probability for minority groups
        if race[i] in ['black', 'hispanic']:
            base_prob *= 0.7
        
        predictions[i] = np.random.binomial(1, base_prob)
    
    # Convert to probabilities for bias metrics calculation
    predictions_prob = predictions.astype(float)
    
    # Assess bias for gender
    print(f"Assessing bias for gender attribute...")
    gender_report = bias_detector.assess_bias(
        model_name="loan_approval_model",
        model_version="1.0.0",
        predictions=predictions_prob,
        ground_truth=ground_truth,
        protected_attributes={'gender': gender},
        metadata={'dataset': 'synthetic_loan_data', 'n_samples': n_samples}
    )
    
    print(f"  Gender Bias Report:")
    print(f"    Assessment: {gender_report.fairness_assessment}")
    print(f"    Severity: {gender_report.bias_severity}")
    print(f"    Metrics: {list(gender_report.bias_metrics['gender'].keys())}")
    
    # Show specific bias metrics
    gender_metrics = gender_report.bias_metrics['gender']
    print(f"    Key metrics:")
    for metric_name, value in list(gender_metrics.items())[:4]:
        print(f"      {metric_name}: {value:.3f}")
    
    # Assess bias for race
    print(f"\nAssessing bias for race attribute...")
    race_report = bias_detector.assess_bias(
        model_name="loan_approval_model",
        model_version="1.0.0",
        predictions=predictions_prob,
        ground_truth=ground_truth,
        protected_attributes={'race': race},
        metadata={'dataset': 'synthetic_loan_data', 'n_samples': n_samples}
    )
    
    print(f"  Race Bias Report:")
    print(f"    Assessment: {race_report.fairness_assessment}")
    print(f"    Severity: {race_report.bias_severity}")
    
    # Show recommendations
    print(f"\nRecommendations from bias reports:")
    for i, recommendation in enumerate(gender_report.recommendations[:3], 1):
        print(f"  {i}. {recommendation}")
    
    # Test fairness constraints
    print(f"\nTesting fairness constraints...")
    
    # Check demographic parity constraint
    dp_constraint_satisfied = bias_detector.check_fairness_constraint(
        FairnessConstraint.DEMOGRAPHIC_PARITY_CONSTRAINT,
        predictions_prob,
        ground_truth,
        gender,
        threshold=0.8
    )
    print(f"  Demographic Parity Constraint: {'Satisfied' if dp_constraint_satisfied else 'Violated'}")
    
    # Check equal opportunity constraint
    eo_constraint_satisfied = bias_detector.check_fairness_constraint(
        FairnessConstraint.EQUAL_OPPORTUNITY_CONSTRAINT,
        predictions_prob,
        ground_truth,
        gender,
        threshold=0.8
    )
    print(f"  Equal Opportunity Constraint: {'Satisfied' if eo_constraint_satisfied else 'Violated'}")
    
    # List bias reports
    reports = bias_detector.list_bias_reports()
    print(f"\nBias Reports Generated:")
    for report in reports:
        print(f"  {report.model_name}:{report.model_version} - {report.fairness_assessment} ({report.bias_severity})")
    
    # Get bias statistics
    stats = bias_detector.get_bias_statistics()
    print(f"\nBias Detection Statistics:")
    print(f"  Total reports: {stats['total_reports']}")
    print(f"  Fairness assessment distribution: {stats['fairness_assessment_distribution']}")
    print(f"  Bias severity distribution: {stats['bias_severity_distribution']}")
    print(f"  Protected attributes covered: {stats['protected_attributes_covered']}")
    
    print(f"\n✅ Bias detection system demo completed!")


def demo_comprehensive_risk_management():
    """Demonstrate comprehensive risk management workflow."""
    print("\n" + "="*60)
    print("🎯 DEMO: Comprehensive Risk Management Workflow")
    print("="*60)
    
    print("This demo showcases a complete risk management pipeline:")
    print("1. Risk Assessment - Comprehensive risk evaluation across all categories")
    print("2. Compliance Monitoring - Regulatory compliance tracking and violation detection")
    print("3. Bias Detection - Fairness monitoring and bias mitigation")
    print("4. Integrated Risk Dashboard - Unified view of all risk factors")
    
    # Create all risk management components
    risk_assessor = RiskAssessor()
    compliance_monitor = ComplianceMonitor()
    bias_detector = BiasDetector()
    
    print(f"\n✅ All risk management components initialized")
    
    # Simulate comprehensive risk assessment
    print(f"\nPerforming comprehensive risk assessment...")
    
    # Multiple risk scenarios
    risk_scenarios = [
        {
            'category': RiskCategory.DATA_QUALITY,
            'context': {'missing_data_percent': 30, 'outlier_percent': 20, 'data_age_days': 60},
            'source': 'data_pipeline_monitor'
        },
        {
            'category': RiskCategory.MODEL_PERFORMANCE,
            'context': {'accuracy': 0.65, 'precision': 0.62, 'recall': 0.68, 'prediction_drift': 0.35},
            'source': 'model_performance_monitor'
        },
        {
            'category': RiskCategory.SECURITY,
            'context': {'failed_logins': 25, 'suspicious_requests': 12, 'data_access_anomalies': 8},
            'source': 'security_monitor'
        },
        {
            'category': RiskCategory.FINANCIAL,
            'context': {'trading_loss': 25000, 'max_drawdown': 0.22, 'var_violation': True},
            'source': 'risk_manager'
        }
    ]
    
    assessed_risks = []
    for scenario in risk_scenarios:
        risk = risk_assessor.assess_risk(
            scenario['category'],
            scenario['context'],
            scenario['source']
        )
        if risk:
            assessed_risks.append(risk)
    
    print(f"✅ Assessed {len(assessed_risks)} risks across multiple categories")
    
    # Run compliance checks
    print(f"\nRunning compliance monitoring...")
    compliance_violations = compliance_monitor.run_compliance_checks()
    print(f"✅ Found {len(compliance_violations)} compliance violations")
    
    # Perform bias assessment
    print(f"\nPerforming bias assessment...")
    
    # Generate biased synthetic data
    np.random.seed(123)
    n_samples = 500
    ground_truth = np.random.binomial(1, 0.5, n_samples)
    gender = np.random.choice(['male', 'female'], n_samples, p=[0.7, 0.3])
    
    # Create biased predictions
    predictions = np.zeros(n_samples)
    for i in range(n_samples):
        base_prob = 0.7 if ground_truth[i] == 1 else 0.3
        if gender[i] == 'female':
            base_prob *= 0.6  # Strong bias against females
        predictions[i] = np.random.binomial(1, base_prob)
    
    bias_report = bias_detector.assess_bias(
        model_name="hiring_model",
        model_version="2.0.0",
        predictions=predictions.astype(float),
        ground_truth=ground_truth,
        protected_attributes={'gender': gender},
        metadata={'domain': 'hr', 'decision_type': 'hiring'}
    )
    
    print(f"✅ Bias assessment completed: {bias_report.fairness_assessment} ({bias_report.bias_severity})")
    
    # Create integrated risk dashboard data
    print(f"\n📊 Integrated Risk Dashboard Summary:")
    
    # Risk assessment summary
    risk_stats = risk_assessor.get_risk_statistics()
    print(f"  Risk Assessment:")
    print(f"    Active risks: {risk_stats['active_risks']}")
    print(f"    Average risk score: {risk_stats['average_risk_score']:.2f}")
    print(f"    Critical risks: {risk_stats['risk_level_distribution'].get('critical', 0)}")
    
    # Compliance summary
    compliance_stats = compliance_monitor.get_violation_statistics()
    print(f"  Compliance Monitoring:")
    print(f"    Open violations: {compliance_stats['open_violations']}")
    print(f"    Critical violations: {compliance_stats['severity_distribution'].get('critical', 0)}")
    print(f"    Compliance frameworks: {len(compliance_stats['framework_distribution'])}")
    
    # Bias detection summary
    bias_stats = bias_detector.get_bias_statistics()
    print(f"  Bias Detection:")
    print(f"    Total bias reports: {bias_stats['total_reports']}")
    print(f"    Unfair models: {bias_stats['fairness_assessment_distribution'].get('unfair', 0)}")
    print(f"    Protected attributes: {bias_stats['total_protected_attributes']}")
    
    # Overall risk score calculation
    total_risk_score = (
        risk_stats['average_risk_score'] * 0.4 +  # 40% weight for operational risks
        (1 - compliance_stats['open_violations'] / max(compliance_stats['total_violations'], 1)) * 10 * 0.3 +  # 30% weight for compliance
        (1 - bias_stats['fairness_assessment_distribution'].get('unfair', 0) / max(bias_stats['total_reports'], 1)) * 10 * 0.3  # 30% weight for fairness
    )
    
    print(f"\n🎯 Overall Risk Score: {total_risk_score:.2f}/10")
    
    if total_risk_score >= 8:
        overall_risk_level = "LOW"
    elif total_risk_score >= 6:
        overall_risk_level = "MEDIUM"
    elif total_risk_score >= 4:
        overall_risk_level = "HIGH"
    else:
        overall_risk_level = "CRITICAL"
    
    print(f"   Risk Level: {overall_risk_level}")
    
    # Generate recommendations
    print(f"\n📋 Integrated Recommendations:")
    
    if risk_stats['active_risks'] > 0:
        print(f"  1. Address {risk_stats['active_risks']} active operational risks")
    
    if compliance_stats['open_violations'] > 0:
        print(f"  2. Resolve {compliance_stats['open_violations']} compliance violations")
    
    if bias_stats['fairness_assessment_distribution'].get('unfair', 0) > 0:
        print(f"  3. Mitigate bias in {bias_stats['fairness_assessment_distribution'].get('unfair', 0)} unfair models")
    
    if overall_risk_level in ['HIGH', 'CRITICAL']:
        print(f"  4. Implement comprehensive risk mitigation strategy")
        print(f"  5. Increase monitoring frequency and reporting")
        print(f"  6. Conduct executive risk review")
    
    print(f"\n🎉 Comprehensive risk management workflow completed!")
    print(f"   The system provides enterprise-grade risk management for ML operations!")


def main():
    """Run all risk management demos."""
    print("⚠️ Risk Management & Compliance Monitoring Demo (Phase 5D.5)")
    print("=" * 60)
    
    try:
        # Run individual demos
        demo_risk_assessment()
        demo_compliance_monitoring()
        demo_bias_detection()
        
        # Run comprehensive integration demo
        demo_comprehensive_risk_management()
        
        print("\n" + "="*60)
        print("🎉 All risk management demos completed successfully!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error running risk management demos: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
