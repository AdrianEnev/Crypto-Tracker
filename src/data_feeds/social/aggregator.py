"""
Social Media Aggregator - combines sentiment from multiple sources
"""

import asyncio
import logging
from typing import Optional

from ...intelligence.models import SocialSentiment
from .twitter_analyzer import TwitterSentimentAnalyzer
from .reddit_analyzer import RedditSentimentAnalyzer


class SocialMediaAggregator:
    """
    Aggregates sentiment from multiple social media sources
    
    Features:
    - Parallel fetching from Twitter and Reddit
    - Weighted aggregation
    - Graceful degradation if sources fail
    """
    
    def __init__(self, config: dict):
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Initialize analyzers
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
        
        # Weights for aggregation
        self.twitter_weight = config.get('twitter_weight', 0.6)
        self.reddit_weight = config.get('reddit_weight', 0.4)
    
    async def get_aggregated_sentiment(self, symbol: str) -> SocialSentiment:
        """
        Get aggregated sentiment from all sources
        
        Args:
            symbol: Cryptocurrency symbol
            
        Returns:
            Aggregated SocialSentiment
        """
        # Fetch from all sources in parallel
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
            sources=sources
        )
    
    def get_stats(self) -> dict:
        """Get statistics from all sources"""
        return {
            'twitter': self.twitter.get_stats(),
            'reddit': self.reddit.get_stats()
        }
