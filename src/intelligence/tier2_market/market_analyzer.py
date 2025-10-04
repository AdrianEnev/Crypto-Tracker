"""
Tier 2: Market Intelligence

Analyzes market conditions by combining:
- Market regime (trending/ranging/volatile)
- Social sentiment (Twitter, Reddit)
- Orderbook microstructure
- On-chain signals (optional)
- Derivatives signals (optional)
"""

import asyncio
import logging
from typing import Optional

from ..base import BaseIntelligence
from ..models import (
    MarketState,
    SocialSentiment,
    OrderbookSignal,
    OnChainSignal,
    DerivativesSignal
)


class MarketIntelligence(BaseIntelligence):
    """
    Aggregates market intelligence from multiple sources
    
    Provides comprehensive market state assessment for tactical decisions
    """
    
    def __init__(self, config: dict, data_feeds, ml_models=None):
        super().__init__(config, logger_name=__name__)
        
        self.data_feeds = data_feeds
        self.ml_models = ml_models
        
        # Configuration
        self.social_weight = config.get('social_weight', 0.3)
        self.orderbook_weight = config.get('orderbook_weight', 0.3)
        self.regime_weight = config.get('regime_weight', 0.4)
        
        self.min_confidence_threshold = config.get('min_confidence_threshold', 0.4)
        self.min_liquidity_for_trading = config.get('min_liquidity', 10000)
    
    async def analyze(self, coin_id: str, symbol: str = None) -> MarketState:
        """
        Analyze market state for a coin
        
        Args:
            coin_id: Coin identifier (e.g., 'bitcoin')
            symbol: Trading symbol (e.g., 'BTC/USDT')
            
        Returns:
            MarketState with comprehensive analysis
        """
        # Use coin_id as symbol if not provided
        if not symbol:
            symbol = self._coin_id_to_symbol(coin_id)
        
        try:
            # Gather all intelligence in parallel
            results = await asyncio.gather(
                self._get_regime(coin_id),
                self._get_social_sentiment(coin_id),
                self._get_orderbook_signal(symbol),
                self._get_onchain_signal(coin_id),
                self._get_derivatives_signal(symbol),
                return_exceptions=True
            )
            
            regime, social, orderbook, onchain, derivatives = results
            
            # Handle failures gracefully
            regime = self._safe_result(regime, ('UNKNOWN', 0.0))
            social = self._safe_result(social, SocialSentiment.default())
            orderbook = self._safe_result(orderbook, OrderbookSignal.default())
            onchain = self._safe_result(onchain, OnChainSignal.default())
            derivatives = self._safe_result(derivatives, DerivativesSignal.default())
            
            # Compute market state
            market_state = self._compute_market_state(
                regime, social, orderbook, onchain, derivatives
            )
            
            self.record_success()
            return market_state
            
        except Exception as e:
            self.logger.error(f"Market intelligence failed for {coin_id}: {e}")
            self.record_failure(e)
            return MarketState.default()
    
    async def _get_regime(self, coin_id: str) -> tuple:
        """
        Get market regime classification
        
        Returns:
            Tuple of (regime_name, confidence)
        """
        try:
            if self.ml_models and hasattr(self.ml_models, 'regime_classifier'):
                # Use ML regime classifier if available
                regime_result = await self.ml_models.regime_classifier.classify(coin_id)
                return (regime_result.get('regime', 'UNKNOWN'), regime_result.get('confidence', 0.0))
            else:
                # Fallback to simple regime detection
                return await self._simple_regime_detection(coin_id)
        except Exception as e:
            self.logger.warning(f"Regime detection failed: {e}")
            return ('UNKNOWN', 0.0)
    
    async def _simple_regime_detection(self, coin_id: str) -> tuple:
        """
        Simple regime detection based on volatility
        
        This is a fallback when ML models aren't available
        """
        try:
            # Get recent price data (would need access to price history)
            # For now, return neutral
            return ('RANGING', 0.5)
        except Exception:
            return ('UNKNOWN', 0.0)
    
    async def _get_social_sentiment(self, coin_id: str) -> SocialSentiment:
        """Get aggregated social sentiment"""
        try:
            if hasattr(self.data_feeds, 'social'):
                symbol = self._coin_id_to_trading_symbol(coin_id)
                return await self.data_feeds.social.get_aggregated_sentiment(symbol)
            return SocialSentiment.default()
        except Exception as e:
            self.logger.warning(f"Social sentiment failed: {e}")
            return SocialSentiment.default()
    
    async def _get_orderbook_signal(self, symbol: str) -> OrderbookSignal:
        """Get orderbook analysis"""
        try:
            if hasattr(self.data_feeds, 'orderbook'):
                signal = await self.data_feeds.orderbook.analyze(symbol)
                self.logger.info(f"Orderbook signal for {symbol}: spread_bps={signal.spread_bps}, is_liquid={signal.is_liquid}")
                return signal
            else:
                self.logger.warning(f"No orderbook feed available for {symbol}, using default")
                default_signal = OrderbookSignal.default()
                self.logger.info(f"Default orderbook signal for {symbol}: spread_bps={default_signal.spread_bps}, is_liquid={default_signal.is_liquid}")
                return default_signal
        except Exception as e:
            self.logger.warning(f"Orderbook analysis failed: {e}")
            fallback_signal = OrderbookSignal.default()
            self.logger.info(f"Fallback orderbook signal for {symbol}: spread_bps={fallback_signal.spread_bps}, is_liquid={fallback_signal.is_liquid}")
            return fallback_signal
    
    async def _get_onchain_signal(self, coin_id: str) -> OnChainSignal:
        """Get on-chain signals using free APIs + LLM analysis"""
        try:
            if hasattr(self.data_feeds, 'onchain'):
                # Get social sentiment for enhanced analysis
                social_sentiment = None
                if hasattr(self.data_feeds, 'social'):
                    try:
                        social_data = await self.data_feeds.social.get_aggregated_sentiment(coin_id)
                        social_sentiment = {
                            'overall': {'score': social_data.score},
                            'confidence': social_data.confidence
                        }
                    except Exception as e:
                        self.logger.debug(f"Could not get social sentiment for on-chain analysis: {e}")
                
                return await self.data_feeds.onchain.analyze(coin_id, social_sentiment)
            return OnChainSignal.default()
        except Exception as e:
            self.logger.warning(f"On-chain analysis failed: {e}")
            return OnChainSignal.default()
    
    async def _get_derivatives_signal(self, symbol: str) -> DerivativesSignal:
        """Get derivatives signals (optional)"""
        try:
            if hasattr(self.data_feeds, 'derivatives'):
                return await self.data_feeds.derivatives.analyze(symbol)
            return DerivativesSignal.default()
        except Exception:
            return DerivativesSignal.default()
    
    def _compute_market_state(
        self,
        regime: tuple,
        social: SocialSentiment,
        orderbook: OrderbookSignal,
        onchain: OnChainSignal,
        derivatives: DerivativesSignal
    ) -> MarketState:
        """
        Compute overall market state from all signals
        
        Returns:
            MarketState object
        """
        regime_name, regime_confidence = regime
        
        # Debug: Log orderbook signal details
        self.logger.info(f"Computing market state with orderbook: spread_bps={orderbook.spread_bps}, is_liquid={orderbook.is_liquid}, is_favorable={orderbook.is_favorable}")
        
        # Compute overall confidence
        confidence = self._compute_confidence(
            regime_confidence, social, orderbook
        )
        
        # Compute risk multiplier
        risk_multiplier = self._compute_risk_multiplier(
            regime_name, social, orderbook
        )
        
        # Determine if market is tradeable
        is_tradeable, reason = self._is_tradeable(
            confidence, orderbook, social
        )
        
        return MarketState(
            regime=regime_name,
            regime_confidence=regime_confidence,
            social_sentiment=social,
            orderbook_signal=orderbook,
            onchain_signal=onchain,
            derivatives_signal=derivatives,
            is_tradeable=is_tradeable,
            reason=reason,
            confidence=confidence,
            risk_multiplier=risk_multiplier
        )
    
    def _compute_confidence(
        self,
        regime_confidence: float,
        social: SocialSentiment,
        orderbook: OrderbookSignal
    ) -> float:
        """
        Compute weighted confidence from all sources
        
        Returns:
            Overall confidence (0-1)
        """
        # Weighted average of confidences
        confidence = (
            regime_confidence * self.regime_weight +
            social.confidence * self.social_weight +
            (1.0 if orderbook.is_liquid else 0.0) * self.orderbook_weight
        )
        
        # If social and orderbook are unavailable, boost confidence from regime
        if social.confidence == 0.0 and not orderbook.is_liquid:
            # Give more weight to regime when other sources are unavailable
            confidence = regime_confidence * 0.8  # 80% of regime confidence
        
        return min(1.0, max(0.0, confidence))
    
    def _compute_risk_multiplier(
        self,
        regime: str,
        social: SocialSentiment,
        orderbook: OrderbookSignal
    ) -> float:
        """
        Compute risk multiplier based on market conditions
        
        Returns:
            Risk multiplier (0-1.5)
        """
        multiplier = 1.0
        
        # Regime adjustments
        if regime == 'TRENDING':
            multiplier *= 1.2  # Increase size in trends
        elif regime == 'VOLATILE':
            multiplier *= 0.7  # Reduce size in volatility
        elif regime == 'RANGING':
            multiplier *= 0.9  # Slightly reduce in ranging
        
        # Social sentiment adjustments
        if abs(social.score) > 0.7 and social.confidence > 0.6:
            # Strong sentiment with high confidence
            multiplier *= 1.1
        elif social.confidence < 0.3:
            # Low confidence in sentiment
            multiplier *= 0.9
        
        # Orderbook adjustments
        if not orderbook.is_liquid:
            multiplier *= 0.5  # Significantly reduce if illiquid
        elif orderbook.spread_bps > 30:
            multiplier *= 0.8  # Reduce if wide spread
        
        return min(1.5, max(0.0, multiplier))
    
    def _is_tradeable(
        self,
        confidence: float,
        orderbook: OrderbookSignal,
        social: SocialSentiment
    ) -> tuple:
        """
        Determine if market conditions are favorable for trading
        
        Returns:
            Tuple of (is_tradeable, reason)
        """
        # Debug: Log orderbook details in tradeable check
        self.logger.info(f"Tradeable check: confidence={confidence:.2f}, orderbook.spread_bps={orderbook.spread_bps}, orderbook.is_liquid={orderbook.is_liquid}")
        
        # Check confidence threshold
        if confidence < self.min_confidence_threshold:
            return False, f"Low confidence: {confidence:.2f}"
        
        # Check orderbook liquidity
        if not orderbook.is_liquid:
            return False, f"Insufficient liquidity (spread: {orderbook.spread_bps:.1f} bps)"
        
        # Check if orderbook is favorable
        if not orderbook.is_favorable:
            return False, "Unfavorable orderbook structure"
        
        # All checks passed
        return True, "Favorable market conditions"
    
    def _coin_id_to_symbol(self, coin_id: str) -> str:
        """Convert coin_id to trading symbol"""
        # Mapping based on config.yaml tracked_coins
        mapping = {
            'bitcoin': 'BTC/USDT',
            'ethereum': 'ETH/USDT',
            'tether': 'BTC/USDT',  # Skip USDT orderbook analysis, use BTC as proxy
            'usd-coin': 'USDC/USDT',
            'binance-coin': 'BNB/USDT',
            'xrp': 'XRP/USDT',
            'solana': 'SOL/USDT',
            'cardano': 'ADA/USDT',
            'dogecoin': 'DOGE/USDT',
            'polkadot': 'DOT/USDT',
            'tron': 'TRX/USDT',
            'avalanche': 'AVAX/USDT',
            'shiba-inu': 'SHIB/USDT',
            'litecoin': 'LTC/USDT',
            'chainlink': 'LINK/USDT',
            'bitcoin-cash': 'BCH/USDT',
            'uniswap': 'UNI/USDT',
            'aptos': 'APT/USDT',
            'sui': 'SUI/USDT',
            'near-protocol': 'NEAR/USDT',
            'cosmos': 'ATOM/USDT',
            'stellar': 'XLM/USDT',
            'internet-computer': 'ICP/USDT'
        }
        return mapping.get(coin_id.lower(), f"{coin_id.upper()}/USDT")
    
    def _coin_id_to_trading_symbol(self, coin_id: str) -> str:
        """Convert coin_id to ticker symbol for social media"""
        mapping = {
            'bitcoin': 'BTC',
            'ethereum': 'ETH',
            'binancecoin': 'BNB',
            'cardano': 'ADA',
            'solana': 'SOL'
        }
        return mapping.get(coin_id.lower(), coin_id.upper()[:3])
    
    def _safe_result(self, result, default):
        """Return result if not an exception, otherwise return default"""
        if isinstance(result, Exception):
            self.logger.warning(f"Component failed: {result}")
            return default
        return result
