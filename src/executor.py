from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Order:
    id: str
    symbol: str
    side: str  # "buy" | "sell"
    size_usd: float
    order_type: str  # "market" | "limit" | "stop-limit"
    status: str  # "Placed" | "Filled" | "Rejected"
    created_at: datetime
    filled_price: Optional[float] = None
    note: str = ""


class PaperExecutor:
    """Simulates order placement without contacting an exchange.

    - No live side effects. Safe for development.
    - Later we can add partial fills, latency, and price impact simulation.
    """

    def __init__(self):
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"paper-{self._counter}"

    def place_order(
        self, symbol: str, side: str, size_usd: float, order_type: str = "limit"
    ) -> Order:
        now = datetime.now(timezone.utc)
        oid = self._next_id()
        # For Phase 3, we just mark as Placed and immediately Filled (simplest model)
        order = Order(
            id=oid,
            symbol=symbol,
            side=side,
            size_usd=size_usd,
            order_type=order_type,
            status="Filled",
            created_at=now,
            filled_price=None,
            note="paper-fill",
        )
        return order
