"""
Reddit Data Source Implementation

Fetches data from Reddit API for cryptocurrency subreddits.
Replaces LunarCrush features with free Reddit data.
"""

import asyncio
import aiohttp
import base64
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .config import SocialMediaConfig
from .base import BaseSocialDataSource, SocialDataPoint, SocialDataBatch, RateLimiter


@dataclass
class RedditPost:
    """Reddit post data structure"""
    title: str
    selftext: str
    score: int
    upvote_ratio: float
    num_comments: int
    created_utc: float
    subreddit: str
    author: str
    url: str
    is_self: bool


class RedditSource(BaseSocialDataSource):
    """Reddit API data source for subreddit monitoring"""
    
    def __init__(self, config: SocialMediaConfig):
        super().__init__(config, "reddit")
        self.client_id = config.reddit.client_id
        self.client_secret = config.reddit.client_secret
        self.user_agent = config.reddit.user_agent
        self.subreddits = config.reddit.subreddits
        self.access_token = None
        
        # Initialize rate limiter (Reddit allows 60 requests per minute)
        self.rate_limiter = RateLimiter(60, 60)  # 60 requests per minute
        
    async def fetch_data(self, coin_id: str, data_types: List[str]) -> SocialDataBatch:
        """Fetch Reddit data for a coin"""
        # Skip if no client_id configured
        if not self.client_id:
            logger.debug("Reddit API not configured, skipping...")
            return SocialDataBatch(coin_id, [], self.source_name, datetime.now())
            
        try:
            await self.rate_limiter.acquire()
            
            # Check cache first
            cache_key = f"reddit_{coin_id}_{datetime.now().strftime('%Y%m%d%H')}"
            cached_data = await self._get_smart_cached_data(coin_id, "reddit", {"data_types": data_types})
            if cached_data:
                return cached_data
            
            # Get access token if needed
            if not self.access_token:
                await self._get_access_token()
            
            # Fetch posts from relevant subreddits
            posts = await self._fetch_posts(coin_id)
            
            # Process posts for metrics
            data_points = []
            
            if posts:
                # Calculate post volume
                post_volume = len(posts)
                data_points.append(SocialDataPoint(
                    timestamp=datetime.now(),
                    source=self.source_name,
                    coin_id=coin_id,
                    data_type="post_volume",
                    value=post_volume,
                    confidence=1.0,
                    metadata={"subreddits": list(set(post.subreddit for post in posts))}
                ))
                
                # Calculate sentiment score
                sentiment_score = self._calculate_sentiment(posts)
                data_points.append(SocialDataPoint(
                    timestamp=datetime.now(),
                    source=self.source_name,
                    coin_id=coin_id,
                    data_type="sentiment_score",
                    value=sentiment_score,
                    confidence=0.8,
                    metadata={"sample_size": len(posts)}
                ))
                
                # Calculate engagement score
                engagement_score = self._calculate_engagement(posts)
                data_points.append(SocialDataPoint(
                    timestamp=datetime.now(),
                    source=self.source_name,
                    coin_id=coin_id,
                    data_type="engagement_score",
                    value=engagement_score,
                    confidence=0.9,
                    metadata={"total_score": sum(post.score for post in posts)}
                ))
                
                # Identify hot topics
                hot_topics = self._identify_hot_topics(posts)
                data_points.append(SocialDataPoint(
                    timestamp=datetime.now(),
                    source=self.source_name,
                    coin_id=coin_id,
                    data_type="hot_topics",
                    value=len(hot_topics),
                    confidence=0.7,
                    metadata={"topics": hot_topics[:5]}  # Top 5 topics
                ))
            
            batch = SocialDataBatch(
                coin_id=coin_id,
                data_points=data_points,
                source=self.source_name,
                timestamp=datetime.now(),
                quality_score=0.8 if posts else 0.3
            )
            
            # Cache the data using smart cache
            await self._cache_smart_data(coin_id, "reddit", batch, {"data_types": data_types})
            return batch
            
        except Exception as e:
            logger.error(f"Reddit fetch failed for {coin_id}: {e}")
            return SocialDataBatch(coin_id, [], self.source_name, datetime.now())
    
    async def _get_access_token(self):
        """Get Reddit OAuth access token"""
        try:
            # Prepare credentials
            credentials = base64.b64encode(
                f"{self.client_id}:{self.client_secret}".encode()
            ).decode()
            
            headers = {
                "Authorization": f"Basic {credentials}",
                "User-Agent": self.user_agent,
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            data = {
                "grant_type": "client_credentials",
                "device_id": "crypto_discovery_scanner"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://www.reddit.com/api/v1/access_token",
                    headers=headers,
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 200:
                        token_data = await response.json()
                        self.access_token = token_data.get("access_token")
                        logger.info("Reddit access token obtained successfully")
                    else:
                        logger.error(f"Reddit token request failed: {response.status}")
                        
        except Exception as e:
            logger.error(f"Error getting Reddit access token: {e}")
    
    async def _fetch_posts(self, coin_id: str) -> List[RedditPost]:
        """Fetch posts from relevant subreddits"""
        posts = []
        
        # Get search terms for the coin
        search_terms = self._get_search_terms(coin_id)
        
        for subreddit in self.subreddits:
            try:
                # Search for posts in subreddit
                subreddit_posts = await self._search_subreddit(subreddit, search_terms)
                posts.extend(subreddit_posts)
                
                # Also get hot posts from the subreddit
                hot_posts = await self._get_hot_posts(subreddit)
                posts.extend(hot_posts)
                
            except Exception as e:
                logger.error(f"Error fetching posts from r/{subreddit}: {e}")
                continue
        
        # Remove duplicates and filter by relevance
        unique_posts = self._deduplicate_posts(posts)
        relevant_posts = self._filter_relevant_posts(unique_posts, coin_id)
        
        return relevant_posts[:50]  # Limit to 50 most relevant posts
    
    async def _search_subreddit(self, subreddit: str, search_terms: List[str]) -> List[RedditPost]:
        """Search for posts in a specific subreddit"""
        posts = []
        
        for term in search_terms[:3]:  # Limit to 3 terms to avoid rate limits
            try:
                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "User-Agent": self.user_agent
                }
                
                params = {
                    "q": term,
                    "sort": "new",
                    "limit": 10,
                    "t": "day"  # Last 24 hours
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"https://oauth.reddit.com/r/{subreddit}/search",
                        headers=headers,
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        
                        if response.status == 200:
                            data = await response.json()
                            posts_data = data.get("data", {}).get("children", [])
                            
                            for post_data in posts_data:
                                post = self._parse_post(post_data["data"])
                                if post:
                                    posts.append(post)
                        else:
                            logger.error(f"Reddit search failed for r/{subreddit}: {response.status}")
                            
            except Exception as e:
                logger.error(f"Error searching r/{subreddit} for '{term}': {e}")
                continue
        
        return posts
    
    async def _get_hot_posts(self, subreddit: str) -> List[RedditPost]:
        """Get hot posts from a subreddit"""
        posts = []
        
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "User-Agent": self.user_agent
            }
            
            params = {
                "limit": 25,
                "t": "day"  # Last 24 hours
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://oauth.reddit.com/r/{subreddit}/hot",
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        posts_data = data.get("data", {}).get("children", [])
                        
                        for post_data in posts_data:
                            post = self._parse_post(post_data["data"])
                            if post:
                                posts.append(post)
                    else:
                        logger.error(f"Reddit hot posts failed for r/{subreddit}: {response.status}")
                        
        except Exception as e:
            logger.error(f"Error getting hot posts from r/{subreddit}: {e}")
        
        return posts
    
    def _parse_post(self, post_data: Dict[str, Any]) -> Optional[RedditPost]:
        """Parse Reddit post data"""
        try:
            return RedditPost(
                title=post_data.get("title", ""),
                selftext=post_data.get("selftext", ""),
                score=post_data.get("score", 0),
                upvote_ratio=post_data.get("upvote_ratio", 0.5),
                num_comments=post_data.get("num_comments", 0),
                created_utc=post_data.get("created_utc", 0),
                subreddit=post_data.get("subreddit", ""),
                author=post_data.get("author", ""),
                url=post_data.get("url", ""),
                is_self=post_data.get("is_self", False)
            )
        except Exception as e:
            logger.error(f"Error parsing Reddit post: {e}")
            return None
    
    def _get_search_terms(self, coin_id: str) -> List[str]:
        """Get search terms for a coin"""
        term_map = {
            "bitcoin": ["bitcoin", "btc", "bitcoin price", "bitcoin news"],
            "ethereum": ["ethereum", "eth", "ethereum price", "ethereum news"],
            "binancecoin": ["binance", "bnb", "binance coin", "binance news"],
            "cardano": ["cardano", "ada", "cardano price", "cardano news"],
            "solana": ["solana", "sol", "solana price", "solana news"],
            "polkadot": ["polkadot", "dot", "polkadot price", "polkadot news"],
            "chainlink": ["chainlink", "link", "chainlink price", "chainlink news"],
            "dogecoin": ["dogecoin", "doge", "dogecoin price", "dogecoin news"],
            "shiba-inu": ["shiba inu", "shib", "shiba inu price", "shiba inu news"],
            "avalanche-2": ["avalanche", "avax", "avalanche price", "avalanche news"],
            "polygon": ["polygon", "matic", "polygon price", "polygon news"],
            "cosmos": ["cosmos", "atom", "cosmos price", "cosmos news"],
            "litecoin": ["litecoin", "ltc", "litecoin price", "litecoin news"],
            "monero": ["monero", "xmr", "monero price", "monero news"],
            "tron": ["tron", "trx", "tron price", "tron news"]
        }
        return term_map.get(coin_id.lower(), [coin_id])
    
    def _deduplicate_posts(self, posts: List[RedditPost]) -> List[RedditPost]:
        """Remove duplicate posts based on title similarity"""
        unique_posts = []
        seen_titles = set()
        
        for post in posts:
            # Simple deduplication based on title
            title_key = post.title.lower().strip()
            if title_key not in seen_titles and len(title_key) > 10:
                seen_titles.add(title_key)
                unique_posts.append(post)
        
        return unique_posts
    
    def _filter_relevant_posts(self, posts: List[RedditPost], coin_id: str) -> List[RedditPost]:
        """Filter posts for relevance to the specific coin"""
        relevant_posts = []
        search_terms = [term.lower() for term in self._get_search_terms(coin_id)]
        
        for post in posts:
            # Check if post mentions the coin
            title_lower = post.title.lower()
            text_lower = post.selftext.lower()
            
            # Score relevance
            relevance_score = 0
            for term in search_terms:
                if term in title_lower:
                    relevance_score += 3  # Title mentions are more important
                if term in text_lower:
                    relevance_score += 1
            
            # Only include posts with some relevance
            if relevance_score > 0:
                relevant_posts.append(post)
        
        # Sort by relevance and recency
        relevant_posts.sort(key=lambda p: (p.score, p.created_utc), reverse=True)
        return relevant_posts
    
    def _calculate_sentiment(self, posts: List[RedditPost]) -> float:
        """Calculate sentiment score from posts"""
        if not posts:
            return 0.0
        
        total_score = 0
        total_weight = 0
        
        for post in posts:
            # Use upvote ratio as sentiment indicator
            sentiment = (post.upvote_ratio - 0.5) * 2  # Convert to -1 to +1 range
            
            # Weight by post score (more popular posts matter more)
            weight = max(1, post.score)
            
            total_score += sentiment * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        return total_score / total_weight
    
    def _calculate_engagement(self, posts: List[RedditPost]) -> float:
        """Calculate engagement score from posts"""
        if not posts:
            return 0.0
        
        total_engagement = 0
        for post in posts:
            # Engagement = score + comments
            engagement = post.score + (post.num_comments * 2)  # Comments weighted more
            total_engagement += engagement
        
        # Normalize by number of posts
        avg_engagement = total_engagement / len(posts)
        
        # Scale to 0-1 range (rough approximation)
        return min(1.0, avg_engagement / 100)
    
    def _identify_hot_topics(self, posts: List[RedditPost]) -> List[str]:
        """Identify hot topics from posts"""
        if not posts:
            return []
        
        # Simple keyword extraction (in real implementation, use NLP)
        keywords = []
        for post in posts:
            # Extract words from title
            words = post.title.lower().split()
            keywords.extend([word for word in words if len(word) > 3])
        
        # Count keyword frequency
        keyword_counts = {}
        for keyword in keywords:
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
        
        # Return top keywords
        sorted_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
        return [keyword for keyword, count in sorted_keywords[:10] if count > 1]


# Import logger
import logging
logger = logging.getLogger(__name__)
