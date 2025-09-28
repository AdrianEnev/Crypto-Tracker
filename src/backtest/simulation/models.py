"""
Data models for backtest simulation.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Trade:
    """Represents a single trade in the backtest."""
    entry_idx: int
    entry_price: float
    exit_idx: Optional[int] = None
    exit_price: Optional[float] = None
    reason: str = ""

    def pnl_pct(self) -> Optional[float]:
        """Calculate P&L percentage for this trade."""
        if self.exit_price is None or self.entry_price == 0:
            return None
        return (self.exit_price / self.entry_price - 1.0) * 100.0


@dataclass
class BacktestResult:
    """Results from a backtest simulation."""
    trades: List[Trade]
    equity: List[float]
    win_rate: float
    profit_factor: float
    max_drawdown: float
    cagr: float = 0.0
    mar: float = 0.0
    avg_return_pct: float = 0.0
