"""
Performance Metrics and Reporting

Comprehensive performance analysis and reporting for paper trading results.
Includes standard trading metrics, risk analysis, and visualization.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

from .portfolio import Trade, AccountSnapshot


class PerformanceMetrics:
    """Calculate comprehensive trading performance metrics."""
    
    def __init__(self, trades: List[Trade], account_history: List[AccountSnapshot], 
                 initial_cash: float):
        self.trades = trades
        self.account_history = account_history
        self.initial_cash = initial_cash
        
        # Calculate derived metrics
        self._calculate_metrics()
    
    def _calculate_metrics(self):
        """Calculate all performance metrics."""
        
        if not self.trades:
            self._set_zero_metrics()
            return
        
        # Basic metrics
        self.total_trades = len(self.trades)
        self.winning_trades = len([t for t in self.trades if self._get_trade_pnl(t) > 0])
        self.losing_trades = len([t for t in self.trades if self._get_trade_pnl(t) < 0])
        
        # PnL metrics
        self.total_pnl = sum(self._get_trade_pnl(t) for t in self.trades)
        self.total_fees = sum(t.fee for t in self.trades)
        self.net_pnl = self.total_pnl - self.total_fees
        
        # Return metrics
        self.total_return = (self.net_pnl / self.initial_cash) * 100.0
        
        # Win rate
        self.win_rate = (self.winning_trades / self.total_trades) * 100.0 if self.total_trades > 0 else 0.0
        
        # Average metrics
        self.avg_win = self._calculate_avg_win()
        self.avg_loss = self._calculate_avg_loss()
        self.avg_trade = self.net_pnl / self.total_trades if self.total_trades > 0 else 0.0
        
        # Risk metrics
        self.max_drawdown = self._calculate_max_drawdown()
        self.sharpe_ratio = self._calculate_sharpe_ratio()
        self.sortino_ratio = self._calculate_sortino_ratio()
        
        # Time metrics
        self.time_in_market = self._calculate_time_in_market()
        self.avg_trade_duration = self._calculate_avg_trade_duration()
        
        # Additional metrics
        self.expectancy = self._calculate_expectancy()
        self.profit_factor = self._calculate_profit_factor()
        self.recovery_factor = self._calculate_recovery_factor()
        
        # Annualized metrics (if applicable)
        self.annualized_return = self._calculate_annualized_return()
    
    def _set_zero_metrics(self):
        """Set all metrics to zero for empty trade list."""
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0.0
        self.total_fees = 0.0
        self.net_pnl = 0.0
        self.total_return = 0.0
        self.win_rate = 0.0
        self.avg_win = 0.0
        self.avg_loss = 0.0
        self.avg_trade = 0.0
        self.max_drawdown = 0.0
        self.sharpe_ratio = 0.0
        self.sortino_ratio = 0.0
        self.time_in_market = 0.0
        self.avg_trade_duration = 0.0
        self.expectancy = 0.0
        self.profit_factor = 0.0
        self.recovery_factor = 0.0
        self.annualized_return = 0.0
    
    def _get_trade_pnl(self, trade: Trade) -> float:
        """Calculate PnL for a trade (simplified - assumes sell trades close positions)."""
        if trade.side == "sell":
            # This is a simplified calculation - in reality you'd need to track
            # entry prices and position sizes more carefully
            return trade.value - trade.fee
        else:
            return -trade.fee  # Buy trades only incur fees
    
    def _calculate_avg_win(self) -> float:
        """Calculate average winning trade."""
        winning_trades = [t for t in self.trades if self._get_trade_pnl(t) > 0]
        if not winning_trades:
            return 0.0
        return sum(self._get_trade_pnl(t) for t in winning_trades) / len(winning_trades)
    
    def _calculate_avg_loss(self) -> float:
        """Calculate average losing trade."""
        losing_trades = [t for t in self.trades if self._get_trade_pnl(t) < 0]
        if not losing_trades:
            return 0.0
        return sum(self._get_trade_pnl(t) for t in losing_trades) / len(losing_trades)
    
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown."""
        if not self.account_history:
            return 0.0
        
        equity_values = [snapshot.total_equity for snapshot in self.account_history]
        peak = equity_values[0]
        max_dd = 0.0
        
        for equity in equity_values:
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak * 100.0
            max_dd = max(max_dd, dd)
        
        return max_dd
    
    def _calculate_sharpe_ratio(self, risk_free_rate: float = 0.0) -> float:
        """Calculate Sharpe ratio."""
        if not self.account_history or len(self.account_history) < 2:
            return 0.0
        
        # Calculate daily returns
        returns = []
        for i in range(1, len(self.account_history)):
            prev_equity = self.account_history[i-1].total_equity
            curr_equity = self.account_history[i].total_equity
            daily_return = (curr_equity - prev_equity) / prev_equity
            returns.append(daily_return)
        
        if not returns:
            return 0.0
        
        avg_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0.0
        
        return (avg_return - risk_free_rate / 365) / std_return
    
    def _calculate_sortino_ratio(self, risk_free_rate: float = 0.0) -> float:
        """Calculate Sortino ratio."""
        if not self.account_history or len(self.account_history) < 2:
            return 0.0
        
        # Calculate daily returns
        returns = []
        for i in range(1, len(self.account_history)):
            prev_equity = self.account_history[i-1].total_equity
            curr_equity = self.account_history[i].total_equity
            daily_return = (curr_equity - prev_equity) / prev_equity
            returns.append(daily_return)
        
        if not returns:
            return 0.0
        
        avg_return = np.mean(returns)
        downside_returns = [r for r in returns if r < 0]
        
        if not downside_returns:
            return float('inf') if avg_return > risk_free_rate / 365 else 0.0
        
        downside_deviation = np.std(downside_returns)
        
        if downside_deviation == 0:
            return 0.0
        
        return (avg_return - risk_free_rate / 365) / downside_deviation
    
    def _calculate_time_in_market(self) -> float:
        """Calculate percentage of time in market."""
        if not self.account_history:
            return 0.0
        
        total_time = (self.account_history[-1].timestamp - self.account_history[0].timestamp).total_seconds()
        time_with_positions = sum(
            (snapshot.timestamp - self.account_history[0].timestamp).total_seconds()
            for snapshot in self.account_history
            if snapshot.positions
        )
        
        return (time_with_positions / total_time) * 100.0 if total_time > 0 else 0.0
    
    def _calculate_avg_trade_duration(self) -> float:
        """Calculate average trade duration in hours."""
        if not self.trades:
            return 0.0
        
        # This is simplified - in reality you'd need to track entry/exit times
        return 24.0  # Placeholder
    
    def _calculate_expectancy(self) -> float:
        """Calculate trading expectancy."""
        if self.total_trades == 0:
            return 0.0
        
        return (self.win_rate / 100.0) * self.avg_win + ((100.0 - self.win_rate) / 100.0) * self.avg_loss
    
    def _calculate_profit_factor(self) -> float:
        """Calculate profit factor."""
        gross_profit = sum(self._get_trade_pnl(t) for t in self.trades if self._get_trade_pnl(t) > 0)
        gross_loss = abs(sum(self._get_trade_pnl(t) for t in self.trades if self._get_trade_pnl(t) < 0))
        
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0
        
        return gross_profit / gross_loss
    
    def _calculate_recovery_factor(self) -> float:
        """Calculate recovery factor."""
        if self.max_drawdown == 0:
            return float('inf') if self.net_pnl > 0 else 0.0
        
        return self.net_pnl / (self.max_drawdown / 100.0 * self.initial_cash)
    
    def _calculate_annualized_return(self) -> float:
        """Calculate annualized return."""
        if not self.account_history or len(self.account_history) < 2:
            return 0.0
        
        start_time = self.account_history[0].timestamp
        end_time = self.account_history[-1].timestamp
        days = (end_time - start_time).days
        
        if days == 0:
            return 0.0
        
        years = days / 365.25
        return ((1 + self.total_return / 100.0) ** (1 / years) - 1) * 100.0
    
    def get_summary(self) -> Dict[str, Any]:
        """Get complete performance summary."""
        return {
            # Basic metrics
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": round(self.win_rate, 2),
            
            # PnL metrics
            "total_pnl": round(self.total_pnl, 2),
            "total_fees": round(self.total_fees, 2),
            "net_pnl": round(self.net_pnl, 2),
            "total_return": round(self.total_return, 2),
            "annualized_return": round(self.annualized_return, 2),
            
            # Risk metrics
            "max_drawdown": round(self.max_drawdown, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 3),
            "sortino_ratio": round(self.sortino_ratio, 3),
            
            # Trade metrics
            "avg_win": round(self.avg_win, 2),
            "avg_loss": round(self.avg_loss, 2),
            "avg_trade": round(self.avg_trade, 2),
            "expectancy": round(self.expectancy, 2),
            "profit_factor": round(self.profit_factor, 2),
            "recovery_factor": round(self.recovery_factor, 2),
            
            # Time metrics
            "time_in_market": round(self.time_in_market, 2),
            "avg_trade_duration": round(self.avg_trade_duration, 2),
        }


