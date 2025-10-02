"""
Tier 1: Crisis Detection using LLM

Highest priority intelligence tier that detects macro-level crises
that should halt or reduce trading activity.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from cachetools import TTLCache

from ..base import BaseIntelligence
from ..models import CrisisStatus, CrisisLevel


class CrisisDetector(BaseIntelligence):
    """
    Detects market crises using LLM analysis
    
    Crisis types:
    - Political (government shutdown, instability)
    - Economic (banking crisis, recession)
    - Regulatory (exchange shutdowns, bans)
    - Market (extreme volatility, liquidity crisis)
    """
    
    def __init__(self, llm_client, config: dict):
        super().__init__(config, logger_name=__name__)
        self.llm_client = llm_client
        
        # Configuration
        self.check_interval_seconds = config.get('check_interval_seconds', 300)  # 5 min
        self.llm_timeout = config.get('llm_timeout_seconds', 15)
        self.cache_ttl = config.get('cache_ttl_seconds', 300)
        self.max_llm_failures = config.get('llm_max_failures', 5)
        
        # State
        self.cache = TTLCache(maxsize=10, ttl=self.cache_ttl)
        self.last_check_time: Optional[datetime] = None
        self.llm_failure_count = 0
        self.llm_disabled = False
    
    async def analyze(self) -> CrisisStatus:
        """
        Main analysis method - detects crises
        
        Returns:
            CrisisStatus with level and details
        """
        return await self.detect_crisis()
    
    async def detect_crisis(self) -> CrisisStatus:
        """
        Detect if there's a market crisis
        
        Returns:
            CrisisStatus object
        """
        # Check if we should use cache
        if self._should_use_cache():
            cached = self.cache.get('crisis_status')
            if cached:
                return cached
        
        # Check if LLM is disabled
        if self.llm_disabled or not self.is_enabled():
            return self._get_fallback_status()
        
        # Check if API key is configured
        if not self.llm_client.config.api_key:
            self.logger.debug("LLM API key not configured, skipping crisis detection")
            return self._get_fallback_status()
        
        # Check if LLM is in backoff period
        if hasattr(self.llm_client, 'backoff_until_ts') and self.llm_client.backoff_until_ts > 0:
            import time
            if time.time() < self.llm_client.backoff_until_ts:
                remaining = int(self.llm_client.backoff_until_ts - time.time())
                self.logger.debug(f"LLM is rate-limited, skipping crisis detection (backoff: {remaining}s)")
                return self._get_fallback_status()
        
        try:
            # Gather macro data
            macro_data = await self._gather_macro_data()
            
            # LLM analysis with timeout
            analysis = await asyncio.wait_for(
                self._llm_analyze_crisis(macro_data),
                timeout=self.llm_timeout
            )
            
            # Parse response
            crisis_status = self._parse_llm_response(analysis)
            
            # Cache result
            self.cache['crisis_status'] = crisis_status
            self.last_check_time = datetime.now(timezone.utc)
            
            # Reset failure count on success
            if self.llm_failure_count > 0:
                self.logger.info(f"LLM recovered after {self.llm_failure_count} failures")
                self.llm_failure_count = 0
            
            self.record_success()
            return crisis_status
            
        except asyncio.TimeoutError:
            self.logger.warning(f"LLM timeout after {self.llm_timeout}s")
            self._handle_llm_failure("Timeout")
            return self._get_fallback_status()
            
        except Exception as e:
            self.logger.error(f"Crisis detection failed: {e}")
            self._handle_llm_failure(str(e))
            self.record_failure(e)
            return CrisisStatus.unknown()
    
    async def _gather_macro_data(self) -> dict:
        """
        Gather macro-economic and political data
        
        In production, this would fetch from:
        - News APIs
        - Economic data feeds
        - Government RSS feeds
        - Exchange status APIs
        
        For now, returns basic structure
        """
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'political': {
                'government_stability': 'stable',  # Would be real data
                'recent_events': [],
                'geopolitical_tensions': 'low'
            },
            'economic': {
                'fed_policy': 'neutral',  # Would be real data
                'banking_system': 'stable',
                'recession_indicators': 'low'
            },
            'regulatory': {
                'recent_actions': [],  # Would be real data
                'exchange_status': 'operational'
            },
            'market': {
                'volatility_level': 'normal',  # Would be real data
                'liquidity_status': 'adequate'
            }
        }
    
    async def _llm_analyze_crisis(self, macro_data: dict) -> dict:
        """
        Use LLM to analyze macro data for crises
        
        Args:
            macro_data: Dictionary of macro indicators
            
        Returns:
            LLM analysis result
        """
        prompt = self._build_crisis_prompt(macro_data)
        
        try:
            # Use existing LLM client
            response = await self.llm_client.generate_response(prompt)
            
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
            import json
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # If not JSON, create structured response
                return {
                    'crisis_level': 'NONE',
                    'confidence': 0.5,
                    'reason': content[:200],
                    'raw_response': content
                }
                
        except Exception as e:
            self.logger.error(f"LLM analysis failed: {e}")
            raise
    
    def _build_crisis_prompt(self, macro_data: dict) -> str:
        """Build prompt for LLM crisis analysis"""
        return f"""
