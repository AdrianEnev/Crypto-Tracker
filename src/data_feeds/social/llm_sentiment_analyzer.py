"""
LLM-Enhanced Social Media Sentiment Analyzer

Uses GPT to provide advanced sentiment analysis beyond simple keyword matching.
Analyzes context, sarcasm, market-specific sentiment, and trend detection.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
import json

from ...intelligence.models import SocialSentiment
from ...llm.client import LLMClient


class LLMSentimentAnalyzer:
    """
    LLM-enhanced sentiment analyzer for social media data.
    
    Features:
    - Context-aware sentiment analysis
    - Sarcasm and irony detection
    - Market-specific sentiment (technical vs fundamental)
    - Trend detection and momentum analysis
    - News impact assessment
    - Confidence scoring based on analysis quality
    """
    
    def __init__(self, llm_client: LLMClient, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.llm_client = llm_client
        self.config = config
        
        # Analysis prompts
        self.sentiment_prompt = """
        Analyze the sentiment of the following cryptocurrency-related social media posts for {symbol}:

        POSTS:
        {posts}

        Please provide a comprehensive sentiment analysis including:

        1. OVERALL SENTIMENT (score from -1.0 to 1.0):
           - -1.0 = Extremely bearish
           - 0.0 = Neutral
           - 1.0 = Extremely bullish

        2. SENTIMENT BREAKDOWN:
           - Technical sentiment (chart analysis, indicators)
           - Fundamental sentiment (news, adoption, partnerships)
           - Market sentiment (fear, greed, FOMO)

        3. CONTEXT ANALYSIS:
           - Sarcasm/irony detection
           - News impact assessment
           - Trend momentum (accelerating, decelerating, reversing)

        4. CONFIDENCE ASSESSMENT (0.0 to 1.0):
           - Based on post volume, agreement, and clarity

        5. KEY INSIGHTS:
           - Main themes and topics
           - Unusual patterns or spikes
           - Market-moving information

        Respond in JSON format:
        {{
            "overall_sentiment": -1.0 to 1.0,
            "technical_sentiment": -1.0 to 1.0,
            "fundamental_sentiment": -1.0 to 1.0,
            "market_sentiment": -1.0 to 1.0,
            "confidence": 0.0 to 1.0,
            "sarcasm_detected": true/false,
            "news_impact": "high"/"medium"/"low",
            "trend_momentum": "accelerating"/"stable"/"decelerating"/"reversing",
            "key_themes": ["theme1", "theme2", ...],
            "unusual_patterns": ["pattern1", "pattern2", ...],
            "market_moving_info": ["info1", "info2", ...]
        }}
        """
        
        self.trend_analysis_prompt = """
        Analyze the trend and momentum in cryptocurrency social media sentiment for {symbol}:

        CURRENT POSTS:
        {current_posts}

        PREVIOUS ANALYSIS (if available):
        {previous_analysis}

        Provide trend analysis including:

        1. MOMENTUM DIRECTION:
           - "bullish_accelerating" - Sentiment improving and gaining speed
           - "bullish_stable" - Sentiment positive but stable
           - "bullish_decelerating" - Sentiment positive but slowing
           - "bearish_accelerating" - Sentiment worsening and gaining speed
           - "bearish_stable" - Sentiment negative but stable
           - "bearish_decelerating" - Sentiment negative but slowing
           - "neutral" - No clear trend

        2. TREND STRENGTH (0.0 to 1.0):
           - How strong is the current trend

        3. REVERSAL SIGNALS:
           - Any signs of sentiment reversal
           - Contrarian indicators

        4. VOLUME ANALYSIS:
           - Is discussion volume increasing/decreasing
           - Quality of engagement

        Respond in JSON format:
        {{
            "momentum_direction": "bullish_accelerating",
            "trend_strength": 0.0 to 1.0,
            "reversal_signals": ["signal1", "signal2", ...],
            "volume_trend": "increasing"/"stable"/"decreasing",
            "engagement_quality": "high"/"medium"/"low",
            "contrarian_indicators": ["indicator1", "indicator2", ...]
        }}
        """
    
    async def analyze_sentiment(
        self, 
        symbol: str, 
        posts: List[Dict[str, Any]], 
        previous_analysis: Optional[Dict[str, Any]] = None
    ) -> SocialSentiment:
        """
        Analyze sentiment using LLM.
        
        Args:
            symbol: Cryptocurrency symbol
            posts: List of social media posts
            previous_analysis: Previous analysis for trend detection
            
        Returns:
            Enhanced SocialSentiment with LLM analysis
        """
        try:
            if not posts or len(posts) == 0:
                return SocialSentiment.default()
            
            # Format posts for analysis
            formatted_posts = self._format_posts_for_analysis(posts)
            
            # Get LLM sentiment analysis
            sentiment_analysis = await self._get_sentiment_analysis(symbol, formatted_posts)
            
            # Get trend analysis if previous data available
            trend_analysis = None
            if previous_analysis:
                trend_analysis = await self._get_trend_analysis(
                    symbol, formatted_posts, previous_analysis
                )
            
            # Combine analyses
            enhanced_sentiment = self._combine_analyses(
                sentiment_analysis, trend_analysis, posts
            )
            
            return enhanced_sentiment
            
        except Exception as e:
            self.logger.error(f"LLM sentiment analysis failed for {symbol}: {e}")
            # Fallback to simple sentiment
            return self._fallback_sentiment(posts)
    
    def _format_posts_for_analysis(self, posts: List[Dict[str, Any]]) -> str:
        """Format posts for LLM analysis."""
        formatted_posts = []
        
        for i, post in enumerate(posts[:20]):  # Limit to 20 posts for token efficiency
            text = post.get('text', '') or post.get('content', '') or post.get('body', '')
            if not text:
                continue
                
            # Truncate long posts
            if len(text) > 500:
                text = text[:500] + "..."
            
            # Add metadata if available
            metadata = []
            if 'score' in post:
                metadata.append(f"score: {post['score']}")
            if 'num_comments' in post:
                metadata.append(f"comments: {post['num_comments']}")
            if 'created_utc' in post:
                metadata.append(f"time: {post['created_utc']}")
            
            metadata_str = f" ({', '.join(metadata)})" if metadata else ""
            formatted_posts.append(f"{i+1}. {text}{metadata_str}")
        
        return "\n".join(formatted_posts)
    
    async def _get_sentiment_analysis(self, symbol: str, formatted_posts: str) -> Dict[str, Any]:
        """Get sentiment analysis from LLM."""
        
        prompt = self.sentiment_prompt.format(
            symbol=symbol,
            posts=formatted_posts
        )
        
        try:
            response = await self.llm_client.generate_response(
                prompt=prompt,
                max_tokens=800,
                temperature=0.3  # Lower temperature for more consistent analysis
            )
            
            # Parse JSON response
            try:
                # Handle different response formats
                if isinstance(response, dict):
                    if 'choices' in response:
                        content = response['choices'][0]['message']['content']
                        analysis = json.loads(content)
                    else:
                        analysis = response
                else:
                    analysis = json.loads(response)
                return analysis
            except (json.JSONDecodeError, KeyError, IndexError):
                # If JSON parsing fails, try to extract JSON from response
                analysis = self._extract_json_from_response(str(response))
                return analysis
                
        except Exception as e:
            self.logger.error(f"LLM sentiment analysis failed: {e}")
            return self._get_default_sentiment_analysis()
    
    async def _get_trend_analysis(
        self, 
        symbol: str, 
        formatted_posts: str, 
        previous_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get trend analysis from LLM."""
        
        prompt = self.trend_analysis_prompt.format(
            symbol=symbol,
            current_posts=formatted_posts,
            previous_analysis=json.dumps(previous_analysis, indent=2)
        )
        
        try:
            response = await self.llm_client.generate_response(
                prompt=prompt,
                max_tokens=600,
                temperature=0.3
            )
            
            try:
                analysis = json.loads(response)
                return analysis
            except json.JSONDecodeError:
                analysis = self._extract_json_from_response(response)
                return analysis
                
        except Exception as e:
            self.logger.error(f"LLM trend analysis failed: {e}")
            return self._get_default_trend_analysis()
    
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
                return self._get_default_sentiment_analysis()
                
        except Exception as e:
            self.logger.error(f"JSON extraction failed: {e}")
            return self._get_default_sentiment_analysis()
    
    def _get_default_sentiment_analysis(self) -> Dict[str, Any]:
        """Get default sentiment analysis when LLM fails."""
        return {
            "overall_sentiment": 0.0,
            "technical_sentiment": 0.0,
            "fundamental_sentiment": 0.0,
            "market_sentiment": 0.0,
            "confidence": 0.3,
            "sarcasm_detected": False,
            "news_impact": "low",
            "trend_momentum": "stable",
            "key_themes": ["LLM analysis unavailable"],
            "unusual_patterns": [],
            "market_moving_info": []
        }
    
    def _get_default_trend_analysis(self) -> Dict[str, Any]:
        """Get default trend analysis when LLM fails."""
        return {
            "momentum_direction": "neutral",
            "trend_strength": 0.0,
            "reversal_signals": [],
            "volume_trend": "stable",
            "engagement_quality": "medium",
            "contrarian_indicators": []
        }
    
    def _combine_analyses(
        self, 
        sentiment_analysis: Dict[str, Any], 
        trend_analysis: Optional[Dict[str, Any]], 
        posts: List[Dict[str, Any]]
    ) -> SocialSentiment:
        """Combine sentiment and trend analyses into SocialSentiment."""
        
        # Calculate overall score
        overall_sentiment = sentiment_analysis.get('overall_sentiment', 0.0)
        
        # Calculate confidence
        base_confidence = sentiment_analysis.get('confidence', 0.3)
        
        # Adjust confidence based on analysis quality
        if sentiment_analysis.get('sarcasm_detected', False):
            base_confidence *= 0.8  # Reduce confidence if sarcasm detected
        
        if sentiment_analysis.get('news_impact') == 'high':
            base_confidence *= 1.2  # Increase confidence for high-impact news
        
        # Adjust based on trend analysis
        if trend_analysis:
            trend_strength = trend_analysis.get('trend_strength', 0.0)
            base_confidence = (base_confidence + trend_strength) / 2
        
        # Calculate volume
        volume = len(posts)
        
        # Create metadata
        metadata = {
            'llm_enhanced': True,
            'technical_sentiment': sentiment_analysis.get('technical_sentiment', 0.0),
            'fundamental_sentiment': sentiment_analysis.get('fundamental_sentiment', 0.0),
            'market_sentiment': sentiment_analysis.get('market_sentiment', 0.0),
            'sarcasm_detected': sentiment_analysis.get('sarcasm_detected', False),
            'news_impact': sentiment_analysis.get('news_impact', 'low'),
            'trend_momentum': sentiment_analysis.get('trend_momentum', 'stable'),
            'key_themes': sentiment_analysis.get('key_themes', []),
            'unusual_patterns': sentiment_analysis.get('unusual_patterns', []),
            'market_moving_info': sentiment_analysis.get('market_moving_info', [])
        }
        
        # Add trend analysis if available
        if trend_analysis:
            metadata.update({
                'momentum_direction': trend_analysis.get('momentum_direction', 'neutral'),
                'trend_strength': trend_analysis.get('trend_strength', 0.0),
                'reversal_signals': trend_analysis.get('reversal_signals', []),
                'volume_trend': trend_analysis.get('volume_trend', 'stable'),
                'engagement_quality': trend_analysis.get('engagement_quality', 'medium'),
                'contrarian_indicators': trend_analysis.get('contrarian_indicators', [])
            })
        
        return SocialSentiment(
            score=overall_sentiment,
            volume=volume,
            confidence=min(base_confidence, 1.0),
            sources=['llm_enhanced'],
            timestamp=datetime.now(timezone.utc),
            metadata=metadata
        )
    
    def _fallback_sentiment(self, posts: List[Dict[str, Any]]) -> SocialSentiment:
        """Fallback to simple sentiment analysis."""
        if not posts:
            return SocialSentiment.default()
        
        # Simple keyword-based sentiment
        positive_words = ['bullish', 'moon', 'pump', 'buy', 'long', 'up', 'gain', 'profit']
        negative_words = ['bearish', 'dump', 'sell', 'short', 'down', 'loss', 'crash']
        
        total_sentiment = 0.0
        analyzed_posts = 0
        
        for post in posts:
            text = post.get('text', '') or post.get('content', '') or post.get('body', '')
            if not text:
                continue
                
            text_lower = text.lower()
            positive_count = sum(1 for word in positive_words if word in text_lower)
            negative_count = sum(1 for word in negative_words if word in text_lower)
            
            total = positive_count + negative_count
            if total > 0:
                sentiment = (positive_count - negative_count) / total
                total_sentiment += sentiment
                analyzed_posts += 1
        
        if analyzed_posts == 0:
            return SocialSentiment.default()
        
        avg_sentiment = total_sentiment / analyzed_posts
        
        return SocialSentiment(
            score=avg_sentiment,
            volume=len(posts),
            confidence=0.3,  # Lower confidence for fallback
            sources=['fallback'],
            timestamp=datetime.now(timezone.utc),
            metadata={'llm_enhanced': False, 'fallback_used': True}
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get analyzer statistics."""
        return {
            'analyzer_type': 'llm_enhanced',
            'llm_client_available': self.llm_client is not None,
            'config': self.config
        }
