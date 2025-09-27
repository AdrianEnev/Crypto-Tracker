from __future__ import annotations

from src.decision import compute_confidence, recommend_action


def test_recommend_buy_when_rsi_low_and_price_below_threshold():
    price = 95.0
    threshold = 100.0
    rsi = 25.0
    # Simulate MAs close to price to avoid overpowering effect
    ma_short = 96.0
    ma_long = 97.0
    conf = compute_confidence(price, threshold, rsi, ma_short, ma_long)
    signal, action, reason = recommend_action(price, threshold, rsi, conf, suggestion_threshold=0.5)
    assert signal in ("threshold_rsi", "threshold_check")
    assert action == "Buy"
    assert "RSI<30" in reason


def test_hold_when_rsi_not_low():
    price = 95.0
    threshold = 100.0
    rsi = 45.0
    ma_short = 96.0
    ma_long = 97.0
    conf = compute_confidence(price, threshold, rsi, ma_short, ma_long)
    signal, action, reason = recommend_action(price, threshold, rsi, conf, suggestion_threshold=0.5)
    assert action == "Hold"
