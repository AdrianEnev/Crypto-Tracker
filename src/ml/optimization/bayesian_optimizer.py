"""
Bayesian Optimization for hyperparameter tuning.
Implements Gaussian Process-based optimization with various acquisition functions.
"""

import time
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AcquisitionFunction(Enum):
    """Available acquisition functions for Bayesian optimization."""
    EXPECTED_IMPROVEMENT = "expected_improvement"
    UPPER_CONFIDENCE_BOUND = "upper_confidence_bound"
    PROBABILITY_IMPROVEMENT = "probability_improvement"
    ENTROPY_SEARCH = "entropy_search"


@dataclass
class GaussianProcess:
    """Simple Gaussian Process implementation for Bayesian optimization."""
    
    def __init__(self, kernel='rbf', alpha=1e-6):
        self.kernel = kernel
        self.alpha = alpha
        self.X_train = None
        self.y_train = None
        self.K = None
        self.K_inv = None
        self.is_fitted = False
    
    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """Fit the Gaussian Process."""
        self.X_train = X.copy()
        self.y_train = y.copy()
        
        # Compute kernel matrix
        self.K = self._compute_kernel(self.X_train, self.X_train)
        self.K += self.alpha * np.eye(len(self.X_train))
        
        # Compute inverse (using pseudo-inverse for numerical stability)
        try:
            self.K_inv = np.linalg.inv(self.K)
        except np.linalg.LinAlgError:
            self.K_inv = np.linalg.pinv(self.K)
        
        self.is_fitted = True
    
    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Predict mean and variance."""
        if not self.is_fitted:
            raise ValueError("GP must be fitted before prediction")
        
        # Compute kernel between test and training points
        K_star = self._compute_kernel(X, self.X_train)
        K_star_star = self._compute_kernel(X, X)
        
        # Mean prediction
        mu = K_star @ self.K_inv @ self.y_train
        
        # Variance prediction
        var = np.diag(K_star_star - K_star @ self.K_inv @ K_star.T)
        var = np.maximum(var, 0)  # Ensure non-negative variance
        
        return mu, var
    
    def _compute_kernel(self, X1: np.ndarray, X2: np.ndarray) -> np.ndarray:
        """Compute RBF kernel matrix."""
        # Simple RBF kernel
        if X1.ndim == 1:
            X1 = X1.reshape(-1, 1)
        if X2.ndim == 1:
            X2 = X2.reshape(-1, 1)
        
        # Pairwise squared distances
        dists = np.sum(X1**2, axis=1)[:, np.newaxis] + np.sum(X2**2, axis=1) - 2 * X1 @ X2.T
        
        # RBF kernel with length scale = 1
        return np.exp(-0.5 * dists)


class BayesianOptimizer:
    """
    Bayesian optimization using Gaussian Processes.
    """
    
    def __init__(self, config):
        self.config = config
        self.gp = GaussianProcess()
        self.X_history = []
        self.y_history = []
        self.trial_history = []
        self.best_score = float('-inf') if config.direction == 'maximize' else float('inf')
        self.best_params = None
        self.best_trial = -1
        self.start_time = None
        
    def optimize(self, objective_function: Callable[[Dict[str, Any]], float]) -> Any:
        """Run Bayesian optimization."""
        logger.info(f"Starting Bayesian optimization with {self.config.n_trials} trials")
        
        self.start_time = datetime.now(timezone.utc)
        
        # Random initialization
        n_init = min(5, self.config.n_trials // 4)
        logger.info(f"Random initialization with {n_init} trials")
        
        for trial in range(n_init):
            if self.config.timeout_seconds:
                elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds()
                if elapsed > self.config.timeout_seconds:
                    break
            
            params = self._random_sample()
            score = self._evaluate_trial(params, objective_function, trial)
            
            if self._check_early_stopping(trial):
                break
        
        # Bayesian optimization
        for trial in range(n_init, self.config.n_trials):
            if self.config.timeout_seconds:
                elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds()
                if elapsed > self.config.timeout_seconds:
                    break
            
            # Fit GP on current data
            if len(self.X_history) >= 2:
                self.gp.fit(np.array(self.X_history), np.array(self.y_history))
                
                # Find next point using acquisition function
                params = self._acquisition_optimize()
            else:
                # Fallback to random sampling
                params = self._random_sample()
            
            # Evaluate trial
            score = self._evaluate_trial(params, objective_function, trial)
            
            if self._check_early_stopping(trial):
                break
        
        return self._create_result()
    
    def _random_sample(self) -> Dict[str, Any]:
        """Sample random parameters."""
        params = {}
        
        for param_name, param_config in self.config.parameter_space.items():
            if isinstance(param_config, dict):
                param_type = param_config.get('type', 'uniform')
                
                if param_type == 'uniform':
                    low = param_config['low']
                    high = param_config['high']
                    params[param_name] = np.random.uniform(low, high)
                    
                elif param_type == 'loguniform':
                    low = param_config['low']
                    high = param_config['high']
                    params[param_name] = np.exp(np.random.uniform(np.log(low), np.log(high)))
                    
                elif param_type == 'int':
                    low = param_config['low']
                    high = param_config['high']
                    params[param_name] = np.random.randint(low, high + 1)
                    
                elif param_type == 'categorical':
                    choices = param_config['choices']
                    params[param_name] = np.random.choice(choices)
                    
                elif param_type == 'discrete':
                    choices = param_config['choices']
                    params[param_name] = np.random.choice(choices)
                    
            else:
                params[param_name] = np.random.choice(param_config)
        
        return params
    
    def _params_to_vector(self, params: Dict[str, Any]) -> np.ndarray:
        """Convert parameters to numerical vector."""
        vector = []
        param_names = sorted(params.keys())
        
        for param_name in param_names:
            value = params[param_name]
            
            if isinstance(value, str):
                # Handle categorical parameters
                param_config = self.config.parameter_space[param_name]
                if isinstance(param_config, dict):
                    choices = param_config['choices']
                    vector.append(choices.index(value))
                else:
                    vector.append(param_config.index(value))
            else:
                vector.append(float(value))
        
        return np.array(vector)
    
    def _vector_to_params(self, vector: np.ndarray) -> Dict[str, Any]:
        """Convert numerical vector to parameters."""
        params = {}
        param_names = sorted(self.config.parameter_space.keys())
        
        for i, param_name in enumerate(param_names):
            param_config = self.config.parameter_space[param_name]
            value = vector[i]
            
            if isinstance(param_config, dict):
                param_type = param_config.get('type', 'uniform')
                
                if param_type in ['categorical', 'discrete']:
                    choices = param_config['choices']
                    idx = int(round(value))
                    idx = max(0, min(idx, len(choices) - 1))
                    params[param_name] = choices[idx]
                elif param_type == 'int':
                    low = param_config['low']
                    high = param_config['high']
                    params[param_name] = int(round(np.clip(value, low, high)))
                else:
                    params[param_name] = value
            else:
                idx = int(round(value))
                idx = max(0, min(idx, len(param_config) - 1))
                params[param_name] = param_config[idx]
        
        return params
    
    def _acquisition_optimize(self) -> Dict[str, Any]:
        """Optimize acquisition function to find next point."""
        from scipy.optimize import minimize
        
        def acquisition_objective(x):
            try:
                # Convert vector to parameters
                params = self._vector_to_params(x)
                
                # Get GP prediction
                mu, var = self.gp.predict(x.reshape(1, -1))
                mu, var = mu[0], var[0]
                std = np.sqrt(var + 1e-9)
                
                # Compute acquisition function
                if self.config.acquisition_function == AcquisitionFunction.EXPECTED_IMPROVEMENT.value:
                    return -self._expected_improvement(mu, std)
                elif self.config.acquisition_function == AcquisitionFunction.UPPER_CONFIDENCE_BOUND.value:
                    return -self._upper_confidence_bound(mu, std)
                elif self.config.acquisition_function == AcquisitionFunction.PROBABILITY_IMPROVEMENT.value:
                    return -self._probability_improvement(mu, std)
                else:
                    return -self._expected_improvement(mu, std)
                    
            except Exception as e:
                logger.warning(f"Error in acquisition optimization: {e}")
                return float('inf')
        
        # Bounds for optimization
        bounds = []
        param_names = sorted(self.config.parameter_space.keys())
        
        for param_name in param_names:
            param_config = self.config.parameter_space[param_name]
            
            if isinstance(param_config, dict):
                param_type = param_config.get('type', 'uniform')
                
                if param_type in ['categorical', 'discrete']:
                    choices = param_config['choices']
                    bounds.append((0, len(choices) - 1))
                elif param_type == 'int':
                    low = param_config['low']
                    high = param_config['high']
                    bounds.append((low, high))
                else:
                    low = param_config['low']
                    high = param_config['high']
                    bounds.append((low, high))
            else:
                bounds.append((0, len(param_config) - 1))
        
        # Random restarts for global optimization
        best_x = None
        best_acq = float('inf')
        
        for _ in range(10):  # 10 random restarts
            x0 = []
            for low, high in bounds:
                x0.append(np.random.uniform(low, high))
            x0 = np.array(x0)
            
            try:
                result = minimize(acquisition_objective, x0, bounds=bounds, method='L-BFGS-B')
                
                if result.fun < best_acq:
                    best_acq = result.fun
                    best_x = result.x
                    
            except Exception as e:
                logger.warning(f"Optimization restart failed: {e}")
                continue
        
        if best_x is None:
            # Fallback to random sampling
            return self._random_sample()
        
        return self._vector_to_params(best_x)
    
    def _expected_improvement(self, mu: float, std: float) -> float:
        """Compute Expected Improvement acquisition function."""
        if std <= 0:
            return 0.0
        
        if self.config.direction == 'maximize':
            best = max(self.y_history) if self.y_history else 0
            improvement = mu - best
        else:
            best = min(self.y_history) if self.y_history else 0
            improvement = best - mu
        
        z = improvement / std
        ei = improvement * self._normal_cdf(z) + std * self._normal_pdf(z)
        
        return ei
    
    def _upper_confidence_bound(self, mu: float, std: float) -> float:
        """Compute Upper Confidence Bound acquisition function."""
        beta = self.config.exploration_weight
        return mu + beta * std
    
    def _probability_improvement(self, mu: float, std: float) -> float:
        """Compute Probability of Improvement acquisition function."""
        if std <= 0:
            return 0.0
        
        if self.config.direction == 'maximize':
            best = max(self.y_history) if self.y_history else 0
            z = (mu - best) / std
        else:
            best = min(self.y_history) if self.y_history else 0
            z = (best - mu) / std
        
        return self._normal_cdf(z)
    
    def _normal_cdf(self, x: float) -> float:
        """Normal cumulative distribution function."""
        return 0.5 * (1 + np.sign(x) * np.sqrt(1 - np.exp(-2 * x**2 / np.pi)))
    
    def _normal_pdf(self, x: float) -> float:
        """Normal probability density function."""
        return np.exp(-0.5 * x**2) / np.sqrt(2 * np.pi)
    
    def _evaluate_trial(self, params: Dict[str, Any], objective_function: Callable, trial: int) -> float:
        """Evaluate a single trial."""
        try:
            start_time = time.time()
            score = objective_function(params)
            evaluation_time = time.time() - start_time
            
            # Store trial history
            trial_data = {
                'trial_number': trial,
                'params': params.copy(),
                'score': score,
                'evaluation_time': evaluation_time,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            self.trial_history.append(trial_data)
            
            # Store for GP
            x_vector = self._params_to_vector(params)
            self.X_history.append(x_vector)
            self.y_history.append(score)
            
            # Update best score
            is_better = (
                (self.config.direction == 'maximize' and score > self.best_score) or
                (self.config.direction == 'minimize' and score < self.best_score)
            )
            
            if is_better:
                self.best_score = score
                self.best_params = params.copy()
                self.best_trial = trial
                
                logger.info(f"Trial {trial}: New best score {score:.4f} with params {params}")
            
            return score
            
        except Exception as e:
            logger.error(f"Error in trial {trial}: {e}")
            return float('-inf') if self.config.direction == 'maximize' else float('inf')
    
    def _check_early_stopping(self, trial: int) -> bool:
        """Check if early stopping should be triggered."""
        if self.config.early_stopping_rounds is None:
            return False
        
        if len(self.trial_history) < self.config.early_stopping_rounds:
            return False
        
        recent_trials = self.trial_history[-self.config.early_stopping_rounds:]
        recent_scores = [trial['score'] for trial in recent_trials]
        
        if self.config.direction == 'maximize':
            return max(recent_scores) <= self.best_score
        else:
            return min(recent_scores) >= self.best_score
    
    def _create_result(self):
        """Create optimization result."""
        from .hyperparameter_optimizer import OptimizationResult
        
        optimization_time = (
            datetime.now(timezone.utc) - self.start_time
        ).total_seconds() if self.start_time else 0.0
        
        convergence_data = [
            (trial['trial_number'], trial['score']) 
            for trial in self.trial_history
        ]
        
        return OptimizationResult(
            best_params=self.best_params or {},
            best_score=self.best_score,
            best_trial=self.best_trial,
            n_trials=len(self.trial_history),
            optimization_time=optimization_time,
            optimization_algorithm='bayesian',
            objective_metric=self.config.objective_metric,
            trial_history=self.trial_history.copy(),
            convergence_data=convergence_data
        )
