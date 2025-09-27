from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional, Any
import json
from pathlib import Path


@dataclass
class Position:
    symbol: str
    units: float
    entry_price: float
    peak_price: float
    adds_count: int = 0
    last_add_price: float = 0.0

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

    def __init__(self, initial_cash_usd: float = 10000.0):
        self.positions: Dict[str, Position] = {}
        self.initial_cash_usd: float = float(initial_cash_usd)
        self.cash_usd: float = float(initial_cash_usd)

    def get(self, symbol: str) -> Optional[Position]:
        return self.positions.get(symbol)

    def open(self, symbol: str, usd_size: float, price: float, fee_bps: float = 0.0) -> Position:
        if price <= 0:
            raise ValueError("Invalid entry price")
        # Do not exceed available cash
        usd_alloc = min(float(usd_size), float(self.cash_usd))
        fee_mult = 1.0 + (float(fee_bps) / 10000.0)
        units = usd_alloc / price
        pos = Position(symbol=symbol, units=units, entry_price=price, peak_price=price, adds_count=0, last_add_price=price)
        self.positions[symbol] = pos
        # Deduct notional + fee from cash
        self.cash_usd -= usd_alloc * fee_mult
        return pos

    def close(self, symbol: str, price: float, fee_bps: float = 0.0) -> Optional[Dict[str, Any]]:
        pos = self.positions.pop(symbol, None)
        if pos is None:
            return None
        proceeds = float(pos.units) * float(price)
        fee = proceeds * (float(fee_bps) / 10000.0)
        self.cash_usd += (proceeds - fee)
        pnl_usd = (float(price) - float(pos.entry_price)) * float(pos.units)
        pnl_pct = pos.pnl_pct(float(price))
        return {
            "symbol": symbol,
            "entry_price": float(pos.entry_price),
            "exit_price": float(price),
            "units": float(pos.units),
            "pnl_usd": float(pnl_usd),
            "pnl_pct": float(pnl_pct),
        }

    def equity_usd(self, sym_to_price: Dict[str, float]) -> float:
        equity = float(self.cash_usd)
        for sym, pos in self.positions.items():
            px = sym_to_price.get(sym)
            if px is not None:
                equity += float(pos.units) * float(px)
        return equity

    # Persistence helpers
    def to_dict(self) -> Dict[str, Any]:
        return {
            "initial_cash_usd": float(self.initial_cash_usd),
            "cash_usd": float(self.cash_usd),
            "positions": {
                sym: {
                    "symbol": pos.symbol,
                    "units": float(pos.units),
                    "entry_price": float(pos.entry_price),
                    "peak_price": float(pos.peak_price),
                }
                for sym, pos in self.positions.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Portfolio":
        p = cls(initial_cash_usd=float(data.get("initial_cash_usd", 0.0)))
        p.cash_usd = float(data.get("cash_usd", p.initial_cash_usd))
        positions = data.get("positions", {}) or {}
        for sym, d in positions.items():
            try:
                pos = Position(
                    symbol=str(d.get("symbol", sym)),
                    units=float(d.get("units", 0.0)),
                    entry_price=float(d.get("entry_price", 0.0)),
                    peak_price=float(d.get("peak_price", 0.0)),
                )
                p.positions[sym] = pos
            except Exception:
                continue
        return p

    def save_state(self, path: str | Path) -> None:
        try:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w") as f:
                json.dump(self.to_dict(), f)
        except Exception:
            pass

    def add_to_position(self, symbol: str, usd_size: float, price: float, fee_bps: float = 0.0) -> Optional[Position]:
        """Increase an existing position by investing additional USD at current price.
        Updates weighted average entry, peak, cash, and pyramiding metadata.
        """
        pos = self.positions.get(symbol)
        if pos is None:
            return None
        if price <= 0 or usd_size <= 0:
            return pos
        usd_alloc = min(float(usd_size), float(self.cash_usd))
        if usd_alloc <= 0:
            return pos
        fee_mult = 1.0 + (float(fee_bps) / 10000.0)
        add_units = usd_alloc / float(price)
        # Weighted average entry
        total_value_prev = float(pos.units) * float(pos.entry_price)
        total_value_new = total_value_prev + usd_alloc
        new_units = float(pos.units) + float(add_units)
        new_entry = (total_value_new / new_units) if new_units > 0 else pos.entry_price
        pos.units = new_units
        pos.entry_price = new_entry
        # Update peak to at least entry
        if pos.peak_price < new_entry:
            pos.peak_price = new_entry
        pos.adds_count += 1
        pos.last_add_price = float(price)
        # Deduct notional + fee
        self.cash_usd -= usd_alloc * fee_mult
        return pos

    @classmethod
    def load_state(cls, path: str | Path) -> Optional["Portfolio"]:
        try:
            path = Path(path)
            if not path.exists():
                return None
            with path.open("r") as f:
                data = json.load(f)
            return cls.from_dict(data)
        except Exception:
            return None
