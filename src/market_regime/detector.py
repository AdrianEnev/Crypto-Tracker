"""
Advanced market regime detection system.
Implements volatility clustering, trend strength analysis, and macro filters.
"""

import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats


class MarketRegimeDetector:
    """
    Advanced market regime detection with multiple indicators.
    
    Detects regimes:
    - Bull Market: Strong uptrend with moderate volatility
    - Bear Market: Strong downtrend with moderate volatility  
    - Sideways: Range-bound with low volatility
    - High Volatility: Elevated volatility regardless of trend
    - Crisis: Extreme volatility and stress conditions
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # Volatility parameters
        self.vol_period = int(self.config.get("vol_period", 20))
        self.vol_threshold_low = float(self.config.get("vol_threshold_low", 0.15))
        self.vol_threshold_high = float(self.config.get("vol_threshold_high", 0.35))
        self.vol_threshold_extreme = float(self.config.get("vol_threshold_extreme", 0.50))
        
        # Trend parameters
        self.trend_period = int(self.config.get("trend_period", 50))
        self.trend_threshold = float(self.config.get("trend_threshold", 0.02))
        
        # Volatility clustering parameters
        self.clustering_window = int(self.config.get("clustering_window", 60))
        self.clustering_threshold = float(self.config.get("clustering_threshold", 0.7))
        
        # Macro filter parameters
        self.macro_period = int(self.config.get("macro_period", 252))
        self.correlation_threshold = float(self.config.get("correlation_threshold", 0.8))
        
        # Crisis detection parameters
        self.crisis_vol_mult = float(self.config.get("crisis_vol_mult", 2.0))
        self.crisis_drawdown_threshold = float(self.config.get("crisis_drawdown_threshold", 0.20))
        
        # State tracking
        self.regime_history = []
        self.current_regime = "unknown"
        self.regime_confidence = 0.0
        
    def detect_regime(
        self,
        prices: List[float],
        volumes: Optional[List[float]] = None,
        timestamps: Optional[List[datetime]] = None
    ) -> Dict[str, any]:
        """
        Detect current market regime based on price and volume data.
        
        Args:
            prices: List of closing prices
            volumes: Optional list of volumes
            timestamps: Optional list of timestamps
            
        Returns:
            Dictionary with regime information
        """
        if len(prices) < max(self.vol_period, self.trend_period, self.clustering_window):
            return {
                "regime": "insufficient_data",
                "confidence": 0.0,
                "indicators": {},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Calculate indicators
        indicators = self._calculate_indicators(prices, volumes)
        
        # Determine regime based on indicators
        regime_result = self._classify_regime(indicators)
        
        # Update state
        self.current_regime = regime_result["regime"]
        self.regime_confidence = regime_result["confidence"]
        
        # Record history
        regime_record = {
            "timestamp": timestamps[-1].isoformat() if timestamps else datetime.now(timezone.utc).isoformat(),
            "regime": self.current_regime,
            "confidence": self.regime_confidence,
            "indicators": indicators,
            "prices": prices[-10:] if len(prices) >= 10 else prices  # Last 10 prices
        }
        self.regime_history.append(regime_record)
        
        # Keep only recent history
        if len(self.regime_history) > 1000:
            self.regime_history = self.regime_history[-1000:]
        
        return regime_result
    
    def _calculate_indicators(
        self, 
        prices: List[float], 
        volumes: Optional[List[float]] = None
    ) -> Dict[str, float]:
        """Calculate all regime detection indicators."""
        indicators = {}
        
        # Price-based indicators
        indicators.update(self._calculate_volatility_indicators(prices))
        indicators.update(self._calculate_trend_indicators(prices))
        indicators.update(self._calculate_momentum_indicators(prices))
        
        # Volume-based indicators (if available)
        if volumes:
            indicators.update(self._calculate_volume_indicators(prices, volumes))
        
        # Advanced indicators
        indicators.update(self._calculate_volatility_clustering(prices))
        indicators.update(self._calculate_regime_persistence(prices))
        indicators.update(self._calculate_crisis_indicators(prices))
        
        return indicators
    
    def _calculate_volatility_indicators(self, prices: List[float]) -> Dict[str, float]:
        """Calculate volatility-based indicators."""
        returns = [prices[i] / prices[i-1] - 1 for i in range(1, len(prices))]
        
        if len(returns) < self.vol_period:
            return {"volatility": 0.0, "vol_percentile": 0.0}
        
        # Current volatility (annualized)
        recent_returns = returns[-self.vol_period:]
        volatility = np.std(recent_returns) * math.sqrt(252)
        
        # Volatility percentile
        all_volatilities = []
        for i in range(self.vol_period, len(returns)):
            vol_window = returns[i-self.vol_period:i]
            vol = np.std(vol_window) * math.sqrt(252)
            all_volatilities.append(vol)
        
        if all_volatilities:
            vol_percentile = stats.percentileofscore(all_volatilities, volatility) / 100.0
        else:
            vol_percentile = 0.5
        
        return {
            "volatility": volatility,
            "vol_percentile": vol_percentile
        }
    
    def _calculate_trend_indicators(self, prices: List[float]) -> Dict[str, float]:
        """Calculate trend-based indicators."""
        if len(prices) < self.trend_period:
            return {"trend_strength": 0.0, "trend_direction": 0.0}
        
        # Linear regression trend
        x = np.arange(len(prices[-self.trend_period:]))
        y = prices[-self.trend_period:]
        
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        
        # Trend strength (R-squared)
        trend_strength = r_value ** 2
        
        # Trend direction (normalized slope)
        price_level = prices[-1]
        trend_direction = slope / price_level if price_level > 0 else 0
        
        # Moving average trend
        short_ma = np.mean(prices[-10:]) if len(prices) >= 10 else prices[-1]
        long_ma = np.mean(prices[-self.trend_period:])
        ma_trend = (short_ma - long_ma) / long_ma if long_ma > 0 else 0
        
        return {
            "trend_strength": trend_strength,
            "trend_direction": trend_direction,
            "ma_trend": ma_trend
        }
    
    def _calculate_momentum_indicators(self, prices: List[float]) -> Dict[str, float]:
        """Calculate momentum-based indicators."""
        if len(prices) < 20:
            return {"momentum": 0.0, "acceleration": 0.0}
        
        # Price momentum
        momentum = (prices[-1] / prices[-20] - 1) if prices[-20] > 0 else 0
        
        # Momentum acceleration
        if len(prices) >= 40:
            momentum_1 = (prices[-20] / prices[-40] - 1) if prices[-40] > 0 else 0
            momentum_2 = (prices[-1] / prices[-20] - 1) if prices[-20] > 0 else 0
            acceleration = momentum_2 - momentum_1
        else:
            acceleration = 0.0
        
        # Rate of change
        roc_5 = (prices[-1] / prices[-5] - 1) if len(prices) >= 5 and prices[-5] > 0 else 0
        roc_10 = (prices[-1] / prices[-10] - 1) if len(prices) >= 10 and prices[-10] > 0 else 0
        
        return {
            "momentum": momentum,
            "acceleration": acceleration,
            "roc_5": roc_5,
            "roc_10": roc_10
        }
    
    def _calculate_volume_indicators(
        self, prices: List[float], volumes: List[float]
    ) -> Dict[str, float]:
        """Calculate volume-based indicators."""
        if len(volumes) < 20:
            return {"volume_trend": 0.0, "volume_spike": 0.0}
        
        # Volume trend
        recent_volume = np.mean(volumes[-10:])
        avg_volume = np.mean(volumes[-20:])
        volume_trend = (recent_volume / avg_volume - 1) if avg_volume > 0 else 0
        
        # Volume spike detection
        volume_std = np.std(volumes[-20:])
        current_volume = volumes[-1]
        volume_spike = (current_volume - avg_volume) / volume_std if volume_std > 0 else 0
        
        # Price-volume correlation
        if len(prices) >= 20 and len(volumes) >= 20:
            price_changes = [prices[i] / prices[i-1] - 1 for i in range(-19, 0)]
            volume_changes = [volumes[i] / volumes[i-1] - 1 for i in range(-19, 0)]
            
            if len(price_changes) == len(volume_changes) and len(price_changes) > 5:
                correlation = np.corrcoef(price_changes, volume_changes)[0, 1]
                if np.isnan(correlation):
                    correlation = 0.0
            else:
                correlation = 0.0
        else:
            correlation = 0.0
        
        return {
            "volume_trend": volume_trend,
            "volume_spike": volume_spike,
            "price_volume_correlation": correlation
        }
    
    def _calculate_volatility_clustering(self, prices: List[float]) -> Dict[str, float]:
        """Calculate volatility clustering indicators."""
        returns = [prices[i] / prices[i-1] - 1 for i in range(1, len(prices))]
        
        if len(returns) < self.clustering_window:
            return {"vol_clustering": 0.0, "vol_persistence": 0.0}
        
        # Volatility clustering (autocorrelation of squared returns)
        squared_returns = [r ** 2 for r in returns]
        
        if len(squared_returns) >= 10:
            # Calculate autocorrelation of squared returns
            autocorr = np.corrcoef(squared_returns[:-1], squared_returns[1:])[0, 1]
            if np.isnan(autocorr):
                autocorr = 0.0
        else:
            autocorr = 0.0
        
        # Volatility persistence (how long high vol periods last)
        vol_threshold = np.percentile([abs(r) for r in returns[-self.clustering_window:]], 75)
        high_vol_periods = []
        current_period = 0
        
        for r in returns[-self.clustering_window:]:
            if abs(r) > vol_threshold:
                current_period += 1
            else:
                if current_period > 0:
                    high_vol_periods.append(current_period)
                    current_period = 0
        
        if current_period > 0:
            high_vol_periods.append(current_period)
        
        vol_persistence = np.mean(high_vol_periods) if high_vol_periods else 0
        
        return {
            "vol_clustering": autocorr,
            "vol_persistence": vol_persistence
        }
    
    def _calculate_regime_persistence(self, prices: List[float]) -> Dict[str, float]:
        """Calculate regime persistence indicators."""
        if len(self.regime_history) < 10:
            return {"regime_persistence": 0.0, "regime_stability": 0.0}
        
        # Count recent regime changes
        recent_regimes = [r["regime"] for r in self.regime_history[-20:]]
        regime_changes = sum(1 for i in range(1, len(recent_regimes)) if recent_regimes[i] != recent_regimes[i-1])
        regime_persistence = 1.0 - (regime_changes / len(recent_regimes)) if recent_regimes else 0.0
        
        # Regime stability (consistency of confidence)
        recent_confidences = [r["confidence"] for r in self.regime_history[-10:]]
        regime_stability = 1.0 - np.std(recent_confidences) if recent_confidences else 0.0
        
        return {
            "regime_persistence": regime_persistence,
            "regime_stability": regime_stability
        }
    
    def _calculate_crisis_indicators(self, prices: List[float]) -> Dict[str, float]:
        """Calculate crisis detection indicators."""
        returns = [prices[i] / prices[i-1] - 1 for i in range(1, len(prices))]
        
        if len(returns) < 20:
            return {"crisis_probability": 0.0, "stress_level": 0.0}
        
        # Extreme volatility
        recent_vol = np.std(returns[-10:]) * math.sqrt(252)
        historical_vol = np.std(returns[-50:]) * math.sqrt(252) if len(returns) >= 50 else recent_vol
        vol_ratio = recent_vol / historical_vol if historical_vol > 0 else 1.0
        
        # Drawdown analysis
        peak = max(prices[-20:])
        current_drawdown = (peak - prices[-1]) / peak if peak > 0 else 0
        
        # Stress level (combination of volatility and drawdown)
        stress_level = min(1.0, (vol_ratio - 1.0) * 0.5 + current_drawdown * 2.0)
        
        # Crisis probability
        crisis_probability = 0.0
        if vol_ratio > self.crisis_vol_mult:
            crisis_probability += 0.4
        if current_drawdown > self.crisis_drawdown_threshold:
            crisis_probability += 0.4
        if stress_level > 0.8:
            crisis_probability += 0.2
        
        return {
            "crisis_probability": crisis_probability,
            "stress_level": stress_level,
            "vol_ratio": vol_ratio,
            "current_drawdown": current_drawdown
        }
    
    def _classify_regime(self, indicators: Dict[str, float]) -> Dict[str, any]:
        """Classify market regime based on indicators."""
        vol = indicators.get("volatility", 0)
        vol_percentile = indicators.get("vol_percentile", 0.5)
        trend_strength = indicators.get("trend_strength", 0)
        trend_direction = indicators.get("trend_direction", 0)
        crisis_prob = indicators.get("crisis_probability", 0)
        stress_level = indicators.get("stress_level", 0)
        
        # Determine regime
        if crisis_prob > 0.7 or stress_level > 0.8:
            regime = "crisis"
            confidence = min(1.0, crisis_prob + stress_level * 0.3)
        elif vol > self.vol_threshold_extreme or vol_percentile > 0.9:
            regime = "high_volatility"
            confidence = min(1.0, vol_percentile + 0.3)
        elif trend_strength > 0.3:
            if trend_direction > self.trend_threshold:
                regime = "bull_market"
                confidence = trend_strength + 0.2
            elif trend_direction < -self.trend_threshold:
                regime = "bear_market"
                confidence = trend_strength + 0.2
            else:
                regime = "sideways"
                confidence = 0.6
        elif vol < self.vol_threshold_low and vol_percentile < 0.3:
            regime = "sideways"
            confidence = 0.8
        else:
            regime = "transition"
            confidence = 0.4
        
        # Adjust confidence based on regime persistence
        regime_persistence = indicators.get("regime_persistence", 0.5)
        confidence = confidence * 0.7 + regime_persistence * 0.3
        
        return {
            "regime": regime,
            "confidence": min(1.0, max(0.0, confidence)),
            "indicators": indicators,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def get_regime_history(self, days: int = 30) -> List[Dict[str, any]]:
        """Get regime history for the specified number of days."""
        return self.regime_history[-days:] if self.regime_history else []
    
    def get_regime_transitions(self) -> List[Dict[str, any]]:
        """Get list of regime transitions."""
        transitions = []
        
        if len(self.regime_history) < 2:
            return transitions
        
        for i in range(1, len(self.regime_history)):
            current = self.regime_history[i]
            previous = self.regime_history[i-1]
            
            if current["regime"] != previous["regime"]:
                transitions.append({
                    "timestamp": current["timestamp"],
                    "from_regime": previous["regime"],
                    "to_regime": current["regime"],
                    "confidence": current["confidence"],
                    "indicators": current["indicators"]
                })
        
        return transitions
    
    def get_regime_statistics(self) -> Dict[str, any]:
        """Get statistics about detected regimes."""
        if not self.regime_history:
            return {}
        
        # Count regime occurrences
        regime_counts = {}
        total_time = 0
        
        for record in self.regime_history:
            regime = record["regime"]
            regime_counts[regime] = regime_counts.get(regime, 0) + 1
            total_time += 1
        
        # Calculate percentages
        regime_percentages = {
            regime: count / total_time * 100 
            for regime, count in regime_counts.items()
        }
        
        # Average confidence by regime
        regime_confidences = {}
        for record in self.regime_history:
            regime = record["regime"]
            confidence = record["confidence"]
            
            if regime not in regime_confidences:
                regime_confidences[regime] = []
            regime_confidences[regime].append(confidence)
        
        avg_confidences = {
            regime: np.mean(confidences) 
            for regime, confidences in regime_confidences.items()
        }
        
        return {
            "regime_counts": regime_counts,
            "regime_percentages": regime_percentages,
            "avg_confidence_by_regime": avg_confidences,
            "total_observations": total_time,
            "num_transitions": len(self.get_regime_transitions())
        }
