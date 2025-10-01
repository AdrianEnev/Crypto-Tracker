"""
Comprehensive Market Analysis LLM

Provides comprehensive market analysis using LLM integration,
balancing technical, social, economic, and political factors.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from .client import LLMClient, LLMConfig, LLMProvider


class ComprehensiveMarketAnalyzer:
    """Comprehensive market analysis using LLM"""
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
        
        # Analysis weights for different market conditions
        self.analysis_weights = {
            "normal": {
                "technical": 0.25,
                "social": 0.15,
                "news": 0.10,
                "macro_economic": 0.15,
                "political": 0.10,
                "regulatory": 0.10,
                "market_structure": 0.10,
                "volatility": 0.05
            },
            "alert": {
                "technical": 0.20,
                "social": 0.15,
                "news": 0.15,
                "macro_economic": 0.20,
                "political": 0.15,
                "regulatory": 0.10,
                "market_structure": 0.05,
                "volatility": 0.00
            },
            "crisis": {
                "technical": 0.15,
                "social": 0.10,
                "news": 0.10,
                "macro_economic": 0.25,
                "political": 0.30,
                "regulatory": 0.05,
                "market_structure": 0.05,
                "volatility": 0.00
            },
            "emergency": {
                "technical": 0.10,
                "social": 0.10,
                "news": 0.05,
                "macro_economic": 0.30,
                "political": 0.40,
                "regulatory": 0.05,
                "market_structure": 0.00,
                "volatility": 0.00
            }
        }
    
    def _build_comprehensive_prompt(self, coin: str, market_data: Dict[str, Any], weights: Dict[str, float]) -> str:
        """Build comprehensive analysis prompt"""
        
        prompt = f"""
        Provide comprehensive market analysis for {coin} considering all relevant factors with the following weight distribution:
        
        TECHNICAL ANALYSIS (Weight: {weights['technical']:.1%}):
        - Price action and trends: {market_data.get('technical', {}).get('trend', 'N/A')}
        - Key support/resistance levels: {market_data.get('technical', {}).get('support_resistance', 'N/A')}
        - Volume analysis: {market_data.get('technical', {}).get('volume', 'N/A')}
        - Momentum indicators: {market_data.get('technical', {}).get('momentum', 'N/A')}
        - RSI: {market_data.get('technical', {}).get('rsi', 'N/A')}
        - Moving averages: {market_data.get('technical', {}).get('moving_averages', 'N/A')}
        
        SOCIAL SENTIMENT (Weight: {weights['social']:.1%}):
        - Twitter sentiment: {market_data.get('social', {}).get('twitter_sentiment', 'N/A')}
        - Reddit sentiment: {market_data.get('social', {}).get('reddit_sentiment', 'N/A')}
        - Community activity: {market_data.get('social', {}).get('community_activity', 'N/A')}
        - Influencer sentiment: {market_data.get('social', {}).get('influencer_sentiment', 'N/A')}
        - Social momentum score: {market_data.get('social', {}).get('momentum_score', 'N/A')}
        
        NEWS & MEDIA (Weight: {weights['news']:.1%}):
        - Recent headlines: {market_data.get('news', {}).get('headlines', 'N/A')}
        - Media sentiment: {market_data.get('news', {}).get('sentiment', 'N/A')}
        - Coverage volume: {market_data.get('news', {}).get('coverage_volume', 'N/A')}
        
        MACRO ECONOMIC FACTORS (Weight: {weights['macro_economic']:.1%}):
        - Fed policy: {market_data.get('economic', {}).get('fed_policy', 'N/A')}
        - Inflation data: {market_data.get('economic', {}).get('inflation', 'N/A')}
        - Economic indicators: {market_data.get('economic', {}).get('indicators', 'N/A')}
        - Dollar strength: {market_data.get('economic', {}).get('dollar_strength', 'N/A')}
        - Interest rates: {market_data.get('economic', {}).get('interest_rates', 'N/A')}
        
        POLITICAL FACTORS (Weight: {weights['political']:.1%}):
        - Government stability: {market_data.get('political', {}).get('government_stability', 'N/A')}
        - Political events: {market_data.get('political', {}).get('events', 'N/A')}
        - Geopolitical tensions: {market_data.get('political', {}).get('geopolitical', 'N/A')}
        - Policy announcements: {market_data.get('political', {}).get('policy_announcements', 'N/A')}
        
        REGULATORY ENVIRONMENT (Weight: {weights['regulatory']:.1%}):
        - Regulatory news: {market_data.get('regulatory', {}).get('news', 'N/A')}
        - Compliance updates: {market_data.get('regulatory', {}).get('compliance', 'N/A')}
        - Legal developments: {market_data.get('regulatory', {}).get('legal', 'N/A')}
        
        MARKET STRUCTURE (Weight: {weights['market_structure']:.1%}):
        - Institutional flows: {market_data.get('market_structure', {}).get('institutional_flows', 'N/A')}
        - Exchange flows: {market_data.get('market_structure', {}).get('exchange_flows', 'N/A')}
        - Derivatives data: {market_data.get('market_structure', {}).get('derivatives', 'N/A')}
        - On-chain metrics: {market_data.get('market_structure', {}).get('onchain', 'N/A')}
        
        VOLATILITY ANALYSIS (Weight: {weights['volatility']:.1%}):
        - Current volatility: {market_data.get('volatility', {}).get('current', 'N/A')}
        - Volatility trends: {market_data.get('volatility', {}).get('trends', 'N/A')}
        - Risk metrics: {market_data.get('volatility', {}).get('risk_metrics', 'N/A')}
        
        ANALYSIS REQUIREMENTS:
        
        1. OVERALL MARKET ASSESSMENT:
           - Market regime (trending/ranging/volatile/crisis)
           - Risk level (low/medium/high/critical)
           - Primary market drivers (ranked by importance)
           - Secondary factors
        
        2. SIGNAL ANALYSIS:
           - Primary trading signal (buy/sell/hold)
           - Signal strength (0-1)
           - Confidence level (0-1)
           - Time horizon (immediate/short-term/medium-term)
        
        3. FACTOR WEIGHTING ANALYSIS:
           - Most important factors (ranked 1-5)
           - Factor interactions and correlations
           - Conflicting signals resolution
        
        4. RISK ASSESSMENT:
           - Key risk factors
           - Risk mitigation strategies
           - Position sizing recommendations
           - Stop loss levels
        
        5. SCENARIO ANALYSIS:
           - Bull case scenario (probability: 0-1)
           - Bear case scenario (probability: 0-1)
           - Base case scenario (probability: 0-1)
        
        6. TRADING RECOMMENDATIONS:
           - Immediate action
           - Entry strategy
           - Position sizing (percentage of portfolio)
           - Risk management
           - Profit targets
        
        CRITICAL EVENT ESCALATION:
        If any political, regulatory, or macro-economic factors show critical levels (>0.8), 
        provide detailed analysis of potential market disruption and immediate trading implications.
        
        IMPORTANT: Respond with valid JSON format for programmatic processing. Include all required fields.
        """
        
        return prompt
    
    async def analyze_market(
        self, 
        coin: str, 
        market_data: Dict[str, Any], 
        analysis_mode: str = "normal"
    ) -> Dict[str, Any]:
        """
        Perform comprehensive market analysis
        
        Args:
            coin: Cryptocurrency symbol (e.g., 'BTC', 'ETH')
            market_data: Dictionary containing all market data
            analysis_mode: Analysis mode ('normal', 'alert', 'crisis', 'emergency')
            
        Returns:
            Comprehensive analysis results
        """
        try:
            # Get appropriate weights for analysis mode
            weights = self.analysis_weights.get(analysis_mode, self.analysis_weights["normal"])
            
            # Build comprehensive prompt
            prompt = self._build_comprehensive_prompt(coin, market_data, weights)
            
            # Get LLM response
            response = await self.llm_client.generate_response(
                prompt,
                temperature=0.1,  # Low temperature for consistent analysis
                max_tokens=4000
            )
            
            # Extract content from response
            if self.llm_client.config.provider == LLMProvider.OPENAI:
                content = response["choices"][0]["message"]["content"]
            elif self.llm_client.config.provider == LLMProvider.ANTHROPIC:
                content = response["content"][0]["text"]
            else:
                raise ValueError(f"Unsupported provider: {self.llm_client.config.provider}")
            
            # Parse JSON response
            try:
                analysis_result = json.loads(content)
            except json.JSONDecodeError:
                # If JSON parsing fails, create structured response
                analysis_result = {
                    "raw_response": content,
                    "parsing_error": "Failed to parse JSON response",
                    "analysis_mode": analysis_mode,
                    "weights_used": weights
                }
            
            # Add metadata
            analysis_result.update({
                "analysis_mode": analysis_mode,
                "weights_used": weights,
                "coin": coin,
                "timestamp": market_data.get("timestamp", "N/A")
            })
            
            self.logger.info(f"Comprehensive market analysis completed for {coin} in {analysis_mode} mode")
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"Error in comprehensive market analysis for {coin}: {e}")
            return {
                "error": str(e),
                "coin": coin,
                "analysis_mode": analysis_mode,
                "fallback": True
            }
    
    async def detect_crisis_events(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect potential crisis events that require escalated analysis
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            Crisis detection results
        """
        crisis_prompt = f"""
        Analyze the following market data for potential crisis events that could significantly impact cryptocurrency markets:
        
        POLITICAL FACTORS:
        - Government stability: {market_data.get('political', {}).get('government_stability', 'N/A')}
        - Political events: {market_data.get('political', {}).get('events', 'N/A')}
        - Geopolitical tensions: {market_data.get('political', {}).get('geopolitical', 'N/A')}
        
        ECONOMIC FACTORS:
        - Fed policy: {market_data.get('economic', {}).get('fed_policy', 'N/A')}
        - Banking system: {market_data.get('economic', {}).get('banking_system', 'N/A')}
        - Economic indicators: {market_data.get('economic', {}).get('indicators', 'N/A')}
        
        REGULATORY FACTORS:
        - Regulatory news: {market_data.get('regulatory', {}).get('news', 'N/A')}
        - Legal developments: {market_data.get('regulatory', {}).get('legal', 'N/A')}
        
        MARKET FACTORS:
        - Volatility: {market_data.get('volatility', {}).get('current', 'N/A')}
        - Liquidity: {market_data.get('market_structure', {}).get('liquidity', 'N/A')}
        
        CRISIS DETECTION CRITERIA:
        
        1. GOVERNMENT CRISIS INDICATORS (Score 0-1):
           - Government shutdown/instability
           - Political paralysis
           - Constitutional crisis
           - Leadership crisis
        
        2. ECONOMIC CRISIS INDICATORS (Score 0-1):
           - Banking system stress
           - Liquidity crisis
           - Economic recession signals
           - Currency crisis
        
        3. REGULATORY CRISIS INDICATORS (Score 0-1):
           - Major regulatory crackdown
           - Exchange shutdowns
           - Legal uncertainty
           - Compliance crisis
        
        4. MARKET CRISIS INDICATORS (Score 0-1):
           - Extreme volatility
           - Liquidity crisis
           - Market manipulation
           - Systemic risk
        
        Provide analysis in JSON format with:
        - crisis_score: Overall crisis score (0-1)
        - crisis_type: Primary crisis type
        - crisis_level: none/low/medium/high/critical
        - individual_scores: Scores for each crisis category
        - crisis_description: Detailed description
        - recommended_response: Recommended analysis mode (normal/alert/crisis/emergency)
        - immediate_actions: Immediate actions to take
        """
        
        try:
            response = await self.llm_client.generate_response(crisis_prompt)
            
            if self.llm_client.config.provider == LLMProvider.OPENAI:
                content = response["choices"][0]["message"]["content"]
            elif self.llm_client.config.provider == LLMProvider.ANTHROPIC:
                content = response["content"][0]["text"]
            else:
                raise ValueError(f"Unsupported provider: {self.llm_client.config.provider}")
            
            crisis_result = json.loads(content)
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
    
    def get_analysis_weights(self, mode: str) -> Dict[str, float]:
        """Get analysis weights for specified mode"""
        return self.analysis_weights.get(mode, self.analysis_weights["normal"])
