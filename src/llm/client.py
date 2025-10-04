"""
LLM Client Implementation

Handles API communication with various LLM providers using official client libraries.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from datetime import datetime, timezone

from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from rich.console import Console
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
    """Client for interacting with various LLM providers using official libraries"""
    
    def __init__(self, config: LLMConfig, secrets_manager: Optional[SecretsManager] = None):
        self.config = config
        self.secrets_manager = secrets_manager
        self.logger = logging.getLogger(__name__)
        
        # Rate limiting
        self.request_times: List[float] = []
        self.cache: Dict[str, Any] = {}
        
        # Rate limiting with backoff (matching CoinMarketCap pattern)
        self.backoff_until_ts = 0.0
        self.backoff_seconds = 0
        self.backoff_cap = 600  # 10 minutes cap
        self.console = Console()
        
        # Failure tracking
        self.failure_count = 0
        self.max_failures = 5
        self.disabled = False
        self.disabled_time = None
        
        # Initialize API clients
        self._initialize_clients()
    
    def is_disabled(self) -> bool:
        """Check if LLM is disabled due to failures."""
        if self.disabled and self.disabled_time:
            import time
            from datetime import datetime, timezone
            
            time_since_disabled = datetime.now(timezone.utc) - self.disabled_time
            hours_since_disabled = time_since_disabled.total_seconds() / 3600
            
            # Re-enable after 1 hour
            if hours_since_disabled >= 1.0:
                self.disabled = False
                self.failure_count = 0
                self.disabled_time = None
                self.logger.info("LLM client re-enabled after timeout")
                return False
        
        return self.disabled
    
    def _track_failure(self, error_message: str):
        """Track LLM failure and disable if threshold reached."""
        self.failure_count += 1
        
        # Calculate backoff time (120s base, exponential backoff)
        if self.failure_count == 1:
            self.backoff_seconds = 120  # 2 minutes
        else:
            self.backoff_seconds = min(
                self.backoff_seconds * 2,
                self.backoff_cap
            )
        
        self.backoff_until_ts = time.time() + self.backoff_seconds
        
        self.logger.warning(
            f"LLM failure #{self.failure_count}: {error_message}. "
            f"Backing off for {self.backoff_seconds}s"
        )
        
        if self.failure_count >= self.max_failures and not self.disabled:
            self.disabled = True
            self.disabled_time = datetime.now(timezone.utc)
            self.logger.error(f"LLM client disabled after {self.failure_count} failures")
    
    def _track_success(self):
        """Reset failure count on successful request."""
        if self.failure_count > 0:
            self.failure_count = 0
            self.backoff_until_ts = 0.0
            self.backoff_seconds = 0
            self.logger.info("LLM failure count reset due to successful request")
    
    def is_rate_limited(self) -> bool:
        """Check if LLM is currently rate-limited."""
        return self.backoff_until_ts > 0 and time.time() < self.backoff_until_ts
    
    def get_remaining_backoff(self) -> int:
        """Get remaining backoff time in seconds."""
        if self.backoff_until_ts <= 0:
            return 0
        return max(0, int(self.backoff_until_ts - time.time()))
    
    def update_rate_limited_manager(self, rate_limited_manager):
        """Update the rate-limited decision manager when LLM status changes."""
        try:
            if hasattr(rate_limited_manager, 'update_service_status'):
                if self.is_rate_limited():
                    remaining = self.get_remaining_backoff()
                    rate_limited_manager.update_service_status(
                        'llm', 
                        'rate_limited', 
                        f"LLM rate-limited for {remaining}s",
                        remaining
                    )
                elif self.disabled:
                    rate_limited_manager.update_service_status(
                        'llm', 
                        'disabled', 
                        f"LLM disabled after {self.failure_count} failures"
                    )
                else:
                    rate_limited_manager.update_service_status('llm', 'available')
        except Exception as e:
            self.logger.warning(f"Failed to update rate-limited manager: {e}")
    
    def _initialize_clients(self):
        """Initialize official API clients"""
        if self.config.provider == LLMProvider.OPENAI:
            self.openai_client = AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url
            )
        elif self.config.provider == LLMProvider.ANTHROPIC:
            self.anthropic_client = AsyncAnthropic(
                api_key=self.config.api_key,
                base_url=self.config.base_url
            )
        else:
            raise ValueError(f"Unsupported provider: {self.config.provider}")
    
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
        """Make request to OpenAI API using official client"""
        try:
            # Remove duplicate parameters from kwargs
            kwargs.pop('max_tokens', None)
            kwargs.pop('temperature', None)
            
            response = await self.openai_client.chat.completions.create(
                model=self.config.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                **kwargs
            )
            
            # Convert response to dict format for compatibility
            return {
                "choices": [{"message": {"content": response.choices[0].message.content}}],
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
            
        except Exception as e:
            error_msg = str(e)
            if "insufficient_quota" in error_msg or "billing" in error_msg or "credit" in error_msg:
                raise Exception(f"OpenAI API credits exhausted or billing issue: {e}")
            elif "authentication" in error_msg or "api_key" in error_msg:
                raise Exception(f"OpenAI API authentication failed: {e}")
            else:
                raise Exception(f"OpenAI API error: {e}")
    
    async def _make_anthropic_request(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Make request to Anthropic API using official client"""
        try:
            response = await self.anthropic_client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )
            
            # Convert response to dict format for compatibility
            return {
                "content": [{"text": response.content[0].text}],
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                }
            }
            
        except Exception as e:
            raise Exception(f"Anthropic API error: {e}")
    
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
        # Check if LLM is disabled due to failures
        if self.is_disabled():
            raise Exception(f"LLM client is disabled due to {self.failure_count} consecutive failures")
        
        if not self.config.api_key:
            raise ValueError(f"No API key configured for {self.config.provider.value}")
        
        # Check cache first
        cache_key = self._get_cache_key(prompt, self.config.model)
        if not force_refresh:
            cached_response = await self._get_cached_response(cache_key)
            if cached_response:
                return cached_response
        
        # Check if we're in backoff period
        if time.time() < self.backoff_until_ts:
            remaining = int(self.backoff_until_ts - time.time())
            self.console.print(
                f"[yellow]LLM rate-limited. Backing off for {remaining}s.[/yellow]"
            )
            raise Exception(f"LLM rate-limited. Backing off for {remaining}s.")
        
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
                
                # Track success
                self._track_success()
                
                self.logger.debug("LLM request successful")
                return response
                
            except Exception as e:
                last_exception = e
                self.logger.warning(f"LLM request failed (attempt {attempt + 1}): {e}")
                
                # Check for rate limiting errors (matching CoinMarketCap pattern)
                error_msg = str(e).lower()
                if any(phrase in error_msg for phrase in ['rate limit', 'too many requests', '429', 'throttled', 'connection error', 'timeout']):
                    # Exponential backoff starting at 120s
                    self.backoff_seconds = min(
                        max(120, self.backoff_seconds * 2 or 120), self.backoff_cap
                    )
                    self.backoff_until_ts = time.time() + self.backoff_seconds
                    self.console.print(
                        f"[yellow]LLM rate-limited. Backing off for {self.backoff_seconds}s.[/yellow]"
                    )
                    raise Exception(f"LLM rate-limited. Backing off for {self.backoff_seconds}s.")
                
                # Track failure
                self._track_failure(str(e))
                
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
