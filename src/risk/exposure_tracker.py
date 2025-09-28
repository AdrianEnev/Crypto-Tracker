"""
Portfolio exposure tracking and management.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

from .models import ExposureMetrics, RiskViolation, RiskViolationType, RiskLevel


@dataclass
class PositionInfo:
    """Information about a position for exposure calculation."""

    symbol: str
    units: float
    entry_price: float
    current_price: float
    market_value: float
    leverage: float = 1.0
    is_perpetual: bool = False
    funding_rate: float = 0.0


class ExposureTracker:
    """Tracks portfolio exposure and enforces exposure limits."""

    def __init__(self, config_manager, portfolio_manager):
        self.config_manager = config_manager
        self.portfolio_manager = portfolio_manager
        self.correlation_matrix: Dict[str, Dict[str, float]] = {}
        self.asset_categories: Dict[str, List[str]] = {}
        self._load_configuration()

    def _load_configuration(self):
        """Load exposure tracking configuration."""
        try:
            robust_risk_config = self.config_manager.load_full_config().get("robust_risk", {})
            self.correlation_matrix = robust_risk_config.get("correlation_matrix", {})
            self.asset_categories = robust_risk_config.get("asset_categories", {})
        except Exception:
            self.correlation_matrix = {}
            self.asset_categories = {}

    def calculate_exposure_metrics(
        self, sym_to_price: Dict[str, float], total_equity: float
    ) -> ExposureMetrics:
        """Calculate comprehensive exposure metrics."""
        try:
            metrics = ExposureMetrics()

            # Get current positions
            positions = self._get_position_info(sym_to_price)

            if not positions:
                return metrics

            # Calculate total exposure
            total_market_value = sum(pos.market_value for pos in positions)
            metrics.total_exposure_usd = total_market_value
            metrics.total_exposure_pct = (
                (total_market_value / total_equity * 100.0) if total_equity > 0 else 0.0
            )

            # Calculate per-coin exposure
            for pos in positions:
                coin_exposure_usd = pos.market_value
                coin_exposure_pct = (
                    (coin_exposure_usd / total_equity * 100.0) if total_equity > 0 else 0.0
                )

                metrics.per_coin_exposure[pos.symbol] = coin_exposure_usd
                metrics.per_coin_exposure_pct[pos.symbol] = coin_exposure_pct

            # Calculate correlation exposure
            metrics.correlation_exposure = self._calculate_correlation_exposure(
                positions, total_equity
            )

            # Calculate leverage and margin utilization
            metrics.leverage_utilization = self._calculate_leverage_utilization(
                positions, total_equity
            )
            metrics.margin_utilization = self._calculate_margin_utilization(positions, total_equity)

            # Calculate funding rate costs
            metrics.funding_rate_cost_daily = self._calculate_funding_rate_costs(positions)

            return metrics

        except Exception as e:
            # Return empty metrics on error
            return ExposureMetrics()

    def _get_position_info(self, sym_to_price: Dict[str, float]) -> List[PositionInfo]:
        """Get position information for exposure calculation."""
        positions = []

        try:
            for symbol, position in self.portfolio_manager.portfolio.positions.items():
                current_price = sym_to_price.get(symbol)
                if current_price is None:
                    continue

                market_value = position.units * current_price

                # TODO: Get actual leverage and funding rate from exchange/order data
                # For now, assume spot trading (leverage = 1.0)
                leverage = 1.0
                is_perpetual = False
                funding_rate = 0.0

                pos_info = PositionInfo(
                    symbol=symbol,
                    units=position.units,
                    entry_price=position.entry_price,
                    current_price=current_price,
                    market_value=market_value,
                    leverage=leverage,
                    is_perpetual=is_perpetual,
                    funding_rate=funding_rate,
                )
                positions.append(pos_info)

        except Exception:
            pass

        return positions

    def _calculate_correlation_exposure(
        self, positions: List[PositionInfo], total_equity: float
    ) -> Dict[str, float]:
        """Calculate exposure to correlated assets."""
        correlation_exposure = {}

        try:
            # Group positions by correlation
            for pos in positions:
                symbol = pos.symbol
                correlated_symbols = self.correlation_matrix.get(symbol, {})

                if correlated_symbols:
                    # Find positions in correlated assets
                    correlated_exposure = 0.0
                    for correlated_symbol, correlation in correlated_symbols.items():
                        if correlation > 0.5:  # Only consider significant correlations
                            for other_pos in positions:
                                if other_pos.symbol == correlated_symbol:
                                    correlated_exposure += other_pos.market_value * correlation

                    if correlated_exposure > 0:
                        correlation_exposure[symbol] = (
                            (correlated_exposure / total_equity * 100.0)
                            if total_equity > 0
                            else 0.0
                        )

        except Exception:
            pass

        return correlation_exposure

    def _calculate_leverage_utilization(
        self, positions: List[PositionInfo], total_equity: float
    ) -> float:
        """Calculate total leverage utilization."""
        try:
            if not positions or total_equity <= 0:
                return 0.0

            total_leveraged_value = sum(pos.market_value * pos.leverage for pos in positions)
            return (total_leveraged_value / total_equity) if total_equity > 0 else 0.0

        except Exception:
            return 0.0

    def _calculate_margin_utilization(
        self, positions: List[PositionInfo], total_equity: float
    ) -> float:
        """Calculate margin utilization for leveraged positions."""
        try:
            if not positions or total_equity <= 0:
                return 0.0

            total_margin_required = 0.0
            for pos in positions:
                if pos.leverage > 1.0:
                    margin_required = pos.market_value / pos.leverage
                    total_margin_required += margin_required

            return (total_margin_required / total_equity * 100.0) if total_equity > 0 else 0.0

        except Exception:
            return 0.0

    def _calculate_funding_rate_costs(self, positions: List[PositionInfo]) -> float:
        """Calculate daily funding rate costs."""
        try:
            total_daily_cost = 0.0

            for pos in positions:
                if pos.is_perpetual and pos.funding_rate != 0.0:
                    # Funding rate is typically charged every 8 hours (3 times per day)
                    daily_cost = pos.market_value * pos.funding_rate * 3.0
                    total_daily_cost += daily_cost

            return total_daily_cost

        except Exception:
            return 0.0

    def check_exposure_limits(
        self, metrics: ExposureMetrics, limits: Dict[str, float]
    ) -> List[RiskViolation]:
        """Check exposure against limits and return violations."""
        violations = []
        timestamp = datetime.now(timezone.utc)

        try:
            # Check total exposure limit
            max_total_exposure_pct = limits.get("max_total_exposure_pct", 80.0)
            if metrics.total_exposure_pct > max_total_exposure_pct:
                violation = RiskViolation(
                    violation_type=RiskViolationType.PORTFOLIO_EXPOSURE_EXCEEDED,
                    severity=RiskLevel.HIGH,
                    message=f"Total exposure {metrics.total_exposure_pct:.2f}% exceeds limit {max_total_exposure_pct}%",
                    current_value=metrics.total_exposure_pct,
                    limit_value=max_total_exposure_pct,
                    timestamp=timestamp,
                )
                violations.append(violation)

            # Check per-coin exposure limits
            max_per_coin_exposure_pct = limits.get("max_exposure_per_coin_pct", 15.0)
            for symbol, exposure_pct in metrics.per_coin_exposure_pct.items():
                if exposure_pct > max_per_coin_exposure_pct:
                    violation = RiskViolation(
                        violation_type=RiskViolationType.PER_COIN_EXPOSURE_EXCEEDED,
                        severity=RiskLevel.MEDIUM,
                        message=f"Exposure to {symbol} {exposure_pct:.2f}% exceeds limit {max_per_coin_exposure_pct}%",
                        current_value=exposure_pct,
                        limit_value=max_per_coin_exposure_pct,
                        timestamp=timestamp,
                        symbol=symbol,
                    )
                    violations.append(violation)

            # Check correlation exposure limits
            max_correlation_exposure_pct = limits.get("max_correlation_exposure_pct", 25.0)
            for symbol, correlation_exposure in metrics.correlation_exposure.items():
                if correlation_exposure > max_correlation_exposure_pct:
                    violation = RiskViolation(
                        violation_type=RiskViolationType.CORRELATION_EXPOSURE_EXCEEDED,
                        severity=RiskLevel.MEDIUM,
                        message=f"Correlated exposure for {symbol} {correlation_exposure:.2f}% exceeds limit {max_correlation_exposure_pct}%",
                        current_value=correlation_exposure,
                        limit_value=max_correlation_exposure_pct,
                        timestamp=timestamp,
                        symbol=symbol,
                    )
                    violations.append(violation)

            # Check leverage limits
            max_leverage = limits.get("max_leverage", 3.0)
            if metrics.leverage_utilization > max_leverage:
                violation = RiskViolation(
                    violation_type=RiskViolationType.LEVERAGE_EXCEEDED,
                    severity=RiskLevel.HIGH,
                    message=f"Leverage utilization {metrics.leverage_utilization:.2f}x exceeds limit {max_leverage}x",
                    current_value=metrics.leverage_utilization,
                    limit_value=max_leverage,
                    timestamp=timestamp,
                )
                violations.append(violation)

            # Check margin utilization limits
            max_margin_utilization_pct = limits.get("max_margin_utilization_pct", 75.0)
            if metrics.margin_utilization > max_margin_utilization_pct:
                violation = RiskViolation(
                    violation_type=RiskViolationType.MARGIN_UTILIZATION_EXCEEDED,
                    severity=RiskLevel.HIGH,
                    message=f"Margin utilization {metrics.margin_utilization:.2f}% exceeds limit {max_margin_utilization_pct}%",
                    current_value=metrics.margin_utilization,
                    limit_value=max_margin_utilization_pct,
                    timestamp=timestamp,
                )
                violations.append(violation)

            # Check funding rate cost limits
            max_funding_rate_cost_daily = limits.get("funding_rate_cost_limit_daily", 0.005)
            if metrics.funding_rate_cost_daily > max_funding_rate_cost_daily:
                violation = RiskViolation(
                    violation_type=RiskViolationType.FUNDING_RATE_EXPOSURE_EXCEEDED,
                    severity=RiskLevel.MEDIUM,
                    message=f"Daily funding rate cost {metrics.funding_rate_cost_daily:.4f} exceeds limit {max_funding_rate_cost_daily:.4f}",
                    current_value=metrics.funding_rate_cost_daily,
                    limit_value=max_funding_rate_cost_daily,
                    timestamp=timestamp,
                )
                violations.append(violation)

        except Exception:
            pass

        return violations

    def get_exposure_warnings(
        self, metrics: ExposureMetrics, warning_thresholds: Dict[str, float]
    ) -> List[str]:
        """Get exposure warnings based on warning thresholds."""
        warnings = []

        try:
            # Total exposure warning
            exposure_warning_pct = warning_thresholds.get("exposure_warning_pct", 70.0)
            if metrics.total_exposure_pct > exposure_warning_pct:
                warnings.append(
                    f"Total exposure {metrics.total_exposure_pct:.2f}% approaching limit"
                )

            # Per-coin exposure warnings
            for symbol, exposure_pct in metrics.per_coin_exposure_pct.items():
                if exposure_pct > exposure_warning_pct * 0.8:  # 80% of warning threshold
                    warnings.append(f"Exposure to {symbol} {exposure_pct:.2f}% approaching limit")

            # Leverage warning
            leverage_warning_pct = warning_thresholds.get("leverage_warning_pct", 80.0)
            if metrics.leverage_utilization > leverage_warning_pct:
                warnings.append(
                    f"Leverage utilization {metrics.leverage_utilization:.2f}x approaching limit"
                )

        except Exception:
            pass

        return warnings
