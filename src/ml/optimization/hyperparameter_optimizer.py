"""
Hyperparameter Optimization for ML trading models.
Provides automated hyperparameter tuning using various optimization strategies.
"""

import time
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class OptimizationConfig:
    """Configuration for hyperparameter optimization."""
    model_type: str
    parameter_space: Dict[str, Any]
    objective_metric: str = 'sharpe_ratio'
    optimization_algorithm: str = 'bayesian'  # 'bayesian', 'random', 'grid', 'genetic'
    n_trials: int = 100
    n_jobs: int = 1
    cv_folds: int = 5
    timeout_seconds: Optional[int] = None
    early_stopping_rounds: Optional[int] = None
    direction: str = 'maximize'  # 'maximize' or 'minimize'
    random_seed: Optional[int] = None
    study_name: Optional[str] = None
    
    # Bayesian optimization specific
    acquisition_function: str = 'expected_improvement'
    exploration_weight: float = 0.1
    
    # Advanced options
    pruning_enabled: bool = True
    warm_start: bool = False
    warm_start_trials: int = 10


@dataclass
class OptimizationResult:
    """Result of hyperparameter optimization."""
    best_params: Dict[str, Any]
    best_score: float
    best_trial: int
    n_trials: int
    optimization_time: float
    optimization_algorithm: str
    objective_metric: str
    trial_history: List[Dict[str, Any]] = field(default_factory=list)
    convergence_data: List[Tuple[int, float]] = field(default_factory=list)
    parameter_importance: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'best_params': self.best_params,
            'best_score': self.best_score,
            'best_trial': self.best_trial,
            'n_trials': self.n_trials,
            'optimization_time': self.optimization_time,
            'optimization_algorithm': self.optimization_algorithm,
            'objective_metric': self.objective_metric,
            'trial_history': self.trial_history,
            'convergence_data': self.convergence_data,
            'parameter_importance': self.parameter_importance
        }


class BaseOptimizer(ABC):
    """Base class for hyperparameter optimizers."""
    
    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.trial_history: List[Dict[str, Any]] = []
        self.start_time: Optional[datetime] = None
        self.best_score: float = float('-inf') if config.direction == 'maximize' else float('inf')
        self.best_params: Optional[Dict[str, Any]] = None
        self.best_trial: int = -1
        
    @abstractmethod
    def optimize(self, objective_function: Callable[[Dict[str, Any]], float]) -> OptimizationResult:
        """Run hyperparameter optimization."""
        pass
    
    def _evaluate_trial(self, 
                       params: Dict[str, Any], 
                       objective_function: Callable[[Dict[str, Any]], float],
                       trial_number: int) -> float:
        """Evaluate a single trial."""
        try:
            start_time = time.time()
            score = objective_function(params)
            evaluation_time = time.time() - start_time
            
            # Store trial history
            trial_data = {
                'trial_number': trial_number,
                'params': params.copy(),
                'score': score,
                'evaluation_time': evaluation_time,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            self.trial_history.append(trial_data)
            
            # Update best score
            is_better = (
                (self.config.direction == 'maximize' and score > self.best_score) or
                (self.config.direction == 'minimize' and score < self.best_score)
            )
            
            if is_better:
                self.best_score = score
                self.best_params = params.copy()
                self.best_trial = trial_number
                
                logger.info(f"Trial {trial_number}: New best score {score:.4f} with params {params}")
            
            return score
            
        except Exception as e:
            logger.error(f"Error in trial {trial_number}: {e}")
            # Return worst possible score
            return float('-inf') if self.config.direction == 'maximize' else float('inf')
    
    def _check_early_stopping(self, trial_number: int) -> bool:
        """Check if early stopping should be triggered."""
        if self.config.early_stopping_rounds is None:
            return False
        
        if len(self.trial_history) < self.config.early_stopping_rounds:
            return False
        
        # Check if best score hasn't improved in recent trials
        recent_trials = self.trial_history[-self.config.early_stopping_rounds:]
        recent_scores = [trial['score'] for trial in recent_trials]
        
        if self.config.direction == 'maximize':
            return max(recent_scores) <= self.best_score
        else:
            return min(recent_scores) >= self.best_score


class RandomOptimizer(BaseOptimizer):
    """Random search hyperparameter optimizer."""
    
    def optimize(self, objective_function: Callable[[Dict[str, Any]], float]) -> OptimizationResult:
        """Run random search optimization."""
        logger.info(f"Starting random search optimization with {self.config.n_trials} trials")
        
        self.start_time = datetime.now(timezone.utc)
        
        for trial in range(self.config.n_trials):
            if self.config.timeout_seconds:
                elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds()
                if elapsed > self.config.timeout_seconds:
                    logger.info(f"Optimization timeout reached after {elapsed:.2f} seconds")
                    break
            
            # Sample random parameters
            params = self._sample_parameters()
            
            # Evaluate trial
            score = self._evaluate_trial(params, objective_function, trial)
            
            # Check early stopping
            if self._check_early_stopping(trial):
                logger.info(f"Early stopping triggered at trial {trial}")
                break
        
        return self._create_result()
    
    def _sample_parameters(self) -> Dict[str, Any]:
        """Sample random parameters from the parameter space."""
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
                # Simple list of choices
                params[param_name] = np.random.choice(param_config)
        
        return params
    
    def _create_result(self) -> OptimizationResult:
        """Create optimization result."""
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
            optimization_algorithm='random',
            objective_metric=self.config.objective_metric,
            trial_history=self.trial_history.copy(),
            convergence_data=convergence_data
        )


