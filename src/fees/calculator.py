"""
Fee Calculation Engine

Core fee calculation logic that determines appropriate fees based on
exchange, order type, volume tiers, and asset-specific rules.
"""

from __future__ import annotations
from typing import Optional, Dict, Any
from datetime import datetime

from .models import (
    FeeBreakdown, FeeType, FeeCalculationMode, OrderFeeContext,
    FeeCalculationError, UnsupportedExchangeError, UnsupportedAssetError
)
from .exchange_fees import get_exchange_fees


class FeeCalculator:
    """Main fee calculation engine."""
    
    def __init__(self, calculation_mode: FeeCalculationMode = FeeCalculationMode.REALISTIC):
        self.calculation_mode = calculation_mode
    
    def calculate_fees(self, context: OrderFeeContext) -> FeeBreakdown:
        """
        Calculate fees for an order based on the provided context.
        
        Args:
            context: Order fee context containing all necessary information
            
        Returns:
            FeeBreakdown with detailed fee information
            
        Raises:
            FeeCalculationError: If fee calculation fails
            UnsupportedExchangeError: If exchange is not supported
            UnsupportedAssetError: If asset is not supported
        """
        if self.calculation_mode == FeeCalculationMode.ZERO:
            return self._calculate_zero_fees(context)
        elif self.calculation_mode == FeeCalculationMode.SIMPLIFIED:
            return self._calculate_simplified_fees(context)
        else:
            return self._calculate_realistic_fees(context)
    
    def _calculate_zero_fees(self, context: OrderFeeContext) -> FeeBreakdown:
        """Calculate zero fees (for testing)."""
        return FeeBreakdown(
            exchange=context.exchange,
            calculation_mode=FeeCalculationMode.ZERO,
            fee_type_used=FeeType.TAKER,
            maker_bps=0.0,
            taker_bps=0.0
        )
    
    def _calculate_simplified_fees(self, context: OrderFeeContext) -> FeeBreakdown:
        """Calculate simplified flat fees."""
        # Use a simple 5 bps taker fee for all trades
        trading_fee_usd = context.order_value_usd * 0.0005  # 5 bps
        
        return FeeBreakdown(
            trading_fee_usd=trading_fee_usd,
            taker_fee_usd=trading_fee_usd,
            exchange=context.exchange,
            volume_tier="simplified",
            fee_type_used=FeeType.TAKER,
            calculation_mode=FeeCalculationMode.SIMPLIFIED,
            taker_bps=5.0
        )
    
    def _calculate_realistic_fees(self, context: OrderFeeContext) -> FeeBreakdown:
        """Calculate realistic fees based on exchange and volume tiers."""
        # Get exchange fee structure
        exchange_fees = get_exchange_fees(context.exchange)
        if not exchange_fees:
            raise UnsupportedExchangeError(f"Exchange '{context.exchange}' is not supported")
        
        # Check if asset is supported
        if exchange_fees.supported_assets:
            base_asset = self._extract_base_asset(context.symbol)
            if base_asset not in exchange_fees.supported_assets:
                raise UnsupportedAssetError(f"Asset '{base_asset}' not supported on {context.exchange}")
        
        # Get appropriate fee tier based on monthly volume
        fee_tier = exchange_fees.get_tier_for_volume(context.monthly_volume_usd)
        
        # Determine if this is a maker or taker order
        is_maker = context.is_maker or (context.order_type.lower() == "limit")
        fee_type = FeeType.MAKER if is_maker else FeeType.TAKER
        
        # Calculate trading fee
        if is_maker:
            fee_bps = fee_tier.maker_bps
            trading_fee_usd = context.order_value_usd * (fee_bps / 10000.0)
            maker_fee_usd = trading_fee_usd
            taker_fee_usd = 0.0
        else:
            fee_bps = fee_tier.taker_bps
            trading_fee_usd = context.order_value_usd * (fee_bps / 10000.0)
            maker_fee_usd = 0.0
            taker_fee_usd = trading_fee_usd
        
        # Calculate withdrawal fee (if applicable)
        withdrawal_fee_usd = self._calculate_withdrawal_fee(fee_tier, context)
        
        return FeeBreakdown(
            maker_fee_usd=maker_fee_usd,
            taker_fee_usd=taker_fee_usd,
            trading_fee_usd=trading_fee_usd,
            withdrawal_fee_usd=withdrawal_fee_usd,
            exchange=context.exchange,
            volume_tier=fee_tier.description,
            fee_type_used=fee_type,
            calculation_mode=FeeCalculationMode.REALISTIC,
            maker_bps=fee_tier.maker_bps,
            taker_bps=fee_tier.taker_bps,
            withdrawal_fee_rate=withdrawal_fee_usd
        )
    
    def _extract_base_asset(self, symbol: str) -> str:
        """Extract base asset from trading symbol (e.g., BTC from BTC/USDT)."""
        if "/" in symbol:
            return symbol.split("/")[0]
        return symbol
    
    def _calculate_withdrawal_fee(self, fee_tier, context: OrderFeeContext) -> float:
        """Calculate withdrawal fee based on fee tier and context."""
        # For now, we'll use a simple approach
        # In a more sophisticated implementation, this would consider:
        # - Asset-specific withdrawal fees
        # - Network fees (gas, etc.)
        # - Minimum/maximum withdrawal amounts
        
        if fee_tier.withdrawal_fee_usd is not None:
            return fee_tier.withdrawal_fee_usd
        elif fee_tier.withdrawal_fee_pct is not None:
            return context.order_value_usd * (fee_tier.withdrawal_fee_pct / 100.0)
        else:
            # Default withdrawal fee (e.g., 0.001 BTC for Bitcoin)
            base_asset = self._extract_base_asset(context.symbol)
            default_fees = {
                "BTC": 0.001,
                "ETH": 0.01,
                "LTC": 0.01,
                "BCH": 0.001,
                "XRP": 0.25,
                "ADA": 1.0,
                "DOT": 0.1,
                "LINK": 0.5,
                "UNI": 1.0
            }
            
            # Convert asset amount to USD (simplified)
            asset_price = context.order_price if context.side == "sell" else context.order_price
            asset_amount = default_fees.get(base_asset, 0.001)
            return asset_amount * asset_price
    
    def calculate_fees_for_order(
        self,
        order_value_usd: float,
        exchange: str,
        symbol: str,
        side: str,
        order_type: str,
        is_maker: bool = False,
        monthly_volume_usd: float = 0.0,
        order_price: Optional[float] = None,
        order_quantity: Optional[float] = None
    ) -> FeeBreakdown:
        """
        Convenience method for calculating fees for a single order.
        
        Args:
            order_value_usd: Total value of the order in USD
            exchange: Exchange name
            symbol: Trading symbol (e.g., "BTC/USDT")
            side: Order side ("buy" or "sell")
            order_type: Order type ("market", "limit", etc.)
            is_maker: Whether this order adds liquidity
            monthly_volume_usd: Monthly trading volume for tier calculation
            order_price: Order price (for withdrawal fee calculation)
            order_quantity: Order quantity (for withdrawal fee calculation)
            
        Returns:
            FeeBreakdown with calculated fees
        """
        context = OrderFeeContext(
            order_value_usd=order_value_usd,
            order_quantity=order_quantity or (order_value_usd / (order_price or 1.0)),
            order_price=order_price or 1.0,
            side=side,
            order_type=order_type,
            is_maker=is_maker,
            exchange=exchange,
            symbol=symbol,
            monthly_volume_usd=monthly_volume_usd,
            timestamp=datetime.now()
        )
        
        return self.calculate_fees(context)
    
    def get_supported_exchanges(self) -> list[str]:
        """Get list of supported exchanges."""
        from .exchange_fees import list_supported_exchanges
        return list_supported_exchanges()
    
    def get_exchange_info(self, exchange: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about an exchange's fee structure."""
        exchange_fees = get_exchange_fees(exchange)
        if not exchange_fees:
            return None
        
        return {
            "exchange_name": exchange_fees.exchange_name,
            "default_maker_bps": exchange_fees.default_maker_bps,
            "default_taker_bps": exchange_fees.default_taker_bps,
            "volume_tiers": [
                {
                    "volume_usd": tier.volume_usd,
                    "maker_bps": tier.maker_bps,
                    "taker_bps": tier.taker_bps,
                    "description": tier.description
                }
                for tier in exchange_fees.volume_tiers
            ],
            "supported_assets": exchange_fees.supported_assets
        }
