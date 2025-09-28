"""
Centralized robust risk manager for comprehensive risk management.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .drawdown_manager import DrawdownManager
from .exposure_tracker import ExposureTracker
from .kill_switch import KillSwitch
from .models import (
    DrawdownMetrics,
    ExposureMetrics,
    RiskCheckResult,
    RiskConfig,
    RiskLevel,
    RiskLimits,
    RiskStatus,
    RiskViolation,
    RiskViolationType,
)


class RobustRiskManager:
    """Centralized robust risk manager for comprehensive portfolio protection."""

    def __init__(self, config_manager, portfolio_manager, order_manager=None):
        self.config_manager = config_manager
        self.portfolio_manager = portfolio_manager
        self.order_manager = order_manager

        # Core components
        self.exposure_tracker = ExposureTracker(config_manager, portfolio_manager)
        self.drawdown_manager = DrawdownManager(config_manager, portfolio_manager)
        self.kill_switch = KillSwitch(config_manager, portfolio_manager, order_manager)

        # Configuration
        self.config = RiskConfig()
        self._load_configuration()

        # State
        self.last_risk_check: Optional[datetime] = None
        self.risk_status = RiskStatus()

        # Logger
        self.logger = logging.getLogger(__name__)

        # Event handlers
        self.violation_handlers: List[callable] = []
        self.warning_handlers: List[callable] = []

    def _load_configuration(self):
        """Load risk management configuration."""
        try:
            config_data = self.config_manager.load_full_config()
            robust_risk_config = config_data.get("robust_risk", {})

            if not robust_risk_config.get("enabled", True):
                self.config.enabled = False
                return

            # Load limits
            self.config.limits.portfolio.max_exposure_per_coin_pct = robust_risk_config.get(
                "portfolio_limits", {}
            ).get("max_exposure_per_coin_pct", 15.0)
            self.config.limits.portfolio.max_total_exposure_pct = robust_risk_config.get(
                "portfolio_limits", {}
            ).get("max_total_exposure_pct", 80.0)
            self.config.limits.portfolio.max_open_positions = robust_risk_config.get(
                "portfolio_limits", {}
            ).get("max_open_positions", 8)
            self.config.limits.portfolio.max_correlation_exposure_pct = robust_risk_config.get(
                "portfolio_limits", {}
            ).get("max_correlation_exposure_pct", 25.0)

            self.config.limits.per_trade.max_loss_pct_equity = robust_risk_config.get(
                "per_trade_limits", {}
            ).get("max_loss_pct_equity", 2.0)
            self.config.limits.per_trade.max_position_size_pct = robust_risk_config.get(
                "per_trade_limits", {}
            ).get("max_position_size_pct", 10.0)
            self.config.limits.per_trade.min_risk_reward_ratio = robust_risk_config.get(
                "per_trade_limits", {}
            ).get("min_risk_reward_ratio", 1.5)

            self.config.limits.drawdown.daily_max_drawdown_pct = robust_risk_config.get(
                "drawdown_limits", {}
            ).get("daily_max_drawdown_pct", 5.0)
            self.config.limits.drawdown.weekly_max_drawdown_pct = robust_risk_config.get(
                "drawdown_limits", {}
            ).get("weekly_max_drawdown_pct", 12.0)
            self.config.limits.drawdown.max_drawdown_pct = robust_risk_config.get(
                "drawdown_limits", {}
            ).get("max_drawdown_pct", 20.0)
            self.config.limits.drawdown.kill_switch_drawdown_pct = robust_risk_config.get(
                "drawdown_limits", {}
            ).get("kill_switch_drawdown_pct", 15.0)

            self.config.limits.leverage.max_leverage = robust_risk_config.get(
                "leverage_limits", {}
            ).get("max_leverage", 3.0)
            self.config.limits.leverage.margin_requirement_buffer = robust_risk_config.get(
                "leverage_limits", {}
            ).get("margin_requirement_buffer", 1.2)
            self.config.limits.leverage.max_margin_utilization_pct = robust_risk_config.get(
                "leverage_limits", {}
            ).get("max_margin_utilization_pct", 75.0)

            self.config.limits.funding_rate.max_funding_rate_exposure = robust_risk_config.get(
                "funding_rate_limits", {}
            ).get("max_funding_rate_exposure", 0.01)
            self.config.limits.funding_rate.funding_rate_cost_limit_daily = robust_risk_config.get(
                "funding_rate_limits", {}
            ).get("funding_rate_cost_limit_daily", 0.005)
            self.config.limits.funding_rate.perpetual_exposure_limit_pct = robust_risk_config.get(
                "funding_rate_limits", {}
            ).get("perpetual_exposure_limit_pct", 50.0)

            # Load monitoring config
            monitoring_config = robust_risk_config.get("monitoring", {})
            self.config.limits.monitoring.risk_check_interval_seconds = monitoring_config.get(
                "risk_check_interval_seconds", 30
            )
            self.config.limits.monitoring.alert_thresholds = monitoring_config.get(
                "alert_thresholds", {}
            )

            # Load additional config
            self.config.strict_mode = robust_risk_config.get("strict_mode", False)
            self.config.correlation_matrix = robust_risk_config.get("correlation_matrix", {})
            self.config.asset_categories = robust_risk_config.get("asset_categories", {})

        except Exception as e:
            self.logger.error(f"Failed to load risk configuration: {e}")
            # Use defaults if config loading fails

    def check_pre_trade_risk(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        stop_loss: Optional[float] = None,
    ) -> RiskCheckResult:
        """Comprehensive pre-trade risk check."""
        try:
            if not self.config.enabled:
                return RiskCheckResult(is_valid=True)

            # Get current portfolio state
            sym_to_price = self._get_current_prices()
            if symbol not in sym_to_price:
                sym_to_price[symbol] = price  # Use provided price if not available

            total_equity = self._calculate_total_equity(sym_to_price)

            # Check kill switch first
            if not self.kill_switch.is_trading_allowed():
                return RiskCheckResult(
                    is_valid=False,
                    violations=[
                        RiskViolation(
                            violation_type=RiskViolationType.KILL_SWITCH_ACTIVATED,
                            severity=RiskLevel.CRITICAL,
                            message="Trading blocked by kill switch",
                            current_value=0.0,
                            limit_value=0.0,
                            timestamp=datetime.now(timezone.utc),
                        )
                    ],
                )

            # Check portfolio limits
            portfolio_check = self._check_portfolio_limits(
                symbol, side, quantity, price, total_equity
            )
            if not portfolio_check.is_valid:
                return portfolio_check

            # Check per-trade limits
            trade_check = self._check_per_trade_limits(
                symbol, side, quantity, price, stop_loss, total_equity
            )
            if not trade_check.is_valid:
                return trade_check

            # Check drawdown limits
            drawdown_check = self._check_drawdown_limits()
            if not drawdown_check.is_valid:
                return drawdown_check

            # Check leverage limits (if applicable)
            leverage_check = self._check_leverage_limits(symbol, quantity, price, total_equity)
            if not leverage_check.is_valid:
                return leverage_check

            return RiskCheckResult(is_valid=True)

        except Exception as e:
            self.logger.error(f"Error in pre-trade risk check: {e}")
            return RiskCheckResult(
                is_valid=False,
                violations=[
                    RiskViolation(
                        violation_type=RiskViolationType.KILL_SWITCH_ACTIVATED,
                        severity=RiskLevel.HIGH,
                        message=f"Risk check error: {str(e)}",
                        current_value=0.0,
                        limit_value=0.0,
                        timestamp=datetime.now(timezone.utc),
                    )
                ],
            )

    def perform_risk_assessment(self, sym_to_price: Dict[str, float]) -> RiskStatus:
        """Perform comprehensive risk assessment."""
        try:
            if not self.config.enabled:
                return RiskStatus()

            total_equity = self._calculate_total_equity(sym_to_price)

            # Update equity tracking
            self.drawdown_manager.update_equity_tracking(total_equity)

            # Calculate exposure metrics
            exposure_metrics = self.exposure_tracker.calculate_exposure_metrics(
                sym_to_price, total_equity
            )

            # Calculate drawdown metrics
            drawdown_metrics = self.drawdown_manager.calculate_drawdown_metrics()

            # Check for violations
            violations = []

            # Check exposure limits
            portfolio_limits = {
                "max_total_exposure_pct": self.config.limits.portfolio.max_total_exposure_pct,
                "max_exposure_per_coin_pct": self.config.limits.portfolio.max_exposure_per_coin_pct,
                "max_correlation_exposure_pct": self.config.limits.portfolio.max_correlation_exposure_pct,
                "max_leverage": self.config.limits.leverage.max_leverage,
                "max_margin_utilization_pct": self.config.limits.leverage.max_margin_utilization_pct,
                "funding_rate_cost_limit_daily": self.config.limits.funding_rate.funding_rate_cost_limit_daily,
            }
            exposure_violations = self.exposure_tracker.check_exposure_limits(
                exposure_metrics, portfolio_limits
            )
            violations.extend(exposure_violations)

            # Check drawdown limits
            drawdown_limits = {
                "daily_max_drawdown_pct": self.config.limits.drawdown.daily_max_drawdown_pct,
                "weekly_max_drawdown_pct": self.config.limits.drawdown.weekly_max_drawdown_pct,
                "max_drawdown_pct": self.config.limits.drawdown.max_drawdown_pct,
                "kill_switch_drawdown_pct": self.config.limits.drawdown.kill_switch_drawdown_pct,
            }
            drawdown_violations = self.drawdown_manager.check_drawdown_limits(
                drawdown_metrics, drawdown_limits
            )
            violations.extend(drawdown_violations)

            # Check kill switch triggers
            kill_switch_violations = self.kill_switch.check_triggers(self.risk_status)
            violations.extend(kill_switch_violations)

            # Determine overall risk level
            overall_risk_level = self._determine_risk_level(violations)

            # Update risk status
            self.risk_status = RiskStatus(
                overall_risk_level=overall_risk_level,
                active_violations=violations,
                kill_switch_active=self.kill_switch.is_active,
                last_risk_check=datetime.now(timezone.utc),
                exposure_metrics=exposure_metrics,
                drawdown_metrics=drawdown_metrics,
            )

            # Handle violations and warnings
            self._handle_violations(violations)

            self.last_risk_check = datetime.now(timezone.utc)
            return self.risk_status

        except Exception as e:
            self.logger.error(f"Error in risk assessment: {e}")
            return RiskStatus()

    def _get_current_prices(self) -> Dict[str, float]:
        """Get current prices for all tracked symbols."""
        try:
            # This would integrate with the price manager
            # For now, return empty dict - prices should be passed from calling code
            return {}
        except Exception:
            return {}

    def _calculate_total_equity(self, sym_to_price: Dict[str, float]) -> float:
        """Calculate total portfolio equity."""
        try:
            return self.portfolio_manager.calculate_equity(sym_to_price)
        except Exception:
            return 0.0

    def _check_portfolio_limits(
        self, symbol: str, side: str, quantity: float, price: float, total_equity: float
    ) -> RiskCheckResult:
        """Check portfolio-level limits."""
        violations = []

        try:
            # Check max open positions
            current_positions = len(self.portfolio_manager.portfolio.positions)
            if (
                side == "buy"
                and current_positions >= self.config.limits.portfolio.max_open_positions
            ):
                if symbol not in self.portfolio_manager.portfolio.positions:
                    violation = RiskViolation(
                        violation_type=RiskViolationType.MAX_POSITIONS_EXCEEDED,
                        severity=RiskLevel.MEDIUM,
                        message=f"Maximum open positions {self.config.limits.portfolio.max_open_positions} exceeded",
                        current_value=float(current_positions),
                        limit_value=float(self.config.limits.portfolio.max_open_positions),
                        timestamp=datetime.now(timezone.utc),
                        symbol=symbol,
                    )
                    violations.append(violation)

            # Check if already in position for this symbol
            if side == "buy" and symbol in self.portfolio_manager.portfolio.positions:
                violation = RiskViolation(
                    violation_type=RiskViolationType.PER_COIN_EXPOSURE_EXCEEDED,
                    severity=RiskLevel.MEDIUM,
                    message=f"Already in position for {symbol}",
                    current_value=1.0,
                    limit_value=1.0,
                    timestamp=datetime.now(timezone.utc),
                    symbol=symbol,
                )
                violations.append(violation)

        except Exception as e:
            self.logger.error(f"Error checking portfolio limits: {e}")

        return RiskCheckResult(is_valid=len(violations) == 0, violations=violations)

    def _check_per_trade_limits(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        stop_loss: Optional[float],
        total_equity: float,
    ) -> RiskCheckResult:
        """Check per-trade risk limits."""
        violations = []

        try:
            trade_value = quantity * price

            # Check position size limit
            position_size_pct = (trade_value / total_equity * 100.0) if total_equity > 0 else 0.0
            if position_size_pct > self.config.limits.per_trade.max_position_size_pct:
                violation = RiskViolation(
                    violation_type=RiskViolationType.PER_COIN_EXPOSURE_EXCEEDED,
                    severity=RiskLevel.MEDIUM,
                    message=f"Position size {position_size_pct:.2f}% exceeds limit {self.config.limits.per_trade.max_position_size_pct}%",
                    current_value=position_size_pct,
                    limit_value=self.config.limits.per_trade.max_position_size_pct,
                    timestamp=datetime.now(timezone.utc),
                    symbol=symbol,
                )
                violations.append(violation)

            # Check risk-reward ratio if stop loss provided
            if stop_loss and side == "buy":
                risk_amount = price - stop_loss
                reward_amount = price * 0.06  # Assume 6% take profit
                if reward_amount > 0:
                    risk_reward_ratio = reward_amount / risk_amount
                    if risk_reward_ratio < self.config.limits.per_trade.min_risk_reward_ratio:
                        violation = RiskViolation(
                            violation_type=RiskViolationType.PER_COIN_EXPOSURE_EXCEEDED,
                            severity=RiskLevel.LOW,
                            message=f"Risk-reward ratio {risk_reward_ratio:.2f} below minimum {self.config.limits.per_trade.min_risk_reward_ratio}",
                            current_value=risk_reward_ratio,
                            limit_value=self.config.limits.per_trade.min_risk_reward_ratio,
                            timestamp=datetime.now(timezone.utc),
                            symbol=symbol,
                        )
                        violations.append(violation)

        except Exception as e:
            self.logger.error(f"Error checking per-trade limits: {e}")

        return RiskCheckResult(is_valid=len(violations) == 0, violations=violations)

    def _check_drawdown_limits(self) -> RiskCheckResult:
        """Check drawdown limits."""
        violations = []

        try:
            drawdown_metrics = self.drawdown_manager.calculate_drawdown_metrics()
            drawdown_limits = {
                "daily_max_drawdown_pct": self.config.limits.drawdown.daily_max_drawdown_pct,
                "weekly_max_drawdown_pct": self.config.limits.drawdown.weekly_max_drawdown_pct,
                "max_drawdown_pct": self.config.limits.drawdown.max_drawdown_pct,
                "kill_switch_drawdown_pct": self.config.limits.drawdown.kill_switch_drawdown_pct,
            }
            violations = self.drawdown_manager.check_drawdown_limits(
                drawdown_metrics, drawdown_limits
            )

        except Exception as e:
            self.logger.error(f"Error checking drawdown limits: {e}")

        return RiskCheckResult(is_valid=len(violations) == 0, violations=violations)

    def _check_leverage_limits(
        self, symbol: str, quantity: float, price: float, total_equity: float
    ) -> RiskCheckResult:
        """Check leverage limits."""
        violations = []

        try:
            # For now, assume spot trading (leverage = 1.0)
            # This would be enhanced to check actual leverage for perpetual positions
            leverage = 1.0
            if leverage > self.config.limits.leverage.max_leverage:
                violation = RiskViolation(
                    violation_type=RiskViolationType.LEVERAGE_EXCEEDED,
                    severity=RiskLevel.HIGH,
                    message=f"Leverage {leverage}x exceeds limit {self.config.limits.leverage.max_leverage}x",
                    current_value=leverage,
                    limit_value=self.config.limits.leverage.max_leverage,
                    timestamp=datetime.now(timezone.utc),
                    symbol=symbol,
                )
                violations.append(violation)

        except Exception as e:
            self.logger.error(f"Error checking leverage limits: {e}")

        return RiskCheckResult(is_valid=len(violations) == 0, violations=violations)

    def _determine_risk_level(self, violations: List[RiskViolation]) -> RiskLevel:
        """Determine overall risk level based on violations."""
        if not violations:
            return RiskLevel.LOW

        # Check for critical violations
        critical_violations = [v for v in violations if v.severity == RiskLevel.CRITICAL]
        if critical_violations:
            return RiskLevel.CRITICAL

        # Check for high violations
        high_violations = [v for v in violations if v.severity == RiskLevel.HIGH]
        if high_violations:
            return RiskLevel.HIGH

        # Check for medium violations
        medium_violations = [v for v in violations if v.severity == RiskLevel.MEDIUM]
        if medium_violations:
            return RiskLevel.MEDIUM

        return RiskLevel.LOW

    def _handle_violations(self, violations: List[RiskViolation]):
        """Handle risk violations."""
        try:
            for violation in violations:
                # Call violation handlers
                for handler in self.violation_handlers:
                    try:
                        handler(violation)
                    except Exception:
                        continue

                # Log violation
                self.logger.warning(f"Risk violation: {violation.message}")

        except Exception as e:
            self.logger.error(f"Error handling violations: {e}")

    def add_violation_handler(self, handler: callable):
        """Add a violation handler."""
        self.violation_handlers.append(handler)

    def add_warning_handler(self, handler: callable):
        """Add a warning handler."""
        self.warning_handlers.append(handler)

    def get_risk_summary(self) -> Dict[str, Any]:
        """Get comprehensive risk summary."""
        try:
            return {
                "overall_risk_level": self.risk_status.overall_risk_level.value,
                "kill_switch_active": self.kill_switch.is_active,
                "kill_switch_status": self.kill_switch.get_status(),
                "exposure_metrics": {
                    "total_exposure_pct": self.risk_status.exposure_metrics.total_exposure_pct,
                    "total_exposure_usd": self.risk_status.exposure_metrics.total_exposure_usd,
                    "leverage_utilization": self.risk_status.exposure_metrics.leverage_utilization,
                    "margin_utilization": self.risk_status.exposure_metrics.margin_utilization,
                    "funding_rate_cost_daily": self.risk_status.exposure_metrics.funding_rate_cost_daily,
                },
                "drawdown_metrics": {
                    "current_drawdown_pct": self.risk_status.drawdown_metrics.current_drawdown_pct,
                    "daily_drawdown_pct": self.risk_status.drawdown_metrics.daily_drawdown_pct,
                    "weekly_drawdown_pct": self.risk_status.drawdown_metrics.weekly_drawdown_pct,
                    "max_drawdown_pct": self.risk_status.drawdown_metrics.max_drawdown_pct,
                    "equity_peak": self.risk_status.drawdown_metrics.equity_peak,
                },
                "active_violations_count": len(self.risk_status.active_violations),
                "last_risk_check": (
                    self.risk_status.last_risk_check.isoformat()
                    if self.risk_status.last_risk_check
                    else None
                ),
                "configuration": {
                    "enabled": self.config.enabled,
                    "strict_mode": self.config.strict_mode,
                },
            }
        except Exception as e:
            self.logger.error(f"Error getting risk summary: {e}")
            return {}

    def is_trading_allowed(self) -> bool:
        """Check if trading is currently allowed."""
        return self.config.enabled and self.kill_switch.is_trading_allowed()

    def force_kill_switch_activation(self, reason: str = "manual"):
        """Manually activate kill switch."""
        self.kill_switch.activate_kill_switch("manual", reason)

    def force_kill_switch_deactivation(self, reason: str = "manual"):
        """Manually deactivate kill switch."""
        self.kill_switch.deactivate_kill_switch(reason)
