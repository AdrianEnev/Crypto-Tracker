"""
LLM-powered on-chain data analyzer.
Uses OpenAI GPT to analyze free blockchain data and social media for on-chain insights.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import json

from ...intelligence.models import OnChainSignal
from ...llm.client import LLMClient, LLMConfig, LLMProvider
from .free_onchain_analyzer import FreeOnChainAnalyzer, FreeOnChainData


class LLMOnChainAnalyzer:
    """
    LLM-powered on-chain data analyzer.
    
    Combines:
    - Free blockchain data from public APIs
    - Social media sentiment analysis
    - LLM analysis for pattern recognition and insights
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Initialize components
        self.free_analyzer = FreeOnChainAnalyzer(config)
        
        # Create LLMConfig from dict
        llm_config_dict = config.get('llm', {})
        llm_config = LLMConfig(
            provider=LLMProvider(llm_config_dict.get('provider', 'openai')),
            model=llm_config_dict.get('model', 'gpt-4o-mini'),
            api_key=llm_config_dict.get('api_key'),
            base_url=llm_config_dict.get('base_url'),
            max_tokens=llm_config_dict.get('max_tokens', 4000),
            temperature=llm_config_dict.get('temperature', 0.1),
            timeout=llm_config_dict.get('timeout', 30),
            max_retries=llm_config_dict.get('max_retries', 3),
            rate_limit_per_minute=llm_config_dict.get('rate_limit_per_minute', 60),
            enable_caching=llm_config_dict.get('enable_caching', True),
            cache_ttl_seconds=llm_config_dict.get('cache_ttl_seconds', 300)
        )
        self.llm_client = LLMClient(llm_config)
        
        # Analysis prompts
        self.analysis_prompt = """
        Analyze the following on-chain and social media data for {symbol} and provide trading insights:

        ON-CHAIN DATA:
        - Transaction Count: {transaction_count}
        - Active Addresses: {active_addresses}
        - Network Hash Rate: {network_hash_rate}
        - Mempool Size: {mempool_size}
        - Average Fee: {average_fee}
        - Large Transactions: {large_transactions}

        SOCIAL MEDIA SENTIMENT:
        - Twitter Sentiment: {twitter_sentiment}
        - Reddit Sentiment: {reddit_sentiment}
        - Overall Sentiment: {overall_sentiment}

        Please analyze this data and provide:
        1. Exchange flow assessment (0-1 scale, where 1 = heavy exchange activity)
        2. Whale activity assessment (0-1 scale, where 1 = high whale activity)
        3. Network health assessment (0-1 scale, where 1 = very healthy)
        4. Overall confidence in the analysis (0-1 scale)
        5. Key insights and patterns you've identified

        Respond in JSON format:
        {{
            "exchange_flow_score": 0.0-1.0,
            "whale_activity_score": 0.0-1.0,
            "network_health_score": 0.0-1.0,
            "confidence": 0.0-1.0,
            "insights": ["insight1", "insight2", ...],
            "patterns": ["pattern1", "pattern2", ...]
        }}
        """
    
    async def analyze(self, symbol: str, social_sentiment: Optional[Dict[str, Any]] = None) -> OnChainSignal:
        """
        Analyze on-chain data using LLM.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC', 'ETH')
            social_sentiment: Optional social media sentiment data
            
        Returns:
            OnChainSignal with LLM analysis results
        """
        try:
            # Get free on-chain data
            onchain_data = await self.free_analyzer._fetch_free_data(symbol)
            
            # Prepare data for LLM analysis
            analysis_data = self._prepare_analysis_data(onchain_data, social_sentiment)
            
            # Get LLM analysis
            llm_analysis = await self._get_llm_analysis(symbol, analysis_data)
            
            # Convert to OnChainSignal
            signal = self._convert_to_signal(llm_analysis, onchain_data.timestamp)
            
            return signal
            
        except Exception as e:
            self.logger.error(f"LLM on-chain analysis failed for {symbol}: {e}")
            # Fallback to free analyzer
            return await self.free_analyzer.analyze(symbol)
    
    def _prepare_analysis_data(self, onchain_data: FreeOnChainData, social_sentiment: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare data for LLM analysis."""
        
        # Extract social sentiment data
        twitter_sentiment = 0.0
        reddit_sentiment = 0.0
        overall_sentiment = 0.0
        
        if social_sentiment:
            twitter_sentiment = social_sentiment.get('twitter', {}).get('score', 0.0)
            reddit_sentiment = social_sentiment.get('reddit', {}).get('score', 0.0)
            overall_sentiment = social_sentiment.get('overall', {}).get('score', 0.0)
        
        return {
            'transaction_count': onchain_data.transaction_count or 0,
            'active_addresses': onchain_data.active_addresses or 0,
            'network_hash_rate': onchain_data.network_hash_rate or 0,
            'mempool_size': onchain_data.mempool_size or 0,
            'average_fee': onchain_data.average_fee or 0,
            'large_transactions': onchain_data.large_transactions or 0,
            'twitter_sentiment': twitter_sentiment,
            'reddit_sentiment': reddit_sentiment,
            'overall_sentiment': overall_sentiment
        }
    
    async def _get_llm_analysis(self, symbol: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Get LLM analysis of the data."""
        
        # Format the prompt
        prompt = self.analysis_prompt.format(
            symbol=symbol,
            **data
        )
        
        try:
            # Get LLM response
            response = await self.llm_client.generate_response(
                prompt=prompt,
                max_tokens=500,
                temperature=0.3  # Lower temperature for more consistent analysis
            )
            
            # Parse JSON response
            try:
                analysis = json.loads(response)
                return analysis
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract JSON from response
                analysis = self._extract_json_from_response(response)
                return analysis
                
        except Exception as e:
            self.logger.error(f"LLM analysis failed: {e}")
            # Return default analysis
            return self._get_default_analysis(data)
    
    def _extract_json_from_response(self, response: str) -> Dict[str, Any]:
        """Extract JSON from LLM response if it's not pure JSON."""
        try:
            # Look for JSON block in response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx]
                return json.loads(json_str)
            else:
                # No JSON found, return default
                return self._get_default_analysis({})
                
        except Exception as e:
            self.logger.error(f"JSON extraction failed: {e}")
            return self._get_default_analysis({})
    
    def _get_default_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Get default analysis when LLM fails."""
        
        # Simple heuristics based on the data
        exchange_flow_score = 0.5
        whale_activity_score = 0.5
        network_health_score = 0.5
        confidence = 0.3
        
        # Adjust based on available data
        if data.get('transaction_count', 0) > 0:
            confidence += 0.2
        if data.get('active_addresses', 0) > 0:
            confidence += 0.2
        if data.get('mempool_size', 0) > 0:
            confidence += 0.1
        if data.get('average_fee', 0) > 0:
            confidence += 0.1
        
        return {
            'exchange_flow_score': exchange_flow_score,
            'whale_activity_score': whale_activity_score,
            'network_health_score': network_health_score,
            'confidence': min(confidence, 1.0),
            'insights': ['LLM analysis unavailable, using fallback heuristics'],
            'patterns': ['Default pattern detection']
        }
    
    def _convert_to_signal(self, analysis: Dict[str, Any], timestamp: datetime) -> OnChainSignal:
        """Convert LLM analysis to OnChainSignal."""
        
        return OnChainSignal(
            exchange_flow_score=analysis.get('exchange_flow_score', 0.0),
            whale_activity_score=analysis.get('whale_activity_score', 0.0),
            miner_pressure_score=analysis.get('network_health_score', 0.0),  # Map to miner_pressure_score
            confidence=analysis.get('confidence', 0.0),
            timestamp=timestamp
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get analyzer statistics."""
        return {
            'free_analyzer_stats': self.free_analyzer.get_stats(),
            'llm_client_stats': self.llm_client.get_stats() if hasattr(self.llm_client, 'get_stats') else {},
            'analyzer_type': 'llm_onchain'
        }
