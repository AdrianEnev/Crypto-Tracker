"""
Tier 3: Tactical Intelligence

Generates trading signals using:
- Regime-aware strategy selection
- ML-enhanced technical analysis
- Risk-adjusted position recommendations
"""

import logging
from typing import Optional
import pandas as pd

from ..base import BaseIntelligence
from ..models import TacticalSignal, MarketState


class TacticalIntelligence(BaseIntelligence):
    """
    Generates tactical trading signals based on market state
    
    Features:
    - Regime-aware strategy selection
    - ML-enhanced signal generation
    - Fallback to simple strategies
    """
    
    def __init__(self, config: dict, ml_models=None, strategies=None):
        super().__init__(config, logger_name=__name__)
        
        self.ml_models = ml_models
        self.strategies = strategies
        
        # Configuration
        self.ml_enhanced = config.get('ml_enhanced', True)
        self.confidence_threshold = config.get('confidence_threshold', 0.6)
        self.use_fallback = config.get('fallback_to_simple', True)
    
    async def analyze(
        self,
        coin_id: str,
        current_price: float,
        market_state: MarketState,
        risk_multiplier: float = 1.0
    ) -> TacticalSignal:
        """
        Generate tactical trading signal
        
        Args:
            coin_id: Coin identifier
            current_price: Current market price
            market_state: Market state from Tier 2
            risk_multiplier: Risk adjustment from Tier 1
            
        Returns:
            TacticalSignal with action and confidence
        """
        return await self.generate_signal(coin_id, current_price, market_state, risk_multiplier)
    
    async def generate_signal(
        self,
        coin_id: str,
        current_price: float,
        market_state: MarketState,
        risk_multiplier: float = 1.0
    ) -> TacticalSignal:
        """
        Generate trading signal based on regime and market conditions
        
        Returns:
            TacticalSignal object
        """
        try:
            # Select strategy based on regime
            strategy = self._select_strategy(market_state.regime)
            
            # Get market data
            market_data = await self._get_market_data(coin_id)
            
            if market_data is None or market_data.empty:
                return TacticalSignal.hold_default()
            
            # Generate signal using selected strategy
            if self.ml_enhanced and self.ml_models:
                signal = await self._generate_ml_signal(
                    strategy, market_data, market_state
                )
            else:
                signal = await self._generate_simple_signal(
                    strategy, market_data, market_state
                )
            
            # Apply risk adjustment
            signal.confidence *= risk_multiplier
            
            # Check confidence threshold
            if signal.confidence < self.confidence_threshold:
                signal.action = "HOLD"
                signal.reason += f" (confidence {signal.confidence:.2f} below threshold)"
            
            self.record_success()
            return signal
            
        except Exception as e:
            self.logger.error(f"Signal generation failed for {coin_id}: {e}")
            self.record_failure(e)
            return TacticalSignal.hold_default()
    
    def _select_strategy(self, regime: str) -> str:
        """
        Select appropriate strategy based on market regime
        
        Args:
            regime: Market regime (TRENDING, RANGING, VOLATILE, UNKNOWN)
            
        Returns:
            Strategy name
        """
        strategy_map = {
            'TRENDING': 'momentum',
            'RANGING': 'mean_reversion',
            'VOLATILE': 'breakout',
            'UNKNOWN': 'mean_reversion'  # Conservative default
        }
        
        return strategy_map.get(regime, 'mean_reversion')
    
    async def _get_market_data(self, coin_id: str) -> Optional[pd.DataFrame]:
        """
        Get market data for analysis
        
        This would fetch from price history in production
        """
        try:
            # In production, this would fetch real price data
            # For now, return None to trigger fallback
            return None
        except Exception as e:
            self.logger.error(f"Failed to get market data: {e}")
            return None
    
    async def _generate_ml_signal(
        self,
        strategy_name: str,
        market_data: pd.DataFrame,
        market_state: MarketState
    ) -> TacticalSignal:
        """
        Generate signal using ML-enhanced strategy
        
        Args:
            strategy_name: Name of strategy to use
            market_data: Price and volume data
            market_state: Current market state
            
        Returns:
            TacticalSignal
        """
        try:
            # Get ML model for strategy
            model = self._get_ml_model(strategy_name)
            
            if model:
                # Extract features
                features = self._extract_features(market_data, market_state)
                
                # Generate prediction
                prediction = model.predict(features)
                
                # Convert to signal
                return self._prediction_to_signal(
                    prediction, strategy_name, market_data
                )
            else:
                # Fallback to simple strategy
                return await self._generate_simple_signal(
                    strategy_name, market_data, market_state
                )
                
        except Exception as e:
            self.logger.warning(f"ML signal generation failed: {e}")
            
            if self.use_fallback:
                return await self._generate_simple_signal(
                    strategy_name, market_data, market_state
                )
            else:
                return TacticalSignal.hold_default()
    
    async def _generate_simple_signal(
        self,
        strategy_name: str,
        market_data: pd.DataFrame,
        market_state: MarketState
    ) -> TacticalSignal:
        """
        Generate signal using simple technical analysis
        
        This is the fallback when ML is unavailable
        """
        try:
            # Use existing strategy implementations
            if self.strategies and hasattr(self.strategies, strategy_name):
                strategy = getattr(self.strategies, strategy_name)
                signals = strategy.generate_signals(market_data)
                
                # Get last signal
                if not signals.empty and 'signal' in signals.columns:
                    last_signal = int(signals['signal'].iloc[-1])
                    
                    action = "HOLD"
                    if last_signal > 0:
                        action = "BUY"
                    elif last_signal < 0:
                        action = "SELL"
                    
                    return TacticalSignal(
                        action=action,
                        confidence=0.7,  # Moderate confidence for simple signals
                        strategy_name=strategy_name,
                        reason=f"Simple {strategy_name} signal"
                    )
            
            # Default hold
            return TacticalSignal.hold_default()
            
        except Exception as e:
            self.logger.error(f"Simple signal generation failed: {e}")
            return TacticalSignal.hold_default()
    
    def _get_ml_model(self, strategy_name: str):
        """Get ML model for strategy"""
        if not self.ml_models:
            return None
        
        model_map = {
            'momentum': 'momentum_model',
            'mean_reversion': 'mean_reversion_model',
            'breakout': 'breakout_model'
        }
        
        model_attr = model_map.get(strategy_name)
        if model_attr and hasattr(self.ml_models, model_attr):
            return getattr(self.ml_models, model_attr)
        
        return None
    
    def _extract_features(
        self,
        market_data: pd.DataFrame,
        market_state: MarketState
    ) -> pd.DataFrame:
        """
        Extract features for ML model
        
        Would include:
        - Technical indicators
        - Social sentiment
        - Orderbook metrics
        - Regime indicators
        """
        features = pd.DataFrame()
        
        # Add social sentiment features
        features['social_score'] = market_state.social_sentiment.score
        features['social_volume'] = market_state.social_sentiment.volume
        
        # Add orderbook features
        features['ob_imbalance'] = market_state.orderbook_signal.bid_ask_imbalance
        features['ob_spread'] = market_state.orderbook_signal.spread_bps
        
        # Add regime
        features['regime_trending'] = 1 if market_state.regime == 'TRENDING' else 0
        features['regime_ranging'] = 1 if market_state.regime == 'RANGING' else 0
        features['regime_volatile'] = 1 if market_state.regime == 'VOLATILE' else 0
        
        return features
    
    def _prediction_to_signal(
        self,
        prediction,
        strategy_name: str,
        market_data: pd.DataFrame
    ) -> TacticalSignal:
        """Convert ML prediction to TacticalSignal"""
        # Assuming prediction is a probability or class
        if hasattr(prediction, 'shape') and len(prediction.shape) > 0:
            pred_value = float(prediction[0])
        else:
            pred_value = float(prediction)
        
        # Convert to action
        if pred_value > 0.6:
            action = "BUY"
            confidence = pred_value
        elif pred_value < 0.4:
            action = "SELL"
            confidence = 1.0 - pred_value
        else:
            action = "HOLD"
            confidence = 0.5
        
        # Calculate stop loss and take profit
        current_price = float(market_data['close'].iloc[-1])
        stop_loss = current_price * 0.98  # 2% stop
        take_profit = current_price * 1.04  # 4% target
        
        return TacticalSignal(
            action=action,
            confidence=confidence,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            strategy_name=strategy_name,
            reason=f"ML {strategy_name} prediction: {pred_value:.3f}"
        )
