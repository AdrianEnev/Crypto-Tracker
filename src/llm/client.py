"""
LLM Client Implementation

Handles API communication with various LLM providers including OpenAI,
Anthropic, and other language model services.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
from enum import Enum

import aiohttp
from ..security.secrets_manager import SecretsManager


class LLMProvider(Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    COHERE = "cohere"


@dataclass
class LLMConfig:
    """Configuration for LLM integration"""
    provider: LLMProvider = LLMProvider.OPENAI
    model: str = "gpt-4o-mini"  # Cost-effective default
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 4000
    temperature: float = 0.1  # Low temperature for consistent analysis
    timeout: int = 30
    max_retries: int = 3
    rate_limit_per_minute: int = 60
    enable_caching: bool = True
    cache_ttl_seconds: int = 300  # 5 minutes


class LLMClient:
    """Client for interacting with various LLM providers"""
    
    def __init__(self, config: LLMConfig, secrets_manager: Optional[SecretsManager] = None):
        self.config = config
        self.secrets_manager = secrets_manager
        self.logger = logging.getLogger(__name__)
        
        # Rate limiting
        self.request_times: List[float] = []
        self.cache: Dict[str, Any] = {}
        
        # Initialize API key
        self._initialize_api_key()
    
    def _initialize_api_key(self):
        """Initialize API key from secrets manager or environment"""
        if self.config.api_key:
            return
        
        # Try to get from secrets manager
        if self.secrets_manager:
            key_name = f"{self.config.provider.value}_api_key"
            self.config.api_key = self.secrets_manager.get_secret(key_name)
        
        if not self.config.api_key:
            self.logger.warning(f"No API key found for {self.config.provider.value}")
    
    async def _check_rate_limit(self):
        """Check and enforce rate limiting"""
        current_time = asyncio.get_event_loop().time()
        
        # Remove requests older than 1 minute
        self.request_times = [
            t for t in self.request_times 
            if current_time - t < 60
        ]
        
        if len(self.request_times) >= self.config.rate_limit_per_minute:
            sleep_time = 60 - (current_time - self.request_times[0])
            self.logger.info(f"Rate limit reached, sleeping for {sleep_time:.2f} seconds")
            await asyncio.sleep(sleep_time)
    
    def _get_cache_key(self, prompt: str, model: str) -> str:
        """Generate cache key for prompt"""
        import hashlib
        content = f"{model}:{prompt}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def _get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached response if available and not expired"""
        if not self.config.enable_caching:
            return None
        
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            if asyncio.get_event_loop().time() - cached_data["timestamp"] < self.config.cache_ttl_seconds:
                self.logger.debug("Using cached LLM response")
                return cached_data["response"]
            else:
                # Remove expired cache entry
                del self.cache[cache_key]
        
        return None
    
    def _cache_response(self, cache_key: str, response: Dict[str, Any]):
        """Cache LLM response"""
        if self.config.enable_caching:
            self.cache[cache_key] = {
                "response": response,
                "timestamp": asyncio.get_event_loop().time()
            }
    
    async def _make_openai_request(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Make request to OpenAI API"""
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            **kwargs
        }
        
        base_url = self.config.base_url or "https://api.openai.com/v1"
        url = f"{base_url}/chat/completions"
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.timeout)) as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"OpenAI API error {response.status}: {error_text}")
    
    async def _make_anthropic_request(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Make request to Anthropic API"""
        headers = {
            "x-api-key": self.config.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "messages": [{"role": "user", "content": prompt}],
            **kwargs
        }
        
        base_url = self.config.base_url or "https://api.anthropic.com/v1"
        url = f"{base_url}/messages"
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.timeout)) as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"Anthropic API error {response.status}: {error_text}")
    
    async def generate_response(
        self, 
        prompt: str, 
        force_refresh: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate response from LLM
        
        Args:
            prompt: The input prompt
            force_refresh: Force refresh even if cached response exists
            **kwargs: Additional parameters for the LLM request
            
        Returns:
            Dict containing the LLM response and metadata
        """
        if not self.config.api_key:
            raise ValueError(f"No API key configured for {self.config.provider.value}")
        
        # Check cache first
        cache_key = self._get_cache_key(prompt, self.config.model)
        if not force_refresh:
            cached_response = await self._get_cached_response(cache_key)
            if cached_response:
                return cached_response
        
        # Check rate limiting
        await self._check_rate_limit()
        
        # Make request with retries
        last_exception = None
        for attempt in range(self.config.max_retries):
            try:
                self.logger.debug(f"Making LLM request (attempt {attempt + 1})")
                
                if self.config.provider == LLMProvider.OPENAI:
                    response = await self._make_openai_request(prompt, **kwargs)
                elif self.config.provider == LLMProvider.ANTHROPIC:
                    response = await self._make_anthropic_request(prompt, **kwargs)
                else:
                    raise ValueError(f"Unsupported provider: {self.config.provider}")
                
                # Record successful request
                self.request_times.append(asyncio.get_event_loop().time())
                
                # Cache response
                self._cache_response(cache_key, response)
                
                self.logger.debug("LLM request successful")
                return response
                
            except Exception as e:
                last_exception = e
                self.logger.warning(f"LLM request failed (attempt {attempt + 1}): {e}")
                
                if attempt < self.config.max_retries - 1:
                    # Exponential backoff
                    sleep_time = 2 ** attempt
                    await asyncio.sleep(sleep_time)
        
        # All retries failed
        raise Exception(f"LLM request failed after {self.config.max_retries} attempts: {last_exception}")
    
    async def analyze_market_data(
        self, 
        market_data: Dict[str, Any], 
        analysis_type: str = "comprehensive"
    ) -> Dict[str, Any]:
        """
        Analyze market data using LLM
        
        Args:
            market_data: Dictionary containing market data
            analysis_type: Type of analysis to perform
            
        Returns:
            Analysis results from LLM
        """
        # This will be implemented by specific analyzer classes
        raise NotImplementedError("Use specific analyzer classes for market analysis")
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        return {
            "requests_last_minute": len(self.request_times),
            "cache_size": len(self.cache),
            "provider": self.config.provider.value,
            "model": self.config.model
        }
