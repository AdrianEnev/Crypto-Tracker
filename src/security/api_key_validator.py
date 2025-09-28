"""
API Key Safety Validator

Validates API key permissions and safety controls before trading operations.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from datetime import datetime, timezone
from enum import Enum
import logging

# Conditional import for ccxt
try:
    import ccxt

    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False
    ccxt = None


class PermissionLevel(Enum):
    """API key permission levels."""

    READ_ONLY = "read_only"
    TRADING_ONLY = "trading_only"
    FULL_ACCESS = "full_access"
    WITHDRAWAL_ENABLED = "withdrawal_enabled"


class SafetyStatus(Enum):
    """API key safety status."""

    SAFE = "safe"
    WARNING = "warning"
    UNSAFE = "unsafe"
    CRITICAL = "critical"


@dataclass
class APIKeyValidationResult:
    """Result of API key validation."""

    is_safe: bool
    safety_status: SafetyStatus
    permission_level: PermissionLevel
    warnings: List[str]
    errors: List[str]
    withdrawal_addresses: List[str]
    ip_whitelist: List[str]
    restrictions: Dict[str, any]


class APIKeyValidator:
    """Validates API key safety and permissions."""

    def __init__(self, exchange_name: str, api_key: str, secret: str):
        self.exchange_name = exchange_name
        self.api_key = api_key
        self.secret = secret
        self.logger = logging.getLogger(__name__)

        # Initialize exchange for validation
        self.exchange = self._initialize_exchange()

        # Safety thresholds
        self.max_withdrawal_amount_usd = 1000.0  # Configurable
        self.required_ip_whitelist = True
        self.allowed_permission_levels = {PermissionLevel.READ_ONLY, PermissionLevel.TRADING_ONLY}

    def validate_api_key_safety(self) -> APIKeyValidationResult:
        """Comprehensive API key safety validation."""
        warnings = []
        errors = []

        try:
            # Test basic connectivity
            if not self._test_connectivity():
                errors.append("Failed to connect to exchange")
                return APIKeyValidationResult(
                    is_safe=False,
                    safety_status=SafetyStatus.CRITICAL,
                    permission_level=PermissionLevel.FULL_ACCESS,
                    warnings=warnings,
                    errors=errors,
                    withdrawal_addresses=[],
                    ip_whitelist=[],
                    restrictions={},
                )

            # Check permissions
            permission_level = self._check_permissions()

            # Check withdrawal settings
            withdrawal_addresses = self._get_withdrawal_addresses()
            withdrawal_enabled = len(withdrawal_addresses) > 0

            # Check IP whitelist
            ip_whitelist = self._get_ip_whitelist()

            # Determine safety status
            safety_status = self._determine_safety_status(
                permission_level, withdrawal_enabled, ip_whitelist
            )

            # Generate warnings/errors
            if withdrawal_enabled:
                warnings.append("WITHDRAWAL ENABLED: API key has withdrawal permissions")
                if permission_level == PermissionLevel.FULL_ACCESS:
                    errors.append("CRITICAL: API key has full access including withdrawals")

            if not ip_whitelist:
                warnings.append("No IP whitelist configured - API key accessible from any IP")

            if permission_level not in self.allowed_permission_levels:
                errors.append(
                    f"API key has {permission_level.value} permissions - not recommended for trading"
                )

            return APIKeyValidationResult(
                is_safe=safety_status in [SafetyStatus.SAFE, SafetyStatus.WARNING],
                safety_status=safety_status,
                permission_level=permission_level,
                warnings=warnings,
                errors=errors,
                withdrawal_addresses=withdrawal_addresses,
                ip_whitelist=ip_whitelist,
                restrictions=self._get_account_restrictions(),
            )

        except Exception as e:
            self.logger.error(f"API key validation failed: {e}")
            errors.append(f"Validation error: {str(e)}")
            return APIKeyValidationResult(
                is_safe=False,
                safety_status=SafetyStatus.CRITICAL,
                permission_level=PermissionLevel.FULL_ACCESS,
                warnings=warnings,
                errors=errors,
                withdrawal_addresses=[],
                ip_whitelist=[],
                restrictions={},
            )

    def _initialize_exchange(self):
        """Initialize exchange instance for validation."""
        if not CCXT_AVAILABLE:
            raise ImportError("ccxt library is required for API key validation")

        exchange_class = getattr(ccxt, self.exchange_name)
        return exchange_class(
            {
                "apiKey": self.api_key,
                "secret": self.secret,
                "enableRateLimit": True,
                "sandbox": False,  # Use live for validation
            }
        )

    def _test_connectivity(self) -> bool:
        """Test basic API connectivity."""
        try:
            self.exchange.load_markets()
            return True
        except Exception:
            return False

    def _check_permissions(self) -> PermissionLevel:
        """Check API key permissions."""
        try:
            # Try to fetch account info
            account = self.exchange.fetch_balance()

            # Try to place a test order (will be cancelled immediately)
            # This is exchange-specific and may need adjustment
            if hasattr(self.exchange, "fetch_permissions"):
                permissions = self.exchange.fetch_permissions()
                if "withdraw" in permissions and permissions["withdraw"]:
                    return PermissionLevel.WITHDRAWAL_ENABLED
                elif "trade" in permissions and permissions["trade"]:
                    return PermissionLevel.TRADING_ONLY
                else:
                    return PermissionLevel.READ_ONLY

            # Fallback: assume trading permissions if we can fetch balance
            return PermissionLevel.TRADING_ONLY

        except Exception:
            return PermissionLevel.READ_ONLY

    def _get_withdrawal_addresses(self) -> List[str]:
        """Get configured withdrawal addresses."""
        try:
            if hasattr(self.exchange, "fetch_withdrawal_addresses"):
                addresses = self.exchange.fetch_withdrawal_addresses()
                return [addr["address"] for addr in addresses]
            return []
        except Exception:
            return []

    def _get_ip_whitelist(self) -> List[str]:
        """Get IP whitelist configuration."""
        try:
            if hasattr(self.exchange, "fetch_ip_whitelist"):
                return self.exchange.fetch_ip_whitelist()
            return []
        except Exception:
            return []

    def _get_account_restrictions(self) -> Dict[str, any]:
        """Get account restrictions and limits."""
        try:
            restrictions = {}

            # Get trading limits
            if hasattr(self.exchange, "fetch_trading_limits"):
                restrictions["trading_limits"] = self.exchange.fetch_trading_limits()

            # Get withdrawal limits
            if hasattr(self.exchange, "fetch_withdrawal_limits"):
                restrictions["withdrawal_limits"] = self.exchange.fetch_withdrawal_limits()

            return restrictions
        except Exception:
            return {}

    def _determine_safety_status(
        self, permission_level: PermissionLevel, withdrawal_enabled: bool, ip_whitelist: List[str]
    ) -> SafetyStatus:
        """Determine overall safety status."""
        if permission_level == PermissionLevel.WITHDRAWAL_ENABLED or withdrawal_enabled:
            return SafetyStatus.CRITICAL
        elif permission_level == PermissionLevel.FULL_ACCESS:
            return SafetyStatus.UNSAFE
        elif not ip_whitelist:
            return SafetyStatus.WARNING
        else:
            return SafetyStatus.SAFE
