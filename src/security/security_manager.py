"""
Security Manager

Centralized security management for API keys, permissions, and safety controls.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .api_key_validator import APIKeyValidationResult, APIKeyValidator, SafetyStatus

# Conditional import for notifier
try:
    from src.notifier import Notifier

    NOTIFIER_AVAILABLE = True
except ImportError:
    NOTIFIER_AVAILABLE = False
    Notifier = None


class SecurityManager:
    """Manages security controls and API key safety."""

    def __init__(self, config_manager, notifier: Optional[Notifier] = None):
        self.config_manager = config_manager
        if NOTIFIER_AVAILABLE and notifier is not None:
            self.notifier = notifier
        elif NOTIFIER_AVAILABLE:
            self.notifier = Notifier()
        else:
            self.notifier = None
        self.logger = logging.getLogger(__name__)

        # Security configuration
        self.security_config = self._load_security_config()

        # Validation results cache
        self.validation_cache: Dict[str, APIKeyValidationResult] = {}
        self.last_validation: Dict[str, datetime] = {}

        # Security alerts
        self.security_alerts_sent: Dict[str, datetime] = {}

    def validate_exchange_api_key(
        self, exchange_name: str, api_key: str, secret: str
    ) -> APIKeyValidationResult:
        """Validate exchange API key safety."""
        cache_key = f"{exchange_name}_{api_key[:8]}"

        # Check cache (validate every 24 hours)
        if cache_key in self.validation_cache:
            last_check = self.last_validation.get(cache_key)
            if last_check and (datetime.now(timezone.utc) - last_check).total_seconds() < 86400:
                return self.validation_cache[cache_key]

        # Perform validation
        validator = APIKeyValidator(exchange_name, api_key, secret)
        result = validator.validate_api_key_safety()

        # Cache result
        self.validation_cache[cache_key] = result
        self.last_validation[cache_key] = datetime.now(timezone.utc)

        # Handle security alerts
        self._handle_security_alerts(exchange_name, result)

        return result

    def is_trading_safe(self, exchange_name: str, api_key: str, secret: str) -> bool:
        """Check if trading is safe with given API key."""
        result = self.validate_exchange_api_key(exchange_name, api_key, secret)

        # Block trading if critical safety issues
        if result.safety_status == SafetyStatus.CRITICAL:
            self.logger.critical(f"Trading blocked for {exchange_name}: {result.errors}")
            return False

        # Allow trading with warnings
        if result.safety_status in [SafetyStatus.SAFE, SafetyStatus.WARNING]:
            if result.warnings:
                self.logger.warning(
                    f"Trading allowed for {exchange_name} with warnings: {result.warnings}"
                )
            return True

        # Block trading for unsafe status
        self.logger.error(f"Trading blocked for {exchange_name}: Unsafe API key configuration")
        return False

    def _load_security_config(self) -> Dict:
        """Load security configuration."""
        try:
            config = self.config_manager.load_full_config()
            return config.get(
                "security",
                {
                    "max_withdrawal_amount_usd": 1000.0,
                    "required_ip_whitelist": True,
                    "allowed_permission_levels": ["read_only", "trading_only"],
                    "validation_interval_hours": 24,
                    "alert_on_withdrawal_enabled": True,
                    "alert_on_no_ip_whitelist": True,
                },
            )
        except Exception:
            return {}

    def _handle_security_alerts(self, exchange_name: str, result: APIKeyValidationResult):
        """Handle security alerts based on validation results."""
        alert_key = f"{exchange_name}_{result.safety_status.value}"

        # Prevent spam - only alert once per day per issue
        if alert_key in self.security_alerts_sent:
            last_alert = self.security_alerts_sent[alert_key]
            if (datetime.now(timezone.utc) - last_alert).total_seconds() < 86400:
                return

        # Send alerts for critical issues
        if result.safety_status == SafetyStatus.CRITICAL:
            self._send_critical_alert(exchange_name, result)
            self.security_alerts_sent[alert_key] = datetime.now(timezone.utc)

        elif result.safety_status == SafetyStatus.UNSAFE:
            self._send_unsafe_alert(exchange_name, result)
            self.security_alerts_sent[alert_key] = datetime.now(timezone.utc)

        elif result.warnings and self.security_config.get("alert_on_withdrawal_enabled", True):
            self._send_warning_alert(exchange_name, result)
            self.security_alerts_sent[alert_key] = datetime.now(timezone.utc)

    def _send_critical_alert(self, exchange_name: str, result: APIKeyValidationResult):
        """Send critical security alert."""
        message = "🚨 CRITICAL SECURITY ALERT 🚨\n"
        message += f"Exchange: {exchange_name}\n"
        message += f"Issues: {', '.join(result.errors)}\n"
        message += "Trading has been BLOCKED for safety."

        if self.notifier:
            self.notifier.alert("Security Alert", message, "red", "error")
        else:
            self.logger.critical(message)

    def _send_unsafe_alert(self, exchange_name: str, result: APIKeyValidationResult):
        """Send unsafe configuration alert."""
        message = "⚠️ UNSAFE API KEY CONFIGURATION ⚠️\n"
        message += f"Exchange: {exchange_name}\n"
        message += f"Issues: {', '.join(result.errors)}\n"
        message += "Please review API key permissions."

        if self.notifier:
            self.notifier.alert("Security Warning", message, "yellow", "warning")
        else:
            self.logger.warning(message)

    def _send_warning_alert(self, exchange_name: str, result: APIKeyValidationResult):
        """Send warning alert."""
        message = "⚠️ API KEY WARNING ⚠️\n"
        message += f"Exchange: {exchange_name}\n"
        message += f"Warnings: {', '.join(result.warnings)}\n"
        message += "Trading continues but please review configuration."

        if self.notifier:
            self.notifier.alert("Security Notice", message, "yellow", "info")
        else:
            self.logger.info(message)
