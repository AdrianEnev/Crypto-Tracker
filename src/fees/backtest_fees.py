"""
Backtest-Specific Fee Calculator

Specialized fee calculator for backtesting scenarios with additional
features like historical fee tracking and strategy performance analysis.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from .calculator import FeeCalculator
from .models import FeeBreakdown, FeeCalculationMode, OrderFeeContext


@dataclass
class BacktestFeeStats:
    """Statistics for fee analysis during backtesting."""

    total_fees_usd: float = 0.0
    total_trading_fees_usd: float = 0.0
    total_withdrawal_fees_usd: float = 0.0
    total_deposit_fees_usd: float = 0.0

    # Fee breakdown by type
    maker_fees_usd: float = 0.0
    taker_fees_usd: float = 0.0

    # Fee breakdown by exchange
    fees_by_exchange: Dict[str, float] = field(default_factory=dict)

    # Volume and trade counts
    total_volume_usd: float = 0.0
    trade_count: int = 0
    maker_trade_count: int = 0
    taker_trade_count: int = 0

    # Fee rates
    avg_fee_bps: float = 0.0
    avg_maker_fee_bps: float = 0.0
    avg_taker_fee_bps: float = 0.0

    def add_trade(self, fee_breakdown: FeeBreakdown, trade_value_usd: float) -> None:
        """Add a trade to the statistics."""
        self.total_fees_usd += fee_breakdown.total_fees_usd
        self.total_trading_fees_usd += fee_breakdown.trading_fee_usd
        self.total_withdrawal_fees_usd += fee_breakdown.withdrawal_fee_usd
        self.total_deposit_fees_usd += fee_breakdown.deposit_fee_usd

        self.maker_fees_usd += fee_breakdown.maker_fee_usd
        self.taker_fees_usd += fee_breakdown.taker_fee_usd

        # Track by exchange
        if fee_breakdown.exchange not in self.fees_by_exchange:
            self.fees_by_exchange[fee_breakdown.exchange] = 0.0
        self.fees_by_exchange[fee_breakdown.exchange] += fee_breakdown.total_fees_usd

        self.total_volume_usd += trade_value_usd
        self.trade_count += 1

        if fee_breakdown.fee_type_used.value == "maker":
            self.maker_trade_count += 1
        else:
            self.taker_trade_count += 1

        # Update averages
        if self.total_volume_usd > 0:
            self.avg_fee_bps = (self.total_fees_usd / self.total_volume_usd) * 10000

        if self.maker_trade_count > 0:
            self.avg_maker_fee_bps = (
                self.maker_fees_usd
                / sum(
                    f.trading_fee_usd for f in self.fee_history if f.fee_type_used.value == "maker"
                )
            ) * 10000

        if self.taker_trade_count > 0:
            self.avg_taker_fee_bps = (
                self.taker_fees_usd
                / sum(
                    f.trading_fee_usd for f in self.fee_history if f.fee_type_used.value == "taker"
                )
            ) * 10000

    @property
    def fee_efficiency_score(self) -> float:
        """Calculate fee efficiency score (lower is better)."""
        if self.total_volume_usd == 0:
            return 0.0
        return self.total_fees_usd / self.total_volume_usd

    @property
    def maker_ratio(self) -> float:
        """Calculate ratio of maker trades."""
        if self.trade_count == 0:
            return 0.0
        return self.maker_trade_count / self.trade_count


class BacktestFeeCalculator(FeeCalculator):
    """Enhanced fee calculator for backtesting with statistics tracking."""

    def __init__(
        self,
        calculation_mode: FeeCalculationMode = FeeCalculationMode.REALISTIC,
        track_statistics: bool = True,
    ):
        super().__init__(calculation_mode)
        self.track_statistics = track_statistics
        self.fee_history: List[Tuple[datetime, FeeBreakdown, float]] = (
            []
        )  # (timestamp, fees, trade_value)
        self.stats = BacktestFeeStats()

    def calculate_fees_with_tracking(
        self, context: OrderFeeContext, trade_value_usd: float
    ) -> FeeBreakdown:
        """
        Calculate fees and track statistics for backtesting.

        Args:
            context: Order fee context
            trade_value_usd: Value of the trade for statistics

        Returns:
            FeeBreakdown with calculated fees
        """
        fee_breakdown = self.calculate_fees(context)

        if self.track_statistics:
            self.fee_history.append((datetime.now(), fee_breakdown, trade_value_usd))
            self.stats.add_trade(fee_breakdown, trade_value_usd)

        return fee_breakdown

    def get_fee_statistics(self) -> BacktestFeeStats:
        """Get current fee statistics."""
        return self.stats

    def get_fee_history(
        self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None
    ) -> List[Tuple[datetime, FeeBreakdown, float]]:
        """Get fee history within a time range."""
        if start_time is None and end_time is None:
            return self.fee_history.copy()

        filtered_history = []
        for timestamp, fee_breakdown, trade_value in self.fee_history:
            if start_time and timestamp < start_time:
                continue
            if end_time and timestamp > end_time:
                continue
            filtered_history.append((timestamp, fee_breakdown, trade_value))

        return filtered_history

    def get_fees_by_period(self, period_hours: int = 24) -> Dict[datetime, BacktestFeeStats]:
        """Get fee statistics grouped by time periods."""
        if not self.fee_history:
            return {}

        periods: Dict[datetime, BacktestFeeStats] = {}

        for timestamp, fee_breakdown, trade_value in self.fee_history:
            # Round timestamp to period boundary
            period_start = timestamp.replace(minute=0, second=0, microsecond=0) - timedelta(
                hours=timestamp.hour % period_hours
            )

            if period_start not in periods:
                periods[period_start] = BacktestFeeStats()

            periods[period_start].add_trade(fee_breakdown, trade_value)

        return periods

    def reset_statistics(self) -> None:
        """Reset all statistics and history."""
        self.fee_history.clear()
        self.stats = BacktestFeeStats()

    def export_fee_report(self) -> Dict[str, any]:
        """Export comprehensive fee report for analysis."""
        return {
            "summary": {
                "total_fees_usd": self.stats.total_fees_usd,
                "total_trading_fees_usd": self.stats.total_trading_fees_usd,
                "total_withdrawal_fees_usd": self.stats.total_withdrawal_fees_usd,
                "total_volume_usd": self.stats.total_volume_usd,
                "trade_count": self.stats.trade_count,
                "avg_fee_bps": self.stats.avg_fee_bps,
                "fee_efficiency_score": self.stats.fee_efficiency_score,
                "maker_ratio": self.stats.maker_ratio,
            },
            "breakdown": {
                "maker_fees_usd": self.stats.maker_fees_usd,
                "taker_fees_usd": self.stats.taker_fees_usd,
                "maker_trade_count": self.stats.maker_trade_count,
                "taker_trade_count": self.stats.taker_trade_count,
                "avg_maker_fee_bps": self.stats.avg_maker_fee_bps,
                "avg_taker_fee_bps": self.stats.avg_taker_fee_bps,
            },
            "by_exchange": self.stats.fees_by_exchange,
            "calculation_mode": self.calculation_mode.value,
            "supported_exchanges": self.get_supported_exchanges(),
        }

    def compare_exchanges(
        self, order_value_usd: float, symbol: str, side: str, order_type: str
    ) -> Dict[str, FeeBreakdown]:
        """Compare fees across different exchanges for the same order."""
        exchanges = self.get_supported_exchanges()
        comparison = {}

        for exchange in exchanges:
            try:
                context = OrderFeeContext(
                    order_value_usd=order_value_usd,
                    order_quantity=order_value_usd / 50000.0,  # Assume $50k price
                    order_price=50000.0,
                    side=side,
                    order_type=order_type,
                    is_maker=(order_type.lower() == "limit"),
                    exchange=exchange,
                    symbol=symbol,
                    monthly_volume_usd=0.0,
                )

                fees = self.calculate_fees(context)
                comparison[exchange] = fees

            except Exception as e:
                # Skip exchanges that don't support the symbol
                continue

        return comparison

    def optimize_for_maker_fees(
        self, target_volume_usd: float, symbol: str
    ) -> Dict[str, Dict[str, any]]:
        """Find the best exchanges for maker fees at different volume levels."""
        exchanges = self.get_supported_exchanges()
        optimization = {}

        for exchange in exchanges:
            exchange_fees = self.get_exchange_info(exchange)
            if not exchange_fees:
                continue

            tiers = exchange_fees["volume_tiers"]
            tier_analysis = []

            for tier in tiers:
                if tier["volume_usd"] <= target_volume_usd:
                    tier_analysis.append(
                        {
                            "volume_usd": tier["volume_usd"],
                            "maker_bps": tier["maker_bps"],
                            "taker_bps": tier["taker_bps"],
                            "description": tier["description"],
                            "savings_vs_taker": tier["taker_bps"] - tier["maker_bps"],
                        }
                    )

            if tier_analysis:
                optimization[exchange] = {
                    "best_tier": max(tier_analysis, key=lambda t: t["volume_usd"]),
                    "all_tiers": tier_analysis,
                }

        return optimization
