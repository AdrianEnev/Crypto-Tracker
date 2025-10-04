"""
Batched LLM Market Analyzer

Processes multiple coins in a single LLM request to reduce API costs and improve efficiency.
Implements proper rate limiting and backoff mechanisms.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from .client import LLMClient
from .config_manager import LLMConfigManager


@dataclass
class BatchedAnalysisResult:
    """Result of batched LLM analysis for multiple coins."""
    coin_analyses: Dict[str, Dict]  # coin_id -> analysis result
    success: bool
    error: Optional[str] = None
    rate_limited: bool = False
    backoff_seconds: int = 0


class BatchedLLMAnalyzer:
    """
    Batched LLM analyzer that processes multiple coins in a single request.
    
    Features:
    - Batches multiple coin analyses into single API call
    - Implements exponential backoff with 120s base
    - Tracks rate limiting and disables when needed
    - Provides fallback when LLM is unavailable
    """
    
    def __init__(self, llm_client: LLMClient, config_manager: LLMConfigManager):
        self.logger = logging.getLogger(__name__)
        self.llm_client = llm_client
        self.config_manager = config_manager
        
        # Rate limiting state
        self.backoff_until_ts: float = 0.0
        self.backoff_seconds: int = 0
        self.max_backoff_seconds: int = 600  # 10 minutes max
        self.failure_count: int = 0
        self.max_failures: int = 5
        self.disabled: bool = False
        
        # Configuration
        self.batch_size_limit: int = 20  # Max coins per batch
        self.request_timeout: int = 30  # seconds
        
    def is_available(self) -> bool:
        """Check if LLM is available (not disabled or rate-limited)."""
        if self.disabled:
            return False
            
        if not self.llm_client.config.api_key:
            return False
            
        if self.backoff_until_ts > 0 and time.time() < self.backoff_until_ts:
            return False
            
        return True
    
    def get_remaining_backoff(self) -> int:
        """Get remaining backoff time in seconds."""
        if self.backoff_until_ts <= 0:
            return 0
        return max(0, int(self.backoff_until_ts - time.time()))
    
    async def analyze_coins_batch(
        self, 
        coins_data: Dict[str, Dict], 
        analysis_type: str = "comprehensive"
    ) -> BatchedAnalysisResult:
        """
        Analyze multiple coins in a single LLM request.
        
        Args:
            coins_data: Dict mapping coin_id -> market data
            analysis_type: Type of analysis to perform
            
        Returns:
            BatchedAnalysisResult with individual coin analyses
        """
        if not self.is_available():
            remaining = self.get_remaining_backoff()
            if remaining > 0:
                self.logger.debug(f"LLM unavailable due to backoff: {remaining}s remaining")
                return BatchedAnalysisResult(
                    coin_analyses={},
                    success=False,
                    rate_limited=True,
                    backoff_seconds=remaining
                )
            else:
                self.logger.debug("LLM unavailable (disabled or no API key)")
                return BatchedAnalysisResult(
                    coin_analyses={},
                    success=False,
                    error="LLM unavailable"
                )
        
        # Limit batch size
        coin_ids = list(coins_data.keys())[:self.batch_size_limit]
        if len(coin_ids) != len(coins_data):
            self.logger.warning(f"Batch size limited to {self.batch_size_limit} coins")
        
        try:
            # Build batched prompt
            prompt = self._build_batched_prompt(coin_ids, coins_data, analysis_type)
            
            # Make LLM request with timeout
            response = await asyncio.wait_for(
                self.llm_client.generate_response(prompt),
                timeout=self.request_timeout
            )
            
            # Parse response
            result = self._parse_batched_response(response, coin_ids)
            
            # Reset failure count on success
            self.failure_count = 0
            
            return BatchedAnalysisResult(
                coin_analyses=result,
                success=True
            )
            
        except asyncio.TimeoutError:
            self.logger.warning(f"LLM request timeout after {self.request_timeout}s")
            self._handle_failure("Timeout")
            return BatchedAnalysisResult(
                coin_analyses={},
                success=False,
                error="Request timeout"
            )
            
        except Exception as e:
            self.logger.error(f"LLM batch analysis failed: {e}")
            self._handle_failure(str(e))
            return BatchedAnalysisResult(
                coin_analyses={},
                success=False,
                error=str(e)
            )
    
    def _build_batched_prompt(self, coin_ids: List[str], coins_data: Dict[str, Dict], analysis_type: str) -> str:
        """Build a single prompt for analyzing multiple coins."""
        prompt_parts = [
            "Analyze the following cryptocurrencies for trading decisions. "
            "Provide JSON response with analysis for each coin.",
            "",
            "ANALYSIS REQUIREMENTS:",
            "- Assess technical indicators, market sentiment, and risk factors",
            "- Provide BUY/SELL/HOLD recommendation with confidence score",
            "- Consider market volatility, liquidity, and trend strength",
            "- Factor in any crisis indicators or market stress",
            "",
            "COINS TO ANALYZE:",
            ""
        ]
        
        for coin_id in coin_ids:
            coin_data = coins_data[coin_id]
            prompt_parts.extend([
                f"=== {coin_id.upper()} ===",
                f"Current Price: ${coin_data.get('current_price', 0):.2f}",
                f"RSI: {coin_data.get('rsi', 50):.1f}",
                f"Trend: {coin_data.get('trend', 'neutral')}",
                f"Volume: {coin_data.get('volume', 'normal')}",
                f"Volatility: {coin_data.get('volatility', 'normal')}",
                ""
            ])
        
        prompt_parts.extend([
            "RESPONSE FORMAT:",
            "Provide JSON array with analysis for each coin:",
            "[",
            "  {",
            '    "coin_id": "bitcoin",',
            '    "action": "BUY|SELL|HOLD",',
            '    "confidence": 0.85,',
            '    "sentiment": "bullish|bearish|neutral",',
            '    "reason": "Brief explanation of decision",',
            '    "risk_factors": ["factor1", "factor2"]',
            "  },",
            "  ...",
            "]",
            "",
            "Ensure all requested coins are included in the response."
        ])
        
        return "\n".join(prompt_parts)
    
    def _parse_batched_response(self, response: Dict, coin_ids: List[str]) -> Dict[str, Dict]:
        """Parse LLM response into individual coin analyses."""
        try:
            # Extract content based on provider
            if hasattr(self.llm_client.config, 'provider'):
                provider = self.llm_client.config.provider.value
                if provider == 'openai':
                    content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
                elif provider == 'anthropic':
                    content = response.get('content', [{}])[0].get('text', '')
                else:
                    content = str(response)
            else:
                content = str(response)
            
            # Try to parse as JSON
            try:
                analyses = json.loads(content)
                if not isinstance(analyses, list):
                    raise ValueError("Expected JSON array")
                
                # Convert to dict keyed by coin_id
                result = {}
                for analysis in analyses:
                    coin_id = analysis.get('coin_id', '').lower()
                    if coin_id in coin_ids:
                        result[coin_id] = {
                            'action': analysis.get('action', 'HOLD'),
                            'confidence': float(analysis.get('confidence', 0.5)),
                            'sentiment': analysis.get('sentiment', 'neutral'),
                            'reason': analysis.get('reason', 'No analysis provided'),
                            'risk_factors': analysis.get('risk_factors', [])
                        }
                
                # Ensure all requested coins are included
                for coin_id in coin_ids:
                    if coin_id not in result:
                        result[coin_id] = {
                            'action': 'HOLD',
                            'confidence': 0.0,
                            'sentiment': 'neutral',
                            'reason': 'No analysis provided by LLM',
                            'risk_factors': []
                        }
                
                return result
                
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse LLM response as JSON: {e}")
                # Fallback: create default responses for all coins
                return {
                    coin_id: {
                        'action': 'HOLD',
                        'confidence': 0.0,
                        'sentiment': 'neutral',
                        'reason': 'LLM response parsing failed',
                        'risk_factors': []
                    }
                    for coin_id in coin_ids
                }
                
        except Exception as e:
            self.logger.error(f"Error parsing batched response: {e}")
            return {}
    
    def _handle_failure(self, error_msg: str):
        """Handle LLM failure with exponential backoff."""
        self.failure_count += 1
        
        # Calculate backoff time (120s base, exponential backoff)
        if self.failure_count == 1:
            self.backoff_seconds = 120  # 2 minutes
        else:
            self.backoff_seconds = min(
                self.backoff_seconds * 2,
                self.max_backoff_seconds
            )
        
        self.backoff_until_ts = time.time() + self.backoff_seconds
        
        self.logger.warning(
            f"LLM failure #{self.failure_count}: {error_msg}. "
            f"Backing off for {self.backoff_seconds}s"
        )
        
        # Disable after max failures
        if self.failure_count >= self.max_failures:
            self.disabled = True
            self.logger.critical(
                f"LLM disabled after {self.failure_count} failures. "
                f"Last error: {error_msg}"
            )
    
    def reset_backoff(self):
        """Reset backoff state (called when LLM recovers)."""
        self.backoff_until_ts = 0.0
        self.backoff_seconds = 0
        self.failure_count = 0
        self.disabled = False
        self.logger.info("LLM backoff reset - service recovered")
    
    def get_status(self) -> Dict:
        """Get current status of the batched analyzer."""
        return {
            'available': self.is_available(),
            'disabled': self.disabled,
            'failure_count': self.failure_count,
            'backoff_remaining': self.get_remaining_backoff(),
            'has_api_key': bool(self.llm_client.config.api_key)
        }
