"""
Reddit sentiment analysis using PRAW
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Optional
import numpy as np
from rich.console import Console

try:
    import asyncpraw
    ASYNCPRAW_AVAILABLE = True
except ImportError:
    ASYNCPRAW_AVAILABLE = False
    logging.warning("asyncpraw not installed - Reddit analysis will be disabled")

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False

from cachetools import TTLCache
from ...intelligence.models import SocialSentiment


class RedditSentimentAnalyzer:
    """
    Analyzes Reddit sentiment for cryptocurrency symbols
    
    Features:
    - Multi-subreddit search
    - Sentiment analysis
    - Upvote/comment weighted scoring
    - Caching
    """
    
    def __init__(self, credentials: Optional[dict] = None, config: dict = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # Check if Reddit is available
        if not ASYNCPRAW_AVAILABLE:
            self.logger.warning("Reddit analysis disabled - asyncpraw not installed")
            self.enabled = False
            return
        
        if not credentials:
            self.logger.warning("Reddit analysis disabled - no credentials provided")
            self.enabled = False
            return
        
        # Temporarily disable Reddit due to AsyncPRAW timeout context issues
        self.logger.warning("Reddit analysis temporarily disabled due to AsyncPRAW timeout context issues")
        self.enabled = False
        return
        
        try:
            self.reddit = asyncpraw.Reddit(
                client_id=credentials.get('client_id'),
                client_secret=credentials.get('client_secret'),
                user_agent=credentials.get('user_agent', 'CryptoBot/2.0'),
                ratelimit_seconds=300  # Allow up to 5 minutes of automatic rate limit handling
            )
            self.enabled = True
        except Exception as e:
            self.logger.error(f"Failed to initialize Reddit client: {e}")
            self.enabled = False
            return
        
        # Configuration
        self.cache_ttl = self.config.get('cache_ttl_seconds', 600)  # 10 minutes
        self.subreddits = self.config.get('subreddits', [
            'cryptocurrency',
            'cryptomarkets',
            'bitcoin',
            'ethereum'
        ])
        self.max_results_per_sub = self.config.get('max_results_per_sub', 25)
        
        # State
        self.cache = TTLCache(maxsize=1000, ttl=self.cache_ttl)
        self.request_count = 0
        
        # Rate limiting (matching CoinMarketCap pattern)
        self.backoff_until_ts = 0.0
        self.backoff_seconds = 0
        self.backoff_cap = 600  # 10 minutes cap
        self.console = Console()
    
    async def get_sentiment(self, symbol: str) -> SocialSentiment:
        """
        Get Reddit sentiment for a cryptocurrency symbol
        
        Args:
            symbol: Cryptocurrency symbol (e.g., 'BTC', 'ETH')
            
        Returns:
            SocialSentiment object
        """
        if not self.enabled:
            return SocialSentiment.default()
        
        # Check if rate limited (matching CoinMarketCap pattern)
        if time.time() < self.backoff_until_ts:
            return SocialSentiment.default()
        
        # Check cache
        cache_key = f"reddit_{symbol.upper()}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            # Search across multiple subreddits
            all_sentiments = []
            all_weights = []
            total_posts = 0
            
            for subreddit_name in self.subreddits:
                try:
                    sentiments, weights = await self._analyze_subreddit(
                        subreddit_name,
                        symbol
                    )
                    all_sentiments.extend(sentiments)
                    all_weights.extend(weights)
                    total_posts += len(sentiments)
                except Exception as e:
                    self.logger.warning(f"Error analyzing r/{subreddit_name}: {e}")
                    continue
            
            if not all_sentiments:
                result = SocialSentiment(
                    score=0.0,
                    volume=0,
                    confidence=0.0,
                    sources=['reddit'],
                    timestamp=datetime.now(timezone.utc)
                )
                self.cache[cache_key] = result
                return result
            
            # Calculate weighted average
            avg_sentiment = np.average(all_sentiments, weights=all_weights)
            
            # Calculate confidence
            std_sentiment = np.std(all_sentiments)
            volume_confidence = min(1.0, total_posts / 50)
            agreement_confidence = 1.0 - min(1.0, std_sentiment)
            confidence = (volume_confidence + agreement_confidence) / 2
            
            result = SocialSentiment(
                score=float(avg_sentiment),
                volume=total_posts,
                confidence=float(confidence),
                sources=['reddit'],
                timestamp=datetime.now(timezone.utc)
            )
            
            self.cache[cache_key] = result
            self.request_count += 1
            return result
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check for rate limiting errors (matching CoinMarketCap pattern)
            if any(phrase in error_msg for phrase in ['rate limit', 'too many requests', '429', 'throttled']):
                # Exponential backoff starting at 120s
                self.backoff_seconds = min(
                    max(120, self.backoff_seconds * 2 or 120), self.backoff_cap
                )
                self.backoff_until_ts = time.time() + self.backoff_seconds
                self.console.print(
                    f"[yellow]Reddit rate-limited. Backing off for {self.backoff_seconds}s.[/yellow]"
                )
                return SocialSentiment(
                    score=0.0,
                    volume=0,
                    confidence=0.0,
                    sources=['reddit'],
                    error="Rate limited"
                )
            
            self.logger.error(f"Reddit API error for {symbol}: {e}")
            return SocialSentiment(
                score=0.0,
                volume=0,
                confidence=0.0,
                sources=['reddit'],
                error=str(e)
            )
    
    async def _analyze_subreddit(self, subreddit_name: str, symbol: str) -> tuple:
        """
        Analyze sentiment in a specific subreddit
        
        Returns:
            Tuple of (sentiments, weights)
        """
        sentiments = []
        weights = []
        
        try:
            subreddit = await self.reddit.subreddit(subreddit_name)
            
            # Search for posts with proper async handling
            search_query = f"{symbol} OR ${symbol}"
            submissions = subreddit.search(
                search_query,
                time_filter='day',
                limit=self.max_results_per_sub
            )
            
            # Convert async generator to list to avoid timeout context issues
            submission_list = []
            async for submission in submissions:
                submission_list.append(submission)
            
            for submission in submission_list:
                # Combine title and selftext for sentiment analysis
                text = f"{submission.title} {submission.selftext}"
                
                # Sentiment analysis
                if TEXTBLOB_AVAILABLE:
                    sentiment = TextBlob(text).sentiment.polarity
                else:
                    sentiment = self._simple_sentiment(text)
                
                # Weight by engagement
                weight = submission.score + submission.num_comments
                
                sentiments.append(sentiment)
                weights.append(max(weight, 1.0))
            
            return sentiments, weights
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check for rate limiting errors (matching CoinMarketCap pattern)
            if any(phrase in error_msg for phrase in ['rate limit', 'too many requests', '429', 'throttled']):
                # Exponential backoff starting at 120s
                self.backoff_seconds = min(
                    max(120, self.backoff_seconds * 2 or 120), self.backoff_cap
                )
                self.backoff_until_ts = time.time() + self.backoff_seconds
                self.console.print(
                    f"[yellow]Reddit rate-limited. Backing off for {self.backoff_seconds}s.[/yellow]"
                )
                return [], []
            
            self.logger.error(f"Error searching r/{subreddit_name}: {e}")
            return [], []
    
    def _simple_sentiment(self, text: str) -> float:
        """Simple sentiment analysis fallback"""
        text_lower = text.lower()
        
        positive_words = ['bullish', 'moon', 'pump', 'buy', 'long', 'up', 'gain', 'profit']
        negative_words = ['bearish', 'dump', 'sell', 'short', 'down', 'loss', 'crash']
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        total = positive_count + negative_count
        if total == 0:
            return 0.0
        
        return (positive_count - negative_count) / total
    
    def get_stats(self) -> dict:
        """Get statistics"""
        return {
            'enabled': self.enabled,
            'request_count': self.request_count,
            'cache_size': len(self.cache),
            'subreddits': self.subreddits,
            'rate_limited': time.time() < self.backoff_until_ts,
            'backoff_until_ts': self.backoff_until_ts
        }
