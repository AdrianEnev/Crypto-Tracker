"""
Regime Classification Model Training

Trains models to classify market regimes (trending, ranging, volatile, etc.)
using price data, technical indicators, and market conditions.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import logging
from pathlib import Path
import joblib
import json

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)


@dataclass
class RegimeData:
    """Container for regime classification training data."""
    features: np.ndarray
    labels: np.ndarray
    feature_names: List[str]
    timestamp: datetime
    coin_id: str
    timeframe: str


@dataclass
class RegimeModel:
    """Container for trained regime classification model."""
    model: Any
    scaler: StandardScaler
    feature_names: List[str]
    accuracy: float
    training_date: datetime
    coin_id: str
    timeframe: str
    model_type: str


class RegimeClassifierTrainer:
    """
    Trains regime classification models using historical price data.
    
    Features:
    - Multiple model types (Random Forest, Gradient Boosting)
    - Feature engineering (technical indicators, volatility, momentum)
    - Cross-validation and model selection
    - Model persistence and versioning
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Model configuration
        self.model_types = config.get('model_types', ['random_forest', 'gradient_boosting'])
        self.test_size = config.get('test_size', 0.2)
        self.random_state = config.get('random_state', 42)
        self.cv_folds = config.get('cv_folds', 5)
        
        # Feature engineering parameters
        self.lookback_periods = config.get('lookback_periods', [5, 10, 20, 50])
        self.volatility_periods = config.get('volatility_periods', [10, 20])
        self.momentum_periods = config.get('momentum_periods', [5, 10, 20])
        
        # Model storage
        self.models_dir = Path(config.get('models_dir', 'models/regime_classifiers'))
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Regime definitions
        self.regime_definitions = {
            'TRENDING_UP': 0,
            'TRENDING_DOWN': 1,
            'RANGING': 2,
            'VOLATILE': 3,
            'CONSOLIDATION': 4
        }
    
    def prepare_training_data(
        self, 
        price_data: pd.DataFrame, 
        coin_id: str, 
        timeframe: str
    ) -> RegimeData:
        """
        Prepare training data for regime classification.
        
        Args:
            price_data: DataFrame with OHLCV data
            coin_id: Cryptocurrency identifier
            timeframe: Timeframe (1d, 4h, 1h)
            
        Returns:
            RegimeData with features and labels
        """
        try:
            # Ensure we have required columns
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            if not all(col in price_data.columns for col in required_cols):
                raise ValueError(f"Missing required columns: {required_cols}")
            
            # Create features
            features_df = self._create_features(price_data)
            
            # Create labels (regime classification)
            labels = self._create_regime_labels(price_data)
            
            # Remove rows with NaN values
            valid_mask = ~(features_df.isna().any(axis=1) | pd.isna(labels))
            features_array = features_df[valid_mask].values
            labels_array = labels[valid_mask].values
            
            if len(features_array) == 0:
                raise ValueError("No valid training data after feature engineering")
            
            return RegimeData(
                features=features_array,
                labels=labels_array,
                feature_names=features_df.columns.tolist(),
                timestamp=datetime.now(timezone.utc),
                coin_id=coin_id,
                timeframe=timeframe
            )
            
        except Exception as e:
            self.logger.error(f"Failed to prepare training data: {e}")
            raise
    
    def _create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create feature matrix from price data."""
        features_df = pd.DataFrame(index=df.index)
        
        # Price-based features
        features_df['returns'] = df['close'].pct_change()
        features_df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        features_df['price_change'] = df['close'] - df['open']
        features_df['price_change_pct'] = (df['close'] - df['open']) / df['open']
        
        # Technical indicators
        for period in self.lookback_periods:
            # Moving averages
            features_df[f'sma_{period}'] = df['close'].rolling(period).mean()
            features_df[f'ema_{period}'] = df['close'].ewm(span=period).mean()
            
            # Price relative to moving averages
            features_df[f'price_vs_sma_{period}'] = df['close'] / features_df[f'sma_{period}'] - 1
            features_df[f'price_vs_ema_{period}'] = df['close'] / features_df[f'ema_{period}'] - 1
            
            # Volume features
            features_df[f'volume_sma_{period}'] = df['volume'].rolling(period).mean()
            features_df[f'volume_ratio_{period}'] = df['volume'] / features_df[f'volume_sma_{period}']
        
        # Volatility features
        for period in self.volatility_periods:
            features_df[f'volatility_{period}'] = df['close'].rolling(period).std()
            features_df[f'volatility_ratio_{period}'] = (
                features_df[f'volatility_{period}'] / features_df[f'volatility_{period}'].rolling(50).mean()
            )
        
        # Momentum features
        for period in self.momentum_periods:
            features_df[f'momentum_{period}'] = df['close'] / df['close'].shift(period) - 1
            features_df[f'rsi_{period}'] = self._calculate_rsi(df['close'], period)
        
        # Additional technical features
        features_df['bollinger_upper'] = self._calculate_bollinger_bands(df['close'], 20, 2)[0]
        features_df['bollinger_lower'] = self._calculate_bollinger_bands(df['close'], 20, 2)[1]
        features_df['bollinger_position'] = (
            (df['close'] - features_df['bollinger_lower']) / 
            (features_df['bollinger_upper'] - features_df['bollinger_lower'])
        )
        
        # Market structure features
        features_df['high_low_ratio'] = df['high'] / df['low']
        features_df['close_position'] = (df['close'] - df['low']) / (df['high'] - df['low'])
        features_df['volume_price_trend'] = df['volume'] * features_df['returns']
        
        # Trend strength
        features_df['trend_strength'] = self._calculate_trend_strength(df)
        
        return features_df
    
    def _create_regime_labels(self, df: pd.DataFrame) -> pd.Series:
        """Create regime labels based on price action patterns."""
        labels = pd.Series(index=df.index, dtype=int)
        
        # Calculate trend indicators
        sma_20 = df['close'].rolling(20).mean()
        sma_50 = df['close'].rolling(50).mean()
        volatility = df['close'].rolling(20).std()
        returns = df['close'].pct_change()
        
        # Trend direction
        trend_up = (sma_20 > sma_50) & (sma_20.shift(1) <= sma_50.shift(1))
        trend_down = (sma_20 < sma_50) & (sma_20.shift(1) >= sma_50.shift(1))
        
        # Volatility regime
        high_volatility = volatility > volatility.rolling(50).quantile(0.8)
        low_volatility = volatility < volatility.rolling(50).quantile(0.2)
        
        # Range-bound conditions
        price_range = (df['high'].rolling(20).max() - df['low'].rolling(20).min()) / df['close']
        ranging = price_range < price_range.rolling(50).quantile(0.3)
        
        # Assign regime labels
        labels[trend_up & ~high_volatility] = self.regime_definitions['TRENDING_UP']
        labels[trend_down & ~high_volatility] = self.regime_definitions['TRENDING_DOWN']
        labels[high_volatility] = self.regime_definitions['VOLATILE']
        labels[ranging & ~high_volatility] = self.regime_definitions['RANGING']
        labels[~trend_up & ~trend_down & ~high_volatility & ~ranging] = self.regime_definitions['CONSOLIDATION']
        
        return labels
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: float = 2) -> Tuple[pd.Series, pd.Series]:
        """Calculate Bollinger Bands."""
        sma = prices.rolling(period).mean()
        std = prices.rolling(period).std()
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        return upper, lower
    
    def _calculate_trend_strength(self, df: pd.DataFrame) -> pd.Series:
        """Calculate trend strength indicator."""
        # Simple trend strength based on consecutive moves
        returns = df['close'].pct_change()
        trend_strength = returns.rolling(10).apply(
            lambda x: np.sum(np.sign(x) == np.sign(x.iloc[-1])) / len(x)
        )
        return trend_strength
    
    def train_model(
        self, 
        regime_data: RegimeData, 
        model_type: str = 'random_forest'
    ) -> RegimeModel:
        """
        Train a regime classification model.
        
        Args:
            regime_data: Training data
            model_type: Type of model to train
            
        Returns:
            Trained RegimeModel
        """
        try:
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                regime_data.features,
                regime_data.labels,
                test_size=self.test_size,
                random_state=self.random_state,
                stratify=regime_data.labels
            )
            
            # Create model
            if model_type == 'random_forest':
                model = RandomForestClassifier(
                    n_estimators=100,
                    max_depth=10,
                    random_state=self.random_state,
                    n_jobs=-1
                )
            elif model_type == 'gradient_boosting':
                model = GradientBoostingClassifier(
                    n_estimators=100,
                    max_depth=6,
                    learning_rate=0.1,
                    random_state=self.random_state
                )
            else:
                raise ValueError(f"Unknown model type: {model_type}")
            
            # Create pipeline with scaling
            scaler = StandardScaler()
            pipeline = Pipeline([
                ('scaler', scaler),
                ('classifier', model)
            ])
            
            # Train model
            pipeline.fit(X_train, y_train)
            
            # Evaluate model
            y_pred = pipeline.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            
            # Cross-validation
            cv_scores = cross_val_score(pipeline, regime_data.features, regime_data.labels, cv=self.cv_folds)
            cv_mean = cv_scores.mean()
            cv_std = cv_scores.std()
            
            self.logger.info(f"Model trained - Accuracy: {accuracy:.3f}, CV: {cv_mean:.3f} ± {cv_std:.3f}")
            
            return RegimeModel(
                model=pipeline,
                scaler=scaler,
                feature_names=regime_data.feature_names,
                accuracy=accuracy,
                training_date=datetime.now(timezone.utc),
                coin_id=regime_data.coin_id,
                timeframe=regime_data.timeframe,
                model_type=model_type
            )
            
        except Exception as e:
            self.logger.error(f"Model training failed: {e}")
            raise
    
    def save_model(self, model: RegimeModel) -> str:
        """Save trained model to disk."""
        try:
            # Create model filename
            timestamp = model.training_date.strftime("%Y%m%d_%H%M%S")
            filename = f"{model.coin_id}_{model.timeframe}_{model.model_type}_{timestamp}.joblib"
            filepath = self.models_dir / filename
            
            # Save model
            joblib.dump(model, filepath)
            
            # Save metadata
            metadata = {
                'coin_id': model.coin_id,
                'timeframe': model.timeframe,
                'model_type': model.model_type,
                'accuracy': model.accuracy,
                'training_date': model.training_date.isoformat(),
                'feature_names': model.feature_names,
                'regime_definitions': self.regime_definitions
            }
            
            metadata_file = filepath.with_suffix('.json')
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            self.logger.info(f"Model saved to {filepath}")
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"Failed to save model: {e}")
            raise
    
    def load_model(self, filepath: str) -> RegimeModel:
        """Load trained model from disk."""
        try:
            model = joblib.load(filepath)
            self.logger.info(f"Model loaded from {filepath}")
            return model
        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get trainer statistics."""
        return {
            'models_dir': str(self.models_dir),
            'model_types': self.model_types,
            'regime_definitions': self.regime_definitions,
            'feature_engineering': {
                'lookback_periods': self.lookback_periods,
                'volatility_periods': self.volatility_periods,
                'momentum_periods': self.momentum_periods
            }
        }
