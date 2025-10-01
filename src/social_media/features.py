"""
Social Media Feature Engineering

Creates social momentum features from raw social media data.
Includes sentiment analysis, volume calculations, and influence scoring.
All features are designed to be easily configurable and validated.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
import statistics

from .config import SocialMediaConfig
from .base import SocialDataBatch
from .data_sources import SocialDataManager


logger = logging.getLogger(__name__)


@dataclass
class SocialFeatureSet:
    """Complete set of social media features for a coin"""
    coin_id: str
    timestamp: datetime
    features: Dict[str, float]
    confidence: float
    quality_score: float
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SocialFeatureEngine:
    """Main engine for creating social media features"""
    
    def __init__(self, config: SocialMediaConfig, data_manager: SocialDataManager):
        self.config = config
        self.data_manager = data_manager
        self.feature_config = config.features
        
        # Feature calculation methods
        self.feature_calculators = {
            "volume_velocity": self._calculate_volume_velocity,
            "weighted_sentiment": self._calculate_weighted_sentiment,
            "influencer_activity": self._calculate_influencer_activity,
            "network_centrality": self._calculate_network_centrality,
            "bot_likeness": self._calculate_bot_likeness,
            "cross_validation": self._calculate_cross_validation
        }
    
    async def generate_features(self, coin_id: str, 
                              data_types: List[str] = None) -> SocialFeatureSet:
        """Generate complete social feature set for a coin"""
        if not self.feature_config.enabled:
            return self._create_empty_feature_set(coin_id)
        
        try:
            # Fetch raw data from all sources
            raw_data = await self.data_manager.fetch_all_data(
                coin_id, 
                data_types or ["social_volume", "sentiment_score", "influencer_activity"]
            )
            
            if not raw_data:
                logger.warning(f"No social data available for {coin_id}")
                return self._create_empty_feature_set(coin_id)
            
            # Calculate individual features
            features = {}
            feature_confidences = {}
            
            for feature_name, calculator in self.feature_calculators.items():
                try:
                    feature_value, confidence = await calculator(coin_id, raw_data)
                    features[feature_name] = feature_value
                    feature_confidences[feature_name] = confidence
                except Exception as e:
                    logger.error(f"Error calculating {feature_name} for {coin_id}: {e}")
                    features[feature_name] = 0.0
                    feature_confidences[feature_name] = 0.0
            
            # Calculate Social Momentum Score (SMS)
            sms = self._calculate_sms(features)
            
            # Calculate overall confidence and quality
            overall_confidence = statistics.mean(feature_confidences.values())
            quality_score = self._calculate_overall_quality(raw_data, features)
            
            # Add SMS to features
            features["sms"] = sms
            
            return SocialFeatureSet(
                coin_id=coin_id,
                timestamp=datetime.now(),
                features=features,
                confidence=overall_confidence,
                quality_score=quality_score,
                metadata={
                    "feature_confidences": feature_confidences,
                    "data_sources": list(raw_data.keys()),
                    "raw_data_quality": {k: v.quality_score for k, v in raw_data.items()}
                }
            )
            
        except Exception as e:
            logger.error(f"Feature generation failed for {coin_id}: {e}")
            return self._create_empty_feature_set(coin_id)
    
    def _create_empty_feature_set(self, coin_id: str) -> SocialFeatureSet:
        """Create empty feature set when no data is available"""
        empty_features = {name: 0.0 for name in self.feature_calculators.keys()}
        empty_features["sms"] = 0.0
        
        return SocialFeatureSet(
            coin_id=coin_id,
            timestamp=datetime.now(),
            features=empty_features,
            confidence=0.0,
            quality_score=0.0,
            metadata={"error": "No data available"}
        )
    
    async def _calculate_volume_velocity(self, coin_id: str, 
                                       raw_data: Dict[str, SocialDataBatch]) -> Tuple[float, float]:
        """Calculate mention volume velocity"""
        try:
            volume_data = []
            
            # Collect volume data from all sources
            for source_name, batch in raw_data.items():
                volume_point = batch.get_latest("social_volume")
                if volume_point and isinstance(volume_point.value, (int, float)):
                    volume_data.append(volume_point.value)
            
            if not volume_data:
                return 0.0, 0.0
            
            # Calculate velocity as rate of change
            current_volume = statistics.mean(volume_data)
            
            # For now, we'll use a simple velocity calculation
            # In a real implementation, you'd compare with historical data
            velocity = current_volume / 100.0  # Normalize
            
            # Confidence based on data availability and consistency
            confidence = min(1.0, len(volume_data) / 3.0)  # More sources = higher confidence
            
            return velocity, confidence
            
        except Exception as e:
            logger.error(f"Volume velocity calculation failed: {e}")
            return 0.0, 0.0
    
    async def _calculate_weighted_sentiment(self, coin_id: str, 
                                          raw_data: Dict[str, SocialDataBatch]) -> Tuple[float, float]:
        """Calculate weighted sentiment score"""
        try:
            sentiment_data = []
            weights = []
            
            # Collect sentiment data from all sources
            for source_name, batch in raw_data.items():
                sentiment_point = batch.get_latest("sentiment_score")
                if sentiment_point and isinstance(sentiment_point.value, (int, float)):
                    sentiment_data.append(sentiment_point.value)
                    weights.append(sentiment_point.confidence)
            
            if not sentiment_data:
                return 0.0, 0.0
            
            # Calculate weighted average sentiment
            if weights:
                weighted_sentiment = sum(s * w for s, w in zip(sentiment_data, weights)) / sum(weights)
            else:
                weighted_sentiment = statistics.mean(sentiment_data)
            
            # Normalize sentiment to [-1, 1] range
            normalized_sentiment = max(-1.0, min(1.0, weighted_sentiment / 100.0))
            
            # Confidence based on data quality and consistency
            confidence = statistics.mean(weights) if weights else 0.5
            
            return normalized_sentiment, confidence
            
        except Exception as e:
            logger.error(f"Weighted sentiment calculation failed: {e}")
            return 0.0, 0.0
    
    async def _calculate_influencer_activity(self, coin_id: str, 
                                           raw_data: Dict[str, SocialDataBatch]) -> Tuple[float, float]:
        """Calculate influencer activity score"""
        try:
            influencer_data = []
            
            # Collect influencer activity data
            for source_name, batch in raw_data.items():
                influencer_point = batch.get_latest("influencer_activity")
                if influencer_point and isinstance(influencer_point.value, (int, float)):
                    influencer_data.append(influencer_point.value)
            
            if not influencer_data:
                return 0.0, 0.0
            
            # Calculate activity score
            activity_score = statistics.mean(influencer_data)
            
            # Normalize based on threshold
            normalized_score = min(1.0, activity_score / self.feature_config.influencer_threshold)
            
            # Confidence based on data availability
            confidence = min(1.0, len(influencer_data) / 2.0)
            
            return normalized_score, confidence
            
        except Exception as e:
            logger.error(f"Influencer activity calculation failed: {e}")
            return 0.0, 0.0
    
    async def _calculate_network_centrality(self, coin_id: str, 
                                           raw_data: Dict[str, SocialDataBatch]) -> Tuple[float, float]:
        """Calculate network centrality metrics"""
        try:
            # For now, we'll simulate network centrality
            # In a real implementation, you'd analyze retweet networks, mention networks, etc.
            
            # Simple heuristic: more diverse sources = higher centrality
            source_count = len(raw_data)
            centrality_score = min(1.0, source_count / 5.0)  # Normalize to 5 sources max
            
            # Confidence based on data quality
            avg_quality = statistics.mean([batch.quality_score for batch in raw_data.values()])
            confidence = avg_quality * centrality_score
            
            return centrality_score, confidence
            
        except Exception as e:
            logger.error(f"Network centrality calculation failed: {e}")
            return 0.0, 0.0
    
    async def _calculate_bot_likeness(self, coin_id: str, 
                                    raw_data: Dict[str, SocialDataBatch]) -> Tuple[float, float]:
        """Calculate bot likelihood score (higher = more likely to be bots)"""
        try:
            # For now, we'll use a simple heuristic
            # In a real implementation, you'd analyze posting patterns, account metadata, etc.
            
            bot_indicators = []
            
            # Check for suspicious patterns in the data
            for source_name, batch in raw_data.items():
                # Simple heuristic: very high volume with low quality might indicate bots
                volume_point = batch.get_latest("social_volume")
                if volume_point and isinstance(volume_point.value, (int, float)):
                    if volume_point.value > 10000 and batch.quality_score < 0.5:
                        bot_indicators.append(0.8)  # High bot likelihood
                    elif volume_point.value > 5000 and batch.quality_score < 0.7:
                        bot_indicators.append(0.5)  # Medium bot likelihood
                    else:
                        bot_indicators.append(0.2)  # Low bot likelihood
            
            if not bot_indicators:
                return 0.0, 0.0
            
            bot_score = statistics.mean(bot_indicators)
            confidence = 0.7  # Moderate confidence in bot detection
            
            return bot_score, confidence
            
        except Exception as e:
            logger.error(f"Bot likeness calculation failed: {e}")
            return 0.0, 0.0
    
    async def _calculate_cross_validation(self, coin_id: str, 
                                        raw_data: Dict[str, SocialDataBatch]) -> Tuple[float, float]:
        """Calculate cross-validation score between sources"""
        try:
            if len(raw_data) < 2:
                return 0.0, 0.0  # Need at least 2 sources for cross-validation
            
            # Compare sentiment scores across sources
            sentiment_scores = []
            for source_name, batch in raw_data.items():
                sentiment_point = batch.get_latest("sentiment_score")
                if sentiment_point and isinstance(sentiment_point.value, (int, float)):
                    sentiment_scores.append(sentiment_point.value)
            
            if len(sentiment_scores) < 2:
                return 0.0, 0.0
            
            # Calculate correlation/consistency
            sentiment_std = statistics.stdev(sentiment_scores)
            sentiment_mean = statistics.mean(sentiment_scores)
            
            # Lower standard deviation = higher consistency = higher validation score
            consistency_score = max(0.0, 1.0 - (sentiment_std / max(abs(sentiment_mean), 1.0)))
            
            # Confidence based on number of sources and data quality
            avg_quality = statistics.mean([batch.quality_score for batch in raw_data.values()])
            confidence = avg_quality * min(1.0, len(raw_data) / 3.0)
            
            return consistency_score, confidence
            
        except Exception as e:
            logger.error(f"Cross-validation calculation failed: {e}")
            return 0.0, 0.0
    
    def _calculate_sms(self, features: Dict[str, float]) -> float:
        """Calculate Social Momentum Score"""
        try:
            sms = 0.0
            
            for feature_name, weight in self.feature_config.sms_weights.items():
                if feature_name in features:
                    sms += features[feature_name] * weight
            
            # Apply safety limits
            sms = max(-1.0, min(1.0, sms))  # Clamp to [-1, 1]
            
            return sms
            
        except Exception as e:
            logger.error(f"SMS calculation failed: {e}")
            return 0.0
    
    def _calculate_overall_quality(self, raw_data: Dict[str, SocialDataBatch], 
                                 features: Dict[str, float]) -> float:
        """Calculate overall quality score for the feature set"""
        try:
            # Base quality from raw data
            if not raw_data:
                return 0.0
            
            avg_data_quality = statistics.mean([batch.quality_score for batch in raw_data.values()])
            
            # Feature completeness
            expected_features = len(self.feature_calculators)
            actual_features = len([f for f in features.values() if f != 0.0])
            completeness = actual_features / expected_features
            
            # Data freshness
            now = datetime.now()
            max_age = max([(now - batch.timestamp).total_seconds() for batch in raw_data.values()])
            freshness = max(0.0, 1.0 - (max_age / self.feature_config.max_feature_age))
            
            # Overall quality score
            quality_score = (avg_data_quality + completeness + freshness) / 3.0
            
            return min(1.0, quality_score)
            
        except Exception as e:
            logger.error(f"Quality calculation failed: {e}")
            return 0.0
    
    def get_feature_names(self) -> List[str]:
        """Get list of all feature names"""
        return list(self.feature_calculators.keys()) + ["sms"]
    
    def validate_features(self, features: SocialFeatureSet) -> bool:
        """Validate feature set meets quality requirements"""
        if not self.feature_config.enabled:
            return True  # Features disabled, so validation passes
        
        # Check minimum data quality
        if features.quality_score < self.feature_config.min_data_quality:
            logger.warning(f"Feature quality too low for {features.coin_id}: {features.quality_score}")
            return False
        
        # Check feature age
        age_seconds = (datetime.now() - features.timestamp).total_seconds()
        if age_seconds > self.feature_config.max_feature_age:
            logger.warning(f"Features too old for {features.coin_id}: {age_seconds}s")
            return False
        
        # Check confidence
        if features.confidence < 0.5:
            logger.warning(f"Feature confidence too low for {features.coin_id}: {features.confidence}")
            return False
        
        return True
