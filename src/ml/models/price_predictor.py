"""
Price prediction models for short-term price direction and magnitude.
Uses time series and alternative data for price forecasting.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Union, List, Tuple
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

from .base_model import BaseModel, ModelMetadata


class PricePredictor(BaseModel):
    """
    ML model for predicting price movements.
    
    Predicts both price direction and magnitude for short-term forecasting.
    Can be used to enhance existing strategies or provide standalone predictions.
    """
    
    def __init__(self, 
                 prediction_horizon: int = 1,
                 prediction_type: str = "direction_magnitude",
                 model_method: str = "xgboost",
                 version: str = "1.0"):
        super().__init__(
            model_name=f"price_predictor_{prediction_horizon}period",
            model_type="price_predictor",
            version=version
        )
        
        self.prediction_horizon = prediction_horizon
        self.prediction_type = prediction_type
        self.model_method = model_method
        self.scaler = StandardScaler()
        self.price_history = []
        
    def _initialize_model(self, **kwargs) -> Any:
        """Initialize the price prediction model."""
        if self.model_method == "xgboost":
            return xgb.XGBRegressor(
                n_estimators=kwargs.get('n_estimators', 100),
                max_depth=kwargs.get('max_depth', 6),
                learning_rate=kwargs.get('learning_rate', 0.1),
                subsample=kwargs.get('subsample', 0.8),
                colsample_bytree=kwargs.get('colsample_bytree', 0.8),
                random_state=42
            )
        elif self.model_method == "random_forest":
            return RandomForestRegressor(
                n_estimators=kwargs.get('n_estimators', 100),
                max_depth=kwargs.get('max_depth', 10),
                min_samples_split=kwargs.get('min_samples_split', 5),
                min_samples_leaf=kwargs.get('min_samples_leaf', 2),
                random_state=42
            )
        elif self.model_method == "gradient_boosting":
            return GradientBoostingRegressor(
                n_estimators=kwargs.get('n_estimators', 100),
                max_depth=kwargs.get('max_depth', 6),
                learning_rate=kwargs.get('learning_rate', 0.1),
                subsample=kwargs.get('subsample', 0.8),
                random_state=42
            )
        else:
            raise ValueError(f"Unknown model method: {self.model_method}")
    
    def _train_model(self, 
                    X: pd.DataFrame, 
                    y: Union[pd.Series, pd.DataFrame], 
                    validation_data: Optional[tuple] = None,
                    **kwargs) -> Dict[str, Any]:
        """Train the price prediction model."""
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X.values)
        
        # Prepare targets
        if isinstance(y, pd.Series):
            y_train = y.values
        else:
            y_train = y.values
        
        # Handle validation data
        if validation_data:
            X_val, y_val = validation_data
            X_val_scaled = self.scaler.transform(X_val.values)
            y_val = y_val.values if isinstance(y_val, pd.Series) else y_val.values
            
            # Train with early stopping for XGBoost
            if self.model_method == "xgboost":
                self.model.fit(
                    X_scaled, y_train,
                    eval_set=[(X_val_scaled, y_val)],
                    early_stopping_rounds=kwargs.get('early_stopping_rounds', 10),
                    verbose=False
                )
            else:
                self.model.fit(X_scaled, y_train)
            
            # Calculate validation metrics
            val_predictions = self.model.predict(X_val_scaled)
            val_metrics = self._calculate_regression_metrics(y_val, val_predictions, prefix='val_')
        else:
            self.model.fit(X_scaled, y_train)
            val_metrics = {}
        
        # Calculate training metrics
        train_predictions = self.model.predict(X_scaled)
        train_metrics = self._calculate_regression_metrics(y_train, train_predictions)
        
        # Cross-validation score
        cv_scores = cross_val_score(self.model, X_scaled, y_train, cv=TimeSeriesSplit(n_splits=3), scoring='neg_mean_squared_error')
        
        metrics = {
            **train_metrics,
            **val_metrics,
            'cv_rmse_mean': np.sqrt(-cv_scores.mean()),
            'cv_rmse_std': cv_scores.std()
        }
        
        # Get hyperparameters
        hyperparameters = self.model.get_params()
        
        return {
            'metrics': metrics,
            'hyperparameters': hyperparameters,
            'feature_importance': self.get_feature_importance(X)
        }
    
    def _calculate_regression_metrics(self, y_true: np.ndarray, y_pred: np.ndarray, prefix: str = '') -> Dict[str, float]:
        """Calculate regression metrics."""
        try:
            mse = mean_squared_error(y_true, y_pred)
            mae = mean_absolute_error(y_true, y_pred)
            r2 = r2_score(y_true, y_pred)
            
            return {
                f'{prefix}mse': mse,
                f'{prefix}mae': mae,
                f'{prefix}rmse': np.sqrt(mse),
                f'{prefix}r2': r2
            }
        except Exception as e:
            print(f"Error calculating regression metrics: {e}")
            return {}
    
    def _predict_model(self, X: pd.DataFrame) -> np.ndarray:
        """Make price predictions."""
        X_scaled = self.scaler.transform(X.values)
        return self.model.predict(X_scaled)
    
    def predict_price_movement(self, 
                             market_data: pd.DataFrame,
                             current_price: float,
                             return_confidence: bool = False) -> Union[Dict[str, float], Tuple[Dict[str, float], float]]:
        """
        Predict price movement for the next period(s).
        
        Args:
            market_data: Current market features
            current_price: Current price level
            return_confidence: Whether to return confidence score
            
        Returns:
            Dictionary with prediction results or (results, confidence) tuple
        """
        if not self.is_trained:
            raise ValueError("Price predictor is not trained yet")
        
        # Make prediction
        prediction = self.predict(market_data)[0]
        
        # Interpret prediction based on type
        if self.prediction_type == "direction_magnitude":
            # Prediction represents expected return
            expected_return = prediction
            predicted_price = current_price * (1 + expected_return)
            
            results = {
                'expected_return': expected_return,
                'predicted_price': predicted_price,
                'price_change': predicted_price - current_price,
                'direction': 'up' if expected_return > 0 else 'down',
                'magnitude': abs(expected_return)
            }
            
        elif self.prediction_type == "price_level":
            # Prediction represents price level
            predicted_price = prediction
            
            results = {
                'predicted_price': predicted_price,
                'expected_return': (predicted_price - current_price) / current_price,
                'price_change': predicted_price - current_price,
                'direction': 'up' if predicted_price > current_price else 'down',
                'magnitude': abs((predicted_price - current_price) / current_price)
            }
            
        elif self.prediction_type == "volatility_adjusted":
            # Prediction with volatility adjustment
            volatility = market_data.get('volatility_20d', 0.02).iloc[0] if len(market_data) > 0 else 0.02
            expected_return = prediction * volatility  # Scale by volatility
            predicted_price = current_price * (1 + expected_return)
            
            results = {
                'expected_return': expected_return,
                'predicted_price': predicted_price,
                'price_change': predicted_price - current_price,
                'direction': 'up' if expected_return > 0 else 'down',
                'magnitude': abs(expected_return),
                'volatility_adjustment': volatility
            }
        
        if return_confidence:
            # Calculate confidence based on feature importance and prediction magnitude
            confidence = self._calculate_prediction_confidence(market_data, results)
            return results, confidence
        
        return results
    
    def _calculate_prediction_confidence(self, market_data: pd.DataFrame, results: Dict[str, float]) -> float:
        """Calculate confidence score for prediction."""
        # Base confidence on prediction magnitude and market conditions
        magnitude = results.get('magnitude', 0)
        
        # Higher confidence for moderate predictions (not too extreme)
        if 0.01 <= magnitude <= 0.05:  # 1-5% movement
            magnitude_confidence = 0.8
        elif 0.005 <= magnitude <= 0.1:  # 0.5-10% movement
            magnitude_confidence = 0.6
        else:
            magnitude_confidence = 0.4
        
        # Adjust based on market volatility
        if 'volatility_20d' in market_data.columns:
            volatility = market_data['volatility_20d'].iloc[0] if len(market_data) > 0 else 0.02
            if volatility < 0.03:  # Low volatility
                volatility_confidence = 0.9
            elif volatility < 0.07:  # Medium volatility
                volatility_confidence = 0.7
            else:  # High volatility
                volatility_confidence = 0.5
        else:
            volatility_confidence = 0.7
        
        # Combine confidence factors
        confidence = (magnitude_confidence + volatility_confidence) / 2
        
        return min(max(confidence, 0.1), 0.95)  # Clamp between 0.1 and 0.95
    
    def create_training_data(self, 
                           market_data: pd.DataFrame,
                           price_column: str = 'close',
                           target_type: str = "returns") -> Tuple[pd.DataFrame, pd.Series]:
        """
        Create training data for price prediction.
        
        Args:
            market_data: Historical market data with features
            price_column: Column name for price data
            target_type: Type of target ('returns', 'price_level', 'volatility_adjusted')
            
        Returns:
            Tuple of (features, targets) for training
        """
        print(f"Creating training data for price prediction (horizon: {self.prediction_horizon})...")
        
        if price_column not in market_data.columns:
            raise ValueError(f"Price column '{price_column}' not found in market data")
        
        # Prepare features (exclude price columns and targets)
        feature_columns = [col for col in market_data.columns 
                          if col not in ['close', 'open', 'high', 'low', 'volume', 'timestamp']]
        
        features_list = []
        targets_list = []
        
        for i in range(len(market_data) - self.prediction_horizon):
            # Features for current period
            current_features = market_data.iloc[i][feature_columns]
            features_list.append(current_features)
            
            # Target: price movement in future period
            current_price = market_data.iloc[i][price_column]
            future_price = market_data.iloc[i + self.prediction_horizon][price_column]
            
            if target_type == "returns":
                target = (future_price - current_price) / current_price
            elif target_type == "price_level":
                target = future_price
            elif target_type == "volatility_adjusted":
                # Normalize by current volatility
                if 'volatility_20d' in market_data.columns:
                    volatility = market_data.iloc[i]['volatility_20d']
                    raw_return = (future_price - current_price) / current_price
                    target = raw_return / max(volatility, 0.001)
                else:
                    target = (future_price - current_price) / current_price
            else:
                raise ValueError(f"Unknown target type: {target_type}")
            
            targets_list.append(target)
        
        if not features_list:
            raise ValueError("No valid training data generated")
        
        features_df = pd.DataFrame(features_list)
        targets_series = pd.Series(targets_list, name=f'{target_type}_{self.prediction_horizon}period')
        
        print(f"Generated {len(features_list)} training samples")
        print(f"Target statistics: mean={targets_series.mean():.4f}, std={targets_series.std():.4f}")
        
        return features_df, targets_series
    
    def predict_signals(self, 
                       market_data: pd.DataFrame,
                       current_price: float,
                       signal_threshold: float = 0.01,
                       strength_multiplier: float = 1.0) -> Dict[str, Any]:
        """
        Generate trading signals based on price predictions.
        
        Args:
            market_data: Current market features
            current_price: Current price level
            signal_threshold: Minimum expected return for signal generation
            strength_multiplier: Multiplier for signal strength
            
        Returns:
            Trading signal dictionary
        """
        prediction, confidence = self.predict_price_movement(market_data, current_price, return_confidence=True)
        
        expected_return = prediction['expected_return']
        magnitude = prediction['magnitude']
        
        # Generate signal based on prediction
        if magnitude < signal_threshold:
            action = 'hold'
            strength = 0.0
        elif expected_return > 0:
            action = 'buy'
            strength = min(magnitude * strength_multiplier * confidence, 1.0)
        else:
            action = 'sell'
            strength = min(magnitude * strength_multiplier * confidence, 1.0)
        
        return {
            'action': action,
            'strength': strength,
            'expected_return': expected_return,
            'predicted_price': prediction['predicted_price'],
            'confidence': confidence,
            'magnitude': magnitude,
            'prediction_horizon': self.prediction_horizon
        }
    
    def get_prediction_accuracy(self, 
                              market_data: pd.DataFrame,
                              actual_prices: pd.Series,
                              start_index: int = 0) -> Dict[str, float]:
        """
        Calculate prediction accuracy on historical data.
        
        Args:
            market_data: Market data with features
            actual_prices: Actual price series
            start_index: Starting index for evaluation
            
        Returns:
            Dictionary with accuracy metrics
        """
        if not self.is_trained:
            raise ValueError("Price predictor is not trained yet")
        
        predictions = []
        actuals = []
        
        for i in range(start_index, len(market_data) - self.prediction_horizon):
            # Get features for prediction
            features = market_data.iloc[i:i+1]
            
            # Make prediction
            prediction_result = self.predict_price_movement(features, actual_prices.iloc[i])
            predicted_price = prediction_result['predicted_price']
            
            # Get actual price
            actual_price = actual_prices.iloc[i + self.prediction_horizon]
            
            predictions.append(predicted_price)
            actuals.append(actual_price)
        
        if not predictions:
            return {}
        
        predictions = np.array(predictions)
        actuals = np.array(actuals)
        
        # Calculate accuracy metrics
        mse = mean_squared_error(actuals, predictions)
        mae = mean_absolute_error(actuals, predictions)
        r2 = r2_score(actuals, predictions)
        
        # Direction accuracy
        pred_direction = np.sign(predictions - actual_prices.iloc[start_index:start_index+len(predictions)].values)
        actual_direction = np.sign(actuals - actual_prices.iloc[start_index:start_index+len(actuals)].values)
        direction_accuracy = np.mean(pred_direction == actual_direction)
        
        return {
            'mse': mse,
            'mae': mae,
            'rmse': np.sqrt(mse),
            'r2': r2,
            'direction_accuracy': direction_accuracy,
            'mean_absolute_percentage_error': np.mean(np.abs((actuals - predictions) / actuals)) * 100
        }
    
    def update_price_history(self, price: float) -> None:
        """Update internal price history for adaptive predictions."""
        self.price_history.append(price)
        
        # Keep only recent history (e.g., last 1000 prices)
        if len(self.price_history) > 1000:
            self.price_history = self.price_history[-1000:]
    
    def get_price_trend_analysis(self, market_data: pd.DataFrame, current_price: float) -> Dict[str, Any]:
        """
        Analyze price trends and provide context for predictions.
        
        Args:
            market_data: Current market features
            current_price: Current price level
            
        Returns:
            Dictionary with trend analysis
        """
        trend_analysis = {
            'current_price': current_price,
            'prediction_horizon': self.prediction_horizon
        }
        
        # Short-term trend (if price history available)
        if len(self.price_history) >= 5:
            recent_prices = self.price_history[-5:]
            short_trend = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
            trend_analysis['short_term_trend'] = short_trend
            trend_analysis['trend_direction'] = 'up' if short_trend > 0 else 'down'
        
        # Volatility analysis
        if 'volatility_20d' in market_data.columns:
            volatility = market_data['volatility_20d'].iloc[0] if len(market_data) > 0 else 0.02
            trend_analysis['current_volatility'] = volatility
            
            if volatility > 0.05:
                trend_analysis['volatility_regime'] = 'high'
            elif volatility < 0.02:
                trend_analysis['volatility_regime'] = 'low'
            else:
                trend_analysis['volatility_regime'] = 'medium'
        
        # Technical indicators alignment
        if 'ema_20' in market_data.columns and 'ema_50' in market_data.columns:
            ema_20 = market_data['ema_20'].iloc[0] if len(market_data) > 0 else current_price
            ema_50 = market_data['ema_50'].iloc[0] if len(market_data) > 0 else current_price
            
            trend_analysis['ema_alignment'] = 'bullish' if ema_20 > ema_50 else 'bearish'
            trend_analysis['price_vs_ema20'] = (current_price - ema_20) / ema_20
            trend_analysis['price_vs_ema50'] = (current_price - ema_50) / ema_50
        
        return trend_analysis
