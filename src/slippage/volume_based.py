"""
Volume-Based Slippage Calculator

Calculates slippage based on order size relative to historical trading volume
and market activity. This model is useful when order book data is not available.
"""

from __future__ import annotations
from typing import Optional, Dict, List, Tuple
import math

from .models import (
    SlippageResult, SlippageContext, SlippageType, MarketCondition,
    SlippageCalculationError
)


class VolumeBasedSlippage:
    """Slippage calculator based on trading volume analysis."""
    
    def __init__(
        self,
        base_slippage_bps: float = 5.0,  # Base slippage for small orders
        volume_impact_factor: float = 0.5,  # Impact of volume on slippage
        volatility_factor: float = 2.0,  # Impact of volatility
        min_volume_ratio: float = 0.001,  # Minimum volume ratio for calculation
        max_slippage_bps: float = 1000.0  # Maximum slippage cap
    ):
        self.base_slippage_bps = base_slippage_bps
        self.volume_impact_factor = volume_impact_factor
        self.volatility_factor = volatility_factor
        self.min_volume_ratio = min_volume_ratio
        self.max_slippage_bps = max_slippage_bps
    
    def calculate_slippage(self, context: SlippageContext) -> SlippageResult:
        """
        Calculate slippage based on volume analysis.
        
        Args:
            context: Slippage calculation context
            
        Returns:
            SlippageResult with calculated slippage information
        """
        if not context.volume_24h:
            # Fallback to static slippage if no volume data
            return self._calculate_static_slippage(context)
        
        # Calculate volume impact
        volume_impact = self._calculate_volume_impact(context)
        
        # Calculate volatility impact
        volatility_impact = self._calculate_volatility_impact(context)
        
        # Calculate market condition
        market_condition = self._assess_market_condition(context)
        
        # Calculate base slippage
        base_slippage = self.base_slippage_bps
        
        # Apply volume and volatility impacts
        total_slippage = base_slippage * volume_impact * volatility_impact
        
        # Apply market condition adjustments
        total_slippage = self._apply_market_condition_adjustment(total_slippage, market_condition)
        
        # Cap slippage
        total_slippage = min(total_slippage, self.max_slippage_bps)
        
        # Calculate slippage in USD
        reference_price = context.current_price or 50000.0  # Fallback price
        slippage_usd = (total_slippage / 10000.0) * reference_price * context.quantity
        
        return SlippageResult(
            slippage_bps=total_slippage,
            slippage_usd=slippage_usd,
            effective_price=reference_price * (1 + (total_slippage / 10000.0) if context.side == "buy" else 1 - (total_slippage / 10000.0)),
            reference_price=reference_price,
            slippage_type=SlippageType.VOLUME_BASED,
            market_condition=market_condition,
            fill_quantity=context.quantity,
            unfilled_quantity=0.0,
            partial_fill=False
        )
    
    def _calculate_static_slippage(self, context: SlippageContext) -> SlippageResult:
        """Calculate static slippage when volume data is not available."""
        reference_price = context.current_price or 50000.0
        slippage_usd = (self.base_slippage_bps / 10000.0) * reference_price * context.quantity
        
        return SlippageResult(
            slippage_bps=self.base_slippage_bps,
            slippage_usd=slippage_usd,
            effective_price=reference_price * (1 + (self.base_slippage_bps / 10000.0) if context.side == "buy" else 1 - (self.base_slippage_bps / 10000.0)),
            reference_price=reference_price,
            slippage_type=SlippageType.STATIC,
            market_condition=MarketCondition.NORMAL,
            fill_quantity=context.quantity,
            unfilled_quantity=0.0,
            partial_fill=False
        )
    
    def _calculate_volume_impact(self, context: SlippageContext) -> float:
        """Calculate slippage impact based on order size vs volume."""
        if not context.volume_24h:
            return 1.0
        
        # Calculate order size as percentage of daily volume
        order_value = context.quantity * (context.current_price or 50000.0)
        volume_ratio = order_value / context.volume_24h
        
        # Ensure minimum ratio for calculation
        volume_ratio = max(volume_ratio, self.min_volume_ratio)
        
        # Apply power law scaling
        # Small orders have minimal impact, large orders have exponential impact
        impact = math.pow(volume_ratio, self.volume_impact_factor)
        
        return max(impact, 0.1)  # Minimum 10% of base slippage
    
    def _calculate_volatility_impact(self, context: SlippageContext) -> float:
        """Calculate slippage impact based on market volatility."""
        volatility = context.volatility or 0.02  # Default 2% volatility
        
        # Linear scaling with volatility
        # Higher volatility = higher slippage
        impact = 1.0 + (volatility * self.volatility_factor * 100)
        
        return max(impact, 0.5)  # Minimum 50% of base slippage
    
    def _assess_market_condition(self, context: SlippageContext) -> MarketCondition:
        """Assess market condition based on volume and volatility."""
        volatility = context.volatility or 0.02
        volume_ratio = 0.0
        
        if context.volume_24h and context.current_price:
            order_value = context.quantity * context.current_price
            volume_ratio = order_value / context.volume_24h
        
        # Classify based on volatility and volume impact
        if volatility > 0.05 or volume_ratio > 0.1:
            return MarketCondition.STRESSED
        elif volatility > 0.03 or volume_ratio > 0.05:
            return MarketCondition.ILLIQUID
        elif volatility > 0.02 or volume_ratio > 0.01:
            return MarketCondition.VOLATILE
        elif volatility < 0.01 and volume_ratio < 0.001:
            return MarketCondition.CALM
        else:
            return MarketCondition.NORMAL
    
    def _apply_market_condition_adjustment(self, slippage_bps: float, market_condition: MarketCondition) -> float:
        """Apply market condition adjustments to slippage."""
        adjustments = {
            MarketCondition.CALM: 0.7,      # 30% reduction in calm markets
            MarketCondition.NORMAL: 1.0,    # No adjustment
            MarketCondition.VOLATILE: 1.4,  # 40% increase in volatile markets
            MarketCondition.ILLIQUID: 2.0,  # 100% increase in illiquid markets
            MarketCondition.STRESSED: 3.0   # 200% increase in stressed markets
        }
        
        return slippage_bps * adjustments.get(market_condition, 1.0)
    
    def estimate_market_impact(self, context: SlippageContext) -> float:
        """Estimate the market impact of an order."""
        if not context.volume_24h:
            return 0.001  # Default 0.1% impact
        
        order_value = context.quantity * (context.current_price or 50000.0)
        volume_ratio = order_value / context.volume_24h
        
        # Market impact scales with square root of volume ratio
        impact = math.sqrt(volume_ratio)
        
        return min(impact, 0.1)  # Cap at 10% market impact
    
    def get_optimal_order_size(self, context: SlippageContext, max_slippage_bps: float) -> float:
        """Calculate optimal order size for a given maximum slippage."""
        if not context.volume_24h or not context.current_price:
            # Fallback calculation
            return context.quantity * 0.1  # Assume 10% of desired size
        
        # Reverse engineer the volume impact calculation
        # slippage = base_slippage * (order_value / volume_24h)^impact_factor
        # order_value = volume_24h * (slippage / base_slippage)^(1/impact_factor)
        
        max_impact = max_slippage_bps / self.base_slippage_bps
        max_volume_ratio = math.pow(max_impact, 1.0 / self.volume_impact_factor)
        max_order_value = context.volume_24h * max_volume_ratio
        
        return max_order_value / context.current_price
    
    def calculate_twap_impact(self, total_quantity: float, num_slices: int, context: SlippageContext) -> List[SlippageResult]:
        """Calculate slippage for TWAP order slicing."""
        slice_size = total_quantity / num_slices
        results = []
        
        for i in range(num_slices):
            slice_context = SlippageContext(
                symbol=context.symbol,
                side=context.side,
                quantity=slice_size,
                order_type=context.order_type,
                limit_price=context.limit_price,
                timestamp=context.timestamp,
                current_price=context.current_price,
                volume_24h=context.volume_24h,
                volatility=context.volatility,
                market_condition=context.market_condition
            )
            
            result = self.calculate_slippage(slice_context)
            results.append(result)
        
        return results
    
    def get_volume_profile(self, context: SlippageContext, order_sizes: List[float]) -> Dict[float, float]:
        """Get slippage profile for different order sizes."""
        profile = {}
        
        for size in order_sizes:
            test_context = SlippageContext(
                symbol=context.symbol,
                side=context.side,
                quantity=size,
                order_type=context.order_type,
                limit_price=context.limit_price,
                timestamp=context.timestamp,
                current_price=context.current_price,
                volume_24h=context.volume_24h,
                volatility=context.volatility,
                market_condition=context.market_condition
            )
            
            result = self.calculate_slippage(test_context)
            profile[size] = result.slippage_bps
        
        return profile