class ReportGenerator:
    """Generate comprehensive trading reports."""
    
    def __init__(self, metrics: PerformanceMetrics, run_id: str, config: Dict[str, Any]):
        self.metrics = metrics
        self.run_id = run_id
        self.config = config
    
    def generate_json_report(self, output_path: str) -> str:
        """Generate JSON report."""
        
        report = {
            "run_id": self.run_id,
            "config": self.config,
            "metrics": self.metrics.get_summary(),
            "generated_at": datetime.now().isoformat(),
        }
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        return str(output_file)
    
    def generate_html_report(self, output_path: str, trades_df: Optional[pd.DataFrame] = None,
                           account_df: Optional[pd.DataFrame] = None) -> str:
        """Generate HTML report with charts."""
        
        summary = self.metrics.get_summary()
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Paper Trading Report - {self.run_id}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
                .metric {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; border-left: 4px solid #007bff; }}
                .metric h3 {{ margin: 0 0 10px 0; color: #333; }}
                .metric .value {{ font-size: 24px; font-weight: bold; color: #007bff; }}
                .metric .label {{ font-size: 14px; color: #666; }}
                .section {{ margin: 30px 0; }}
                .section h2 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .positive {{ color: #28a745; }}
                .negative {{ color: #dc3545; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Paper Trading Performance Report</h1>
                <p><strong>Run ID:</strong> {self.run_id}</p>
                <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="section">
                <h2>Performance Summary</h2>
                <div class="metrics">
                    <div class="metric">
                        <h3>Total Return</h3>
                        <div class="value {'positive' if summary['total_return'] > 0 else 'negative'}">{summary['total_return']:.2f}%</div>
                        <div class="label">Net return on initial capital</div>
                    </div>
                    <div class="metric">
                        <h3>Total Trades</h3>
                        <div class="value">{summary['total_trades']}</div>
                        <div class="label">Number of executed trades</div>
                    </div>
                    <div class="metric">
                        <h3>Win Rate</h3>
                        <div class="value">{summary['win_rate']:.1f}%</div>
                        <div class="label">Percentage of profitable trades</div>
                    </div>
                    <div class="metric">
                        <h3>Max Drawdown</h3>
                        <div class="value negative">{summary['max_drawdown']:.2f}%</div>
                        <div class="label">Maximum peak-to-trough decline</div>
                    </div>
                    <div class="metric">
                        <h3>Sharpe Ratio</h3>
                        <div class="value">{summary['sharpe_ratio']:.3f}</div>
                        <div class="label">Risk-adjusted return</div>
                    </div>
                    <div class="metric">
                        <h3>Profit Factor</h3>
                        <div class="value">{summary['profit_factor']:.2f}</div>
                        <div class="label">Gross profit / Gross loss</div>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>Detailed Metrics</h2>
                <table>
                    <tr><th>Metric</th><th>Value</th></tr>
                    <tr><td>Net P&L</td><td class="{'positive' if summary['net_pnl'] > 0 else 'negative'}">${summary['net_pnl']:.2f}</td></tr>
                    <tr><td>Total Fees</td><td>${summary['total_fees']:.2f}</td></tr>
                    <tr><td>Average Win</td><td class="positive">${summary['avg_win']:.2f}</td></tr>
                    <tr><td>Average Loss</td><td class="negative">${summary['avg_loss']:.2f}</td></tr>
                    <tr><td>Average Trade</td><td class="{'positive' if summary['avg_trade'] > 0 else 'negative'}">${summary['avg_trade']:.2f}</td></tr>
                    <tr><td>Expectancy</td><td class="{'positive' if summary['expectancy'] > 0 else 'negative'}">${summary['expectancy']:.2f}</td></tr>
                    <tr><td>Recovery Factor</td><td>{summary['recovery_factor']:.2f}</td></tr>
                    <tr><td>Time in Market</td><td>{summary['time_in_market']:.1f}%</td></tr>
                    <tr><td>Annualized Return</td><td class="{'positive' if summary['annualized_return'] > 0 else 'negative'}">{summary['annualized_return']:.2f}%</td></tr>
                </table>
            </div>
            
            <div class="section">
                <h2>Configuration</h2>
                <pre>{json.dumps(self.config, indent=2)}</pre>
            </div>
        </body>
        </html>
        """
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        return str(output_file)
    
    def generate_jupyter_notebook(self, output_path: str, trades_df: Optional[pd.DataFrame] = None,
                                account_df: Optional[pd.DataFrame] = None) -> str:
        """Generate Jupyter notebook with analysis and charts."""
        
        notebook_content = {
            "cells": [
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": [
                        f"# Paper Trading Analysis - {self.run_id}\n",
                        f"\n",
                        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
                        f"\n",
                        f"This notebook provides a comprehensive analysis of the paper trading results."
                    ]
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": [
                        "import pandas as pd\n",
                        "import numpy as np\n",
                        "import matplotlib.pyplot as plt\n",
                        "import seaborn as sns\n",
                        "from datetime import datetime\n",
                        "\n",
                        "# Set style\n",
                        "plt.style.use('seaborn-v0_8')\n",
                        "sns.set_palette('husl')"
                    ]
                },
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": [
                        "## Performance Summary\n",
                        "\n",
                        "Key performance metrics for this trading run:"
                    ]
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": [
                        f"# Performance metrics\n",
                        f"summary = {json.dumps(self.metrics.get_summary(), indent=2)}\n",
                        f"\n",
                        f"print(\"Performance Summary:\")\n",
                        f"print(\"=\" * 50)\n",
                        f"for key, value in summary.items():\n",
                        f"    print(f\"{{key}}: {{value}}\")"
                    ]
                }
            ],
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3"
                },
                "language_info": {
                    "name": "python",
                    "version": "3.8.0"
                }
            },
            "nbformat": 4,
            "nbformat_minor": 4
        }
        
        # Add more cells if data is available
        if trades_df is not None:
            notebook_content["cells"].extend([
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": ["## Trade Analysis"]
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": [
                        "# Load trade data\n",
                        "trades_df = pd.read_csv('trades.csv')\n",
                        "print(f\"Total trades: {len(trades_df)}\")\n",
                        "print(f\"\\nTrade summary:\")\n",
                        "print(trades_df.describe())"
                    ]
                }
            ])
        
        if account_df is not None:
            notebook_content["cells"].extend([
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": ["## Portfolio Evolution"]
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": [
                        "# Load account history\n",
                        "account_df = pd.read_csv('account_history.csv')\n",
                        "account_df['timestamp'] = pd.to_datetime(account_df['timestamp'])\n",
                        "\n",
                        "# Plot equity curve\n",
                        "plt.figure(figsize=(12, 6))\n",
                        "plt.plot(account_df['timestamp'], account_df['total_equity'])\n",
                        "plt.title('Portfolio Equity Over Time')\n",
                        "plt.xlabel('Date')\n",
                        "plt.ylabel('Total Equity ($)')\n",
                        "plt.xticks(rotation=45)\n",
                        "plt.tight_layout()\n",
                        "plt.show()"
                    ]
                }
            ])
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(notebook_content, f, indent=2)
        
        return str(output_file)
