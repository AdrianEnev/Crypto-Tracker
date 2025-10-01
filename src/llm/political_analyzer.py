"""
Political Event Analyzer

Specialized LLM for analyzing political events and their impact on markets.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from .client import LLMClient, LLMConfig, LLMProvider


class PoliticalEventAnalyzer:
    """Specialized LLM for political event analysis"""
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
    
    async def analyze_political_events(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze political events and their market impact
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            Political analysis results
        """
        try:
            political_prompt = self._build_political_analysis_prompt(market_data)
            
            response = await self.llm_client.generate_response(political_prompt)
            
            # Extract content from response
            if self.llm_client.config.provider == LLMProvider.OPENAI:
                content = response["choices"][0]["message"]["content"]
            elif self.llm_client.config.provider == LLMProvider.ANTHROPIC:
                content = response["content"][0]["text"]
            else:
                raise ValueError(f"Unsupported provider: {self.llm_client.config.provider}")
            
            # Parse JSON response
            try:
                political_result = json.loads(content)
            except json.JSONDecodeError:
                political_result = {
                    "raw_response": content,
                    "parsing_error": "Failed to parse JSON response",
                    "political_impact": 0.0,
                    "stability_score": 0.5
                }
            
            self.logger.info(f"Political analysis completed: {political_result.get('political_impact', 'unknown')}")
            return political_result
            
        except Exception as e:
            self.logger.error(f"Error in political analysis: {e}")
            return {
                "error": str(e),
                "political_impact": 0.0,
                "stability_score": 0.5,
                "fallback": True
            }
    
    def _build_political_analysis_prompt(self, market_data: Dict[str, Any]) -> str:
        """Build political analysis prompt"""
        
        prompt = f"""
        Analyze the political environment and its potential impact on cryptocurrency markets:
        
        POLITICAL CONTEXT:
        - Government stability: {market_data.get('political', {}).get('government_stability', 'N/A')}
        - Political events: {market_data.get('political', {}).get('events', 'N/A')}
        - Geopolitical tensions: {market_data.get('political', {}).get('geopolitical', 'N/A')}
        - Policy announcements: {market_data.get('political', {}).get('policy_announcements', 'N/A')}
        
        ECONOMIC POLICY CONTEXT:
        - Fed policy: {market_data.get('economic', {}).get('fed_policy', 'N/A')}
        - Economic indicators: {market_data.get('economic', {}).get('indicators', 'N/A')}
        - Inflation: {market_data.get('economic', {}).get('inflation', 'N/A')}
        
        REGULATORY CONTEXT:
        - Regulatory news: {market_data.get('regulatory', {}).get('news', 'N/A')}
        - Legal developments: {market_data.get('regulatory', {}).get('legal', 'N/A')}
        
        ANALYSIS REQUIREMENTS:
        
        Provide analysis in JSON format with the following structure:
        
        {{
            "political_impact": 0.0-1.0,  // Overall political impact score
            "stability_score": 0.0-1.0,  // Government/political stability
            "policy_uncertainty": 0.0-1.0,  // Level of policy uncertainty
            "regulatory_risk": 0.0-1.0,  // Regulatory risk level
            "geopolitical_risk": 0.0-1.0,  // Geopolitical risk level
            "market_sentiment_impact": "positive|neutral|negative",  // Impact on market sentiment
            "crypto_policy_outlook": "favorable|neutral|hostile",  // Crypto policy outlook
            "key_risks": ["risk1", "risk2"],  // Key political risks
            "opportunities": ["opp1", "opp2"],  // Political opportunities
            "recommended_weight": 0.0-1.0,  // Recommended weight for political factors
            "confidence": 0.0-1.0  // Confidence in analysis
        }}
        """
        
        return prompt
