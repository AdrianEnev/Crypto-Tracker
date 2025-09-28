"""
Enhanced Trading Simulation Engine

Integrates advanced fee and slippage models for realistic backtesting
with detailed cost analysis and execution simulation.
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field

from .models import Trade, BacktestResult
from .metrics import MetricsCalculator
from ...indicators.core import rsi as rsi_series, ema as ema_series, atr as atr_series
from ...decision import compute_confidence, recommend_action
from ...risk import ATRRiskParams, compute_stop_levels_atr, compute_stop_levels

# Import our new fee and slippage models
from ...fees import BacktestFeeCalculator, FeeCalculationMode, OrderFeeContext
from ...slippage import BacktestSlippageCalculator, SlippageContext, SlippageType


@dataclass
class EnhancedTrade(Trade):
    """Enhanced trade model with detailed execution information."""
    # Additional execution details
    entry_fees_usd: float = 0.0
    exit_fees_usd: float = 0.0
    entry_slippage_bps: float = 0.0
    exit_slippage_bps: float = 0.0
    entry_effective_price: float = 0.0
    exit_effective_price: float = 0.0
    
    # Fee and slippage breakdown
    maker_fees_usd: float = 0.0
    taker_fees_usd: float = 0.0
    total_execution_costs_usd: float = 0.0
    
    # Execution metadata
    exchange: str = ""
    order_type: str = "market"
    is_maker_entry: bool = False
    is_maker_exit: bool = False
    
    @property
    def net_pnl_pct(self) -> Optional[float]:
        """Calculate net PnL percentage after all costs."""
        if self.exit_price is None or self.entry_price == 0:
            return None
        
        # Calculate gross PnL
        gross_pnl_pct = (self.exit_price / self.entry_price - 1.0) * 100.0
        
        # Subtract execution costs as percentage
        cost_pct = (self.total_execution_costs_usd / (self.entry_price * self.units)) * 100.0
        
        return gross_pnl_pct - cost_pct
    
    @property
    def total_cost_bps(self) -> float:
        """Calculate total execution costs in basis points."""
        if self.entry_price == 0 or self.units == 0:
            return 0.0
        
        trade_value = self.entry_price * self.units
        return (self.total_execution_costs_usd / trade_value) * 10000


@dataclass
class EnhancedBacktestResult(BacktestResult):
    """Enhanced backtest result with detailed cost analysis."""
    # Fee and slippage statistics
    total_fees_usd: float = 0.0
    total_slippage_usd: float = 0.0
    total_execution_costs_usd: float = 0.0
    
    # Detailed breakdowns
    avg_entry_fee_bps: float = 0.0
    avg_exit_fee_bps: float = 0.0
    avg_entry_slippage_bps: float = 0.0
    avg_exit_slippage_bps: float = 0.0
    
    # Execution quality metrics
    maker_ratio: float = 0.0  # Percentage of maker trades
    avg_fill_time_ms: float = 0.0  # Average fill time
    
    # Cost efficiency metrics
    cost_efficiency_score: float = 0.0  # Lower is better
    slippage_efficiency_score: float = 0.0  # Lower is better


class EnhancedTradingSimulator:
    """Enhanced trading simulator with realistic fee and slippage modeling."""
    
    def __init__(
        self,
        exchange: str = "binance",
        fee_mode: FeeCalculationMode = FeeCalculationMode.REALISTIC,
        slippage_model: SlippageType = SlippageType.DEPTH_BASED,
        monthly_volume_usd: float = 0.0
    ):
        self.exchange = exchange
        self.monthly_volume_usd = monthly_volume_usd
        
        # Initialize fee and slippage calculators
        self.fee_calculator = BacktestFeeCalculator(fee_mode)
        self.slippage_calculator = BacktestSlippageCalculator(slippage_model)
        
        # Initialize metrics calculator
        self.metrics_calculator = MetricsCalculator()
        
        # Track simulation statistics
        self.simulation_stats = {
            "total_trades": 0,
            "total_volume_usd": 0.0,
            "total_fees_usd": 0.0,
            "total_slippage_usd": 0.0
        }
    
    def simulate_on_series(
        self,
        closes: List[float],
        highs: List[float],
        lows: List[float],
        times: List[int],
        symbol: str = "BTC/USDT",
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
        timeframe: str = "1d",
        use_enhanced_costs: bool = True
    ) -> EnhancedBacktestResult:
        """Simulate trading with enhanced cost modeling."""
        try:
            if auto_threshold_bear is None:
                auto_threshold_bear = auto_threshold
            
            # Calculate indicators
            rsi_vals = rsi_series(closes, rsi_period)
            ema_fast_vals = ema_series(closes, ema_fast)
            ema_slow_vals = ema_series(closes, ema_slow)
            atr_vals = atr_series(highs, lows, closes, atr_params.atr_period if atr_params else 14)
            
            # Initialize tracking variables
            trades: List[EnhancedTrade] = []
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
                confidence = compute_confidence(current_price, threshold, rsi_val, ema_fast_val, ema_slow_val)
                
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
                should_buy = (action == "Buy" and 
                            confidence >= auto_threshold and 
                            regime_ok and 
                            vol_ok and 
                            current_position is None)
                
                should_sell = (action == "Sell" and current_position is not None)
                
                # Execute buy
                if should_buy:
                    trade = self._execute_buy_order(
                        i, current_price, cash, risk_budget_pct, symbol, reason, use_enhanced_costs
                    )
                    if trade:
                        current_position = trade
                        cash -= (trade.entry_effective_price * trade.units + trade.entry_fees_usd)
                
                # Execute sell
                elif should_sell and current_position is not None:
                    trade = self._execute_sell_order(
                        current_position, i, current_price, symbol, reason, use_enhanced_costs
                    )
                    if trade:
                        cash += (trade.exit_effective_price * trade.units - trade.exit_fees_usd)
                        trades.append(trade)
                        current_position = None
                
                # Check stop loss and take profit for current position
                if current_position is not None:
                    should_exit = self._check_exit_conditions(
                        current_position, current_price, atr_val, atr_params
                    )
                    
                    if should_exit:
                        trade = self._execute_sell_order(
                            current_position, i, current_price, symbol, "stop_loss_or_take_profit", use_enhanced_costs
                        )
                        if trade:
                            cash += (trade.exit_effective_price * trade.units - trade.exit_fees_usd)
                            trades.append(trade)
                            current_position = None
                
                # Calculate current equity
                position_value = 0.0
                if current_position is not None:
                    position_value = current_position.units * current_price
                
                current_equity = cash + position_value
                equity.append(current_equity)
            
            # Close any remaining position
            if current_position is not None:
                final_price = closes[-1]
                trade = self._execute_sell_order(
                    current_position, len(closes) - 1, final_price, symbol, "end_of_data", use_enhanced_costs
                )
                if trade:
                    trades.append(trade)
            
            # Calculate enhanced metrics
            enhanced_metrics = self._calculate_enhanced_metrics(trades, equity, timeframe)
            
            return EnhancedBacktestResult(
                trades=trades,
                equity=equity,
                win_rate=enhanced_metrics['win_rate'],
                profit_factor=enhanced_metrics['profit_factor'],
                max_drawdown=enhanced_metrics['max_drawdown'],
                cagr=enhanced_metrics['cagr'],
                mar=enhanced_metrics['mar'],
                avg_return_pct=enhanced_metrics['avg_return_pct'],
                total_fees_usd=enhanced_metrics['total_fees_usd'],
                total_slippage_usd=enhanced_metrics['total_slippage_usd'],
                total_execution_costs_usd=enhanced_metrics['total_execution_costs_usd'],
                avg_entry_fee_bps=enhanced_metrics['avg_entry_fee_bps'],
                avg_exit_fee_bps=enhanced_metrics['avg_exit_fee_bps'],
                avg_entry_slippage_bps=enhanced_metrics['avg_entry_slippage_bps'],
                avg_exit_slippage_bps=enhanced_metrics['avg_exit_slippage_bps'],
                maker_ratio=enhanced_metrics['maker_ratio'],
                cost_efficiency_score=enhanced_metrics['cost_efficiency_score'],
                slippage_efficiency_score=enhanced_metrics['slippage_efficiency_score']
            )
            
        except Exception as ex:
            print(f"Enhanced simulation failed: {ex}")
            return EnhancedBacktestResult(
                trades=[],
                equity=[10000.0],
                win_rate=0.0,
                profit_factor=0.0,
                max_drawdown=100.0,
                cagr=-100.0,
                mar=0.0,
                avg_return_pct=0.0
            )
    
    def _execute_buy_order(
        self, 
        bar_idx: int, 
        price: float, 
        available_cash: float, 
        risk_budget_pct: float,
        symbol: str,
        reason: str,
        use_enhanced_costs: bool
    ) -> Optional[EnhancedTrade]:
        """Execute a buy order with enhanced cost modeling."""
        try:
            # Calculate position size
            position_value = available_cash * risk_budget_pct
            if position_value <= 0:
                return None
            
            # For simplicity, assume market orders for now
            order_type = "market"
            is_maker = False
            
            if use_enhanced_costs:
                # Calculate fees
                fee_context = OrderFeeContext(
                    order_value_usd=position_value,
                    order_quantity=position_value / price,
                    order_price=price,
                    side="buy",
                    order_type=order_type,
                    is_maker=is_maker,
                    exchange=self.exchange,
                    symbol=symbol,
                    monthly_volume_usd=self.monthly_volume_usd
                )
                
                fee_breakdown = self.fee_calculator.calculate_fees_with_tracking(
                    fee_context, position_value
                )
                
                # Calculate slippage
                slippage_context = SlippageContext(
                    symbol=symbol,
                    side="buy",
                    quantity=position_value / price,
                    order_type=order_type,
                    timestamp=datetime.now(),
                    current_price=price,
                    volume_24h=None,  # Would need historical volume data
                    volatility=None   # Would need volatility calculation
                )
                
                slippage_result = self.slippage_calculator.calculate_slippage_with_tracking(
                    slippage_context, position_value, position_value / price
                )
                
                # Calculate effective prices and costs
                entry_effective_price = slippage_result.effective_price
                entry_fees_usd = fee_breakdown.total_fees_usd
                entry_slippage_bps = slippage_result.slippage_bps
                
                # Update simulation stats
                self.simulation_stats["total_volume_usd"] += position_value
                self.simulation_stats["total_fees_usd"] += entry_fees_usd
                self.simulation_stats["total_slippage_usd"] += slippage_result.slippage_usd
                
            else:
                # Use simple cost model
                entry_effective_price = price * 1.001  # 10 bps slippage
                entry_fees_usd = position_value * 0.0004  # 4 bps fees
                entry_slippage_bps = 10.0
            
            units = position_value / entry_effective_price
            
            return EnhancedTrade(
                entry_idx=bar_idx,
                entry_price=price,
                units=units,
                reason=reason,
                entry_fees_usd=entry_fees_usd,
                entry_slippage_bps=entry_slippage_bps,
                entry_effective_price=entry_effective_price,
                exchange=self.exchange,
                order_type=order_type,
                is_maker_entry=is_maker
            )
            
        except Exception as e:
            print(f"Buy order execution failed: {e}")
            return None
    
    def _execute_sell_order(
        self, 
        position: EnhancedTrade, 
        bar_idx: int, 
        price: float,
        symbol: str,
        reason: str,
        use_enhanced_costs: bool
    ) -> Optional[EnhancedTrade]:
        """Execute a sell order with enhanced cost modeling."""
        try:
            # For simplicity, assume market orders for now
            order_type = "market"
            is_maker = False
            
            if use_enhanced_costs:
                # Calculate fees
                exit_value = position.units * price
                fee_context = OrderFeeContext(
                    order_value_usd=exit_value,
                    order_quantity=position.units,
                    order_price=price,
                    side="sell",
                    order_type=order_type,
                    is_maker=is_maker,
                    exchange=self.exchange,
                    symbol=symbol,
                    monthly_volume_usd=self.monthly_volume_usd
                )
                
                fee_breakdown = self.fee_calculator.calculate_fees_with_tracking(
                    fee_context, exit_value
                )
                
                # Calculate slippage
                slippage_context = SlippageContext(
                    symbol=symbol,
                    side="sell",
                    quantity=position.units,
                    order_type=order_type,
                    timestamp=datetime.now(),
                    current_price=price,
                    volume_24h=None,  # Would need historical volume data
                    volatility=None   # Would need volatility calculation
                )
                
                slippage_result = self.slippage_calculator.calculate_slippage_with_tracking(
                    slippage_context, exit_value, position.units
                )
                
                # Calculate effective prices and costs
                exit_effective_price = slippage_result.effective_price
                exit_fees_usd = fee_breakdown.total_fees_usd
                exit_slippage_bps = slippage_result.slippage_bps
                
                # Update simulation stats
                self.simulation_stats["total_volume_usd"] += exit_value
                self.simulation_stats["total_fees_usd"] += exit_fees_usd
                self.simulation_stats["total_slippage_usd"] += slippage_result.slippage_usd
                
            else:
                # Use simple cost model
                exit_effective_price = price * 0.999  # 10 bps slippage
                exit_fees_usd = (position.units * price) * 0.0004  # 4 bps fees
                exit_slippage_bps = 10.0
            
            # Update position with exit information
            position.exit_idx = bar_idx
            position.exit_price = price
            position.reason = reason
            position.exit_fees_usd = exit_fees_usd
            position.exit_slippage_bps = exit_slippage_bps
            position.exit_effective_price = exit_effective_price
            position.is_maker_exit = is_maker
            
            # Calculate total execution costs
            position.total_execution_costs_usd = position.entry_fees_usd + position.exit_fees_usd
            
            # Calculate maker/taker breakdown
            if position.is_maker_entry:
                position.maker_fees_usd = position.entry_fees_usd
            else:
                position.taker_fees_usd = position.entry_fees_usd
            
            if position.is_maker_exit:
                position.maker_fees_usd += position.exit_fees_usd
            else:
                position.taker_fees_usd += position.exit_fees_usd
            
            self.simulation_stats["total_trades"] += 1
            
            return position
            
        except Exception as e:
            print(f"Sell order execution failed: {e}")
            return None
    
    def _check_exit_conditions(self, position: EnhancedTrade, current_price: float, atr_val: Optional[float], atr_params: Optional[ATRRiskParams]) -> bool:
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
    
    def _calculate_enhanced_metrics(self, trades: List[EnhancedTrade], equity: List[float], timeframe: str) -> Dict[str, float]:
        """Calculate enhanced metrics including cost analysis."""
        # Calculate basic metrics
        basic_metrics = self.metrics_calculator.calculate_all_metrics(trades, equity, timeframe)
        
        # Calculate enhanced metrics
        if not trades:
            return {
                **basic_metrics,
                'total_fees_usd': 0.0,
                'total_slippage_usd': 0.0,
                'total_execution_costs_usd': 0.0,
                'avg_entry_fee_bps': 0.0,
                'avg_exit_fee_bps': 0.0,
                'avg_entry_slippage_bps': 0.0,
                'avg_exit_slippage_bps': 0.0,
                'maker_ratio': 0.0,
                'cost_efficiency_score': 0.0,
                'slippage_efficiency_score': 0.0
            }
        
        # Calculate cost metrics
        total_fees_usd = sum(t.entry_fees_usd + t.exit_fees_usd for t in trades)
        total_slippage_usd = sum(
            (t.entry_slippage_bps / 10000.0) * t.entry_effective_price * t.units +
            (t.exit_slippage_bps / 10000.0) * t.exit_effective_price * t.units
            for t in trades
        )
        total_execution_costs_usd = total_fees_usd + total_slippage_usd
        
        # Calculate average costs
        avg_entry_fee_bps = sum(t.entry_fees_usd for t in trades) / len(trades) if trades else 0.0
        avg_exit_fee_bps = sum(t.exit_fees_usd for t in trades) / len(trades) if trades else 0.0
        avg_entry_slippage_bps = sum(t.entry_slippage_bps for t in trades) / len(trades) if trades else 0.0
        avg_exit_slippage_bps = sum(t.exit_slippage_bps for t in trades) / len(trades) if trades else 0.0
        
        # Calculate maker ratio
        maker_trades = sum(1 for t in trades if t.is_maker_entry or t.is_maker_exit)
        maker_ratio = (maker_trades / len(trades)) * 100.0 if trades else 0.0
        
        # Calculate efficiency scores
        total_volume = sum(t.entry_effective_price * t.units for t in trades)
        cost_efficiency_score = (total_execution_costs_usd / total_volume) * 100.0 if total_volume > 0 else 0.0
        slippage_efficiency_score = (total_slippage_usd / total_volume) * 100.0 if total_volume > 0 else 0.0
        
        return {
            **basic_metrics,
            'total_fees_usd': total_fees_usd,
            'total_slippage_usd': total_slippage_usd,
            'total_execution_costs_usd': total_execution_costs_usd,
            'avg_entry_fee_bps': avg_entry_fee_bps,
            'avg_exit_fee_bps': avg_exit_fee_bps,
            'avg_entry_slippage_bps': avg_entry_slippage_bps,
            'avg_exit_slippage_bps': avg_exit_slippage_bps,
            'maker_ratio': maker_ratio,
            'cost_efficiency_score': cost_efficiency_score,
            'slippage_efficiency_score': slippage_efficiency_score
        }
    
    def get_fee_statistics(self) -> Dict[str, any]:
        """Get detailed fee statistics from the fee calculator."""
        return self.fee_calculator.export_fee_report()
    
    def get_slippage_statistics(self) -> Dict[str, any]:
        """Get detailed slippage statistics from the slippage calculator."""
        return self.slippage_calculator.export_slippage_report()
    
    def get_simulation_statistics(self) -> Dict[str, any]:
        """Get overall simulation statistics."""
        return {
            **self.simulation_stats,
            "fee_stats": self.get_fee_statistics(),
            "slippage_stats": self.get_slippage_statistics()
        }
