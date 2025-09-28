"""
Advanced risk metrics calculation for backtest simulation.
Implements Sharpe, Sortino, Calmar ratios and other sophisticated risk measures.
"""

import math
from typing import List, Optional

from .models import Trade


class AdvancedMetricsCalculator:
    """Calculates advanced risk-adjusted performance metrics."""

    @staticmethod
    def calculate_sharpe_ratio(
        equity: List[float], 
        risk_free_rate: float = 0.02, 
        timeframe: str = "1d"
    ) -> float:
        """
        Calculate Sharpe ratio (excess return / volatility).
        
        Args:
            equity: List of equity values over time
            risk_free_rate: Annual risk-free rate (default 2%)
            timeframe: Timeframe for annualization
            
        Returns:
            Sharpe ratio (higher is better)
        """
        if len(equity) < 2:
            return 0.0
        
        # Calculate period returns
        returns = []
        for i in range(1, len(equity)):
            if equity[i-1] > 0:
                period_return = (equity[i] - equity[i-1]) / equity[i-1]
                returns.append(period_return)
        
        if not returns:
            return 0.0
        
        # Calculate annualized return and volatility
        periods_per_year = AdvancedMetricsCalculator._get_periods_per_year(timeframe)
        years = len(equity) / periods_per_year
        
        if years <= 0:
            return 0.0
        
        # Annualized return
        total_return = (equity[-1] / equity[0]) ** (1.0 / years) - 1.0
        excess_return = total_return - risk_free_rate
        
        # Annualized volatility
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        volatility = math.sqrt(variance * periods_per_year)
        
        if volatility == 0:
            return float("inf") if excess_return > 0 else 0.0
        
        return excess_return / volatility

    @staticmethod
    def calculate_sortino_ratio(
        equity: List[float], 
        risk_free_rate: float = 0.02, 
        timeframe: str = "1d"
    ) -> float:
        """
        Calculate Sortino ratio (excess return / downside deviation).
        
        Args:
            equity: List of equity values over time
            risk_free_rate: Annual risk-free rate (default 2%)
            timeframe: Timeframe for annualization
            
        Returns:
            Sortino ratio (higher is better)
        """
        if len(equity) < 2:
            return 0.0
        
        # Calculate period returns
        returns = []
        for i in range(1, len(equity)):
            if equity[i-1] > 0:
                period_return = (equity[i] - equity[i-1]) / equity[i-1]
                returns.append(period_return)
        
        if not returns:
            return 0.0
        
        # Calculate annualized return
        periods_per_year = AdvancedMetricsCalculator._get_periods_per_year(timeframe)
        years = len(equity) / periods_per_year
        
        if years <= 0:
            return 0.0
        
        total_return = (equity[-1] / equity[0]) ** (1.0 / years) - 1.0
        excess_return = total_return - risk_free_rate
        
        # Calculate downside deviation (only negative returns)
        mean_return = sum(returns) / len(returns)
        downside_returns = [r for r in returns if r < mean_return]
        
        if not downside_returns:
            return float("inf") if excess_return > 0 else 0.0
        
        downside_variance = sum((r - mean_return) ** 2 for r in downside_returns) / len(returns)
        downside_deviation = math.sqrt(downside_variance * periods_per_year)
        
        if downside_deviation == 0:
            return float("inf") if excess_return > 0 else 0.0
        
        return excess_return / downside_deviation

    @staticmethod
    def calculate_calmar_ratio(equity: List[float], timeframe: str = "1d") -> float:
        """
        Calculate Calmar ratio (CAGR / Max Drawdown).
        
        Args:
            equity: List of equity values over time
            timeframe: Timeframe for annualization
            
        Returns:
            Calmar ratio (higher is better)
        """
        if len(equity) < 2:
            return 0.0
        
        # Calculate CAGR
        periods_per_year = AdvancedMetricsCalculator._get_periods_per_year(timeframe)
        years = len(equity) / periods_per_year
        
        if years <= 0 or equity[0] <= 0:
            return 0.0
        
        cagr = (equity[-1] / equity[0]) ** (1.0 / years) - 1.0
        
        # Calculate max drawdown
        peak = equity[0]
        max_dd = 0.0
        
        for value in equity:
            if value > peak:
                peak = value
            dd = (peak - value) / peak
            max_dd = max(max_dd, dd)
        
        if max_dd == 0:
            return float("inf") if cagr > 0 else 0.0
        
        return (cagr * 100.0) / (max_dd * 100.0)

    @staticmethod
    def calculate_information_ratio(
        strategy_returns: List[float], 
        benchmark_returns: List[float]
    ) -> float:
        """
        Calculate Information ratio (active return / tracking error).
        
        Args:
            strategy_returns: Strategy period returns
            benchmark_returns: Benchmark period returns (same length)
            
        Returns:
            Information ratio (higher is better)
        """
        if len(strategy_returns) != len(benchmark_returns) or len(strategy_returns) < 2:
            return 0.0
        
        # Calculate active returns (strategy - benchmark)
        active_returns = [s - b for s, b in zip(strategy_returns, benchmark_returns)]
        
        if not active_returns:
            return 0.0
        
        # Calculate mean active return
        mean_active_return = sum(active_returns) / len(active_returns)
        
        # Calculate tracking error (std dev of active returns)
        variance = sum((r - mean_active_return) ** 2 for r in active_returns) / len(active_returns)
        tracking_error = math.sqrt(variance)
        
        if tracking_error == 0:
            return float("inf") if mean_active_return > 0 else 0.0
        
        return mean_active_return / tracking_error

    @staticmethod
    def calculate_win_loss_distribution(trades: List[Trade]) -> dict:
        """
        Calculate win/loss distribution statistics.
        
        Args:
            trades: List of completed trades
            
        Returns:
            Dictionary with distribution statistics
        """
        if not trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "largest_win": 0.0,
                "largest_loss": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "win_loss_ratio": 0.0,
                "consecutive_wins": 0,
                "consecutive_losses": 0,
            }
        
        winning_trades = [t for t in trades if t.pnl_pct() and t.pnl_pct() > 0]
        losing_trades = [t for t in trades if t.pnl_pct() and t.pnl_pct() < 0]
        
        largest_win = max((t.pnl_pct() for t in winning_trades), default=0.0)
        largest_loss = min((t.pnl_pct() for t in losing_trades), default=0.0)
        
        avg_win = sum(t.pnl_pct() for t in winning_trades) / len(winning_trades) if winning_trades else 0.0
        avg_loss = sum(t.pnl_pct() for t in losing_trades) / len(losing_trades) if losing_trades else 0.0
        
        win_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else float("inf") if avg_win > 0 else 0.0
        
        # Calculate consecutive wins/losses
        consecutive_wins = 0
        consecutive_losses = 0
        current_streak = 0
        current_type = None
        
        for trade in trades:
            if trade.pnl_pct() is None:
                continue
            
            is_win = trade.pnl_pct() > 0
            
            if current_type is None:
                current_type = is_win
                current_streak = 1
            elif current_type == is_win:
                current_streak += 1
            else:
                if current_type:  # Was winning streak
                    consecutive_wins = max(consecutive_wins, current_streak)
                else:  # Was losing streak
                    consecutive_losses = max(consecutive_losses, current_streak)
                
                current_type = is_win
                current_streak = 1
        
        # Check final streak
        if current_type:  # Final streak was winning
            consecutive_wins = max(consecutive_wins, current_streak)
        else:  # Final streak was losing
            consecutive_losses = max(consecutive_losses, current_streak)
        
        return {
            "total_trades": len(trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "largest_win": largest_win,
            "largest_loss": largest_loss,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "win_loss_ratio": win_loss_ratio,
            "consecutive_wins": consecutive_wins,
            "consecutive_losses": consecutive_losses,
        }

    @staticmethod
    def calculate_tail_risk_metrics(equity: List[float]) -> dict:
        """
        Calculate tail risk metrics (VaR, CVaR).
        
        Args:
            equity: List of equity values over time
            
        Returns:
            Dictionary with tail risk metrics
        """
        if len(equity) < 2:
            return {
                "var_95": 0.0,
                "var_99": 0.0,
                "cvar_95": 0.0,
                "cvar_99": 0.0,
                "skewness": 0.0,
                "kurtosis": 0.0,
            }
        
        # Calculate period returns
        returns = []
        for i in range(1, len(equity)):
            if equity[i-1] > 0:
                period_return = (equity[i] - equity[i-1]) / equity[i-1]
                returns.append(period_return)
        
        if not returns:
            return {
                "var_95": 0.0,
                "var_99": 0.0,
                "cvar_95": 0.0,
                "cvar_99": 0.0,
                "skewness": 0.0,
                "kurtosis": 0.0,
            }
        
        # Sort returns for percentile calculations
        sorted_returns = sorted(returns)
        n = len(sorted_returns)
        
        # Calculate VaR (Value at Risk)
        var_95_idx = int(0.05 * n)
        var_99_idx = int(0.01 * n)
        
        var_95 = sorted_returns[var_95_idx] if var_95_idx < n else sorted_returns[0]
        var_99 = sorted_returns[var_99_idx] if var_99_idx < n else sorted_returns[0]
        
        # Calculate CVaR (Conditional Value at Risk)
        cvar_95 = sum(sorted_returns[:var_95_idx+1]) / (var_95_idx + 1) if var_95_idx >= 0 else 0.0
        cvar_99 = sum(sorted_returns[:var_99_idx+1]) / (var_99_idx + 1) if var_99_idx >= 0 else 0.0
        
        # Calculate higher moments
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance)
        
        if std_dev == 0:
            skewness = 0.0
            kurtosis = 0.0
        else:
            # Skewness
            skewness = sum((r - mean_return) ** 3 for r in returns) / (len(returns) * std_dev ** 3)
            
            # Kurtosis (excess kurtosis)
            kurtosis = sum((r - mean_return) ** 4 for r in returns) / (len(returns) * std_dev ** 4) - 3
        
        return {
            "var_95": var_95 * 100.0,  # Convert to percentage
            "var_99": var_99 * 100.0,
            "cvar_95": cvar_95 * 100.0,
            "cvar_99": cvar_99 * 100.0,
            "skewness": skewness,
            "kurtosis": kurtosis,
        }

    @staticmethod
    def _get_periods_per_year(timeframe: str) -> int:
        """Get number of periods per year for annualization."""
        return {
            "1d": 365,
            "4h": 365 * 6,
            "1h": 365 * 24,
            "30m": 365 * 48,
            "15m": 365 * 96,
            "5m": 365 * 288,
        }.get(timeframe, 365)

    @classmethod
    def calculate_all_advanced_metrics(
        cls, 
        trades: List[Trade], 
        equity: List[float], 
        timeframe: str,
        risk_free_rate: float = 0.02
    ) -> dict:
        """
        Calculate all advanced metrics at once.
        
        Args:
            trades: List of completed trades
            equity: List of equity values over time
            timeframe: Timeframe for annualization
            risk_free_rate: Annual risk-free rate
            
        Returns:
            Dictionary with all advanced metrics
        """
        # Risk-adjusted ratios
        sharpe_ratio = cls.calculate_sharpe_ratio(equity, risk_free_rate, timeframe)
        sortino_ratio = cls.calculate_sortino_ratio(equity, risk_free_rate, timeframe)
        calmar_ratio = cls.calculate_calmar_ratio(equity, timeframe)
        
        # Distribution metrics
        win_loss_dist = cls.calculate_win_loss_distribution(trades)
        tail_risk = cls.calculate_tail_risk_metrics(equity)
        
        return {
            # Risk-adjusted ratios
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            "calmar_ratio": calmar_ratio,
            
            # Win/loss distribution
            **win_loss_dist,
            
            # Tail risk metrics
            **tail_risk,
        }
