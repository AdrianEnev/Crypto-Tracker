from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class Position:
    symbol: str
    units: float
    entry_price: float
    peak_price: float

    def pnl_pct(self, current_price: float) -> float:
        if self.entry_price <= 0:
            return 0.0
        return ((current_price - self.entry_price) / self.entry_price) * 100.0

    def update_peak(self, current_price: float) -> None:
        if current_price > self.peak_price:
            self.peak_price = current_price


class Portfolio:
    """In-memory paper portfolio for Phase 6.
    - Single position per symbol for simplicity.
    - Open only when allowed by config and decision engine.
    """

    def __init__(self):
        self.positions: Dict[str, Position] = {}

    def get(self, symbol: str) -> Optional[Position]:
        return self.positions.get(symbol)

    def open(self, symbol: str, usd_size: float, price: float) -> Position:
        if price <= 0:
            raise ValueError("Invalid entry price")
        units = usd_size / price
        pos = Position(symbol=symbol, units=units, entry_price=price, peak_price=price)
        self.positions[symbol] = pos
        return pos

    def close(self, symbol: str) -> Optional[Position]:
        return self.positions.pop(symbol, None)
