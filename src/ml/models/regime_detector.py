"""
Market regime detection models.
Identifies different market regimes (bull/bear/sideways, volatility regimes, etc.)
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Union, List, Tuple
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler
import hmmlearn.hmm as hmm

from .base_model import BaseModel, ModelMetadata


class RegimeDetector(BaseModel):
    """
    ML model for detecting market regimes.
    
    Uses various techniques to identify market regimes such as:
    - Bull/Bear/Sideways markets
    - High/Low volatility periods
    - Trend/Mean-reversion regimes
    - Crisis/Normal periods
    """
    
    def __init__(self, 
                 regime_type: str = "volatility_regime",
                 detection_method: str = "hmm",
                 n_regimes: int = 3,
                 version: str = "1.0"):
        super().__init__(
            model_name=f"{regime_type}_detector",
            model_type="regime_detector",
            version=version
        )
        
        self.regime_type = regime_type
        self.detection_method = detection_method
        self.n_regimes = n_regimes
        self.regime_labels = {}
        self.regime_transition_matrix = None
        self.scaler = StandardScaler()
        
    def _initialize_model(self, **kwargs) -> Any:
        """Initialize the regime detection model."""
        if self.detection_method == "hmm":
            return hmm.GaussianHMM(
                n_components=self.n_regimes,
                covariance_type=kwargs.get('covariance_type', 'full'),
                n_iter=kwargs.get('n_iter', 100),
                random_state=42
            )
        elif self.detection_method == "kmeans":
            return KMeans(
                n_clusters=self.n_regimes,
                random_state=42,
                n_init=kwargs.get('n_init', 10)
            )
        elif self.detection_method == "gmm":
            return GaussianMixture(
                n_components=self.n_regimes,
                covariance_type=kwargs.get('covariance_type', 'full'),
                random_state=42
            )
        elif self.detection_method == "random_forest":
            return RandomForestClassifier(
                n_estimators=kwargs.get('n_estimators', 100),
                max_depth=kwargs.get('max_depth', 10),
                random_state=42
            )
        elif self.detection_method == "gradient_boosting":
            return GradientBoostingClassifier(
                n_estimators=kwargs.get('n_estimators', 100),
                max_depth=kwargs.get('max_depth', 6),
                learning_rate=kwargs.get('learning_rate', 0.1),
                random_state=42
            )
        else:
            raise ValueError(f"Unknown detection method: {self.detection_method}")
    
    def _train_model(self, 
                    X: pd.DataFrame, 
                    y: Optional[Union[pd.Series, pd.DataFrame]] = None,
                    validation_data: Optional[tuple] = None,
                    **kwargs) -> Dict[str, Any]:
        """Train the regime detection model."""
        
        # Scale features for clustering methods
        if self.detection_method in ["hmm", "kmeans", "gmm"]:
            X_scaled = self.scaler.fit_transform(X.values)
        else:
            X_scaled = X.values
        
        # Train based on method
        if self.detection_method in ["hmm", "kmeans", "gmm"]:
            # Unsupervised methods
            self.model.fit(X_scaled)
            
            # Get regime labels
            if self.detection_method == "hmm":
                regime_states = self.model.predict(X_scaled)
                regime_probs = self.model.predict_proba(X_scaled)
                
                # Calculate transition matrix
                self.regime_transition_matrix = self.model.transmat_
            else:
                regime_states = self.model.predict(X_scaled)
                regime_probs = None
            
            # Create regime labels
            self._create_regime_labels(regime_states, X)
            
            # Calculate metrics
            metrics = self._calculate_clustering_metrics(X_scaled, regime_states)
            
        else:
            # Supervised methods
            if y is None:
                raise ValueError(f"Supervised method {self.detection_method} requires target labels")
            
            y_train = y.values if isinstance(y, pd.Series) else y.values.flatten()
            self.model.fit(X_scaled, y_train)
            
            # Predict on training data
            train_predictions = self.model.predict(X_scaled)
            
            # Calculate classification metrics
            metrics = self._calculate_classification_metrics(y_train, train_predictions)
        
        # Handle validation data
        val_metrics = {}
        if validation_data:
            X_val, y_val = validation_data
            X_val_scaled = self.scaler.transform(X_val.values) if self.detection_method in ["hmm", "kmeans", "gmm"] else X_val.values
            
            if self.detection_method in ["hmm", "kmeans", "gmm"]:
                val_predictions = self.model.predict(X_val_scaled)
                val_metrics = self._calculate_clustering_metrics(X_val_scaled, val_predictions, prefix='val_')
            else:
                y_val_flat = y_val.values if isinstance(y_val, pd.Series) else y_val.values.flatten()
                val_predictions = self.model.predict(X_val_scaled)
                val_metrics = self._calculate_classification_metrics(y_val_flat, val_predictions, prefix='val_')
        
        # Get hyperparameters
        hyperparameters = self.model.get_params()
        
        return {
            'metrics': {**metrics, **val_metrics},
            'hyperparameters': hyperparameters,
            'n_regimes': self.n_regimes,
            'regime_labels': self.regime_labels
        }
    
    def _create_regime_labels(self, regime_states: np.ndarray, X: pd.DataFrame) -> None:
        """Create meaningful labels for regimes based on market characteristics."""
        
        # Calculate market characteristics for each regime
        regime_stats = {}
        
        for regime_id in range(self.n_regimes):
            regime_mask = regime_states == regime_id
            if np.sum(regime_mask) == 0:
                continue
            
            regime_data = X[regime_mask]
            
            # Calculate statistics
            stats = {
                'count': np.sum(regime_mask),
                'percentage': np.sum(regime_mask) / len(regime_states) * 100
            }
            
            # Add regime-specific statistics based on regime type
            if self.regime_type == "volatility_regime":
                if 'volatility_20d' in X.columns:
                    stats['avg_volatility'] = regime_data['volatility_20d'].mean()
                    stats['vol_std'] = regime_data['volatility_20d'].std()
                
                # Label regimes based on volatility
                if stats['avg_volatility'] > X['volatility_20d'].quantile(0.7):
                    regime_name = "high_volatility"
                elif stats['avg_volatility'] < X['volatility_20d'].quantile(0.3):
                    regime_name = "low_volatility"
                else:
                    regime_name = "medium_volatility"
            
            elif self.regime_type == "trend_regime":
                if 'returns_20d' in X.columns:
                    stats['avg_return'] = regime_data['returns_20d'].mean()
                    stats['trend_strength'] = abs(regime_data['returns_20d']).mean()
                
                # Label regimes based on trend
                if stats['avg_return'] > 0.02:
                    regime_name = "strong_bull"
                elif stats['avg_return'] < -0.02:
                    regime_name = "strong_bear"
                elif stats['avg_return'] > 0:
                    regime_name = "weak_bull"
                elif stats['avg_return'] < 0:
                    regime_name = "weak_bear"
                else:
                    regime_name = "sideways"
            
            else:
                regime_name = f"regime_{regime_id}"
            
            self.regime_labels[regime_id] = {
                'name': regime_name,
                'stats': stats
            }
        
        print(f"Regime labels created: {self.regime_labels}")
    
    def _calculate_clustering_metrics(self, X: np.ndarray, labels: np.ndarray, prefix: str = '') -> Dict[str, float]:
        """Calculate clustering quality metrics."""
        from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
        
        try:
            silhouette = silhouette_score(X, labels)
            calinski_harabasz = calinski_harabasz_score(X, labels)
            davies_bouldin = davies_bouldin_score(X, labels)
            
            return {
                f'{prefix}silhouette_score': silhouette,
                f'{prefix}calinski_harabasz_score': calinski_harabasz,
                f'{prefix}davies_bouldin_score': davies_bouldin
            }
        except Exception as e:
            print(f"Error calculating clustering metrics: {e}")
            return {}
    
    def _calculate_classification_metrics(self, y_true: np.ndarray, y_pred: np.ndarray, prefix: str = '') -> Dict[str, float]:
        """Calculate classification metrics."""
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
        
        try:
            accuracy = accuracy_score(y_true, y_pred)
            precision = precision_score(y_true, y_pred, average='weighted', zero_division=0)
            recall = recall_score(y_true, y_pred, average='weighted', zero_division=0)
            f1 = f1_score(y_true, y_pred, average='weighted', zero_division=0)
            
            return {
                f'{prefix}accuracy': accuracy,
                f'{prefix}precision': precision,
                f'{prefix}recall': recall,
                f'{prefix}f1_score': f1
            }
        except Exception as e:
            print(f"Error calculating classification metrics: {e}")
            return {}
    
    def _predict_model(self, X: pd.DataFrame) -> np.ndarray:
        """Make regime predictions."""
        # Scale features if needed
        if self.detection_method in ["hmm", "kmeans", "gmm"]:
            X_scaled = self.scaler.transform(X.values)
        else:
            X_scaled = X.values
        
        return self.model.predict(X_scaled)
    
    def predict_regime(self, 
                      market_data: pd.DataFrame,
                      return_probabilities: bool = False) -> Union[str, Tuple[str, np.ndarray]]:
        """
        Predict the current market regime.
        
        Args:
            market_data: Current market features
            return_probabilities: Whether to return regime probabilities
            
        Returns:
            Regime name or (regime_name, probabilities) tuple
        """
        if not self.is_trained:
            raise ValueError("Regime detector is not trained yet")
        
        # Make prediction
        regime_id = self.predict(market_data)[0]
        
        # Get regime name
        regime_name = self.regime_labels.get(regime_id, {}).get('name', f'regime_{regime_id}')
        
        if return_probabilities:
            # Get regime probabilities if available
            if hasattr(self.model, 'predict_proba'):
                X_scaled = self.scaler.transform(market_data.values) if self.detection_method in ["hmm", "kmeans", "gmm"] else market_data.values
                probabilities = self.model.predict_proba(X_scaled)[0]
            else:
                probabilities = np.zeros(self.n_regimes)
                probabilities[regime_id] = 1.0
            
            return regime_name, probabilities
        
        return regime_name
    
    def get_regime_probabilities(self, market_data: pd.DataFrame) -> Dict[str, float]:
        """
        Get probabilities for all regimes.
        
        Args:
            market_data: Current market features
            
        Returns:
            Dictionary mapping regime names to probabilities
        """
        regime_name, probabilities = self.predict_regime(market_data, return_probabilities=True)
        
        result = {}
        for regime_id in range(self.n_regimes):
            regime_info = self.regime_labels.get(regime_id, {})
            regime_name = regime_info.get('name', f'regime_{regime_id}')
            result[regime_name] = probabilities[regime_id]
        
        return result
    
    def get_regime_transition_probabilities(self) -> pd.DataFrame:
        """Get regime transition probability matrix."""
        if self.regime_transition_matrix is None:
            raise ValueError("Transition matrix not available for this model type")
        
        regime_names = [self.regime_labels.get(i, {}).get('name', f'regime_{i}') 
                       for i in range(self.n_regimes)]
        
        return pd.DataFrame(
            self.regime_transition_matrix,
            index=regime_names,
            columns=regime_names
        )
    
    def get_regime_statistics(self) -> Dict[str, Any]:
        """Get statistics for all detected regimes."""
        return {
            'regime_labels': self.regime_labels,
            'n_regimes': self.n_regimes,
            'regime_type': self.regime_type,
            'detection_method': self.detection_method
        }
    
    def create_regime_labels_from_data(self, 
                                     market_data: pd.DataFrame,
                                     regime_type: str = "volatility_regime") -> pd.Series:
        """
        Create regime labels from market data for supervised learning.
        
        Args:
            market_data: Market data with features
            regime_type: Type of regime to create labels for
            
        Returns:
            Series of regime labels
        """
        labels = pd.Series(index=market_data.index, dtype='object')
        
        if regime_type == "volatility_regime":
            if 'volatility_20d' in market_data.columns:
                vol_data = market_data['volatility_20d']
                labels[vol_data > vol_data.quantile(0.7)] = "high_volatility"
                labels[vol_data < vol_data.quantile(0.3)] = "low_volatility"
                labels[labels.isna()] = "medium_volatility"
            else:
                # Use price volatility as proxy
                returns = market_data['close'].pct_change().rolling(20).std()
                labels[returns > returns.quantile(0.7)] = "high_volatility"
                labels[returns < returns.quantile(0.3)] = "low_volatility"
                labels[labels.isna()] = "medium_volatility"
        
        elif regime_type == "trend_regime":
            if 'returns_20d' in market_data.columns:
                ret_data = market_data['returns_20d']
                labels[ret_data > 0.02] = "strong_bull"
                labels[ret_data < -0.02] = "strong_bear"
                labels[(ret_data > 0) & (ret_data <= 0.02)] = "weak_bull"
                labels[(ret_data < 0) & (ret_data >= -0.02)] = "weak_bear"
                labels[labels.isna()] = "sideways"
            else:
                # Use price trend as proxy
                returns = market_data['close'].pct_change().rolling(20).mean()
                labels[returns > 0.02] = "strong_bull"
                labels[returns < -0.02] = "strong_bear"
                labels[(returns > 0) & (returns <= 0.02)] = "weak_bull"
                labels[(returns < 0) & (returns >= -0.02)] = "weak_bear"
                labels[labels.isna()] = "sideways"
        
        elif regime_type == "crisis_regime":
            # Detect crisis periods based on extreme volatility and returns
            returns = market_data['close'].pct_change()
            volatility = returns.rolling(20).std()
            
            crisis_mask = (abs(returns) > returns.rolling(252).quantile(0.95)) | \
                         (volatility > volatility.rolling(252).quantile(0.95))
            
            labels[crisis_mask] = "crisis"
            labels[~crisis_mask] = "normal"
        
        else:
            raise ValueError(f"Unknown regime type: {regime_type}")
        
        return labels
    
    def analyze_regime_stability(self, market_data: pd.DataFrame, window_size: int = 30) -> Dict[str, Any]:
        """
        Analyze stability of regime detection over time.
        
        Args:
            market_data: Market data
            window_size: Window size for rolling analysis
            
        Returns:
            Dictionary with stability metrics
        """
        if not self.is_trained:
            raise ValueError("Regime detector is not trained yet")
        
        # Get regime predictions for all data
        regimes = []
        for i in range(window_size, len(market_data)):
            period_data = market_data.iloc[i-window_size:i]
            regime = self.predict_regime(period_data)
            regimes.append(regime)
        
        # Calculate stability metrics
        regime_changes = sum(1 for i in range(1, len(regimes)) if regimes[i] != regimes[i-1])
        stability_ratio = 1 - (regime_changes / len(regimes))
        
        # Calculate regime durations
        regime_durations = []
        current_regime = regimes[0]
        duration = 1
        
        for i in range(1, len(regimes)):
            if regimes[i] == current_regime:
                duration += 1
            else:
                regime_durations.append(duration)
                current_regime = regimes[i]
                duration = 1
        regime_durations.append(duration)
        
        return {
            'stability_ratio': stability_ratio,
            'regime_changes': regime_changes,
            'avg_regime_duration': np.mean(regime_durations),
            'max_regime_duration': np.max(regime_durations),
            'min_regime_duration': np.min(regime_durations),
            'regime_frequencies': pd.Series(regimes).value_counts().to_dict()
        }
