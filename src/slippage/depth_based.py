"""
Depth-Based Slippage Calculator

Calculates slippage based on order book depth and available liquidity.
This provides the most realistic slippage estimation for market orders.
"""

from __future__ import annotations
from typing import Optional, List, Tuple
import math

from .models import (
    SlippageResult,
    SlippageContext,
    MarketDepth,
    SlippageType,
    MarketCondition,
    SlippageCalculationError,
    InsufficientLiquidityError,
    InvalidOrderBookError,
)


class DepthBasedSlippage:
    """Slippage calculator based on order book depth analysis."""

    def __init__(
        self,
        max_depth_levels: int = 20,
        min_liquidity_ratio: float = 0.1,  # Minimum 10% of order size available
        max_slippage_bps: float = 1000.0,  # Maximum 10% slippage
        spread_penalty_factor: float = 1.5,  # Penalty for wide spreads
    ):
        self.max_depth_levels = max_depth_levels
        self.min_liquidity_ratio = min_liquidity_ratio
        self.max_slippage_bps = max_slippage_bps
        self.spread_penalty_factor = spread_penalty_factor

    def calculate_slippage(self, context: SlippageContext) -> SlippageResult:
        """
        Calculate slippage based on order book depth.

        Args:
            context: Slippage calculation context

        Returns:
            SlippageResult with detailed slippage information

        Raises:
            SlippageCalculationError: If calculation fails
            InsufficientLiquidityError: If insufficient liquidity
            InvalidOrderBookError: If order book data is invalid
        """
        if not context.order_book:
            raise InvalidOrderBookError("Order book data is required for depth-based slippage")

        market_depth = context.order_book.get_market_depth()

        # Validate order book
        self._validate_order_book(market_depth, context)

        # Determine market condition
        market_condition = self._assess_market_condition(market_depth, context)

        # Calculate slippage based on order type
        if context.order_type.lower() == "market":
            return self._calculate_market_order_slippage(market_depth, context, market_condition)
        elif context.order_type.lower() == "limit":
            return self._calculate_limit_order_slippage(market_depth, context, market_condition)
        else:
            # Default to market order calculation
            return self._calculate_market_order_slippage(market_depth, context, market_condition)

    def _validate_order_book(self, market_depth: MarketDepth, context: SlippageContext) -> None:
        """Validate order book data."""
        if not market_depth.bids or not market_depth.asks:
            raise InvalidOrderBookError("Order book missing bid or ask data")

        if market_depth.best_bid is None or market_depth.best_ask is None:
            raise InvalidOrderBookError("Invalid bid/ask prices")

        if market_depth.best_bid >= market_depth.best_ask:
            raise InvalidOrderBookError("Crossed order book (bid >= ask)")

        # Check for reasonable spread
        spread_bps = market_depth.spread_bps
        if spread_bps and spread_bps > 5000:  # More than 50% spread
            raise InvalidOrderBookError(f"Unreasonably wide spread: {spread_bps:.2f} bps")

    def _assess_market_condition(
        self, market_depth: MarketDepth, context: SlippageContext
    ) -> MarketCondition:
        """Assess current market condition based on order book and context."""
        spread_bps = market_depth.spread_bps or 0.0

        # Calculate liquidity metrics
        total_bid_liquidity = sum(level.quantity for level in market_depth.bids[:5])
        total_ask_liquidity = sum(level.quantity for level in market_depth.asks[:5])
        avg_liquidity = (total_bid_liquidity + total_ask_liquidity) / 2.0

        # Use volatility if available
        volatility = context.volatility or 0.02  # Default 2% volatility

        # Classify market condition
        if spread_bps > 100 or volatility > 0.05 or avg_liquidity < context.quantity * 0.5:
            return MarketCondition.STRESSED
        elif spread_bps > 50 or volatility > 0.03 or avg_liquidity < context.quantity:
            return MarketCondition.ILLIQUID
        elif spread_bps > 20 or volatility > 0.02:
            return MarketCondition.VOLATILE
        elif spread_bps < 5 and volatility < 0.01:
            return MarketCondition.CALM
        else:
            return MarketCondition.NORMAL

    def _calculate_market_order_slippage(
        self, market_depth: MarketDepth, context: SlippageContext, market_condition: MarketCondition
    ) -> SlippageResult:
        """Calculate slippage for market orders."""
        try:
            # Simulate order fill
            average_price, slippage_bps = market_depth.simulate_order_fill(
                context.side, context.quantity
            )

            # Apply market condition adjustments
            slippage_bps = self._apply_market_condition_adjustment(slippage_bps, market_condition)

            # Cap slippage to maximum
            slippage_bps = min(slippage_bps, self.max_slippage_bps)

            # Calculate slippage in USD
            reference_price = (
                market_depth.best_ask if context.side == "buy" else market_depth.best_bid
            )
            slippage_usd = abs(average_price - reference_price) * context.quantity

            # Calculate liquidity metrics
            liquidity_used, depth_levels_used = self._calculate_liquidity_metrics(
                market_depth, context.side, context.quantity
            )

            return SlippageResult(
                slippage_bps=slippage_bps,
                slippage_usd=slippage_usd,
                effective_price=average_price,
                reference_price=reference_price,
                slippage_type=SlippageType.DEPTH_BASED,
                market_condition=market_condition,
                liquidity_used=liquidity_used,
                depth_levels_used=depth_levels_used,
                fill_quantity=context.quantity,
                unfilled_quantity=0.0,
                partial_fill=False,
            )

        except Exception as e:
            raise InsufficientLiquidityError(f"Insufficient liquidity for order: {e}")

    def _calculate_limit_order_slippage(
        self, market_depth: MarketDepth, context: SlippageContext, market_condition: MarketCondition
    ) -> SlippageResult:
        """Calculate slippage for limit orders."""
        if not context.limit_price:
            # Treat as market order if no limit price
            return self._calculate_market_order_slippage(market_depth, context, market_condition)

        reference_price = market_depth.best_ask if context.side == "buy" else market_depth.best_bid

        # Check if limit order would execute immediately
        if context.side == "buy" and context.limit_price >= market_depth.best_ask:
            # Limit buy at or above ask - immediate execution
            return SlippageResult(
                slippage_bps=0.0,
                slippage_usd=0.0,
                effective_price=market_depth.best_ask,
                reference_price=context.limit_price,
                slippage_type=SlippageType.DEPTH_BASED,
                market_condition=market_condition,
                fill_quantity=context.quantity,
                unfilled_quantity=0.0,
                partial_fill=False,
            )
        elif context.side == "sell" and context.limit_price <= market_depth.best_bid:
            # Limit sell at or below bid - immediate execution
            return SlippageResult(
                slippage_bps=0.0,
                slippage_usd=0.0,
                effective_price=market_depth.best_bid,
                reference_price=context.limit_price,
                slippage_type=SlippageType.DEPTH_BASED,
                market_condition=market_condition,
                fill_quantity=context.quantity,
                unfilled_quantity=0.0,
                partial_fill=False,
            )
        else:
            # Limit order would not execute immediately
            # Estimate slippage based on market movement probability
            spread_bps = market_depth.spread_bps or 0.0
            estimated_slippage = spread_bps * 0.5  # Conservative estimate

            return SlippageResult(
                slippage_bps=estimated_slippage,
                slippage_usd=0.0,  # No immediate execution
                effective_price=context.limit_price,
                reference_price=reference_price,
                slippage_type=SlippageType.DEPTH_BASED,
                market_condition=market_condition,
                fill_quantity=0.0,  # No immediate fill
                unfilled_quantity=context.quantity,
                partial_fill=False,
            )

    def _apply_market_condition_adjustment(
        self, slippage_bps: float, market_condition: MarketCondition
    ) -> float:
        """Apply market condition adjustments to slippage."""
        adjustments = {
            MarketCondition.CALM: 0.8,  # 20% reduction in calm markets
            MarketCondition.NORMAL: 1.0,  # No adjustment
            MarketCondition.VOLATILE: 1.3,  # 30% increase in volatile markets
            MarketCondition.ILLIQUID: 1.8,  # 80% increase in illiquid markets
            MarketCondition.STRESSED: 2.5,  # 150% increase in stressed markets
        }

        return slippage_bps * adjustments.get(market_condition, 1.0)

    def _calculate_liquidity_metrics(
        self, market_depth: MarketDepth, side: str, quantity: float
    ) -> Tuple[float, int]:
        """Calculate liquidity usage metrics."""
        levels = market_depth.asks if side == "buy" else market_depth.bids

        remaining_quantity = quantity
        liquidity_used = 0.0
        depth_levels_used = 0

        for level in levels:
            if remaining_quantity <= 0:
                break

            fill_quantity = min(remaining_quantity, level.quantity)
            liquidity_used += fill_quantity
            remaining_quantity -= fill_quantity
            depth_levels_used += 1

        return liquidity_used, depth_levels_used

    def estimate_liquidity_impact(
        self, market_depth: MarketDepth, side: str, quantity: float
    ) -> float:
        """Estimate the liquidity impact of an order."""
        levels = market_depth.asks if side == "buy" else market_depth.bids

        # Calculate total liquidity in first few levels
        total_liquidity = sum(level.quantity for level in levels[:5])

        if total_liquidity == 0:
            return 1.0  # Maximum impact if no liquidity

        # Impact is the ratio of order size to available liquidity
        impact_ratio = quantity / total_liquidity

        # Apply logarithmic scaling to prevent extreme values
        return min(impact_ratio, 1.0)

    def get_optimal_order_size(
        self, market_depth: MarketDepth, side: str, max_slippage_bps: float
    ) -> float:
        """Calculate optimal order size for a given maximum slippage."""
        levels = market_depth.asks if side == "buy" else market_depth.bids

        total_quantity = 0.0
        cumulative_cost = 0.0

        for level in levels:
            level_cost = level.quantity * level.price
            cumulative_cost += level_cost
            total_quantity += level.quantity

            # Calculate average price so far
            average_price = cumulative_cost / total_quantity

            # Calculate slippage
            reference_price = market_depth.best_ask if side == "buy" else market_depth.best_bid
            if side == "buy":
                slippage_bps = ((average_price - reference_price) / reference_price) * 10000
            else:
                slippage_bps = ((reference_price - average_price) / reference_price) * 10000

            if slippage_bps > max_slippage_bps:
                break

        return total_quantity
