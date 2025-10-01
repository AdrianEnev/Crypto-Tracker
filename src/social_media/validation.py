"""
Social Signal Validation

Validates social media signals against on-chain data, derivatives, and volume.
Includes manipulation detection and safety checks.
All validation is configurable and can be disabled independently.
"""

import asyncio
import aiohttp
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
import statistics
import numpy as np

from .config import SocialMediaConfig
from .features import SocialFeatureSet


logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of social signal validation"""
    is_valid: bool
    validation_score: float
    confidence: float
    details: Dict[str, Any]
    recommendation: str
    risk_level: str  # "low", "medium", "high"
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class OnChainData:
    """On-chain data for validation"""
    coin_id: str
    timestamp: datetime
    exchange_netflow: Optional[float] = None
    whale_movements: Optional[float] = None
    network_activity: Optional[float] = None
    confidence: float = 1.0


@dataclass
class DerivativesData:
    """Derivatives data for validation"""
    coin_id: str
    timestamp: datetime
    funding_rate: Optional[float] = None
    futures_basis: Optional[float] = None
    options_skew: Optional[float] = None
    confidence: float = 1.0


class OnChainValidator:
    """Validates social signals against on-chain data"""
    
    def __init__(self, config: SocialMediaConfig):
        self.config = config
        self.validation_config = config.validation
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def validate_social_signal(self, coin_id: str, social_features: SocialFeatureSet) -> ValidationResult:
        """Validate social signal against on-chain data"""
        if not self.validation_config.enabled or not self.validation_config.require_onchain_confirmation:
            return ValidationResult(
                is_valid=True,
                validation_score=1.0,
                confidence=1.0,
                details={"reason": "On-chain validation disabled"},
                recommendation="proceed",
                risk_level="low"
            )
        
        try:
            # Fetch on-chain data
            onchain_data = await self._fetch_onchain_data(coin_id)
            
            if not onchain_data:
                logger.warning(f"No on-chain data available for {coin_id}")
                return ValidationResult(
                    is_valid=False,
                    validation_score=0.0,
                    confidence=0.0,
                    details={"reason": "No on-chain data available"},
                    recommendation="hold",
                    risk_level="high"
                )
            
            # Perform validation checks
            validation_details = {}
            validation_scores = []
            
            # Check exchange flows
            if onchain_data.exchange_netflow is not None:
                flow_score = self._validate_exchange_flows(social_features, onchain_data)
                validation_details["exchange_flows"] = {
                    "score": flow_score,
                    "netflow": onchain_data.exchange_netflow,
                    "correlation": self._calculate_correlation(social_features.features.get("sms", 0), onchain_data.exchange_netflow)
                }
                validation_scores.append(flow_score)
            
            # Check whale movements
            if onchain_data.whale_movements is not None:
                whale_score = self._validate_whale_movements(social_features, onchain_data)
                validation_details["whale_movements"] = {
                    "score": whale_score,
                    "movement": onchain_data.whale_movements
                }
                validation_scores.append(whale_score)
            
            # Check network activity
            if onchain_data.network_activity is not None:
                activity_score = self._validate_network_activity(social_features, onchain_data)
                validation_details["network_activity"] = {
                    "score": activity_score,
                    "activity": onchain_data.network_activity
                }
                validation_scores.append(activity_score)
            
            # Calculate overall validation score
            if validation_scores:
                overall_score = statistics.mean(validation_scores)
                confidence = onchain_data.confidence
            else:
                overall_score = 0.5  # Neutral if no data
                confidence = 0.0
            
            # Determine recommendation
            is_valid = overall_score >= self.validation_config.min_validation_score
            recommendation = self._get_recommendation(overall_score, validation_details)
            risk_level = self._assess_risk_level(overall_score, validation_details)
            
            return ValidationResult(
                is_valid=is_valid,
                validation_score=overall_score,
                confidence=confidence,
                details=validation_details,
                recommendation=recommendation,
                risk_level=risk_level,
                metadata={
                    "onchain_data": onchain_data,
                    "validation_timestamp": datetime.now()
                }
            )
            
        except Exception as e:
            logger.error(f"On-chain validation failed for {coin_id}: {e}")
            return ValidationResult(
                is_valid=False,
                validation_score=0.0,
                confidence=0.0,
                details={"error": str(e)},
                recommendation="hold",
                risk_level="high"
            )
    
    async def _fetch_onchain_data(self, coin_id: str) -> Optional[OnChainData]:
        """Fetch on-chain data for a coin"""
        try:
            # For now, we'll simulate on-chain data
            # In a real implementation, you'd fetch from Glassnode, CryptoQuant, etc.
            
            # Simulate exchange netflow (negative = outflow = bullish)
            exchange_netflow = np.random.normal(0, 1000)  # Simulate random flow
            
            # Simulate whale movements (positive = large transfers)
            whale_movements = max(0, np.random.normal(100, 50))
            
            # Simulate network activity
            network_activity = max(0, np.random.normal(10000, 2000))
            
            return OnChainData(
                coin_id=coin_id,
                timestamp=datetime.now(),
                exchange_netflow=exchange_netflow,
                whale_movements=whale_movements,
                network_activity=network_activity,
                confidence=0.8  # Simulated data confidence
            )
            
        except Exception as e:
            logger.error(f"Failed to fetch on-chain data for {coin_id}: {e}")
            return None
    
    def _validate_exchange_flows(self, social_features: SocialFeatureSet, onchain_data: OnChainData) -> float:
        """Validate social sentiment against exchange flows"""
        try:
            sms = social_features.features.get("sms", 0)
            netflow = onchain_data.exchange_netflow
            
            # Negative netflow (outflow) with positive sentiment is bullish
            # Positive netflow (inflow) with negative sentiment is bearish
            if sms > 0 and netflow < 0:
                return 0.8  # Bullish alignment
            elif sms < 0 and netflow > 0:
                return 0.8  # Bearish alignment
            elif sms > 0 and netflow > 0:
                return 0.3  # Contradictory - sentiment bullish but inflow bearish
            elif sms < 0 and netflow < 0:
                return 0.3  # Contradictory - sentiment bearish but outflow bullish
            else:
                return 0.5  # Neutral
            
        except Exception as e:
            logger.error(f"Exchange flow validation failed: {e}")
            return 0.0
    
    def _validate_whale_movements(self, social_features: SocialFeatureSet, onchain_data: OnChainData) -> float:
        """Validate social sentiment against whale movements"""
        try:
            sms = social_features.features.get("sms", 0)
            whale_movements = onchain_data.whale_movements
            
            # High whale activity with positive sentiment suggests institutional interest
            if whale_movements > 200 and sms > 0.3:
                return 0.9  # Strong bullish signal
            elif whale_movements > 200 and sms < -0.3:
                return 0.1  # Strong bearish signal
            elif whale_movements < 50:
                return 0.6  # Low whale activity, neutral
            else:
                return 0.5  # Moderate whale activity
            
        except Exception as e:
            logger.error(f"Whale movement validation failed: {e}")
            return 0.0
    
    def _validate_network_activity(self, social_features: SocialFeatureSet, onchain_data: OnChainData) -> float:
        """Validate social sentiment against network activity"""
        try:
            sms = social_features.features.get("sms", 0)
            network_activity = onchain_data.network_activity
            
            # High network activity with positive sentiment suggests adoption
            if network_activity > 15000 and sms > 0.2:
                return 0.8  # Strong adoption signal
            elif network_activity < 5000:
                return 0.4  # Low activity
            else:
                return 0.6  # Moderate activity
            
        except Exception as e:
            logger.error(f"Network activity validation failed: {e}")
            return 0.0
    
    def _calculate_correlation(self, social_value: float, onchain_value: float) -> float:
        """Calculate correlation between social and on-chain values"""
        try:
            # Simple correlation calculation
            if abs(social_value) < 0.01 or abs(onchain_value) < 0.01:
                return 0.0
            
            # Normalize values for correlation
            norm_social = social_value / max(abs(social_value), 1.0)
            norm_onchain = onchain_value / max(abs(onchain_value), 1.0)
            
            # Calculate simple correlation
            correlation = norm_social * norm_onchain
            return max(-1.0, min(1.0, correlation))
            
        except Exception as e:
            logger.error(f"Correlation calculation failed: {e}")
            return 0.0
    
    def _get_recommendation(self, validation_score: float, details: Dict[str, Any]) -> str:
        """Get trading recommendation based on validation score"""
        if validation_score >= 0.8:
            return "strong_buy" if details.get("exchange_flows", {}).get("netflow", 0) < 0 else "strong_sell"
        elif validation_score >= 0.6:
            return "buy" if details.get("exchange_flows", {}).get("netflow", 0) < 0 else "sell"
        elif validation_score >= 0.4:
            return "hold"
        else:
            return "avoid"
    
    def _assess_risk_level(self, validation_score: float, details: Dict[str, Any]) -> str:
        """Assess risk level based on validation results"""
        if validation_score >= 0.7:
            return "low"
        elif validation_score >= 0.4:
            return "medium"
        else:
            return "high"


class ManipulationDetector:
    """Detects potential manipulation in social signals"""
    
    def __init__(self, config: SocialMediaConfig):
        self.config = config
        self.validation_config = config.validation
    
    def detect_manipulation(self, social_features: SocialFeatureSet) -> Dict[str, Any]:
        """Detect potential manipulation in social features"""
        if not self.validation_config.manipulation_detection:
            return {
                "is_manipulated": False,
                "risk_score": 0.0,
                "indicators": {},
                "confidence": 1.0
            }
        
        try:
            indicators = {}
            risk_scores = []
            
            # Check for bot-like patterns
            bot_score = self._detect_bot_patterns(social_features)
            indicators["bot_patterns"] = bot_score
            risk_scores.append(bot_score)
            
            # Check for coordination patterns
            coordination_score = self._detect_coordination(social_features)
            indicators["coordination"] = coordination_score
            risk_scores.append(coordination_score)
            
            # Check for artificial volume spikes
            volume_spike_score = self._detect_volume_spikes(social_features)
            indicators["volume_spikes"] = volume_spike_score
            risk_scores.append(volume_spike_score)
            
            # Check for sentiment manipulation
            sentiment_manipulation_score = self._detect_sentiment_manipulation(social_features)
            indicators["sentiment_manipulation"] = sentiment_manipulation_score
            risk_scores.append(sentiment_manipulation_score)
            
            # Calculate overall risk score
            overall_risk = max(risk_scores) if risk_scores else 0.0
            
            # Determine if manipulation is detected
            is_manipulated = overall_risk >= self.validation_config.coordination_threshold
            
            return {
                "is_manipulated": is_manipulated,
                "risk_score": overall_risk,
                "indicators": indicators,
                "confidence": 0.8  # Moderate confidence in manipulation detection
            }
            
        except Exception as e:
            logger.error(f"Manipulation detection failed: {e}")
            return {
                "is_manipulated": False,
                "risk_score": 0.0,
                "indicators": {},
                "confidence": 0.0
            }
    
    def _detect_bot_patterns(self, social_features: SocialFeatureSet) -> float:
        """Detect bot-like patterns in social features"""
        try:
            bot_likeness = social_features.features.get("bot_likeness", 0)
            
            # High bot likeness score indicates potential manipulation
            if bot_likeness >= self.validation_config.bot_likeness_threshold:
                return bot_likeness
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"Bot pattern detection failed: {e}")
            return 0.0
    
    def _detect_coordination(self, social_features: SocialFeatureSet) -> float:
        """Detect coordinated activity patterns"""
        try:
            # Check for suspiciously high volume with low quality
            volume_velocity = social_features.features.get("volume_velocity", 0)
            quality_score = social_features.quality_score
            
            # High volume with low quality might indicate coordination
            if volume_velocity > 0.8 and quality_score < 0.5:
                return 0.8
            elif volume_velocity > 0.6 and quality_score < 0.7:
                return 0.5
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"Coordination detection failed: {e}")
            return 0.0
    
    def _detect_volume_spikes(self, social_features: SocialFeatureSet) -> float:
        """Detect artificial volume spikes"""
        try:
            volume_velocity = social_features.features.get("volume_velocity", 0)
            
            # Very high volume velocity might indicate artificial spikes
            if volume_velocity > 2.0:  # 2x normal volume
                return min(1.0, volume_velocity / 3.0)
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"Volume spike detection failed: {e}")
            return 0.0
    
    def _detect_sentiment_manipulation(self, social_features: SocialFeatureSet) -> float:
        """Detect sentiment manipulation patterns"""
        try:
            sentiment = social_features.features.get("weighted_sentiment", 0)
            cross_validation = social_features.features.get("cross_validation", 0)
            
            # Extreme sentiment with low cross-validation might indicate manipulation
            if abs(sentiment) > 0.8 and cross_validation < 0.3:
                return 0.8
            elif abs(sentiment) > 0.6 and cross_validation < 0.5:
                return 0.5
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"Sentiment manipulation detection failed: {e}")
            return 0.0


class SocialSignalValidator:
    """Main validator for social media signals"""
    
    def __init__(self, config: SocialMediaConfig):
        self.config = config
        self.validation_config = config.validation
        self.onchain_validator = OnChainValidator(config)
        self.manipulation_detector = ManipulationDetector(config)
    
    async def validate_signal(self, coin_id: str, social_features: SocialFeatureSet) -> ValidationResult:
        """Comprehensive validation of social signals"""
        if not self.validation_config.enabled:
            return ValidationResult(
                is_valid=True,
                validation_score=1.0,
                confidence=1.0,
                details={"reason": "Validation disabled"},
                recommendation="proceed",
                risk_level="low"
            )
        
        try:
            validation_details = {}
            validation_scores = []
            
            # 1. Check for manipulation
            manipulation_result = self.manipulation_detector.detect_manipulation(social_features)
            validation_details["manipulation"] = manipulation_result
            
            if manipulation_result["is_manipulated"]:
                # Apply manipulation penalty
                penalty = self.validation_config.manipulation_penalty
                validation_details["manipulation_penalty"] = penalty
                validation_scores.append(1.0 - penalty)  # Reduce validation score
            else:
                validation_scores.append(1.0)  # No penalty
            
            # 2. On-chain validation
            if self.validation_config.require_onchain_confirmation:
                async with self.onchain_validator:
                    onchain_result = await self.onchain_validator.validate_social_signal(coin_id, social_features)
                    validation_details["onchain"] = {
                        "is_valid": onchain_result.is_valid,
                        "score": onchain_result.validation_score,
                        "details": onchain_result.details
                    }
                    validation_scores.append(onchain_result.validation_score)
            
            # 3. Volume confirmation
            if self.validation_config.require_volume_confirmation:
                volume_score = self._validate_volume_confirmation(social_features)
                validation_details["volume"] = {"score": volume_score}
                validation_scores.append(volume_score)
            
            # 4. Derivatives confirmation (if enabled)
            if self.validation_config.require_derivatives_confirmation:
                derivatives_score = self._validate_derivatives_confirmation(social_features)
                validation_details["derivatives"] = {"score": derivatives_score}
                validation_scores.append(derivatives_score)
            
            # Calculate overall validation score
            if validation_scores:
                overall_score = statistics.mean(validation_scores)
            else:
                overall_score = 0.5  # Neutral if no validations
            
            # Determine final recommendation
            is_valid = overall_score >= self.validation_config.min_validation_score
            recommendation = self._get_final_recommendation(overall_score, validation_details)
            risk_level = self._assess_final_risk_level(overall_score, validation_details)
            
            # Calculate confidence
            confidence = self._calculate_validation_confidence(validation_details)
            
            return ValidationResult(
                is_valid=is_valid,
                validation_score=overall_score,
                confidence=confidence,
                details=validation_details,
                recommendation=recommendation,
                risk_level=risk_level,
                metadata={
                    "validation_timestamp": datetime.now(),
                    "coin_id": coin_id
                }
            )
            
        except Exception as e:
            logger.error(f"Signal validation failed for {coin_id}: {e}")
            return ValidationResult(
                is_valid=False,
                validation_score=0.0,
                confidence=0.0,
                details={"error": str(e)},
                recommendation="hold",
                risk_level="high"
            )
    
    def _validate_volume_confirmation(self, social_features: SocialFeatureSet) -> float:
        """Validate volume confirmation"""
        try:
            volume_velocity = social_features.features.get("volume_velocity", 0)
            
            # Higher volume velocity = better confirmation
            if volume_velocity > 0.5:
                return min(1.0, volume_velocity)
            else:
                return 0.3  # Low volume confirmation
                
        except Exception as e:
            logger.error(f"Volume validation failed: {e}")
            return 0.0
    
    def _validate_derivatives_confirmation(self, social_features: SocialFeatureSet) -> float:
        """Validate derivatives confirmation"""
        try:
            # For now, we'll simulate derivatives validation
            # In a real implementation, you'd check funding rates, futures basis, etc.
            
            sms = social_features.features.get("sms", 0)
            
            # Simulate derivatives alignment
            if sms > 0.3:
                return 0.7  # Bullish derivatives
            elif sms < -0.3:
                return 0.7  # Bearish derivatives
            else:
                return 0.5  # Neutral derivatives
                
        except Exception as e:
            logger.error(f"Derivatives validation failed: {e}")
            return 0.0
    
    def _get_final_recommendation(self, validation_score: float, details: Dict[str, Any]) -> str:
        """Get final trading recommendation"""
        # Check for manipulation first
        manipulation = details.get("manipulation", {})
        if manipulation.get("is_manipulated", False):
            return "avoid"
        
        # Check on-chain validation
        onchain = details.get("onchain", {})
        if not onchain.get("is_valid", True):
            return "hold"
        
        # Base recommendation on validation score
        if validation_score >= 0.8:
            return "strong_buy"
        elif validation_score >= 0.6:
            return "buy"
        elif validation_score >= 0.4:
            return "hold"
        else:
            return "avoid"
    
    def _assess_final_risk_level(self, validation_score: float, details: Dict[str, Any]) -> str:
        """Assess final risk level"""
        # Check for manipulation
        manipulation = details.get("manipulation", {})
        if manipulation.get("is_manipulated", False):
            return "high"
        
        # Check on-chain validation
        onchain = details.get("onchain", {})
        if not onchain.get("is_valid", True):
            return "high"
        
        # Base risk on validation score
        if validation_score >= 0.7:
            return "low"
        elif validation_score >= 0.4:
            return "medium"
        else:
            return "high"
    
    def _calculate_validation_confidence(self, details: Dict[str, Any]) -> float:
        """Calculate overall validation confidence"""
        try:
            confidences = []
            
            # Manipulation detection confidence
            manipulation = details.get("manipulation", {})
            confidences.append(manipulation.get("confidence", 0.5))
            
            # On-chain validation confidence
            onchain = details.get("onchain", {})
            if onchain:
                confidences.append(0.8)  # On-chain data is generally reliable
            
            # Volume validation confidence
            if details.get("volume"):
                confidences.append(0.7)  # Volume data is moderately reliable
            
            # Derivatives validation confidence
            if details.get("derivatives"):
                confidences.append(0.6)  # Derivatives data is less reliable
            
            if confidences:
                return statistics.mean(confidences)
            else:
                return 0.5  # Default confidence
                
        except Exception as e:
            logger.error(f"Confidence calculation failed: {e}")
            return 0.5
