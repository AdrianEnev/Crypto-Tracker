"""
Performance Metrics Tracking Module

Tracks comprehensive performance metrics for the trading system including:
- Trade performance (win rate, P&L, trades per hour)
- Portfolio performance (returns, drawdowns, equity curves)
- System health metrics (uptime, errors, restarts)
- Risk metrics (exposure, volatility, risk-adjusted returns)
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .logger import log_event


class PerformanceMetricsTracker:
    """Tracks comprehensive performance metrics for the trading system."""
    
    def __init__(self, config_manager, export_directory: str = "./reports"):
        self.config_manager = config_manager
        self.export_directory = Path(export_directory)
        self.export_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize metrics storage
        self.metrics = {
            "system_start_time": datetime.now(timezone.utc).isoformat(),
            "trade_metrics": {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "total_pnl": 0.0,
                "total_pnl_pct": 0.0,
                "win_rate_pct": 0.0,
                "avg_win_pct": 0.0,
                "avg_loss_pct": 0.0,
                "profit_factor": 0.0,
                "trades_per_hour": 0.0,
                "last_trade_time": None
            },
            "portfolio_metrics": {
                "initial_value": 0.0,
                "current_value": 0.0,
                "peak_value": 0.0,
                "total_return_pct": 0.0,
                "max_drawdown_pct": 0.0,
                "sharpe_ratio": 0.0,
                "sortino_ratio": 0.0,
                "calmar_ratio": 0.0,
                "last_update_time": None
            },
            "system_health": {
                "uptime_hours": 0.0,
                "restart_count": 0,
                "error_count": 0,
                "last_error_time": None,
                "last_heartbeat_time": None,
                "cache_hit_rate": 0.0,
                "api_response_time_avg": 0.0
            },
            "risk_metrics": {
                "max_exposure_pct": 0.0,
                "current_exposure_pct": 0.0,
                "volatility_pct": 0.0,
                "var_95_pct": 0.0,
                "max_position_size_pct": 0.0,
                "correlation_risk": 0.0
            }
        }
        
        # Load configuration
        self._load_config()
        
        # Initialize tracking
        self._last_export_time = time.time()
        
    def _load_config(self):
        """Load performance metrics configuration."""
        try:
            config_data = self.config_manager.load_full_config()
            metrics_config = config_data.get("performance_metrics", {})
            
            self.enabled = metrics_config.get("enabled", True)
            self.track_trades_per_hour = metrics_config.get("track_trades_per_hour", True)
            self.track_portfolio_performance = metrics_config.get("track_portfolio_performance", True)
            self.track_system_health = metrics_config.get("track_system_health", True)
            self.export_metrics = metrics_config.get("export_metrics", True)
            self.export_interval_minutes = metrics_config.get("metrics_export_interval_minutes", 60)
            
            if self.enabled:
                log_event("performance_metrics_initialized", {
                    "enabled": True,
                    "export_interval": self.export_interval_minutes
                })
            else:
                log_event("performance_metrics_disabled", {"enabled": False})
                
        except Exception as ex:
            log_event("performance_metrics_config_error", {"error": str(ex)})
            self.enabled = False
    
    def track_trade(self, trade_data: Dict[str, Any]):
        """Track a completed trade."""
        if not self.enabled:
            return
            
        try:
            trade_metrics = self.metrics["trade_metrics"]
            
            # Update trade counts
            trade_metrics["total_trades"] += 1
            
            # Track P&L
            pnl = trade_data.get("pnl", 0.0)
            pnl_pct = trade_data.get("pnl_pct", 0.0)
            
            trade_metrics["total_pnl"] += pnl
            trade_metrics["total_pnl_pct"] += pnl_pct
            
            if pnl > 0:
                trade_metrics["winning_trades"] += 1
            elif pnl < 0:
                trade_metrics["losing_trades"] += 1
            
            # Update win rate
            if trade_metrics["total_trades"] > 0:
                trade_metrics["win_rate_pct"] = (
                    trade_metrics["winning_trades"] / trade_metrics["total_trades"] * 100
                )
            
            # Update trades per hour
            if self.track_trades_per_hour:
                uptime_hours = self._get_uptime_hours()
                if uptime_hours > 0:
                    trade_metrics["trades_per_hour"] = trade_metrics["total_trades"] / uptime_hours
            
            # Update last trade time
            trade_metrics["last_trade_time"] = datetime.now(timezone.utc).isoformat()
            
            # Calculate profit factor
            self._update_profit_factor()
            
            log_event("trade_tracked", {
                "total_trades": trade_metrics["total_trades"],
                "pnl": pnl,
                "win_rate": trade_metrics["win_rate_pct"]
            })
            
        except Exception as ex:
            log_event("trade_tracking_error", {"error": str(ex)})
    
    def track_portfolio_performance(self, portfolio_data: Dict[str, Any]):
        """Track portfolio performance metrics."""
        if not self.enabled or not self.track_portfolio_performance:
            return
            
        try:
            portfolio_metrics = self.metrics["portfolio_metrics"]
            
            # Update portfolio values
            current_value = portfolio_data.get("current_value", 0.0)
            peak_value = portfolio_data.get("peak_value", current_value)
            initial_value = portfolio_data.get("initial_value", current_value)
            
            portfolio_metrics["current_value"] = current_value
            portfolio_metrics["peak_value"] = max(portfolio_metrics["peak_value"], peak_value)
            
            if initial_value > 0:
                portfolio_metrics["total_return_pct"] = (
                    (current_value - initial_value) / initial_value * 100
                )
            
            # Calculate drawdown
            if portfolio_metrics["peak_value"] > 0:
                portfolio_metrics["max_drawdown_pct"] = (
                    (portfolio_metrics["peak_value"] - current_value) / portfolio_metrics["peak_value"] * 100
                )
            
            # Update last update time
            portfolio_metrics["last_update_time"] = datetime.now(timezone.utc).isoformat()
            
            # Calculate risk-adjusted returns
            self._calculate_risk_adjusted_returns()
            
        except Exception as ex:
            log_event("portfolio_tracking_error", {"error": str(ex)})
    
    def track_system_health(self, health_data: Dict[str, Any]):
        """Track system health metrics."""
        if not self.enabled or not self.track_system_health:
            return
            
        try:
            health_metrics = self.metrics["system_health"]
            
            # Update uptime
            health_metrics["uptime_hours"] = self._get_uptime_hours()
            
            # Update restart count
            health_metrics["restart_count"] = health_data.get("restart_count", 0)
            
            # Update error count
            if health_data.get("error_occurred", False):
                health_metrics["error_count"] += 1
                health_metrics["last_error_time"] = datetime.now(timezone.utc).isoformat()
            
            # Update heartbeat
            if health_data.get("heartbeat", False):
                health_metrics["last_heartbeat_time"] = datetime.now(timezone.utc).isoformat()
            
            # Update cache performance
            cache_stats = health_data.get("cache_stats", {})
            if cache_stats:
                health_metrics["cache_hit_rate"] = cache_stats.get("hit_rate_pct", 0.0)
            
            # Update API performance
            api_response_time = health_data.get("api_response_time")
            if api_response_time:
                # Simple moving average of API response times
                current_avg = health_metrics["api_response_time_avg"]
                health_metrics["api_response_time_avg"] = (
                    (current_avg * 0.9) + (api_response_time * 0.1)
                )
            
        except Exception as ex:
            log_event("system_health_tracking_error", {"error": str(ex)})
    
    def track_risk_metrics(self, risk_data: Dict[str, Any]):
        """Track risk metrics."""
        if not self.enabled:
            return
            
        try:
            risk_metrics = self.metrics["risk_metrics"]
            
            # Update exposure metrics
            risk_metrics["max_exposure_pct"] = risk_data.get("max_exposure_pct", 0.0)
            risk_metrics["current_exposure_pct"] = risk_data.get("current_exposure_pct", 0.0)
            
            # Update volatility
            risk_metrics["volatility_pct"] = risk_data.get("volatility_pct", 0.0)
            
            # Update VaR
            risk_metrics["var_95_pct"] = risk_data.get("var_95_pct", 0.0)
            
            # Update position sizing
            risk_metrics["max_position_size_pct"] = risk_data.get("max_position_size_pct", 0.0)
            
            # Update correlation risk
            risk_metrics["correlation_risk"] = risk_data.get("correlation_risk", 0.0)
            
        except Exception as ex:
            log_event("risk_metrics_tracking_error", {"error": str(ex)})
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        try:
            # Update calculated metrics
            self._update_calculated_metrics()
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "uptime_hours": self._get_uptime_hours(),
                "trade_metrics": self.metrics["trade_metrics"].copy(),
                "portfolio_metrics": self.metrics["portfolio_metrics"].copy(),
                "system_health": self.metrics["system_health"].copy(),
                "risk_metrics": self.metrics["risk_metrics"].copy()
            }
            
        except Exception as ex:
            log_event("performance_summary_error", {"error": str(ex)})
            return {}
    
    def export_metrics(self) -> bool:
        """Export metrics to file."""
        if not self.enabled or not self.export_metrics_enabled:
            return False
            
        try:
            # Check if it's time to export
            current_time = time.time()
            if current_time - self._last_export_time < (self.export_interval_minutes * 60):
                return False
            
            # Generate filename with timestamp
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"performance_metrics_{timestamp}.json"
            filepath = self.export_directory / filename
            
            # Export metrics
            summary = self.get_performance_summary()
            with open(filepath, 'w') as f:
                json.dump(summary, f, indent=2)
            
            self._last_export_time = current_time
            
            log_event("metrics_exported", {
                "filename": filename,
                "filepath": str(filepath)
            })
            
            return True
            
        except Exception as ex:
            log_event("metrics_export_error", {"error": str(ex)})
            return False
    
    def _get_uptime_hours(self) -> float:
        """Calculate system uptime in hours."""
        try:
            start_time = datetime.fromisoformat(self.metrics["system_start_time"])
            current_time = datetime.now(timezone.utc)
            uptime_seconds = (current_time - start_time).total_seconds()
            return uptime_seconds / 3600.0
        except Exception:
            return 0.0
    
    def _update_profit_factor(self):
        """Update profit factor calculation."""
        try:
            trade_metrics = self.metrics["trade_metrics"]
            
            if trade_metrics["losing_trades"] > 0:
                avg_loss = abs(trade_metrics["total_pnl"]) / trade_metrics["losing_trades"]
                avg_win = trade_metrics["total_pnl"] / max(1, trade_metrics["winning_trades"])
                trade_metrics["profit_factor"] = avg_win / avg_loss if avg_loss > 0 else 0.0
            else:
                trade_metrics["profit_factor"] = float('inf') if trade_metrics["winning_trades"] > 0 else 0.0
                
        except Exception:
            pass
    
    def _calculate_risk_adjusted_returns(self):
        """Calculate risk-adjusted return metrics."""
        try:
            portfolio_metrics = self.metrics["portfolio_metrics"]
            risk_metrics = self.metrics["risk_metrics"]
            
            # Simple Sharpe ratio calculation (would need risk-free rate in production)
            volatility = risk_metrics["volatility_pct"] / 100.0
            if volatility > 0:
                portfolio_metrics["sharpe_ratio"] = portfolio_metrics["total_return_pct"] / (volatility * 100)
            
            # Sortino ratio (downside deviation)
            if risk_metrics["var_95_pct"] > 0:
                portfolio_metrics["sortino_ratio"] = portfolio_metrics["total_return_pct"] / risk_metrics["var_95_pct"]
            
            # Calmar ratio (return / max drawdown)
            if portfolio_metrics["max_drawdown_pct"] > 0:
                portfolio_metrics["calmar_ratio"] = portfolio_metrics["total_return_pct"] / portfolio_metrics["max_drawdown_pct"]
                
        except Exception:
            pass
    
    def _update_calculated_metrics(self):
        """Update all calculated metrics."""
        try:
            self._update_profit_factor()
            self._calculate_risk_adjusted_returns()
            
            # Update uptime
            self.metrics["system_health"]["uptime_hours"] = self._get_uptime_hours()
            
        except Exception:
            pass
