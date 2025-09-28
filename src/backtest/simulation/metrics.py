"""
Metrics calculation for backtest simulation.
"""

from typing import List

from .models import BacktestResult, Trade


class MetricsCalculator:
    """Calculates performance metrics from backtest results."""

    @staticmethod
    def calculate_win_rate(trades: List[Trade]) -> float:
        """Calculate win rate percentage."""
        if not trades:
            return 0.0

        winning_trades = sum(1 for trade in trades if trade.pnl_pct() and trade.pnl_pct() > 0)
        return (winning_trades / len(trades)) * 100.0

    @staticmethod
    def calculate_profit_factor(trades: List[Trade]) -> float:
        """Calculate profit factor."""
        if not trades:
            return 0.0

        gross_profit = sum(
            trade.pnl_pct() for trade in trades if trade.pnl_pct() and trade.pnl_pct() > 0
        )
        gross_loss = abs(
            sum(trade.pnl_pct() for trade in trades if trade.pnl_pct() and trade.pnl_pct() < 0)
        )

        if gross_loss == 0:
            return float("inf") if gross_profit > 0 else 0.0

        return gross_profit / gross_loss

    @staticmethod
    def calculate_max_drawdown(equity: List[float]) -> float:
        """Calculate maximum drawdown percentage."""
        if not equity:
            return 0.0

        peak = equity[0]
        max_dd = 0.0

        for value in equity:
            if value > peak:
                peak = value
            dd = (peak - value) / peak * 100.0
            max_dd = max(max_dd, dd)

        return max_dd

    @staticmethod
    def calculate_cagr(equity: List[float], timeframe: str) -> float:
        """Calculate Compound Annual Growth Rate."""
        if len(equity) < 2:
            return 0.0

        initial = equity[0]
        final = equity[-1]

        if initial <= 0:
            return 0.0

        # Calculate years based on timeframe
        periods_per_year = {
            "1d": 365,
            "4h": 365 * 6,
            "1h": 365 * 24,
            "30m": 365 * 48,
            "15m": 365 * 96,
            "5m": 365 * 288,
        }.get(timeframe, 365)

        years = len(equity) / periods_per_year

        if years <= 0:
            return 0.0

        return ((final / initial) ** (1.0 / years) - 1.0) * 100.0

    @staticmethod
    def calculate_mar(cagr: float, max_drawdown: float) -> float:
        """Calculate MAR (CAGR / Max Drawdown)."""
        if max_drawdown <= 0:
            return float("inf") if cagr > 0 else 0.0
        return cagr / max_drawdown

    @staticmethod
    def calculate_avg_return(trades: List[Trade]) -> float:
        """Calculate average return per trade."""
        if not trades:
            return 0.0

        returns = [trade.pnl_pct() for trade in trades if trade.pnl_pct() is not None]
        if not returns:
            return 0.0

        return sum(returns) / len(returns)

    @classmethod
    def calculate_all_metrics(
        cls, trades: List[Trade], equity: List[float], timeframe: str
    ) -> dict:
        """Calculate all metrics at once."""
        win_rate = cls.calculate_win_rate(trades)
        profit_factor = cls.calculate_profit_factor(trades)
        max_drawdown = cls.calculate_max_drawdown(equity)
        cagr = cls.calculate_cagr(equity, timeframe)
        mar = cls.calculate_mar(cagr, max_drawdown)
        avg_return = cls.calculate_avg_return(trades)

        return {
            "trades": len(trades),
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "max_drawdown": max_drawdown,
            "cagr": cagr,
            "mar": mar,
            "avg_return_pct": avg_return,
        }
