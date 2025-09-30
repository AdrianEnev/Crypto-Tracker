"""
Bitcoin Fundamental Strategy - Designed for Bitcoin's unique market dynamics.
Considers macro trends, institutional flows, and fundamental factors beyond technical analysis.
"""

import pandas as pd
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import requests
import json

from .base import BaseStrategy
from ..indicators.core import ema, rsi, atr


class BitcoinFundamentalStrategy(BaseStrategy):
    """
    Bitcoin-specific strategy that considers:
    - Macro economic indicators
    - Institutional adoption signals
    - Market structure analysis
    - Long-term trend continuation
    - Political/regulatory sentiment
    """
    
    def __init__(self, strategy_config: dict):
        super().__init__(strategy_config)
        
        # Technical parameters (as backup)
        self.fast_ema_period = self.config.get("fast_ema_period", 21)
        self.slow_ema_period = self.config.get("slow_ema_period", 50)
        self.rsi_period = self.config.get("rsi_period", 14)
        
        # Fundamental parameters
        self.macro_weight = self.config.get("macro_weight", 0.4)  # Weight for macro factors
        self.technical_weight = self.config.get("technical_weight", 0.3)  # Weight for technical
        self.sentiment_weight = self.config.get("sentiment_weight", 0.3)  # Weight for sentiment
        
        # Bitcoin-specific thresholds
        self.btc_dominance_threshold = self.config.get("btc_dominance_threshold", 45.0)
        self.institutional_threshold = self.config.get("institutional_threshold", 0.7)
        self.macro_bullish_threshold = self.config.get("macro_bullish_threshold", 0.6)
        
        # External data sources (can be enhanced)
        self.use_external_data = self.config.get("use_external_data", False)
        
    def _get_macro_sentiment(self) -> float:
        """
        Get macro economic sentiment score (0-1).
        Higher = more bullish for Bitcoin.
        """
        try:
            # This is a placeholder - can be enhanced with real macro data
            # Examples: DXY, Fed rates, inflation data, etc.
            
            # For now, return a neutral score
            # In production, this would fetch:
            # - DXY (Dollar Strength Index)
            # - Fed interest rates
            # - Inflation data
            # - Stock market volatility (VIX)
            # - Gold prices
            
            return 0.5  # Neutral macro sentiment
            
        except Exception:
            return 0.5
    
    def _get_bitcoin_dominance_trend(self, data: pd.DataFrame) -> float:
        """
        Analyze Bitcoin dominance trend.
        Higher dominance = more bullish for Bitcoin.
        """
        try:
            # This would typically fetch BTC dominance data
            # For now, use price momentum as proxy
            closes = data["close"].tolist()
            if len(closes) < 20:
                return 0.5
                
            # Calculate price momentum over different timeframes
            short_momentum = (closes[-1] - closes[-5]) / closes[-5] if len(closes) >= 5 else 0
            medium_momentum = (closes[-1] - closes[-20]) / closes[-20] if len(closes) >= 20 else 0
            
            # Combine momentum signals
            momentum_score = (short_momentum * 0.3 + medium_momentum * 0.7)
            
            # Convert to 0-1 scale
            return max(0, min(1, 0.5 + momentum_score * 2))
            
        except Exception:
            return 0.5
    
    def _get_institutional_sentiment(self) -> float:
        """
        Get institutional adoption sentiment (0-1).
        Higher = more institutional buying pressure.
        """
        try:
            # This would typically fetch:
            # - ETF flows
            # - Corporate treasury purchases
            # - Institutional custody data
            # - Futures positioning
            
            # For now, return bullish bias (Bitcoin is in institutional adoption phase)
            return 0.7  # Slightly bullish institutional sentiment
            
        except Exception:
            return 0.5
    
    def _get_regulatory_sentiment(self) -> float:
        """
        Get regulatory/political sentiment (0-1).
        Higher = more favorable regulatory environment.
        """
        try:
            # This would typically fetch:
            # - Regulatory news sentiment
            # - Political statements
            # - Legal developments
            # - Country adoption rates
            
            # For now, return neutral (can be enhanced with news APIs)
            return 0.5
            
        except Exception:
            return 0.5
    
    def _calculate_fundamental_score(self, data: pd.DataFrame) -> float:
        """
        Calculate overall fundamental score (0-1).
        """
        try:
            macro_score = self._get_macro_sentiment()
            dominance_score = self._get_bitcoin_dominance_trend(data)
            institutional_score = self._get_institutional_sentiment()
            regulatory_score = self._get_regulatory_sentiment()
            
            # Weighted combination
            fundamental_score = (
                macro_score * 0.25 +
                dominance_score * 0.35 +
                institutional_score * 0.25 +
                regulatory_score * 0.15
            )
            
            return fundamental_score
            
        except Exception:
            return 0.5
    
    def _calculate_technical_score(self, data: pd.DataFrame) -> float:
        """
        Calculate technical analysis score (0-1).
        """
        try:
            closes = data["close"].tolist()
            if len(closes) < max(self.slow_ema_period, self.rsi_period):
                return 0.5
                
            # Calculate EMAs
            fast_ema = ema(closes, self.fast_ema_period)
            slow_ema = ema(closes, self.slow_ema_period)
            rsi_values = rsi(closes, self.rsi_period)
            
            if not fast_ema or not slow_ema or not rsi_values:
                return 0.5
                
            # Get latest values
            latest_fast = fast_ema[-1]
            latest_slow = slow_ema[-1]
            latest_rsi = rsi_values[-1]
            
            if latest_fast is None or latest_slow is None or latest_rsi is None:
                return 0.5
            
            technical_score = 0.5  # Base score
            
            # EMA trend
            if latest_fast > latest_slow:
                technical_score += 0.2  # Bullish trend
            else:
                technical_score -= 0.1  # Bearish trend
                
            # RSI momentum
            if latest_rsi < 70:  # Not overbought
                technical_score += 0.1
            if latest_rsi > 30:  # Not oversold
                technical_score += 0.1
                
            # Price above/below EMAs
            current_price = closes[-1]
            if current_price > latest_fast:
                technical_score += 0.1
            if current_price > latest_slow:
                technical_score += 0.1
                
            return max(0, min(1, technical_score))
            
        except Exception:
            return 0.5
    
    def _calculate_sentiment_score(self, data: pd.DataFrame) -> float:
        """
        Calculate market sentiment score (0-1).
        """
        try:
            # This would typically fetch:
            # - Fear & Greed Index
            # - Social media sentiment
            # - Options flow
            # - Funding rates
            
            # For now, use price volatility as sentiment proxy
            closes = data["close"].tolist()
            if len(closes) < 10:
                return 0.5
                
            # Calculate recent volatility
            recent_closes = closes[-10:]
            volatility = 0
            for i in range(1, len(recent_closes)):
                volatility += abs((recent_closes[i] - recent_closes[i-1]) / recent_closes[i-1])
            
            volatility /= len(recent_closes) - 1
            
            # High volatility = high sentiment (excitement/fear)
            # Moderate volatility = balanced sentiment
            if volatility > 0.05:  # High volatility
                return 0.7
            elif volatility > 0.02:  # Moderate volatility
                return 0.5
            else:  # Low volatility
                return 0.3
                
        except Exception:
            return 0.5
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate signals based on fundamental analysis with technical confirmation.
        """
        signals = pd.DataFrame(index=data.index)
        signals["signal"] = 0
        
        try:
            # Calculate component scores
            fundamental_score = self._calculate_fundamental_score(data)
            technical_score = self._calculate_technical_score(data)
            sentiment_score = self._calculate_sentiment_score(data)
            
            # Weighted overall score
            overall_score = (
                fundamental_score * self.macro_weight +
                technical_score * self.technical_weight +
                sentiment_score * self.sentiment_weight
            )
            
            # Generate signals based on overall score
            # More aggressive thresholds for Bitcoin's fundamental strength
            buy_threshold = 0.6  # Lower threshold for buying
            sell_threshold = 0.4  # Higher threshold for selling
            
            # Apply signals
            for i in range(len(data)):
                if overall_score > buy_threshold:
                    signals.iloc[i]["signal"] = 1  # Buy
                elif overall_score < sell_threshold:
                    signals.iloc[i]["signal"] = -1  # Sell
                else:
                    signals.iloc[i]["signal"] = 0  # Hold
            
            # Add confidence metadata
            signals["fundamental_score"] = fundamental_score
            signals["technical_score"] = technical_score
            signals["sentiment_score"] = sentiment_score
            signals["overall_score"] = overall_score
            
            return signals
            
        except Exception as e:
            # Fallback to neutral signals
            signals["signal"] = 0
            signals["fundamental_score"] = 0.5
            signals["technical_score"] = 0.5
            signals["sentiment_score"] = 0.5
            signals["overall_score"] = 0.5
            return signals
