"""
Advanced Trading System Integration
Integrates all components: ATR sizing, derivatives, on-chain metrics, and regime classification.
"""

import pandas as pd
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
import numpy as np

from ..risk.atr_position_sizing import ATRPositionSizer, VolatilityRegimeClassifier, RiskManager
from ..risk.regime_classifier import RegimeAwareStrategy
from ..data.derivatives import DerivativesSignalGenerator
from ..data.onchain_metrics import OnChainSignalGenerator


class AdvancedTradingSystem:
    """
    Comprehensive trading system integrating all advanced features.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Initialize components
        self.atr_sizer = ATRPositionSizer(config.get("atr_sizing", {}))
        self.regime_classifier = VolatilityRegimeClassifier(config.get("regime_classification", {}))
        self.risk_manager = RiskManager(config.get("risk_management", {}))
        self.derivatives_generator = DerivativesSignalGenerator(config.get("derivatives", {}))
        self.onchain_generator = OnChainSignalGenerator(config.get("onchain", {}))
        self.regime_aware_strategy = RegimeAwareStrategy(config.get("regime_adaptation", {}))
        
        # Integration settings
        self.use_derivatives_signals = config.get("use_derivatives_signals", True)
        self.use_onchain_signals = config.get("use_onchain_signals", True)
        self.use_regime_adaptation = config.get("use_regime_adaptation", True)
        
        # Signal weights
        self.signal_weights = config.get("signal_weights", {
            "technical": 0.3,
            "derivatives": 0.25,
            "onchain": 0.25,
            "regime": 0.2
        })
        
    def generate_comprehensive_signal(
        self,
        symbol: str,
        data: pd.DataFrame,
        technical_signal: int = 0,
        technical_confidence: float = 0.0
    ) -> Dict[str, Any]:
        """
        Generate comprehensive trading signal combining all data sources.
        
        Args:
            symbol: Trading symbol
            data: Price data
            technical_signal: Technical analysis signal (-1, 0, 1)
            technical_confidence: Technical analysis confidence (0-1)
        
        Returns:
            Dict with comprehensive signal and metadata
        """
        try:
            # Get regime classification
            regime_result = self.regime_classifier.classify_regime(data)
            
            # Get derivatives signals
            derivatives_signal = {"signal": 0, "confidence": 0.0}
            if self.use_derivatives_signals:
                derivatives_signal = self.derivatives_generator.generate_combined_signal(symbol)
            
            # Get on-chain signals
            onchain_signal = {"signal": 0, "confidence": 0.0}
            if self.use_onchain_signals:
                onchain_signal = self.onchain_generator.generate_combined_signal(symbol)
            
            # Calculate regime-based signal
            regime_signal = self._calculate_regime_signal(regime_result)
            
            # Combine all signals
            combined_signal = self._combine_signals(
                technical_signal, technical_confidence,
                derivatives_signal["signal"], derivatives_signal["confidence"],
                onchain_signal["signal"], onchain_signal["confidence"],
                regime_signal["signal"], regime_signal["confidence"]
            )
            
            # Calculate position sizing
            position_sizing = self._calculate_position_sizing(
                symbol, data, combined_signal["signal"], combined_signal["confidence"]
            )
            
            # Check risk limits
            risk_status = self.risk_manager.check_risk_limits(
                self.config.get("portfolio_value", 100000.0)
            )
            
            # Apply risk management
            final_signal = self._apply_risk_management(
                combined_signal, position_sizing, risk_status
            )
            
            return {
                "signal": final_signal["signal"],
                "confidence": final_signal["confidence"],
                "position_size": position_sizing["position_size"],
                "position_value": position_sizing["position_value"],
                "stop_price": position_sizing["stop_price"],
                "take_profit_price": position_sizing["take_profit_price"],
                "regime": regime_result["regime"],
                "regime_confidence": regime_result["confidence"],
                "derivatives_signal": derivatives_signal,
                "onchain_signal": onchain_signal,
                "regime_signal": regime_signal,
                "risk_status": risk_status,
                "success": True
            }
            
        except Exception as e:
            return {
                "signal": 0,
                "confidence": 0.0,
                "position_size": 0.0,
                "position_value": 0.0,
                "stop_price": 0.0,
                "take_profit_price": 0.0,
                "regime": "unknown",
                "regime_confidence": 0.0,
                "error": str(e),
                "success": False
            }
    
    def _calculate_regime_signal(self, regime_result: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate signal based on volatility regime."""
        try:
            if not regime_result["success"]:
                return {"signal": 0, "confidence": 0.0}
            
            regime = regime_result["regime"]
            confidence = regime_result["confidence"]
            
            # Regime-based signal logic
            if regime == "low":
                # Low volatility - favor mean reversion
                signal = 0  # Neutral, wait for opportunities
                confidence = confidence * 0.5
            elif regime == "high":
                # High volatility - favor momentum
                signal = 0  # Neutral, wait for volatility to settle
                confidence = confidence * 0.3
            else:
                # Medium volatility - normal trading
                signal = 0  # Neutral, let other signals decide
                confidence = confidence * 0.7
            
            return {"signal": signal, "confidence": confidence}
            
        except Exception:
            return {"signal": 0, "confidence": 0.0}
    
    def _combine_signals(
        self,
        tech_signal: int, tech_conf: float,
        deriv_signal: int, deriv_conf: float,
        onchain_signal: int, onchain_conf: float,
        regime_signal: int, regime_conf: float
    ) -> Dict[str, Any]:
        """Combine signals from all sources."""
        try:
            # Calculate weighted signal
            weighted_signal = (
                tech_signal * tech_conf * self.signal_weights["technical"] +
                deriv_signal * deriv_conf * self.signal_weights["derivatives"] +
                onchain_signal * onchain_conf * self.signal_weights["onchain"] +
                regime_signal * regime_conf * self.signal_weights["regime"]
            )
            
            # Calculate total confidence
            total_confidence = (
                tech_conf * self.signal_weights["technical"] +
                deriv_conf * self.signal_weights["derivatives"] +
                onchain_conf * self.signal_weights["onchain"] +
                regime_conf * self.signal_weights["regime"]
            )
            
            # Determine final signal
            if weighted_signal > 0.3:
                final_signal = 1
            elif weighted_signal < -0.3:
                final_signal = -1
            else:
                final_signal = 0
            
            return {
                "signal": final_signal,
                "confidence": total_confidence,
                "weighted_signal": weighted_signal
            }
            
        except Exception:
            return {"signal": 0, "confidence": 0.0, "weighted_signal": 0.0}
    
    def _calculate_position_sizing(
        self,
        symbol: str,
        data: pd.DataFrame,
        signal: int,
        confidence: float
    ) -> Dict[str, Any]:
        """Calculate position sizing using ATR-based method."""
        try:
            if signal == 0:
                return {
                    "position_size": 0.0,
                    "position_value": 0.0,
                    "stop_price": 0.0,
                    "take_profit_price": 0.0,
                    "success": True
                }
            
            # Get current price
            current_price = data["close"].iloc[-1]
            
            # Calculate entry price (current price for market orders)
            entry_price = current_price
            
            # Calculate stop price
            stop_result = self.atr_sizer.calculate_dynamic_stop(
                entry_price, current_price, data, "atr"
            )
            
            if not stop_result["success"]:
                return {"position_size": 0.0, "position_value": 0.0, "success": False}
            
            stop_price = stop_result["stop_price"]
            
            # Calculate position size
            sizing_result = self.atr_sizer.calculate_position_size(
                current_price, entry_price, stop_price, data, symbol
            )
            
            if not sizing_result["success"]:
                return {"position_size": 0.0, "position_value": 0.0, "success": False}
            
            # Calculate take profit
            tp_result = self.atr_sizer.calculate_take_profit(
                entry_price, current_price, data, 2.0
            )
            
            take_profit_price = tp_result.get("take_profit_price", entry_price * 1.05)
            
            return {
                "position_size": sizing_result["position_size"],
                "position_value": sizing_result["position_value"],
                "stop_price": stop_price,
                "take_profit_price": take_profit_price,
                "risk_amount": sizing_result["risk_amount"],
                "success": True
            }
            
        except Exception as e:
            return {
                "position_size": 0.0,
                "position_value": 0.0,
                "stop_price": 0.0,
                "take_profit_price": 0.0,
                "error": str(e),
                "success": False
            }
    
    def _apply_risk_management(
        self,
        signal: Dict[str, Any],
        position_sizing: Dict[str, Any],
        risk_status: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply risk management rules."""
        try:
            # Check if risk limits are breached
            if risk_status["risk_off"]:
                return {
                    "signal": 0,
                    "confidence": 0.0,
                    "reason": "risk_limits_breached"
                }
            
            # Check if position size is within limits
            max_position_value = self.config.get("max_position_value", 10000.0)
            if position_sizing["position_value"] > max_position_value:
                return {
                    "signal": 0,
                    "confidence": 0.0,
                    "reason": "position_size_limit_exceeded"
                }
            
            # Apply confidence threshold
            min_confidence = self.config.get("min_confidence_threshold", 0.6)
            if signal["confidence"] < min_confidence:
                return {
                    "signal": 0,
                    "confidence": signal["confidence"],
                    "reason": "confidence_too_low"
                }
            
            # All checks passed
            return {
                "signal": signal["signal"],
                "confidence": signal["confidence"],
                "reason": "all_checks_passed"
            }
            
        except Exception:
            return {
                "signal": 0,
                "confidence": 0.0,
                "reason": "risk_management_error"
            }
    
    def get_system_status(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Get comprehensive system status."""
        try:
            # Get regime status
            regime_result = self.regime_classifier.classify_regime(data)
            
            # Get risk status
            risk_status = self.risk_manager.check_risk_limits(
                self.config.get("portfolio_value", 100000.0)
            )
            
            return {
                "regime": regime_result["regime"],
                "regime_confidence": regime_result["confidence"],
                "volatility": regime_result["volatility"],
                "risk_off": risk_status["risk_off"],
                "daily_loss_pct": risk_status["daily_loss_pct"],
                "drawdown_pct": risk_status["drawdown_pct"],
                "system_healthy": not risk_status["risk_off"],
                "success": True
            }
            
        except Exception as e:
            return {
                "regime": "unknown",
                "regime_confidence": 0.0,
                "volatility": 0.0,
                "risk_off": False,
                "daily_loss_pct": 0.0,
                "drawdown_pct": 0.0,
                "system_healthy": False,
                "error": str(e),
                "success": False
            }
