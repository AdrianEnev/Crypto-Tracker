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
