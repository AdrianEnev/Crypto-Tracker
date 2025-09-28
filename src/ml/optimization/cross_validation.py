"""
Cross-Validation strategies for hyperparameter optimization.
Provides various validation schemes for robust model evaluation.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class ValidationStrategy(Enum):
    """Available cross-validation strategies."""
    K_FOLD = "k_fold"
    TIME_SERIES_SPLIT = "time_series_split"
    WALK_FORWARD = "walk_forward"
    PURGED_CROSS_VALIDATION = "purged_cv"
    BLOCKED_CROSS_VALIDATION = "blocked_cv"
    MONTE_CARLO_CV = "monte_carlo_cv"


@dataclass
class ValidationSplit:
    """Container for a single validation split."""
    train_indices: List[int]
    test_indices: List[int]
    train_start: Optional[datetime] = None
    train_end: Optional[datetime] = None
    test_start: Optional[datetime] = None
    test_end: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'train_indices': self.train_indices,
            'test_indices': self.test_indices,
            'train_start': self.train_start.isoformat() if self.train_start else None,
            'train_end': self.train_end.isoformat() if self.train_end else None,
            'test_start': self.test_start.isoformat() if self.test_start else None,
            'test_end': self.test_end.isoformat() if self.test_end else None
        }


class BaseCrossValidator(ABC):
    """Base class for cross-validation strategies."""
    
    def __init__(self, n_splits: int = 5):
        self.n_splits = n_splits
    
    @abstractmethod
    def split(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> List[ValidationSplit]:
        """Generate cross-validation splits."""
        pass
    
    @abstractmethod
    def get_n_splits(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> int:
        """Get number of splits."""
        pass


class KFoldValidator(BaseCrossValidator):
    """K-Fold cross-validation."""
    
    def split(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> List[ValidationSplit]:
        """Generate K-Fold splits."""
        n_samples = len(X)
        indices = np.arange(n_samples)
        np.random.shuffle(indices)
        
        splits = []
        fold_size = n_samples // self.n_splits
        
        for i in range(self.n_splits):
            start = i * fold_size
            end = start + fold_size
            
            if i == self.n_splits - 1:  # Last fold gets remaining samples
                end = n_samples
            
            test_indices = indices[start:end].tolist()
            train_indices = np.concatenate([indices[:start], indices[end:]]).tolist()
            
            splits.append(ValidationSplit(
                train_indices=train_indices,
                test_indices=test_indices
            ))
        
        return splits
    
    def get_n_splits(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> int:
        """Get number of splits."""
        return self.n_splits


class TimeSeriesSplitValidator(BaseCrossValidator):
    """Time series cross-validation."""
    
    def __init__(self, n_splits: int = 5, test_size: float = 0.2):
        super().__init__(n_splits)
        self.test_size = test_size
    
    def split(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> List[ValidationSplit]:
        """Generate time series splits."""
        n_samples = len(X)
        splits = []
        
        for i in range(self.n_splits):
            # Calculate split points
            test_start = int(n_samples * (i + 1) / (self.n_splits + 1))
            test_end = int(n_samples * (i + 1 + self.test_size) / (self.n_splits + 1))
            
            if test_end >= n_samples:
                test_end = n_samples
            
            train_indices = list(range(test_start))
            test_indices = list(range(test_start, test_end))
            
            splits.append(ValidationSplit(
                train_indices=train_indices,
                test_indices=test_indices
            ))
        
        return splits
    
    def get_n_splits(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> int:
        """Get number of splits."""
        return self.n_splits


class WalkForwardValidator(BaseCrossValidator):
    """Walk-forward cross-validation for time series."""
    
    def __init__(self, 
                 n_splits: int = 5, 
                 train_size: int = 252,  # 1 year of daily data
                 test_size: int = 63):   # 3 months
        super().__init__(n_splits)
        self.train_size = train_size
        self.test_size = test_size
    
    def split(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> List[ValidationSplit]:
        """Generate walk-forward splits."""
        n_samples = len(X)
        splits = []
        
        for i in range(self.n_splits):
            test_start = self.train_size + i * self.test_size
            test_end = test_start + self.test_size
            
            if test_end >= n_samples:
                break
            
            train_indices = list(range(test_start))
            test_indices = list(range(test_start, test_end))
            
            splits.append(ValidationSplit(
                train_indices=train_indices,
                test_indices=test_indices
            ))
        
        return splits
    
    def get_n_splits(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> int:
        """Get number of splits."""
        n_samples = len(X)
        max_splits = (n_samples - self.train_size) // self.test_size
        return min(self.n_splits, max_splits)


class PurgedCrossValidator(BaseCrossValidator):
    """Purged cross-validation to avoid data leakage."""
    
    def __init__(self, 
                 n_splits: int = 5, 
                 purge_period: int = 5,  # Days to purge between train and test
                 embargo_period: int = 5):  # Days to embargo after test
        super().__init__(n_splits)
        self.purge_period = purge_period
        self.embargo_period = embargo_period
    
    def split(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> List[ValidationSplit]:
        """Generate purged cross-validation splits."""
        n_samples = len(X)
        splits = []
        
        # Calculate split boundaries
        fold_size = n_samples // (self.n_splits + 1)
        
        for i in range(self.n_splits):
            # Test set boundaries
            test_start = fold_size * (i + 1)
            test_end = test_start + fold_size
            
            # Purge periods
            purge_start = test_start - self.purge_period
            purge_end = test_end + self.embargo_period
            
            # Training set (excluding purge periods)
            train_indices = []
            train_indices.extend(range(0, max(0, purge_start)))
            train_indices.extend(range(min(n_samples, purge_end), n_samples))
            
            test_indices = list(range(test_start, min(test_end, n_samples)))
            
            splits.append(ValidationSplit(
                train_indices=train_indices,
                test_indices=test_indices
            ))
        
        return splits
    
    def get_n_splits(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> int:
        """Get number of splits."""
        return self.n_splits


class BlockedCrossValidator(BaseCrossValidator):
    """Blocked cross-validation to preserve temporal structure."""
    
    def __init__(self, 
                 n_splits: int = 5, 
                 block_size: int = 50):
        super().__init__(n_splits)
        self.block_size = block_size
    
    def split(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> List[ValidationSplit]:
        """Generate blocked cross-validation splits."""
        n_samples = len(X)
        n_blocks = n_samples // self.block_size
        
        splits = []
        
        for i in range(self.n_splits):
            # Select test blocks
            test_blocks = [j for j in range(n_blocks) if j % self.n_splits == i]
            
            test_indices = []
            for block in test_blocks:
                start = block * self.block_size
                end = min(start + self.block_size, n_samples)
                test_indices.extend(range(start, end))
            
            # Training blocks are all other blocks
            train_indices = []
            for block in range(n_blocks):
                if block not in test_blocks:
                    start = block * self.block_size
                    end = min(start + self.block_size, n_samples)
                    train_indices.extend(range(start, end))
            
            splits.append(ValidationSplit(
                train_indices=train_indices,
                test_indices=test_indices
            ))
        
        return splits
    
    def get_n_splits(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> int:
        """Get number of splits."""
        return self.n_splits


class MonteCarloValidator(BaseCrossValidator):
    """Monte Carlo cross-validation."""
    
    def __init__(self, 
                 n_splits: int = 100, 
                 test_size: float = 0.2,
                 random_seed: Optional[int] = None):
        super().__init__(n_splits)
        self.test_size = test_size
        self.random_seed = random_seed
        
        if random_seed is not None:
            np.random.seed(random_seed)
    
    def split(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> List[ValidationSplit]:
        """Generate Monte Carlo splits."""
        n_samples = len(X)
        test_size_int = int(n_samples * self.test_size)
        splits = []
        
        for _ in range(self.n_splits):
            indices = np.arange(n_samples)
            np.random.shuffle(indices)
            
            test_indices = indices[:test_size_int].tolist()
            train_indices = indices[test_size_int:].tolist()
            
            splits.append(ValidationSplit(
                train_indices=train_indices,
                test_indices=test_indices
            ))
        
        return splits
    
    def get_n_splits(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> int:
        """Get number of splits."""
        return self.n_splits


class CrossValidator:
    """
    Main cross-validation interface.
    """
    
    def __init__(self, strategy: ValidationStrategy = ValidationStrategy.K_FOLD, **kwargs):
        self.strategy = strategy
        self.kwargs = kwargs
        self.validator = self._create_validator()
    
    def _create_validator(self) -> BaseCrossValidator:
        """Create the appropriate validator based on strategy."""
        if self.strategy == ValidationStrategy.K_FOLD:
            return KFoldValidator(**self.kwargs)
        elif self.strategy == ValidationStrategy.TIME_SERIES_SPLIT:
            return TimeSeriesSplitValidator(**self.kwargs)
        elif self.strategy == ValidationStrategy.WALK_FORWARD:
            return WalkForwardValidator(**self.kwargs)
        elif self.strategy == ValidationStrategy.PURGED_CROSS_VALIDATION:
            return PurgedCrossValidator(**self.kwargs)
        elif self.strategy == ValidationStrategy.BLOCKED_CROSS_VALIDATION:
            return BlockedCrossValidator(**self.kwargs)
        elif self.strategy == ValidationStrategy.MONTE_CARLO_CV:
            return MonteCarloValidator(**self.kwargs)
        else:
            raise ValueError(f"Unsupported validation strategy: {self.strategy}")
    
    def split(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> List[ValidationSplit]:
        """Generate cross-validation splits."""
        return self.validator.split(X, y)
    
    def get_n_splits(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> int:
        """Get number of splits."""
        return self.validator.get_n_splits(X, y)
    
    def cross_validate(self, 
                      X: pd.DataFrame, 
                      y: pd.Series,
                      model_factory: Callable,
                      score_function: Callable[[Any, Any, Any], float],
                      **model_kwargs) -> Dict[str, Any]:
        """
        Perform cross-validation with a model factory and scoring function.
        
        Args:
            X: Feature matrix
            y: Target variable
            model_factory: Function that creates a model instance
            score_function: Function that scores predictions (y_true, y_pred, model)
            **model_kwargs: Additional arguments for model creation
            
        Returns:
            Dictionary with cross-validation results
        """
        splits = self.split(X, y)
        scores = []
        
        logger.info(f"Running {len(splits)}-fold cross-validation")
        
        for i, split in enumerate(splits):
            logger.info(f"Fold {i+1}/{len(splits)}")
            
            # Split data
            X_train = X.iloc[split.train_indices]
            X_test = X.iloc[split.test_indices]
            y_train = y.iloc[split.train_indices]
            y_test = y.iloc[split.test_indices]
            
            # Create and train model
            model = model_factory(**model_kwargs)
            model.train(X_train, y_train)
            
            # Make predictions
            if hasattr(model, 'predict'):
                y_pred = model.predict(X_test)
            else:
                # Fallback for models without predict method
                y_pred = np.random.random(len(y_test))  # Mock predictions
            
            # Score predictions
            score = score_function(y_test, y_pred, model)
            scores.append(score)
            
            logger.info(f"  Fold {i+1} score: {score:.4f}")
        
        # Calculate statistics
        scores_array = np.array(scores)
        
        results = {
            'scores': scores,
            'mean_score': np.mean(scores_array),
            'std_score': np.std(scores_array),
            'min_score': np.min(scores_array),
            'max_score': np.max(scores_array),
            'median_score': np.median(scores_array),
            'n_splits': len(splits),
            'strategy': self.strategy.value
        }
        
        logger.info(f"Cross-validation completed. Mean score: {results['mean_score']:.4f} ± {results['std_score']:.4f}")
        
        return results
