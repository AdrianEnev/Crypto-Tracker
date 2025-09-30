"""
Bitcoin Multi-Bucket Strategy
Implements core HODL allocation, tactical accumulation ladder, and momentum/mean-reversion overlay.
"""

import pandas as pd
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
import numpy as np

from .base import BaseStrategy
from ..indicators.core import ema, rsi, atr


class BitcoinMultiBucketStrategy(BaseStrategy):
    """
    Bitcoin-specific multi-bucket strategy implementing:
    1. Core HODL allocation (40-70% of crypto allocation)
    2. Tactical accumulation ladder on drawdowns
    3. Momentum + mean-reversion overlay
    4. Volatility-aware stops
    5. Cycle/macro awareness
    """
    
    def __init__(self, strategy_config: dict):
        super().__init__(strategy_config)
        
        # Core HODL allocation parameters
        self.core_allocation_pct = self.config.get("core_allocation_pct", 60.0)
        self.core_rebalance_threshold = self.config.get("core_rebalance_threshold", 10.0)
        
        # Tactical accumulation ladder
        self.dip_ladder_enabled = self.config.get("dip_ladder_enabled", True)
        self.dip_levels = self.config.get("dip_levels", [5.0, 10.0, 20.0, 35.0, 50.0])
        self.dip_weights = self.config.get("dip_weights", [0.4, 0.3, 0.2, 0.1, 0.0])
        self.exchange_flow_filter = self.config.get("exchange_flow_filter", True)
        
        # Momentum overlay
        self.momentum_enabled = self.config.get("momentum_enabled", True)
        self.momentum_ema_period = self.config.get("momentum_ema_period", 50)
        self.momentum_rsi_range = self.config.get("momentum_rsi_range", [40, 70])
        self.momentum_vol_slope_period = self.config.get("momentum_vol_slope_period", 30)
        
        # Mean reversion overlay
        self.mean_reversion_enabled = self.config.get("mean_reversion_enabled", True)
        self.mr_dip_threshold = self.config.get("mr_dip_threshold", [5.0, 12.0])
        self.mr_rsi_threshold = self.config.get("mr_rsi_threshold", 30)
        self.mr_profit_target = self.config.get("mr_profit_target", [5.0, 12.0])
        self.mr_stop_loss = self.config.get("mr_stop_loss", [8.0, 15.0])
        
        # Volatility-aware stops
        self.atr_period = self.config.get("atr_period", 14)
        self.atr_multiplier = self.config.get("atr_multiplier", 3.0)
        
        # Cycle/macro awareness
        self.halving_aware = self.config.get("halving_aware", True)
        self.macro_regime_filter = self.config.get("macro_regime_filter", True)
        
        # State tracking
        self.local_peaks = []  # Track local peaks for drawdown calculation
        self.core_allocation_current = 0.0
        self.last_rebalance_date = None
        
    def _calculate_local_peak(self, data: pd.DataFrame, window: int = 20) -> float:
        """Calculate local peak price for drawdown measurement."""
        try:
            closes = data["close"].tolist()
            if len(closes) < window:
                return closes[-1] if closes else 0.0
            
            # Use rolling maximum as local peak
            recent_closes = closes[-window:]
            return max(recent_closes)
        except Exception:
            return 0.0
    
    def _calculate_drawdown_from_peak(self, current_price: float, peak_price: float) -> float:
        """Calculate drawdown percentage from peak."""
        if peak_price <= 0:
            return 0.0
        return ((peak_price - current_price) / peak_price) * 100.0
    
    def _get_dip_ladder_signal(self, data: pd.DataFrame) -> Tuple[int, float]:
        """
        Generate dip ladder accumulation signal.
        Returns: (signal: -1/0/1, confidence: 0-1)
        """
        try:
            if not self.dip_ladder_enabled:
                return 0, 0.0
            
            closes = data["close"].tolist()
            if len(closes) < 20:
                return 0, 0.0
            
            current_price = closes[-1]
            peak_price = self._calculate_local_peak(data)
            drawdown = self._calculate_drawdown_from_peak(current_price, peak_price)
            
            # Check if drawdown matches any ladder level
            for i, level in enumerate(self.dip_levels):
                if abs(drawdown - level) < 1.0:  # Within 1% of ladder level
                    weight = self.dip_weights[i]
                    if weight > 0:
                        # Check exchange flow filter if enabled
                        if self.exchange_flow_filter:
                            # Placeholder: would check actual exchange flow data
                            exchange_flow_ok = True  # Assume OK for now
                        else:
                            exchange_flow_ok = True
                        
                        if exchange_flow_ok:
                            return 1, weight  # Buy signal with confidence = weight
            
            return 0, 0.0
            
        except Exception:
            return 0, 0.0
    
    def _get_momentum_signal(self, data: pd.DataFrame) -> Tuple[int, float]:
        """
        Generate momentum overlay signal.
        Returns: (signal: -1/0/1, confidence: 0-1)
        """
        try:
            if not self.momentum_enabled:
                return 0, 0.0
            
            closes = data["close"].tolist()
            if len(closes) < max(self.momentum_ema_period, self.momentum_vol_slope_period):
                return 0, 0.0
            
            current_price = closes[-1]
            
            # Calculate EMA
            ema_values = ema(closes, self.momentum_ema_period)
            if not ema_values or ema_values[-1] is None:
                return 0, 0.0
            
            current_ema = ema_values[-1]
            
            # Calculate RSI
            rsi_values = rsi(closes, 14)
            if not rsi_values or rsi_values[-1] is None:
                return 0, 0.0
            
            current_rsi = rsi_values[-1]
            
            # Calculate volatility slope
            vol_slope = self._calculate_volatility_slope(closes, self.momentum_vol_slope_period)
            
            # Momentum conditions
            price_above_ema = current_price > current_ema
            rsi_in_range = self.momentum_rsi_range[0] <= current_rsi <= self.momentum_rsi_range[1]
            positive_vol_slope = vol_slope > 0
            
            # Long-only momentum entry
            if price_above_ema and rsi_in_range and positive_vol_slope:
                confidence = 0.7  # High confidence for momentum
                return 1, confidence
            
            # Exit conditions
            if current_rsi > 80 or current_price < current_ema:
                return -1, 0.5  # Sell signal
            
            return 0, 0.0
            
        except Exception:
            return 0, 0.0
    
    def _get_mean_reversion_signal(self, data: pd.DataFrame) -> Tuple[int, float]:
        """
        Generate mean reversion signal.
        Returns: (signal: -1/0/1, confidence: 0-1)
        """
        try:
            if not self.mean_reversion_enabled:
                return 0, 0.0
            
            closes = data["close"].tolist()
            if len(closes) < 20:
                return 0, 0.0
            
            current_price = closes[-1]
            
            # Calculate intraday dip
            daily_high = max(closes[-24:]) if len(closes) >= 24 else max(closes)
            intraday_dip = ((daily_high - current_price) / daily_high) * 100.0
            
            # Calculate RSI
            rsi_values = rsi(closes, 14)
            if not rsi_values or rsi_values[-1] is None:
                return 0, 0.0
            
            current_rsi = rsi_values[-1]
            
            # Mean reversion conditions
            dip_in_range = self.mr_dip_threshold[0] <= intraday_dip <= self.mr_dip_threshold[1]
            rsi_oversold = current_rsi < self.mr_rsi_threshold
            
            if dip_in_range and rsi_oversold:
                confidence = 0.6  # Medium confidence for mean reversion
                return 1, confidence
            
            return 0, 0.0
            
        except Exception:
            return 0, 0.0
    
    def _calculate_volatility_slope(self, closes: List[float], period: int) -> float:
        """Calculate volatility slope over given period."""
        try:
            if len(closes) < period * 2:
                return 0.0
            
            # Calculate rolling volatility
            volatilities = []
            for i in range(period, len(closes)):
                period_closes = closes[i-period:i]
                vol = np.std(period_closes) / np.mean(period_closes)
                volatilities.append(vol)
            
            if len(volatilities) < 2:
                return 0.0
            
            # Calculate slope
            x = np.arange(len(volatilities))
            slope = np.polyfit(x, volatilities, 1)[0]
            return slope
            
        except Exception:
            return 0.0
    
    def _get_core_allocation_signal(self, data: pd.DataFrame) -> Tuple[int, float]:
        """
        Generate core allocation rebalancing signal.
        Returns: (signal: -1/0/1, confidence: 0-1)
        """
        try:
            # This would typically check current portfolio allocation
            # For now, return neutral signal
            return 0, 0.0
            
        except Exception:
            return 0, 0.0
    
    def _apply_regime_filters(self, signal: int, confidence: float, data: pd.DataFrame) -> Tuple[int, float]:
        """Apply macro regime and halving cycle filters."""
        try:
            if not self.macro_regime_filter and not self.halving_aware:
                return signal, confidence
            
            # Placeholder for regime detection
            # In production, this would check:
            # - Macro indicators (DXY, rates, inflation)
            # - Halving cycle position
            # - Market regime classification
            
            # For now, apply basic filters
            if self.halving_aware:
                # Placeholder: would check halving cycle position
                halving_phase = "accumulation"  # accumulation, bull, distribution, bear
                if halving_phase in ["distribution", "bear"]:
                    confidence *= 0.5  # Reduce confidence in bear phases
            
            return signal, confidence
            
        except Exception:
            return signal, confidence
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate signals using multi-bucket approach.
        """
        signals = pd.DataFrame(index=data.index)
        signals["signal"] = 0
        signals["confidence"] = 0.0
        signals["bucket_type"] = "none"
        
        try:
            # Get signals from each bucket
            dip_signal, dip_confidence = self._get_dip_ladder_signal(data)
            momentum_signal, momentum_confidence = self._get_momentum_signal(data)
            mr_signal, mr_confidence = self._get_mean_reversion_signal(data)
            core_signal, core_confidence = self._get_core_allocation_signal(data)
            
            # Combine signals with priority
            final_signal = 0
            final_confidence = 0.0
            bucket_type = "none"
            
            # Priority order: Dip ladder > Momentum > Mean reversion > Core
            if dip_signal != 0 and dip_confidence > 0.3:
                final_signal = dip_signal
                final_confidence = dip_confidence
                bucket_type = "dip_ladder"
            elif momentum_signal != 0 and momentum_confidence > 0.5:
                final_signal = momentum_signal
                final_confidence = momentum_confidence
                bucket_type = "momentum"
            elif mr_signal != 0 and mr_confidence > 0.4:
                final_signal = mr_signal
                final_confidence = mr_confidence
                bucket_type = "mean_reversion"
            elif core_signal != 0 and core_confidence > 0.6:
                final_signal = core_signal
                final_confidence = core_confidence
                bucket_type = "core_allocation"
            
            # Apply regime filters
            final_signal, final_confidence = self._apply_regime_filters(
                final_signal, final_confidence, data
            )
            
            # Apply to all rows (simplified - in production would be per-row)
            signals["signal"] = final_signal
            signals["confidence"] = final_confidence
            signals["bucket_type"] = bucket_type
            
            # Add metadata
            signals["dip_signal"] = dip_signal
            signals["momentum_signal"] = momentum_signal
            signals["mr_signal"] = mr_signal
            signals["core_signal"] = core_signal
            
            return signals
            
        except Exception as e:
            # Fallback to neutral signals
            signals["signal"] = 0
            signals["confidence"] = 0.0
            signals["bucket_type"] = "error"
            return signals
