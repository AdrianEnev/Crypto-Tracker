from __future__ import annotations
from collections import deque
from typing import Deque, List, Optional


def compute_rsi(prices: List[float], period: int = 14) -> Optional[float]:
    """Compute RSI (Relative Strength Index) using simple Wilder's smoothing.
    Returns None if insufficient data.
    """
    if len(prices) < period + 1:
        return None
    gains = []
    losses = []
    for i in range(1, period + 1):
        change = prices[i] - prices[i - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    # Continue smoothing over the rest of the series
    for i in range(period + 1, len(prices)):
        change = prices[i] - prices[i - 1]
        gain = max(change, 0.0)
        loss = max(-change, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    if avg_loss == 0:
        return 100.0  # No losses -> RSI at 100
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def compute_ma(prices: List[float], window: int) -> Optional[float]:
    """Simple moving average. Returns None if insufficient data."""
    if len(prices) < window:
        return None
    return sum(prices[-window:]) / float(window)


def price_distance_score(price: float, threshold: float) -> float:
    """Score in [0,1] higher when price is below threshold (for buys).
    If price >= threshold, score declines to 0.
    """
    if threshold <= 0:
        return 0.0
    if price >= threshold:
        return 0.0
    # Closer to zero -> higher score; cap at 1.0 when price is 0
    return max(0.0, min(1.0, (threshold - price) / threshold))


def rsi_buy_score(rsi: Optional[float]) -> float:
    """Map RSI to a [0,1] buy score: lower RSI -> higher score.
    Using 30 as strong buy region, 50 as neutral.
    """
    if rsi is None:
        return 0.0
    if rsi <= 30:
        return 1.0
    if rsi >= 50:
        return 0.0
    # Linear scale between 30 and 50
    return max(0.0, min(1.0, (50 - rsi) / 20.0))


def ma_alignment_score(short_ma: Optional[float], long_ma: Optional[float], price: float) -> float:
    """Score in [0,1] when price is below short MA and short MA < long MA (down trend -> dip buys more cautious).
    This is a soft component for Phase 2; returns 0 if missing.
    """
    if short_ma is None or long_ma is None:
        return 0.0
    score = 0.0
    if price < short_ma:
        score += 0.5
    if short_ma < long_ma:
        score += 0.5
    return min(1.0, score)


def compute_confidence(price: float, threshold: float, rsi: Optional[float],
                       short_ma: Optional[float], long_ma: Optional[float]) -> float:
    """Weighted sum of independent signals into [0,1]."""
    p_score = price_distance_score(price, threshold)
    r_score = rsi_buy_score(rsi)
    m_score = ma_alignment_score(short_ma, long_ma, price)
    # Weights can be tuned; start conservative
    confidence = 0.5 * p_score + 0.35 * r_score + 0.15 * m_score
    return round(max(0.0, min(1.0, confidence)), 4)


def recommend_action(price: float, threshold: float, rsi: Optional[float],
                     confidence: float, suggestion_threshold: float = 0.5) -> (str, str, str):
    """Return (signal, action_recommended, reason).
    For Phase 2: recommend Buy if price <= threshold and RSI < 35, else Hold.
    """
    if price <= threshold: #and (rsi is not None and rsi < 35):
        signal = "threshold_rsi"
        action = "Buy" if confidence >= suggestion_threshold else "Hold"
        reason = "price<=threshold & RSI<35"
        return signal, action, reason
    # Otherwise hold
    return "threshold_check", "Hold", "no-strong-signal"
