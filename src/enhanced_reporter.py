"""
Enhanced Reporting Module

Provides comprehensive reporting capabilities including:
- Performance reports with advanced analytics
- Trade analysis and P&L reports
- Risk metrics and drawdown analysis
- System health and monitoring reports
- CSV export functionality
- Legacy compatibility
"""

import csv
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

from .logger import log_event


class EnhancedReporter:
    """Enhanced reporting system with comprehensive analytics."""
    
    def __init__(self, config_manager, export_directory: str = "./reports"):
        self.config_manager = config_manager
        self.export_directory = Path(export_directory)
        self.export_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize configuration
        self._load_config()
        
        # Initialize report templates
        self._init_report_templates()
        
    def _load_config(self):
        """Load reporting configuration."""
        try:
            config_data = self.config_manager.load_full_config()
            reporting_config = config_data.get("reporting", {})
            
            self.enabled = reporting_config.get("enabled", True)
            self.enhanced_reports = reporting_config.get("enhanced_reports", True)
            self.legacy_compatibility = reporting_config.get("legacy_compatibility", True)
            self.csv_export = reporting_config.get("csv_export", True)
            self.report_interval_hours = reporting_config.get("report_interval_hours", 24)
            self.export_directory = Path(reporting_config.get("export_directory", "./reports"))
            
            if self.enabled:
                log_event("enhanced_reporter_initialized", {
                    "enabled": True,
                    "enhanced_reports": self.enhanced_reports,
                    "csv_export": self.csv_export,
                    "export_directory": str(self.export_directory)
                })
            else:
                log_event("enhanced_reporter_disabled", {"enabled": False})
                
        except Exception as ex:
            log_event("enhanced_reporter_config_error", {"error": str(ex)})
            self.enabled = False
    
    def _init_report_templates(self):
        """Initialize report templates."""
        self.report_templates = {
            "performance": {
                "title": "Performance Report",
                "sections": ["summary", "trades", "portfolio", "risk", "system"]
            },
            "trades": {
                "title": "Trade Analysis Report", 
                "sections": ["overview", "win_loss", "timing", "correlation"]
            },
            "risk": {
                "title": "Risk Analysis Report",
                "sections": ["exposure", "drawdown", "volatility", "var"]
            },
            "system": {
                "title": "System Health Report",
                "sections": ["uptime", "errors", "performance", "optimization"]
            }
        }
    
    def generate_enhanced_reports(self, db_path: Path, output_dir: Optional[Path] = None) -> bool:
        """Generate comprehensive enhanced reports."""
        if not self.enabled:
            return False
            
        try:
            if output_dir is None:
                output_dir = self.export_directory / "enhanced"
            
            output_dir.mkdir(parents=True, exist_ok=True)
            
            log_event("enhanced_reports_generation_started", {
                "db_path": str(db_path),
                "output_dir": str(output_dir)
            })
            
            # Generate all report types
            reports_generated = []
            
            if self.enhanced_reports:
                reports_generated.extend([
                    self._generate_performance_report(db_path, output_dir),
                    self._generate_trade_analysis_report(db_path, output_dir),
                    self._generate_risk_analysis_report(db_path, output_dir),
                    self._generate_system_health_report(db_path, output_dir)
                ])
            
            if self.legacy_compatibility:
                self._generate_legacy_reports(db_path, output_dir)
            
            if self.csv_export:
                self._export_csv_data(db_path, output_dir)
            
            # Generate summary report
            self._generate_summary_report(output_dir, reports_generated)
            
            log_event("enhanced_reports_generation_completed", {
                "reports_generated": len(reports_generated),
                "output_dir": str(output_dir)
            })
            
            return True
            
        except Exception as ex:
            log_event("enhanced_reports_generation_error", {"error": str(ex)})
            return False
    
    def _generate_performance_report(self, db_path: Path, output_dir: Path) -> bool:
        """Generate comprehensive performance report."""
        try:
            conn = sqlite3.connect(db_path)
            
            # Get trade data
            trades_df = pd.read_sql_query("SELECT * FROM trades", conn) if PANDAS_AVAILABLE else None
            
            if trades_df is not None and not trades_df.empty:
                # Calculate performance metrics
                total_trades = len(trades_df)
                winning_trades = len(trades_df[trades_df['pnl_pct'] > 0])
                losing_trades = len(trades_df[trades_df['pnl_pct'] < 0])
                win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
                
                total_pnl = trades_df['pnl_pct'].sum()
                avg_win = trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].mean() if winning_trades > 0 else 0
                avg_loss = trades_df[trades_df['pnl_pct'] < 0]['pnl_pct'].mean() if losing_trades > 0 else 0
                
                # Calculate additional metrics
                profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
                
                # Generate report data
                report_data = {
                    "report_type": "performance",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "summary": {
                        "total_trades": int(total_trades),
                        "winning_trades": int(winning_trades),
                        "losing_trades": int(losing_trades),
                        "win_rate_pct": round(win_rate, 2),
                        "total_pnl_pct": round(total_pnl, 2),
                        "avg_win_pct": round(avg_win, 2),
                        "avg_loss_pct": round(avg_loss, 2),
                        "profit_factor": round(profit_factor, 2)
                    },
                    "detailed_metrics": {
                        "best_trade_pct": round(trades_df['pnl_pct'].max(), 2),
                        "worst_trade_pct": round(trades_df['pnl_pct'].min(), 2),
                        "trades_per_day": round(total_trades / max(1, (trades_df['timestamp'].max() - trades_df['timestamp'].min()) / 86400000), 2),
                        "consecutive_wins": self._calculate_consecutive_wins(trades_df),
                        "consecutive_losses": self._calculate_consecutive_losses(trades_df)
                    }
                }
                
                # Save report
                report_file = output_dir / "performance_report.json"
                with open(report_file, 'w') as f:
                    json.dump(report_data, f, indent=2)
                
                conn.close()
                return True
            else:
                conn.close()
                return False
                
        except Exception as ex:
            log_event("performance_report_error", {"error": str(ex)})
            return False
    
    def _generate_trade_analysis_report(self, db_path: Path, output_dir: Path) -> bool:
        """Generate detailed trade analysis report."""
        try:
            conn = sqlite3.connect(db_path)
            
            if PANDAS_AVAILABLE:
                trades_df = pd.read_sql_query("SELECT * FROM trades", conn)
                
                if not trades_df.empty:
                    # Analyze trade patterns
                    report_data = {
                        "report_type": "trade_analysis",
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                        "trade_patterns": {
                            "hourly_distribution": self._analyze_hourly_distribution(trades_df),
                            "daily_distribution": self._analyze_daily_distribution(trades_df),
                            "symbol_performance": self._analyze_symbol_performance(trades_df),
                            "trade_duration_analysis": self._analyze_trade_duration(trades_df)
                        },
                        "correlation_analysis": self._analyze_trade_correlations(trades_df)
                    }
                    
                    # Save report
                    report_file = output_dir / "trade_analysis_report.json"
                    with open(report_file, 'w') as f:
                        json.dump(report_data, f, indent=2)
                    
                    conn.close()
                    return True
            
            conn.close()
            return False
            
        except Exception as ex:
            log_event("trade_analysis_report_error", {"error": str(ex)})
            return False
    
    def _generate_risk_analysis_report(self, db_path: Path, output_dir: Path) -> bool:
        """Generate risk analysis report."""
        try:
            conn = sqlite3.connect(db_path)
            
            if PANDAS_AVAILABLE:
                trades_df = pd.read_sql_query("SELECT * FROM trades", conn)
                
                if not trades_df.empty:
                    # Calculate risk metrics
                    returns = trades_df['pnl_pct'].values
                    
                    report_data = {
                        "report_type": "risk_analysis",
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                        "risk_metrics": {
                            "volatility": round(returns.std(), 4),
                            "sharpe_ratio": self._calculate_sharpe_ratio(returns),
                            "max_drawdown": self._calculate_max_drawdown(returns),
                            "var_95": self._calculate_var(returns, 0.95),
                            "var_99": self._calculate_var(returns, 0.99),
                            "skewness": self._calculate_skewness(returns),
                            "kurtosis": self._calculate_kurtosis(returns)
                        },
                        "exposure_analysis": self._analyze_exposure(trades_df)
                    }
                    
                    # Save report
                    report_file = output_dir / "risk_analysis_report.json"
                    with open(report_file, 'w') as f:
                        json.dump(report_data, f, indent=2)
                    
                    conn.close()
                    return True
            
            conn.close()
            return False
            
        except Exception as ex:
            log_event("risk_analysis_report_error", {"error": str(ex)})
            return False
    
    def _generate_system_health_report(self, db_path: Path, output_dir: Path) -> bool:
        """Generate system health report."""
        try:
            # This would typically read from system logs and metrics
            # For now, we'll create a basic structure
            
            report_data = {
                "report_type": "system_health",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "system_metrics": {
                    "uptime_hours": 0,  # Would be calculated from logs
                    "error_count": 0,   # Would be read from logs
                    "restart_count": 0,  # Would be read from logs
                    "cache_hit_rate": 0, # Would be read from cache stats
                    "api_response_time": 0 # Would be read from API logs
                },
                "performance_metrics": {
                    "trades_per_hour": 0,
                    "system_load": 0,
                    "memory_usage": 0,
                    "cpu_usage": 0
                }
            }
            
            # Save report
            report_file = output_dir / "system_health_report.json"
            with open(report_file, 'w') as f:
                json.dump(report_data, f, indent=2)
            
            return True
            
        except Exception as ex:
            log_event("system_health_report_error", {"error": str(ex)})
            return False
    
    def _generate_legacy_reports(self, db_path: Path, output_dir: Path):
        """Generate legacy compatibility reports."""
        try:
            conn = sqlite3.connect(db_path)
            
            # Generate P&L Report (legacy format)
            trades_df = pd.read_sql_query("SELECT * FROM trades", conn) if PANDAS_AVAILABLE else None
            
            if trades_df is not None and not trades_df.empty:
                pnl_report = (
                    trades_df.groupby("symbol")
                    .agg(
                        total_trades=("symbol", "size"),
                        win_rate=("pnl_pct", lambda x: (x > 0).mean()),
                        avg_pnl_pct=("pnl_pct", "mean"),
                        total_pnl_pct=("pnl_pct", "sum"),
                    )
                    .reset_index()
                )
                
                # Save legacy report
                legacy_file = output_dir / "legacy_pnl_report.csv"
                pnl_report.to_csv(legacy_file, index=False)
            
            conn.close()
            
        except Exception as ex:
            log_event("legacy_reports_error", {"error": str(ex)})
    
    def _export_csv_data(self, db_path: Path, output_dir: Path):
        """Export raw data to CSV files."""
        try:
            conn = sqlite3.connect(db_path)
            
            # Export trades data
            trades_df = pd.read_sql_query("SELECT * FROM trades", conn) if PANDAS_AVAILABLE else None
            if trades_df is not None:
                trades_file = output_dir / "trades_export.csv"
                trades_df.to_csv(trades_file, index=False)
            
            # Export other tables if they exist
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            for table_name in tables:
                if table_name[0] != 'trades':  # Already exported
                    try:
                        df = pd.read_sql_query(f"SELECT * FROM {table_name[0]}", conn)
                        csv_file = output_dir / f"{table_name[0]}_export.csv"
                        df.to_csv(csv_file, index=False)
                    except Exception:
                        continue
            
            conn.close()
            
        except Exception as ex:
            log_event("csv_export_error", {"error": str(ex)})
    
    def _generate_summary_report(self, output_dir: Path, reports_generated: List[bool]):
        """Generate summary report of all generated reports."""
        try:
            summary_data = {
                "summary_type": "report_generation_summary",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "reports_generated": sum(reports_generated),
                "total_reports_attempted": len(reports_generated),
                "success_rate": sum(reports_generated) / len(reports_generated) * 100 if reports_generated else 0,
                "report_types": [
                    "performance_report.json",
                    "trade_analysis_report.json", 
                    "risk_analysis_report.json",
                    "system_health_report.json",
                    "legacy_pnl_report.csv",
                    "trades_export.csv"
                ]
            }
            
            summary_file = output_dir / "report_summary.json"
            with open(summary_file, 'w') as f:
                json.dump(summary_data, f, indent=2)
                
        except Exception as ex:
            log_event("summary_report_error", {"error": str(ex)})
    
    # Helper methods for calculations
    def _calculate_consecutive_wins(self, trades_df) -> int:
        """Calculate maximum consecutive wins."""
        if PANDAS_AVAILABLE and not trades_df.empty:
            wins = (trades_df['pnl_pct'] > 0).astype(int)
            max_consecutive = 0
            current_consecutive = 0
            
            for win in wins:
                if win:
                    current_consecutive += 1
                    max_consecutive = max(max_consecutive, current_consecutive)
                else:
                    current_consecutive = 0
            
            return max_consecutive
        return 0
    
    def _calculate_consecutive_losses(self, trades_df) -> int:
        """Calculate maximum consecutive losses."""
        if PANDAS_AVAILABLE and not trades_df.empty:
            losses = (trades_df['pnl_pct'] < 0).astype(int)
            max_consecutive = 0
            current_consecutive = 0
            
            for loss in losses:
                if loss:
                    current_consecutive += 1
                    max_consecutive = max(max_consecutive, current_consecutive)
                else:
                    current_consecutive = 0
            
            return max_consecutive
        return 0
    
    def _analyze_hourly_distribution(self, trades_df) -> Dict[str, int]:
        """Analyze trade distribution by hour."""
        if PANDAS_AVAILABLE and not trades_df.empty:
            trades_df['hour'] = pd.to_datetime(trades_df['timestamp'], unit='ms').dt.hour
            hourly_dist = trades_df['hour'].value_counts().to_dict()
            return {str(k): int(v) for k, v in hourly_dist.items()}
        return {}
    
    def _analyze_daily_distribution(self, trades_df) -> Dict[str, int]:
        """Analyze trade distribution by day of week."""
        if PANDAS_AVAILABLE and not trades_df.empty:
            trades_df['day_of_week'] = pd.to_datetime(trades_df['timestamp'], unit='ms').dt.day_name()
            daily_dist = trades_df['day_of_week'].value_counts().to_dict()
            return daily_dist
        return {}
    
    def _analyze_symbol_performance(self, trades_df) -> Dict[str, Dict[str, float]]:
        """Analyze performance by symbol."""
        if PANDAS_AVAILABLE and not trades_df.empty:
            symbol_perf = trades_df.groupby('symbol')['pnl_pct'].agg(['count', 'mean', 'sum']).to_dict('index')
            return {k: {kk: round(vv, 2) for kk, vv in v.items()} for k, v in symbol_perf.items()}
        return {}
    
    def _analyze_trade_duration(self, trades_df) -> Dict[str, float]:
        """Analyze trade duration patterns."""
        if PANDAS_AVAILABLE and not trades_df.empty:
            # This would require entry/exit timestamps
            return {"avg_duration_hours": 0, "min_duration_hours": 0, "max_duration_hours": 0}
        return {}
    
    def _analyze_trade_correlations(self, trades_df) -> Dict[str, float]:
        """Analyze correlations between different symbols."""
        if PANDAS_AVAILABLE and not trades_df.empty:
            # This would require multiple symbols and their returns
            return {"correlation_matrix": {}}
        return {}
    
    def _calculate_sharpe_ratio(self, returns) -> float:
        """Calculate Sharpe ratio."""
        if len(returns) > 1:
            return round(returns.mean() / returns.std(), 4) if returns.std() != 0 else 0
        return 0
    
    def _calculate_max_drawdown(self, returns) -> float:
        """Calculate maximum drawdown."""
        if len(returns) > 0:
            cumulative = (1 + returns).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            return round(drawdown.min(), 4)
        return 0
    
    def _calculate_var(self, returns, confidence_level) -> float:
        """Calculate Value at Risk."""
        if len(returns) > 0:
            return round(returns.quantile(1 - confidence_level), 4)
        return 0
    
    def _calculate_skewness(self, returns) -> float:
        """Calculate skewness."""
        if len(returns) > 2:
            mean = returns.mean()
            std = returns.std()
            if std != 0:
                return round(((returns - mean) ** 3).mean() / (std ** 3), 4)
        return 0
    
    def _calculate_kurtosis(self, returns) -> float:
        """Calculate kurtosis."""
        if len(returns) > 3:
            mean = returns.mean()
            std = returns.std()
            if std != 0:
                return round(((returns - mean) ** 4).mean() / (std ** 4), 4)
        return 0
    
    def _analyze_exposure(self, trades_df) -> Dict[str, float]:
        """Analyze exposure patterns."""
        if PANDAS_AVAILABLE and not trades_df.empty:
            # This would require position size data
            return {"max_exposure_pct": 0, "avg_exposure_pct": 0}
        return {}
