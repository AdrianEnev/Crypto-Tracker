"""
Twitter sentiment analysis using Twitter API v2
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
import numpy as np
from rich.console import Console

try:
    import tweepy
    TWEEPY_AVAILABLE = True
except ImportError:
    TWEEPY_AVAILABLE = False
    logging.warning("tweepy not installed - Twitter analysis will be disabled")

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False
    logging.warning("textblob not installed - using simple sentiment analysis")

from cachetools import TTLCache
from ...intelligence.models import SocialSentiment


class TwitterSentimentAnalyzer:
    """
    Analyzes Twitter sentiment for cryptocurrency symbols
    
    Features:
    - Real-time tweet search
    - Sentiment analysis using TextBlob
    - Engagement-weighted scoring
    - Rate limit handling
    - Caching to reduce API calls
    """
    
    def __init__(self, bearer_token: Optional[str] = None, config: dict = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # Check if Twitter is available
        if not TWEEPY_AVAILABLE:
            self.logger.warning("Twitter analysis disabled - tweepy not installed")
            self.enabled = False
            return
        
        # Get bearer token from parameter or config
        if not bearer_token:
            bearer_token = self.config.get('api_key') or self.config.get('bearer_token')
        
        if not bearer_token:
            self.logger.warning("Twitter analysis disabled - no API key provided")
            self.enabled = False
            return
        
        try:
            self.client = tweepy.Client(bearer_token=bearer_token)
            self.enabled = True
        except Exception as e:
            self.logger.error(f"Failed to initialize Twitter client: {e}")
            self.enabled = False
            return
        
        # Configuration
        self.cache_ttl = self.config.get('cache_ttl_seconds', 300)  # 5 minutes
        self.max_results = self.config.get('max_results', 100)
        self.rate_limit_pause_minutes = self.config.get('rate_limit_pause_minutes', 15)
        
        # State
        self.cache = TTLCache(maxsize=1000, ttl=self.cache_ttl)
        self.rate_limit_reset: Optional[datetime] = None
        self.request_count = 0
        
        # Rate limiting (matching CoinMarketCap pattern)
        self.backoff_until_ts = 0.0
        self.backoff_seconds = 0
        self.backoff_cap = 600  # 10 minutes cap
        self.console = Console()
    
    async def get_sentiment(self, symbol: str) -> SocialSentiment:
        """
        Get Twitter sentiment for a cryptocurrency symbol
        
        Args:
            symbol: Cryptocurrency symbol (e.g., 'BTC', 'ETH')
            
        Returns:
            SocialSentiment object with score, volume, and confidence
        """
        if not self.enabled:
            return SocialSentiment.default()
        
        # Check cache
        cache_key = f"twitter_{symbol.upper()}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Check rate limit (matching CoinMarketCap pattern)
        if time.time() < self.backoff_until_ts:
            return SocialSentiment.default()
        
        try:
            # Search tweets
            query = self._build_query(symbol)
            tweets = await self._search_tweets(query)
            
            if not tweets or len(tweets) == 0:
                result = SocialSentiment(
                    score=0.0,
                    volume=0,
                    confidence=0.0,
                    sources=['twitter'],
                    timestamp=datetime.now(timezone.utc)
                )
                self.cache[cache_key] = result
                return result
            
            # Analyze sentiment
            sentiments, weights = self._analyze_tweets(tweets)
            
            # Calculate weighted average
            avg_sentiment = np.average(sentiments, weights=weights)
            
            # Calculate confidence based on volume and agreement
            std_sentiment = np.std(sentiments)
            volume_confidence = min(1.0, len(sentiments) / self.max_results)
            agreement_confidence = 1.0 - min(1.0, std_sentiment)
            confidence = (volume_confidence + agreement_confidence) / 2
            
            result = SocialSentiment(
                score=float(avg_sentiment),
                volume=len(sentiments),
                confidence=float(confidence),
                sources=['twitter'],
                timestamp=datetime.now(timezone.utc)
            )
            
            self.cache[cache_key] = result
            self.request_count += 1
            return result
            
        except tweepy.errors.TooManyRequests:
            # Exponential backoff starting at 120s (matching CoinMarketCap pattern)
            self.backoff_seconds = min(
                max(120, self.backoff_seconds * 2 or 120), self.backoff_cap
            )
            self.backoff_until_ts = time.time() + self.backoff_seconds
            self.console.print(
                f"[yellow]Twitter rate-limited. Backing off for {self.backoff_seconds}s.[/yellow]"
            )
            return SocialSentiment.default()
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check for rate limiting errors (matching CoinMarketCap pattern)
            if any(phrase in error_msg for phrase in ['rate limit', 'too many requests', '429', 'throttled', 'unauthorized']):
                # Exponential backoff starting at 120s
                self.backoff_seconds = min(
                    max(120, self.backoff_seconds * 2 or 120), self.backoff_cap
                )
                self.backoff_until_ts = time.time() + self.backoff_seconds
                self.console.print(
                    f"[yellow]Twitter rate-limited. Backing off for {self.backoff_seconds}s.[/yellow]"
                )
                return SocialSentiment(
                    score=0.0,
                    volume=0,
                    confidence=0.0,
                    sources=['twitter'],
                    error="Rate limited"
                )
            
            self.logger.error(f"Twitter API error for {symbol}: {e}")
            return SocialSentiment(
                score=0.0,
                volume=0,
                confidence=0.0,
                sources=['twitter'],
                error=str(e)
            )
    
    def _build_query(self, symbol: str) -> str:
        """Build Twitter search query"""
        # Search for both $ and # mentions
        return f"(${symbol} OR #{symbol}) lang:en -is:retweet -is:reply"
    
    async def _search_tweets(self, query: str) -> list:
        """Search tweets using Twitter API"""
        try:
            response = self.client.search_recent_tweets(
                query=query,
                max_results=self.max_results,
                tweet_fields=['created_at', 'public_metrics', 'author_id']
            )
            
            return response.data if response.data else []
            
        except Exception as e:
            self.logger.error(f"Tweet search failed: {e}")
            raise
    
    def _analyze_tweets(self, tweets: list) -> tuple:
        """
        Analyze sentiment of tweets
        
        Returns:
            Tuple of (sentiments, weights)
        """
        sentiments = []
        weights = []
        
        for tweet in tweets:
            # Sentiment analysis
            if TEXTBLOB_AVAILABLE:
                sentiment = TextBlob(tweet.text).sentiment.polarity
            else:
                sentiment = self._simple_sentiment(tweet.text)
            
            # Weight by engagement
            metrics = tweet.public_metrics
            weight = (
                metrics.get('like_count', 0) * 1.0 +
                metrics.get('retweet_count', 0) * 2.0 +
                metrics.get('reply_count', 0) * 0.5 +
                metrics.get('quote_count', 0) * 1.5
            )
            
            sentiments.append(sentiment)
            weights.append(max(weight, 1.0))  # Minimum weight of 1
        
        return sentiments, weights
    
    def _simple_sentiment(self, text: str) -> float:
        """
        Simple sentiment analysis without TextBlob
        (fallback method)
        """
        text_lower = text.lower()
        
        # Positive words
        positive_words = ['bullish', 'moon', 'pump', 'buy', 'long', 'up', 'gain', 'profit', 'win']
        # Negative words
        negative_words = ['bearish', 'dump', 'sell', 'short', 'down', 'loss', 'crash', 'rekt']
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        total = positive_count + negative_count
        if total == 0:
            return 0.0
        
        return (positive_count - negative_count) / total
    
    
    def get_stats(self) -> dict:
        """Get statistics about Twitter analyzer"""
        return {
            'enabled': self.enabled,
            'request_count': self.request_count,
            'cache_size': len(self.cache),
            'rate_limited': time.time() < self.backoff_until_ts,
            'backoff_until_ts': self.backoff_until_ts
        }
