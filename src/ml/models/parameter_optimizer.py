"""
Parameter optimization models for trading strategies.
Dynamically optimizes strategy parameters based on market conditions.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Union, List, Tuple
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.metrics import mean_squared_error, mean_absolute_error
import xgboost as xgb

from .base_model import BaseModel, ModelMetadata


class ParameterOptimizer(BaseModel):
    """
    ML model for optimizing trading strategy parameters.
    
    This model learns the relationship between market conditions and optimal
    strategy parameters, allowing for dynamic parameter adjustment.
    """
    
    def __init__(self, 
                 strategy_name: str = "volatility_strategy",
                 optimization_method: str = "xgboost",
                 version: str = "1.0"):
        super().__init__(
            model_name=f"{strategy_name}_parameter_optimizer",
            model_type="parameter_optimizer",
            version=version
        )
        
        self.strategy_name = strategy_name
        self.optimization_method = optimization_method
        self.parameter_ranges = {}
        self.baseline_parameters = {}
        
    def _initialize_model(self, **kwargs) -> Any:
        """Initialize the parameter optimization model."""
        if self.optimization_method == "xgboost":
            return xgb.XGBRegressor(
                n_estimators=kwargs.get('n_estimators', 100),
                max_depth=kwargs.get('max_depth', 6),
                learning_rate=kwargs.get('learning_rate', 0.1),
                subsample=kwargs.get('subsample', 0.8),
                colsample_bytree=kwargs.get('colsample_bytree', 0.8),
                random_state=42
            )
        elif self.optimization_method == "random_forest":
            return RandomForestRegressor(
                n_estimators=kwargs.get('n_estimators', 100),
                max_depth=kwargs.get('max_depth', 10),
                min_samples_split=kwargs.get('min_samples_split', 5),
                min_samples_leaf=kwargs.get('min_samples_leaf', 2),
                random_state=42
            )
        elif self.optimization_method == "gradient_boosting":
            return GradientBoostingRegressor(
                n_estimators=kwargs.get('n_estimators', 100),
                max_depth=kwargs.get('max_depth', 6),
                learning_rate=kwargs.get('learning_rate', 0.1),
                subsample=kwargs.get('subsample', 0.8),
                random_state=42
            )
        else:
            raise ValueError(f"Unknown optimization method: {self.optimization_method}")
    
    def set_parameter_ranges(self, parameter_ranges: Dict[str, Tuple[float, float]]) -> None:
        """
        Set the parameter ranges for optimization.
        
        Args:
            parameter_ranges: Dictionary mapping parameter names to (min, max) tuples
        """
        self.parameter_ranges = parameter_ranges
        print(f"Parameter ranges set for {self.strategy_name}: {parameter_ranges}")
    
    def set_baseline_parameters(self, baseline_parameters: Dict[str, float]) -> None:
        """
        Set baseline parameters for the strategy.
        
        Args:
            baseline_parameters: Dictionary mapping parameter names to default values
        """
        self.baseline_parameters = baseline_parameters
        print(f"Baseline parameters set for {self.strategy_name}: {baseline_parameters}")
    
    def _train_model(self, 
                    X: pd.DataFrame, 
                    y: Union[pd.Series, pd.DataFrame], 
                    validation_data: Optional[tuple] = None,
                    **kwargs) -> Dict[str, Any]:
        """Train the parameter optimization model."""
        
        # Prepare training data
        if isinstance(y, pd.Series):
            y_train = y.values
        else:
            y_train = y.values
        
        X_train = X.values
        
        # Handle validation data
        if validation_data:
            X_val, y_val = validation_data
            X_val = X_val.values
            y_val = y_val.values if isinstance(y_val, pd.Series) else y_val.values
            
            # Train with early stopping for XGBoost
            if self.optimization_method == "xgboost":
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
            val_mse = mean_squared_error(y_val, val_predictions)
            val_mae = mean_absolute_error(y_val, val_predictions)
            
            val_metrics = {
                'val_mse': val_mse,
                'val_mae': val_mae,
                'val_rmse': np.sqrt(val_mse)
            }
        else:
            self.model.fit(X_train, y_train)
            val_metrics = {}
        
        # Calculate training metrics
        train_predictions = self.model.predict(X_train)
        train_mse = mean_squared_error(y_train, train_predictions)
        train_mae = mean_absolute_error(y_train, train_predictions)
        
        # Cross-validation score
        cv_scores = cross_val_score(self.model, X_train, y_train, cv=TimeSeriesSplit(n_splits=3), scoring='neg_mean_squared_error')
        cv_rmse = np.sqrt(-cv_scores.mean())
        
        metrics = {
            'train_mse': train_mse,
            'train_mae': train_mae,
            'train_rmse': np.sqrt(train_mse),
            'cv_rmse': cv_rmse,
            **val_metrics
        }
        
        # Get hyperparameters
        hyperparameters = self.model.get_params()
        
        return {
            'metrics': metrics,
            'hyperparameters': hyperparameters,
            'feature_importance': self.get_feature_importance(X)
        }
    
    def _predict_model(self, X: pd.DataFrame) -> np.ndarray:
        """Make parameter predictions."""
        return self.model.predict(X.values)
    
    def optimize_parameters(self, 
                          market_data: pd.DataFrame, 
                          parameter_names: List[str],
                          return_confidence: bool = False) -> Dict[str, Union[float, Tuple[float, float]]]:
        """
        Optimize parameters for given market conditions.
        
        Args:
            market_data: Current market features
            parameter_names: List of parameter names to optimize
            return_confidence: Whether to return confidence intervals
            
        Returns:
            Dictionary mapping parameter names to optimized values
        """
        if not self.is_trained:
            raise ValueError("Parameter optimizer is not trained yet")
        
        # Make predictions
        predictions = self.predict(market_data, return_confidence=return_confidence)
        
        if return_confidence:
            predictions, confidence = predictions
        else:
            confidence = None
        
        # Map predictions to parameter names
        optimized_parameters = {}
        
        for i, param_name in enumerate(parameter_names):
            if i < len(predictions):
                param_value = predictions[i]
                
                # Ensure parameter is within valid range
                if param_name in self.parameter_ranges:
                    min_val, max_val = self.parameter_ranges[param_name]
                    param_value = np.clip(param_value, min_val, max_val)
                
                if return_confidence and confidence is not None:
                    # Add confidence interval (simplified)
                    conf_interval = confidence[i] * 0.1  # 10% of confidence as interval
                    optimized_parameters[param_name] = (param_value, conf_interval)
                else:
                    optimized_parameters[param_name] = param_value
            else:
                # Use baseline parameter if no prediction available
                optimized_parameters[param_name] = self.baseline_parameters.get(param_name, 0.0)
        
        return optimized_parameters
    
    def create_training_data(self, 
                           strategy_instance: Any,
                           market_data: pd.DataFrame,
                           performance_metric: str = "sharpe_ratio",
                           lookback_periods: int = 30) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Create training data for parameter optimization.
        
        Args:
            strategy_instance: Instance of the strategy to optimize
            market_data: Historical market data
            performance_metric: Metric to optimize for
            lookback_periods: Number of periods to look back for performance
            
        Returns:
            Tuple of (features, targets) for training
        """
        print(f"Creating training data for {self.strategy_name} parameter optimization...")
        
        training_features = []
        training_targets = []
        
        # Generate parameter combinations within ranges
        param_combinations = self._generate_parameter_combinations()
        
        for param_combo in param_combinations:
            # Set parameters for strategy
            strategy_instance.update_parameters(param_combo)
            
            # Calculate performance for each time period
            for i in range(lookback_periods, len(market_data)):
                # Get market features for this period
                period_features = market_data.iloc[i-lookback_periods:i].copy()
                
                # Calculate performance with these parameters
                performance = self._calculate_strategy_performance(
                    strategy_instance, period_features, performance_metric
                )
                
                if performance is not None:
                    # Use average features but handle timestamp columns
                    avg_features = period_features.mean()
                    # Remove timestamp columns if present
                    if 'timestamp' in avg_features.index:
                        avg_features = avg_features.drop('timestamp')
                    training_features.append(avg_features)
                    training_targets.append(performance)
        
        if not training_features:
            raise ValueError("No valid training data generated")
        
        features_df = pd.DataFrame(training_features)
        targets_df = pd.DataFrame(training_targets, columns=[performance_metric])
        
        print(f"Generated {len(training_features)} training samples")
        
        return features_df, targets_df
    
    def _generate_parameter_combinations(self, n_samples: int = 100) -> List[Dict[str, float]]:
        """Generate parameter combinations for training."""
        if not self.parameter_ranges:
            return []
        
        param_names = list(self.parameter_ranges.keys())
        param_combinations = []
        
        for _ in range(n_samples):
            param_combo = {}
            for param_name in param_names:
                min_val, max_val = self.parameter_ranges[param_name]
                param_combo[param_name] = np.random.uniform(min_val, max_val)
            param_combinations.append(param_combo)
        
        return param_combinations
    
    def _calculate_strategy_performance(self, 
                                      strategy_instance: Any,
                                      market_data: pd.DataFrame,
                                      metric: str) -> Optional[float]:
        """
        Calculate strategy performance for given parameters.
        
        Args:
            strategy_instance: Strategy instance with current parameters
            market_data: Market data for the period
            metric: Performance metric to calculate
            
        Returns:
            Performance value or None if calculation fails
        """
        try:
            # Generate signals for the period
            signals = []
            returns = []
            
            for i in range(len(market_data)):
                signal = strategy_instance.generate_signal(market_data.iloc[i:i+1])
                signals.append(signal)
                
                # Calculate returns (simplified)
                if i > 0:
                    price_change = (market_data.iloc[i]['close'] - market_data.iloc[i-1]['close']) / market_data.iloc[i-1]['close']
                    if signal.action == 'buy':
                        returns.append(price_change)
                    elif signal.action == 'sell':
                        returns.append(-price_change)
                    else:
                        returns.append(0)
            
            if not returns:
                return None
            
            # Calculate performance metric
            if metric == "sharpe_ratio":
                if np.std(returns) == 0:
                    return 0
                return np.mean(returns) / np.std(returns) * np.sqrt(252)  # Annualized
            
            elif metric == "total_return":
                return np.sum(returns)
            
            elif metric == "win_rate":
                return np.mean(np.array(returns) > 0)
            
            elif metric == "max_drawdown":
                cumulative_returns = np.cumsum(returns)
                running_max = np.maximum.accumulate(cumulative_returns)
                drawdown = (cumulative_returns - running_max) / running_max
                return np.min(drawdown)
            
            else:
                return np.mean(returns)
                
        except Exception as e:
            print(f"Error calculating performance: {e}")
            return None
    
    def get_parameter_sensitivity(self, 
                                market_data: pd.DataFrame,
                                parameter_name: str,
                                values: List[float]) -> Dict[float, float]:
        """
        Analyze sensitivity of a parameter to performance.
        
        Args:
            market_data: Market features
            parameter_name: Name of parameter to analyze
            values: List of parameter values to test
            
        Returns:
            Dictionary mapping parameter values to predicted performance
        """
        if not self.is_trained:
            raise ValueError("Parameter optimizer is not trained yet")
        
        sensitivity_results = {}
        
        for value in values:
            # Create modified market data with this parameter value
            modified_data = market_data.copy()
            modified_data[parameter_name] = value
            
            # Predict performance
            prediction = self.predict(modified_data)
            sensitivity_results[value] = prediction[0] if len(prediction) > 0 else 0
        
        return sensitivity_results
    
    def get_optimal_parameters_for_regime(self, 
                                        market_data: pd.DataFrame,
                                        regime: str,
                                        parameter_names: List[str]) -> Dict[str, float]:
        """
        Get optimal parameters for a specific market regime.
        
        Args:
            market_data: Market features
            regime: Market regime identifier
            parameter_names: List of parameter names
            
        Returns:
            Dictionary of optimal parameters for the regime
        """
        # Add regime information to market data
        regime_data = market_data.copy()
        regime_data['market_regime'] = regime
        
        return self.optimize_parameters(regime_data, parameter_names)
