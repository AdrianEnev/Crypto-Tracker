"""
ATR-Based Position Sizing and Risk Management
Implements volatility-normalized position sizing and dynamic stops.
"""

import pandas as pd
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
import numpy as np

from ..indicators.core import atr


class ATRPositionSizer:
    """
    ATR-based position sizing and risk management system.
    Implements volatility-normalized sizing and dynamic stops.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Risk parameters
        self.risk_per_trade_pct = self.config.get("risk_per_trade_pct", 1.0)  # % of portfolio risk per trade
        self.max_position_size_pct = self.config.get("max_position_size_pct", 10.0)  # Max % of portfolio per position
        self.atr_period = self.config.get("atr_period", 14)
        self.atr_multiplier = self.config.get("atr_multiplier", 2.0)
        
        # Volatility regime parameters
        self.low_vol_threshold = self.config.get("low_vol_threshold", 0.02)  # 2% daily volatility
        self.high_vol_threshold = self.config.get("high_vol_threshold", 0.05)  # 5% daily volatility
        self.regime_adjustment_factor = self.config.get("regime_adjustment_factor", 0.5)
        
        # Portfolio parameters
        self.portfolio_value = self.config.get("portfolio_value", 100000.0)
        self.max_total_exposure_pct = self.config.get("max_total_exposure_pct", 50.0)
        
    def calculate_position_size(
        self,
        current_price: float,
        entry_price: float,
        stop_price: float,
        data: pd.DataFrame,
        coin_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Calculate position size based on ATR and risk parameters.
        
        Returns:
            Dict with position size, risk amount, and metadata
        """
        try:
            # Calculate ATR
            atr_value = self._calculate_atr(data)
            if atr_value is None or atr_value <= 0:
                return self._create_error_result("ATR calculation failed")
            
            # Calculate volatility regime
            volatility_regime = self._classify_volatility_regime(data)
            
            # Calculate risk amount
            risk_amount = self.portfolio_value * (self.risk_per_trade_pct / 100.0)
            
            # Adjust risk based on volatility regime
            adjusted_risk = self._adjust_risk_for_regime(risk_amount, volatility_regime)
            
            # Calculate stop distance
            stop_distance = abs(entry_price - stop_price)
            
            # Calculate position size
            if stop_distance > 0:
                position_size = adjusted_risk / stop_distance
            else:
                # Fallback to ATR-based sizing
                atr_stop_distance = atr_value * self.atr_multiplier
                position_size = adjusted_risk / atr_stop_distance
            
            # Apply maximum position size limit
            max_position_value = self.portfolio_value * (self.max_position_size_pct / 100.0)
            max_position_size = max_position_value / current_price
            position_size = min(position_size, max_position_size)
            
            # Calculate position value
            position_value = position_size * current_price
            
            return {
                "position_size": position_size,
                "position_value": position_value,
                "risk_amount": adjusted_risk,
                "stop_distance": stop_distance,
                "atr_value": atr_value,
                "volatility_regime": volatility_regime,
                "risk_per_trade_pct": self.risk_per_trade_pct,
                "max_position_size_pct": self.max_position_size_pct,
                "success": True
            }
            
        except Exception as e:
            return self._create_error_result(f"Position sizing error: {str(e)}")
    
    def calculate_dynamic_stop(
        self,
        entry_price: float,
        current_price: float,
        data: pd.DataFrame,
        stop_type: str = "atr"
    ) -> Dict[str, Any]:
        """
        Calculate dynamic stop loss based on ATR and price action.
        
        Args:
            entry_price: Entry price of the position
            current_price: Current market price
            data: Price data for ATR calculation
            stop_type: Type of stop ("atr", "trailing", "breakeven")
        
        Returns:
            Dict with stop price, stop distance, and metadata
        """
        try:
            atr_value = self._calculate_atr(data)
            if atr_value is None or atr_value <= 0:
                return self._create_error_result("ATR calculation failed")
            
            if stop_type == "atr":
                # Fixed ATR-based stop
                stop_distance = atr_value * self.atr_multiplier
                stop_price = entry_price - stop_distance
                
            elif stop_type == "trailing":
                # Trailing stop based on ATR
                stop_distance = atr_value * self.atr_multiplier
                stop_price = current_price - stop_distance
                
            elif stop_type == "breakeven":
                # Breakeven stop (entry price)
                stop_price = entry_price
                stop_distance = abs(current_price - entry_price)
                
            else:
                return self._create_error_result(f"Unknown stop type: {stop_type}")
            
            # Calculate stop distance as percentage
            stop_distance_pct = (stop_distance / current_price) * 100.0
            
            return {
                "stop_price": stop_price,
                "stop_distance": stop_distance,
                "stop_distance_pct": stop_distance_pct,
                "atr_value": atr_value,
                "stop_type": stop_type,
                "success": True
            }
            
        except Exception as e:
            return self._create_error_result(f"Stop calculation error: {str(e)}")
    
    def calculate_take_profit(
        self,
        entry_price: float,
        current_price: float,
        data: pd.DataFrame,
        risk_reward_ratio: float = 2.0
    ) -> Dict[str, Any]:
        """
        Calculate take profit level based on risk-reward ratio.
        
        Args:
            entry_price: Entry price of the position
            current_price: Current market price
            data: Price data for ATR calculation
            risk_reward_ratio: Desired risk-reward ratio
        
        Returns:
            Dict with take profit price and metadata
        """
        try:
            atr_value = self._calculate_atr(data)
            if atr_value is None or atr_value <= 0:
                return self._create_error_result("ATR calculation failed")
            
            # Calculate stop distance
            stop_distance = atr_value * self.atr_multiplier
            
            # Calculate take profit distance
            tp_distance = stop_distance * risk_reward_ratio
            
            # Calculate take profit price
            tp_price = entry_price + tp_distance
            
            # Calculate distances as percentages
            stop_distance_pct = (stop_distance / entry_price) * 100.0
            tp_distance_pct = (tp_distance / entry_price) * 100.0
            
            return {
                "take_profit_price": tp_price,
                "take_profit_distance": tp_distance,
                "take_profit_distance_pct": tp_distance_pct,
                "stop_distance": stop_distance,
                "stop_distance_pct": stop_distance_pct,
                "risk_reward_ratio": risk_reward_ratio,
                "atr_value": atr_value,
                "success": True
            }
            
        except Exception as e:
            return self._create_error_result(f"Take profit calculation error: {str(e)}")
    
    def _calculate_atr(self, data: pd.DataFrame) -> Optional[float]:
        """Calculate ATR from price data."""
        try:
            closes = data["close"].tolist()
            highs = data["high"].tolist() if "high" in data.columns else closes
            lows = data["low"].tolist() if "low" in data.columns else closes
            
            atr_values = atr(highs, lows, closes, self.atr_period)
            if not atr_values or atr_values[-1] is None:
                return None
            
            return atr_values[-1]
            
        except Exception:
            return None
    
    def _classify_volatility_regime(self, data: pd.DataFrame) -> str:
        """Classify current volatility regime."""
        try:
            closes = data["close"].tolist()
            if len(closes) < 20:
                return "unknown"
            
            # Calculate recent volatility
            recent_closes = closes[-20:]
            volatility = np.std(recent_closes) / np.mean(recent_closes)
            
            if volatility < self.low_vol_threshold:
                return "low"
            elif volatility > self.high_vol_threshold:
                return "high"
            else:
                return "medium"
                
        except Exception:
            return "unknown"
    
    def _adjust_risk_for_regime(self, base_risk: float, regime: str) -> float:
        """Adjust risk amount based on volatility regime."""
        try:
            if regime == "low":
                # Increase risk in low volatility
                return base_risk * (1 + self.regime_adjustment_factor)
            elif regime == "high":
                # Decrease risk in high volatility
                return base_risk * (1 - self.regime_adjustment_factor)
            else:
                # No adjustment for medium volatility
                return base_risk
                
        except Exception:
            return base_risk
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error result."""
        return {
            "position_size": 0.0,
            "position_value": 0.0,
            "risk_amount": 0.0,
            "stop_distance": 0.0,
            "atr_value": 0.0,
            "volatility_regime": "unknown",
            "error": error_message,
            "success": False
        }


class VolatilityRegimeClassifier:
    """
    Classifies market volatility regimes for parameter switching.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Regime thresholds
        self.low_vol_threshold = self.config.get("low_vol_threshold", 0.02)
        self.high_vol_threshold = self.config.get("high_vol_threshold", 0.05)
        self.lookback_period = self.config.get("lookback_period", 30)
        
        # Regime persistence
        self.min_regime_duration = self.config.get("min_regime_duration", 5)  # days
        self.regime_history = []
        
    def classify_regime(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Classify current volatility regime.
        
        Returns:
            Dict with regime classification and metadata
        """
        try:
            closes = data["close"].tolist()
            if len(closes) < self.lookback_period:
                return {
                    "regime": "unknown",
                    "volatility": 0.0,
                    "confidence": 0.0,
                    "duration": 0,
                    "success": False
                }
            
            # Calculate recent volatility
            recent_closes = closes[-self.lookback_period:]
            volatility = np.std(recent_closes) / np.mean(recent_closes)
            
            # Classify regime
            if volatility < self.low_vol_threshold:
                regime = "low"
            elif volatility > self.high_vol_threshold:
                regime = "high"
            else:
                regime = "medium"
            
            # Calculate regime persistence
            duration = self._calculate_regime_duration(regime)
            
            # Calculate confidence based on persistence
            confidence = min(1.0, duration / self.min_regime_duration)
            
            return {
                "regime": regime,
                "volatility": volatility,
                "confidence": confidence,
                "duration": duration,
                "success": True
            }
            
        except Exception as e:
            return {
                "regime": "unknown",
                "volatility": 0.0,
                "confidence": 0.0,
                "duration": 0,
                "error": str(e),
                "success": False
            }
    
    def _calculate_regime_duration(self, current_regime: str) -> int:
        """Calculate how long the current regime has persisted."""
        try:
            # Add current regime to history
            self.regime_history.append(current_regime)
            
            # Keep only recent history
            if len(self.regime_history) > self.min_regime_duration * 2:
                self.regime_history = self.regime_history[-self.min_regime_duration * 2:]
            
            # Count consecutive occurrences of current regime
            duration = 0
            for regime in reversed(self.regime_history):
                if regime == current_regime:
                    duration += 1
                else:
                    break
            
            return duration
            
        except Exception:
            return 0


class RiskManager:
    """
    Comprehensive risk management system.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Risk limits
        self.max_daily_loss_pct = self.config.get("max_daily_loss_pct", 5.0)
        self.max_drawdown_pct = self.config.get("max_drawdown_pct", 15.0)
        self.max_leverage = self.config.get("max_leverage", 1.0)
        
        # Portfolio tracking
        self.portfolio_value = self.config.get("portfolio_value", 100000.0)
        self.daily_start_value = self.portfolio_value
        self.peak_value = self.portfolio_value
        
        # Risk state
        self.daily_loss = 0.0
        self.current_drawdown = 0.0
        self.risk_off = False
        
    def check_risk_limits(self, current_portfolio_value: float) -> Dict[str, Any]:
        """
        Check if risk limits are breached.
        
        Returns:
            Dict with risk status and actions
        """
        try:
            # Update portfolio value
            self.portfolio_value = current_portfolio_value
            
            # Calculate daily loss
            daily_loss_pct = ((self.daily_start_value - current_portfolio_value) / self.daily_start_value) * 100.0
            
            # Calculate drawdown
            if current_portfolio_value > self.peak_value:
                self.peak_value = current_portfolio_value
            
            drawdown_pct = ((self.peak_value - current_portfolio_value) / self.peak_value) * 100.0
            
            # Check limits
            daily_limit_breached = daily_loss_pct > self.max_daily_loss_pct
            drawdown_limit_breached = drawdown_pct > self.max_drawdown_pct
            
            # Determine action
            if daily_limit_breached or drawdown_limit_breached:
                self.risk_off = True
                action = "halt_trading"
            else:
                self.risk_off = False
                action = "continue_trading"
            
            return {
                "daily_loss_pct": daily_loss_pct,
                "drawdown_pct": drawdown_pct,
                "daily_limit_breached": daily_limit_breached,
                "drawdown_limit_breached": drawdown_limit_breached,
                "risk_off": self.risk_off,
                "action": action,
                "success": True
            }
            
        except Exception as e:
            return {
                "daily_loss_pct": 0.0,
                "drawdown_pct": 0.0,
                "daily_limit_breached": False,
                "drawdown_limit_breached": False,
                "risk_off": False,
                "action": "continue_trading",
                "error": str(e),
                "success": False
            }
    
    def reset_daily_limits(self):
        """Reset daily risk limits (call at start of each day)."""
        self.daily_start_value = self.portfolio_value
        self.daily_loss = 0.0
