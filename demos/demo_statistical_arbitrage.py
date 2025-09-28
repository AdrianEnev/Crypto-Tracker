"""
Demo script for the Statistical Arbitrage and Pairs Trading Strategy.
Shows cointegration testing, hedge ratio calculation, and signal generation.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import pandas as pd
from src.strategies.statistical_arbitrage import StatisticalArbitrageStrategy, PairsTradingStrategy


def generate_sample_data():
    """Generate sample correlated price data for demonstration."""
    np.random.seed(42)
    
    # Generate two correlated price series
    n_days = 500
    dates = pd.date_range('2023-01-01', periods=n_days, freq='D')
    
    # Base price series
    base_trend = np.cumsum(np.random.randn(n_days) * 0.01)
    base_price = 100 * np.exp(base_trend)
    
    # Create correlated series with some divergence
    correlation = 0.8
    noise = np.random.randn(n_days) * 0.02
    asset2_trend = correlation * base_trend + (1 - correlation) * np.cumsum(np.random.randn(n_days) * 0.01)
    asset2_price = 50 * np.exp(asset2_trend + noise)
    
    # Add some mean reversion to the spread
    spread = base_price - 2 * asset2_price
    spread_mean = np.mean(spread)
    spread_reversion = (spread - spread_mean) * 0.1
    asset2_price_adjusted = (base_price - spread_reversion) / 2
    
    data = pd.DataFrame({
        'close_BTC': base_price,
        'close_ETH': asset2_price_adjusted,
        'timestamp': dates
    })
    
    return data


def demo_statistical_arbitrage():
    """Demo the statistical arbitrage strategy."""
    print("=== Statistical Arbitrage Strategy Demo ===\n")
    
    # Generate sample data
    print("Generating sample correlated price data...")
    data = generate_sample_data()
    print(f"Generated {len(data)} data points for BTC and ETH")
    
    # Test different configurations
    configs = [
        {
            "name": "Conservative",
            "config": {
                "lookback_period": 252,
                "z_score_threshold": 2.5,
                "z_score_exit": 0.3,
                "cointegration_threshold": 0.01,
                "hedge_ratio_method": "ols",
                "position_size_method": "fixed"
            }
        },
        {
            "name": "Aggressive",
            "config": {
                "lookback_period": 126,
                "z_score_threshold": 1.5,
                "z_score_exit": 0.7,
                "cointegration_threshold": 0.05,
                "hedge_ratio_method": "rolling",
                "position_size_method": "volatility_adjusted"
            }
        },
        {
            "name": "Kelly-based",
            "config": {
                "lookback_period": 252,
                "z_score_threshold": 2.0,
                "z_score_exit": 0.5,
                "cointegration_threshold": 0.05,
                "hedge_ratio_method": "ols",
                "position_size_method": "kelly"
            }
        }
    ]
    
    for config_info in configs:
        print(f"\n--- Testing {config_info['name']} Configuration ---")
        
        # Create strategy instance
        strategy = StatisticalArbitrageStrategy(config_info["config"])
        
        # Prepare data for strategy (needs close prices)
        strategy_data = pd.DataFrame({
            'close_BTC': data['close_BTC'],
            'close_ETH': data['close_ETH']
        })
        
        try:
            # Generate signals
            signals = strategy.generate_signals(strategy_data)
            
            # Analyze results
            total_signals = len(signals[signals["signal"] != 0])
            buy_signals = len(signals[signals["signal"] == 1])
            sell_signals = len(signals[signals["signal"] == -1])
            
            print(f"Total signals generated: {total_signals}")
            print(f"Buy signals: {buy_signals}")
            print(f"Sell signals: {sell_signals}")
            print(f"Signal rate: {total_signals / len(data) * 100:.2f}%")
            
            # Show strategy info
            info = strategy.get_strategy_info()
            print(f"Strategy: {info['description']}")
            print(f"Hedge ratio method: {info['parameters']['hedge_ratio_method']}")
            print(f"Position sizing: {info['parameters']['position_size_method']}")
            
            # Show sample signals
            if total_signals > 0:
                sample_signals = signals[signals["signal"] != 0].head(3)
                print("Sample signals:")
                for idx, row in sample_signals.iterrows():
                    signal_type = "BUY" if row["signal"] == 1 else "SELL"
                    btc_price = data.iloc[idx]['close_BTC']
                    eth_price = data.iloc[idx]['close_ETH']
                    print(f"  {data.iloc[idx]['timestamp'].strftime('%Y-%m-%d')}: {signal_type} at BTC=${btc_price:.2f}, ETH=${eth_price:.2f}")
            
        except Exception as e:
            print(f"Error running {config_info['name']} strategy: {e}")


def demo_pairs_trading():
    """Demo the pairs trading strategy."""
    print("\n=== Pairs Trading Strategy Demo ===\n")
    
    # Generate multi-asset data
    print("Generating multi-asset sample data...")
    np.random.seed(123)
    
    n_days = 500
    dates = pd.date_range('2023-01-01', periods=n_days, freq='D')
    
    # Generate 4 correlated assets
    base_trend = np.cumsum(np.random.randn(n_days) * 0.01)
    assets = {}
    
    # Asset 1: Base trend
    assets['BTC'] = 50000 * np.exp(base_trend)
    
    # Asset 2: Highly correlated with BTC
    assets['ETH'] = 3000 * np.exp(0.8 * base_trend + 0.2 * np.cumsum(np.random.randn(n_days) * 0.01))
    
    # Asset 3: Moderately correlated
    assets['ADA'] = 1.5 * np.exp(0.6 * base_trend + 0.4 * np.cumsum(np.random.randn(n_days) * 0.01))
    
    # Asset 4: Less correlated
    assets['DOT'] = 25 * np.exp(0.4 * base_trend + 0.6 * np.cumsum(np.random.randn(n_days) * 0.01))
    
    data = pd.DataFrame(assets, index=dates)
    
    print(f"Generated data for {len(assets)} assets over {len(data)} days")
    
    # Test pairs trading strategy
    config = {
        "lookback_period": 252,
        "z_score_threshold": 2.0,
        "z_score_exit": 0.5,
        "cointegration_threshold": 0.05,
        "hedge_ratio_method": "ols",
        "position_size_method": "volatility_adjusted",
        "min_correlation": 0.5,
        "max_correlation": 0.9,
        "max_portfolio_pairs": 3
    }
    
    strategy = PairsTradingStrategy(config)
    
    try:
        # Find potential pairs
        pairs = strategy.find_pairs(data)
        print(f"\nFound {len(pairs)} potential trading pairs:")
        for asset1, asset2, correlation in pairs:
            print(f"  {asset1}-{asset2}: correlation = {correlation:.3f}")
        
        # Generate multi-pair signals
        multi_signals = strategy.generate_multi_pair_signals(data)
        print(f"\nGenerated signals for {len(multi_signals)} pairs")
        
        # Analyze signals
        for pair_name, signals in multi_signals.items():
            total_signals = len(signals[signals != 0])
            if total_signals > 0:
                print(f"  {pair_name}: {total_signals} signals")
        
        # Show strategy info
        info = strategy.get_strategy_info()
        print(f"\nStrategy: {info['description']}")
        print(f"Max portfolio pairs: {info['parameters']['max_portfolio_pairs']}")
        print(f"Pair allocation: {info['parameters']['pair_allocation']*100:.1f}% per pair")
        
    except Exception as e:
        print(f"Error running pairs trading strategy: {e}")


def demo_cointegration_testing():
    """Demo cointegration testing functionality."""
    print("\n=== Cointegration Testing Demo ===\n")
    
    # Generate cointegrated series
    np.random.seed(456)
    n = 500
    
    # Create two cointegrated series
    # Series 1: Random walk
    series1 = np.cumsum(np.random.randn(n) * 0.01)
    
    # Series 2: Cointegrated with series1
    # series2 = 0.5 * series1 + stationary_noise
    cointegration_ratio = 0.5
    stationary_noise = np.random.randn(n) * 0.005
    series2 = cointegration_ratio * series1 + stationary_noise
    
    # Test cointegration
    strategy = StatisticalArbitrageStrategy({})
    
    print(f"Testing cointegration between two series:")
    print(f"  Series 1: Random walk with drift")
    print(f"  Series 2: {cointegration_ratio} * Series1 + stationary noise")
    
    is_cointegrated = strategy._test_cointegration(series1, series2)
    print(f"  Cointegrated: {is_cointegrated}")
    
    # Test hedge ratio calculation
    hedge_ratio = strategy._calculate_hedge_ratio(series1, series2)
    if hedge_ratio is not None:
        print(f"  Calculated hedge ratio: {hedge_ratio:.3f}")
        print(f"  True ratio: {cointegration_ratio:.3f}")
        print(f"  Error: {abs(hedge_ratio - cointegration_ratio):.3f}")
    else:
        print(f"  Hedge ratio calculation failed")
        print(f"  True ratio: {cointegration_ratio:.3f}")
    
    # Test with non-cointegrated series
    print(f"\nTesting with non-cointegrated series:")
    series3 = np.cumsum(np.random.randn(n) * 0.01)  # Independent random walk
    is_cointegrated_3 = strategy._test_cointegration(series1, series3)
    print(f"  Cointegrated: {is_cointegrated_3}")


if __name__ == "__main__":
    demo_statistical_arbitrage()
    demo_pairs_trading()
    demo_cointegration_testing()
    
    print("\n=== Demo Complete ===")
    print("\nKey Features of Statistical Arbitrage Strategy:")
    print("1. COINTEGRATION TESTING: Ensures pairs have long-term equilibrium relationship")
    print("2. HEDGE RATIO CALCULATION: OLS or rolling regression for optimal hedging")
    print("3. Z-SCORE SIGNALS: Mean reversion based on statistical significance")
    print("4. RISK MANAGEMENT: Stop loss and take profit based on z-score multiples")
    print("5. POSITION SIZING: Fixed, volatility-adjusted, or Kelly criterion")
    print("\nPairs Trading Extensions:")
    print("- CORRELATION-BASED PAIR SELECTION: Find optimal trading pairs")
    print("- MULTI-PAIR PORTFOLIO: Manage multiple pairs simultaneously")
    print("- DYNAMIC HEDGE RATIOS: Rebalance hedge ratios periodically")
