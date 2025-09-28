from __future__ import annotations

from typing import List, Optional, Tuple


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


def atr(
    high: List[float], low: List[float], close: List[float], period: int = 14
) -> List[Optional[float]]:
    if period <= 0 or not high:
        return [None for _ in high]
    prev_close: Optional[float] = None
    trs: List[float] = []
    for i in range(len(high)):
        h = float(high[i])
        low_price = float(low[i])
        c_prev = float(prev_close) if prev_close is not None else float(close[i])
        tr = max(h - low_price, abs(h - c_prev), abs(low_price - c_prev))
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


def macd(
    values: List[float], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9
) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
    """
    Compute MACD, Signal Line, and Histogram.
    Returns (macd_line, signal_line, histogram)
    """
    if not values or slow_period <= fast_period:
        return ([None] * len(values), [None] * len(values), [None] * len(values))

    ema_fast = ema(values, fast_period)
    ema_slow = ema(values, slow_period)

    macd_line: List[Optional[float]] = []
    for i in range(len(values)):
        if ema_fast[i] is not None and ema_slow[i] is not None:
            macd_line.append(ema_fast[i] - ema_slow[i])
        else:
            macd_line.append(None)

    # The signal line is an EMA of the MACD line.
    # We need to handle the None values in the MACD line before passing to ema.
    macd_line_non_none = [v for v in macd_line if v is not None]

    if not macd_line_non_none:
        return macd_line, [None] * len(values), [None] * len(values)

    # The first value of the signal line calculation needs enough preceding macd values
    # The number of non-None values in macd_line is len(values) - (slow_period - 1)
    if len(macd_line_non_none) < signal_period:
        signal_line_raw = [None] * len(macd_line_non_none)
    else:
        signal_line_raw = ema(macd_line_non_none, signal_period)

    # Align the signal line with the original macd_line, which has leading Nones
    signal_line: List[Optional[float]] = []
    num_nones_in_macd = len(macd_line) - len(macd_line_non_none)
    signal_line.extend([None] * num_nones_in_macd)
    signal_line.extend(signal_line_raw)

    histogram: List[Optional[float]] = []
    for i in range(len(values)):
        if macd_line[i] is not None and signal_line[i] is not None:
            histogram.append(macd_line[i] - signal_line[i])
        else:
            histogram.append(None)

    return macd_line, signal_line, histogram


def rolling_mean(values: List[float], period: int) -> List[Optional[float]]:
    """
    Simple rolling mean. Returns a list aligned with input values, with None for the
    first period-1 elements where the mean is not defined.
    """
    out: List[Optional[float]] = []
    if period <= 0:
        return [None for _ in values]
    s = 0.0
    for i, v in enumerate(values):
        x = float(v)
        s += x
        if i >= period:
            s -= float(values[i - period])
        if i + 1 >= period:
            out.append(s / period)
        else:
            out.append(None)
    return out


def bollinger(
    values: List[float], period: int = 20, stddev: float = 2.0
) -> Tuple[
    List[Optional[float]], List[Optional[float]], List[Optional[float]], List[Optional[float]]
]:
    """
    Compute Bollinger Bands: middle (SMA), upper, lower, and width (upper-lower).
    Returns 4 lists aligned with input values. Entries are None until enough data.
    """
    n = len(values)
    if period <= 0 or n == 0:
        return [None] * n, [None] * n, [None] * n, [None] * n
    mid = sma(values, period)
    upper: List[Optional[float]] = []
    lower: List[Optional[float]] = []
    width: List[Optional[float]] = []
    # Use a rolling window to compute stddev; O(n*period) which is fine for typical sizes
    import math

    for i in range(n):
        if i + 1 < period:
            upper.append(None)
            lower.append(None)
            width.append(None)
            continue
        window = [float(values[j]) for j in range(i - period + 1, i + 1)]
        m = float(mid[i]) if mid[i] is not None else sum(window) / period
        # population stddev within window
        var = sum((x - m) ** 2 for x in window) / period
        sd = math.sqrt(max(0.0, var))
        up = m + stddev * sd
        lo = m - stddev * sd
        upper.append(up)
        lower.append(lo)
        width.append(up - lo)
    return mid, upper, lower, width
