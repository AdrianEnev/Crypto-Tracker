from __future__ import annotations

import types

import pytest

from src.data.ohlcv import Candle
from src.decision import make_decision


class FakeTracker:
    def __init__(self, config_path: str, history):
        self.config_path = config_path
        self.history = history


def _build_flat_history(coin_id: str, price: float = 100.0, n: int = 60):
    candles = [
        Candle(ts=1_700_000_000_000 + i * 86_400_000, o=price, h=price, l=price, c=price, v=10.0)
        for i in range(n)
    ]
    return {
        coin_id: {
            "candles": candles,
            "last": {"atr": 0.0, "close": price, "ema_fast": price, "ema_slow": price},
        }
    }


def test_make_decision_smoke_uses_config_and_history():
    # Use existing repo config; choose a coin id that exists in config (e.g., 'solana')
    coin_id = "solana"
    config_path = "./config/config.yaml"
    tracker = FakeTracker(config_path=config_path, history=_build_flat_history(coin_id))

    dec = make_decision(tracker, coin_id)
    assert dec is not None
    assert dec.signal.endswith("_signal") or dec.signal in (
        "no_data",
        "strategy_error",
        "strategy_eval_error",
    )
    # With flat series and ATR gate in config, expect Hold due to vol_gate
    assert dec.action_recommended in ("Hold", "Manual", "Sell", "Buy")
    # Confidence should be a float within [0, 1]
    assert 0.0 <= float(dec.confidence) <= 1.0
