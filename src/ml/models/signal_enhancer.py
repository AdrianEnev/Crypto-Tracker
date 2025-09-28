"""
Signal quality assessment and enhancement models.
Filters and enhances signals from existing strategies based on market context.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Union, List, Tuple
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

from .base_model import BaseModel, ModelMetadata


class SignalEnhancer(BaseModel):
    """
    ML model for assessing and enhancing trading signals.
    
    This model evaluates the quality of signals from existing strategies and
    can enhance them by adjusting confidence levels or filtering out low-quality signals.
    """
    
    def __init__(self, 
                 strategy_name: str = "volatility_strategy",
                 enhancement_method: str = "xgboost",
                 enhancement_type: str = "confidence_scoring",
                 version: str = "1.0"):
        super().__init__(
            model_name=f"{strategy_name}_signal_enhancer",
            model_type="signal_enhancer",
            version=version
        )
        
        self.strategy_name = strategy_name
        self.enhancement_method = enhancement_method
        self.enhancement_type = enhancement_type
        self.signal_threshold = 0.5  # Default threshold for signal quality
        self.enhancement_history = []
        
    def _initialize_model(self, **kwargs) -> Any:
        """Initialize the signal enhancement model."""
        if self.enhancement_method == "xgboost":
            return xgb.XGBClassifier(
                n_estimators=kwargs.get('n_estimators', 100),
                max_depth=kwargs.get('max_depth', 6),
                learning_rate=kwargs.get('learning_rate', 0.1),
                subsample=kwargs.get('subsample', 0.8),
                colsample_bytree=kwargs.get('colsample_bytree', 0.8),
                random_state=42
            )
        elif self.enhancement_method == "random_forest":
            return RandomForestClassifier(
                n_estimators=kwargs.get('n_estimators', 100),
                max_depth=kwargs.get('max_depth', 10),
                min_samples_split=kwargs.get('min_samples_split', 5),
                min_samples_leaf=kwargs.get('min_samples_leaf', 2),
                random_state=42
            )
        elif self.enhancement_method == "gradient_boosting":
            return GradientBoostingClassifier(
                n_estimators=kwargs.get('n_estimators', 100),
                max_depth=kwargs.get('max_depth', 6),
                learning_rate=kwargs.get('learning_rate', 0.1),
                subsample=kwargs.get('subsample', 0.8),
                random_state=42
            )
        else:
            raise ValueError(f"Unknown enhancement method: {self.enhancement_method}")
    
    def _train_model(self, 
                    X: pd.DataFrame, 
                    y: Union[pd.Series, pd.DataFrame], 
                    validation_data: Optional[tuple] = None,
                    **kwargs) -> Dict[str, Any]:
        """Train the signal enhancement model."""
        
        # Prepare training data
        if isinstance(y, pd.Series):
            y_train = y.values
        else:
            y_train = y.values.flatten()
        
        X_train = X.values
        
        # Handle validation data
        if validation_data:
            X_val, y_val = validation_data
            X_val = X_val.values
            y_val = y_val.values if isinstance(y_val, pd.Series) else y_val.values.flatten()
            
            # Train with early stopping for XGBoost
            if self.enhancement_method == "xgboost":
                self.model.fit(
                    X_train, y_train,
                    eval_set=[(X_val, y_val)],
                    early_stopping_rounds=kwargs.get('early_stopping_rounds', 10),
                    verbose=False
                )
            else:
                self.model.fit(X_train, y_train)
            
            # Calculate validation metrics
            val_predictions = self.model.predict(X_val)
            val_proba = self.model.predict_proba(X_val)[:, 1]
            
            val_metrics = self._calculate_classification_metrics(y_val, val_predictions, val_proba, prefix='val_')
        else:
            self.model.fit(X_train, y_train)
            val_metrics = {}
        
        # Calculate training metrics
        train_predictions = self.model.predict(X_train)
        train_proba = self.model.predict_proba(X_train)[:, 1]
        
        train_metrics = self._calculate_classification_metrics(y_train, train_predictions, train_proba)
        
        # Cross-validation score
        cv_scores = cross_val_score(self.model, X_train, y_train, cv=TimeSeriesSplit(n_splits=3), scoring='roc_auc')
        
        metrics = {
            **train_metrics,
            **val_metrics,
            'cv_auc_mean': cv_scores.mean(),
            'cv_auc_std': cv_scores.std()
        }
        
        # Get hyperparameters
        hyperparameters = self.model.get_params()
        
        return {
            'metrics': metrics,
            'hyperparameters': hyperparameters,
            'feature_importance': self.get_feature_importance(X)
        }
    
    def _calculate_classification_metrics(self, y_true: np.ndarray, y_pred: np.ndarray, y_proba: np.ndarray, prefix: str = '') -> Dict[str, float]:
        """Calculate classification metrics."""
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
        
        try:
            accuracy = accuracy_score(y_true, y_pred)
            precision = precision_score(y_true, y_pred, zero_division=0)
            recall = recall_score(y_true, y_pred, zero_division=0)
            f1 = f1_score(y_true, y_pred, zero_division=0)
            auc = roc_auc_score(y_true, y_proba)
            
            return {
                f'{prefix}accuracy': accuracy,
                f'{prefix}precision': precision,
                f'{prefix}recall': recall,
                f'{prefix}f1_score': f1,
                f'{prefix}auc': auc
            }
        except Exception as e:
            print(f"Error calculating classification metrics: {e}")
            return {}
    
    def _predict_model(self, X: pd.DataFrame) -> np.ndarray:
        """Make signal quality predictions."""
        return self.model.predict(X.values)
    
    def assess_signal_quality(self, 
                            market_data: pd.DataFrame,
                            signal_data: Dict[str, Any],
                            return_confidence: bool = False) -> Union[float, Tuple[float, float]]:
        """
        Assess the quality of a trading signal.
        
        Args:
            market_data: Current market features
            signal_data: Signal information (action, strength, etc.)
            return_confidence: Whether to return confidence interval
            
        Returns:
            Signal quality score (0-1) or (score, confidence) tuple
        """
        if not self.is_trained:
            raise ValueError("Signal enhancer is not trained yet")
        
        # Combine market data with signal features
        features = self._create_signal_features(market_data, signal_data)
        
        # Make prediction
        prediction = self.predict(features)
        quality_score = prediction[0] if len(prediction) > 0 else 0.5
        
        if return_confidence:
            # Get prediction probability as confidence measure
            proba = self.model.predict_proba(features)[0]
            confidence = max(proba)  # Maximum probability as confidence
            return quality_score, confidence
        
        return quality_score
    
    def enhance_signal(self, 
                      market_data: pd.DataFrame,
                      original_signal: Dict[str, Any],
                      enhancement_level: float = 1.0) -> Dict[str, Any]:
        """
        Enhance a trading signal based on market context.
        
        Args:
            market_data: Current market features
            original_signal: Original signal from strategy
            enhancement_level: Enhancement strength (0-2, where 1 is no change)
            
        Returns:
            Enhanced signal dictionary
        """
        if not self.is_trained:
            # Return original signal if model not trained
            return original_signal
        
        # Assess signal quality
        quality_score, confidence = self.assess_signal_quality(market_data, original_signal, return_confidence=True)
        
        # Create enhanced signal
        enhanced_signal = original_signal.copy()
        
        if self.enhancement_type == "confidence_scoring":
            # Adjust signal strength based on quality
            original_strength = enhanced_signal.get('strength', 1.0)
            quality_multiplier = quality_score * enhancement_level
            enhanced_signal['strength'] = original_strength * quality_multiplier
            enhanced_signal['quality_score'] = quality_score
            enhanced_signal['confidence'] = confidence
            
        elif self.enhancement_type == "filtering":
            # Filter out low-quality signals
            if quality_score < self.signal_threshold:
                enhanced_signal['action'] = 'hold'
                enhanced_signal['strength'] = 0.0
            enhanced_signal['quality_score'] = quality_score
            enhanced_signal['confidence'] = confidence
            
        elif self.enhancement_type == "adaptive_threshold":
            # Adjust thresholds based on market conditions
            market_volatility = market_data.get('volatility_20d', 0.02)
            market_trend = market_data.get('returns_20d', 0.0)
            
            # Adjust signal strength based on market regime
            if market_volatility > 0.05:  # High volatility
                volatility_adjustment = 0.8  # Reduce strength in high volatility
            else:
                volatility_adjustment = 1.2  # Increase strength in low volatility
            
            if abs(market_trend) > 0.02:  # Strong trend
                trend_adjustment = 1.1  # Slight increase for strong trends
            else:
                trend_adjustment = 0.9  # Slight decrease for weak trends
            
            original_strength = enhanced_signal.get('strength', 1.0)
            enhanced_signal['strength'] = original_strength * quality_score * volatility_adjustment * trend_adjustment
            enhanced_signal['quality_score'] = quality_score
            enhanced_signal['confidence'] = confidence
            enhanced_signal['volatility_adjustment'] = volatility_adjustment
            enhanced_signal['trend_adjustment'] = trend_adjustment
        
        # Store enhancement history
        self.enhancement_history.append({
            'timestamp': pd.Timestamp.now(),
            'original_signal': original_signal,
            'enhanced_signal': enhanced_signal,
            'quality_score': quality_score,
            'confidence': confidence
        })
        
        return enhanced_signal
    
    def _create_signal_features(self, market_data: pd.DataFrame, signal_data: Dict[str, Any]) -> pd.DataFrame:
        """Create features combining market data and signal information."""
        
        # Start with market features
        features = market_data.copy()
        
        # Add signal-specific features
        signal_features = {}
        
        # Signal action encoding
        action = signal_data.get('action', 'hold')
        signal_features['signal_action_buy'] = 1 if action == 'buy' else 0
        signal_features['signal_action_sell'] = 1 if action == 'sell' else 0
        signal_features['signal_action_hold'] = 1 if action == 'hold' else 0
        
        # Signal strength
        signal_features['signal_strength'] = signal_data.get('strength', 0.0)
        
        # Market context features
        if 'volatility_20d' in market_data.columns:
            vol = market_data['volatility_20d'].iloc[0] if len(market_data) > 0 else 0.02
            signal_features['signal_strength_vs_volatility'] = signal_features['signal_strength'] / max(vol, 0.001)
        
        if 'returns_20d' in market_data.columns:
            returns = market_data['returns_20d'].iloc[0] if len(market_data) > 0 else 0.0
            signal_features['signal_direction_vs_trend'] = 1 if (action == 'buy' and returns > 0) or (action == 'sell' and returns < 0) else 0
        
        # Technical indicator alignment
        if 'ema_20' in market_data.columns and 'ema_50' in market_data.columns:
            ema_20 = market_data['ema_20'].iloc[0] if len(market_data) > 0 else 0
            ema_50 = market_data['ema_50'].iloc[0] if len(market_data) > 0 else 0
            signal_features['ema_alignment'] = 1 if (action == 'buy' and ema_20 > ema_50) or (action == 'sell' and ema_20 < ema_50) else 0
        
        # Combine all features
        for key, value in signal_features.items():
            features[key] = value
        
        return features
    
    def create_training_data(self, 
                           strategy_instance: Any,
                           market_data: pd.DataFrame,
                           lookforward_periods: int = 5,
                           performance_threshold: float = 0.01) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Create training data for signal quality assessment.
        
        Args:
            strategy_instance: Instance of the strategy to enhance
            market_data: Historical market data
            lookforward_periods: Number of periods to look forward for performance
            performance_threshold: Threshold for classifying signal success
            
        Returns:
            Tuple of (features, targets) for training
        """
        print(f"Creating training data for {self.strategy_name} signal enhancement...")
        
        training_features = []
        training_targets = []
        
        for i in range(lookforward_periods, len(market_data) - lookforward_periods):
            # Get market data for current period
            current_data = market_data.iloc[i:i+1]
            
            # Generate signal
            signal = strategy_instance.generate_signal(current_data)
            
            # Create signal features
            signal_data = {
                'action': signal.action,
                'strength': signal.strength
            }
            features = self._create_signal_features(current_data, signal_data)
            
            # Calculate forward performance
            forward_prices = market_data['close'].iloc[i+1:i+1+lookforward_periods]
            if len(forward_prices) > 0:
                price_change = (forward_prices.iloc[-1] - forward_prices.iloc[0]) / forward_prices.iloc[0]
                
                # Determine if signal was successful
                if signal.action == 'buy' and price_change > performance_threshold:
                    success = 1
                elif signal.action == 'sell' and price_change < -performance_threshold:
                    success = 1
                elif signal.action == 'hold':
                    success = 1  # Hold signals are considered neutral
                else:
                    success = 0
                
                # Handle timestamp columns in features
                feature_row = features.iloc[0]
                if 'timestamp' in feature_row.index:
                    feature_row = feature_row.drop('timestamp')
                training_features.append(feature_row)
                training_targets.append(success)
        
        if not training_features:
            raise ValueError("No valid training data generated")
        
        features_df = pd.DataFrame(training_features)
        targets_series = pd.Series(training_targets, name='signal_success')
        
        print(f"Generated {len(training_features)} training samples")
        print(f"Success rate: {np.mean(training_targets):.2%}")
        
        return features_df, targets_series
    
    def set_signal_threshold(self, threshold: float) -> None:
        """Set the threshold for signal quality filtering."""
        if not 0 <= threshold <= 1:
            raise ValueError("Signal threshold must be between 0 and 1")
        
        self.signal_threshold = threshold
        print(f"Signal quality threshold set to {threshold}")
    
    def get_enhancement_statistics(self) -> Dict[str, Any]:
        """Get statistics about signal enhancements."""
        if not self.enhancement_history:
            return {}
        
        df = pd.DataFrame(self.enhancement_history)
        
        return {
            'total_enhancements': len(self.enhancement_history),
            'avg_quality_score': df['quality_score'].mean(),
            'avg_confidence': df['confidence'].mean(),
            'quality_score_std': df['quality_score'].std(),
            'enhancement_by_action': df.groupby('original_signal')['quality_score'].mean().to_dict()
        }
    
    def analyze_signal_performance(self, 
                                 market_data: pd.DataFrame,
                                 original_signals: List[Dict[str, Any]],
                                 enhanced_signals: List[Dict[str, Any]],
                                 lookforward_periods: int = 5) -> Dict[str, Any]:
        """
        Analyze performance difference between original and enhanced signals.
        
        Args:
            market_data: Market data
            original_signals: List of original signals
            enhanced_signals: List of enhanced signals
            lookforward_periods: Periods to look forward for performance
            
        Returns:
            Performance comparison dictionary
        """
        if len(original_signals) != len(enhanced_signals):
            raise ValueError("Original and enhanced signals must have same length")
        
        original_performance = []
        enhanced_performance = []
        
        for i, (orig_signal, enh_signal) in enumerate(zip(original_signals, enhanced_signals)):
            if i + lookforward_periods >= len(market_data):
                break
            
            # Calculate forward performance
            start_price = market_data.iloc[i]['close']
            end_price = market_data.iloc[i + lookforward_periods]['close']
            price_change = (end_price - start_price) / start_price
            
            # Calculate signal performance
            if orig_signal['action'] == 'buy':
                orig_perf = price_change
            elif orig_signal['action'] == 'sell':
                orig_perf = -price_change
            else:
                orig_perf = 0
            
            if enh_signal['action'] == 'buy':
                enh_perf = price_change * enh_signal.get('strength', 1.0)
            elif enh_signal['action'] == 'sell':
                enh_perf = -price_change * enh_signal.get('strength', 1.0)
            else:
                enh_perf = 0
            
            original_performance.append(orig_perf)
            enhanced_performance.append(enh_perf)
        
        return {
            'original_mean_performance': np.mean(original_performance),
            'enhanced_mean_performance': np.mean(enhanced_performance),
            'performance_improvement': np.mean(enhanced_performance) - np.mean(original_performance),
            'original_win_rate': np.mean(np.array(original_performance) > 0),
            'enhanced_win_rate': np.mean(np.array(enhanced_performance) > 0),
            'original_sharpe': np.mean(original_performance) / max(np.std(original_performance), 0.001),
            'enhanced_sharpe': np.mean(enhanced_performance) / max(np.std(enhanced_performance), 0.001)
        }