Analyze the following market and macro-economic data for potential crises that would affect cryptocurrency trading:

POLITICAL FACTORS:
- Government stability: {macro_data['political']['government_stability']}
- Geopolitical tensions: {macro_data['political']['geopolitical_tensions']}

ECONOMIC FACTORS:
- Fed policy: {macro_data['economic']['fed_policy']}
- Banking system: {macro_data['economic']['banking_system']}
- Recession indicators: {macro_data['economic']['recession_indicators']}

REGULATORY FACTORS:
- Exchange status: {macro_data['regulatory']['exchange_status']}

MARKET FACTORS:
- Volatility: {macro_data['market']['volatility_level']}
- Liquidity: {macro_data['market']['liquidity_status']}

Assess the crisis level on a scale:
- NONE: No crisis, normal trading conditions
- LOW: Minor concerns, slight caution advised
- MEDIUM: Moderate concerns, reduce position sizes
- HIGH: Serious concerns, minimal trading only
- CRITICAL: Severe crisis, halt all trading

Respond in JSON format:
{{
    "crisis_level": "NONE|LOW|MEDIUM|HIGH|CRITICAL",
    "confidence": 0.0-1.0,
    "reason": "Brief explanation",
    "risk_adjustment": 0.0-1.0
}}
"""
    
    def _parse_llm_response(self, analysis: dict) -> CrisisStatus:
        """Parse LLM response into CrisisStatus"""
        try:
            level_str = analysis.get('crisis_level', 'NONE').upper()
            
            # Map string to enum
            level_map = {
                'NONE': CrisisLevel.NONE,
                'LOW': CrisisLevel.LOW,
                'MEDIUM': CrisisLevel.MEDIUM,
                'HIGH': CrisisLevel.HIGH,
                'CRITICAL': CrisisLevel.CRITICAL
            }
            
            level = level_map.get(level_str, CrisisLevel.NONE)
            
            # Calculate risk adjustment based on level
            risk_adjustments = {
                CrisisLevel.NONE: 1.0,
                CrisisLevel.LOW: 0.9,
                CrisisLevel.MEDIUM: 0.7,
                CrisisLevel.HIGH: 0.3,
                CrisisLevel.CRITICAL: 0.0
            }
            
            return CrisisStatus(
                level=level,
                reason=analysis.get('reason', 'No specific reason provided'),
                confidence=float(analysis.get('confidence', 0.5)),
                risk_adjustment=risk_adjustments[level],
                metadata=analysis
            )
            
        except Exception as e:
            self.logger.error(f"Failed to parse LLM response: {e}")
            return CrisisStatus.none()
    
    def _should_use_cache(self) -> bool:
        """Check if we should use cached result"""
        if not self.last_check_time:
            return False
        
        time_since_check = (datetime.now(timezone.utc) - self.last_check_time).total_seconds()
        return time_since_check < self.check_interval_seconds
    
    def _handle_llm_failure(self, error_msg: str):
        """Handle LLM failure"""
        self.llm_failure_count += 1
        
        if self.llm_failure_count >= self.max_llm_failures:
            self.llm_disabled = True
            self.logger.critical(
                f"LLM disabled after {self.llm_failure_count} failures. "
                f"Last error: {error_msg}"
            )
    
    def _get_fallback_status(self) -> CrisisStatus:
        """Get fallback status when LLM is unavailable"""
        # Check cache first
        cached = self.cache.get('crisis_status')
        if cached:
            return cached
        
        # Return safe default (no crisis)
        return CrisisStatus.none()


class MacroIntelligence(CrisisDetector):
    """Alias for CrisisDetector for consistency with tier naming"""
    pass
