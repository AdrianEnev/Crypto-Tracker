"""
Market Impact Calculator

Calculates market impact of large orders and provides sophisticated
slippage estimation for institutional-sized trades.
"""

from __future__ import annotations
from typing import Optional, Dict, List, Tuple
import math

from .models import (
    SlippageResult,
    SlippageContext,
    SlippageType,
    MarketCondition,
    SlippageCalculationError,
)


class MarketImpactCalculator:
    """Advanced market impact calculator for large orders."""

    def __init__(
        self,
        permanent_impact_factor: float = 0.1,  # Permanent impact coefficient
        temporary_impact_factor: float = 0.3,  # Temporary impact coefficient
        decay_rate: float = 0.5,  # Price recovery decay rate
        volume_scale_factor: float = 0.5,  # Volume scaling factor
        volatility_impact: float = 1.5,  # Volatility impact multiplier
    ):
        self.permanent_impact_factor = permanent_impact_factor
        self.temporary_impact_factor = temporary_impact_factor
        self.decay_rate = decay_rate
        self.volume_scale_factor = volume_scale_factor
        self.volatility_impact = volatility_impact

    def calculate_market_impact(self, context: SlippageContext) -> SlippageResult:
        """
        Calculate market impact for large orders.

        Args:
            context: Slippage calculation context

        Returns:
            SlippageResult with market impact analysis
        """
        if not context.volume_24h or not context.current_price:
            # Fallback to simplified calculation
            return self._calculate_simplified_impact(context)

        # Calculate volume participation rate
        participation_rate = self._calculate_participation_rate(context)

        # Calculate permanent impact
        permanent_impact = self._calculate_permanent_impact(participation_rate, context)

        # Calculate temporary impact
        temporary_impact = self._calculate_temporary_impact(participation_rate, context)

        # Calculate total impact
        total_impact = permanent_impact + temporary_impact

        # Assess market condition
        market_condition = self._assess_market_condition(context, participation_rate)

        # Calculate effective price
        reference_price = context.current_price
        if context.side == "buy":
            effective_price = reference_price * (1 + total_impact / 10000.0)
        else:
            effective_price = reference_price * (1 - total_impact / 10000.0)

        # Calculate slippage in USD
        slippage_usd = abs(effective_price - reference_price) * context.quantity

        return SlippageResult(
            slippage_bps=total_impact,
            slippage_usd=slippage_usd,
            effective_price=effective_price,
            reference_price=reference_price,
            slippage_type=SlippageType.MARKET_IMPACT,
            market_condition=market_condition,
            market_impact_bps=total_impact,
            fill_quantity=context.quantity,
            unfilled_quantity=0.0,
            partial_fill=False,
        )

    def _calculate_participation_rate(self, context: SlippageContext) -> float:
        """Calculate participation rate (order size / daily volume)."""
        order_value = context.quantity * context.current_price
        participation_rate = order_value / context.volume_24h

        return min(participation_rate, 1.0)  # Cap at 100%

    def _calculate_permanent_impact(
        self, participation_rate: float, context: SlippageContext
    ) -> float:
        """Calculate permanent market impact."""
        volatility = context.volatility or 0.02

        # Permanent impact scales with square root of participation rate
        # and is proportional to volatility
        impact = self.permanent_impact_factor * math.sqrt(participation_rate) * volatility * 10000

        return impact

    def _calculate_temporary_impact(
        self, participation_rate: float, context: SlippageContext
    ) -> float:
        """Calculate temporary market impact."""
        volatility = context.volatility or 0.02

        # Temporary impact scales linearly with participation rate
        # and is proportional to volatility
        impact = self.temporary_impact_factor * participation_rate * volatility * 10000

        return impact

    def _assess_market_condition(
        self, context: SlippageContext, participation_rate: float
    ) -> MarketCondition:
        """Assess market condition based on impact analysis."""
        volatility = context.volatility or 0.02

        if participation_rate > 0.1 or volatility > 0.05:
            return MarketCondition.STRESSED
        elif participation_rate > 0.05 or volatility > 0.03:
            return MarketCondition.ILLIQUID
        elif participation_rate > 0.01 or volatility > 0.02:
            return MarketCondition.VOLATILE
        elif participation_rate < 0.001 and volatility < 0.01:
            return MarketCondition.CALM
        else:
            return MarketCondition.NORMAL

    def _calculate_simplified_impact(self, context: SlippageContext) -> SlippageResult:
        """Calculate simplified impact when volume data is not available."""
        # Use a simple linear model based on order size
        base_impact = 10.0  # 10 bps base impact
        size_impact = context.quantity * 0.001  # 0.1 bps per unit
        volatility = context.volatility or 0.02
        volatility_impact = volatility * 1000  # Scale volatility

        total_impact = (base_impact + size_impact) * (1 + volatility_impact)

        reference_price = context.current_price or 50000.0
        if context.side == "buy":
            effective_price = reference_price * (1 + total_impact / 10000.0)
        else:
            effective_price = reference_price * (1 - total_impact / 10000.0)

        slippage_usd = abs(effective_price - reference_price) * context.quantity

        return SlippageResult(
            slippage_bps=total_impact,
            slippage_usd=slippage_usd,
            effective_price=effective_price,
            reference_price=reference_price,
            slippage_type=SlippageType.MARKET_IMPACT,
            market_condition=MarketCondition.NORMAL,
            market_impact_bps=total_impact,
            fill_quantity=context.quantity,
            unfilled_quantity=0.0,
            partial_fill=False,
        )

    def calculate_optimal_execution(
        self, total_quantity: float, context: SlippageContext
    ) -> Dict[str, any]:
        """
        Calculate optimal execution strategy for large orders.

        Returns:
            Dictionary with execution strategy recommendations
        """
        if not context.volume_24h:
            # Fallback strategy
            return {
                "strategy": "uniform_slicing",
                "num_slices": 10,
                "slice_size": total_quantity / 10,
                "estimated_total_impact": 50.0,
                "estimated_duration_hours": 1.0,
            }

        # Calculate participation rate
        order_value = total_quantity * (context.current_price or 50000.0)
        participation_rate = order_value / context.volume_24h

        if participation_rate > 0.1:
            # Very large order - use VWAP strategy
            strategy = "vwap"
            num_slices = max(20, int(participation_rate * 100))
            estimated_duration = 8.0  # Full trading day
        elif participation_rate > 0.05:
            # Large order - use TWAP strategy
            strategy = "twap"
            num_slices = max(10, int(participation_rate * 50))
            estimated_duration = 4.0  # Half trading day
        elif participation_rate > 0.01:
            # Medium order - use uniform slicing
            strategy = "uniform_slicing"
            num_slices = max(5, int(participation_rate * 20))
            estimated_duration = 2.0  # 2 hours
        else:
            # Small order - execute immediately
            strategy = "immediate"
            num_slices = 1
            estimated_duration = 0.1  # 6 minutes

        slice_size = total_quantity / num_slices

        # Estimate total impact for the strategy
        estimated_impact = self._estimate_strategy_impact(strategy, num_slices, context)

        return {
            "strategy": strategy,
            "num_slices": num_slices,
            "slice_size": slice_size,
            "estimated_total_impact": estimated_impact,
            "estimated_duration_hours": estimated_duration,
            "participation_rate": participation_rate,
        }

    def _estimate_strategy_impact(
        self, strategy: str, num_slices: int, context: SlippageContext
    ) -> float:
        """Estimate total market impact for a given strategy."""
        slice_context = SlippageContext(
            symbol=context.symbol,
            side=context.side,
            quantity=context.quantity / num_slices,
            order_type=context.order_type,
            limit_price=context.limit_price,
            timestamp=context.timestamp,
            current_price=context.current_price,
            volume_24h=context.volume_24h,
            volatility=context.volatility,
            market_condition=context.market_condition,
        )

        slice_impact = self.calculate_market_impact(slice_context)

        # Apply strategy-specific impact reduction
        if strategy == "vwap":
            reduction_factor = 0.7  # VWAP reduces impact by 30%
        elif strategy == "twap":
            reduction_factor = 0.8  # TWAP reduces impact by 20%
        elif strategy == "uniform_slicing":
            reduction_factor = 0.9  # Uniform slicing reduces impact by 10%
        else:
            reduction_factor = 1.0  # No reduction for immediate execution

        return slice_impact.slippage_bps * reduction_factor

    def analyze_liquidity_consumption(
        self, context: SlippageContext, time_horizon_hours: float = 1.0
    ) -> Dict[str, float]:
        """
        Analyze how order execution would consume available liquidity over time.

        Args:
            context: Order context
            time_horizon_hours: Time horizon for analysis

        Returns:
            Dictionary with liquidity consumption metrics
        """
        if not context.volume_24h:
            return {
                "hourly_volume": 0.0,
                "consumption_rate": 0.0,
                "liquidity_shortfall": 0.0,
                "execution_risk": 0.0,
            }

        # Estimate hourly volume
        hourly_volume = context.volume_24h / 24.0

        # Calculate consumption rate
        order_value = context.quantity * (context.current_price or 50000.0)
        consumption_rate = order_value / (hourly_volume * time_horizon_hours)

        # Calculate liquidity shortfall
        liquidity_shortfall = max(0.0, consumption_rate - 1.0)

        # Calculate execution risk (probability of not being able to execute)
        volatility = context.volatility or 0.02
        execution_risk = min(1.0, liquidity_shortfall * volatility * 10)

        return {
            "hourly_volume": hourly_volume,
            "consumption_rate": consumption_rate,
            "liquidity_shortfall": liquidity_shortfall,
            "execution_risk": execution_risk,
        }

    def get_impact_sensitivity_analysis(self, context: SlippageContext) -> Dict[str, List[float]]:
        """Perform sensitivity analysis on market impact factors."""
        base_context = context

        # Test different participation rates
        participation_rates = [0.001, 0.005, 0.01, 0.05, 0.1, 0.2]
        participation_impacts = []

        for rate in participation_rates:
            test_quantity = rate * context.volume_24h / (context.current_price or 50000.0)
            test_context = SlippageContext(
                symbol=context.symbol,
                side=context.side,
                quantity=test_quantity,
                order_type=context.order_type,
                limit_price=context.limit_price,
                timestamp=context.timestamp,
                current_price=context.current_price,
                volume_24h=context.volume_24h,
                volatility=context.volatility,
                market_condition=context.market_condition,
            )

            result = self.calculate_market_impact(test_context)
            participation_impacts.append(result.slippage_bps)

        # Test different volatility levels
        volatility_levels = [0.005, 0.01, 0.02, 0.03, 0.05, 0.1]
        volatility_impacts = []

        for vol in volatility_levels:
            test_context = SlippageContext(
                symbol=context.symbol,
                side=context.side,
                quantity=context.quantity,
                order_type=context.order_type,
                limit_price=context.limit_price,
                timestamp=context.timestamp,
                current_price=context.current_price,
                volume_24h=context.volume_24h,
                volatility=vol,
                market_condition=context.market_condition,
            )

            result = self.calculate_market_impact(test_context)
            volatility_impacts.append(result.slippage_bps)

        return {
            "participation_rates": participation_rates,
            "participation_impacts": participation_impacts,
            "volatility_levels": volatility_levels,
            "volatility_impacts": volatility_impacts,
        }
