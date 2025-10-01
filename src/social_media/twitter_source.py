#!/usr/bin/env python3
"""
Twitter API Integration for Crypto Discovery

Replaces expensive LunarCrush with free Twitter API for social metrics.
Uses Twitter API v2 free tier (10,000 tweets/month).
"""

import asyncio
import aiohttp
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
import json
import re

from .config import SocialMediaConfig
from .base import BaseSocialDataSource, SocialDataPoint, SocialDataBatch, RateLimiter

logger = logging.getLogger(__name__)


class TwitterSource(BaseSocialDataSource):
    """Twitter API data source for social metrics (free tier)"""
    
    def __init__(self, config: SocialMediaConfig):
        super().__init__(config, "twitter")
        self.api_key = config.twitter.api_key
        self.bearer_token = config.twitter.bearer_token
        self.base_url = "https://api.twitter.com/2"
        
        # Initialize rate limiter (free tier: 10,000 tweets/month)
        self.rate_limiter = RateLimiter(
            config.twitter.rate_limit, 
            3600  # 1 hour window
        )
    
    async def fetch_data(self, coin_id: str, data_types: List[str]) -> SocialDataBatch:
        """Fetch Twitter data for a coin"""
        # Skip if no bearer token configured
        if not self.bearer_token:
            logger.debug("Twitter API not configured, skipping...")
            return SocialDataBatch(coin_id, [], self.source_name, datetime.now())
            
        try:
            await self.rate_limiter.acquire()
            
            # Check cache first
            cache_key = f"twitter_{coin_id}_{datetime.now().strftime('%Y%m%d%H')}"
            cached_data = await self._get_smart_cached_data(coin_id, "twitter", {"data_types": data_types})
            if cached_data:
                return cached_data
            
            # Prepare search terms
            search_terms = self._get_search_terms(coin_id)
            
            # Fetch tweets
            tweets = await self._fetch_tweets(search_terms)
            
            # Process tweets for metrics
            data_points = []
            
            if tweets:
                # Calculate social volume
                social_volume = len(tweets)
                data_points.append(SocialDataPoint(
                    timestamp=datetime.now(),
                    source=self.source_name,
                    coin_id=coin_id,
                    data_type="social_volume",
                    value=social_volume,
                    confidence=0.9
                ))
                
                # Calculate sentiment
                sentiment_score = self._calculate_sentiment(tweets)
                data_points.append(SocialDataPoint(
                    timestamp=datetime.now(),
                    source=self.source_name,
                    coin_id=coin_id,
                    data_type="sentiment_score",
                    value=sentiment_score,
                    confidence=0.8
                ))
                
                # Calculate engagement metrics
                engagement_score = self._calculate_engagement(tweets)
                data_points.append(SocialDataPoint(
                    timestamp=datetime.now(),
                    source=self.source_name,
                    coin_id=coin_id,
                    data_type="engagement_score",
                    value=engagement_score,
                    confidence=0.8
                ))
                
                # Calculate influencer activity
                influencer_score = self._calculate_influencer_activity(tweets)
                data_points.append(SocialDataPoint(
                    timestamp=datetime.now(),
                    source=self.source_name,
                    coin_id=coin_id,
                    data_type="influencer_activity",
                    value=influencer_score,
                    confidence=0.7
                ))
            
            batch = SocialDataBatch(
                coin_id=coin_id,
                data_points=data_points,
                source=self.source_name,
                timestamp=datetime.now(),
                quality_score=0.8 if tweets else 0.3
            )
            
            # Cache the data using smart cache
            await self._cache_smart_data(coin_id, "twitter", batch, {"data_types": data_types})
            return batch
            
        except Exception as e:
            logger.error(f"Twitter fetch failed for {coin_id}: {e}")
            return SocialDataBatch(coin_id, [], self.source_name, datetime.now())
    
    async def _fetch_tweets(self, search_terms: List[str]) -> List[Dict[str, Any]]:
        """Fetch tweets from Twitter API v2"""
        try:
            headers = {
                "Authorization": f"Bearer {self.bearer_token}",
                "User-Agent": "CryptoDiscoveryScanner/1.0"
            }
            
            # Combine search terms
            query = " OR ".join(search_terms)
            
            params = {
                "query": f"{query} -is:retweet lang:en",
                "max_results": 100,  # Free tier limit
                "tweet.fields": "created_at,public_metrics,author_id",
                "user.fields": "public_metrics,verified",
                "expansions": "author_id"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/tweets/search/recent",
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self.config.twitter.timeout)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        return data.get("data", [])
                    elif response.status == 429:  # Rate limited
                        logger.warning(f"Twitter API rate limited, backing off...")
                        await asyncio.sleep(300)  # Wait 5 minutes
                        return []
                    elif response.status == 400:  # Bad request
                        logger.warning(f"Twitter API bad request (400), skipping...")
                        return []
                    else:
                        logger.error(f"Twitter API error: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error fetching tweets: {e}")
            return []
    
    def _get_search_terms(self, coin_id: str) -> List[str]:
        """Get search terms for a coin"""
        term_map = {
            "bitcoin": ["bitcoin", "btc", "$btc"],
            "ethereum": ["ethereum", "eth", "$eth"],
            "binancecoin": ["binance", "bnb", "$bnb"],
            "cardano": ["cardano", "ada", "$ada"],
            "solana": ["solana", "sol", "$sol"],
            "polkadot": ["polkadot", "dot", "$dot"],
            "chainlink": ["chainlink", "link", "$link"],
            "dogecoin": ["dogecoin", "doge", "$doge"],
            "shiba-inu": ["shiba inu", "shib", "$shib"],
            "avalanche-2": ["avalanche", "avax", "$avax"],
            "polygon": ["polygon", "matic", "$matic"],
            "cosmos": ["cosmos", "atom", "$atom"],
            "litecoin": ["litecoin", "ltc", "$ltc"],
            "monero": ["monero", "xmr", "$xmr"],
            "tron": ["tron", "trx", "$trx"]
        }
        return term_map.get(coin_id.lower(), [coin_id])
    
    def _calculate_sentiment(self, tweets: List[Dict[str, Any]]) -> float:
        """Calculate sentiment score from tweets"""
        if not tweets:
            return 0.0
        
        # Simple keyword-based sentiment
        positive_words = [
            "bullish", "moon", "pump", "gains", "up", "rise", "increase",
            "breakthrough", "adoption", "partnership", "launch", "success",
            "positive", "optimistic", "growth", "innovation", "milestone",
            "buy", "hodl", "diamond hands", "to the moon"
        ]
        
        negative_words = [
            "bearish", "dump", "crash", "drop", "fall", "down", "decline",
            "concern", "risk", "warning", "negative", "pessimistic", "loss",
            "sell", "panic", "fud", "scam", "fraud", "regulation", "ban"
        ]
        
        total_sentiment = 0.0
        tweet_count = 0
        
        for tweet in tweets:
            text = tweet.get("text", "").lower()
            
            positive_count = sum(1 for word in positive_words if word in text)
            negative_count = sum(1 for word in negative_words if word in text)
            
            if positive_count + negative_count > 0:
                tweet_sentiment = (positive_count - negative_count) / (positive_count + negative_count)
                total_sentiment += tweet_sentiment
                tweet_count += 1
        
        if tweet_count == 0:
            return 0.0
        
        return max(-1.0, min(1.0, total_sentiment / tweet_count))
    
    def _calculate_engagement(self, tweets: List[Dict[str, Any]]) -> float:
        """Calculate engagement score from tweets"""
        if not tweets:
            return 0.0
        
        total_engagement = 0.0
        
        for tweet in tweets:
            metrics = tweet.get("public_metrics", {})
            engagement = (
                metrics.get("like_count", 0) +
                metrics.get("retweet_count", 0) * 2 +  # Retweets worth more
                metrics.get("reply_count", 0) * 1.5 +  # Replies worth more
                metrics.get("quote_count", 0) * 2.5    # Quotes worth most
            )
            total_engagement += engagement
        
        # Normalize by number of tweets
        avg_engagement = total_engagement / len(tweets)
        
        # Scale to 0-1 range (adjust based on typical engagement)
        return min(1.0, avg_engagement / 1000.0)
    
    def _calculate_influencer_activity(self, tweets: List[Dict[str, Any]]) -> float:
        """Calculate influencer activity score"""
        if not tweets:
            return 0.0
        
        influencer_tweets = 0
        total_tweets = len(tweets)
        
        for tweet in tweets:
            # Check if author has high follower count (simplified)
            author_id = tweet.get("author_id")
            if author_id:
                # In real implementation, check user metrics
                # For now, use engagement as proxy
                metrics = tweet.get("public_metrics", {})
                total_engagement = (
                    metrics.get("like_count", 0) +
                    metrics.get("retweet_count", 0) +
                    metrics.get("reply_count", 0) +
                    metrics.get("quote_count", 0)
                )
                
                # High engagement = likely influencer
                if total_engagement > 100:
                    influencer_tweets += 1
        
        return influencer_tweets / total_tweets if total_tweets > 0 else 0.0
