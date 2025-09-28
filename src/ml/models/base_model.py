"""
Base model interface for ML trading models.
Provides common interface and functionality for all ML models.
"""

import pickle
import joblib
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union, List
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from dataclasses import dataclass, field


@dataclass
class ModelMetadata:
    """Metadata for ML models."""
    model_name: str
    model_type: str
    version: str
    created_at: datetime
    last_trained: datetime
    training_data_shape: tuple
    feature_names: List[str]
    target_names: List[str]
    hyperparameters: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    training_samples: int = 0
    validation_samples: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            'model_name': self.model_name,
            'model_type': self.model_type,
            'version': self.version,
            'created_at': self.created_at.isoformat(),
            'last_trained': self.last_trained.isoformat(),
            'training_data_shape': self.training_data_shape,
            'feature_names': self.feature_names,
            'target_names': self.target_names,
            'hyperparameters': self.hyperparameters,
            'performance_metrics': self.performance_metrics,
            'training_samples': self.training_samples,
            'validation_samples': self.validation_samples
        }


class BaseModel(ABC):
    """
    Base class for all ML trading models.
    
    Provides common interface and functionality for:
    - Model training and validation
    - Prediction and inference
    - Model persistence and loading
    - Performance monitoring
    """
    
    def __init__(self, model_name: str, model_type: str, version: str = "1.0"):
        self.model_name = model_name
        self.model_type = model_type
        self.version = version
        self.model = None
        self.is_trained = False
        self.feature_names = []
        self.target_names = []
        
        # Metadata
        self.metadata = ModelMetadata(
            model_name=model_name,
            model_type=model_type,
            version=version,
            created_at=datetime.now(timezone.utc),
            last_trained=datetime.now(timezone.utc),
            training_data_shape=(0, 0),
            feature_names=[],
            target_names=[]
        )
        
        # Performance tracking
        self.training_history = []
        self.prediction_history = []
    
    @abstractmethod
    def _initialize_model(self, **kwargs) -> Any:
        """Initialize the underlying ML model."""
        pass
    
    @abstractmethod
    def _train_model(self, X: pd.DataFrame, y: Union[pd.Series, pd.DataFrame], **kwargs) -> Dict[str, Any]:
        """Train the model with given data."""
        pass
    
    @abstractmethod
    def _predict_model(self, X: pd.DataFrame) -> Union[np.ndarray, pd.DataFrame]:
        """Make predictions using the trained model."""
        pass
    
    def train(self, 
              X: pd.DataFrame, 
              y: Union[pd.Series, pd.DataFrame], 
              validation_data: Optional[tuple] = None,
              **kwargs) -> Dict[str, Any]:
        """
        Train the model with given features and targets.
        
        Args:
            X: Feature matrix
            y: Target values
            validation_data: Optional validation data tuple (X_val, y_val)
            **kwargs: Additional training parameters
            
        Returns:
            Training results dictionary
        """
        print(f"Training {self.model_name}...")
        
        # Initialize model if not already done
        if self.model is None:
            self.model = self._initialize_model(**kwargs)
        
        # Store feature and target names
        self.feature_names = list(X.columns)
        if y is not None:
            self.target_names = list(y.columns) if isinstance(y, pd.DataFrame) else [y.name or 'target']
        else:
            self.target_names = []  # Unsupervised learning
        
        # Update metadata
        self.metadata.training_data_shape = X.shape
        self.metadata.feature_names = self.feature_names
        self.metadata.target_names = self.target_names
        self.metadata.training_samples = len(X)
        
        if validation_data:
            X_val, y_val = validation_data
            self.metadata.validation_samples = len(X_val)
        
        # Train the model
        start_time = datetime.now(timezone.utc)
        training_results = self._train_model(X, y, validation_data=validation_data, **kwargs)
        end_time = datetime.now(timezone.utc)
        
        # Update metadata
        self.metadata.last_trained = end_time
        self.metadata.performance_metrics = training_results.get('metrics', {})
        self.metadata.hyperparameters = training_results.get('hyperparameters', {})
        
        # Store training history
        training_record = {
            'timestamp': end_time,
            'training_samples': len(X),
            'validation_samples': len(validation_data[0]) if validation_data else 0,
            'training_time_seconds': (end_time - start_time).total_seconds(),
            'metrics': training_results.get('metrics', {}),
            'hyperparameters': training_results.get('hyperparameters', {})
        }
        self.training_history.append(training_record)
        
        self.is_trained = True
        
        print(f"Training completed. Metrics: {training_results.get('metrics', {})}")
        
        return training_results
    
    def predict(self, X: pd.DataFrame, return_confidence: bool = False) -> Union[np.ndarray, pd.DataFrame, tuple]:
        """
        Make predictions using the trained model.
        
        Args:
            X: Feature matrix
            return_confidence: Whether to return confidence scores
            
        Returns:
            Predictions and optionally confidence scores
        """
        if not self.is_trained:
            raise ValueError(f"Model {self.model_name} is not trained yet")
        
        if list(X.columns) != self.feature_names:
            raise ValueError(f"Feature names mismatch. Expected {self.feature_names}, got {list(X.columns)}")
        
        # Make predictions
        predictions = self._predict_model(X)
        
        # Store prediction history
        prediction_record = {
            'timestamp': datetime.now(timezone.utc),
            'samples': len(X),
            'feature_names': self.feature_names
        }
        self.prediction_history.append(prediction_record)
        
        # Calculate confidence if requested
        if return_confidence:
            confidence = self._calculate_confidence(X, predictions)
            return predictions, confidence
        
        return predictions
    
    def _calculate_confidence(self, X: pd.DataFrame, predictions: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """Calculate prediction confidence scores."""
        # Default implementation - can be overridden by subclasses
        # For now, return uniform confidence scores
        if isinstance(predictions, pd.DataFrame):
            return np.full(len(predictions), 0.8)  # 80% confidence
        else:
            return np.full(len(predictions), 0.8)
    
    def evaluate(self, X: pd.DataFrame, y: Union[pd.Series, pd.DataFrame]) -> Dict[str, float]:
        """
        Evaluate model performance on given data.
        
        Args:
            X: Feature matrix
            y: True target values
            
        Returns:
            Performance metrics dictionary
        """
        if not self.is_trained:
            raise ValueError(f"Model {self.model_name} is not trained yet")
        
        predictions = self.predict(X)
        
        # Calculate metrics based on prediction type
        if isinstance(predictions, pd.DataFrame):
            # Multi-output regression
            metrics = {}
            for i, target_name in enumerate(self.target_names):
                if i < predictions.shape[1]:
                    target_pred = predictions.iloc[:, i]
                    target_true = y.iloc[:, i] if isinstance(y, pd.DataFrame) else y
                    
                    metrics[f'{target_name}_mse'] = np.mean((target_pred - target_true) ** 2)
                    metrics[f'{target_name}_mae'] = np.mean(np.abs(target_pred - target_true))
                    metrics[f'{target_name}_r2'] = 1 - np.sum((target_true - target_pred) ** 2) / np.sum((target_true - np.mean(target_true)) ** 2)
        else:
            # Single output
            metrics = {
                'mse': np.mean((predictions - y) ** 2),
                'mae': np.mean(np.abs(predictions - y)),
                'r2': 1 - np.sum((y - predictions) ** 2) / np.sum((y - np.mean(y)) ** 2)
            }
        
        return metrics
    
    def save_model(self, filepath: str) -> None:
        """Save the trained model to disk."""
        if not self.is_trained:
            raise ValueError(f"Model {self.model_name} is not trained yet")
        
        model_data = {
            'model': self.model,
            'metadata': self.metadata,
            'training_history': self.training_history,
            'prediction_history': self.prediction_history
        }
        
        joblib.dump(model_data, filepath)
        print(f"Model saved to {filepath}")
    
    def load_model(self, filepath: str) -> None:
        """Load a trained model from disk."""
        model_data = joblib.load(filepath)
        
        self.model = model_data['model']
        self.metadata = model_data['metadata']
        self.training_history = model_data.get('training_history', [])
        self.prediction_history = model_data.get('prediction_history', [])
        
        self.is_trained = True
        self.feature_names = self.metadata.feature_names
        self.target_names = self.metadata.target_names
        
        print(f"Model loaded from {filepath}")
    
    def get_feature_importance(self, X: pd.DataFrame) -> Dict[str, float]:
        """Get feature importance scores if available."""
        if not self.is_trained:
            raise ValueError(f"Model {self.model_name} is not trained yet")
        
        # Default implementation - can be overridden by subclasses
        if hasattr(self.model, 'feature_importances_'):
            importance_scores = self.model.feature_importances_
            return dict(zip(self.feature_names, importance_scores))
        elif hasattr(self.model, 'coef_'):
            # For linear models
            coef = self.model.coef_
            if coef.ndim > 1:
                # Multi-output model
                importance_scores = np.mean(np.abs(coef), axis=0)
            else:
                importance_scores = np.abs(coef)
            return dict(zip(self.feature_names, importance_scores))
        else:
            # Return uniform importance if not available
            uniform_importance = 1.0 / len(self.feature_names)
            return {feature: uniform_importance for feature in self.feature_names}
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get comprehensive model information."""
        return {
            'model_name': self.model_name,
            'model_type': self.model_type,
            'version': self.version,
            'is_trained': self.is_trained,
            'feature_names': self.feature_names,
            'target_names': self.target_names,
            'metadata': self.metadata.to_dict(),
            'training_history_count': len(self.training_history),
            'prediction_history_count': len(self.prediction_history)
        }
    
    def reset_model(self) -> None:
        """Reset the model to untrained state."""
        self.model = None
        self.is_trained = False
        self.feature_names = []
        self.target_names = []
        self.training_history = []
        self.prediction_history = []
        
        # Reset metadata
        self.metadata = ModelMetadata(
            model_name=self.model_name,
            model_type=self.model_type,
            version=self.version,
            created_at=datetime.now(timezone.utc),
            last_trained=datetime.now(timezone.utc),
            training_data_shape=(0, 0),
            feature_names=[],
            target_names=[]
        )
        
        print(f"Model {self.model_name} reset to untrained state")
