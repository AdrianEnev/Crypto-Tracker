from __future__ import annotations

from src.risk import RiskParams, compute_stop_levels, compute_trailing_stop, ATRRiskParams, compute_stop_levels_atr, compute_trailing_stop_atr


def test_percent_stops():
    rp = RiskParams(stop_loss_pct=0.03, take_profit_pct=0.06, trailing_stop_pct=0.04)
    price = 100.0
    sl, tp = compute_stop_levels(price, rp)
    assert abs(sl - 97.0) < 1e-9
    assert abs(tp - 106.0) < 1e-9
    trail = compute_trailing_stop(110.0, rp)
    assert abs(trail - (110.0 * (1.0 - 0.04))) < 1e-9


def test_atr_stops():
    params = ATRRiskParams(atr_period=14, sl_mult=1.5, tp_mult=3.0, trail_mult=2.0)
    price = 100.0
    atr = 2.0
    sl, tp = compute_stop_levels_atr(price, atr, params)
    assert abs(sl - (100.0 - 1.5 * 2.0)) < 1e-9
    assert abs(tp - (100.0 + 3.0 * 2.0)) < 1e-9
    trail = compute_trailing_stop_atr(peak_price=110.0, atr_value=atr, atr_params=params)
    assert abs(trail - (110.0 - 2.0 * 2.0)) < 1e-9
