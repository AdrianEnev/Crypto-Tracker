"""
Social Media Data Sources

Provides integration with various social media and alternative data sources.
All sources are designed to be easily configurable and can be disabled independently.
Includes rate limiting, error handling, and fallback mechanisms.
"""

import asyncio
import aiohttp
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import logging
from pathlib import Path
import json

from .config import SocialMediaConfig


logger = logging.getLogger(__name__)


@dataclass
class SocialDataPoint:
    """Single data point from social media sources"""
    timestamp: datetime
    source: str
    coin_id: str
    data_type: str
    value: Union[float, int, str, Dict[str, Any]]
    confidence: float = 1.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class SocialDataBatch:
    """Batch of social data points"""
    coin_id: str
    data_points: List[SocialDataPoint]
    source: str
    timestamp: datetime
    quality_score: float = 1.0
    
    def get_latest(self, data_type: str) -> Optional[SocialDataPoint]:
        """Get the latest data point of a specific type"""
        filtered_points = [dp for dp in self.data_points if dp.data_type == data_type]
        if not filtered_points:
            return None
        return max(filtered_points, key=lambda x: x.timestamp)
    
    def get_average(self, data_type: str) -> Optional[float]:
        """Get average value for a specific data type"""
        filtered_points = [dp for dp in self.data_points 
                          if dp.data_type == data_type and isinstance(dp.value, (int, float))]
        if not filtered_points:
            return None
        return sum(dp.value for dp in filtered_points) / len(filtered_points)


class RateLimiter:
    """Simple rate limiter for API calls"""
    
    def __init__(self, max_calls: int, time_window: int):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
    
    async def acquire(self):
        """Acquire permission to make an API call"""
        now = time.time()
        
        # Remove old calls outside the time window
        self.calls = [call_time for call_time in self.calls 
                     if now - call_time < self.time_window]
        
        if len(self.calls) >= self.max_calls:
            # Calculate wait time
            oldest_call = min(self.calls)
            wait_time = self.time_window - (now - oldest_call)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
        
        self.calls.append(now)


