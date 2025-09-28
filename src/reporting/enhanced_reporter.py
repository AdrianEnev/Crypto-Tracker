"""
Enhanced performance reporting system with advanced risk metrics and visualization.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


class EnhancedReporter:
    """Enhanced performance reporter with advanced metrics and visualizations."""
    
    def __init__(self, db_path: Path, output_dir: Path):
        self.db_path = db_path
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_comprehensive_report(self, risk_free_rate: float = 0.02) -> Dict[str, Any]:
        """
        Generate a comprehensive performance report with all metrics.
        
        Args:
            risk_free_rate: Annual risk-free rate for risk-adjusted metrics
            
        Returns:
            Dictionary containing all report data
        """
        conn = sqlite3.connect(self.db_path)
        
        try:
            # Load data
            trades_df = self._load_trades_data(conn)
            equity_df = self._load_equity_data(conn)
            
            if trades_df.empty or equity_df.empty:
                return {"error": "Insufficient data for report generation"}
            
            # Calculate metrics
            report_data = self._calculate_comprehensive_metrics(
                trades_df, equity_df, risk_free_rate
            )
            
            # Generate reports
            self._generate_summary_report(report_data)
            self._generate_detailed_metrics_report(report_data)
            self._generate_trade_analysis_report(trades_df)
            self._generate_risk_analysis_report(report_data)
            self._generate_performance_attribution_report(trades_df)
            
            # Save JSON report
            json_path = self.output_dir / "comprehensive_report.json"
            with open(json_path, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            print(f"Comprehensive report saved to {json_path}")
            return report_data
            
        finally:
            conn.close()
    
    def _load_trades_data(self, conn: sqlite3.Connection) -> pd.DataFrame:
        """Load and process trades data."""
        try:
            trades_df = pd.read_sql_query("SELECT * FROM trades", conn)
            if not trades_df.empty:
                # Ensure numeric columns are properly typed
                numeric_columns = ['pnl_pct', 'entry_price', 'exit_price', 'quantity']
                for col in numeric_columns:
                    if col in trades_df.columns:
                        trades_df[col] = pd.to_numeric(trades_df[col], errors='coerce')
                
                # Convert timestamp columns
                if 'entry_time' in trades_df.columns:
                    trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'], errors='coerce')
                if 'exit_time' in trades_df.columns:
                    trades_df['exit_time'] = pd.to_datetime(trades_df['exit_time'], errors='coerce')
            
            return trades_df
        except Exception as e:
            print(f"Error loading trades data: {e}")
            return pd.DataFrame()
    
    def _load_equity_data(self, conn: sqlite3.Connection) -> pd.DataFrame:
        """Load and process equity data."""
        try:
            equity_df = pd.read_sql_query("SELECT * FROM equity", conn)
            if not equity_df.empty:
                equity_df['ts'] = pd.to_datetime(equity_df['ts'], errors='coerce')
                equity_df = equity_df.set_index('ts')
                equity_df['equity_usd'] = pd.to_numeric(equity_df['equity_usd'], errors='coerce')
                equity_df = equity_df.sort_index()
            
            return equity_df
        except Exception as e:
            print(f"Error loading equity data: {e}")
            return pd.DataFrame()
    
    def _calculate_comprehensive_metrics(
        self, trades_df: pd.DataFrame, equity_df: pd.DataFrame, risk_free_rate: float
    ) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics."""
        equity_values = equity_df['equity_usd'].dropna().tolist()
        
        # Basic performance metrics
        initial_equity = equity_values[0] if equity_values else 0
        final_equity = equity_values[-1] if equity_values else 0
        
        # Calculate returns
        returns = []
        for i in range(1, len(equity_values)):
            if equity_values[i-1] > 0:
                period_return = (equity_values[i] - equity_values[i-1]) / equity_values[i-1]
                returns.append(period_return)
        
        # Time-based metrics
        if len(equity_values) > 1:
            time_span = (equity_df.index[-1] - equity_df.index[0]).days / 365.0
            total_return = (final_equity / initial_equity - 1) * 100 if initial_equity > 0 else 0
            cagr = (final_equity / initial_equity) ** (1.0 / time_span) - 1 if time_span > 0 and initial_equity > 0 else 0
        else:
            time_span = 0
            total_return = 0
            cagr = 0
        
        # Drawdown analysis
        peak = equity_values[0]
        max_dd = 0
        drawdowns = []
        for value in equity_values:
            if value > peak:
                peak = value
            dd = (peak - value) / peak * 100 if peak > 0 else 0
            max_dd = max(max_dd, dd)
            drawdowns.append(dd)
        
        # Risk metrics
        if returns:
            import math
            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
            volatility = math.sqrt(variance * 252) * 100  # Annualized
            
            # Risk-adjusted ratios
            excess_return = cagr - risk_free_rate
            sharpe_ratio = excess_return / (volatility / 100) if volatility > 0 else 0
            
            # Sortino ratio (downside deviation)
            downside_returns = [r for r in returns if r < mean_return]
            if downside_returns:
                downside_variance = sum((r - mean_return) ** 2 for r in downside_returns) / len(returns)
                downside_deviation = math.sqrt(downside_variance * 252) * 100
                sortino_ratio = excess_return / (downside_deviation / 100) if downside_deviation > 0 else 0
            else:
                sortino_ratio = float('inf') if excess_return > 0 else 0
            
            # Calmar ratio
            calmar_ratio = (cagr * 100) / max_dd if max_dd > 0 else float('inf') if cagr > 0 else 0
        else:
            volatility = 0
            sharpe_ratio = 0
            sortino_ratio = 0
            calmar_ratio = 0
        
        # Trade analysis
        if not trades_df.empty and 'pnl_pct' in trades_df.columns:
            winning_trades = trades_df[trades_df['pnl_pct'] > 0]
            losing_trades = trades_df[trades_df['pnl_pct'] < 0]
            
            win_rate = len(winning_trades) / len(trades_df) * 100 if len(trades_df) > 0 else 0
            avg_win = winning_trades['pnl_pct'].mean() if len(winning_trades) > 0 else 0
            avg_loss = losing_trades['pnl_pct'].mean() if len(losing_trades) > 0 else 0
            profit_factor = abs(winning_trades['pnl_pct'].sum() / losing_trades['pnl_pct'].sum()) if len(losing_trades) > 0 and losing_trades['pnl_pct'].sum() != 0 else float('inf') if len(winning_trades) > 0 else 0
            
            largest_win = winning_trades['pnl_pct'].max() if len(winning_trades) > 0 else 0
            largest_loss = losing_trades['pnl_pct'].min() if len(losing_trades) > 0 else 0
        else:
            win_rate = 0
            avg_win = 0
            avg_loss = 0
            profit_factor = 0
            largest_win = 0
            largest_loss = 0
        
        return {
            "report_timestamp": datetime.now(timezone.utc).isoformat(),
            "time_period": {
                "start_date": equity_df.index[0].isoformat() if len(equity_df) > 0 else None,
                "end_date": equity_df.index[-1].isoformat() if len(equity_df) > 0 else None,
                "duration_days": time_span * 365 if time_span > 0 else 0,
            },
            "equity_metrics": {
                "initial_equity": initial_equity,
                "final_equity": final_equity,
                "total_return_pct": total_return,
                "cagr_pct": cagr * 100,
                "max_drawdown_pct": max_dd,
                "volatility_pct": volatility,
            },
            "risk_adjusted_metrics": {
                "sharpe_ratio": sharpe_ratio,
                "sortino_ratio": sortino_ratio,
                "calmar_ratio": calmar_ratio,
                "risk_free_rate": risk_free_rate,
            },
            "trade_metrics": {
                "total_trades": len(trades_df) if not trades_df.empty else 0,
                "winning_trades": len(winning_trades) if not trades_df.empty else 0,
                "losing_trades": len(losing_trades) if not trades_df.empty else 0,
                "win_rate_pct": win_rate,
                "profit_factor": profit_factor,
                "avg_win_pct": avg_win,
                "avg_loss_pct": avg_loss,
                "largest_win_pct": largest_win,
                "largest_loss_pct": largest_loss,
            },
            "drawdown_analysis": {
                "max_drawdown_pct": max_dd,
                "avg_drawdown_pct": sum(drawdowns) / len(drawdowns) if drawdowns else 0,
                "drawdown_duration_days": self._calculate_drawdown_duration(drawdowns),
            }
        }
    
    def _calculate_drawdown_duration(self, drawdowns: List[float]) -> float:
        """Calculate average drawdown duration."""
        if not drawdowns:
            return 0
        
        in_drawdown = False
        drawdown_periods = []
        current_period = 0
        
        for dd in drawdowns:
            if dd > 0:
                if not in_drawdown:
                    in_drawdown = True
                    current_period = 1
                else:
                    current_period += 1
            else:
                if in_drawdown:
                    drawdown_periods.append(current_period)
                    in_drawdown = False
                    current_period = 0
        
        # Handle case where drawdown period extends to end
        if in_drawdown:
            drawdown_periods.append(current_period)
        
        return sum(drawdown_periods) / len(drawdown_periods) if drawdown_periods else 0
    
    def _generate_summary_report(self, report_data: Dict[str, Any]) -> None:
        """Generate summary performance report."""
        summary_df = pd.DataFrame([{
            "Metric": "Total Return (%)",
            "Value": report_data["equity_metrics"]["total_return_pct"]
        }, {
            "Metric": "CAGR (%)",
            "Value": report_data["equity_metrics"]["cagr_pct"]
        }, {
            "Metric": "Max Drawdown (%)",
            "Value": report_data["equity_metrics"]["max_drawdown_pct"]
        }, {
            "Metric": "Volatility (%)",
            "Value": report_data["equity_metrics"]["volatility_pct"]
        }, {
            "Metric": "Sharpe Ratio",
            "Value": report_data["risk_adjusted_metrics"]["sharpe_ratio"]
        }, {
            "Metric": "Sortino Ratio",
            "Value": report_data["risk_adjusted_metrics"]["sortino_ratio"]
        }, {
            "Metric": "Calmar Ratio",
            "Value": report_data["risk_adjusted_metrics"]["calmar_ratio"]
        }, {
            "Metric": "Win Rate (%)",
            "Value": report_data["trade_metrics"]["win_rate_pct"]
        }, {
            "Metric": "Profit Factor",
            "Value": report_data["trade_metrics"]["profit_factor"]
        }])
        
        summary_df.to_csv(self.output_dir / "performance_summary.csv", index=False)
        print(f"Performance summary saved to {self.output_dir / 'performance_summary.csv'}")
    
    def _generate_detailed_metrics_report(self, report_data: Dict[str, Any]) -> None:
        """Generate detailed metrics report."""
        detailed_data = []
        
        # Equity metrics
        for key, value in report_data["equity_metrics"].items():
            detailed_data.append({"Category": "Equity", "Metric": key, "Value": value})
        
        # Risk-adjusted metrics
        for key, value in report_data["risk_adjusted_metrics"].items():
            detailed_data.append({"Category": "Risk-Adjusted", "Metric": key, "Value": value})
        
        # Trade metrics
        for key, value in report_data["trade_metrics"].items():
            detailed_data.append({"Category": "Trades", "Metric": key, "Value": value})
        
        detailed_df = pd.DataFrame(detailed_data)
        detailed_df.to_csv(self.output_dir / "detailed_metrics.csv", index=False)
        print(f"Detailed metrics saved to {self.output_dir / 'detailed_metrics.csv'}")
    
    def _generate_trade_analysis_report(self, trades_df: pd.DataFrame) -> None:
        """Generate detailed trade analysis report."""
        if trades_df.empty:
            return
        
        # Symbol-level analysis
        symbol_analysis = trades_df.groupby('symbol').agg({
            'pnl_pct': ['count', 'mean', 'sum', lambda x: (x > 0).mean() * 100]
        }).round(4)
        
        symbol_analysis.columns = ['total_trades', 'avg_pnl_pct', 'total_pnl_pct', 'win_rate_pct']
        symbol_analysis = symbol_analysis.reset_index()
        
        symbol_analysis.to_csv(self.output_dir / "symbol_analysis.csv", index=False)
        print(f"Symbol analysis saved to {self.output_dir / 'symbol_analysis.csv'}")
        
        # Monthly performance
        if 'entry_time' in trades_df.columns:
            trades_df['month'] = pd.to_datetime(trades_df['entry_time']).dt.to_period('M')
            monthly_performance = trades_df.groupby('month').agg({
                'pnl_pct': ['count', 'sum', 'mean']
            }).round(4)
            
            monthly_performance.columns = ['trades', 'total_pnl_pct', 'avg_pnl_pct']
            monthly_performance = monthly_performance.reset_index()
            
            monthly_performance.to_csv(self.output_dir / "monthly_performance.csv", index=False)
            print(f"Monthly performance saved to {self.output_dir / 'monthly_performance.csv'}")
    
    def _generate_risk_analysis_report(self, report_data: Dict[str, Any]) -> None:
        """Generate risk analysis report."""
        risk_data = []
        
        # Risk metrics
        risk_data.append({"Risk Metric": "Sharpe Ratio", "Value": report_data["risk_adjusted_metrics"]["sharpe_ratio"], "Interpretation": self._interpret_sharpe_ratio(report_data["risk_adjusted_metrics"]["sharpe_ratio"])})
        risk_data.append({"Risk Metric": "Sortino Ratio", "Value": report_data["risk_adjusted_metrics"]["sortino_ratio"], "Interpretation": self._interpret_sortino_ratio(report_data["risk_adjusted_metrics"]["sortino_ratio"])})
        risk_data.append({"Risk Metric": "Calmar Ratio", "Value": report_data["risk_adjusted_metrics"]["calmar_ratio"], "Interpretation": self._interpret_calmar_ratio(report_data["risk_adjusted_metrics"]["calmar_ratio"])})
        risk_data.append({"Risk Metric": "Max Drawdown (%)", "Value": report_data["equity_metrics"]["max_drawdown_pct"], "Interpretation": self._interpret_drawdown(report_data["equity_metrics"]["max_drawdown_pct"])})
        risk_data.append({"Risk Metric": "Volatility (%)", "Value": report_data["equity_metrics"]["volatility_pct"], "Interpretation": self._interpret_volatility(report_data["equity_metrics"]["volatility_pct"])})
        
        risk_df = pd.DataFrame(risk_data)
        risk_df.to_csv(self.output_dir / "risk_analysis.csv", index=False)
        print(f"Risk analysis saved to {self.output_dir / 'risk_analysis.csv'}")
    
    def _generate_performance_attribution_report(self, trades_df: pd.DataFrame) -> None:
        """Generate performance attribution report."""
        if trades_df.empty or 'symbol' not in trades_df.columns:
            return
        
        attribution = trades_df.groupby('symbol').agg({
            'pnl_pct': ['count', 'sum', 'mean']
        }).round(4)
        
        attribution.columns = ['trade_count', 'total_contribution_pct', 'avg_contribution_pct']
        attribution = attribution.reset_index()
        attribution['contribution_rank'] = attribution['total_contribution_pct'].rank(ascending=False)
        
        attribution.to_csv(self.output_dir / "performance_attribution.csv", index=False)
        print(f"Performance attribution saved to {self.output_dir / 'performance_attribution.csv'}")
    
    def _interpret_sharpe_ratio(self, sharpe: float) -> str:
        """Interpret Sharpe ratio value."""
        if sharpe > 2:
            return "Excellent risk-adjusted returns"
        elif sharpe > 1:
            return "Good risk-adjusted returns"
        elif sharpe > 0.5:
            return "Acceptable risk-adjusted returns"
        elif sharpe > 0:
            return "Poor risk-adjusted returns"
        else:
            return "Negative risk-adjusted returns"
    
    def _interpret_sortino_ratio(self, sortino: float) -> str:
        """Interpret Sortino ratio value."""
        if sortino > 2:
            return "Excellent downside risk management"
        elif sortino > 1:
            return "Good downside risk management"
        elif sortino > 0.5:
            return "Acceptable downside risk management"
        elif sortino > 0:
            return "Poor downside risk management"
        else:
            return "Negative downside risk management"
    
    def _interpret_calmar_ratio(self, calmar: float) -> str:
        """Interpret Calmar ratio value."""
        if calmar > 1:
            return "Excellent drawdown-adjusted returns"
        elif calmar > 0.5:
            return "Good drawdown-adjusted returns"
        elif calmar > 0:
            return "Poor drawdown-adjusted returns"
        else:
            return "Negative drawdown-adjusted returns"
    
    def _interpret_drawdown(self, drawdown: float) -> str:
        """Interpret maximum drawdown."""
        if drawdown < 5:
            return "Very low risk"
        elif drawdown < 10:
            return "Low risk"
        elif drawdown < 20:
            return "Moderate risk"
        elif drawdown < 30:
            return "High risk"
        else:
            return "Very high risk"
    
    def _interpret_volatility(self, volatility: float) -> str:
        """Interpret volatility."""
        if volatility < 10:
            return "Very low volatility"
        elif volatility < 20:
            return "Low volatility"
        elif volatility < 30:
            return "Moderate volatility"
        elif volatility < 50:
            return "High volatility"
        else:
            return "Very high volatility"


def generate_enhanced_reports(db_path: Path, output_dir: Path, risk_free_rate: float = 0.02):
    """
    Generate enhanced performance reports.
    
    Args:
        db_path: Path to SQLite database
        output_dir: Directory to save reports
        risk_free_rate: Annual risk-free rate for risk-adjusted metrics
    """
    reporter = EnhancedReporter(db_path, output_dir)
    return reporter.generate_comprehensive_report(risk_free_rate)


if __name__ == "__main__":
    db_path = Path(__file__).parent.parent.parent / "logs" / "tracker.db"
    output_dir = Path(__file__).parent.parent.parent / "logs" / "enhanced_reports"
    generate_enhanced_reports(db_path, output_dir)