class GridOptimizer(BaseOptimizer):
    """Grid search hyperparameter optimizer."""
    
    def optimize(self, objective_function: Callable[[Dict[str, Any]], float]) -> OptimizationResult:
        """Run grid search optimization."""
        logger.info("Starting grid search optimization")
        
        self.start_time = datetime.now(timezone.utc)
        
        # Generate all parameter combinations
        param_combinations = self._generate_parameter_combinations()
        total_combinations = len(param_combinations)
        
        logger.info(f"Evaluating {total_combinations} parameter combinations")
        
        for trial, params in enumerate(param_combinations):
            if self.config.timeout_seconds:
                elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds()
                if elapsed > self.config.timeout_seconds:
                    logger.info(f"Optimization timeout reached after {elapsed:.2f} seconds")
                    break
            
            # Evaluate trial
            score = self._evaluate_trial(params, objective_function, trial)
        
        return self._create_result()
    
    def _generate_parameter_combinations(self) -> List[Dict[str, Any]]:
        """Generate all parameter combinations for grid search."""
        import itertools
        
        param_names = list(self.config.parameter_space.keys())
        param_values = []
        
        for param_name in param_names:
            param_config = self.config.parameter_space[param_name]
            
            if isinstance(param_config, dict):
                if param_config['type'] == 'uniform' or param_config['type'] == 'loguniform':
                    # Create grid points
                    low = param_config['low']
                    high = param_config['high']
                    n_points = param_config.get('n_points', 10)
                    
                    if param_config['type'] == 'uniform':
                        values = np.linspace(low, high, n_points)
                    else:  # loguniform
                        values = np.exp(np.linspace(np.log(low), np.log(high), n_points))
                        
                elif param_config['type'] == 'int':
                    low = param_config['low']
                    high = param_config['high']
                    values = list(range(low, high + 1))
                    
                elif param_config['type'] in ['categorical', 'discrete']:
                    values = param_config['choices']
                    
                else:
                    values = [param_config.get('default', 0)]
                    
            else:
                values = param_config
            
            param_values.append(values)
        
        # Generate all combinations
        combinations = list(itertools.product(*param_values))
        
        # Convert to parameter dictionaries
        param_combinations = []
        for combination in combinations:
            params = dict(zip(param_names, combination))
            param_combinations.append(params)
        
        return param_combinations
    
    def _create_result(self) -> OptimizationResult:
        """Create optimization result."""
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
            optimization_algorithm='grid',
            objective_metric=self.config.objective_metric,
            trial_history=self.trial_history.copy(),
            convergence_data=convergence_data
        )


