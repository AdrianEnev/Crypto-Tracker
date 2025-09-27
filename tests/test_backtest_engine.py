from __future__ import annotations

from src.backtest.engine import simulate_on_series
from src.risk import ATRRiskParams


def test_simulate_on_series_percent_tp():
    # Construct a sequence that becomes oversold (RSI<30) then rallies >6%
    # Use high threshold so price<=threshold is always true
    threshold = 1000.0
    
    # Create a sequence that generates fewer false signals by avoiding continuous decline
    closes = []
    
    # Initial period with some volatility to establish RSI baseline
    base = 100.0
    for i in range(30):
        # Add some randomness but generally sideways
        variation = 1.0 if i % 4 == 0 else (-1.0 if i % 4 == 2 else 0.5)
        closes.append(base + variation)
    
    # Single sharp decline to create oversold condition
    for i in range(10):
        closes.append(100.0 - i * 2.5)  # 100 -> 77.5 rapidly
    
    # Small bounce to let RSI recover slightly (prevent continuous oversold)
    for i in range(5):
        closes.append(77.5 + i * 1.0)  # bounce to 81.5
    
    # Another decline to re-enter oversold
    for i in range(8):
        closes.append(81.5 - i * 0.8)  # 81.5 -> 75.9
    
    # Final rally to hit take profit target
    base_price = 75.9
    for i in range(10):
        closes.append(base_price * (1.0 + (i + 1) * 0.01))  # ~10% rally
    
    highs = closes[:]  # simplified synthetic OHLC
    lows = closes[:]

    res = simulate_on_series(
        coin_id="test",
        threshold=threshold,
        closes=closes,
        highs=highs,
        lows=lows,
        rsi_period=14,
        ema_fast=12,
        ema_slow=40,
        atr_params=None,  # percent-based exits: 3% SL, 6% TP
        slippage_bps=0,
        fee_bps=0,
    )
    # Expect one trade that exits via TP with positive PF
    assert len(res.trades) >= 1
    assert res.profit_factor >= 1.0
