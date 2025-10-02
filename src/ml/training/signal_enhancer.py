"""
Signal Enhancement Model Training

Trains models to enhance trading signals using multiple data sources
including price data, social sentiment, on-chain data, and technical indicators.
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

from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)


@dataclass
class SignalData:
    """Container for signal enhancement training data."""
    features: np.ndarray
    targets: np.ndarray
    feature_names: List[str]
    timestamp: datetime
    coin_id: str
    timeframe: str


@dataclass
class SignalModel:
    """Container for trained signal enhancement model."""
    model: Any
    scaler: StandardScaler
    feature_names: List[str]
    r2_score: float
    mse: float
    mae: float
    training_date: datetime
    coin_id: str
    timeframe: str
    model_type: str


class SignalEnhancerTrainer:
    """
    Trains signal enhancement models using multiple data sources.
    
    Features:
    - Multi-source feature engineering (price, social, on-chain, technical)
    - Signal quality prediction and enhancement
    - Model ensemble and stacking
    - Performance evaluation and validation
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
        self.social_weight = config.get('social_weight', 0.3)
        self.onchain_weight = config.get('onchain_weight', 0.2)
        self.technical_weight = config.get('technical_weight', 0.5)
        
        # Model storage
        self.models_dir = Path(config.get('models_dir', 'models/signal_enhancers'))
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Signal quality thresholds
        self.signal_thresholds = {
            'excellent': 0.8,
            'good': 0.6,
            'fair': 0.4,
            'poor': 0.2
        }
    
    def prepare_training_data(
        self, 
        price_data: pd.DataFrame,
        social_data: Optional[pd.DataFrame] = None,
        onchain_data: Optional[pd.DataFrame] = None,
        coin_id: str = 'bitcoin',
        timeframe: str = '1d'
    ) -> SignalData:
        """
        Prepare training data for signal enhancement.
        
        Args:
            price_data: DataFrame with OHLCV data
            social_data: DataFrame with social sentiment data
            onchain_data: DataFrame with on-chain data
            coin_id: Cryptocurrency identifier
            timeframe: Timeframe
            
        Returns:
            SignalData with features and targets
        """
        try:
            # Create technical features
            technical_features = self._create_technical_features(price_data)
            
            # Create social features
            social_features = self._create_social_features(social_data) if social_data is not None else pd.DataFrame()
            
            # Create on-chain features
            onchain_features = self._create_onchain_features(onchain_data) if onchain_data is not None else pd.DataFrame()
            
            # Combine features
            all_features = pd.concat([technical_features, social_features, onchain_features], axis=1)
            
            # Create targets (signal quality scores)
            targets = self._create_signal_targets(price_data)
            
            # Align data
            common_index = all_features.index.intersection(targets.index)
            if len(common_index) == 0:
                raise ValueError("No common time index between features and targets")
            
            features_aligned = all_features.loc[common_index]
            targets_aligned = targets.loc[common_index]
            
            # Remove rows with NaN values
            valid_mask = ~(features_aligned.isna().any(axis=1) | pd.isna(targets_aligned))
            features_array = features_aligned[valid_mask].values
            targets_array = targets_aligned[valid_mask].values
            
            if len(features_array) == 0:
                raise ValueError("No valid training data after feature engineering")
            
            return SignalData(
                features=features_array,
                targets=targets_array,
                feature_names=features_aligned.columns.tolist(),
                timestamp=datetime.now(timezone.utc),
                coin_id=coin_id,
                timeframe=timeframe
            )
            
        except Exception as e:
            self.logger.error(f"Failed to prepare training data: {e}")
            raise
    
    def _create_technical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create technical analysis features."""
        features_df = pd.DataFrame(index=df.index)
        
        # Price-based features
        features_df['returns'] = df['close'].pct_change()
        features_df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        features_df['volatility'] = df['close'].rolling(20).std()
        features_df['price_momentum'] = df['close'] / df['close'].shift(20) - 1
        
        # Moving averages
        for period in self.lookback_periods:
            features_df[f'sma_{period}'] = df['close'].rolling(period).mean()
            features_df[f'ema_{period}'] = df['close'].ewm(span=period).mean()
            features_df[f'price_vs_sma_{period}'] = df['close'] / features_df[f'sma_{period}'] - 1
        
        # Technical indicators
        features_df['rsi'] = self._calculate_rsi(df['close'])
        features_df['macd'] = self._calculate_macd(df['close'])
        features_df['bollinger_position'] = self._calculate_bollinger_position(df['close'])
        features_df['stochastic'] = self._calculate_stochastic(df)
        
        # Volume features
        features_df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        features_df['volume_price_trend'] = df['volume'] * features_df['returns']
        
        # Market structure
        features_df['high_low_ratio'] = df['high'] / df['low']
        features_df['close_position'] = (df['close'] - df['low']) / (df['high'] - df['low'])
        
        return features_df
    
    def _create_social_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create social sentiment features."""
        features_df = pd.DataFrame(index=df.index)
        
        if 'sentiment_score' in df.columns:
            features_df['social_sentiment'] = df['sentiment_score']
            features_df['social_sentiment_ma'] = df['sentiment_score'].rolling(7).mean()
            features_df['social_sentiment_volatility'] = df['sentiment_score'].rolling(7).std()
            features_df['social_sentiment_momentum'] = df['sentiment_score'] - df['sentiment_score'].shift(7)
        
        if 'volume' in df.columns:
            features_df['social_volume'] = df['volume']
            features_df['social_volume_ratio'] = df['volume'] / df['volume'].rolling(7).mean()
        
        if 'confidence' in df.columns:
            features_df['social_confidence'] = df['confidence']
        
        return features_df
    
    def _create_onchain_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create on-chain data features."""
        features_df = pd.DataFrame(index=df.index)
        
        if 'exchange_flow_score' in df.columns:
            features_df['exchange_flow'] = df['exchange_flow_score']
            features_df['exchange_flow_ma'] = df['exchange_flow_score'].rolling(7).mean()
        
        if 'whale_activity_score' in df.columns:
            features_df['whale_activity'] = df['whale_activity_score']
            features_df['whale_activity_ma'] = df['whale_activity_score'].rolling(7).mean()
        
        if 'miner_pressure_score' in df.columns:
            features_df['miner_pressure'] = df['miner_pressure_score']
            features_df['miner_pressure_ma'] = df['miner_pressure_score'].rolling(7).mean()
        
        if 'confidence' in df.columns:
            features_df['onchain_confidence'] = df['confidence']
        
        return features_df
    
    def _create_signal_targets(self, df: pd.DataFrame) -> pd.Series:
        """Create signal quality targets based on future price performance."""
        # Calculate future returns for different horizons
        future_returns_1d = df['close'].shift(-1) / df['close'] - 1
        future_returns_3d = df['close'].shift(-3) / df['close'] - 1
        future_returns_7d = df['close'].shift(-7) / df['close'] - 1
        
        # Calculate signal quality based on consistency and magnitude
        signal_quality = pd.Series(index=df.index, dtype=float)
        
        for i in range(len(df)):
            if i >= len(df) - 7:  # Skip last 7 days
                continue
                
            # Get future returns
            ret_1d = future_returns_1d.iloc[i]
            ret_3d = future_returns_3d.iloc[i]
            ret_7d = future_returns_7d.iloc[i]
            
            # Calculate signal quality score
            # Higher score for consistent directional moves
            consistency = 1.0
            if not (ret_1d > 0 and ret_3d > 0 and ret_7d > 0) and not (ret_1d < 0 and ret_3d < 0 and ret_7d < 0):
                consistency = 0.5
            
            # Magnitude factor (higher returns = higher quality)
            magnitude = min(1.0, abs(ret_7d) * 10)  # Scale to 0-1
            
            # Combine factors
            signal_quality.iloc[i] = consistency * magnitude
        
        return signal_quality
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.Series:
        """Calculate MACD indicator."""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        return macd
    
    def _calculate_bollinger_position(self, prices: pd.Series, period: int = 20, std_dev: float = 2) -> pd.Series:
        """Calculate Bollinger Band position."""
        sma = prices.rolling(period).mean()
        std = prices.rolling(period).std()
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        position = (prices - lower) / (upper - lower)
        return position
    
    def _calculate_stochastic(self, df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> pd.Series:
        """Calculate Stochastic oscillator."""
        lowest_low = df['low'].rolling(k_period).min()
        highest_high = df['high'].rolling(k_period).max()
        k_percent = 100 * ((df['close'] - lowest_low) / (highest_high - lowest_low))
        return k_percent
    
    def train_model(
        self, 
        signal_data: SignalData, 
        model_type: str = 'random_forest'
    ) -> SignalModel:
        """
        Train a signal enhancement model.
        
        Args:
            signal_data: Training data
            model_type: Type of model to train
            
        Returns:
            Trained SignalModel
        """
        try:
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                signal_data.features,
                signal_data.targets,
                test_size=self.test_size,
                random_state=self.random_state
            )
            
            # Create model
            if model_type == 'random_forest':
                model = RandomForestRegressor(
                    n_estimators=100,
                    max_depth=10,
                    random_state=self.random_state,
                    n_jobs=-1
                )
            elif model_type == 'gradient_boosting':
                model = GradientBoostingRegressor(
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
                ('regressor', model)
            ])
            
            # Train model
            pipeline.fit(X_train, y_train)
            
            # Evaluate model
            y_pred = pipeline.predict(X_test)
            r2 = r2_score(y_test, y_pred)
            mse = mean_squared_error(y_test, y_pred)
            mae = mean_absolute_error(y_test, y_pred)
            
            # Cross-validation
            cv_scores = cross_val_score(pipeline, signal_data.features, signal_data.targets, cv=self.cv_folds, scoring='r2')
            cv_mean = cv_scores.mean()
            cv_std = cv_scores.std()
            
            self.logger.info(f"Model trained - R²: {r2:.3f}, MSE: {mse:.3f}, MAE: {mae:.3f}, CV: {cv_mean:.3f} ± {cv_std:.3f}")
            
            return SignalModel(
                model=pipeline,
                scaler=scaler,
                feature_names=signal_data.feature_names,
                r2_score=r2,
                mse=mse,
                mae=mae,
                training_date=datetime.now(timezone.utc),
                coin_id=signal_data.coin_id,
                timeframe=signal_data.timeframe,
                model_type=model_type
            )
            
        except Exception as e:
            self.logger.error(f"Model training failed: {e}")
            raise
    
    def save_model(self, model: SignalModel) -> str:
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
                'r2_score': model.r2_score,
                'mse': model.mse,
                'mae': model.mae,
                'training_date': model.training_date.isoformat(),
                'feature_names': model.feature_names,
                'signal_thresholds': self.signal_thresholds
            }
            
            metadata_file = filepath.with_suffix('.json')
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            self.logger.info(f"Model saved to {filepath}")
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"Failed to save model: {e}")
            raise
    
    def load_model(self, filepath: str) -> SignalModel:
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
            'signal_thresholds': self.signal_thresholds,
            'feature_weights': {
                'social_weight': self.social_weight,
                'onchain_weight': self.onchain_weight,
                'technical_weight': self.technical_weight
            }
        }
