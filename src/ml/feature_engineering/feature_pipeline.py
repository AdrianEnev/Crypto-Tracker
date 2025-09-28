"""
Main feature engineering pipeline that orchestrates feature creation.
Combines technical, alternative data, and market microstructure features.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .technical_features import TechnicalFeatures
from .onchain_features import OnChainFeatures
from .sentiment_features import SentimentFeatures
from .microstructure_features import MicrostructureFeatures


@dataclass
class FeatureConfig:
    """Configuration for feature engineering pipeline."""
    # Technical features
    include_technical: bool = True
    technical_lookbacks: List[int] = field(default_factory=lambda: [5, 10, 20, 50])
    
    # Alternative data features
    include_onchain: bool = True
    include_sentiment: bool = True
    include_microstructure: bool = True
    
    # Feature selection
    feature_selection: bool = True
    max_features: int = 100
    correlation_threshold: float = 0.95
    
    # Data quality
    min_data_points: int = 100
    handle_missing: str = "forward_fill"  # "forward_fill", "drop", "interpolate"


@dataclass
class FeatureSet:
    """Container for engineered features."""
    features: pd.DataFrame
    feature_names: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class FeaturePipeline:
    """
    Main feature engineering pipeline.
    
    Orchestrates the creation of features from multiple sources:
    - Technical indicators from price/volume data
    - On-chain blockchain metrics
    - Social sentiment data
    - Market microstructure features
    
    Features are designed to enhance existing trading strategies
    rather than replace them.
    """
    
    def __init__(self, config: Optional[FeatureConfig] = None):
        self.config = config or FeatureConfig()
        
        # Initialize feature generators
        self.technical_features = TechnicalFeatures()
        self.onchain_features = OnChainFeatures()
        self.sentiment_features = SentimentFeatures()
        self.microstructure_features = MicrostructureFeatures()
        
        # Feature cache for performance
        self.feature_cache: Dict[str, FeatureSet] = {}
        
    def create_features(self, 
                       market_data: pd.DataFrame,
                       alternative_data: Optional[Dict[str, pd.DataFrame]] = None,
                       symbol: str = "BTC-USDT") -> FeatureSet:
        """
        Create comprehensive feature set from market and alternative data.
        
        Args:
            market_data: OHLCV market data
            alternative_data: Dict of alternative data DataFrames
            symbol: Trading symbol for context
            
        Returns:
            FeatureSet with engineered features
        """
        print(f"Creating features for {symbol}...")
        
        # Initialize feature DataFrame with market data index
        features_df = market_data.copy()
        
        # Technical features
        if self.config.include_technical:
            print("  Adding technical features...")
            technical_features = self.technical_features.create_features(
                market_data, self.config.technical_lookbacks
            )
            features_df = pd.concat([features_df, technical_features], axis=1)
        
        # Alternative data features
        if alternative_data:
            # On-chain features
            if self.config.include_onchain and 'onchain' in alternative_data:
                print("  Adding on-chain features...")
                onchain_features = self.onchain_features.create_features(
                    alternative_data['onchain']
                )
                features_df = pd.concat([features_df, onchain_features], axis=1)
            
            # Sentiment features
            if self.config.include_sentiment and 'sentiment' in alternative_data:
                print("  Adding sentiment features...")
                sentiment_features = self.sentiment_features.create_features(
                    alternative_data['sentiment']
                )
                features_df = pd.concat([features_df, sentiment_features], axis=1)
            
            # Microstructure features
            if self.config.include_microstructure and 'microstructure' in alternative_data:
                print("  Adding microstructure features...")
                microstructure_features = self.microstructure_features.create_features(
                    alternative_data['microstructure']
                )
                features_df = pd.concat([features_df, microstructure_features], axis=1)
        
        # Feature engineering and selection
        features_df = self._engineer_features(features_df)
        
        if self.config.feature_selection:
            features_df = self._select_features(features_df)
        
        # Handle missing data
        features_df = self._handle_missing_data(features_df)
        
        # Create feature set
        feature_names = [col for col in features_df.columns 
                        if col not in ['open', 'high', 'low', 'close', 'volume']]
        
        feature_set = FeatureSet(
            features=features_df,
            feature_names=feature_names,
            metadata={
                'symbol': symbol,
                'total_features': len(feature_names),
                'data_points': len(features_df),
                'date_range': (features_df.index.min(), features_df.index.max())
            }
        )
        
        # Cache features
        cache_key = f"{symbol}_{len(features_df)}"
        self.feature_cache[cache_key] = feature_set
        
        print(f"  Created {len(feature_names)} features with {len(features_df)} data points")
        
        return feature_set
    
    def _engineer_features(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """Create additional engineered features."""
        print("  Engineering additional features...")
        
        # Price-based features
        if 'close' in features_df.columns:
            # Returns
            features_df['returns_1d'] = features_df['close'].pct_change()
            features_df['returns_5d'] = features_df['close'].pct_change(5)
            features_df['returns_20d'] = features_df['close'].pct_change(20)
            
            # Volatility
            features_df['volatility_5d'] = features_df['returns_1d'].rolling(5).std()
            features_df['volatility_20d'] = features_df['returns_1d'].rolling(20).std()
            
            # Price position within range
            if 'high' in features_df.columns and 'low' in features_df.columns:
                features_df['price_position'] = (
                    (features_df['close'] - features_df['low']) / 
                    (features_df['high'] - features_df['low'])
                )
            
            # Gap features
            features_df['gap_up'] = (features_df['open'] > features_df['close'].shift(1)).astype(int)
            features_df['gap_down'] = (features_df['open'] < features_df['close'].shift(1)).astype(int)
        
        # Volume-based features
        if 'volume' in features_df.columns:
            # Volume ratios
            features_df['volume_ratio_5d'] = (
                features_df['volume'] / features_df['volume'].rolling(5).mean()
            )
            features_df['volume_ratio_20d'] = (
                features_df['volume'] / features_df['volume'].rolling(20).mean()
            )
            
            # Volume-price relationship
            if 'close' in features_df.columns:
                features_df['volume_price_trend'] = (
                    features_df['volume'] * np.sign(features_df['returns_1d'])
                )
        
        # Time-based features
        features_df['hour'] = features_df.index.hour
        features_df['day_of_week'] = features_df.index.dayofweek
        features_df['is_weekend'] = (features_df['day_of_week'] >= 5).astype(int)
        
        # Market regime features (simplified)
        if 'volatility_20d' in features_df.columns:
            features_df['high_vol_regime'] = (
                features_df['volatility_20d'] > features_df['volatility_20d'].rolling(50).quantile(0.8)
            ).astype(int)
            
            features_df['low_vol_regime'] = (
                features_df['volatility_20d'] < features_df['volatility_20d'].rolling(50).quantile(0.2)
            ).astype(int)
        
        return features_df
    
    def _select_features(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """Select most relevant features using correlation analysis."""
        print("  Selecting features...")
        
        # Get feature columns (exclude OHLCV)
        feature_cols = [col for col in features_df.columns 
                       if col not in ['open', 'high', 'low', 'close', 'volume']]
        
        if len(feature_cols) <= self.config.max_features:
            return features_df
        
        # Calculate correlation matrix
        feature_data = features_df[feature_cols].dropna()
        corr_matrix = feature_data.corr().abs()
        
        # Find highly correlated pairs
        high_corr_pairs = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                if corr_matrix.iloc[i, j] > self.config.correlation_threshold:
                    high_corr_pairs.append((corr_matrix.columns[i], corr_matrix.columns[j]))
        
        # Remove one feature from each highly correlated pair
        features_to_remove = set()
        for feat1, feat2 in high_corr_pairs:
            # Keep feature with higher variance (more information)
            var1 = feature_data[feat1].var()
            var2 = feature_data[feat2].var()
            
            # Handle NaN values - convert to scalar if Series
            if hasattr(var1, 'iloc'):
                var1 = var1.iloc[0] if len(var1) > 0 else 0
            if hasattr(var2, 'iloc'):
                var2 = var2.iloc[0] if len(var2) > 0 else 0
            
            # Handle NaN values
            if pd.isna(var1):
                var1 = 0
            if pd.isna(var2):
                var2 = 0
            
            if var1 > var2:
                features_to_remove.add(feat2)
            else:
                features_to_remove.add(feat1)
        
        # Remove selected features
        selected_features = [col for col in feature_cols if col not in features_to_remove]
        
        # If still too many features, select top features by variance
        if len(selected_features) > self.config.max_features:
            feature_variance = feature_data[selected_features].var().sort_values(ascending=False)
            top_features = feature_variance.head(self.config.max_features).index.tolist()
            selected_features = top_features
        
        # Return DataFrame with selected features
        base_cols = ['open', 'high', 'low', 'close', 'volume']
        final_cols = [col for col in base_cols if col in features_df.columns] + selected_features
        
        print(f"    Selected {len(selected_features)} features from {len(feature_cols)}")
        
        return features_df[final_cols]
    
    def _handle_missing_data(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing data according to configuration."""
        print("  Handling missing data...")
        
        if self.config.handle_missing == "forward_fill":
            features_df = features_df.fillna(method='ffill')
        elif self.config.handle_missing == "drop":
            features_df = features_df.dropna()
        elif self.config.handle_missing == "interpolate":
            features_df = features_df.interpolate()
        
        # Drop rows with any remaining NaN values
        initial_rows = len(features_df)
        features_df = features_df.dropna()
        final_rows = len(features_df)
        
        if initial_rows != final_rows:
            print(f"    Dropped {initial_rows - final_rows} rows with missing data")
        
        return features_df
    
    def get_feature_importance(self, feature_set: FeatureSet, 
                             target: pd.Series) -> pd.DataFrame:
        """Calculate feature importance using simple correlation analysis."""
        feature_data = feature_set.features[feature_set.feature_names]
        
        # Calculate correlation with target
        correlations = []
        for feature in feature_set.feature_names:
            if feature in feature_data.columns:
                corr = feature_data[feature].corr(target)
                correlations.append(abs(corr) if not pd.isna(corr) else 0)
            else:
                correlations.append(0)
        
        importance_df = pd.DataFrame({
            'feature': feature_set.feature_names,
            'importance': correlations
        }).sort_values('importance', ascending=False)
        
        return importance_df
    
    def create_rolling_features(self, feature_set: FeatureSet, 
                              window_sizes: List[int] = [5, 10, 20]) -> FeatureSet:
        """Create rolling window features for time series models."""
        print("Creating rolling features...")
        
        features_df = feature_set.features.copy()
        
        for window in window_sizes:
            for feature in feature_set.feature_names:
                if feature in features_df.columns:
                    # Rolling statistics
                    features_df[f'{feature}_rolling_mean_{window}'] = (
                        features_df[feature].rolling(window).mean()
                    )
                    features_df[f'{feature}_rolling_std_{window}'] = (
                        features_df[feature].rolling(window).std()
                    )
                    features_df[f'{feature}_rolling_max_{window}'] = (
                        features_df[feature].rolling(window).max()
                    )
                    features_df[f'{feature}_rolling_min_{window}'] = (
                        features_df[feature].rolling(window).min()
                    )
        
        # Update feature names
        new_feature_names = [col for col in features_df.columns 
                           if col not in ['open', 'high', 'low', 'close', 'volume']]
        
        return FeatureSet(
            features=features_df,
            feature_names=new_feature_names,
            metadata=feature_set.metadata.copy()
        )
    
    def get_cached_features(self, symbol: str, data_points: int) -> Optional[FeatureSet]:
        """Retrieve cached features if available."""
        cache_key = f"{symbol}_{data_points}"
        return self.feature_cache.get(cache_key)
    
    def clear_cache(self) -> None:
        """Clear feature cache."""
        self.feature_cache.clear()
        print("Feature cache cleared")
