"""
Demo script for crisis period simulation and tail risk analysis.
Shows historical crisis modeling and extreme scenario testing.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import pandas as pd
from datetime import datetime
from src.backtest.crisis_simulation import CrisisSimulator
from src.strategies.volatility import VolatilityStrategy
from src.strategies.mean_reversion import MeanReversionStrategy


def generate_realistic_market_data():
    """Generate realistic market data with different volatility regimes."""
    np.random.seed(42)
    
    # Generate 3 years of daily data
    n_days = 1095  # ~3 years
    dates = pd.date_range('2021-01-01', periods=n_days, freq='D')
    
    # Create different market regimes
    returns = []
    
    # Bull market (days 0-365) - Low volatility, positive returns
    bull_returns = np.random.normal(0.0008, 0.012, 365)
    
    # Sideways market (days 365-730) - Medium volatility, slightly negative returns
    sideways_returns = np.random.normal(-0.0001, 0.018, 365)
    
    # Volatile market (days 730-1095) - High volatility, mixed returns
    volatile_returns = np.random.normal(0.0002, 0.025, 365)
    
    all_returns = np.concatenate([bull_returns, sideways_returns, volatile_returns])
    
    # Create DataFrame
    market_data = pd.DataFrame({
        'date': dates,
        'returns': all_returns,
        'close': 100 * np.cumprod(1 + all_returns),
        'volume': np.random.randint(1000000, 5000000, len(dates))
    })
    
    return market_data


def demo_historical_crisis_simulation():
    """Demo historical crisis simulation."""
    print("=== Historical Crisis Simulation Demo ===\n")
    
    # Generate market data
    print("Generating realistic market data...")
    market_data = generate_realistic_market_data()
    returns = market_data['returns'].values
    
    print(f"Generated {len(returns)} days of market data")
    print(f"Mean return: {np.mean(returns):.4f}")
    print(f"Volatility: {np.std(returns):.4f}")
    print(f"Min return: {np.min(returns):.4f}")
    print(f"Max return: {np.max(returns):.4f}")
    
    # Create strategy
    strategy_config = {
        "mode": "adaptive",
        "vol_period": 20,
        "vol_threshold_low": 0.8,
        "vol_threshold_high": 2.0,
        "volume_confirmation": True
    }
    strategy = VolatilityStrategy(strategy_config)
    
    # Create crisis simulator
    crisis_config = {
        "crisis_severity_levels": [0.2, 0.3, 0.5],
        "crisis_duration_days": [30, 60, 90],
        "recovery_speed": 0.6
    }
    
    crisis_simulator = CrisisSimulator(crisis_config)
    
    print(f"\nTesting historical crisis scenarios...")
    
    # Test individual historical crisis
    crisis_name = "2008_financial_crisis"
    print(f"\nSimulating {crisis_name}...")
    
    result = crisis_simulator.simulate_historical_crisis(
        strategy=strategy,
        normal_returns=returns,
        crisis_name=crisis_name,
        initial_capital=10000.0
    )
    
    if "error" not in result:
        performance = result["performance"]
        crisis_data = result["crisis_data"]
        
        print(f"\n{crisis_name.replace('_', ' ').title()} Results:")
        print(f"  Description: {crisis_data['description']}")
        print(f"  Crisis Duration: {crisis_data['duration_days']} days")
        print(f"  Peak Drawdown: {crisis_data['peak_drawdown']*100:.1f}%")
        print(f"  Volatility Multiplier: {crisis_data['volatility_multiplier']:.1f}x")
        print(f"  Recovery Time: {crisis_data['recovery_time_days']} days")
        print(f"\n  Strategy Performance:")
        print(f"    Final Value: ${performance.get('final_value', 0):.2f}")
        print(f"    Total Return: {performance.get('total_return', 0):.2f}%")
        print(f"    Max Drawdown: {performance.get('max_drawdown', 0):.2f}%")
        print(f"    Crisis Volatility: {performance.get('crisis_volatility', 0):.2f}%")
        print(f"    Survival Rate: {performance.get('survival_rate', 0)*100:.1f}%")
    else:
        print(f"Error: {result['error']}")


def demo_synthetic_crisis_simulation():
    """Demo synthetic crisis simulation."""
    print("\n=== Synthetic Crisis Simulation Demo ===\n")
    
    # Generate market data
    market_data = generate_realistic_market_data()
    returns = market_data['returns'].values
    
    # Create strategy
    strategy = MeanReversionStrategy({
        "rsi_period": 14,
        "buy_threshold": 30,
        "sell_threshold": 70,
        "use_bollinger": True
    })
    
    # Create crisis simulator
    crisis_simulator = CrisisSimulator()
    
    # Test different synthetic crisis scenarios
    scenarios = [
        (0.2, 30, "Mild crisis, short duration"),
        (0.3, 60, "Moderate crisis, medium duration"),
        (0.5, 90, "Severe crisis, long duration")
    ]
    
    print("Testing synthetic crisis scenarios...")
    
    for severity, duration, description in scenarios:
        print(f"\nScenario: {description}")
        print(f"  Severity: {severity*100:.0f}%, Duration: {duration} days")
        
        result = crisis_simulator.simulate_synthetic_crisis(
            strategy=strategy,
            normal_returns=returns,
            severity=severity,
            duration_days=duration,
            initial_capital=10000.0
        )
        
        if "error" not in result:
            performance = result["performance"]
            print(f"  Strategy Performance:")
            print(f"    Final Value: ${performance.get('final_value', 0):.2f}")
            print(f"    Total Return: {performance.get('total_return', 0):.2f}%")
            print(f"    Max Drawdown: {performance.get('max_drawdown', 0):.2f}%")
            print(f"    Crisis Duration: {performance.get('crisis_duration', 0)} days")
            print(f"    Survival Rate: {performance.get('survival_rate', 0)*100:.1f}%")
        else:
            print(f"  Error: {result['error']}")


def demo_comprehensive_crisis_analysis():
    """Demo comprehensive crisis scenario analysis."""
    print("\n=== Comprehensive Crisis Analysis Demo ===\n")
    
    # Generate market data
    market_data = generate_realistic_market_data()
    returns = market_data['returns'].values
    
    # Create strategy
    strategy = VolatilityStrategy({
        "mode": "adaptive",
        "vol_period": 20,
        "vol_threshold_low": 1.0,
        "vol_threshold_high": 2.5,
        "volume_confirmation": True
    })
    
    # Create crisis simulator with comprehensive configuration
    crisis_config = {
        "crisis_severity_levels": [0.1, 0.2, 0.3, 0.4, 0.5],
        "crisis_duration_days": [15, 30, 60, 90],
        "recovery_speed": 0.7,
        "evt_threshold": 0.95,
        "evt_block_size": 252
    }
    
    crisis_simulator = CrisisSimulator(crisis_config)
    
    print("Running comprehensive crisis scenario analysis...")
    print("This may take a moment...")
    
    # Run comprehensive analysis
    results = crisis_simulator.run_crisis_scenario_analysis(
        strategy=strategy,
        normal_returns=returns,
        initial_capital=10000.0
    )
    
    # Generate and display report
    report = crisis_simulator.generate_crisis_report(results)
    print(report)


def demo_tail_risk_analysis():
    """Demo tail risk analysis and extreme value theory."""
    print("\n=== Tail Risk Analysis Demo ===\n")
    
    # Generate market data with extreme events
    np.random.seed(123)
    
    # Create returns with fat tails (higher probability of extreme events)
    n_days = 1000
    normal_returns = np.random.normal(0.0005, 0.015, n_days)
    
    # Add extreme events (simulating market crashes)
    extreme_events = np.random.choice([-0.05, -0.08, -0.12], size=20)  # 20 extreme negative events
    extreme_indices = np.random.choice(n_days, size=20, replace=False)
    
    returns_with_extremes = normal_returns.copy()
    returns_with_extremes[extreme_indices] = extreme_events
    
    print(f"Generated {len(returns_with_extremes)} days of returns with extreme events")
    print(f"Mean return: {np.mean(returns_with_extremes):.4f}")
    print(f"Volatility: {np.std(returns_with_extremes):.4f}")
    print(f"Skewness: {pd.Series(returns_with_extremes).skew():.4f}")
    print(f"Kurtosis: {pd.Series(returns_with_extremes).kurtosis():.4f}")
    print(f"Min return: {np.min(returns_with_extremes):.4f}")
    print(f"Max return: {np.max(returns_with_extremes):.4f}")
    
    # Create strategy
    strategy = MeanReversionStrategy({
        "rsi_period": 14,
        "buy_threshold": 25,
        "sell_threshold": 75
    })
    
    # Create crisis simulator
    crisis_simulator = CrisisSimulator()
    
    # Run crisis analysis to get tail risk metrics
    print(f"\nRunning crisis analysis for tail risk assessment...")
    
    results = crisis_simulator.run_crisis_scenario_analysis(
        strategy=strategy,
        normal_returns=returns_with_extremes,
        initial_capital=10000.0
    )
    
    # Extract tail risk analysis
    tail_risk = results.get("tail_risk_analysis", {})
    
    if tail_risk and "error" not in tail_risk:
        print("\nTail Risk Analysis Results:")
        print("-" * 40)
        
        # Tail risk metrics
        tail_metrics = tail_risk.get("tail_risk_metrics", {})
        print(f"VaR (99%): {tail_metrics.get('var_99', 0):.2f}%")
        print(f"VaR (99.5%): {tail_metrics.get('var_99_5', 0):.2f}%")
        print(f"VaR (99.9%): {tail_metrics.get('var_99_9', 0):.2f}%")
        print(f"CVaR (99%): {tail_metrics.get('cvar_99', 0):.2f}%")
        print(f"Tail Expectation: {tail_metrics.get('tail_expectation', 0):.2f}%")
        print(f"Tail Ratio: {tail_metrics.get('tail_ratio', 0):.2f}")
        
        # Crisis return statistics
        crisis_stats = tail_risk.get("crisis_return_statistics", {})
        print(f"\nCrisis Return Statistics:")
        print(f"Mean: {crisis_stats.get('mean', 0):.4f}")
        print(f"Std: {crisis_stats.get('std', 0):.4f}")
        print(f"Skewness: {crisis_stats.get('skewness', 0):.4f}")
        print(f"Kurtosis: {crisis_stats.get('kurtosis', 0):.4f}")
        
        # EVT analysis
        evt_analysis = tail_risk.get("evt_analysis", {})
        if "error" not in evt_analysis:
            print(f"\nExtreme Value Theory Analysis:")
            print(f"Threshold: {evt_analysis.get('threshold', 0):.4f}")
            print(f"Shape Parameter: {evt_analysis.get('shape_parameter', 0):.4f}")
            print(f"Scale Parameter: {evt_analysis.get('scale_parameter', 0):.4f}")
            print(f"Number of Excesses: {evt_analysis.get('num_excesses', 0)}")
        
        # Tail dependence
        tail_dependence = tail_risk.get("tail_dependence", {})
        print(f"\nTail Dependence Analysis:")
        print(f"Lower Tail Dependence: {tail_dependence.get('lower_tail_dependence', 0):.4f}")
        print(f"Upper Tail Dependence: {tail_dependence.get('upper_tail_dependence', 0):.4f}")
        print(f"Tail Asymmetry: {tail_dependence.get('tail_asymmetry', 0):.4f}")
    else:
        print(f"Error in tail risk analysis: {tail_risk.get('error', 'Unknown error')}")


def demo_crisis_comparison():
    """Demo comparison of different strategies during crises."""
    print("\n=== Crisis Strategy Comparison Demo ===\n")
    
    # Generate market data
    market_data = generate_realistic_market_data()
    returns = market_data['returns'].values
    
    # Create different strategies
    strategies = {
        "Volatility Strategy": VolatilityStrategy({
            "mode": "adaptive",
            "vol_period": 20,
            "vol_threshold_low": 1.0,
            "vol_threshold_high": 2.0
        }),
        "Mean Reversion Strategy": MeanReversionStrategy({
            "rsi_period": 14,
            "buy_threshold": 30,
            "sell_threshold": 70,
            "use_bollinger": True
        })
    }
    
    # Create crisis simulator
    crisis_simulator = CrisisSimulator()
    
    # Test strategies on historical crises
    crisis_names = ["2008_financial_crisis", "covid_19_pandemic", "black_monday_1987"]
    
    print("Comparing strategies during historical crises...")
    print("\nStrategy Performance During Crises:")
    print("-" * 80)
    print(f"{'Crisis':<25} {'Strategy':<20} {'Return %':<10} {'Max DD %':<10} {'Survival':<10}")
    print("-" * 80)
    
    for crisis_name in crisis_names:
        for strategy_name, strategy in strategies.items():
            result = crisis_simulator.simulate_historical_crisis(
                strategy=strategy,
                normal_returns=returns,
                crisis_name=crisis_name,
                initial_capital=10000.0
            )
            
            if "error" not in result:
                performance = result["performance"]
                crisis_short = crisis_name.replace("_", " ").title()
                print(f"{crisis_short:<25} {strategy_name:<20} {performance.get('total_return', 0):8.2f}% {performance.get('max_drawdown', 0):8.2f}% {performance.get('survival_rate', 0)*100:7.1f}%")
            else:
                crisis_short = crisis_name.replace("_", " ").title()
                print(f"{crisis_short:<25} {strategy_name:<20} {'ERROR':<10} {'ERROR':<10} {'ERROR':<10}")
    
    print("-" * 80)


if __name__ == "__main__":
    demo_historical_crisis_simulation()
    demo_synthetic_crisis_simulation()
    demo_tail_risk_analysis()
    demo_crisis_comparison()
    demo_comprehensive_crisis_analysis()
    
    print("\n=== Demo Complete ===")
    print("\nKey Features of Crisis Simulation:")
    print("1. HISTORICAL CRISIS MODELING: Tests strategies against real historical market crises")
    print("2. SYNTHETIC CRISIS GENERATION: Creates custom crisis scenarios with specified severity")
    print("3. TAIL RISK ANALYSIS: Uses Extreme Value Theory to analyze extreme market events")
    print("4. CRISIS SURVIVAL RATES: Measures strategy resilience during extreme market conditions")
    print("5. COMPREHENSIVE REPORTING: Detailed analysis of strategy performance across crisis scenarios")
    print("\nBenefits:")
    print("- Validates strategy robustness before live trading")
    print("- Identifies potential failure modes and vulnerabilities")
    print("- Provides realistic worst-case scenario analysis")
    print("- Supports regulatory stress testing requirements")
    print("- Enables informed risk management decisions")
