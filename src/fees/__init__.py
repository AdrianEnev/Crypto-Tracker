"""
Advanced Fee Models Package

Provides realistic fee calculation for different exchanges including
maker/taker differentiation, volume-based tiers, and withdrawal fees.
"""

from .models import (
    FeeBreakdown,
    FeeTier,
    ExchangeFeeStructure,
    FeeType,
    FeeCalculationMode,
    OrderFeeContext,
    AssetSpecificFee,
    FeeCalculationError,
    UnsupportedExchangeError,
    UnsupportedAssetError
)
from .exchange_fees import (
    ExchangeFeeRegistry,
    get_exchange_fees,
    register_exchange_fees,
    list_supported_exchanges,
    get_default_fee_tiers
)
from .calculator import FeeCalculator
from .backtest_fees import BacktestFeeCalculator, BacktestFeeStats

__all__ = [
    'FeeBreakdown',
    'FeeTier', 
    'ExchangeFeeStructure',
    'FeeType',
    'FeeCalculationMode',
    'OrderFeeContext',
    'AssetSpecificFee',
    'FeeCalculationError',
    'UnsupportedExchangeError',
    'UnsupportedAssetError',
    'ExchangeFeeRegistry',
    'get_exchange_fees',
    'register_exchange_fees',
    'list_supported_exchanges',
    'get_default_fee_tiers',
    'FeeCalculator',
    'BacktestFeeCalculator',
    'BacktestFeeStats'
]