class BaseSocialDataSource(ABC):
    """Base class for all social media data sources"""
    
    def __init__(self, config: SocialMediaConfig, source_name: str):
        self.config = config
        self.source_name = source_name
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limiter: Optional[RateLimiter] = None
        self.cache: Dict[str, Any] = {}
        self.cache_timestamps: Dict[str, float] = {}
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"User-Agent": "CryptoTracker/1.0"}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    @abstractmethod
    async def fetch_data(self, coin_id: str, data_types: List[str]) -> SocialDataBatch:
        """Fetch data for a specific coin"""
        pass
    
    def _get_cached_data(self, cache_key: str, ttl: int) -> Optional[Any]:
        """Get cached data if still valid"""
        if cache_key in self.cache and cache_key in self.cache_timestamps:
            if time.time() - self.cache_timestamps[cache_key] < ttl:
                return self.cache[cache_key]
            else:
                # Remove expired cache
                del self.cache[cache_key]
                del self.cache_timestamps[cache_key]
        return None
    
    def _cache_data(self, cache_key: str, data: Any):
        """Cache data with current timestamp"""
        self.cache[cache_key] = data
        self.cache_timestamps[cache_key] = time.time()
    
    async def _make_request(self, url: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make HTTP request with error handling"""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        if self.rate_limiter:
            await self.rate_limiter.acquire()
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:  # Rate limited
                    logger.warning(f"Rate limited by {self.source_name}, waiting...")
                    await asyncio.sleep(60)  # Wait 1 minute
                    return await self._make_request(url, params)
                else:
                    logger.error(f"HTTP {response.status} from {self.source_name}: {await response.text()}")
                    return {}
        except Exception as e:
            logger.error(f"Request failed for {self.source_name}: {e}")
            return {}


class LunarCrushSource(BaseSocialDataSource):
    """LunarCrush social media data source"""
    
    def __init__(self, config: SocialMediaConfig):
        super().__init__(config, "lunarcrush")
        self.lc_config = config.lunarcrush
        self.rate_limiter = RateLimiter(self.lc_config.rate_limit, 3600)  # Per hour
    
    async def fetch_data(self, coin_id: str, data_types: List[str]) -> SocialDataBatch:
        """Fetch LunarCrush data for a coin"""
        if not self.lc_config.enabled:
            return SocialDataBatch(coin_id, [], self.source_name, datetime.now())
        
        cache_key = f"lunarcrush_{coin_id}_{'_'.join(data_types)}"
        cached_data = self._get_cached_data(cache_key, self.lc_config.cache_ttl)
        if cached_data:
            return cached_data
        
        data_points = []
        
        try:
            # Map coin_id to LunarCrush symbol
            symbol = self._map_coin_to_symbol(coin_id)
            if not symbol:
                logger.warning(f"No LunarCrush symbol mapping for {coin_id}")
                return SocialDataBatch(coin_id, [], self.source_name, datetime.now())
            
            # Fetch social metrics
            url = f"{self.lc_config.base_url}/coins/{symbol}/metrics"
            params = {
                "data_points": 1,
                "interval": "hour"
            }
            
            if self.lc_config.api_key:
                params["api_key"] = self.lc_config.api_key
            
            response = await self._make_request(url, params)
            
            if response and "data" in response:
                metrics = response["data"]
                timestamp = datetime.now()
                
                for data_type in data_types:
                    if data_type in metrics:
                        value = metrics[data_type]
                        confidence = self._calculate_confidence(value, data_type)
                        
                        data_points.append(SocialDataPoint(
                            timestamp=timestamp,
                            source=self.source_name,
                            coin_id=coin_id,
                            data_type=data_type,
                            value=value,
                            confidence=confidence
                        ))
            
            batch = SocialDataBatch(
                coin_id=coin_id,
                data_points=data_points,
                source=self.source_name,
                timestamp=datetime.now(),
                quality_score=self._calculate_quality_score(data_points)
            )
            
            self._cache_data(cache_key, batch)
            return batch
            
        except Exception as e:
            logger.error(f"LunarCrush fetch failed for {coin_id}: {e}")
            return SocialDataBatch(coin_id, [], self.source_name, datetime.now())
    
    def _map_coin_to_symbol(self, coin_id: str) -> Optional[str]:
        """Map internal coin_id to LunarCrush symbol"""
        # Common mappings - this could be expanded or made configurable
        symbol_map = {
            "bitcoin": "BTC",
            "ethereum": "ETH", 
            "binancecoin": "BNB",
            "cardano": "ADA",
            "solana": "SOL",
            "polkadot": "DOT",
            "chainlink": "LINK",
            "litecoin": "LTC",
            "bitcoin-cash": "BCH",
            "dogecoin": "DOGE"
        }
        return symbol_map.get(coin_id.lower())
    
    def _calculate_confidence(self, value: Any, data_type: str) -> float:
        """Calculate confidence score for a data point"""
        if value is None:
            return 0.0
        
        # Basic confidence based on data type and value
        if data_type == "social_volume":
            return min(1.0, max(0.5, float(value) / 1000))  # More volume = higher confidence
        elif data_type == "sentiment_score":
            return 0.8  # Sentiment scores are generally reliable
        elif data_type == "influencer_activity":
            return min(1.0, max(0.6, float(value) / 100))  # More activity = higher confidence
        else:
            return 0.7  # Default confidence
    
    def _calculate_quality_score(self, data_points: List[SocialDataPoint]) -> float:
        """Calculate overall quality score for the batch"""
        if not data_points:
            return 0.0
        
        avg_confidence = sum(dp.confidence for dp in data_points) / len(data_points)
        completeness = len(data_points) / len(self.lc_config.features)  # How many features we got
        
        return (avg_confidence + completeness) / 2


class SantimentSource(BaseSocialDataSource):
    """Santiment social and on-chain data source"""
    
    def __init__(self, config: SocialMediaConfig):
        super().__init__(config, "santiment")
        self.santiment_config = config.santiment
        self.rate_limiter = RateLimiter(self.santiment_config.rate_limit, 3600)
    
    async def fetch_data(self, coin_id: str, data_types: List[str]) -> SocialDataBatch:
        """Fetch Santiment data for a coin"""
        if not self.santiment_config.enabled:
            return SocialDataBatch(coin_id, [], self.source_name, datetime.now())
        
        cache_key = f"santiment_{coin_id}_{'_'.join(data_types)}"
        cached_data = self._get_cached_data(cache_key, self.santiment_config.cache_ttl)
        if cached_data:
            return cached_data
        
        data_points = []
        
        try:
            # Map coin_id to Santiment slug
            slug = self._map_coin_to_slug(coin_id)
            if not slug:
                logger.warning(f"No Santiment slug mapping for {coin_id}")
                return SocialDataBatch(coin_id, [], self.source_name, datetime.now())
            
            # Fetch metrics for each data type
            for data_type in data_types:
                if data_type not in self.santiment_config.features:
                    continue
                
                url = f"{self.santiment_config.base_url}/metrics/{data_type}"
                params = {
                    "slug": slug,
                    "from": (datetime.now() - timedelta(hours=24)).isoformat(),
                    "to": datetime.now().isoformat(),
                    "interval": "1h"
                }
                
                if self.santiment_config.api_key:
                    params["api_key"] = self.santiment_config.api_key
                
                response = await self._make_request(url, params)
                
                if response and "data" in response:
                    values = response["data"]
                    if values:
                        latest_value = values[-1]["value"] if isinstance(values[-1], dict) else values[-1]
                        timestamp = datetime.now()
                        
                        confidence = self._calculate_confidence(latest_value, data_type)
                        
                        data_points.append(SocialDataPoint(
                            timestamp=timestamp,
                            source=self.source_name,
                            coin_id=coin_id,
                            data_type=data_type,
                            value=latest_value,
                            confidence=confidence
                        ))
            
            batch = SocialDataBatch(
                coin_id=coin_id,
                data_points=data_points,
                source=self.source_name,
                timestamp=datetime.now(),
                quality_score=self._calculate_quality_score(data_points)
            )
            
            self._cache_data(cache_key, batch)
            return batch
            
        except Exception as e:
            logger.error(f"Santiment fetch failed for {coin_id}: {e}")
            return SocialDataBatch(coin_id, [], self.source_name, datetime.now())
    
    def _map_coin_to_slug(self, coin_id: str) -> Optional[str]:
        """Map internal coin_id to Santiment slug"""
        slug_map = {
            "bitcoin": "bitcoin",
            "ethereum": "ethereum",
            "binancecoin": "binancecoin",
            "cardano": "cardano",
            "solana": "solana",
            "polkadot": "polkadot",
            "chainlink": "chainlink",
            "litecoin": "litecoin",
            "bitcoin-cash": "bitcoin-cash",
            "dogecoin": "dogecoin"
        }
        return slug_map.get(coin_id.lower())
    
    def _calculate_confidence(self, value: Any, data_type: str) -> float:
        """Calculate confidence score for Santiment data"""
        if value is None:
            return 0.0
        
        if data_type == "social_volume":
            return min(1.0, max(0.6, float(value) / 500))
        elif data_type == "sentiment":
            return 0.8
        elif data_type == "on_chain_social":
            return 0.9  # On-chain data is very reliable
        else:
            return 0.7
    
    def _calculate_quality_score(self, data_points: List[SocialDataPoint]) -> float:
        """Calculate quality score for Santiment batch"""
        if not data_points:
            return 0.0
        
        avg_confidence = sum(dp.confidence for dp in data_points) / len(data_points)
        completeness = len(data_points) / len(self.santiment_config.features)
        
        return (avg_confidence + completeness) / 2


class GoogleTrendsSource(BaseSocialDataSource):
    """Google Trends search volume data source"""
    
    def __init__(self, config: SocialMediaConfig):
        super().__init__(config, "google_trends")
        self.trends_config = config.google_trends
        # Google Trends doesn't have traditional rate limits, but we'll be conservative
        self.rate_limiter = RateLimiter(100, 3600)  # 100 requests per hour
    
    async def fetch_data(self, coin_id: str, data_types: List[str]) -> SocialDataBatch:
        """Fetch Google Trends data for a coin"""
        if not self.trends_config.enabled:
            return SocialDataBatch(coin_id, [], self.source_name, datetime.now())
        
        cache_key = f"google_trends_{coin_id}_{'_'.join(data_types)}"
        cached_data = self._get_cached_data(cache_key, self.trends_config.cache_ttl)
        if cached_data:
            return cached_data
        
        data_points = []
        
        try:
            # Map coin_id to search terms
            search_terms = self._get_search_terms(coin_id)
            if not search_terms:
                logger.warning(f"No search terms for {coin_id}")
                return SocialDataBatch(coin_id, [], self.source_name, datetime.now())
            
            # For now, we'll simulate Google Trends data
            # In a real implementation, you'd use pytrends or similar library
            timestamp = datetime.now()
            
            for data_type in data_types:
                if data_type == "search_volume":
                    # Simulate search volume data
                    value = self._simulate_search_volume(coin_id)
                    confidence = 0.8
                    
                    data_points.append(SocialDataPoint(
                        timestamp=timestamp,
                        source=self.source_name,
                        coin_id=coin_id,
                        data_type=data_type,
                        value=value,
                        confidence=confidence
                    ))
            
            batch = SocialDataBatch(
                coin_id=coin_id,
                data_points=data_points,
                source=self.source_name,
                timestamp=datetime.now(),
                quality_score=0.8  # Google Trends is generally reliable
            )
            
            self._cache_data(cache_key, batch)
            return batch
            
        except Exception as e:
            logger.error(f"Google Trends fetch failed for {coin_id}: {e}")
            return SocialDataBatch(coin_id, [], self.source_name, datetime.now())
    
    def _get_search_terms(self, coin_id: str) -> List[str]:
        """Get search terms for a coin"""
        term_map = {
            "bitcoin": ["bitcoin", "btc", "bitcoin price"],
            "ethereum": ["ethereum", "eth", "ethereum price"],
            "binancecoin": ["binance", "bnb", "binance coin"],
            "cardano": ["cardano", "ada", "cardano price"],
            "solana": ["solana", "sol", "solana price"],
            "dogecoin": ["dogecoin", "doge", "dogecoin price"]
        }
        return term_map.get(coin_id.lower(), [coin_id])
    
    def _simulate_search_volume(self, coin_id: str) -> float:
        """Simulate search volume data (replace with real implementation)"""
        # This is a placeholder - in real implementation, use pytrends
        import random
        base_volume = {
            "bitcoin": 100,
            "ethereum": 80,
            "dogecoin": 60,
            "solana": 40,
            "cardano": 30
        }.get(coin_id.lower(), 20)
        
        return base_volume + random.uniform(-10, 10)


class NewsAPISource(BaseSocialDataSource):
    """News API data source for headline sentiment analysis"""
    
    def __init__(self, config: SocialMediaConfig):
        super().__init__(config, "news_api")
        self.api_key = config.news_api.api_key
        self.base_url = "https://newsapi.org/v2/everything"
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter(
            config.news_api.rate_limit, 
            3600  # 1 hour window
        )
    
    async def fetch_data(self, coin_id: str, data_types: List[str]) -> SocialDataBatch:
        """Fetch news data for a coin"""
        try:
            await self.rate_limiter.acquire()
            
            # Check cache first
            cache_key = f"news_api_{coin_id}_{datetime.now().strftime('%Y%m%d%H')}"
            cached_data = self._get_cached_data(cache_key)
            if cached_data:
                return cached_data
            
            # Prepare search terms
            search_terms = self._get_search_terms(coin_id)
            
            # Fetch news articles
            articles = await self._fetch_articles(search_terms)
            
            # Process articles for sentiment and metrics
            data_points = []
            
            for article in articles:
                # Calculate sentiment (simplified - in real implementation use NLP)
                sentiment_score = self._calculate_sentiment(article)
                
                data_points.append(SocialDataPoint(
                    timestamp=datetime.now(),
                    source=self.source_name,
                    coin_id=coin_id,
                    data_type="headline_sentiment",
                    value=sentiment_score,
                    confidence=0.8,
                    metadata={
                        "title": article.get("title", ""),
                        "source": article.get("source", {}).get("name", ""),
                        "url": article.get("url", ""),
                        "published_at": article.get("publishedAt", "")
                    }
                ))
            
            # Calculate mention frequency
            mention_frequency = len(articles)
            data_points.append(SocialDataPoint(
                timestamp=datetime.now(),
                source=self.source_name,
                coin_id=coin_id,
                data_type="mention_frequency",
                value=mention_frequency,
                confidence=1.0
            ))
            
            # Calculate source credibility (simplified)
            credibility_score = self._calculate_source_credibility(articles)
            data_points.append(SocialDataPoint(
                timestamp=datetime.now(),
                source=self.source_name,
                coin_id=coin_id,
                data_type="source_credibility",
                value=credibility_score,
                confidence=0.9
            ))
            
            batch = SocialDataBatch(
                coin_id=coin_id,
                data_points=data_points,
                source=self.source_name,
                timestamp=datetime.now(),
                quality_score=0.8
            )
            
            # Cache the data
            self._cache_data(cache_key, batch)
            return batch
            
        except Exception as e:
            logger.error(f"News API fetch failed for {coin_id}: {e}")
            return SocialDataBatch(coin_id, [], self.source_name, datetime.now())
    
    async def _fetch_articles(self, search_terms: List[str]) -> List[Dict[str, Any]]:
        """Fetch articles from News API"""
        try:
            headers = {
                "X-API-Key": self.api_key,
                "User-Agent": "CryptoDiscoveryScanner/1.0"
            }
            
            # Combine search terms
            query = " OR ".join(search_terms)
            
            params = {
                "q": f"{query} cryptocurrency",
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": 20,
                "from": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.base_url,
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self.config.news_api.timeout)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        return data.get("articles", [])
                    else:
                        logger.error(f"News API error: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error fetching articles: {e}")
            return []
    
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
    
    def _calculate_sentiment(self, article: Dict[str, Any]) -> float:
        """Calculate sentiment score for an article (simplified)"""
        title = article.get("title", "").lower()
        description = article.get("description", "").lower()
        text = f"{title} {description}"
        
        # Simple keyword-based sentiment (in real implementation, use NLP)
        positive_words = [
            "bullish", "surge", "rally", "gains", "up", "rise", "increase", 
            "breakthrough", "adoption", "partnership", "launch", "success",
            "positive", "optimistic", "growth", "innovation", "milestone"
        ]
        
        negative_words = [
            "bearish", "crash", "drop", "fall", "down", "decline", "decrease",
            "concern", "risk", "warning", "negative", "pessimistic", "loss",
            "hack", "scam", "fraud", "regulation", "ban", "crackdown"
        ]
        
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        
        if positive_count + negative_count == 0:
            return 0.0
        
        # Normalize to -1 to +1 range
        sentiment = (positive_count - negative_count) / (positive_count + negative_count)
        return max(-1.0, min(1.0, sentiment))
    
    def _calculate_source_credibility(self, articles: List[Dict[str, Any]]) -> float:
        """Calculate source credibility score"""
        if not articles:
            return 0.0
        
        # Credible sources (simplified list)
        credible_sources = [
            "coindesk", "cointelegraph", "decrypt", "the block", "crypto news",
            "reuters", "bloomberg", "forbes", "cnbc", "wall street journal",
            "financial times", "marketwatch", "yahoo finance", "techcrunch"
        ]
        
        credible_count = 0
        for article in articles:
            source_name = article.get("source", {}).get("name", "").lower()
            if any(credible in source_name for credible in credible_sources):
                credible_count += 1
        
        return credible_count / len(articles)


class SocialDataManager:
    """Main manager for all social media data sources"""
    
    def __init__(self, config: SocialMediaConfig):
        self.config = config
        self.sources: Dict[str, BaseSocialDataSource] = {}
        self._initialize_sources()
    
    def _initialize_sources(self):
        """Initialize enabled data sources"""
        if self.config.lunarcrush.enabled:
            self.sources["lunarcrush"] = LunarCrushSource(self.config)
        
        if self.config.santiment.enabled:
            self.sources["santiment"] = SantimentSource(self.config)
        
        if self.config.google_trends.enabled:
            self.sources["google_trends"] = GoogleTrendsSource(self.config)
        
        if self.config.news_api.enabled:
            self.sources["news_api"] = NewsAPISource(self.config)
        
        if self.config.twitter.enabled:
            from .twitter_source import TwitterSource
            self.sources["twitter"] = TwitterSource(self.config)
        
        if self.config.reddit.enabled:
            from .reddit_source import RedditSource
            self.sources["reddit"] = RedditSource(self.config)
        
        if self.config.exchange_api.enabled:
            from .exchange_source import ExchangeAPISource
            self.sources["exchange_api"] = ExchangeAPISource(self.config)
        
        # Add other sources as they're implemented
        logger.info(f"Initialized {len(self.sources)} social data sources: {list(self.sources.keys())}")
    
    async def fetch_all_data(self, coin_id: str, data_types: List[str]) -> Dict[str, SocialDataBatch]:
        """Fetch data from all enabled sources"""
        if not self.config.enabled:
            return {}
        
        results = {}
        
        # Fetch data from all sources concurrently
        tasks = []
        for source_name, source in self.sources.items():
            tasks.append(self._fetch_source_data(source_name, source, coin_id, data_types))
        
        if tasks:
            source_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(source_results):
                source_name = list(self.sources.keys())[i]
                if isinstance(result, Exception):
                    logger.error(f"Error fetching from {source_name}: {result}")
                    results[source_name] = SocialDataBatch(coin_id, [], source_name, datetime.now())
                else:
                    results[source_name] = result
        
        return results
    
    async def _fetch_source_data(self, source_name: str, source: BaseSocialDataSource, 
                                coin_id: str, data_types: List[str]) -> SocialDataBatch:
        """Fetch data from a single source"""
        try:
            async with source:
                return await source.fetch_data(coin_id, data_types)
        except Exception as e:
            logger.error(f"Failed to fetch from {source_name}: {e}")
            return SocialDataBatch(coin_id, [], source_name, datetime.now())
    
    def get_enabled_sources(self) -> List[str]:
        """Get list of enabled source names"""
        return list(self.sources.keys())
    
    def is_source_enabled(self, source_name: str) -> bool:
        """Check if a specific source is enabled"""
        return source_name in self.sources
