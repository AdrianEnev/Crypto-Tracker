"""
Social Media Integration Example

This module demonstrates how to integrate social media signals into the trading system.
Shows how to enhance existing trading decisions with social media data.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from src.social_media import create_social_integration
from src.decision import Decision


logger = logging.getLogger(__name__)


class EnhancedDecisionEngine:
    """Enhanced decision engine that incorporates social media signals"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize enhanced decision engine"""
        self.social_integration = create_social_integration(config_path)
        self.social_enabled = self.social_integration.is_feature_enabled("features")
        
        if self.social_enabled:
            logger.info("Social media integration enabled for decision engine")
        else:
            logger.info("Social media integration disabled for decision engine")
    
    async def make_enhanced_decision(self, tracker, coin_id: str) -> Decision:
        """
        Make enhanced trading decision incorporating social media signals
        
        Args:
            tracker: The main CryptoTracker instance
            coin_id: Coin identifier
            
        Returns:
            Enhanced Decision object with social media context
        """
        try:
            # Get base technical decision
            base_decision = self._get_base_decision(tracker, coin_id)
            
            # Get social media signal if enabled
            social_signal = None
            if self.social_enabled:
                social_signal = await self.social_integration.get_social_signal(coin_id)
            
            # Enhance decision with social signals
            enhanced_decision = self._enhance_decision(base_decision, social_signal, coin_id)
            
            return enhanced_decision
            
        except Exception as e:
            logger.error(f"Enhanced decision failed for {coin_id}: {e}")
            # Fall back to base decision
            return self._get_base_decision(tracker, coin_id)
    
    def _get_base_decision(self, tracker, coin_id: str) -> Decision:
        """Get base technical decision"""
        try:
            from src.decision import make_decision
            return make_decision(tracker, coin_id)
        except Exception as e:
            logger.error(f"Base decision failed for {coin_id}: {e}")
            return Decision(
                signal="error",
                confidence=0.0,
                action_recommended="Hold",
                reason=f"Base decision error: {e}"
            )
    
    def _enhance_decision(self, base_decision: Decision, social_signal: Optional[Dict[str, Any]], 
                         coin_id: str) -> Decision:
        """Enhance base decision with social signals"""
        try:
            if not social_signal or not social_signal.get("enabled", False):
                # No social signal available, return base decision
                return base_decision
            
            # Extract social data
            social_features = social_signal.get("social_features", {})
            validation = social_signal.get("validation", {})
            quality = social_signal.get("quality", {})
            
            # Check if social signal is valid
            if not validation.get("is_valid", False):
                logger.warning(f"Social signal invalid for {coin_id}, using base decision")
                return base_decision
            
            # Check quality requirements
            quality_score = quality.get("quality_score", 0)
            if quality_score < 0.5:
                logger.warning(f"Social signal quality too low for {coin_id}: {quality_score}")
                return base_decision
            
            # Extract key metrics
            sms = social_features.get("sms", 0)
            sentiment = social_features.get("weighted_sentiment", 0)
            volume_velocity = social_features.get("volume_velocity", 0)
            bot_likeness = social_features.get("bot_likeness", 0)
            
            # Apply social enhancement logic
            enhanced_decision = self._apply_social_enhancement(
                base_decision, sms, sentiment, volume_velocity, bot_likeness, validation
            )
            
            return enhanced_decision
            
        except Exception as e:
            logger.error(f"Decision enhancement failed for {coin_id}: {e}")
            return base_decision
    
    def _apply_social_enhancement(self, base_decision: Decision, sms: float, sentiment: float,
                                 volume_velocity: float, bot_likeness: float, 
                                 validation: Dict[str, Any]) -> Decision:
        """Apply social media enhancement to trading decision"""
        try:
            # Start with base decision
            enhanced_decision = Decision(
                signal=base_decision.signal,
                confidence=base_decision.confidence,
                action_recommended=base_decision.action_recommended,
                reason=base_decision.reason
            )
            
            # Check for manipulation
            if bot_likeness > 0.7:
                logger.warning(f"High bot likelihood detected: {bot_likeness}")
                # Reduce confidence due to potential manipulation
                enhanced_decision.confidence *= 0.5
                enhanced_decision.reason += f" | Bot risk: {bot_likeness:.2f}"
                return enhanced_decision
            
            # Apply social momentum enhancement
            social_weight = 0.2  # Conservative weight for social signals
            
            # Enhance buy signals with positive social momentum
            if base_decision.action_recommended == "Buy" and sms > 0.3:
                enhanced_decision.confidence += social_weight * sms
                enhanced_decision.reason += f" | Social momentum: {sms:.2f}"
            
            # Enhance sell signals with negative social momentum
            elif base_decision.action_recommended == "Sell" and sms < -0.3:
                enhanced_decision.confidence += social_weight * abs(sms)
                enhanced_decision.reason += f" | Social momentum: {sms:.2f}"
            
            # Volume confirmation
            if volume_velocity > 1.5:  # High volume
                enhanced_decision.confidence += 0.1
                enhanced_decision.reason += f" | High volume: {volume_velocity:.2f}x"
            
            # Sentiment confirmation
            if abs(sentiment) > 0.5:  # Strong sentiment
                if (base_decision.action_recommended == "Buy" and sentiment > 0) or \
                   (base_decision.action_recommended == "Sell" and sentiment < 0):
                    enhanced_decision.confidence += 0.1
                    enhanced_decision.reason += f" | Sentiment: {sentiment:.2f}"
            
            # Apply validation penalty if needed
            validation_score = validation.get("validation_score", 1.0)
            if validation_score < 0.7:
                penalty = 1.0 - validation_score
                enhanced_decision.confidence *= (1.0 - penalty)
                enhanced_decision.reason += f" | Validation penalty: {penalty:.2f}"
            
            # Clamp confidence to valid range
            enhanced_decision.confidence = max(0.0, min(1.0, enhanced_decision.confidence))
            
            # Update signal based on enhanced confidence
            if enhanced_decision.confidence > 0.8:
                if base_decision.action_recommended == "Buy":
                    enhanced_decision.signal = "strong_buy"
                elif base_decision.action_recommended == "Sell":
                    enhanced_decision.signal = "strong_sell"
            elif enhanced_decision.confidence < 0.3:
                enhanced_decision.action_recommended = "Hold"
                enhanced_decision.signal = "low_confidence"
            
            return enhanced_decision
            
        except Exception as e:
            logger.error(f"Social enhancement application failed: {e}")
            return base_decision
    
    def get_social_status(self) -> Dict[str, Any]:
        """Get social media integration status"""
        return self.social_integration.get_configuration_status()
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on social integration"""
        return await self.social_integration.health_check()
    
    def get_monitoring_dashboard(self) -> Dict[str, Any]:
        """Get monitoring dashboard data"""
        return self.social_integration.get_monitoring_dashboard()


# Example usage function
async def example_social_integration():
    """Example of how to use social media integration"""
    
    # Initialize enhanced decision engine
    decision_engine = EnhancedDecisionEngine()
    
    # Check if social integration is enabled
    status = decision_engine.get_social_status()
    print(f"Social integration enabled: {status['enabled']}")
    
    if not status['enabled']:
        print("Social integration is disabled. Enable it in config/social_media.yaml")
        return
    
    # Perform health check
    health = await decision_engine.health_check()
    print(f"Health status: {health['overall']}")
    
    # Get monitoring dashboard
    dashboard = decision_engine.get_monitoring_dashboard()
    if dashboard.get('enabled'):
        print(f"Active alerts: {dashboard.get('metrics_summary', {}).get('active_alerts', 0)}")
        print(f"Coins tracked: {dashboard.get('metrics_summary', {}).get('total_coins_tracked', 0)}")
    
    # Example: Get social signal for Bitcoin
    social_integration = decision_engine.social_integration
    bitcoin_signal = await social_integration.get_social_signal("bitcoin")
    
    print(f"Bitcoin SMS: {bitcoin_signal.get('social_features', {}).get('sms', 0):.3f}")
    print(f"Bitcoin sentiment: {bitcoin_signal.get('social_features', {}).get('weighted_sentiment', 0):.3f}")
    print(f"Bitcoin validation: {bitcoin_signal.get('validation', {}).get('is_valid', False)}")


if __name__ == "__main__":
    # Run example
    asyncio.run(example_social_integration())
