"""
Enhanced drawdown tracking and management.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path

from .models import DrawdownMetrics, RiskViolation, RiskViolationType, RiskLevel


@dataclass
class EquitySnapshot:
    """Equity snapshot for drawdown tracking."""
    timestamp: datetime
    equity: float
    period: str  # 'daily', 'weekly', 'monthly'


class DrawdownManager:
    """Manages drawdown tracking and enforces drawdown limits."""
    
    def __init__(self, config_manager, portfolio_manager):
        self.config_manager = config_manager
        self.portfolio_manager = portfolio_manager
        
        # Equity tracking
        self.equity_peak: Optional[float] = None
        self.daily_start_equity: Optional[float] = None
        self.weekly_start_equity: Optional[float] = None
        self.monthly_start_equity: Optional[float] = None
        
        # Timestamps
        self.last_equity_day: Optional[str] = None
        self.last_equity_week: Optional[str] = None
        self.last_equity_month: Optional[str] = None
        
        # Historical snapshots
        self.equity_history: List[EquitySnapshot] = []
        self.max_history_days = 30
        
        # Persistence
        self.state_path = self._get_state_path()
        self._load_state()
    
    def _get_state_path(self) -> Path:
        """Get path for persisting drawdown state."""
        try:
            config_path = Path(self.config_manager.config_path)
            return config_path.parent.parent / 'logs' / 'drawdown_state.json'
        except Exception:
            return Path('logs/drawdown_state.json')
    
    def _load_state(self):
        """Load drawdown tracking state from disk."""
        try:
            if self.state_path.exists():
                with self.state_path.open('r') as f:
                    data = json.load(f)
                
                self.equity_peak = data.get('equity_peak')
                self.daily_start_equity = data.get('daily_start_equity')
                self.weekly_start_equity = data.get('weekly_start_equity')
                self.monthly_start_equity = data.get('monthly_start_equity')
                self.last_equity_day = data.get('last_equity_day')
                self.last_equity_week = data.get('last_equity_week')
                self.last_equity_month = data.get('last_equity_month')
                
                # Load equity history
                history_data = data.get('equity_history', [])
                self.equity_history = []
                for item in history_data:
                    try:
                        snapshot = EquitySnapshot(
                            timestamp=datetime.fromisoformat(item['timestamp']),
                            equity=float(item['equity']),
                            period=item['period']
                        )
                        self.equity_history.append(snapshot)
                    except Exception:
                        continue
                        
        except Exception:
            # Initialize with defaults
            self.equity_peak = None
            self.daily_start_equity = None
            self.weekly_start_equity = None
            self.monthly_start_equity = None
            self.last_equity_day = None
            self.last_equity_week = None
            self.last_equity_month = None
            self.equity_history = []
    
    def _save_state(self):
        """Save drawdown tracking state to disk."""
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare data for serialization
            history_data = []
            for snapshot in self.equity_history[-self.max_history_days:]:  # Keep only recent history
                history_data.append({
                    'timestamp': snapshot.timestamp.isoformat(),
                    'equity': snapshot.equity,
                    'period': snapshot.period
                })
            
            data = {
                'equity_peak': self.equity_peak,
                'daily_start_equity': self.daily_start_equity,
                'weekly_start_equity': self.weekly_start_equity,
                'monthly_start_equity': self.monthly_start_equity,
                'last_equity_day': self.last_equity_day,
                'last_equity_week': self.last_equity_week,
                'last_equity_month': self.last_equity_month,
                'equity_history': history_data
            }
            
            with self.state_path.open('w') as f:
                json.dump(data, f, indent=2)
                
        except Exception:
            pass  # Fail silently
    
    def update_equity_tracking(self, current_equity: float):
        """Update equity tracking and calculate drawdowns."""
        try:
            now = datetime.now(timezone.utc)
            today = now.strftime('%Y-%m-%d')
            week_start = (now - timedelta(days=now.weekday())).strftime('%Y-%m-%d')
            month_start = now.strftime('%Y-%m')
            
            # Update equity peak
            if self.equity_peak is None or current_equity > self.equity_peak:
                self.equity_peak = current_equity
            
            # Update daily baseline
            if self.last_equity_day != today:
                self.daily_start_equity = current_equity
                self.last_equity_day = today
            
            # Update weekly baseline
            if self.last_equity_week != week_start:
                self.weekly_start_equity = current_equity
                self.last_equity_week = week_start
            
            # Update monthly baseline
            if self.last_equity_month != month_start:
                self.monthly_start_equity = current_equity
                self.last_equity_month = month_start
            
            # Add to equity history
            self._add_equity_snapshot(current_equity, now)
            
            # Save state
            self._save_state()
            
        except Exception:
            pass
    
    def _add_equity_snapshot(self, equity: float, timestamp: datetime):
        """Add equity snapshot to history."""
        try:
            # Add daily snapshot
            daily_snapshot = EquitySnapshot(
                timestamp=timestamp,
                equity=equity,
                period='daily'
            )
            self.equity_history.append(daily_snapshot)
            
            # Keep only recent history
            cutoff_time = timestamp - timedelta(days=self.max_history_days)
            self.equity_history = [
                snapshot for snapshot in self.equity_history
                if snapshot.timestamp >= cutoff_time
            ]
            
        except Exception:
            pass
    
    def calculate_drawdown_metrics(self) -> DrawdownMetrics:
        """Calculate comprehensive drawdown metrics."""
        try:
            metrics = DrawdownMetrics()
            
            if self.equity_peak is None or self.equity_peak <= 0:
                return metrics
            
            # Get current equity (from latest snapshot)
            current_equity = 0.0
            if self.equity_history:
                current_equity = self.equity_history[-1].equity
            
            # Calculate current drawdown from peak
            metrics.current_drawdown_pct = max(0.0, (self.equity_peak - current_equity) / self.equity_peak * 100.0)
            metrics.equity_peak = self.equity_peak
            
            # Calculate daily drawdown
            if self.daily_start_equity and self.daily_start_equity > 0:
                daily_change = (current_equity - self.daily_start_equity) / self.daily_start_equity
                metrics.daily_drawdown_pct = max(0.0, -daily_change * 100.0) if daily_change < 0 else 0.0
                metrics.daily_start_equity = self.daily_start_equity
            
            # Calculate weekly drawdown
            if self.weekly_start_equity and self.weekly_start_equity > 0:
                weekly_change = (current_equity - self.weekly_start_equity) / self.weekly_start_equity
                metrics.weekly_drawdown_pct = max(0.0, -weekly_change * 100.0) if weekly_change < 0 else 0.0
                metrics.weekly_start_equity = self.weekly_start_equity
            
            # Calculate maximum drawdown from history
            metrics.max_drawdown_pct = self._calculate_max_drawdown_from_history()
            
            return metrics
            
        except Exception:
            return DrawdownMetrics()
    
    def _calculate_max_drawdown_from_history(self) -> float:
        """Calculate maximum drawdown from equity history."""
        try:
            if len(self.equity_history) < 2:
                return 0.0
            
            max_dd = 0.0
            peak = self.equity_history[0].equity
            
            for snapshot in self.equity_history[1:]:
                if snapshot.equity > peak:
                    peak = snapshot.equity
                else:
                    dd = (peak - snapshot.equity) / peak * 100.0 if peak > 0 else 0.0
                    max_dd = max(max_dd, dd)
            
            return max_dd
            
        except Exception:
            return 0.0
    
    def check_drawdown_limits(self, metrics: DrawdownMetrics, limits: Dict[str, float]) -> List[RiskViolation]:
        """Check drawdown against limits and return violations."""
        violations = []
        timestamp = datetime.now(timezone.utc)
        
        try:
            # Check daily drawdown limit
            daily_max_drawdown_pct = limits.get('daily_max_drawdown_pct', 5.0)
            if metrics.daily_drawdown_pct > daily_max_drawdown_pct:
                violation = RiskViolation(
                    violation_type=RiskViolationType.DAILY_DRAWDOWN_EXCEEDED,
                    severity=RiskLevel.HIGH,
                    message=f"Daily drawdown {metrics.daily_drawdown_pct:.2f}% exceeds limit {daily_max_drawdown_pct}%",
                    current_value=metrics.daily_drawdown_pct,
                    limit_value=daily_max_drawdown_pct,
                    timestamp=timestamp
                )
                violations.append(violation)
            
            # Check weekly drawdown limit
            weekly_max_drawdown_pct = limits.get('weekly_max_drawdown_pct', 12.0)
            if metrics.weekly_drawdown_pct > weekly_max_drawdown_pct:
                violation = RiskViolation(
                    violation_type=RiskViolationType.WEEKLY_DRAWDOWN_EXCEEDED,
                    severity=RiskLevel.HIGH,
                    message=f"Weekly drawdown {metrics.weekly_drawdown_pct:.2f}% exceeds limit {weekly_max_drawdown_pct}%",
                    current_value=metrics.weekly_drawdown_pct,
                    limit_value=weekly_max_drawdown_pct,
                    timestamp=timestamp
                )
                violations.append(violation)
            
            # Check maximum drawdown limit
            max_drawdown_pct = limits.get('max_drawdown_pct', 20.0)
            if metrics.max_drawdown_pct > max_drawdown_pct:
                violation = RiskViolation(
                    violation_type=RiskViolationType.MAX_DRAWDOWN_EXCEEDED,
                    severity=RiskLevel.CRITICAL,
                    message=f"Maximum drawdown {metrics.max_drawdown_pct:.2f}% exceeds limit {max_drawdown_pct}%",
                    current_value=metrics.max_drawdown_pct,
                    limit_value=max_drawdown_pct,
                    timestamp=timestamp
                )
                violations.append(violation)
            
            # Check kill switch drawdown limit
            kill_switch_drawdown_pct = limits.get('kill_switch_drawdown_pct', 15.0)
            if metrics.current_drawdown_pct > kill_switch_drawdown_pct:
                violation = RiskViolation(
                    violation_type=RiskViolationType.KILL_SWITCH_ACTIVATED,
                    severity=RiskLevel.CRITICAL,
                    message=f"Kill switch triggered: drawdown {metrics.current_drawdown_pct:.2f}% exceeds limit {kill_switch_drawdown_pct}%",
                    current_value=metrics.current_drawdown_pct,
                    limit_value=kill_switch_drawdown_pct,
                    timestamp=timestamp
                )
                violations.append(violation)
                
        except Exception:
            pass
        
        return violations
    
    def get_drawdown_warnings(self, metrics: DrawdownMetrics, warning_thresholds: Dict[str, float]) -> List[str]:
        """Get drawdown warnings based on warning thresholds."""
        warnings = []
        
        try:
            drawdown_warning_pct = warning_thresholds.get('drawdown_warning_pct', 10.0)
            
            # Current drawdown warning
            if metrics.current_drawdown_pct > drawdown_warning_pct:
                warnings.append(f"Current drawdown {metrics.current_drawdown_pct:.2f}% approaching limit")
            
            # Daily drawdown warning
            if metrics.daily_drawdown_pct > drawdown_warning_pct * 0.5:  # 50% of warning threshold
                warnings.append(f"Daily drawdown {metrics.daily_drawdown_pct:.2f}% approaching limit")
            
            # Weekly drawdown warning
            if metrics.weekly_drawdown_pct > drawdown_warning_pct * 0.8:  # 80% of warning threshold
                warnings.append(f"Weekly drawdown {metrics.weekly_drawdown_pct:.2f}% approaching limit")
                
        except Exception:
            pass
        
        return warnings
    
    def reset_drawdown_tracking(self):
        """Reset drawdown tracking (for testing or manual reset)."""
        try:
            self.equity_peak = None
            self.daily_start_equity = None
            self.weekly_start_equity = None
            self.monthly_start_equity = None
            self.last_equity_day = None
            self.last_equity_week = None
            self.last_equity_month = None
            self.equity_history = []
            self._save_state()
        except Exception:
            pass
