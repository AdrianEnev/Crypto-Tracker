"""
Automated kill switch system for emergency risk management.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional

from .models import RiskLevel, RiskStatus, RiskViolation, RiskViolationType


@dataclass
class KillSwitchTrigger:
    """Represents a kill switch trigger condition."""

    name: str
    condition: Callable[[RiskStatus], bool]
    severity: RiskLevel
    description: str
    cooldown_minutes: int = 60  # Cooldown before auto-reset


class KillSwitch:
    """Automated kill switch system for emergency risk management."""

    def __init__(self, config_manager, portfolio_manager, order_manager=None):
        self.config_manager = config_manager
        self.portfolio_manager = portfolio_manager
        self.order_manager = order_manager

        # Kill switch state
        self.is_active: bool = False
        self.activation_reason: Optional[str] = None
        self.activated_at: Optional[datetime] = None
        self.auto_reset_at: Optional[datetime] = None

        # Trigger conditions
        self.triggers: List[KillSwitchTrigger] = []
        self._initialize_triggers()

        # Persistence
        self.state_path = self._get_state_path()
        self._load_state()

    def _get_state_path(self) -> Path:
        """Get path for persisting kill switch state."""
        try:
            config_path = Path(self.config_manager.config_path)
            return config_path.parent.parent / "logs" / "kill_switch_state.json"
        except Exception:
            return Path("logs/kill_switch_state.json")

    def _load_state(self):
        """Load kill switch state from disk."""
        try:
            if self.state_path.exists():
                with self.state_path.open("r") as f:
                    data = json.load(f)

                self.is_active = data.get("is_active", False)
                self.activation_reason = data.get("activation_reason")

                if data.get("activated_at"):
                    self.activated_at = datetime.fromisoformat(data["activated_at"])

                if data.get("auto_reset_at"):
                    self.auto_reset_at = datetime.fromisoformat(data["auto_reset_at"])

        except Exception:
            self.is_active = False
            self.activation_reason = None
            self.activated_at = None
            self.auto_reset_at = None

    def _save_state(self):
        """Save kill switch state to disk."""
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "is_active": self.is_active,
                "activation_reason": self.activation_reason,
                "activated_at": self.activated_at.isoformat() if self.activated_at else None,
                "auto_reset_at": self.auto_reset_at.isoformat() if self.auto_reset_at else None,
            }

            with self.state_path.open("w") as f:
                json.dump(data, f, indent=2)

        except Exception:
            pass  # Fail silently

    def _initialize_triggers(self):
        """Initialize kill switch trigger conditions."""
        try:
            # Drawdown trigger
            drawdown_trigger = KillSwitchTrigger(
                name="excessive_drawdown",
                condition=self._check_drawdown_trigger,
                severity=RiskLevel.CRITICAL,
                description="Excessive drawdown detected",
                cooldown_minutes=120,  # 2 hours before auto-reset
            )
            self.triggers.append(drawdown_trigger)

            # Exposure trigger
            exposure_trigger = KillSwitchTrigger(
                name="excessive_exposure",
                condition=self._check_exposure_trigger,
                severity=RiskLevel.HIGH,
                description="Excessive portfolio exposure detected",
                cooldown_minutes=60,  # 1 hour before auto-reset
            )
            self.triggers.append(exposure_trigger)

            # Leverage trigger
            leverage_trigger = KillSwitchTrigger(
                name="excessive_leverage",
                condition=self._check_leverage_trigger,
                severity=RiskLevel.HIGH,
                description="Excessive leverage detected",
                cooldown_minutes=90,  # 1.5 hours before auto-reset
            )
            self.triggers.append(leverage_trigger)

            # Error rate trigger
            error_trigger = KillSwitchTrigger(
                name="high_error_rate",
                condition=self._check_error_rate_trigger,
                severity=RiskLevel.MEDIUM,
                description="High error rate detected",
                cooldown_minutes=30,  # 30 minutes before auto-reset
            )
            self.triggers.append(error_trigger)

        except Exception:
            self.triggers = []

    def _check_drawdown_trigger(self, risk_status: RiskStatus) -> bool:
        """Check if drawdown trigger should activate kill switch."""
        try:
            # Get kill switch drawdown limit from config
            robust_risk_config = self.config_manager.load_full_config().get("robust_risk", {})
            drawdown_limits = robust_risk_config.get("drawdown_limits", {})
            kill_switch_drawdown_pct = drawdown_limits.get("kill_switch_drawdown_pct", 15.0)

            # Check current drawdown
            current_drawdown = risk_status.drawdown_metrics.current_drawdown_pct
            return current_drawdown > kill_switch_drawdown_pct

        except Exception:
            return False

    def _check_exposure_trigger(self, risk_status: RiskStatus) -> bool:
        """Check if exposure trigger should activate kill switch."""
        try:
            # Get exposure limits from config
            robust_risk_config = self.config_manager.load_full_config().get("robust_risk", {})
            portfolio_limits = robust_risk_config.get("portfolio_limits", {})
            max_total_exposure_pct = portfolio_limits.get("max_total_exposure_pct", 80.0)

            # Check total exposure (with some buffer for kill switch)
            current_exposure = risk_status.exposure_metrics.total_exposure_pct
            kill_switch_threshold = max_total_exposure_pct * 1.1  # 110% of limit

            return current_exposure > kill_switch_threshold

        except Exception:
            return False

    def _check_leverage_trigger(self, risk_status: RiskStatus) -> bool:
        """Check if leverage trigger should activate kill switch."""
        try:
            # Get leverage limits from config
            robust_risk_config = self.config_manager.load_full_config().get("robust_risk", {})
            leverage_limits = robust_risk_config.get("leverage_limits", {})
            max_leverage = leverage_limits.get("max_leverage", 3.0)

            # Check leverage utilization (with some buffer for kill switch)
            current_leverage = risk_status.exposure_metrics.leverage_utilization
            kill_switch_threshold = max_leverage * 1.2  # 120% of limit

            return current_leverage > kill_switch_threshold

        except Exception:
            return False

    def _check_error_rate_trigger(self, risk_status: RiskStatus) -> bool:
        """Check if error rate trigger should activate kill switch."""
        try:
            # This would need to be implemented with actual error tracking
            # For now, return False as we don't have error rate tracking yet
            return False

        except Exception:
            return False

    def check_triggers(self, risk_status: RiskStatus) -> List[RiskViolation]:
        """Check all kill switch triggers and return violations."""
        violations = []
        timestamp = datetime.now(timezone.utc)

        try:
            # Skip trigger checks if kill switch is already active
            if self.is_active:
                # Check if it's time for auto-reset
                if self.auto_reset_at and datetime.now(timezone.utc) >= self.auto_reset_at:
                    self.deactivate_kill_switch("auto_reset_timeout")
                return violations

            # Check each trigger
            for trigger in self.triggers:
                try:
                    if trigger.condition(risk_status):
                        violation = RiskViolation(
                            violation_type=RiskViolationType.KILL_SWITCH_ACTIVATED,
                            severity=trigger.severity,
                            message=f"Kill switch triggered by {trigger.name}: {trigger.description}",
                            current_value=0.0,  # Will be filled by specific trigger
                            limit_value=0.0,  # Will be filled by specific trigger
                            timestamp=timestamp,
                            additional_data={
                                "trigger_name": trigger.name,
                                "description": trigger.description,
                                "cooldown_minutes": trigger.cooldown_minutes,
                            },
                        )
                        violations.append(violation)

                        # Activate kill switch immediately on first trigger
                        if not self.is_active:
                            self.activate_kill_switch(trigger.name, trigger.description)
                            break

                except Exception:
                    continue  # Skip failed trigger checks

        except Exception:
            pass

        return violations

    def activate_kill_switch(self, trigger_name: str, reason: str):
        """Activate the kill switch."""
        try:
            self.is_active = True
            self.activation_reason = f"{trigger_name}: {reason}"
            self.activated_at = datetime.now(timezone.utc)

            # Set auto-reset time based on trigger cooldown
            trigger = next((t for t in self.triggers if t.name == trigger_name), None)
            if trigger:
                self.auto_reset_at = self.activated_at + timedelta(minutes=trigger.cooldown_minutes)
            else:
                self.auto_reset_at = self.activated_at + timedelta(minutes=60)  # Default 1 hour

            self._save_state()

            # Execute emergency actions
            self._execute_emergency_actions()

        except Exception:
            pass

    def deactivate_kill_switch(self, reason: str = "manual"):
        """Deactivate the kill switch."""
        try:
            self.is_active = False
            self.activation_reason = f"Deactivated: {reason}"
            self.activated_at = None
            self.auto_reset_at = None
            self._save_state()

        except Exception:
            pass

    def _execute_emergency_actions(self):
        """Execute emergency actions when kill switch is activated."""
        try:
            # Cancel all pending orders
            if self.order_manager:
                try:
                    cancelled_count = self.order_manager.cancel_all_orders(
                        reason="kill_switch_activated"
                    )
                    # Log the emergency action
                    self._log_emergency_action(
                        f"Cancelled {cancelled_count} orders due to kill switch"
                    )
                except Exception:
                    self._log_emergency_action(
                        "Failed to cancel orders during kill switch activation"
                    )

            # Log the kill switch activation
            self._log_emergency_action(f"Kill switch activated: {self.activation_reason}")

            # TODO: Implement additional emergency actions:
            # - Close positions if drawdown is extreme
            # - Send emergency notifications
            # - Reduce position sizes
            # - Switch to safe mode

        except Exception:
            pass

    def _log_emergency_action(self, message: str):
        """Log emergency actions."""
        try:
            from src.logger import log_event

            log_event(
                "kill_switch_action",
                {
                    "message": message,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "is_active": self.is_active,
                    "activation_reason": self.activation_reason,
                },
            )
        except Exception:
            pass

    def get_status(self) -> Dict[str, any]:
        """Get current kill switch status."""
        return {
            "is_active": self.is_active,
            "activation_reason": self.activation_reason,
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
            "auto_reset_at": self.auto_reset_at.isoformat() if self.auto_reset_at else None,
            "time_until_reset_minutes": self._get_time_until_reset_minutes(),
        }

    def _get_time_until_reset_minutes(self) -> Optional[int]:
        """Get minutes until auto-reset."""
        try:
            if self.auto_reset_at:
                now = datetime.now(timezone.utc)
                if now < self.auto_reset_at:
                    delta = self.auto_reset_at - now
                    return int(delta.total_seconds() / 60)
            return None
        except Exception:
            return None

    def force_reset(self, reason: str = "manual_force"):
        """Force reset the kill switch (override cooldown)."""
        self.deactivate_kill_switch(f"force_reset: {reason}")

    def is_trading_allowed(self) -> bool:
        """Check if trading is allowed (kill switch not active)."""
        return not self.is_active
