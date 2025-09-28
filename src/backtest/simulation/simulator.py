"""
Trading simulation engine.
"""

import os
from typing import Any, Dict, List, Optional

from src.decision import compute_confidence, recommend_action
from src.indicators.core import atr as atr_series
from src.indicators.core import ema as ema_series
from src.indicators.core import rsi as rsi_series
from src.risk import ATRRiskParams, compute_stop_levels, compute_stop_levels_atr

from .metrics import MetricsCalculator
from .models import BacktestResult, Trade


class TradingSimulator:
    """Simulates trading strategies on historical data."""

    def __init__(self):
        self.metrics_calculator = MetricsCalculator()

    def simulate_on_series(
        self,
        closes: List[float],
        highs: List[float],
        lows: List[float],
        times: List[int],
        ema_fast: int = 20,
        ema_slow: int = 50,
        rsi_period: int = 14,
        threshold: float = 0.0,
        auto_threshold: float = 0.8,
        auto_threshold_bear: float = None,
        use_regime_filter: bool = False,
        vol_min_atr_pct: Optional[float] = None,
        vol_max_atr_pct: Optional[float] = None,
        atr_params: Optional[ATRRiskParams] = None,
        risk_budget_pct: float = 0.005,
        fee_bps: int = 10,
        timeframe: str = "1d",
    ) -> BacktestResult:
        """Simulate trading on a price series."""
        try:
            if auto_threshold_bear is None:
                auto_threshold_bear = auto_threshold

            # Calculate indicators
            rsi_vals = rsi_series(closes, rsi_period)
            ema_fast_vals = ema_series(closes, ema_fast)
            ema_slow_vals = ema_series(closes, ema_slow)
            atr_vals = atr_series(highs, lows, closes, atr_params.atr_period if atr_params else 14)

            # Initialize tracking variables
            trades: List[Trade] = []
            equity = [10000.0]  # Starting equity
            current_position = None
            cash = 10000.0

            # Process each bar
            for i in range(len(closes)):
                if i < max(ema_slow, rsi_period, (atr_params.atr_period if atr_params else 14)):
                    equity.append(cash)
                    continue

                current_price = closes[i]
                rsi_val = rsi_vals[i] if i < len(rsi_vals) else None
                ema_fast_val = ema_fast_vals[i] if i < len(ema_fast_vals) else None
                ema_slow_val = ema_slow_vals[i] if i < len(ema_slow_vals) else None
                atr_val = atr_vals[i] if i < len(atr_vals) else None

                # Calculate confidence
                confidence = compute_confidence(
                    current_price, threshold, rsi_val, ema_fast_val, ema_slow_val
                )

                # Regime filter
                regime_ok = True
                if use_regime_filter and ema_fast_val is not None and ema_slow_val is not None:
                    regime_ok = ema_fast_val > ema_slow_val

                # Volatility gate
                vol_ok = True
                if atr_val is not None and current_price > 0:
                    atr_pct = (atr_val / current_price) * 100.0
                    if vol_min_atr_pct is not None and atr_pct < vol_min_atr_pct:
                        vol_ok = False
                    if vol_max_atr_pct is not None and atr_pct > vol_max_atr_pct:
                        vol_ok = False

                # Get trading signal
                signal, action, reason = recommend_action(
                    current_price, threshold, rsi_val, confidence, auto_threshold
                )

                # Check if we should take action
                should_buy = (
                    action == "Buy"
                    and confidence >= auto_threshold
                    and regime_ok
                    and vol_ok
                    and current_position is None
                )

                should_sell = action == "Sell" and current_position is not None

                # Execute buy
                if should_buy:
                    # Calculate position size
                    position_value = cash * risk_budget_pct
                    units = position_value / current_price

                    # Apply fees
                    fee = position_value * (fee_bps / 10000.0)
                    actual_investment = position_value + fee

                    if actual_investment <= cash:
                        current_position = Trade(
                            entry_idx=i, entry_price=current_price, reason=reason
                        )
                        cash -= actual_investment

                # Execute sell
                elif should_sell and current_position is not None:
                    # Calculate exit value
                    exit_value = (
                        current_position.units * current_price
                        if hasattr(current_position, "units")
                        else 0
                    )
                    fee = exit_value * (fee_bps / 10000.0)
                    net_proceeds = exit_value - fee

                    current_position.exit_idx = i
                    current_position.exit_price = current_price
                    current_position.reason = reason

                    cash += net_proceeds
                    trades.append(current_position)
                    current_position = None

                # Check stop loss and take profit for current position
                if current_position is not None:
                    should_exit = self._check_exit_conditions(
                        current_position, current_price, atr_val, atr_params
                    )

                    if should_exit:
                        exit_value = (
                            current_position.units * current_price
                            if hasattr(current_position, "units")
                            else 0
                        )
                        fee = exit_value * (fee_bps / 10000.0)
                        net_proceeds = exit_value - fee

                        current_position.exit_idx = i
                        current_position.exit_price = current_price
                        current_position.reason = "stop_loss_or_take_profit"

                        cash += net_proceeds
                        trades.append(current_position)
                        current_position = None

                # Calculate current equity
                position_value = 0.0
                if current_position is not None:
                    position_value = (
                        current_position.units * current_price
                        if hasattr(current_position, "units")
                        else 0
                    )

                current_equity = cash + position_value
                equity.append(current_equity)

            # Close any remaining position
            if current_position is not None:
                final_price = closes[-1]
                exit_value = (
                    current_position.units * final_price
                    if hasattr(current_position, "units")
                    else 0
                )
                fee = exit_value * (fee_bps / 10000.0)
                net_proceeds = exit_value - fee

                current_position.exit_idx = len(closes) - 1
                current_position.exit_price = final_price
                current_position.reason = "end_of_data"

                trades.append(current_position)

            # Calculate metrics
            metrics = self.metrics_calculator.calculate_all_metrics(trades, equity, timeframe)

            return BacktestResult(
                trades=trades,
                equity=equity,
                win_rate=metrics["win_rate"],
                profit_factor=metrics["profit_factor"],
                max_drawdown=metrics["max_drawdown"],
                cagr=metrics["cagr"],
                mar=metrics["mar"],
                avg_return_pct=metrics["avg_return_pct"],
            )

        except Exception as ex:
            print(f"Simulation failed: {ex}")
            return BacktestResult(
                trades=[],
                equity=[10000.0],
                win_rate=0.0,
                profit_factor=0.0,
                max_drawdown=100.0,
                cagr=-100.0,
                mar=0.0,
                avg_return_pct=0.0,
            )

    def _check_exit_conditions(
        self,
        position: Trade,
        current_price: float,
        atr_val: Optional[float],
        atr_params: Optional[ATRRiskParams],
    ) -> bool:
        """Check if position should be exited due to stop loss or take profit."""
        try:
            # Calculate stop loss and take profit levels
            if atr_params and atr_val is not None and atr_val > 0:
                sl_level, tp_level = compute_stop_levels_atr(current_price, atr_val, atr_params)
            else:
                # Default percentage-based levels
                sl_level, tp_level = compute_stop_levels(current_price, None)

            if sl_level is None or tp_level is None:
                return False

            # Check stop loss
            if current_price <= sl_level:
                return True

            # Check take profit
            if current_price >= tp_level:
                return True

            return False

        except Exception:
            return False
