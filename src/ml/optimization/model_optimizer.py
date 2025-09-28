"""
Model Optimization interface for ML trading systems.
Provides high-level optimization capabilities for different model types.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple, Callable, Union
from dataclasses import dataclass
from enum import Enum
import logging

from .hyperparameter_optimizer import HyperparameterOptimizer, OptimizationConfig, OptimizationResult
from .multi_objective_optimizer import MultiObjectiveOptimizer, Objective, ParetoFront
from .cross_validation import CrossValidator, ValidationStrategy

logger = logging.getLogger(__name__)


class OptimizationObjective(Enum):
    """Available optimization objectives."""
    SHARPE_RATIO = "sharpe_ratio"
    SORTINO_RATIO = "sortino_ratio"
    CALMAR_RATIO = "calmar_ratio"
    MAX_DRAWDOWN = "max_drawdown"
    WIN_RATE = "win_rate"
    PROFIT_FACTOR = "profit_factor"
    RETURN = "return"
    VOLATILITY = "volatility"
    INFORMATION_RATIO = "information_ratio"
    CUSTOM = "custom"


@dataclass
class ModelOptimizationConfig:
    """Configuration for model optimization."""
    model_type: str
    parameter_space: Dict[str, Any]
    objectives: List[Union[str, OptimizationObjective]]
    objective_weights: Optional[List[float]] = None
    optimization_type: str = 'single_objective'  # 'single_objective' or 'multi_objective'
    optimization_algorithm: str = 'bayesian'
    n_trials: int = 100
    cv_strategy: ValidationStrategy = ValidationStrategy.TIME_SERIES_SPLIT
    cv_folds: int = 5
    timeout_seconds: Optional[int] = None
    early_stopping_rounds: Optional[int] = None
    random_seed: Optional[int] = None
    
    # Multi-objective specific
    population_size: int = 50
    n_generations: int = 50
    
    # Advanced options
    warm_start: bool = False
    warm_start_trials: int = 10
    pruning_enabled: bool = True


class ModelOptimizer:
    """
    High-level model optimization interface.
    """
    
    def __init__(self, config: ModelOptimizationConfig):
        self.config = config
        self.optimization_result: Optional[Union[OptimizationResult, ParetoFront]] = None
        self.training_history: List[Dict[str, Any]] = []
        
        logger.info(f"Initialized model optimizer for {config.model_type}")
    
    def optimize_single_objective(self, 
                                model_factory: Callable,
                                data: pd.DataFrame,
                                target_column: str,
                                feature_columns: Optional[List[str]] = None) -> OptimizationResult:
        """
        Optimize model for a single objective.
        
        Args:
            model_factory: Function that creates model instances
            data: Training data
            target_column: Name of target column
            feature_columns: List of feature column names
            
        Returns:
            OptimizationResult with best parameters
        """
        logger.info(f"Starting single-objective optimization for {self.config.model_type}")
        
        # Prepare data
        if feature_columns is None:
            feature_columns = [col for col in data.columns if col != target_column]
        
        X = data[feature_columns]
        y = data[target_column]
        
        # Create objective function
        primary_objective = self.config.objectives[0]
        objective_function = self._create_objective_function(
            model_factory, X, y, primary_objective
        )
        
        # Create optimization config
        opt_config = OptimizationConfig(
            model_type=self.config.model_type,
            parameter_space=self.config.parameter_space,
            objective_metric=primary_objective.value if isinstance(primary_objective, OptimizationObjective) else primary_objective,
            optimization_algorithm=self.config.optimization_algorithm,
            n_trials=self.config.n_trials,
            cv_folds=self.config.cv_folds,
            timeout_seconds=self.config.timeout_seconds,
            early_stopping_rounds=self.config.early_stopping_rounds,
            random_seed=self.config.random_seed
        )
        
        # Run optimization
        optimizer = HyperparameterOptimizer(opt_config)
        self.optimization_result = optimizer.optimize(objective_function)
        
        logger.info(f"Single-objective optimization completed")
        logger.info(f"Best score: {self.optimization_result.best_score:.4f}")
        
        return self.optimization_result
    
    def optimize_multi_objective(self, 
                               model_factory: Callable,
                               data: pd.DataFrame,
                               target_column: str,
                               feature_columns: Optional[List[str]] = None) -> ParetoFront:
        """
        Optimize model for multiple objectives.
        
        Args:
            model_factory: Function that creates model instances
            data: Training data
            target_column: Name of target column
            feature_columns: List of feature column names
            
        Returns:
            ParetoFront with Pareto-optimal solutions
        """
        logger.info(f"Starting multi-objective optimization for {self.config.model_type}")
        
        # Prepare data
        if feature_columns is None:
            feature_columns = [col for col in data.columns if col != target_column]
        
        X = data[feature_columns]
        y = data[target_column]
        
        # Create objectives
        objectives = []
        for i, obj_name in enumerate(self.config.objectives):
            weight = 1.0
            if self.config.objective_weights and i < len(self.config.objective_weights):
                weight = self.config.objective_weights[i]
            
            obj = Objective(
                name=obj_name.value if isinstance(obj_name, OptimizationObjective) else obj_name,
                weight=weight,
                direction=self._get_objective_direction(obj_name)
            )
            objectives.append(obj)
        
        # Create objective functions
        objective_functions = {}
        for obj in objectives:
            objective_functions[obj.name] = self._create_objective_function(
                model_factory, X, y, obj.name
            )
        
        # Run multi-objective optimization
        optimizer = MultiObjectiveOptimizer(
            objectives=objectives,
            parameter_space=self.config.parameter_space,
            population_size=self.config.population_size,
            n_generations=self.config.n_generations,
            random_seed=self.config.random_seed
        )
        
        self.optimization_result = optimizer.optimize(objective_functions)
        
        logger.info(f"Multi-objective optimization completed")
        logger.info(f"Found {len(self.optimization_result.get_non_dominated())} Pareto-optimal solutions")
        
        return self.optimization_result
    
    def optimize(self, 
                model_factory: Callable,
                data: pd.DataFrame,
                target_column: str,
                feature_columns: Optional[List[str]] = None) -> Union[OptimizationResult, ParetoFront]:
        """
        Optimize model based on configuration.
        
        Args:
            model_factory: Function that creates model instances
            data: Training data
            target_column: Name of target column
            feature_columns: List of feature column names
            
        Returns:
            Optimization result (single or multi-objective)
        """
        if self.config.optimization_type == 'single_objective':
            return self.optimize_single_objective(model_factory, data, target_column, feature_columns)
        elif self.config.optimization_type == 'multi_objective':
            return self.optimize_multi_objective(model_factory, data, target_column, feature_columns)
        else:
            raise ValueError(f"Unsupported optimization type: {self.config.optimization_type}")
    
    def _create_objective_function(self, 
                                 model_factory: Callable,
                                 X: pd.DataFrame,
                                 y: pd.Series,
                                 objective_name: str) -> Callable[[Dict[str, Any]], float]:
        """Create objective function for optimization."""
        
        def objective_function(params: Dict[str, Any]) -> float:
            try:
                # Create cross-validator
                cv = CrossValidator(
                    strategy=self.config.cv_strategy,
                    n_splits=self.config.cv_folds
                )
                
                # Create scoring function
                def score_function(y_true, y_pred, model):
                    return self._calculate_objective_score(y_true, y_pred, model, objective_name)
                
                # Run cross-validation
                cv_results = cv.cross_validate(
                    X, y, model_factory, score_function, **params
                )
                
                # Return mean score
                score = cv_results['mean_score']
                
                # Record training history
                self.training_history.append({
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'params': params.copy(),
                    'objective': objective_name,
                    'score': score,
                    'cv_mean': cv_results['mean_score'],
                    'cv_std': cv_results['std_score']
                })
                
                return score
                
            except Exception as e:
                logger.error(f"Error in objective function: {e}")
                return float('-inf') if self._get_objective_direction(objective_name) == 'maximize' else float('inf')
        
        return objective_function
    
    def _calculate_objective_score(self, 
                                 y_true: pd.Series, 
                                 y_pred: np.ndarray, 
                                 model: Any, 
                                 objective_name: str) -> float:
        """Calculate objective score from predictions."""
        
        # Convert objective name if it's an enum
        if isinstance(objective_name, OptimizationObjective):
            objective_name = objective_name.value
        
        # Mock trading performance calculation
        # In a real implementation, this would use actual trading results
        
        if objective_name == 'sharpe_ratio':
            # Calculate Sharpe ratio from returns
            returns = np.diff(y_pred) / y_pred[:-1]
            if len(returns) > 1 and np.std(returns) > 0:
                return np.mean(returns) / np.std(returns) * np.sqrt(252)
            return 0.0
            
        elif objective_name == 'sortino_ratio':
            # Calculate Sortino ratio (downside deviation)
            returns = np.diff(y_pred) / y_pred[:-1]
            downside_returns = returns[returns < 0]
            if len(downside_returns) > 1:
                return np.mean(returns) / np.std(downside_returns) * np.sqrt(252)
            return 0.0
            
        elif objective_name == 'max_drawdown':
            # Calculate maximum drawdown
            cumulative = np.cumprod(1 + np.diff(y_pred) / y_pred[:-1])
            running_max = np.maximum.accumulate(cumulative)
            drawdowns = (cumulative - running_max) / running_max
            return abs(np.min(drawdowns))
            
        elif objective_name == 'win_rate':
            # Calculate win rate
            returns = np.diff(y_pred) / y_pred[:-1]
            wins = np.sum(returns > 0)
            return wins / len(returns) if len(returns) > 0 else 0.0
            
        elif objective_name == 'profit_factor':
            # Calculate profit factor
            returns = np.diff(y_pred) / y_pred[:-1]
            profits = returns[returns > 0]
            losses = abs(returns[returns < 0])
            
            if len(losses) > 0:
                return np.sum(profits) / np.sum(losses) if np.sum(losses) > 0 else float('inf')
            return 1.0
            
        elif objective_name == 'return':
            # Calculate total return
            if len(y_pred) > 1:
                return (y_pred[-1] - y_pred[0]) / y_pred[0]
            return 0.0
            
        elif objective_name == 'volatility':
            # Calculate volatility
            returns = np.diff(y_pred) / y_pred[:-1]
            return np.std(returns) * np.sqrt(252) if len(returns) > 1 else 0.0
            
        elif objective_name == 'information_ratio':
            # Calculate information ratio vs benchmark
            returns = np.diff(y_pred) / y_pred[:-1]
            benchmark_returns = np.diff(y_true.values) / y_true.values[:-1]
            
            if len(returns) > 1 and len(benchmark_returns) > 1:
                excess_returns = returns - benchmark_returns
                return np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
            return 0.0
            
        else:
            # Default: use model's built-in score if available
            if hasattr(model, 'score'):
                return model.score(y_true, y_pred)
            else:
                # Fallback: use simple accuracy for classification or R² for regression
                if len(np.unique(y_true)) < 10:  # Classification
                    return np.mean(y_true == np.round(y_pred))
                else:  # Regression
                    ss_res = np.sum((y_true - y_pred) ** 2)
                    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
                    return 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
    
    def _get_objective_direction(self, objective_name: str) -> str:
        """Get optimization direction for objective."""
        if isinstance(objective_name, OptimizationObjective):
            objective_name = objective_name.value
        
        # Objectives to minimize
        minimize_objectives = {'max_drawdown', 'volatility'}
        
        return 'minimize' if objective_name in minimize_objectives else 'maximize'
    
    def get_optimization_summary(self) -> Dict[str, Any]:
        """Get summary of optimization results."""
        if self.optimization_result is None:
            return {'status': 'not_optimized'}
        
        summary = {
            'model_type': self.config.model_type,
            'optimization_type': self.config.optimization_type,
            'objectives': [obj.value if isinstance(obj, OptimizationObjective) else obj for obj in self.config.objectives],
            'training_trials': len(self.training_history)
        }
        
        if self.config.optimization_type == 'single_objective':
            result = self.optimization_result
            summary.update({
                'best_score': result.best_score,
                'best_params': result.best_params,
                'total_trials': result.n_trials,
                'optimization_time': result.optimization_time,
                'convergence_data': result.convergence_data
            })
        else:
            pareto_front = self.optimization_result
            non_dominated = pareto_front.get_non_dominated()
            summary.update({
                'pareto_front_size': len(non_dominated),
                'total_generations': len(pareto_front.generation_history) if hasattr(pareto_front, 'generation_history') else 0,
                'objective_ranges': {}
            })
            
            for obj in pareto_front.objectives:
                values = [point.objectives[obj.name] for point in non_dominated]
                if values:
                    summary['objective_ranges'][obj.name] = {
                        'min': np.min(values),
                        'max': np.max(values),
                        'mean': np.mean(values)
                    }
        
        return summary
    
    def get_best_model_config(self) -> Dict[str, Any]:
        """Get configuration for the best model."""
        if self.optimization_result is None:
            raise RuntimeError("Model has not been optimized yet")
        
        if self.config.optimization_type == 'single_objective':
            return self.optimization_result.best_params
        else:
            # For multi-objective, return the first non-dominated solution
            pareto_front = self.optimization_result
            non_dominated = pareto_front.get_non_dominated()
            if non_dominated:
                return non_dominated[0].parameters
            else:
                raise RuntimeError("No Pareto-optimal solutions found")
    
    def save_optimization_result(self, filepath: str) -> None:
        """Save optimization result to file."""
        if self.optimization_result is None:
            raise RuntimeError("No optimization result to save")
        
        import json
        
        data = {
            'config': {
                'model_type': self.config.model_type,
                'optimization_type': self.config.optimization_type,
                'objectives': [obj.value if isinstance(obj, OptimizationObjective) else obj for obj in self.config.objectives],
                'parameter_space': self.config.parameter_space
            },
            'result': self.optimization_result.to_dict() if hasattr(self.optimization_result, 'to_dict') else str(self.optimization_result),
            'training_history': self.training_history,
            'summary': self.get_optimization_summary()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Optimization result saved to {filepath}")
