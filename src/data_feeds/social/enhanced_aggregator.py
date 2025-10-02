"""
Enhanced Social Media Aggregator with LLM Analysis

Combines traditional sentiment analysis with LLM-enhanced analysis for superior insights.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from ...intelligence.models import SocialSentiment
from .twitter_analyzer import TwitterSentimentAnalyzer
from .reddit_analyzer import RedditSentimentAnalyzer
from .llm_sentiment_analyzer import LLMSentimentAnalyzer


@dataclass
class SocialMediaPost:
    """Container for social media post data."""
    text: str
    source: str  # 'twitter' or 'reddit'
    timestamp: datetime
    score: Optional[int] = None  # upvotes, likes, etc.
    num_comments: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class EnhancedSocialMediaAggregator:
    """
    Enhanced social media aggregator with LLM analysis.
    
    Features:
    - Traditional sentiment analysis (keyword-based)
    - LLM-enhanced sentiment analysis
    - Trend detection and momentum analysis
    - Context-aware sentiment scoring
    - Sarcasm and irony detection
    - Market-specific sentiment breakdown
    """
    
    def __init__(self, config: Dict[str, Any], llm_client=None):
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Initialize traditional analyzers
        twitter_config = config.get('twitter', {})
        reddit_config = config.get('reddit', {})
        
        self.twitter = TwitterSentimentAnalyzer(
            bearer_token=twitter_config.get('api_key'),
            config=twitter_config
        )
        
        self.reddit = RedditSentimentAnalyzer(
            credentials=reddit_config.get('credentials'),
            config=reddit_config
        )
        
        # Initialize LLM analyzer
        self.llm_analyzer = None
        if llm_client and config.get('use_llm_analysis', True):
            self.llm_analyzer = LLMSentimentAnalyzer(llm_client, config)
        
        # Weights for aggregation
        self.twitter_weight = config.get('twitter_weight', 0.6)
        self.reddit_weight = config.get('reddit_weight', 0.4)
        self.llm_weight = config.get('llm_weight', 0.7)  # Weight for LLM vs traditional analysis
        
        # Cache for previous analyses (for trend detection)
        self.previous_analyses = {}
        self.cache_ttl = config.get('cache_ttl_seconds', 300)  # 5 minutes
    
    async def get_aggregated_sentiment(self, symbol: str) -> SocialSentiment:
        """
        Get enhanced sentiment analysis combining traditional and LLM methods.
        
        Args:
            symbol: Cryptocurrency symbol
            
        Returns:
            Enhanced SocialSentiment with LLM analysis
        """
        try:
            # Get raw posts from both sources
            posts = await self._collect_posts(symbol)
            
            if not posts:
                return SocialSentiment.default()
            
            # Get traditional sentiment analysis
            traditional_sentiment = await self._get_traditional_sentiment(symbol)
            
            # Get LLM-enhanced analysis
            llm_sentiment = None
            if self.llm_analyzer:
                previous_analysis = self.previous_analyses.get(symbol)
                llm_sentiment = await self.llm_analyzer.analyze_sentiment(
                    symbol, posts, previous_analysis
                )
                
                # Cache for trend analysis
                self.previous_analyses[symbol] = {
                    'timestamp': datetime.now(timezone.utc),
                    'sentiment': llm_sentiment.score,
                    'confidence': llm_sentiment.confidence,
                    'metadata': llm_sentiment.metadata
                }
            
            # Combine analyses
            if llm_sentiment:
                enhanced_sentiment = self._combine_analyses(
                    traditional_sentiment, llm_sentiment
                )
            else:
                enhanced_sentiment = traditional_sentiment
            
            return enhanced_sentiment
            
        except Exception as e:
            self.logger.error(f"Enhanced sentiment analysis failed for {symbol}: {e}")
            return SocialSentiment.default()
    
    async def _collect_posts(self, symbol: str) -> List[SocialMediaPost]:
        """Collect posts from both Twitter and Reddit."""
        posts = []
        
        try:
            # Get Twitter posts
            if self.twitter.enabled:
                twitter_posts = await self._get_twitter_posts(symbol)
                posts.extend(twitter_posts)
            
            # Get Reddit posts
            if self.reddit.enabled:
                reddit_posts = await self._get_reddit_posts(symbol)
                posts.extend(reddit_posts)
                
        except Exception as e:
            self.logger.warning(f"Post collection failed: {e}")
        
        return posts
    
    async def _get_twitter_posts(self, symbol: str) -> List[SocialMediaPost]:
        """Get Twitter posts for analysis."""
        try:
            # This would need to be implemented in TwitterSentimentAnalyzer
            # For now, return empty list
            return []
        except Exception as e:
            self.logger.warning(f"Twitter post collection failed: {e}")
            return []
    
    async def _get_reddit_posts(self, symbol: str) -> List[SocialMediaPost]:
        """Get Reddit posts for analysis."""
        try:
            # This would need to be implemented in RedditSentimentAnalyzer
            # For now, return empty list
            return []
        except Exception as e:
            self.logger.warning(f"Reddit post collection failed: {e}")
            return []
    
    async def _get_traditional_sentiment(self, symbol: str) -> SocialSentiment:
        """Get traditional sentiment analysis."""
        try:
            # Fetch from both sources in parallel
            results = await asyncio.gather(
                self.twitter.get_sentiment(symbol),
                self.reddit.get_sentiment(symbol),
                return_exceptions=True
            )
            
            twitter_sentiment, reddit_sentiment = results
            
            # Handle failures gracefully
            if isinstance(twitter_sentiment, Exception):
                self.logger.warning(f"Twitter failed: {twitter_sentiment}")
                twitter_sentiment = SocialSentiment.default()
            
            if isinstance(reddit_sentiment, Exception):
                self.logger.warning(f"Reddit failed: {reddit_sentiment}")
                reddit_sentiment = SocialSentiment.default()
            
            # If both failed, return default
            total_volume = twitter_sentiment.volume + reddit_sentiment.volume
            if total_volume == 0:
                return SocialSentiment.default()
            
            # Weighted aggregation
            twitter_w = self.twitter_weight
            reddit_w = self.reddit_weight
            
            # Adjust weights if one source has no data
            if twitter_sentiment.volume == 0:
                twitter_w = 0.0
                reddit_w = 1.0
            elif reddit_sentiment.volume == 0:
                twitter_w = 1.0
                reddit_w = 0.0
            
            # Calculate weighted average
            avg_score = (
                twitter_sentiment.score * twitter_w +
                reddit_sentiment.score * reddit_w
            )
            
            avg_confidence = (
                twitter_sentiment.confidence * twitter_w +
                reddit_sentiment.confidence * reddit_w
            )
            
            # Combine sources
            sources = []
            if twitter_sentiment.volume > 0:
                sources.append('twitter')
            if reddit_sentiment.volume > 0:
                sources.append('reddit')
            
            return SocialSentiment(
                score=avg_score,
                volume=total_volume,
                confidence=avg_confidence,
                sources=sources,
                timestamp=datetime.now(timezone.utc),
                metadata={
                    'twitter_sentiment': twitter_sentiment.score,
                    'reddit_sentiment': reddit_sentiment.score,
                    'twitter_confidence': twitter_sentiment.confidence,
                    'reddit_confidence': reddit_sentiment.confidence,
                    'analysis_type': 'traditional'
                }
            )
            
        except Exception as e:
            self.logger.error(f"Traditional sentiment analysis failed: {e}")
            return SocialSentiment.default()
    
    def _combine_analyses(
        self, 
        traditional_sentiment: SocialSentiment, 
        llm_sentiment: SocialSentiment
    ) -> SocialSentiment:
        """Combine traditional and LLM analyses."""
        
        # Weight the analyses
        traditional_weight = 1.0 - self.llm_weight
        llm_weight = self.llm_weight
        
        # Combine scores
        combined_score = (
            traditional_sentiment.score * traditional_weight +
            llm_sentiment.score * llm_weight
        )
        
        # Combine confidence (take the higher one, but weight it)
        combined_confidence = max(
            traditional_sentiment.confidence * traditional_weight,
            llm_sentiment.confidence * llm_weight
        )
        
        # Combine sources
        combined_sources = list(set(traditional_sentiment.sources + llm_sentiment.sources))
        
        # Combine metadata
        combined_metadata = {
            'analysis_type': 'enhanced',
            'traditional_score': traditional_sentiment.score,
            'llm_score': llm_sentiment.score,
            'traditional_confidence': traditional_sentiment.confidence,
            'llm_confidence': llm_sentiment.confidence,
            'llm_weight': llm_weight,
            'traditional_weight': traditional_weight
        }
        
        # Add LLM-specific metadata
        if llm_sentiment.metadata:
            combined_metadata.update(llm_sentiment.metadata)
        
        return SocialSentiment(
            score=combined_score,
            volume=max(traditional_sentiment.volume, llm_sentiment.volume),
            confidence=combined_confidence,
            sources=combined_sources,
            timestamp=datetime.now(timezone.utc),
            metadata=combined_metadata
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get aggregator statistics."""
        return {
            'twitter_stats': self.twitter.get_stats(),
            'reddit_stats': self.reddit.get_stats(),
            'llm_analyzer_stats': self.llm_analyzer.get_stats() if self.llm_analyzer else None,
            'llm_weight': self.llm_weight,
            'twitter_weight': self.twitter_weight,
            'reddit_weight': self.reddit_weight,
            'cached_analyses': len(self.previous_analyses)
        }
