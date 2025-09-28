"""
Portfolio management for the crypto tracker.
Handles portfolio state, equity calculations, and position tracking.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from src.logger import log_event
from src.persistence.sqlite_store import SQLiteStore
from src.portfolio import Portfolio


class PortfolioManager:
    """Manages portfolio state and equity calculations."""

    def __init__(self, config_manager, app_config: Any):
        self.config_manager = config_manager
        self.app_config = app_config

        # Portfolio state
        config_path = Path(config_manager.config_path)
        self.state_path = config_path.parent.parent / "logs" / "state.json"
        self.portfolio = self._load_portfolio()

        # SQLite persistence store
        try:
            db_path = config_path.parent.parent / "logs" / "tracker.db"
            self.store = SQLiteStore(db_path)
        except Exception:
            self.store = None

        # Equity tracking
        self._equity_peak_usd: Optional[float] = None
        self._dd_risk_factor: float = 1.0
        self._daily_equity_start_usd: Optional[float] = None
        self._last_equity_day: Optional[str] = None

        # Risk parameters
        self.max_exposure_pct: float = 1.0
        self.max_exposure_usd: Optional[float] = None
        self.daily_loss_cap_pct: float = 0.0

        # Drawdown thresholds
        self.dd_t1_pct: float = 5.0
        self.dd_t1_factor: float = 0.8
        self.dd_t2_pct: float = 10.0
        self.dd_t2_factor: float = 0.5

        self._load_risk_settings()

    def _load_portfolio(self) -> Portfolio:
        """Load portfolio from saved state or create new one."""
        try:
            if self.state_path.exists():
                return Portfolio.load_state(self.state_path)
            else:
                return Portfolio(initial_cash_usd=10000.0)
        except Exception:
            return Portfolio(initial_cash_usd=10000.0)

    def _load_risk_settings(self):
        """Load risk management settings from configuration."""
        try:
            execution_config = self.config_manager.get_execution_config()
            risk_config = self.config_manager.get_risk_config()

            self.max_exposure_pct = execution_config.get("risk_budget_pct", 1.0)
            self.max_exposure_usd = execution_config.get("max_size_usd")
            self.daily_loss_cap_pct = execution_config.get("daily_loss_cap_pct", 0.0)

            # Drawdown settings
            dd_config = risk_config.get("drawdown", {})
            self.dd_t1_pct = dd_config.get("t1_pct", 5.0)
            self.dd_t1_factor = dd_config.get("t1_factor", 0.8)
            self.dd_t2_pct = dd_config.get("t2_pct", 10.0)
            self.dd_t2_factor = dd_config.get("t2_factor", 0.5)

        except Exception:
            pass

    def save_portfolio_state(self):
        """Save current portfolio state to disk."""
        try:
            self.portfolio.save_state(self.state_path)
        except Exception as ex:
            log_event("portfolio_save_error", {"error": str(ex)})

    def calculate_equity(self, sym_to_price: Dict[str, float]) -> float:
        """Calculate current portfolio equity."""
        equity = 0.0
        for sym, pos in self.portfolio.positions.items():
            px = sym_to_price.get(sym)
            if px is not None:
                equity += float(pos.units) * float(px)
        return equity

    def update_equity_tracking(self, equity_now: float):
        """Update equity tracking and risk factors."""
        try:
            # Update equity peak
            if self._equity_peak_usd is None or equity_now > float(self._equity_peak_usd):
                self._equity_peak_usd = float(equity_now)

            # Calculate drawdown
            dd_pct = 0.0
            if self._equity_peak_usd and self._equity_peak_usd > 0:
                dd_pct = max(
                    0.0, (self._equity_peak_usd - equity_now) / self._equity_peak_usd * 100.0
                )

            # Update risk factor based on drawdown
            if dd_pct >= self.dd_t2_pct:
                self._dd_risk_factor = self.dd_t2_factor
            elif dd_pct >= self.dd_t1_pct:
                self._dd_risk_factor = self.dd_t1_factor
            else:
                self._dd_risk_factor = 1.0

            # Update daily equity baseline
            day_now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            if (
                self._last_equity_day or day_now
            ) != day_now or self._daily_equity_start_usd is None:
                self._daily_equity_start_usd = equity_now
                self._last_equity_day = day_now

            # Persist equity snapshot
            if self.store is not None:
                self.store.insert_equity(equity_now)

        except Exception as ex:
            log_event("equity_update_error", {"error": str(ex)})

    def check_exposure_limits(self, equity_now: float) -> tuple[bool, bool]:
        """Check if exposure limits are exceeded."""
        max_exposure_hit = False
        daily_loss_hit = False

        # Check max exposure
        if self.max_exposure_usd is not None and equity_now >= self.max_exposure_usd:
            max_exposure_hit = True

        if (
            self.max_exposure_pct is not None
            and self._daily_equity_start_usd is not None
            and self._daily_equity_start_usd > 0
        ):
            if equity_now / self._daily_equity_start_usd > self.max_exposure_pct:
                max_exposure_hit = True

        # Check daily loss cap
        if (
            self.daily_loss_cap_pct
            and self._daily_equity_start_usd
            and self._daily_equity_start_usd > 0
        ):
            dd = (equity_now - self._daily_equity_start_usd) / self._daily_equity_start_usd
            if dd <= -abs(self.daily_loss_cap_pct):
                daily_loss_hit = True

        return max_exposure_hit, daily_loss_hit

    def get_portfolio_summary(self, sym_to_price: Dict[str, float]) -> Dict[str, Any]:
        """Get portfolio summary information."""
        equity_now = self.calculate_equity(sym_to_price)
        total_exposure = equity_now

        # Calculate P&L for each position
        positions_summary = {}
        for sym, pos in self.portfolio.positions.items():
            px = sym_to_price.get(sym)
            if px is not None:
                pnl_pct = pos.pnl_pct(float(px))
                positions_summary[sym] = {
                    "units": pos.units,
                    "entry_price": pos.entry_price,
                    "current_price": px,
                    "pnl_pct": pnl_pct,
                    "market_value": pos.units * px,
                }

        return {
            "equity": equity_now,
            "total_exposure": total_exposure,
            "positions": positions_summary,
            "dd_risk_factor": self._dd_risk_factor,
            "equity_peak": self._equity_peak_usd,
            "daily_start": self._daily_equity_start_usd,
        }

    def get_position(self, symbol: str):
        """Get position for a specific symbol."""
        return self.portfolio.get(symbol.upper())

    def update_position_peak(self, symbol: str, current_price: float):
        """Update trailing peak for a position."""
        pos = self.get_position(symbol)
        if pos is not None:
            pos.update_peak(current_price)

    def get_risk_factor(self) -> float:
        """Get current drawdown-based risk factor."""
        return self._dd_risk_factor
