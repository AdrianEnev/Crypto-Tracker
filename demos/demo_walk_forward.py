"""
Demo script for walk-forward validation and enhanced backtesting.
Shows time-series cross-validation for robust strategy evaluation.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from src.backtest.walk_forward import WalkForwardValidator
from src.strategies.volatility import VolatilityStrategy
from src.strategies.mean_reversion import MeanReversionStrategy


def generate_extended_market_data():
    """Generate extended market data for walk-forward validation."""
    np.random.seed(42)
    
    # Generate 5 years of daily data for comprehensive validation
    n_days = 1825  # ~5 years
    dates = pd.date_range('2019-01-01', periods=n_days, freq='D')
    
    # Create different market regimes over time
    returns = []
    
    # 2019: Bull market
    bull_returns_2019 = np.random.normal(0.0008, 0.015, 365)
    
    # 2020: Volatile year with COVID crash and recovery
    covid_crash = np.random.normal(-0.001, 0.03, 90)  # March crash
    covid_recovery = np.random.normal(0.0015, 0.02, 275)  # Recovery
    volatile_2020 = np.concatenate([covid_crash, covid_recovery])
    
    # 2021: Strong bull market
    strong_bull_2021 = np.random.normal(0.0012, 0.018, 365)
    
    # 2022: Bear market
    bear_2022 = np.random.normal(-0.0005, 0.022, 365)
    
    # 2023: Sideways/slow recovery
    sideways_2023 = np.random.normal(0.0002, 0.016, 365)
    
    all_returns = np.concatenate([bull_returns_2019, volatile_2020, strong_bull_2021, bear_2022, sideways_2023])
    
    # Create DataFrame with price data
    prices = 100 * np.cumprod(1 + all_returns)
    
    market_data = pd.DataFrame({
        'date': dates,
        'close': prices,
        'returns': all_returns,
        'volume': np.random.randint(1000000, 5000000, len(dates))
    })
    
    return market_data


def demo_rolling_window_validation():
    """Demo rolling window validation."""
    print("=== Rolling Window Validation Demo ===\n")
    
    # Generate market data
    print("Generating extended market data...")
    market_data = generate_extended_market_data()
    print(f"Generated {len(market_data)} days of market data")
    print(f"Date range: {market_data['date'].min()} to {market_data['date'].max()}")
    
    # Create validator with rolling window configuration
    validator_config = {
        "initial_train_size": 252,  # 1 year training
        "test_size": 63,           # ~3 months testing
        "step_size": 21,           # ~1 month step
        "max_train_size": 504,     # 2 years max training
        "validation_schemes": ["rolling_window"],
        "metrics_to_track": ["total_return", "sharpe_ratio", "max_drawdown", "win_rate", "profit_factor"]
    }
    
    validator = WalkForwardValidator(validator_config)
    
    # Create strategy
    strategy_config = {
        "mode": "adaptive",
        "vol_period": 20,
        "vol_threshold_low": 1.0,
        "vol_threshold_high": 2.0,
        "volume_confirmation": True
    }
    
    print(f"\nRunning rolling window validation...")
    print(f"Strategy: Volatility Strategy (Adaptive Mode)")
    print(f"Training size: {validator_config['initial_train_size']} days")
    print(f"Test size: {validator_config['test_size']} days")
    print(f"Step size: {validator_config['step_size']} days")
    
    results = validator.run_walk_forward_validation(
        strategy_class=VolatilityStrategy,
        strategy_params=strategy_config,
        data=market_data,
        initial_capital=10000.0
    )
    
    # Display results
    print("\n" + "="*60)
    print("ROLLING WINDOW VALIDATION RESULTS")
    print("="*60)
    
    rolling_results = results["validation_schemes"]["rolling_window"]
    fold_performances = rolling_results["fold_performance"]
    
    print(f"Total folds completed: {len(fold_performances)}")
    
    if fold_performances:
        # Calculate aggregate metrics
        total_returns = [fold.get("total_return", 0) for fold in fold_performances]
        sharpe_ratios = [fold.get("sharpe_ratio", 0) for fold in fold_performances]
        max_drawdowns = [fold.get("max_drawdown", 0) for fold in fold_performances]
        win_rates = [fold.get("win_rate", 0) for fold in fold_performances]
        
        print(f"\nAggregate Performance:")
        print(f"  Average Total Return: {np.mean(total_returns):.2f}% ± {np.std(total_returns):.2f}%")
        print(f"  Average Sharpe Ratio: {np.mean(sharpe_ratios):.2f} ± {np.std(sharpe_ratios):.2f}")
        print(f"  Average Max Drawdown: {np.mean(max_drawdowns):.2f}% ± {np.std(max_drawdowns):.2f}%")
        print(f"  Average Win Rate: {np.mean(win_rates):.2f}% ± {np.std(win_rates):.2f}%")
        
        # Performance consistency
        positive_folds = np.sum(np.array(total_returns) > 0)
        print(f"  Positive Folds: {positive_folds}/{len(total_returns)} ({positive_folds/len(total_returns)*100:.1f}%)")
        
        # Best and worst folds
        best_fold_idx = np.argmax(total_returns)
        worst_fold_idx = np.argmin(total_returns)
        print(f"  Best Fold Return: {total_returns[best_fold_idx]:.2f}%")
        print(f"  Worst Fold Return: {total_returns[worst_fold_idx]:.2f}%")
        
        # Performance range
        print(f"  Return Range: {np.min(total_returns):.2f}% to {np.max(total_returns):.2f}%")
    
    # Stability metrics
    stability_metrics = rolling_results["stability_metrics"]
    print(f"\nStability Metrics:")
    for metric, value in stability_metrics.items():
        if "cv" in metric:  # Coefficient of variation
            print(f"  {metric.replace('_cv', '')} CV: {value:.3f}")


def demo_multiple_validation_schemes():
    """Demo multiple validation schemes comparison."""
    print("\n=== Multiple Validation Schemes Demo ===\n")
    
    # Generate market data
    market_data = generate_extended_market_data()
    
    # Create validator with multiple schemes
    validator_config = {
        "initial_train_size": 252,
        "test_size": 63,
        "step_size": 21,
        "max_train_size": 504,
        "validation_schemes": ["rolling_window", "expanding_window", "purged_cv"],
        "metrics_to_track": ["total_return", "sharpe_ratio", "max_drawdown"]
    }
    
    validator = WalkForwardValidator(validator_config)
    
    # Create strategy
    strategy_config = {
        "rsi_period": 14,
        "buy_threshold": 30,
        "sell_threshold": 70,
        "use_bollinger": True,
        "require_confluence": True
    }
    
    print("Running multiple validation schemes...")
    print("Strategy: Mean Reversion Strategy")
    
    results = validator.run_walk_forward_validation(
        strategy_class=MeanReversionStrategy,
        strategy_params=strategy_config,
        data=market_data,
        initial_capital=10000.0
    )
    
    # Compare schemes
    print("\n" + "="*80)
    print("VALIDATION SCHEMES COMPARISON")
    print("="*80)
    
    overall_performance = results["overall_performance"]
    
    print(f"{'Scheme':<20} {'Mean Return':<12} {'Std Return':<12} {'Mean Sharpe':<12} {'Mean DD':<12}")
    print("-" * 80)
    
    for scheme_name, scheme_perf in overall_performance.items():
        tr = scheme_perf.get("total_return", {})
        sr = scheme_perf.get("sharpe_ratio", {})
        dd = scheme_perf.get("max_drawdown", {})
        
        print(f"{scheme_name.replace('_', ' ').title():<20} {tr.get('mean', 0):10.2f}% {tr.get('std', 0):10.2f}% {sr.get('mean', 0):10.2f} {dd.get('mean', 0):10.2f}%")
    
    # Parameter stability analysis
    parameter_stability = results["parameter_stability"]
    print(f"\nParameter Stability Analysis:")
    print("-" * 50)
    
    for scheme_name, scheme_stability in parameter_stability.items():
        stable_params = [param for param, stability in scheme_stability.items() if not stability.get("changed", False)]
        unstable_params = [param for param, stability in scheme_stability.items() if stability.get("changed", False)]
        
        print(f"{scheme_name.replace('_', ' ').title()}:")
        print(f"  Stable Parameters: {len(stable_params)}")
        print(f"  Unstable Parameters: {len(unstable_params)}")
        if unstable_params:
            print(f"  Unstable: {', '.join(unstable_params)}")


def demo_performance_degradation_analysis():
    """Demo performance degradation analysis."""
    print("\n=== Performance Degradation Analysis Demo ===\n")
    
    # Generate market data
    market_data = generate_extended_market_data()
    
    # Create validator
    validator_config = {
        "initial_train_size": 252,
        "test_size": 63,
        "step_size": 21,
        "validation_schemes": ["rolling_window", "expanding_window"],
        "metrics_to_track": ["total_return", "sharpe_ratio", "max_drawdown"]
    }
    
    validator = WalkForwardValidator(validator_config)
    
    # Create strategy
    strategy_config = {
        "mode": "adaptive",
        "vol_period": 20,
        "vol_threshold_low": 1.2,
        "vol_threshold_high": 2.5,
        "volume_confirmation": True
    }
    
    print("Analyzing performance degradation over time...")
    print("Strategy: Volatility Strategy")
    
    results = validator.run_walk_forward_validation(
        strategy_class=VolatilityStrategy,
        strategy_params=strategy_config,
        data=market_data,
        initial_capital=10000.0
    )
    
    # Analyze performance degradation
    print("\n" + "="*70)
    print("PERFORMANCE DEGRADATION ANALYSIS")
    print("="*70)
    
    performance_degradation = results["performance_degradation"]
    
    for scheme_name, scheme_degradation in performance_degradation.items():
        print(f"\n{scheme_name.replace('_', ' ').title()}:")
        print("-" * 40)
        
        for metric, degradation in scheme_degradation.items():
            trend_slope = degradation.get("trend_slope", 0)
            degradation_rate = degradation.get("degradation_rate", 0)
            is_degrading = degradation.get("is_degrading", False)
            
            status = "DEGRADING" if is_degrading else "STABLE"
            trend_direction = "improving" if trend_slope > 0 else "declining"
            
            print(f"  {metric.replace('_', ' ').title()}:")
            print(f"    Status: {status}")
            print(f"    Trend: {trend_direction} (slope: {trend_slope:.4f})")
            print(f"    Degradation Rate: {degradation_rate:.2%}")
    
    # Generate recommendations based on degradation
    print(f"\nRecommendations:")
    validation_summary = results["validation_summary"]
    for rec in validation_summary.get("recommendations", []):
        print(f"  - {rec}")


def demo_comprehensive_validation():
    """Demo comprehensive walk-forward validation with full reporting."""
    print("\n=== Comprehensive Walk-Forward Validation Demo ===\n")
    
    # Generate market data
    market_data = generate_extended_market_data()
    
    # Create validator with comprehensive configuration
    validator_config = {
        "initial_train_size": 252,
        "test_size": 63,
        "step_size": 21,
        "max_train_size": 756,  # 3 years max
        "validation_schemes": ["rolling_window", "expanding_window", "purged_cv", "blocking_cv"],
        "metrics_to_track": ["total_return", "sharpe_ratio", "max_drawdown", "win_rate", "profit_factor"]
    }
    
    validator = WalkForwardValidator(validator_config)
    
    # Create strategy
    strategy_config = {
        "mode": "adaptive",
        "vol_period": 20,
        "vol_threshold_low": 1.0,
        "vol_threshold_high": 2.0,
        "volume_confirmation": True
    }
    
    print("Running comprehensive walk-forward validation...")
    print("This may take a moment...")
    
    results = validator.run_walk_forward_validation(
        strategy_class=VolatilityStrategy,
        strategy_params=strategy_config,
        data=market_data,
        initial_capital=10000.0
    )
    
    # Generate and display comprehensive report
    report = validator.generate_validation_report(results)
    print(report)


def demo_strategy_robustness_comparison():
    """Demo comparison of strategy robustness using walk-forward validation."""
    print("\n=== Strategy Robustness Comparison Demo ===\n")
    
    # Generate market data
    market_data = generate_extended_market_data()
    
    # Create validator
    validator_config = {
        "initial_train_size": 252,
        "test_size": 63,
        "step_size": 21,
        "validation_schemes": ["rolling_window"],
        "metrics_to_track": ["total_return", "sharpe_ratio", "max_drawdown"]
    }
    
    validator = WalkForwardValidator(validator_config)
    
    # Define strategies to compare
    strategies = {
        "Volatility (Adaptive)": {
            "class": VolatilityStrategy,
            "params": {
                "mode": "adaptive",
                "vol_period": 20,
                "vol_threshold_low": 1.0,
                "vol_threshold_high": 2.0,
                "volume_confirmation": True
            }
        },
        "Volatility (Mean Reversion)": {
            "class": VolatilityStrategy,
            "params": {
                "mode": "mean_reversion",
                "vol_period": 20,
                "bb_stddev": 2.0,
                "volume_confirmation": True
            }
        },
        "Mean Reversion (RSI)": {
            "class": MeanReversionStrategy,
            "params": {
                "rsi_period": 14,
                "buy_threshold": 30,
                "sell_threshold": 70,
                "use_bollinger": True,
                "require_confluence": True
            }
        }
    }
    
    print("Comparing strategy robustness using walk-forward validation...")
    
    strategy_results = {}
    
    for strategy_name, strategy_info in strategies.items():
        print(f"\nTesting {strategy_name}...")
        
        results = validator.run_walk_forward_validation(
            strategy_class=strategy_info["class"],
            strategy_params=strategy_info["params"],
            data=market_data,
            initial_capital=10000.0
        )
        
        strategy_results[strategy_name] = results
    
    # Compare strategies
    print("\n" + "="*90)
    print("STRATEGY ROBUSTNESS COMPARISON")
    print("="*90)
    
    print(f"{'Strategy':<25} {'Mean Return':<12} {'Return CV':<10} {'Mean Sharpe':<12} {'Sharpe CV':<10} {'Mean DD':<10}")
    print("-" * 90)
    
    for strategy_name, results in strategy_results.items():
        rolling_results = results["validation_schemes"]["rolling_window"]
        stability_metrics = rolling_results["stability_metrics"]
        
        mean_return = stability_metrics.get("total_return_mean", 0)
        return_cv = stability_metrics.get("total_return_cv", 0)
        mean_sharpe = stability_metrics.get("sharpe_ratio_mean", 0)
        sharpe_cv = stability_metrics.get("sharpe_ratio_cv", 0)
        mean_dd = stability_metrics.get("max_drawdown_mean", 0)
        
        print(f"{strategy_name:<25} {mean_return:10.2f}% {return_cv:8.3f} {mean_sharpe:10.2f} {sharpe_cv:8.3f} {mean_dd:8.2f}%")
    
    # Validation quality comparison
    print(f"\nValidation Quality Assessment:")
    print("-" * 50)
    
    for strategy_name, results in strategy_results.items():
        validation_summary = results["validation_summary"]
        quality = validation_summary.get("validation_quality", "unknown")
        
        print(f"{strategy_name:<25} {quality.upper():<10}")
    
    print(f"\nKey Insights:")
    print("- Lower CV (Coefficient of Variation) indicates more consistent performance")
    print("- Higher mean returns with lower CV suggests better risk-adjusted performance")
    print("- Validation quality reflects overall robustness and reliability")


if __name__ == "__main__":
    demo_rolling_window_validation()
    demo_multiple_validation_schemes()
    demo_performance_degradation_analysis()
    demo_strategy_robustness_comparison()
    demo_comprehensive_validation()
    
    print("\n=== Demo Complete ===")
    print("\nKey Features of Walk-Forward Validation:")
    print("1. TIME-SERIES CROSS-VALIDATION: Proper validation for time-series data")
    print("2. MULTIPLE VALIDATION SCHEMES: Rolling, expanding, purged, and blocked CV")
    print("3. OUT-OF-SAMPLE TESTING: True performance validation without look-ahead bias")
    print("4. PERFORMANCE DEGRADATION ANALYSIS: Tracks strategy performance over time")
    print("5. PARAMETER STABILITY TESTING: Ensures strategy robustness across different periods")
    print("6. COMPREHENSIVE REPORTING: Detailed analysis and recommendations")
    print("\nBenefits:")
    print("- Provides realistic performance expectations")
    print("- Identifies strategy overfitting and degradation")
    print("- Enables robust strategy comparison and selection")
    print("- Supports regulatory backtesting requirements")
    print("- Reduces deployment risk through proper validation")
