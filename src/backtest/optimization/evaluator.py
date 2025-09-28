"""
Parameter evaluation for backtest optimization.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Tuple
import os

from ..engine import simulate_on_series, ATRRiskParams


@dataclass
class EvalResult:
    """Result of parameter evaluation."""
    params: Dict[str, float]
    trades: int
    win_rate: float
    profit_factor: float
    max_drawdown: float
    cagr: float
    mar: float
    avg_return_pct: float


class ParameterEvaluator:
    """Evaluates parameter combinations for optimization."""
    
    def __init__(self, config_loader):
        self.config_loader = config_loader
    
    def evaluate_parameters(self, 
                           coin_id: str,
                           closes: List[float],
                           highs: List[float], 
                           lows: List[float],
                           times: List[int],
                           params: Dict[str, float],
                           timeframe: str,
                           use_price_as_threshold: bool = False,
                           disable_regime_filter: bool = False,
                           disable_vol_gate: bool = False) -> EvalResult:
        """Evaluate a parameter combination."""
        try:
            cfg_all = self.config_loader.load_config()
            
            # Extract parameters
            ind_cfg = cfg_all.get("indicators", {})
            ema_fast = int(params.get("ema_fast", ind_cfg.get("ema_fast", 20)))
            ema_slow = int(params.get("ema_slow", ind_cfg.get("ema_slow", 50)))
            rsi_p = int(params.get("rsi", ind_cfg.get("rsi_period", 14)))
            
            # Strategy settings
            strat = cfg_all.get("strategy", {})
            use_regime_filter = bool(strat.get("use_regime_filter", False))
            if disable_regime_filter:
                use_regime_filter = False
            
            # Volatility gate
            vg = strat.get("vol_gate", {})
            vol_min = float(vg.get("min_atr_pct", 0.0)) if vg.get("min_atr_pct") is not None else None
            vol_max = float(vg.get("max_atr_pct", 0.0)) if vg.get("max_atr_pct") is not None else None
            if disable_vol_gate:
                vol_min = None
                vol_max = None
            
            # Decision thresholds
            decision = cfg_all.get("decision", {})
            thr = decision.get("confidence_thresholds", {})
            auto_thr = float(thr.get("auto", 0.8))
            auto_thr_bear = thr.get("auto_bear")
            auto_thr_bear = float(auto_thr_bear) if auto_thr_bear is not None else None
            
            # ATR parameters
            risk_cfg2 = cfg_all.get("risk", {})
            atr_cfg = risk_cfg2.get("atr", {})
            atr_params = ATRRiskParams(
                atr_period=int(atr_cfg.get("period", 14)),
                sl_mult=float(params.get("sl_mult", atr_cfg.get("sl_mult", 1.5))),
                tp_mult=float(params.get("tp_mult", atr_cfg.get("tp_mult", 3.0))),
                trail_mult=float(atr_cfg.get("trail_mult", 2.0)),
            )
            
            # Risk budget
            risk_budget_pct = float(params.get("risk_budget_pct", 0.0))
            
            # Threshold selection
            if use_price_as_threshold:
                threshold_val = float(sorted(closes)[len(closes)//2]) if closes else 0.0
            else:
                tracked = cfg_all.get("tracked_coins", {})
                threshold_val = float((tracked.get(coin_id) or {}).get("threshold", 0.0))
            
            # Fee/slippage configuration
            exe_cfg = cfg_all.get("execution", {})
            fee_bps = self._calculate_fee_bps(exe_cfg, risk_budget_pct)
            
            # Run simulation
            result = simulate_on_series(
                closes=closes,
                highs=highs,
                lows=lows,
                times=times,
                ema_fast=ema_fast,
                ema_slow=ema_slow,
                rsi_period=rsi_p,
                threshold=threshold_val,
                auto_threshold=auto_thr,
                auto_threshold_bear=auto_thr_bear,
                use_regime_filter=use_regime_filter,
                vol_min_atr_pct=vol_min,
                vol_max_atr_pct=vol_max,
                atr_params=atr_params,
                risk_budget_pct=risk_budget_pct,
                fee_bps=fee_bps,
                timeframe=timeframe
            )
            
            # Calculate metrics
            trades = len(result.trades)
            win_rate = self._calculate_win_rate(result.trades)
            profit_factor = self._calculate_profit_factor(result.trades)
            max_drawdown = self._calculate_max_drawdown(result.equity)
            cagr = self._calculate_cagr(result.equity, timeframe)
            mar = cagr / max_drawdown if max_drawdown > 0 else 0.0
            avg_return_pct = self._calculate_avg_return(result.trades)
            
            return EvalResult(
                params=params,
                trades=trades,
                win_rate=win_rate,
                profit_factor=profit_factor,
                max_drawdown=max_drawdown,
                cagr=cagr,
                mar=mar,
                avg_return_pct=avg_return_pct
            )
            
        except Exception as ex:
            print(f"  Evaluation failed for {coin_id}: {ex}")
            return EvalResult(
                params=params,
                trades=0,
                win_rate=0.0,
                profit_factor=0.0,
                max_drawdown=100.0,
                cagr=-100.0,
                mar=0.0,
                avg_return_pct=0.0
            )
    
    def _calculate_fee_bps(self, exe_cfg: Dict[str, Any], risk_budget_pct: float) -> int:
        """Calculate fee basis points based on configuration."""
        fee_bps = 5  # Default
        
        try:
            tiers = exe_cfg.get("fee_tiers") or []
            fee_tier_volume_usd = float(exe_cfg.get("fee_tier_volume_usd", 0.0))
            
            if isinstance(tiers, list):
                best = None
                for t in tiers:
                    try:
                        min_vol = float(t.get("min_volume_usd", 0.0))
                        max_vol = float(t.get("max_volume_usd", float('inf')))
                        fee = int(t.get("fee_bps", 10))
                        
                        if fee_tier_volume_usd >= min_vol and fee_tier_volume_usd < max_vol:
                            if best is None or fee < best:
                                best = fee
                    except Exception:
                        continue
                
                if best is not None:
                    fee_bps = best
            else:
                fee_bps = int(exe_cfg.get("fee_bps", 10))
                
        except Exception:
            fee_bps = 10
        
        return fee_bps
    
    def _calculate_win_rate(self, trades: List[Any]) -> float:
        """Calculate win rate from trades."""
        if not trades:
            return 0.0
        
        winning_trades = sum(1 for trade in trades if trade.pnl_pct() and trade.pnl_pct() > 0)
        return (winning_trades / len(trades)) * 100.0
    
    def _calculate_profit_factor(self, trades: List[Any]) -> float:
        """Calculate profit factor from trades."""
        if not trades:
            return 0.0
        
        gross_profit = sum(trade.pnl_pct() for trade in trades if trade.pnl_pct() and trade.pnl_pct() > 0)
        gross_loss = abs(sum(trade.pnl_pct() for trade in trades if trade.pnl_pct() and trade.pnl_pct() < 0))
        
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0
        
        return gross_profit / gross_loss
    
    def _calculate_max_drawdown(self, equity: List[float]) -> float:
        """Calculate maximum drawdown from equity curve."""
        if not equity:
            return 0.0
        
        peak = equity[0]
        max_dd = 0.0
        
        for value in equity:
            if value > peak:
                peak = value
            dd = (peak - value) / peak * 100.0
            max_dd = max(max_dd, dd)
        
        return max_dd
    
    def _calculate_cagr(self, equity: List[float], timeframe: str) -> float:
        """Calculate Compound Annual Growth Rate."""
        if len(equity) < 2:
            return 0.0
        
        initial = equity[0]
        final = equity[-1]
        
        if initial <= 0:
            return 0.0
        
        # Calculate years based on timeframe
        periods_per_year = {
            '1d': 365,
            '4h': 365 * 6,
            '1h': 365 * 24,
            '30m': 365 * 48,
            '15m': 365 * 96,
            '5m': 365 * 288
        }.get(timeframe, 365)
        
        years = len(equity) / periods_per_year
        
        if years <= 0:
            return 0.0
        
        return ((final / initial) ** (1.0 / years) - 1.0) * 100.0
    
    def _calculate_avg_return(self, trades: List[Any]) -> float:
        """Calculate average return per trade."""
        if not trades:
            return 0.0
        
        returns = [trade.pnl_pct() for trade in trades if trade.pnl_pct() is not None]
        if not returns:
            return 0.0
        
        return sum(returns) / len(returns)