class HyperparameterOptimizer:
    """
    Main hyperparameter optimization interface.
    """
    
    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.optimizer: Optional[BaseOptimizer] = None
        self._initialize_optimizer()
    
    def _initialize_optimizer(self) -> None:
        """Initialize the appropriate optimizer based on config."""
        if self.config.optimization_algorithm == 'random':
            self.optimizer = RandomOptimizer(self.config)
        elif self.config.optimization_algorithm == 'grid':
            self.optimizer = GridOptimizer(self.config)
        elif self.config.optimization_algorithm == 'bayesian':
            # Will be implemented in BayesianOptimizer
            from .bayesian_optimizer import BayesianOptimizer
            self.optimizer = BayesianOptimizer(self.config)
        else:
            raise ValueError(f"Unsupported optimization algorithm: {self.config.optimization_algorithm}")
    
    def optimize(self, objective_function: Callable[[Dict[str, Any]], float]) -> OptimizationResult:
        """
        Run hyperparameter optimization.
        
        Args:
            objective_function: Function that takes parameters and returns a score
            
        Returns:
            OptimizationResult with best parameters and scores
        """
        if not self.optimizer:
            raise RuntimeError("Optimizer not initialized")
        
        logger.info(f"Starting {self.config.optimization_algorithm} optimization")
        logger.info(f"Parameter space: {list(self.config.parameter_space.keys())}")
        logger.info(f"Objective: {self.config.objective_metric} ({self.config.direction})")
        
        result = self.optimizer.optimize(objective_function)
        
        logger.info(f"Optimization completed in {result.optimization_time:.2f} seconds")
        logger.info(f"Best score: {result.best_score:.4f}")
        logger.info(f"Best parameters: {result.best_params}")
        
        return result
    
    def save_result(self, result: OptimizationResult, filepath: str) -> None:
        """Save optimization result to file."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)
        
        logger.info(f"Optimization result saved to {filepath}")
    
    def load_result(self, filepath: str) -> OptimizationResult:
        """Load optimization result from file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        return OptimizationResult(
            best_params=data['best_params'],
            best_score=data['best_score'],
            best_trial=data['best_trial'],
            n_trials=data['n_trials'],
            optimization_time=data['optimization_time'],
            optimization_algorithm=data['optimization_algorithm'],
            objective_metric=data['objective_metric'],
            trial_history=data['trial_history'],
            convergence_data=data['convergence_data'],
            parameter_importance=data.get('parameter_importance', {})
        )
    
    def get_optimization_summary(self, result: OptimizationResult) -> Dict[str, Any]:
        """Get summary of optimization results."""
        if not result.trial_history:
            return {}
        
        scores = [trial['score'] for trial in result.trial_history]
        evaluation_times = [trial['evaluation_time'] for trial in result.trial_history]
        
        summary = {
            'best_score': result.best_score,
            'best_trial': result.best_trial,
            'total_trials': result.n_trials,
            'optimization_time': result.optimization_time,
            'avg_evaluation_time': np.mean(evaluation_times),
            'score_statistics': {
                'mean': np.mean(scores),
                'std': np.std(scores),
                'min': np.min(scores),
                'max': np.max(scores),
                'median': np.median(scores)
            },
            'convergence_info': {
                'improvements': len([i for i in range(1, len(scores)) if scores[i] > scores[i-1]]),
                'final_improvement_trial': self._find_last_improvement(scores)
            }
        }
        
        return summary
    
    def _find_last_improvement(self, scores: List[float]) -> int:
        """Find the trial number of the last improvement."""
        if len(scores) < 2:
            return 0
        
        best_score = scores[0]
        last_improvement = 0
        
        for i, score in enumerate(scores[1:], 1):
            if self.config.direction == 'maximize':
                if score > best_score:
                    best_score = score
                    last_improvement = i
            else:
                if score < best_score:
                    best_score = score
                    last_improvement = i
        
        return last_improvement
