from __future__ import annotations
from typing import Optional


def estimate_slippage(size_usd: float, spread_bps_default: int = 10) -> float:
    """Very simple slippage estimator for Phase 3 scaffolding.

    - Uses a default bid/ask spread in basis points (bps) when we don't have
      order book depth or reliable 24h volume.
    - Returns an estimated percentage (e.g., 0.10 for 0.10%).

    Notes:
    - In later phases, incorporate: 24h volume, order book depth, and market impact models.
    - For now, we keep it constant and independent of size.
    """
    spread_pct = spread_bps_default / 10000.0  # bps to fraction
    # Assume expected slippage approximately equals half-spread for maker/limit,
    # near full spread for market. As a scaffold, return full spread.
    return round(spread_pct * 100.0, 3)  # return as percent
