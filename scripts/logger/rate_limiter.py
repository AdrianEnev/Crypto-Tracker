"""
Rate Limiter for API calls using Token Bucket algorithm.

This module provides rate limiting functionality to prevent exceeding
exchange API rate limits and ensure graceful degradation.
"""

import time
import threading
from typing import Dict, Optional
from functools import wraps


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter for controlling API call frequency.
    
    The token bucket algorithm allows bursts of requests up to the bucket
    capacity while maintaining an average rate over time.
    """
    
    def __init__(self, max_calls: int, time_window: float):
        """
        Initialize the rate limiter.
        
        Args:
            max_calls: Maximum number of calls allowed in the time window
            time_window: Time window in seconds
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.tokens = float(max_calls)
        self.last_refill = time.time()
        self.lock = threading.Lock()
        
    def _refill_tokens(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Calculate tokens to add based on elapsed time
        tokens_to_add = (elapsed / self.time_window) * self.max_calls
        self.tokens = min(self.max_calls, self.tokens + tokens_to_add)
        self.last_refill = now
        
    def acquire(self, tokens: int = 1, blocking: bool = True) -> bool:
        """
        Acquire tokens from the bucket.
        
        Args:
            tokens: Number of tokens to acquire
            blocking: If True, wait until tokens are available
            
        Returns:
            True if tokens were acquired, False otherwise
        """
        with self.lock:
            self._refill_tokens()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            if not blocking:
                return False
            
            # Calculate wait time
            tokens_needed = tokens - self.tokens
            wait_time = (tokens_needed / self.max_calls) * self.time_window
            
        # Wait outside the lock to allow other threads
        time.sleep(wait_time)
        
        with self.lock:
            self._refill_tokens()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def get_available_tokens(self) -> float:
        """Get the current number of available tokens."""
        with self.lock:
            self._refill_tokens()
            return self.tokens


class ExchangeRateLimiter:
    """
    Manages rate limiters for multiple exchanges.
    
    Each exchange has its own rate limiter with appropriate limits.
    """
    
    # Default rate limits per exchange (calls per minute)
    DEFAULT_LIMITS = {
        'binance': 600,      # Conservative limit (actual: 1200/min)
        'coinbase': 10,      # Conservative limit (actual: 15/sec)
        'kraken': 15,        # Conservative limit (actual: varies)
        'bybit': 50,         # Conservative limit
        'coingecko': 10,     # Free tier limit
    }
    
    def __init__(self, custom_limits: Optional[Dict[str, int]] = None):
        """
        Initialize exchange rate limiters.
        
        Args:
            custom_limits: Optional custom rate limits per exchange
        """
        self.limiters: Dict[str, TokenBucketRateLimiter] = {}
        self.limits = {**self.DEFAULT_LIMITS}
        
        if custom_limits:
            self.limits.update(custom_limits)
        
        # Initialize limiters for each exchange
        for exchange, limit in self.limits.items():
            self.limiters[exchange] = TokenBucketRateLimiter(
                max_calls=limit,
                time_window=60.0  # 1 minute
            )
    
    def acquire(self, exchange: str, tokens: int = 1, blocking: bool = True) -> bool:
        """
        Acquire tokens for a specific exchange.
        
        Args:
            exchange: Exchange name (e.g., 'binance')
            tokens: Number of tokens to acquire
            blocking: If True, wait until tokens are available
            
        Returns:
            True if tokens were acquired, False otherwise
        """
        exchange_lower = exchange.lower()
        
        # Create limiter if it doesn't exist
        if exchange_lower not in self.limiters:
            default_limit = self.DEFAULT_LIMITS.get(exchange_lower, 60)
            self.limiters[exchange_lower] = TokenBucketRateLimiter(
                max_calls=default_limit,
                time_window=60.0
            )
        
        return self.limiters[exchange_lower].acquire(tokens, blocking)
    
    def get_status(self, exchange: str) -> Dict[str, float]:
        """
        Get rate limiter status for an exchange.
        
        Args:
            exchange: Exchange name
            
        Returns:
            Dictionary with available tokens and max tokens
        """
        exchange_lower = exchange.lower()
        
        if exchange_lower not in self.limiters:
            return {'available': 0, 'max': 0, 'percentage': 0}
        
        limiter = self.limiters[exchange_lower]
        available = limiter.get_available_tokens()
        max_tokens = limiter.max_calls
        
        return {
            'available': available,
            'max': max_tokens,
            'percentage': (available / max_tokens * 100) if max_tokens > 0 else 0
        }


def rate_limited(exchange: str, tokens: int = 1):
    """
    Decorator to rate limit function calls.
    
    Args:
        exchange: Exchange name for rate limiting
        tokens: Number of tokens to consume per call
        
    Example:
        @rate_limited('binance', tokens=1)
        def fetch_price(symbol):
            # This call will be rate limited
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get or create global rate limiter
            if not hasattr(wrapper, '_rate_limiter'):
                wrapper._rate_limiter = ExchangeRateLimiter()
            
            # Acquire tokens before executing
            wrapper._rate_limiter.acquire(exchange, tokens, blocking=True)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


# Global rate limiter instance
_global_rate_limiter: Optional[ExchangeRateLimiter] = None


def get_global_rate_limiter(custom_limits: Optional[Dict[str, int]] = None) -> ExchangeRateLimiter:
    """
    Get or create the global rate limiter instance.
    
    Args:
        custom_limits: Optional custom rate limits per exchange
        
    Returns:
        Global ExchangeRateLimiter instance
    """
    global _global_rate_limiter
    
    if _global_rate_limiter is None:
        _global_rate_limiter = ExchangeRateLimiter(custom_limits)
    
    return _global_rate_limiter
