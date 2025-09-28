"""
Risk management data models and enums.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone


class RiskViolationType(Enum):
    """Types of risk violations."""

    PORTFOLIO_EXPOSURE_EXCEEDED = "portfolio_exposure_exceeded"
    PER_COIN_EXPOSURE_EXCEEDED = "per_coin_exposure_exceeded"
    MAX_POSITIONS_EXCEEDED = "max_positions_exceeded"
    DAILY_DRAWDOWN_EXCEEDED = "daily_drawdown_exceeded"
    WEEKLY_DRAWDOWN_EXCEEDED = "weekly_drawdown_exceeded"
    MAX_DRAWDOWN_EXCEEDED = "max_drawdown_exceeded"
    LEVERAGE_EXCEEDED = "leverage_exceeded"
    MARGIN_UTILIZATION_EXCEEDED = "margin_utilization_exceeded"
    FUNDING_RATE_EXPOSURE_EXCEEDED = "funding_rate_exposure_exceeded"
    KILL_SWITCH_ACTIVATED = "kill_switch_activated"
    CORRELATION_EXPOSURE_EXCEEDED = "correlation_exposure_exceeded"


class RiskLevel(Enum):
    """Risk levels for monitoring and alerts."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskViolation:
    """Represents a risk management violation."""

    violation_type: RiskViolationType
    severity: RiskLevel
    message: str
    current_value: float
    limit_value: float
    timestamp: datetime
    symbol: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskCheckResult:
    """Result of a risk management check."""

    is_valid: bool
    violations: List[RiskViolation] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    risk_factor: float = 1.0  # Risk reduction factor (0.0-1.0)
    additional_info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PortfolioLimits:
    """Portfolio-level risk limits."""

    max_exposure_per_coin_pct: float = 15.0
    max_total_exposure_pct: float = 80.0
    max_open_positions: int = 8
    max_correlation_exposure_pct: float = 25.0


@dataclass
class PerTradeLimits:
    """Per-trade risk limits."""

    max_loss_pct_equity: float = 2.0
    max_position_size_pct: float = 10.0
    min_risk_reward_ratio: float = 1.5


@dataclass
class DrawdownLimits:
    """Drawdown risk limits."""

    daily_max_drawdown_pct: float = 5.0
    weekly_max_drawdown_pct: float = 12.0
    max_drawdown_pct: float = 20.0
    kill_switch_drawdown_pct: float = 15.0


@dataclass
class LeverageLimits:
    """Leverage and margin limits."""

    max_leverage: float = 3.0
    margin_requirement_buffer: float = 1.2
    max_margin_utilization_pct: float = 75.0


@dataclass
class FundingRateLimits:
    """Funding rate exposure limits."""

    max_funding_rate_exposure: float = 0.01
    funding_rate_cost_limit_daily: float = 0.005
    perpetual_exposure_limit_pct: float = 50.0


@dataclass
class RiskMonitoringConfig:
    """Risk monitoring configuration."""

    risk_check_interval_seconds: int = 30
    alert_thresholds: Dict[str, float] = field(
        default_factory=lambda: {
            "exposure_warning_pct": 70.0,
            "drawdown_warning_pct": 10.0,
            "leverage_warning_pct": 80.0,
        }
    )


@dataclass
class RiskLimits:
    """Complete set of risk management limits."""

    portfolio: PortfolioLimits = field(default_factory=PortfolioLimits)
    per_trade: PerTradeLimits = field(default_factory=PerTradeLimits)
    drawdown: DrawdownLimits = field(default_factory=DrawdownLimits)
    leverage: LeverageLimits = field(default_factory=LeverageLimits)
    funding_rate: FundingRateLimits = field(default_factory=FundingRateLimits)
    monitoring: RiskMonitoringConfig = field(default_factory=RiskMonitoringConfig)


@dataclass
class RiskConfig:
    """Complete risk management configuration."""

    limits: RiskLimits = field(default_factory=RiskLimits)
    enabled: bool = True
    strict_mode: bool = False  # If True, blocks all trading on any violation
    correlation_matrix: Dict[str, Dict[str, float]] = field(default_factory=dict)
    asset_categories: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class ExposureMetrics:
    """Portfolio exposure metrics."""

    total_exposure_usd: float = 0.0
    total_exposure_pct: float = 0.0
    per_coin_exposure: Dict[str, float] = field(default_factory=dict)
    per_coin_exposure_pct: Dict[str, float] = field(default_factory=dict)
    correlation_exposure: Dict[str, float] = field(default_factory=dict)
    leverage_utilization: float = 0.0
    margin_utilization: float = 0.0
    funding_rate_cost_daily: float = 0.0


@dataclass
class DrawdownMetrics:
    """Drawdown tracking metrics."""

    current_drawdown_pct: float = 0.0
    daily_drawdown_pct: float = 0.0
    weekly_drawdown_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    equity_peak: float = 0.0
    daily_start_equity: float = 0.0
    weekly_start_equity: float = 0.0


@dataclass
class RiskStatus:
    """Current risk management status."""

    overall_risk_level: RiskLevel = RiskLevel.LOW
    active_violations: List[RiskViolation] = field(default_factory=list)
    kill_switch_active: bool = False
    last_risk_check: Optional[datetime] = None
    exposure_metrics: ExposureMetrics = field(default_factory=ExposureMetrics)
    drawdown_metrics: DrawdownMetrics = field(default_factory=DrawdownMetrics)
