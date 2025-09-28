from __future__ import annotations
import math

from src.indicators.core import rsi, ema, sma, atr, bollinger, rolling_mean


def test_rsi_basic():
    # Rising close sequence -> RSI should be > 50
    closes = [i for i in range(1, 60)]
    vals = rsi(closes, period=14)
    assert len(vals) == len(closes)
    assert vals[-1] > 50


def test_ema_monotonicity():
    closes = [float(i) for i in range(1, 101)]
    e = ema(closes, period=20)
    assert len(e) == len(closes)
    # EMA should be strictly increasing for strictly increasing series
    # Filter out None values before comparison
    valid_values = [val for val in e if val is not None]
    assert all(valid_values[i] >= valid_values[i-1] for i in range(1, len(valid_values)))


def test_atr_nonnegative():
    # Flat prices -> ATR should be ~0
    closes = [100.0] * 100
    highs = [100.0] * 100
    lows = [100.0] * 100
    a = atr(highs, lows, closes, period=14)
    assert len(a) == len(closes)
    assert a[-1] >= 0.0
    # Nearly zero tolerance
    assert a[-1] < 1e-6


def test_bollinger_flat_series():
    # Flat prices -> upper == lower == middle, width ~ 0
    closes = [100.0] * 50
    mid, up, lo, width = bollinger(closes, period=20, stddev=2.0)
    assert len(mid) == len(up) == len(lo) == len(width) == len(closes)
    # After warmup, bands collapse
    assert abs((mid[-1] or 0) - 100.0) < 1e-9
    assert abs((up[-1] or 0) - 100.0) < 1e-9
    assert abs((lo[-1] or 0) - 100.0) < 1e-9
    assert (width[-1] or 0) < 1e-9


def test_rolling_mean_correctness():
    vals = [1, 2, 3, 4, 5]
    rm = rolling_mean(vals, period=3)
    # Expect: [None, None, 2.0, 3.0, 4.0]
    assert rm[0] is None and rm[1] is None
    assert abs(rm[2] - 2.0) < 1e-9
    assert abs(rm[3] - 3.0) < 1e-9
    assert abs(rm[4] - 4.0) < 1e-9
