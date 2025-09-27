from __future__ import annotations
import math

from src.indicators.core import rsi, ema, sma, atr


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
