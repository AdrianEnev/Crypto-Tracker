"""
Demo script for the new Volatility Strategy.
Shows different volatility modes and their performance characteristics.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from src.strategies.volatility import VolatilityStrategy
from src.data.ohlcv import get_candles


def demo_volatility_strategy():
    """Demo the volatility strategy with different modes."""
    print("=== Volatility Strategy Demo ===\n")
    
    # Fetch some sample data
    print("Fetching sample data...")
    try:
        candles = get_candles(
            coin_id="bitcoin",
            timeframe="1d",
            days=365,
            use_cache=True
        )
        
        if not candles:
            print("Failed to fetch data. Using sample data...")
            # Create sample data
            import numpy as np
            dates = pd.date_range('2023-01-01', periods=365, freq='D')
            np.random.seed(42)
            price = 50000 + np.cumsum(np.random.randn(365) * 1000)
            volume = np.random.randint(1000000, 10000000, 365)
            
            data = pd.DataFrame({
                'close': price,
                'volume': volume,
                'timestamp': dates
            })
        else:
            # Convert candles to DataFrame
            data = pd.DataFrame([{
                'close': c.c,
                'volume': c.v,
                'timestamp': pd.to_datetime(c.ts, unit='ms')
            } for c in candles])
        
        print(f"Loaded {len(data)} data points")
        
    except Exception as e:
        print(f"Error fetching data: {e}")
        return
    
    # Test different volatility strategy modes
    modes = ["mean_reversion", "breakout", "adaptive"]
    
    for mode in modes:
        print(f"\n--- Testing {mode.upper()} Mode ---")
        
        # Configure strategy
        config = {
            "mode": mode,
            "vol_period": 20,
            "vol_threshold_low": 0.5,
            "vol_threshold_high": 2.0,
            "bb_period": 20,
            "bb_stddev": 2.0,
            "volume_confirmation": True,
            "volume_period": 20,
            "volume_mult": 1.5,
        }
        
        # Create strategy instance
        strategy = VolatilityStrategy(config)
        
        # Generate signals
        try:
            signals = strategy.generate_signals(data)
            
            # Analyze signals
            total_signals = len(signals[signals["signal"] != 0])
            buy_signals = len(signals[signals["signal"] == 1])
            sell_signals = len(signals[signals["signal"] == -1])
            
            print(f"Total signals generated: {total_signals}")
            print(f"Buy signals: {buy_signals}")
            print(f"Sell signals: {sell_signals}")
            print(f"Signal rate: {total_signals / len(data) * 100:.2f}%")
            
            # Show strategy info
            info = strategy.get_strategy_info()
            print(f"Strategy description: {info['description']}")
            
            # Show sample signals
            if total_signals > 0:
                sample_signals = signals[signals["signal"] != 0].head(3)
                print("Sample signals:")
                for idx, row in sample_signals.iterrows():
                    signal_type = "BUY" if row["signal"] == 1 else "SELL"
                    print(f"  {data.iloc[idx]['timestamp'].strftime('%Y-%m-%d')}: {signal_type} at ${data.iloc[idx]['close']:.2f}")
            
        except Exception as e:
            print(f"Error running {mode} strategy: {e}")
    
    print("\n=== Demo Complete ===")
    print("\nKey Features of Volatility Strategy:")
    print("1. MEAN REVERSION: Trades reversals in low volatility periods")
    print("2. BREAKOUT: Follows breakouts in high volatility periods") 
    print("3. ADAPTIVE: Automatically switches between modes based on volatility regime")
    print("\nConfiguration Options:")
    print("- vol_period: Period for volatility calculation")
    print("- vol_threshold_low/high: Volatility regime thresholds")
    print("- bb_period/stddev: Bollinger Bands parameters")
    print("- volume_confirmation: Require volume confirmation")
    print("- volume_mult: Volume multiplier threshold")


if __name__ == "__main__":
    demo_volatility_strategy()
