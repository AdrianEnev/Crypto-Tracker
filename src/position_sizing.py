from __future__ import annotations
from typing import Optional


def _clamp(v: float, lo: Optional[float], hi: Optional[float]) -> float:
    if lo is not None:
        v = max(lo, v)
    if hi is not None:
        v = min(hi, v)
    return v


def compute_size_usd(
    entry_price: float,
    sl_price: Optional[float],
    equity_usd: float,
    risk_budget_pct: float = 0.005,
    min_size_usd: Optional[float] = None,
    max_size_usd: Optional[float] = None,
) -> float:
    """
    Volatility/risk-based position sizing in USD given entry and stop levels.
    - Risk per trade = equity_usd * risk_budget_pct
    - Dollar risk per unit = max(1e-9, entry - sl) for long positions.
      If sl_price is None or invalid, fall back to fixed min_size_usd (or 0 if missing).
    Returns clamped USD size in [min_size_usd, max_size_usd] if provided.
    """
    try:
        risk_budget = max(0.0, float(equity_usd) * float(risk_budget_pct))
        if sl_price is None or entry_price is None or entry_price <= 0:
            # Fallback: use min_size_usd if provided, else zero
            return float(min_size_usd) if (min_size_usd is not None) else 0.0
        dollar_risk_per_unit = max(1e-9, float(entry_price) - float(sl_price))
        if dollar_risk_per_unit <= 0:
            # If SL not below entry (for long), default to min size
            return float(min_size_usd) if (min_size_usd is not None) else 0.0
        units = risk_budget / dollar_risk_per_unit
        size_usd = units * float(entry_price)
        size_usd = _clamp(
            size_usd,
            float(min_size_usd) if min_size_usd is not None else None,
            float(max_size_usd) if max_size_usd is not None else None,
        )
        return round(size_usd, 2)
    except Exception:
        return float(min_size_usd) if (min_size_usd is not None) else 0.0


def units_from_usd(size_usd: float, price: float) -> float:
    """
    Convert USD notional to units at given price, guarding division by zero.
    """
    try:
        if price <= 0:
            return 0.0
        return float(size_usd) / float(price)
    except Exception:
        return 0.0
