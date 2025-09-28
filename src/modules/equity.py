from __future__ import annotations

from typing import Dict


def compute_equity(tracker, sym_to_price: Dict[str, float]) -> float:
    """Compute total equity = cash + sum(position units * current price).
    If a price is missing for a symbol, that position contributes 0 for this cycle.
    """
    try:
        cash = float(getattr(tracker.portfolio, "cash_usd", 0.0))
    except Exception:
        cash = 0.0
    eq = cash
    try:
        for sym, pos in (tracker.portfolio.positions or {}).items():
            px = sym_to_price.get(sym)
            if px is not None:
                eq += float(pos.units) * float(px)
    except Exception:
        pass
    return float(eq)


def update_daily_equity_baseline(tracker, equity_now: float) -> None:
    """Maintain UTC day-start equity snapshot to compute intraday drawdown, and track equity peak."""
    try:
        from datetime import datetime, timezone

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if getattr(tracker, "_last_equity_day", None) != today:
            tracker._daily_equity_start_usd = float(equity_now)
            tracker._last_equity_day = today
        if getattr(tracker, "_equity_peak_usd", None) is None or float(equity_now) > float(
            tracker._equity_peak_usd
        ):
            tracker._equity_peak_usd = float(equity_now)
    except Exception:
        pass
