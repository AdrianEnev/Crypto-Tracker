"""
Crisis Detection LLM

Specialized LLM for detecting and analyzing crisis events that could impact markets.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from .client import LLMClient, LLMConfig, LLMProvider


class CrisisDetectionLLM:
    """Specialized LLM for crisis detection and analysis"""
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
        
        # Crisis detection thresholds
        self.crisis_thresholds = {
            "government_crisis": 0.8,
            "economic_crisis": 0.7,
            "regulatory_crisis": 0.8,
            "market_crisis": 0.9,
            "banking_crisis": 0.9,
            "monetary_policy_crisis": 0.8
        }
    
    async def detect_crisis_events(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect potential crisis events from market data
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            Crisis detection results
        """
        try:
            crisis_prompt = self._build_crisis_detection_prompt(market_data)
            
            response = await self.llm_client.generate_response(crisis_prompt)
            
            # Extract content from response
            if self.llm_client.config.provider == LLMProvider.OPENAI:
                content = response["choices"][0]["message"]["content"]
            elif self.llm_client.config.provider == LLMProvider.ANTHROPIC:
                content = response["content"][0]["text"]
            else:
                raise ValueError(f"Unsupported provider: {self.llm_client.config.provider}")
            
            # Parse JSON response
            try:
                crisis_result = json.loads(content)
            except json.JSONDecodeError:
                crisis_result = {
                    "raw_response": content,
                    "parsing_error": "Failed to parse JSON response",
                    "crisis_score": 0.0,
                    "crisis_level": "none"
                }
            
            self.logger.info(f"Crisis detection completed: {crisis_result.get('crisis_level', 'unknown')}")
            return crisis_result
            
        except Exception as e:
            self.logger.error(f"Error in crisis detection: {e}")
            return {
                "error": str(e),
                "crisis_score": 0.0,
                "crisis_level": "none",
                "fallback": True
            }
    
    def _build_crisis_detection_prompt(self, market_data: Dict[str, Any]) -> str:
        """Build crisis detection prompt"""
        
        prompt = f"""
        Analyze the following market data for potential crisis events that could significantly impact cryptocurrency markets:
        
        POLITICAL FACTORS:
        - Government stability: {market_data.get('political', {}).get('government_stability', 'N/A')}
        - Political events: {market_data.get('political', {}).get('events', 'N/A')}
        - Geopolitical tensions: {market_data.get('political', {}).get('geopolitical', 'N/A')}
        - Policy announcements: {market_data.get('political', {}).get('policy_announcements', 'N/A')}
        
        ECONOMIC FACTORS:
        - Fed policy: {market_data.get('economic', {}).get('fed_policy', 'N/A')}
        - Banking system: {market_data.get('economic', {}).get('banking_system', 'N/A')}
        - Economic indicators: {market_data.get('economic', {}).get('indicators', 'N/A')}
        - Inflation: {market_data.get('economic', {}).get('inflation', 'N/A')}
        - Interest rates: {market_data.get('economic', {}).get('interest_rates', 'N/A')}
        
        REGULATORY FACTORS:
        - Regulatory news: {market_data.get('regulatory', {}).get('news', 'N/A')}
        - Legal developments: {market_data.get('regulatory', {}).get('legal', 'N/A')}
        - Compliance updates: {market_data.get('regulatory', {}).get('compliance', 'N/A')}
        
        MARKET FACTORS:
        - Volatility: {market_data.get('volatility', {}).get('current', 'N/A')}
        - Liquidity: {market_data.get('market_structure', {}).get('liquidity', 'N/A')}
        - Volume: {market_data.get('technical', {}).get('volume', 'N/A')}
        
        SOCIAL FACTORS:
        - Social sentiment: {market_data.get('social', {}).get('twitter_sentiment', 'N/A')}
        - Community activity: {market_data.get('social', {}).get('community_activity', 'N/A')}
        
        CRISIS DETECTION CRITERIA:
        
        1. GOVERNMENT CRISIS INDICATORS (Score 0-1):
           - Government shutdown/instability
           - Political paralysis
           - Constitutional crisis
           - Leadership crisis
           - Policy uncertainty
        
        2. ECONOMIC CRISIS INDICATORS (Score 0-1):
           - Banking system stress
           - Liquidity crisis
           - Economic recession signals
           - Currency crisis
           - Inflation crisis
        
        3. REGULATORY CRISIS INDICATORS (Score 0-1):
           - Major regulatory crackdown
           - Exchange shutdowns
           - Legal uncertainty
           - Compliance crisis
           - Policy reversals
        
        4. MARKET CRISIS INDICATORS (Score 0-1):
           - Extreme volatility
           - Liquidity crisis
           - Market manipulation
           - Systemic risk
           - Flash crashes
        
        5. BANKING CRISIS INDICATORS (Score 0-1):
           - Bank failures
           - Credit crunch
           - Liquidity freeze
           - Systemic banking stress
        
        6. MONETARY POLICY CRISIS INDICATORS (Score 0-1):
           - Emergency rate changes
           - Quantitative easing/tightening
           - Currency intervention
           - Policy uncertainty
        
        ANALYSIS REQUIREMENTS:
        
        Provide analysis in JSON format with the following structure:
        
        {{
            "crisis_score": 0.0-1.0,  // Overall crisis score
            "crisis_type": "primary_crisis_type",  // Most significant crisis type
            "crisis_level": "none|low|medium|high|critical",  // Crisis severity
            "individual_scores": {{
                "government_crisis": 0.0-1.0,
                "economic_crisis": 0.0-1.0,
                "regulatory_crisis": 0.0-1.0,
                "market_crisis": 0.0-1.0,
                "banking_crisis": 0.0-1.0,
                "monetary_policy_crisis": 0.0-1.0
            }},
            "crisis_description": "Detailed description of the crisis situation",
            "recommended_response": "normal|alert|crisis|emergency",  // Recommended analysis mode
            "immediate_actions": ["action1", "action2"],  // Immediate actions to take
            "risk_factors": ["factor1", "factor2"],  // Key risk factors
            "market_impact": "low|medium|high|critical",  // Expected market impact
            "time_horizon": "immediate|short-term|medium-term|long-term",  // Crisis timeline
            "confidence": 0.0-1.0  // Confidence in crisis assessment
        }}
        
        IMPORTANT: 
        - Be conservative in crisis detection (false positives are better than false negatives)
        - Consider historical precedents for similar situations
        - Focus on events that could cause significant market disruption
        - Provide actionable recommendations
        """
        
        return prompt
