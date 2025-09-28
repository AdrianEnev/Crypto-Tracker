"""
Social sentiment feature engineering.
Creates features from social media and news sentiment data.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
import re
from datetime import datetime, timezone, timedelta


class SentimentFeatures:
    """
    Social sentiment feature generator.
    
    Creates features from social media sentiment, news sentiment,
    and market sentiment indicators.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.sentiment_cache = {}
        
        # Mock sentiment data for demonstration
        self.mock_sentiment_data = self._generate_mock_sentiment_data()
        
        # Sentiment keywords (simplified)
        self.positive_keywords = [
            'bullish', 'moon', 'pump', 'buy', 'long', 'hodl', 'diamond hands',
            'breakthrough', 'rally', 'surge', 'gains', 'profit', 'up'
        ]
        
        self.negative_keywords = [
            'bearish', 'dump', 'crash', 'sell', 'short', 'fud', 'paper hands',
            'decline', 'drop', 'loss', 'down', 'rekt', 'liquidated'
        ]
    
    def create_features(self, sentiment_data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Create sentiment features from social media and news data.
        
        Args:
            sentiment_data: DataFrame with sentiment data (optional)
            
        Returns:
            DataFrame with sentiment features
        """
        if sentiment_data is None:
            # Use mock data for demonstration
            sentiment_data = self.mock_sentiment_data
        
        features_df = pd.DataFrame(index=sentiment_data.index)
        
        # Social media sentiment features
        features_df = self._create_social_sentiment_features(features_df, sentiment_data)
        
        # News sentiment features
        features_df = self._create_news_sentiment_features(features_df, sentiment_data)
        
        # Volume and engagement features
        features_df = self._create_engagement_features(features_df, sentiment_data)
        
        # Sentiment momentum features
        features_df = self._create_sentiment_momentum_features(features_df, sentiment_data)
        
        # Influencer sentiment features
        features_df = self._create_influencer_features(features_df, sentiment_data)
        
        # Market sentiment indicators
        features_df = self._create_market_sentiment_features(features_df, sentiment_data)
        
        return features_df
    
    def _create_social_sentiment_features(self, features_df: pd.DataFrame,
                                        sentiment_data: pd.DataFrame) -> pd.DataFrame:
        """Create social media sentiment features."""
        
        # Twitter sentiment
        if 'twitter_sentiment' in sentiment_data.columns:
            features_df['twitter_sentiment_7d_ma'] = sentiment_data['twitter_sentiment'].rolling(7).mean()
            features_df['twitter_sentiment_30d_ma'] = sentiment_data['twitter_sentiment'].rolling(30).mean()
            features_df['twitter_sentiment_ratio_7d'] = sentiment_data['twitter_sentiment'] / features_df['twitter_sentiment_7d_ma']
            features_df['twitter_extreme_positive'] = (sentiment_data['twitter_sentiment'] > 0.8).astype(int)
            features_df['twitter_extreme_negative'] = (sentiment_data['twitter_sentiment'] < -0.8).astype(int)
        
        # Reddit sentiment
        if 'reddit_sentiment' in sentiment_data.columns:
            features_df['reddit_sentiment_7d_ma'] = sentiment_data['reddit_sentiment'].rolling(7).mean()
            features_df['reddit_sentiment_30d_ma'] = sentiment_data['reddit_sentiment'].rolling(30).mean()
            features_df['reddit_sentiment_ratio_7d'] = sentiment_data['reddit_sentiment'] / features_df['reddit_sentiment_7d_ma']
            features_df['reddit_extreme_positive'] = (sentiment_data['reddit_sentiment'] > 0.8).astype(int)
            features_df['reddit_extreme_negative'] = (sentiment_data['reddit_sentiment'] < -0.8).astype(int)
        
        # Combined social sentiment
        if 'twitter_sentiment' in sentiment_data.columns and 'reddit_sentiment' in sentiment_data.columns:
            features_df['combined_social_sentiment'] = (
                sentiment_data['twitter_sentiment'] + sentiment_data['reddit_sentiment']
            ) / 2
            features_df['social_sentiment_7d_ma'] = features_df['combined_social_sentiment'].rolling(7).mean()
            features_df['social_sentiment_30d_ma'] = features_df['combined_social_sentiment'].rolling(30).mean()
        
        # Sentiment divergence
        if 'twitter_sentiment' in sentiment_data.columns and 'reddit_sentiment' in sentiment_data.columns:
            features_df['sentiment_divergence'] = abs(
                sentiment_data['twitter_sentiment'] - sentiment_data['reddit_sentiment']
            )
            features_df['high_sentiment_divergence'] = (features_df['sentiment_divergence'] > 0.5).astype(int)
        
        return features_df
    
    def _create_news_sentiment_features(self, features_df: pd.DataFrame,
                                      sentiment_data: pd.DataFrame) -> pd.DataFrame:
        """Create news sentiment features."""
        
        # News sentiment
        if 'news_sentiment' in sentiment_data.columns:
            features_df['news_sentiment_7d_ma'] = sentiment_data['news_sentiment'].rolling(7).mean()
            features_df['news_sentiment_30d_ma'] = sentiment_data['news_sentiment'].rolling(30).mean()
            features_df['news_sentiment_ratio_7d'] = sentiment_data['news_sentiment'] / features_df['news_sentiment_7d_ma']
            features_df['news_extreme_positive'] = (sentiment_data['news_sentiment'] > 0.8).astype(int)
            features_df['news_extreme_negative'] = (sentiment_data['news_sentiment'] < -0.8).astype(int)
        
        # News impact score
        if 'news_impact_score' in sentiment_data.columns:
            features_df['news_impact_7d_ma'] = sentiment_data['news_impact_score'].rolling(7).mean()
            features_df['news_impact_30d_ma'] = sentiment_data['news_impact_score'].rolling(30).mean()
            features_df['high_impact_news'] = (sentiment_data['news_impact_score'] > 0.7).astype(int)
        
        # News volume
        if 'news_volume' in sentiment_data.columns:
            features_df['news_volume_7d_ma'] = sentiment_data['news_volume'].rolling(7).mean()
            features_df['news_volume_30d_ma'] = sentiment_data['news_volume'].rolling(30).mean()
            features_df['news_volume_ratio_7d'] = sentiment_data['news_volume'] / features_df['news_volume_7d_ma']
            features_df['high_news_volume'] = (features_df['news_volume_ratio_7d'] > 2).astype(int)
        
        return features_df
    
    def _create_engagement_features(self, features_df: pd.DataFrame,
                                  sentiment_data: pd.DataFrame) -> pd.DataFrame:
        """Create engagement and volume features."""
        
        # Social media volume
        if 'twitter_volume' in sentiment_data.columns:
            features_df['twitter_volume_7d_ma'] = sentiment_data['twitter_volume'].rolling(7).mean()
            features_df['twitter_volume_30d_ma'] = sentiment_data['twitter_volume'].rolling(30).mean()
            features_df['twitter_volume_ratio_7d'] = sentiment_data['twitter_volume'] / features_df['twitter_volume_7d_ma']
            features_df['twitter_volume_ratio_30d'] = sentiment_data['twitter_volume'] / features_df['twitter_volume_30d_ma']
        
        if 'reddit_volume' in sentiment_data.columns:
            features_df['reddit_volume_7d_ma'] = sentiment_data['reddit_volume'].rolling(7).mean()
            features_df['reddit_volume_30d_ma'] = sentiment_data['reddit_volume'].rolling(30).mean()
            features_df['reddit_volume_ratio_7d'] = sentiment_data['reddit_volume'] / features_df['reddit_volume_7d_ma']
            features_df['reddit_volume_ratio_30d'] = sentiment_data['reddit_volume'] / features_df['reddit_volume_30d_ma']
        
        # Engagement metrics
        if 'twitter_engagement' in sentiment_data.columns:
            features_df['twitter_engagement_7d_ma'] = sentiment_data['twitter_engagement'].rolling(7).mean()
            features_df['twitter_engagement_ratio_7d'] = sentiment_data['twitter_engagement'] / features_df['twitter_engagement_7d_ma']
        
        if 'reddit_engagement' in sentiment_data.columns:
            features_df['reddit_engagement_7d_ma'] = sentiment_data['reddit_engagement'].rolling(7).mean()
            features_df['reddit_engagement_ratio_7d'] = sentiment_data['reddit_engagement'] / features_df['reddit_engagement_7d_ma']
        
        # Viral content indicators
        if 'twitter_volume' in sentiment_data.columns and 'twitter_engagement' in sentiment_data.columns:
            features_df['twitter_viral_score'] = sentiment_data['twitter_volume'] * sentiment_data['twitter_engagement']
            features_df['twitter_viral_7d_ma'] = features_df['twitter_viral_score'].rolling(7).mean()
            features_df['viral_twitter'] = (features_df['twitter_viral_score'] > features_df['twitter_viral_7d_ma'] * 2).astype(int)
        
        return features_df
    
    def _create_sentiment_momentum_features(self, features_df: pd.DataFrame,
                                          sentiment_data: pd.DataFrame) -> pd.DataFrame:
        """Create sentiment momentum and trend features."""
        
        # Sentiment momentum
        if 'twitter_sentiment' in sentiment_data.columns:
            features_df['twitter_sentiment_momentum_3d'] = sentiment_data['twitter_sentiment'].rolling(3).mean()
            features_df['twitter_sentiment_momentum_7d'] = sentiment_data['twitter_sentiment'].rolling(7).mean()
            features_df['twitter_sentiment_acceleration'] = features_df['twitter_sentiment_momentum_3d'].diff()
        
        if 'reddit_sentiment' in sentiment_data.columns:
            features_df['reddit_sentiment_momentum_3d'] = sentiment_data['reddit_sentiment'].rolling(3).mean()
            features_df['reddit_sentiment_momentum_7d'] = sentiment_data['reddit_sentiment'].rolling(7).mean()
            features_df['reddit_sentiment_acceleration'] = features_df['reddit_sentiment_momentum_3d'].diff()
        
        # Sentiment trend strength
        if 'twitter_sentiment' in sentiment_data.columns:
            features_df['twitter_sentiment_trend_5d'] = sentiment_data['twitter_sentiment'].rolling(5).apply(
                lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) == 5 else np.nan
            )
            features_df['strong_twitter_trend'] = (abs(features_df['twitter_sentiment_trend_5d']) > 0.1).astype(int)
        
        # Sentiment reversal indicators
        if 'twitter_sentiment' in sentiment_data.columns:
            features_df['twitter_sentiment_reversal'] = (
                (sentiment_data['twitter_sentiment'].shift(1) > 0) & 
                (sentiment_data['twitter_sentiment'] < 0)
            ).astype(int)
            features_df['twitter_sentiment_reversal'] += (
                (sentiment_data['twitter_sentiment'].shift(1) < 0) & 
                (sentiment_data['twitter_sentiment'] > 0)
            ).astype(int)
        
        return features_df
    
    def _create_influencer_features(self, features_df: pd.DataFrame,
                                  sentiment_data: pd.DataFrame) -> pd.DataFrame:
        """Create influencer sentiment features."""
        
        # Influencer sentiment
        if 'influencer_sentiment' in sentiment_data.columns:
            features_df['influencer_sentiment_7d_ma'] = sentiment_data['influencer_sentiment'].rolling(7).mean()
            features_df['influencer_sentiment_30d_ma'] = sentiment_data['influencer_sentiment'].rolling(30).mean()
            features_df['influencer_sentiment_ratio_7d'] = sentiment_data['influencer_sentiment'] / features_df['influencer_sentiment_7d_ma']
            features_df['influencer_bullish'] = (sentiment_data['influencer_sentiment'] > 0.6).astype(int)
            features_df['influencer_bearish'] = (sentiment_data['influencer_sentiment'] < -0.6).astype(int)
        
        # Influencer activity
        if 'influencer_activity' in sentiment_data.columns:
            features_df['influencer_activity_7d_ma'] = sentiment_data['influencer_activity'].rolling(7).mean()
            features_df['influencer_activity_ratio_7d'] = sentiment_data['influencer_activity'] / features_df['influencer_activity_7d_ma']
            features_df['high_influencer_activity'] = (features_df['influencer_activity_ratio_7d'] > 1.5).astype(int)
        
        # Influencer impact
        if 'influencer_impact' in sentiment_data.columns:
            features_df['influencer_impact_7d_ma'] = sentiment_data['influencer_impact'].rolling(7).mean()
            features_df['high_influencer_impact'] = (sentiment_data['influencer_impact'] > 0.7).astype(int)
        
        # Influencer vs. crowd divergence
        if ('influencer_sentiment' in sentiment_data.columns and 
            'twitter_sentiment' in sentiment_data.columns):
            features_df['influencer_crowd_divergence'] = abs(
                sentiment_data['influencer_sentiment'] - sentiment_data['twitter_sentiment']
            )
            features_df['high_influencer_divergence'] = (features_df['influencer_crowd_divergence'] > 0.4).astype(int)
        
        return features_df
    
    def _create_market_sentiment_features(self, features_df: pd.DataFrame,
                                        sentiment_data: pd.DataFrame) -> pd.DataFrame:
        """Create market-wide sentiment indicators."""
        
        # Fear & Greed Index
        if 'fear_greed_index' in sentiment_data.columns:
            features_df['fear_greed_7d_ma'] = sentiment_data['fear_greed_index'].rolling(7).mean()
            features_df['fear_greed_30d_ma'] = sentiment_data['fear_greed_index'].rolling(30).mean()
            features_df['extreme_fear'] = (sentiment_data['fear_greed_index'] < 20).astype(int)
            features_df['extreme_greed'] = (sentiment_data['fear_greed_index'] > 80).astype(int)
            features_df['fear_greed_change'] = sentiment_data['fear_greed_index'].pct_change()
        
        # Put/Call ratio (if available)
        if 'put_call_ratio' in sentiment_data.columns:
            features_df['put_call_ratio_7d_ma'] = sentiment_data['put_call_ratio'].rolling(7).mean()
            features_df['high_put_call_ratio'] = (sentiment_data['put_call_ratio'] > 1.2).astype(int)
            features_df['low_put_call_ratio'] = (sentiment_data['put_call_ratio'] < 0.8).astype(int)
        
        # Funding rates sentiment
        if 'funding_rate' in sentiment_data.columns:
            features_df['funding_rate_7d_ma'] = sentiment_data['funding_rate'].rolling(7).mean()
            features_df['positive_funding'] = (sentiment_data['funding_rate'] > 0).astype(int)
            features_df['negative_funding'] = (sentiment_data['funding_rate'] < 0).astype(int)
            features_df['extreme_positive_funding'] = (sentiment_data['funding_rate'] > 0.01).astype(int)
            features_df['extreme_negative_funding'] = (sentiment_data['funding_rate'] < -0.01).astype(int)
        
        # Social dominance
        if 'social_dominance' in sentiment_data.columns:
            features_df['social_dominance_7d_ma'] = sentiment_data['social_dominance'].rolling(7).mean()
            features_df['social_dominance_30d_ma'] = sentiment_data['social_dominance'].rolling(30).mean()
            features_df['high_social_dominance'] = (sentiment_data['social_dominance'] > 0.8).astype(int)
        
        # Sentiment breadth
        if 'sentiment_breadth' in sentiment_data.columns:
            features_df['sentiment_breadth_7d_ma'] = sentiment_data['sentiment_breadth'].rolling(7).mean()
            features_df['positive_sentiment_breadth'] = (sentiment_data['sentiment_breadth'] > 0.6).astype(int)
            features_df['negative_sentiment_breadth'] = (sentiment_data['sentiment_breadth'] < 0.4).astype(int)
        
        return features_df
    
    def _generate_mock_sentiment_data(self) -> pd.DataFrame:
        """Generate mock sentiment data for demonstration."""
        dates = pd.date_range(start='2023-01-01', end='2024-01-01', freq='D')
        
        # Generate realistic mock data
        np.random.seed(42)
        n_days = len(dates)
        
        mock_data = pd.DataFrame(index=dates)
        
        # Social media sentiment (normalized to -1 to 1)
        mock_data['twitter_sentiment'] = np.random.normal(0, 0.3, n_days)
        mock_data['reddit_sentiment'] = np.random.normal(0, 0.25, n_days)
        
        # Social media volume and engagement
        mock_data['twitter_volume'] = np.random.normal(10000, 2000, n_days)
        mock_data['reddit_volume'] = np.random.normal(5000, 1000, n_days)
        mock_data['twitter_engagement'] = np.random.uniform(0.1, 0.5, n_days)
        mock_data['reddit_engagement'] = np.random.uniform(0.15, 0.6, n_days)
        
        # News sentiment
        mock_data['news_sentiment'] = np.random.normal(0, 0.2, n_days)
        mock_data['news_impact_score'] = np.random.uniform(0, 1, n_days)
        mock_data['news_volume'] = np.random.normal(500, 100, n_days)
        
        # Influencer metrics
        mock_data['influencer_sentiment'] = np.random.normal(0, 0.25, n_days)
        mock_data['influencer_activity'] = np.random.normal(100, 20, n_days)
        mock_data['influencer_impact'] = np.random.uniform(0, 1, n_days)
        
        # Market sentiment indicators
        mock_data['fear_greed_index'] = np.random.uniform(20, 80, n_days)
        mock_data['put_call_ratio'] = np.random.uniform(0.5, 1.5, n_days)
        mock_data['funding_rate'] = np.random.normal(0, 0.005, n_days)
        mock_data['social_dominance'] = np.random.uniform(0.5, 0.9, n_days)
        mock_data['sentiment_breadth'] = np.random.uniform(0.3, 0.7, n_days)
        
        # Clamp sentiment values to [-1, 1] range
        for col in ['twitter_sentiment', 'reddit_sentiment', 'news_sentiment', 'influencer_sentiment']:
            mock_data[col] = np.clip(mock_data[col], -1, 1)
        
        # Ensure positive values for volume and engagement
        for col in ['twitter_volume', 'reddit_volume', 'news_volume', 'influencer_activity']:
            mock_data[col] = mock_data[col].abs()
        
        return mock_data
    
    def analyze_sentiment_text(self, text: str) -> Dict[str, float]:
        """
        Simple sentiment analysis of text (placeholder implementation).
        
        In production, this would use:
        - Pre-trained sentiment models (BERT, RoBERTa)
        - VADER sentiment analysis
        - Custom crypto-specific sentiment models
        """
        text_lower = text.lower()
        
        positive_count = sum(1 for word in self.positive_keywords if word in text_lower)
        negative_count = sum(1 for word in self.negative_keywords if word in text_lower)
        
        total_sentiment_words = positive_count + negative_count
        
        if total_sentiment_words == 0:
            return {'sentiment': 0.0, 'confidence': 0.0}
        
        sentiment_score = (positive_count - negative_count) / total_sentiment_words
        confidence = min(1.0, total_sentiment_words / 10.0)  # More words = higher confidence
        
        return {
            'sentiment': sentiment_score,
            'confidence': confidence,
            'positive_words': positive_count,
            'negative_words': negative_count
        }
    
    def fetch_real_sentiment_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch real sentiment data from APIs (placeholder implementation).
        
        In production, this would integrate with:
        - Twitter API v2
        - Reddit API
        - News APIs (Alpha Vantage, NewsAPI)
        - Sentiment analysis services
        """
        print(f"Fetching real sentiment data for {symbol} from {start_date} to {end_date}")
        print("Note: Using mock data for demonstration")
        
        return self.mock_sentiment_data
    
    def get_feature_summary(self, features_df: pd.DataFrame) -> Dict:
        """Get summary statistics of sentiment features."""
        numeric_features = features_df.select_dtypes(include=[np.number])
        
        return {
            'total_features': len(numeric_features.columns),
            'missing_values': numeric_features.isnull().sum().sum(),
            'feature_types': {
                'social_features': len([col for col in numeric_features.columns if any(x in col for x in ['twitter', 'reddit', 'social'])]),
                'news_features': len([col for col in numeric_features.columns if 'news' in col]),
                'engagement_features': len([col for col in numeric_features.columns if any(x in col for x in ['volume', 'engagement', 'viral'])]),
                'momentum_features': len([col for col in numeric_features.columns if any(x in col for x in ['momentum', 'trend', 'acceleration'])]),
                'influencer_features': len([col for col in numeric_features.columns if 'influencer' in col]),
                'market_sentiment_features': len([col for col in numeric_features.columns if any(x in col for x in ['fear_greed', 'put_call', 'funding', 'dominance'])])
            }
        }
