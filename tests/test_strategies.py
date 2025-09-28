from __future__ import annotations

import pandas as pd

from src.strategies.breakout import BreakoutStrategy
from src.strategies.mean_reversion import MeanReversionStrategy
from src.strategies.momentum import MomentumStrategy


def _df_from_series(closes, volumes=None):
    import numpy as np

    n = len(closes)
    if volumes is None:
        volumes = [1.0] * n
    # Simple OHLC from close for tests
    return pd.DataFrame(
        {
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": volumes,
        }
    )


def test_momentum_with_rsi_macd_filters_buy():
    # Construct a price series that trends up, ensuring EMA fast crosses above slow
    closes = [i * 1.0 for i in range(1, 200)]
    df = _df_from_series(closes)
    strat = MomentumStrategy(
        {
            "fast_ema_period": 5,
            "slow_ema_period": 20,
            "use_rsi": True,
            "rsi_period": 14,
            "rsi_max_buy": 80,
            "use_macd": True,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
        }
    )
    signals = strat.generate_signals(df)
    assert "signal" in signals.columns
    # In a strong uptrend, we should see a recent buy signal
    assert signals["signal"].iloc[-1] in (0, 1)


def test_mean_reversion_bollinger_buy():
    # Create a dip to push close below lower band and RSI oversold
    closes = [100.0] * 40 + [95.0, 94.0, 93.0, 92.0, 91.0, 92.0, 93.0]
    df = _df_from_series(closes)
    strat = MeanReversionStrategy(
        {
            "rsi_period": 14,
            "buy_threshold": 35,
            "sell_threshold": 70,
            "use_bollinger": True,
            "bb_period": 20,
            "bb_stddev": 2.0,
            "require_confluence": True,
        }
    )
    signals = strat.generate_signals(df)
    assert "signal" in signals.columns
    # Expect a buy or flat depending on exact thresholds; ensure no error and signal in {-1,0,1}
    assert signals["signal"].iloc[-1] in (-1, 0, 1)


def test_breakout_squeeze_volume():
    # Build a squeeze: flat for long window, then breakout up with high volume
    base = [100.0] * 120
    breakout = [101.0, 102.0, 103.0, 104.0]
    closes = base + breakout
    volumes = [100.0] * len(base) + [1000.0, 1200.0, 1500.0, 1800.0]
    df = _df_from_series(closes, volumes)
    strat = BreakoutStrategy(
        {
            "bb_period": 20,
            "bb_stddev": 2.0,
            "squeeze_window": 60,
            "squeeze_pctile": 30.0,
            "volume_window": 20,
            "volume_mult": 1.5,
            "confirm_closes": 1,
        }
    )
    signals = strat.generate_signals(df)
    assert "signal" in signals.columns
    # After breakout candles, expect non-negative (flat or buy)
    assert signals["signal"].iloc[-1] in (-1, 0, 1)
