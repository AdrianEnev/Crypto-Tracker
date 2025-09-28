"""
Fee Model Data Structures

Defines the core data structures for fee calculation including
fee breakdowns, tiers, and exchange-specific configurations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class FeeType(Enum):
    """Types of fees that can be charged."""

    MAKER = "maker"
    TAKER = "taker"
    WITHDRAWAL = "withdrawal"
    DEPOSIT = "deposit"
    FUNDING = "funding"
    TRADING = "trading"


class FeeCalculationMode(Enum):
    """Mode for fee calculation in backtests."""

    REALISTIC = "realistic"  # Use actual exchange fees
    SIMPLIFIED = "simplified"  # Use simplified flat fees
    ZERO = "zero"  # No fees for testing


@dataclass
class FeeTier:
    """Represents a fee tier based on trading volume."""

    volume_usd: float  # Minimum volume to qualify for this tier
    maker_bps: float  # Maker fee in basis points
    taker_bps: float  # Taker fee in basis points
    withdrawal_fee_usd: Optional[float] = None  # Fixed withdrawal fee
    withdrawal_fee_pct: Optional[float] = None  # Percentage withdrawal fee
    description: str = ""


@dataclass
class ExchangeFeeStructure:
    """Complete fee structure for an exchange."""

    exchange_name: str
    default_maker_bps: float
    default_taker_bps: float
    default_withdrawal_fee_usd: float = 0.0
    default_withdrawal_fee_pct: float = 0.0
    volume_tiers: List[FeeTier] = field(default_factory=list)
    supported_assets: List[str] = field(default_factory=list)
    asset_specific_fees: Dict[str, Dict[FeeType, float]] = field(default_factory=dict)

    def get_tier_for_volume(self, volume_usd: float) -> FeeTier:
        """Get the appropriate fee tier for a given volume."""
        applicable_tiers = [tier for tier in self.volume_tiers if tier.volume_usd <= volume_usd]
        if not applicable_tiers:
            # Return default tier
            return FeeTier(
                volume_usd=0.0,
                maker_bps=self.default_maker_bps,
                taker_bps=self.default_taker_bps,
                withdrawal_fee_usd=self.default_withdrawal_fee_usd,
                withdrawal_fee_pct=self.default_withdrawal_fee_pct,
                description="Default tier",
            )

        # Return the highest applicable tier
        return max(applicable_tiers, key=lambda t: t.volume_usd)


@dataclass
class FeeBreakdown:
    """Detailed breakdown of all fees applied to a trade."""

    # Core fees
    maker_fee_usd: float = 0.0
    taker_fee_usd: float = 0.0
    trading_fee_usd: float = 0.0  # Total trading fee (maker or taker)

    # Additional fees
    withdrawal_fee_usd: float = 0.0
    deposit_fee_usd: float = 0.0
    funding_fee_usd: float = 0.0

    # Metadata
    exchange: str = ""
    volume_tier: str = "default"
    fee_type_used: FeeType = FeeType.TAKER
    calculation_mode: FeeCalculationMode = FeeCalculationMode.REALISTIC

    # Rates used (for transparency)
    maker_bps: float = 0.0
    taker_bps: float = 0.0
    withdrawal_fee_rate: float = 0.0

    @property
    def total_fees_usd(self) -> float:
        """Calculate total fees in USD."""
        return (
            self.trading_fee_usd
            + self.withdrawal_fee_usd
            + self.deposit_fee_usd
            + self.funding_fee_usd
        )

    @property
    def total_fees_bps(self) -> float:
        """Calculate total fees as basis points of trade value."""
        if hasattr(self, "_trade_value_usd") and self._trade_value_usd > 0:
            return (self.total_fees_usd / self._trade_value_usd) * 10000
        return 0.0

    def set_trade_value(self, trade_value_usd: float) -> None:
        """Set the trade value for percentage calculations."""
        self._trade_value_usd = trade_value_usd


@dataclass
class OrderFeeContext:
    """Context information for fee calculation."""

    order_value_usd: float
    order_quantity: float
    order_price: float
    side: str  # "buy" or "sell"
    order_type: str  # "market", "limit", etc.
    is_maker: bool = False  # Whether this order adds liquidity
    exchange: str = ""
    symbol: str = ""
    monthly_volume_usd: float = 0.0  # Monthly trading volume for tier calculation
    timestamp: Optional[datetime] = None


@dataclass
class AssetSpecificFee:
    """Fee structure for a specific asset."""

    asset: str
    maker_bps: float
    taker_bps: float
    withdrawal_fee_usd: Optional[float] = None
    withdrawal_fee_pct: Optional[float] = None
    deposit_fee_usd: Optional[float] = None
    min_withdrawal_amount: Optional[float] = None
    max_withdrawal_amount: Optional[float] = None


class FeeCalculationError(Exception):
    """Exception raised when fee calculation fails."""

    pass


class UnsupportedExchangeError(FeeCalculationError):
    """Exception raised when exchange is not supported."""

    pass


class UnsupportedAssetError(FeeCalculationError):
    """Exception raised when asset is not supported."""

    pass
