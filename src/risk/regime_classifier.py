"""
Volatility Regime Classifier
Classifies market volatility regimes and switches parameters accordingly.
"""

import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


class VolatilityRegimeClassifier:
    """
    Advanced volatility regime classifier using multiple indicators.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Regime parameters
        self.low_vol_threshold = self.config.get("low_vol_threshold", 0.02)  # 2% daily volatility
        self.high_vol_threshold = self.config.get("high_vol_threshold", 0.05)  # 5% daily volatility
        self.lookback_period = self.config.get("lookback_period", 30)
        
        # Regime persistence
        self.min_regime_duration = self.config.get("min_regime_duration", 5)  # days
        self.regime_history = []
        
        # Advanced classification
        self.use_clustering = self.config.get("use_clustering", True)
        self.n_clusters = self.config.get("n_clusters", 3)  # low, medium, high
        self.feature_window = self.config.get("feature_window", 20)
        
        # Regime-specific parameters
        self.regime_parameters = {
            "low": {
                "atr_multiplier": 2.0,
                "position_size_multiplier": 1.2,
                "stop_loss_multiplier": 1.0,
                "take_profit_multiplier": 2.0,
                "risk_per_trade_pct": 1.5
            },
            "medium": {
                "atr_multiplier": 2.5,
                "position_size_multiplier": 1.0,
                "stop_loss_multiplier": 1.0,
                "take_profit_multiplier": 2.5,
                "risk_per_trade_pct": 1.0
            },
            "high": {
                "atr_multiplier": 3.0,
                "position_size_multiplier": 0.8,
                "stop_loss_multiplier": 1.2,
                "take_profit_multiplier": 3.0,
                "risk_per_trade_pct": 0.5
            }
        }
        
        # Clustering model
        self.kmeans_model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        
    def classify_regime(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Classify current volatility regime using advanced methods.
        
        Returns:
            Dict with regime classification and metadata
        """
        try:
            closes = data["close"].tolist()
            if len(closes) < self.lookback_period:
                return self._create_error_result("insufficient_data")
            
            # Calculate volatility features
            features = self._calculate_volatility_features(data)
            
            # Classify regime
            if self.use_clustering and self.is_trained:
                regime = self._classify_with_clustering(features)
            else:
                regime = self._classify_with_thresholds(features)
            
            # Calculate regime persistence
            duration = self._calculate_regime_duration(regime)
            
            # Calculate confidence based on persistence and feature consistency
            confidence = self._calculate_regime_confidence(features, regime, duration)
            
            # Get regime-specific parameters
            regime_params = self.regime_parameters.get(regime, self.regime_parameters["medium"])
            
            return {
                "regime": regime,
                "volatility": features["volatility"],
                "confidence": confidence,
                "duration": duration,
                "features": features,
                "parameters": regime_params,
                "success": True
            }
            
        except Exception as e:
            return self._create_error_result(f"classification_error: {str(e)}")
    
    def train_classifier(self, historical_data: List[pd.DataFrame]) -> Dict[str, Any]:
        """
        Train the clustering model on historical data.
        
        Args:
            historical_data: List of historical price data DataFrames
        
        Returns:
            Dict with training results
        """
        try:
            if not historical_data:
                return {"success": False, "error": "no_historical_data"}
            
            # Extract features from historical data
            all_features = []
            for data in historical_data:
                if len(data) >= self.lookback_period:
                    features = self._calculate_volatility_features(data)
                    all_features.append([
                        features["volatility"],
                        features["volatility_of_volatility"],
                        features["trend_strength"],
                        features["mean_reversion_strength"]
                    ])
            
            if len(all_features) < 10:
                return {"success": False, "error": "insufficient_training_data"}
            
            # Scale features
            scaled_features = self.scaler.fit_transform(all_features)
            
            # Train K-means model
            self.kmeans_model = KMeans(n_clusters=self.n_clusters, random_state=42)
            self.kmeans_model.fit(scaled_features)
            
            self.is_trained = True
            
            return {
                "success": True,
                "n_samples": len(all_features),
                "n_features": len(all_features[0]),
                "n_clusters": self.n_clusters
            }
            
        except Exception as e:
            return {"success": False, "error": f"training_error: {str(e)}"}
    
    def _calculate_volatility_features(self, data: pd.DataFrame) -> Dict[str, float]:
        """Calculate comprehensive volatility features."""
        try:
            closes = data["close"].tolist()
            highs = data["high"].tolist() if "high" in data.columns else closes
            lows = data["low"].tolist() if "low" in data.columns else closes
            
            # Basic volatility
            returns = [closes[i] / closes[i-1] - 1 for i in range(1, len(closes))]
            volatility = np.std(returns) if returns else 0.0
            
            # Volatility of volatility
            if len(returns) >= 10:
                rolling_vol = []
                for i in range(10, len(returns)):
                    rolling_vol.append(np.std(returns[i-10:i]))
                vol_of_vol = np.std(rolling_vol) if rolling_vol else 0.0
            else:
                vol_of_vol = 0.0
            
            # Trend strength (using price momentum)
            if len(closes) >= 20:
                short_ma = np.mean(closes[-10:])
                long_ma = np.mean(closes[-20:])
                trend_strength = (short_ma - long_ma) / long_ma
            else:
                trend_strength = 0.0
            
            # Mean reversion strength (using price oscillation)
            if len(closes) >= 20:
                price_oscillation = []
                for i in range(1, len(closes)):
                    oscillation = abs(closes[i] - closes[i-1]) / closes[i-1]
                    price_oscillation.append(oscillation)
                mean_reversion_strength = np.mean(price_oscillation)
            else:
                mean_reversion_strength = 0.0
            
            # ATR-based volatility
            if len(highs) >= 14 and len(lows) >= 14:
                atr_values = []
                for i in range(1, min(14, len(highs))):
                    tr = max(
                        highs[i] - lows[i],
                        abs(highs[i] - closes[i-1]),
                        abs(lows[i] - closes[i-1])
                    )
                    atr_values.append(tr)
                atr_volatility = np.mean(atr_values) / closes[-1] if closes else 0.0
            else:
                atr_volatility = 0.0
            
            return {
                "volatility": volatility,
                "volatility_of_volatility": vol_of_vol,
                "trend_strength": trend_strength,
                "mean_reversion_strength": mean_reversion_strength,
                "atr_volatility": atr_volatility
            }
            
        except Exception:
            return {
                "volatility": 0.0,
                "volatility_of_volatility": 0.0,
                "trend_strength": 0.0,
                "mean_reversion_strength": 0.0,
                "atr_volatility": 0.0
            }
    
    def _classify_with_clustering(self, features: Dict[str, float]) -> str:
        """Classify regime using trained clustering model."""
        try:
            if not self.kmeans_model:
                return "medium"
            
            # Prepare features for prediction
            feature_vector = [
                features["volatility"],
                features["volatility_of_volatility"],
                features["trend_strength"],
                features["mean_reversion_strength"]
            ]
            
            # Scale features
            scaled_features = self.scaler.transform([feature_vector])
            
            # Predict cluster
            cluster = self.kmeans_model.predict(scaled_features)[0]
            
            # Map cluster to regime
            cluster_to_regime = {
                0: "low",
                1: "medium",
                2: "high"
            }
            
            return cluster_to_regime.get(cluster, "medium")
            
        except Exception:
            return "medium"
    
    def _classify_with_thresholds(self, features: Dict[str, float]) -> str:
        """Classify regime using simple thresholds."""
        try:
            volatility = features["volatility"]
            
            if volatility < self.low_vol_threshold:
                return "low"
            elif volatility > self.high_vol_threshold:
                return "high"
            else:
                return "medium"
                
        except Exception:
            return "medium"
    
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
    
    def _calculate_regime_confidence(self, features: Dict[str, float], regime: str, duration: int) -> float:
        """Calculate confidence in regime classification."""
        try:
            # Base confidence from feature consistency
            base_confidence = 0.5
            
            # Adjust based on volatility level
            volatility = features["volatility"]
            if regime == "low" and volatility < self.low_vol_threshold:
                base_confidence += 0.2
            elif regime == "high" and volatility > self.high_vol_threshold:
                base_confidence += 0.2
            elif regime == "medium" and self.low_vol_threshold <= volatility <= self.high_vol_threshold:
                base_confidence += 0.2
            
            # Adjust based on regime persistence
            if duration >= self.min_regime_duration:
                base_confidence += 0.2
            
            # Adjust based on feature consistency
            vol_of_vol = features["volatility_of_volatility"]
            if vol_of_vol < 0.01:  # Low volatility of volatility = stable regime
                base_confidence += 0.1
            
            return min(1.0, base_confidence)
            
        except Exception:
            return 0.5
    
    def get_regime_parameters(self, regime: str) -> Dict[str, float]:
        """Get parameters for a specific regime."""
        return self.regime_parameters.get(regime, self.regime_parameters["medium"])
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error result."""
        return {
            "regime": "unknown",
            "volatility": 0.0,
            "confidence": 0.0,
            "duration": 0,
            "features": {},
            "parameters": self.regime_parameters["medium"],
            "error": error_message,
            "success": False
        }


class RegimeAwareStrategy:
    """
    Strategy that adapts parameters based on volatility regime.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Regime classifier
        self.regime_classifier = VolatilityRegimeClassifier(config)
        
        # Base parameters
        self.base_parameters = config.get("base_parameters", {})
        
        # Regime adaptation
        self.adapt_position_sizing = config.get("adapt_position_sizing", True)
        self.adapt_stops = config.get("adapt_stops", True)
        self.adapt_risk = config.get("adapt_risk", True)
        
    def adapt_parameters(self, data: pd.DataFrame, base_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapt strategy parameters based on current volatility regime.
        
        Args:
            data: Price data for regime classification
            base_params: Base strategy parameters
        
        Returns:
            Dict with adapted parameters
        """
        try:
            # Classify current regime
            regime_result = self.regime_classifier.classify_regime(data)
            
            if not regime_result["success"]:
                return base_params
            
            regime = regime_result["regime"]
            regime_params = regime_result["parameters"]
            confidence = regime_result["confidence"]
            
            # Adapt parameters based on regime
            adapted_params = base_params.copy()
            
            if self.adapt_position_sizing:
                # Adjust position sizing
                size_multiplier = regime_params["position_size_multiplier"]
                if "position_size" in adapted_params:
                    adapted_params["position_size"] *= size_multiplier
            
            if self.adapt_stops:
                # Adjust stop loss and take profit
                sl_multiplier = regime_params["stop_loss_multiplier"]
                tp_multiplier = regime_params["take_profit_multiplier"]
                
                if "stop_loss_multiplier" in adapted_params:
                    adapted_params["stop_loss_multiplier"] *= sl_multiplier
                if "take_profit_multiplier" in adapted_params:
                    adapted_params["take_profit_multiplier"] *= tp_multiplier
            
            if self.adapt_risk:
                # Adjust risk per trade
                risk_multiplier = regime_params["risk_per_trade_pct"] / 100.0
                if "risk_per_trade_pct" in adapted_params:
                    adapted_params["risk_per_trade_pct"] *= risk_multiplier
            
            # Add regime metadata
            adapted_params["regime"] = regime
            adapted_params["regime_confidence"] = confidence
            adapted_params["regime_parameters"] = regime_params
            
            return adapted_params
            
        except Exception as e:
            # Return base parameters if adaptation fails
            return base_params
    
    def get_regime_status(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Get current regime status."""
        return self.regime_classifier.classify_regime(data)
