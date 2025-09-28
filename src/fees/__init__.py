"""
Advanced Fee Models Package

Provides realistic fee calculation for different exchanges including
maker/taker differentiation, volume-based tiers, and withdrawal fees.
"""

from .backtest_fees import BacktestFeeCalculator, BacktestFeeStats
from .calculator import FeeCalculator
from .exchange_fees import (
    ExchangeFeeRegistry,
    get_default_fee_tiers,
    get_exchange_fees,
    list_supported_exchanges,
    register_exchange_fees,
)
from .models import (
    AssetSpecificFee,
    ExchangeFeeStructure,
    FeeBreakdown,
    FeeCalculationError,
    FeeCalculationMode,
    FeeTier,
    FeeType,
    OrderFeeContext,
    UnsupportedAssetError,
    UnsupportedExchangeError,
)

__all__ = [
    "FeeBreakdown",
    "FeeTier",
    "ExchangeFeeStructure",
    "FeeType",
    "FeeCalculationMode",
    "OrderFeeContext",
    "AssetSpecificFee",
    "FeeCalculationError",
    "UnsupportedExchangeError",
    "UnsupportedAssetError",
    "ExchangeFeeRegistry",
    "get_exchange_fees",
    "register_exchange_fees",
    "list_supported_exchanges",
    "get_default_fee_tiers",
    "FeeCalculator",
    "BacktestFeeCalculator",
    "BacktestFeeStats",
]
