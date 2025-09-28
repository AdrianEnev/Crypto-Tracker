"""
Demo script for Monte Carlo stress testing and bootstrapping.
Shows different stress testing methodologies for robust strategy validation.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from src.backtest.stress_testing import MonteCarloStressTest
from src.strategies.volatility import VolatilityStrategy
from src.strategies.mean_reversion import MeanReversionStrategy


def generate_sample_returns_data():
    """Generate sample returns data for stress testing."""
    np.random.seed(42)
    
    # Generate realistic market returns with different regimes
    n_days = 1000
    dates = pd.date_range('2020-01-01', periods=n_days, freq='D')
    
    # Create returns with different volatility regimes
    returns = []
    
    # Bull market period (days 0-300)
    bull_returns = np.random.normal(0.0008, 0.015, 300)  # 0.08% daily return, 1.5% volatility
    
    # Bear market period (days 300-600)
    bear_returns = np.random.normal(-0.0005, 0.025, 300)  # -0.05% daily return, 2.5% volatility
    
    # Crisis period (days 600-800)
    crisis_returns = np.random.normal(-0.002, 0.05, 200)  # -0.2% daily return, 5% volatility
    
    # Recovery period (days 800-1000)
    recovery_returns = np.random.normal(0.001, 0.02, 200)  # 0.1% daily return, 2% volatility
    
    all_returns = np.concatenate([bull_returns, bear_returns, crisis_returns, recovery_returns])
    
    # Create DataFrame
    returns_df = pd.DataFrame({
        'date': dates,
        'returns': all_returns
    })
    
    return returns_df


def demo_bootstrap_stress_test():
    """Demo bootstrap stress testing."""
    print("=== Bootstrap Stress Testing Demo ===\n")
    
    # Generate sample data
    print("Generating sample returns data...")
    returns_data = generate_sample_returns_data()
    print(f"Generated {len(returns_data)} days of returns data")
    print(f"Mean return: {returns_data['returns'].mean():.4f}")
    print(f"Volatility: {returns_data['returns'].std():.4f}")
    print(f"Skewness: {returns_data['returns'].skew():.4f}")
    print(f"Kurtosis: {returns_data['returns'].kurtosis():.4f}")
    
    # Create strategy
    strategy_config = {
        "mode": "adaptive",
        "vol_period": 20,
        "vol_threshold_low": 0.5,
        "vol_threshold_high": 2.0,
        "volume_confirmation": True
    }
    strategy = VolatilityStrategy(strategy_config)
    
    # Configure stress test
    stress_test_config = {
        "num_simulations": 500,  # Reduced for demo
        "confidence_levels": [0.90, 0.95, 0.99],
        "bootstrap_samples": 1000
    }
    
    # Run bootstrap stress test
    stress_tester = MonteCarloStressTest(stress_test_config)
    
    print(f"\nRunning bootstrap stress test with {stress_test_config['num_simulations']} simulations...")
    results = stress_tester.run_bootstrap_stress_test(
        strategy=strategy,
        returns_data=returns_data[['returns']],
        initial_capital=10000.0,
        num_periods=252
    )
    
    if "error" in results:
        print(f"Error: {results['error']}")
        return
    
    # Display results
    print("\n" + "="*60)
    print("BOOTSTRAP STRESS TEST RESULTS")
    print("="*60)
    
    summary = results.get("summary_statistics", {})
    print(f"Mean Final Value: ${summary.get('mean_final_value', 0):.2f}")
    print(f"Mean Total Return: {summary.get('mean_total_return', 0):.2f}%")
    print(f"Mean Max Drawdown: {summary.get('mean_max_drawdown', 0):.2f}%")
    print(f"Worst Case Return: {summary.get('worst_case_return', 0):.2f}%")
    print(f"Best Case Return: {summary.get('best_case_return', 0):.2f}%")
    
    # Confidence intervals
    print(f"\nConfidence Intervals:")
    ci = results.get("confidence_intervals", {})
    for level, intervals in ci.items():
        print(f"  {level} Confidence:")
        print(f"    Final Value: ${intervals['final_value']['lower']:.2f} - ${intervals['final_value']['upper']:.2f}")
        print(f"    Total Return: {intervals['total_return']['lower']:.2f}% - {intervals['total_return']['upper']:.2f}%")
        print(f"    Max Drawdown: {intervals['max_drawdown']['lower']:.2f}% - {intervals['max_drawdown']['upper']:.2f}%")
    
    # Tail risk metrics
    print(f"\nTail Risk Metrics:")
    tail_risk = results.get("tail_risk_metrics", {})
    print(f"  VaR (95%): {tail_risk.get('var_95', 0):.2f}%")
    print(f"  VaR (99%): {tail_risk.get('var_99', 0):.2f}%")
    print(f"  CVaR (95%): {tail_risk.get('cvar_95', 0):.2f}%")
    print(f"  Worst Drawdown: {tail_risk.get('worst_drawdown', 0):.2f}%")
    print(f"  Tail Ratio: {tail_risk.get('tail_ratio', 0):.2f}")


def demo_crisis_stress_test():
    """Demo crisis stress testing."""
    print("\n=== Crisis Stress Testing Demo ===\n")
    
    # Generate sample data
    returns_data = generate_sample_returns_data()
    
    # Create strategy
    strategy_config = {
        "rsi_period": 14,
        "buy_threshold": 30,
        "sell_threshold": 70,
        "use_bollinger": True,
        "require_confluence": True
    }
    strategy = MeanReversionStrategy(strategy_config)
    
    # Configure crisis stress test
    stress_test_config = {
        "num_simulations": 300,
        "crisis_probability": 0.1,  # 10% chance of crisis per period
        "crisis_severity": 0.5,     # 50% severity multiplier
        "confidence_levels": [0.95, 0.99]
    }
    
    # Run crisis stress test
    stress_tester = MonteCarloStressTest(stress_test_config)
    
    print(f"Running crisis stress test with {stress_test_config['num_simulations']} simulations...")
    print(f"Crisis probability: {stress_test_config['crisis_probability']*100}% per period")
    print(f"Crisis severity: {stress_test_config['crisis_severity']*100}%")
    
    results = stress_tester.run_crisis_stress_test(
        strategy=strategy,
        returns_data=returns_data[['returns']],
        initial_capital=10000.0,
        num_periods=252
    )
    
    if "error" in results:
        print(f"Error: {results['error']}")
        return
    
    # Display results
    print("\n" + "="*60)
    print("CRISIS STRESS TEST RESULTS")
    print("="*60)
    
    crisis_metrics = results.get("crisis_metrics", {})
    print(f"Crisis Survival Rate: {crisis_metrics.get('crisis_survival_rate', 0):.1f}%")
    print(f"Mean Crisis Return: {crisis_metrics.get('mean_crisis_return', 0):.2f}%")
    print(f"Worst Crisis Return: {crisis_metrics.get('worst_crisis_return', 0):.2f}%")
    print(f"Mean Crisis Drawdown: {crisis_metrics.get('mean_crisis_drawdown', 0):.2f}%")
    print(f"Worst Crisis Drawdown: {crisis_metrics.get('worst_crisis_drawdown', 0):.2f}%")
    print(f"Crisis VaR (95%): {crisis_metrics.get('crisis_var_95', 0):.2f}%")
    print(f"Crisis VaR (99%): {crisis_metrics.get('crisis_var_99', 0):.2f}%")


def demo_correlation_stress_test():
    """Demo correlation stress testing."""
    print("\n=== Correlation Stress Testing Demo ===\n")
    
    # Generate multi-asset returns data
    np.random.seed(123)
    n_days = 500
    
    # Generate correlated returns
    correlation_levels = [0.3, 0.5, 0.7, 0.9]
    correlation_results = {}
    
    for corr in correlation_levels:
        print(f"Testing correlation level: {corr}")
        
        # Generate correlated returns
        mean_returns = [0.0005, 0.0003]  # Two assets
        cov_matrix = np.array([
            [0.02**2, corr * 0.02 * 0.025],
            [corr * 0.02 * 0.025, 0.025**2]
        ])
        
        correlated_returns = np.random.multivariate_normal(mean_returns, cov_matrix, n_days)
        
        returns_df = pd.DataFrame(correlated_returns, columns=['asset1', 'asset2'])
        
        # Create strategy
        strategy = VolatilityStrategy({"mode": "adaptive"})
        
        # Configure stress test
        stress_test_config = {
            "num_simulations": 200,
            "correlation_stress": corr
        }
        
        # Run correlation stress test
        stress_tester = MonteCarloStressTest(stress_test_config)
        
        results = stress_tester.run_correlation_stress_test(
            strategy=strategy,
            returns_data=returns_df,
            correlation_stress_levels=[corr],
            initial_capital=10000.0
        )
        
        if corr in results.get("correlation_results", {}):
            corr_result = results["correlation_results"][corr]
            correlation_results[corr] = {
                "mean_return": corr_result["mean_total_return"],
                "mean_drawdown": corr_result["mean_max_drawdown"],
                "var_95": corr_result["var_95"],
                "var_99": corr_result["var_99"]
            }
    
    # Display results
    print("\n" + "="*60)
    print("CORRELATION STRESS TEST RESULTS")
    print("="*60)
    print("Correlation | Mean Return | Mean DD | VaR 95% | VaR 99%")
    print("-" * 60)
    
    for corr, metrics in correlation_results.items():
        print(f"    {corr:.1f}     |    {metrics['mean_return']:6.2f}%   | {metrics['mean_drawdown']:6.2f}% | {metrics['var_95']:6.2f}% | {metrics['var_99']:6.2f}%")


def demo_regime_change_stress_test():
    """Demo regime change stress testing."""
    print("\n=== Regime Change Stress Testing Demo ===\n")
    
    # Generate sample data
    returns_data = generate_sample_returns_data()
    
    # Create strategy
    strategy = VolatilityStrategy({"mode": "adaptive"})
    
    # Configure regime change stress test
    stress_test_config = {
        "num_simulations": 200,
        "regime_change_probability": 0.05,
        "regime_volatility_mult": 1.5
    }
    
    # Run regime change stress test
    stress_tester = MonteCarloStressTest(stress_test_config)
    
    regime_types = ["bull_market", "bear_market", "high_volatility", "crisis"]
    
    print(f"Running regime change stress test with {len(regime_types)} regime types...")
    
    results = stress_tester.run_regime_change_stress_test(
        strategy=strategy,
        returns_data=returns_data[['returns']],
        regime_types=regime_types,
        initial_capital=10000.0,
        num_periods=252
    )
    
    if "error" in results:
        print(f"Error: {results['error']}")
        return
    
    # Display results
    print("\n" + "="*60)
    print("REGIME CHANGE STRESS TEST RESULTS")
    print("="*60)
    print("Regime Type      | Mean Return | Mean DD | Volatility | Mean Return")
    print("-" * 70)
    
    regime_results = results.get("regime_results", {})
    for regime, metrics in regime_results.items():
        print(f"{regime:15} |    {metrics['mean_total_return']:6.2f}%   | {metrics['mean_max_drawdown']:6.2f}% |    {metrics['regime_volatility']:8.4f} |    {metrics['regime_mean_return']:8.4f}")


def demo_comprehensive_stress_test():
    """Demo comprehensive stress testing report generation."""
    print("\n=== Comprehensive Stress Test Report Demo ===\n")
    
    # Generate sample data
    returns_data = generate_sample_returns_data()
    
    # Create strategy
    strategy = VolatilityStrategy({"mode": "adaptive"})
    
    # Configure stress test
    stress_test_config = {
        "num_simulations": 100,
        "confidence_levels": [0.90, 0.95, 0.99]
    }
    
    # Run bootstrap stress test
    stress_tester = MonteCarloStressTest(stress_test_config)
    
    print("Running comprehensive bootstrap stress test...")
    results = stress_tester.run_bootstrap_stress_test(
        strategy=strategy,
        returns_data=returns_data[['returns']],
        initial_capital=10000.0,
        num_periods=252
    )
    
    if "error" not in results:
        # Generate and display report
        report = stress_tester.generate_stress_test_report(results)
        print(report)
    else:
        print(f"Error: {results['error']}")


if __name__ == "__main__":
    demo_bootstrap_stress_test()
    demo_crisis_stress_test()
    demo_correlation_stress_test()
    demo_regime_change_stress_test()
    demo_comprehensive_stress_test()
    
    print("\n=== Demo Complete ===")
    print("\nKey Features of Monte Carlo Stress Testing:")
    print("1. BOOTSTRAP RESAMPLING: Tests strategy robustness using historical return distributions")
    print("2. CRISIS SIMULATION: Simulates extreme market conditions and crisis periods")
    print("3. CORRELATION STRESS: Tests performance under different asset correlation scenarios")
    print("4. REGIME CHANGE: Evaluates strategy performance across different market regimes")
    print("5. TAIL RISK ANALYSIS: Provides VaR, CVaR, and extreme loss probability metrics")
    print("6. CONFIDENCE INTERVALS: Statistical confidence bounds for performance metrics")
    print("\nBenefits:")
    print("- Identifies strategy vulnerabilities before live trading")
    print("- Provides realistic worst-case scenario analysis")
    print("- Enables risk-adjusted strategy comparison")
    print("- Supports regulatory stress testing requirements")
