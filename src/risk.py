from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class RiskParams:
    stop_loss_pct: float = 0.03
    take_profit_pct: float = 0.06
    trailing_stop_pct: float = 0.04


def compute_stop_levels(entry_price: float, params: RiskParams) -> tuple[float, float]:
    """Return (stop_loss_level, take_profit_level) from entry and percent params."""
    sl = entry_price * (1.0 - params.stop_loss_pct)
    tp = entry_price * (1.0 + params.take_profit_pct)
    return round(sl, 6), round(tp, 6)


def compute_trailing_stop(peak_price: float, params: RiskParams) -> float:
    """Return the trailing stop level based on the current peak since entry."""
    return round(peak_price * (1.0 - params.trailing_stop_pct), 6)


@dataclass
class ATRRiskParams:
    atr_period: int = 14
    sl_mult: float = 1.5
    tp_mult: float = 3.0
    trail_mult: float = 2.0


def compute_stop_levels_atr(
    entry_price: float, atr_value: Optional[float], atr_params: ATRRiskParams
) -> tuple[Optional[float], Optional[float]]:
    """ATR-based stops and targets. Returns (sl, tp) or (None, None) if ATR missing."""
    if atr_value is None or atr_value <= 0:
        return None, None
    sl = entry_price - atr_params.sl_mult * atr_value
    tp = entry_price + atr_params.tp_mult * atr_value
    return round(sl, 6), round(tp, 6)


def compute_trailing_stop_atr(
    peak_price: float, atr_value: Optional[float], atr_params: ATRRiskParams
) -> Optional[float]:
    """ATR-based trailing: peak - k*ATR. Returns None if ATR missing."""
    if atr_value is None or atr_value <= 0:
        return None
    lvl = peak_price - atr_params.trail_mult * atr_value
    return round(lvl, 6)
