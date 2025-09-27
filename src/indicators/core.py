from __future__ import annotations
from typing import List, Optional


def sma(values: List[float], period: int) -> List[Optional[float]]:
    out: List[Optional[float]] = []
    if period <= 0:
        return [None for _ in values]
    s = 0.0
    for i, v in enumerate(values):
        s += float(v)
        if i >= period:
            s -= float(values[i - period])
        if i + 1 >= period:
            out.append(s / period)
        else:
            out.append(None)
    return out


def ema(values: List[float], period: int) -> List[Optional[float]]:
    out: List[Optional[float]] = []
    if period <= 0:
        return [None for _ in values]
    k = 2.0 / (period + 1)
    ema_val: Optional[float] = None
    for i, v in enumerate(values):
        x = float(v)
        if ema_val is None:
            ema_val = x
        else:
            ema_val = x * k + ema_val * (1 - k)
        out.append(ema_val if i + 1 >= period else None)
    return out


def rsi(values: List[float], period: int = 14) -> List[Optional[float]]:
    out: List[Optional[float]] = []
    if period <= 0 or len(values) == 0:
        return [None for _ in values]
    gains = 0.0
    losses = 0.0
    prev = float(values[0])
    out.append(None)
    for i in range(1, len(values)):
        cur = float(values[i])
        change = cur - prev
        prev = cur
        gain = max(change, 0.0)
        loss = max(-change, 0.0)
        if i <= period:
            gains += gain
            losses += loss
            out.append(None)
            continue
        # Wilder's smoothing
        gains = (gains * (period - 1) + gain) / period
        losses = (losses * (period - 1) + loss) / period
        if losses == 0:
            out.append(100.0)
        else:
            rs = gains / losses
            out.append(100.0 - (100.0 / (1.0 + rs)))
    return out


def atr(high: List[float], low: List[float], close: List[float], period: int = 14) -> List[Optional[float]]:
    out: List[Optional[float]] = []
    if period <= 0 or not high:
        return [None for _ in high]
    prev_close: Optional[float] = None
    trs: List[float] = []
    for i in range(len(high)):
        h = float(high[i])
        l = float(low[i])
        c_prev = float(prev_close) if prev_close is not None else float(close[i])
        tr = max(h - l, abs(h - c_prev), abs(l - c_prev))
        trs.append(tr)
        prev_close = float(close[i])
    # Wilder's ATR
    atr_vals: List[Optional[float]] = []
    atr_sum = 0.0
    for i, tr in enumerate(trs):
        atr_sum += tr
        if i + 1 == period:
            atr_vals.append(atr_sum / period)
        elif i + 1 > period:
            prev_atr = atr_vals[-1] if atr_vals[-1] is not None else atr_sum / period
            curr = (prev_atr * (period - 1) + tr) / period
            atr_vals.append(curr)
        else:
            atr_vals.append(None)
    return atr_vals
