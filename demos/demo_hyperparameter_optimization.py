#!/usr/bin/env python3
"""
Demo script for Hyperparameter Optimization Framework (Phase 5D.2).
Demonstrates automated hyperparameter tuning and model optimization.
"""

import sys
import os
import time
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Callable

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, str(project_root))

from src.ml.optimization import (
    HyperparameterOptimizer, OptimizationConfig, OptimizationResult,
    BayesianOptimizer, AcquisitionFunction,
    MultiObjectiveOptimizer, Objective, ParetoFront,
    CrossValidator, ValidationStrategy,
    ModelOptimizer, ModelOptimizationConfig, OptimizationObjective
)


def generate_mock_trading_data(n_points: int = 1000) -> pd.DataFrame:
    """Generate mock trading data for optimization demos."""
    np.random.seed(42)
    dates = pd.date_range(start=datetime(2020, 1, 1, tzinfo=timezone.utc), periods=n_points, freq='4h')
    
    # Generate realistic price data
    base_price = 100.0
    returns = np.random.normal(0.001, 0.02, n_points)  # 0.1% mean return, 2% volatility
    
    prices = [base_price]
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    # Generate features
    data = pd.DataFrame({
        'timestamp': dates,
        'price': prices,
        'returns': [0] + [prices[i]/prices[i-1] - 1 for i in range(1, len(prices))],
        'rsi': 50 + np.random.normal(0, 15, n_points),
        'macd': np.random.normal(0, 0.5, n_points),
        'bb_position': np.random.uniform(0, 1, n_points),
        'volume': np.random.exponential(1000, n_points),
        'volatility': np.random.exponential(0.02, n_points)
    })
    
    # Create target variable (future returns)
    data['target'] = data['returns'].shift(-1).fillna(0)
    
    return data


class MockTradingModel:
    """Mock trading model for demonstration."""
    
    def __init__(self, 
                 learning_rate: float = 0.1,
                 n_estimators: int = 100,
                 max_depth: int = 6,
                 min_samples_split: int = 2,
                 subsample: float = 1.0,
                 colsample_bytree: float = 1.0,
                 reg_alpha: float = 0.0,
                 reg_lambda: float = 1.0,
                 gamma: float = 0.0):
        self.learning_rate = learning_rate
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.subsample = subsample
        self.colsample_bytree = colsample_bytree
        self.reg_alpha = reg_alpha
        self.reg_lambda = reg_lambda
        self.gamma = gamma
        
        self.is_trained = False
        self.feature_importance = None
    
    def train(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
        """Mock training method."""
        self.is_trained = True
        
        # Simulate training time
        time.sleep(0.01)
        
        # Mock feature importance
        self.feature_importance = {col: np.random.random() for col in X.columns}
        
        # Mock training metrics
        metrics = {
            'train_score': np.random.uniform(0.7, 0.9),
            'validation_score': np.random.uniform(0.6, 0.8),
            'training_time': 0.01
        }
        
        return metrics
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Mock prediction method."""
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")
        
        # Generate mock predictions based on parameters
        n_samples = len(X)
        
        # Simple mock prediction that depends on hyperparameters
        base_prediction = np.random.normal(0, 0.01, n_samples)
        
        # Adjust based on model complexity
        complexity_factor = (self.n_estimators * self.max_depth) / 1000
        base_prediction *= complexity_factor
        
        # Add some noise based on regularization
        noise_factor = 1.0 / (1.0 + self.reg_alpha + self.reg_lambda)
        base_prediction += np.random.normal(0, 0.005 * noise_factor, n_samples)
        
        return base_prediction
    
    def score(self, y_true: pd.Series, y_pred: np.ndarray) -> float:
        """Mock scoring method."""
        # Simple R² score
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        return 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0


def demo_single_objective_optimization():
    """Demonstrate single-objective hyperparameter optimization."""
    print("\n" + "="*60)
    print("🎯 DEMO: Single-Objective Hyperparameter Optimization")
    print("="*60)
    
    # Define parameter space
    parameter_space = {
        'learning_rate': {'type': 'loguniform', 'low': 0.01, 'high': 0.3},
        'n_estimators': {'type': 'int', 'low': 50, 'high': 300},
        'max_depth': {'type': 'int', 'low': 3, 'high': 10},
        'min_samples_split': {'type': 'int', 'low': 2, 'high': 20},
        'subsample': {'type': 'uniform', 'low': 0.6, 'high': 1.0},
        'colsample_bytree': {'type': 'uniform', 'low': 0.6, 'high': 1.0},
        'reg_alpha': {'type': 'loguniform', 'low': 0.001, 'high': 1.0},
        'reg_lambda': {'type': 'loguniform', 'low': 0.001, 'high': 1.0}
    }
    
    # Create optimization config
    config = OptimizationConfig(
        model_type='mock_trading_model',
        parameter_space=parameter_space,
        objective_metric='sharpe_ratio',
        optimization_algorithm='bayesian',
        n_trials=20,  # Reduced for demo
        cv_folds=3,
        timeout_seconds=60,
        early_stopping_rounds=5,
        direction='maximize',
        random_seed=42
    )
    
    print(f"Parameter space: {list(parameter_space.keys())}")
    print(f"Optimization algorithm: {config.optimization_algorithm}")
    print(f"Number of trials: {config.n_trials}")
    
    # Create objective function
    def objective_function(params: Dict[str, Any]) -> float:
        """Objective function that evaluates model performance."""
        try:
            # Create model with given parameters
            model = MockTradingModel(**params)
            
            # Generate mock data
            data = generate_mock_trading_data(500)
            
            # Simple train/test split
            split_idx = int(0.8 * len(data))
            train_data = data.iloc[:split_idx]
            test_data = data.iloc[split_idx:]
            
            # Train model
            feature_cols = ['rsi', 'macd', 'bb_position', 'volume', 'volatility']
            X_train = train_data[feature_cols]
            y_train = train_data['target']
            
            model.train(X_train, y_train)
            
            # Evaluate on test set
            X_test = test_data[feature_cols]
            y_test = test_data['target']
            y_pred = model.predict(X_test)
            
            # Calculate Sharpe ratio (mock)
            returns = y_pred
            if len(returns) > 1 and np.std(returns) > 0:
                sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252)
            else:
                sharpe = 0.0
            
            print(f"  Trial with params {params}: Sharpe = {sharpe:.4f}")
            return sharpe
            
        except Exception as e:
            print(f"  Error in trial: {e}")
            return float('-inf')
    
    # Run optimization
    print(f"\nStarting {config.optimization_algorithm} optimization...")
    optimizer = HyperparameterOptimizer(config)
    result = optimizer.optimize(objective_function)
    
    # Display results
    print(f"\n📊 Optimization Results:")
    print(f"  Best Score: {result.best_score:.4f}")
    print(f"  Best Parameters:")
    for param, value in result.best_params.items():
        print(f"    {param}: {value}")
    print(f"  Total Trials: {result.n_trials}")
    print(f"  Optimization Time: {result.optimization_time:.2f} seconds")
    
    # Show convergence
    if result.convergence_data:
        print(f"  Convergence:")
        scores = [score for _, score in result.convergence_data]
        print(f"    Initial Score: {scores[0]:.4f}")
        print(f"    Final Score: {scores[-1]:.4f}")
        print(f"    Improvement: {scores[-1] - scores[0]:.4f}")
    
    print(f"\n✅ Single-objective optimization demo completed!")


def demo_multi_objective_optimization():
    """Demonstrate multi-objective hyperparameter optimization."""
    print("\n" + "="*60)
    print("🎯 DEMO: Multi-Objective Hyperparameter Optimization")
    print("="*60)
    
    # Define parameter space
    parameter_space = {
        'learning_rate': {'type': 'loguniform', 'low': 0.01, 'high': 0.3},
        'n_estimators': {'type': 'int', 'low': 50, 'high': 200},
        'max_depth': {'type': 'int', 'low': 3, 'high': 8},
        'reg_alpha': {'type': 'loguniform', 'low': 0.001, 'high': 0.1},
        'reg_lambda': {'type': 'loguniform', 'low': 0.001, 'high': 0.1}
    }
    
    # Define objectives
    objectives = [
        Objective('sharpe_ratio', weight=1.0, direction='maximize'),
        Objective('max_drawdown', weight=1.0, direction='minimize'),
        Objective('win_rate', weight=0.5, direction='maximize')
    ]
    
    print(f"Parameter space: {list(parameter_space.keys())}")
    print(f"Objectives: {[obj.name for obj in objectives]}")
    
    # Create objective functions
    def create_objective_function(objective_name: str) -> Callable[[Dict[str, Any]], float]:
        """Create objective function for a specific objective."""
        def objective_function(params: Dict[str, Any]) -> float:
            try:
                model = MockTradingModel(**params)
                data = generate_mock_trading_data(400)
                
                split_idx = int(0.8 * len(data))
                train_data = data.iloc[:split_idx]
                test_data = data.iloc[split_idx:]
                
                feature_cols = ['rsi', 'macd', 'bb_position', 'volume', 'volatility']
                X_train = train_data[feature_cols]
                y_train = train_data['target']
                
                model.train(X_train, y_train)
                
                X_test = test_data[feature_cols]
                y_test = test_data['target']
                y_pred = model.predict(X_test)
                
                # Calculate objective-specific metrics
                if objective_name == 'sharpe_ratio':
                    returns = y_pred
                    if len(returns) > 1 and np.std(returns) > 0:
                        return np.mean(returns) / np.std(returns) * np.sqrt(252)
                    return 0.0
                    
                elif objective_name == 'max_drawdown':
                    cumulative = np.cumprod(1 + y_pred)
                    running_max = np.maximum.accumulate(cumulative)
                    drawdowns = (cumulative - running_max) / running_max
                    return abs(np.min(drawdowns))
                    
                elif objective_name == 'win_rate':
                    wins = np.sum(y_pred > 0)
                    return wins / len(y_pred) if len(y_pred) > 0 else 0.0
                
                return 0.0
                
            except Exception as e:
                print(f"  Error in {objective_name} evaluation: {e}")
                return float('-inf') if objectives[0].direction == 'maximize' else float('inf')
        
        return objective_function
    
    # Create objective functions
    objective_functions = {
        obj.name: create_objective_function(obj.name) for obj in objectives
    }
    
    # Run multi-objective optimization
    print(f"\nStarting multi-objective optimization...")
    optimizer = MultiObjectiveOptimizer(
        objectives=objectives,
        parameter_space=parameter_space,
        population_size=20,  # Reduced for demo
        n_generations=10,    # Reduced for demo
        random_seed=42
    )
    
    pareto_front = optimizer.optimize(objective_functions)
    
    # Display results
    non_dominated = pareto_front.get_non_dominated()
    print(f"\n📊 Multi-Objective Optimization Results:")
    print(f"  Pareto Front Size: {len(non_dominated)} solutions")
    print(f"  Total Generations: {len(pareto_front.generation_history) if hasattr(pareto_front, 'generation_history') else 'N/A'}")
    
    # Show top solutions
    print(f"\n  Top Pareto-Optimal Solutions:")
    for i, solution in enumerate(non_dominated[:5]):  # Show top 5
        print(f"    Solution {i+1}:")
        print(f"      Sharpe Ratio: {solution.objectives['sharpe_ratio']:.4f}")
        print(f"      Max Drawdown: {solution.objectives['max_drawdown']:.4f}")
        print(f"      Win Rate: {solution.objectives['win_rate']:.4f}")
        print(f"      Key Params: learning_rate={solution.parameters['learning_rate']:.3f}, "
              f"n_estimators={solution.parameters['n_estimators']}")
    
    # Show optimization summary
    summary = optimizer.get_optimization_summary()
    print(f"\n  Optimization Summary:")
    print(f"    Final Population: {summary['final_population_size']}")
    print(f"    Pareto Front: {summary['pareto_front_size']} solutions")
    
    print(f"\n✅ Multi-objective optimization demo completed!")


def demo_cross_validation():
    """Demonstrate cross-validation strategies."""
    print("\n" + "="*60)
    print("🔄 DEMO: Cross-Validation Strategies")
    print("="*60)
    
    # Generate mock data
    data = generate_mock_trading_data(200)
    feature_cols = ['rsi', 'macd', 'bb_position', 'volume', 'volatility']
    X = data[feature_cols]
    y = data['target']
    
    print(f"Dataset size: {len(X)} samples")
    print(f"Features: {feature_cols}")
    
    # Test different validation strategies
    strategies = [
        (ValidationStrategy.K_FOLD, "K-Fold"),
        (ValidationStrategy.TIME_SERIES_SPLIT, "Time Series Split"),
        (ValidationStrategy.WALK_FORWARD, "Walk Forward"),
        (ValidationStrategy.BLOCKED_CROSS_VALIDATION, "Blocked CV")
    ]
    
    for strategy, name in strategies:
        print(f"\n  Testing {name}:")
        
        try:
            # Create validator
            if strategy == ValidationStrategy.K_FOLD:
                validator = CrossValidator(strategy=strategy, n_splits=5)
            elif strategy == ValidationStrategy.TIME_SERIES_SPLIT:
                validator = CrossValidator(strategy=strategy, n_splits=5, test_size=0.2)
            elif strategy == ValidationStrategy.WALK_FORWARD:
                validator = CrossValidator(strategy=strategy, n_splits=3, train_size=100, test_size=30)
            else:  # BLOCKED_CROSS_VALIDATION
                validator = CrossValidator(strategy=strategy, n_splits=5, block_size=20)
            
            # Generate splits
            splits = validator.split(X, y)
            print(f"    Generated {len(splits)} splits")
            
            # Show split statistics
            for i, split in enumerate(splits):
                train_size = len(split.train_indices)
                test_size = len(split.test_indices)
                print(f"    Split {i+1}: Train={train_size}, Test={test_size}")
            
            # Run cross-validation
            def model_factory(**kwargs):
                return MockTradingModel(**kwargs)
            
            def score_function(y_true, y_pred, model):
                return model.score(y_true, y_pred)
            
            cv_results = validator.cross_validate(
                X, y, model_factory, score_function,
                learning_rate=0.1, n_estimators=100
            )
            
            print(f"    CV Results: {cv_results['mean_score']:.4f} ± {cv_results['std_score']:.4f}")
            
        except Exception as e:
            print(f"    Error: {e}")
    
    print(f"\n✅ Cross-validation demo completed!")


def demo_model_optimizer():
    """Demonstrate high-level model optimization interface."""
    print("\n" + "="*60)
    print("🚀 DEMO: Model Optimizer Interface")
    print("="*60)
    
    # Generate data
    data = generate_mock_trading_data(300)
    feature_cols = ['rsi', 'macd', 'bb_position', 'volume', 'volatility']
    
    print(f"Dataset size: {len(data)} samples")
    print(f"Features: {feature_cols}")
    
    # Single-objective optimization
    print(f"\n  Single-Objective Optimization:")
    
    single_obj_config = ModelOptimizationConfig(
        model_type='mock_trading_model',
        parameter_space={
            'learning_rate': {'type': 'loguniform', 'low': 0.01, 'high': 0.3},
            'n_estimators': {'type': 'int', 'low': 50, 'high': 150},
            'max_depth': {'type': 'int', 'low': 3, 'high': 8}
        },
        objectives=[OptimizationObjective.SHARPE_RATIO],
        optimization_type='single_objective',
        optimization_algorithm='random',
        n_trials=10,
        cv_strategy=ValidationStrategy.K_FOLD,
        cv_folds=3,
        random_seed=42
    )
    
    optimizer = ModelOptimizer(single_obj_config)
    
    def model_factory(**kwargs):
        return MockTradingModel(**kwargs)
    
    result = optimizer.optimize_single_objective(
        model_factory=model_factory,
        data=data,
        target_column='target',
        feature_columns=feature_cols
    )
    
    print(f"    Best Score: {result.best_score:.4f}")
    print(f"    Best Parameters: {result.best_params}")
    print(f"    Optimization Time: {result.optimization_time:.2f}s")
    
    # Multi-objective optimization
    print(f"\n  Multi-Objective Optimization:")
    
    multi_obj_config = ModelOptimizationConfig(
        model_type='mock_trading_model',
        parameter_space={
            'learning_rate': {'type': 'loguniform', 'low': 0.01, 'high': 0.2},
            'n_estimators': {'type': 'int', 'low': 50, 'high': 100},
            'reg_alpha': {'type': 'loguniform', 'low': 0.001, 'high': 0.1}
        },
        objectives=[OptimizationObjective.SHARPE_RATIO, OptimizationObjective.MAX_DRAWDOWN],
        objective_weights=[1.0, 1.0],
        optimization_type='multi_objective',
        population_size=15,
        n_generations=8,
        random_seed=42
    )
    
    optimizer_multi = ModelOptimizer(multi_obj_config)
    
    pareto_result = optimizer_multi.optimize_multi_objective(
        model_factory=model_factory,
        data=data,
        target_column='target',
        feature_columns=feature_cols
    )
    
    non_dominated = pareto_result.get_non_dominated()
    print(f"    Pareto Front Size: {len(non_dominated)} solutions")
    
    if non_dominated:
        best_solution = non_dominated[0]
        print(f"    Best Solution Objectives:")
        for obj_name, obj_value in best_solution.objectives.items():
            print(f"      {obj_name}: {obj_value:.4f}")
    
    # Get optimization summaries
    single_summary = optimizer.get_optimization_summary()
    multi_summary = optimizer_multi.get_optimization_summary()
    
    print(f"\n  Optimization Summaries:")
    print(f"    Single-objective trials: {single_summary['training_trials']}")
    print(f"    Multi-objective generations: {multi_summary['total_generations']}")
    
    print(f"\n✅ Model optimizer demo completed!")


def demo_comprehensive_optimization():
    """Demonstrate comprehensive optimization workflow."""
    print("\n" + "="*60)
    print("🎯 DEMO: Comprehensive Optimization Workflow")
    print("="*60)
    
    # Generate comprehensive dataset
    data = generate_mock_trading_data(500)
    feature_cols = ['rsi', 'macd', 'bb_position', 'volume', 'volatility']
    
    print(f"Comprehensive dataset: {len(data)} samples")
    
    # Define comprehensive parameter space
    parameter_space = {
        'learning_rate': {'type': 'loguniform', 'low': 0.005, 'high': 0.5},
        'n_estimators': {'type': 'int', 'low': 30, 'high': 500},
        'max_depth': {'type': 'int', 'low': 2, 'high': 15},
        'min_samples_split': {'type': 'int', 'low': 2, 'high': 50},
        'subsample': {'type': 'uniform', 'low': 0.5, 'high': 1.0},
        'colsample_bytree': {'type': 'uniform', 'low': 0.5, 'high': 1.0},
        'reg_alpha': {'type': 'loguniform', 'low': 0.0001, 'high': 10.0},
        'reg_lambda': {'type': 'loguniform', 'low': 0.0001, 'high': 10.0},
        'gamma': {'type': 'loguniform', 'low': 0.0001, 'high': 1.0}
    }
    
    print(f"Parameter space: {len(parameter_space)} parameters")
    
    # Multi-objective optimization with multiple objectives
    objectives = [
        Objective('sharpe_ratio', weight=2.0, direction='maximize'),
        Objective('max_drawdown', weight=1.5, direction='minimize'),
        Objective('win_rate', weight=1.0, direction='maximize'),
        Objective('volatility', weight=0.5, direction='minimize')
    ]
    
    print(f"Optimization objectives: {[obj.name for obj in objectives]}")
    
    # Create comprehensive objective functions
    def create_comprehensive_objective(objective_name: str) -> Callable:
        def objective_function(params: Dict[str, Any]) -> float:
            try:
                model = MockTradingModel(**params)
                
                # Use time series split for more realistic evaluation
                split_idx = int(0.7 * len(data))
                train_data = data.iloc[:split_idx]
                test_data = data.iloc[split_idx:]
                
                X_train = train_data[feature_cols]
                y_train = train_data['target']
                
                model.train(X_train, y_train)
                
                X_test = test_data[feature_cols]
                y_test = test_data['target']
                y_pred = model.predict(X_test)
                
                # Calculate comprehensive metrics
                if objective_name == 'sharpe_ratio':
                    returns = y_pred
                    if len(returns) > 1 and np.std(returns) > 0:
                        return np.mean(returns) / np.std(returns) * np.sqrt(252)
                    return 0.0
                    
                elif objective_name == 'max_drawdown':
                    cumulative = np.cumprod(1 + y_pred)
                    running_max = np.maximum.accumulate(cumulative)
                    drawdowns = (cumulative - running_max) / running_max
                    return abs(np.min(drawdowns))
                    
                elif objective_name == 'win_rate':
                    wins = np.sum(y_pred > 0)
                    return wins / len(y_pred) if len(y_pred) > 0 else 0.0
                    
                elif objective_name == 'volatility':
                    returns = y_pred
                    return np.std(returns) * np.sqrt(252) if len(returns) > 1 else 0.0
                
                return 0.0
                
            except Exception as e:
                return float('-inf') if objectives[0].direction == 'maximize' else float('inf')
        
        return objective_function
    
    # Create objective functions
    objective_functions = {
        obj.name: create_comprehensive_objective(obj.name) for obj in objectives
    }
    
    # Run comprehensive optimization
    print(f"\nStarting comprehensive multi-objective optimization...")
    print(f"Population size: 25, Generations: 15")
    
    optimizer = MultiObjectiveOptimizer(
        objectives=objectives,
        parameter_space=parameter_space,
        population_size=25,
        n_generations=15,
        mutation_rate=0.15,
        crossover_rate=0.8,
        random_seed=42
    )
    
    pareto_front = optimizer.optimize(objective_functions)
    
    # Analyze results
    non_dominated = pareto_front.get_non_dominated()
    print(f"\n📊 Comprehensive Optimization Results:")
    print(f"  Final Pareto Front: {len(non_dominated)} solutions")
    print(f"  Total Generations: {len(pareto_front.generation_history) if hasattr(pareto_front, 'generation_history') else 'N/A'}")
    
    # Show top solutions by different criteria
    if non_dominated:
        # Sort by Sharpe ratio
        best_sharpe = max(non_dominated, key=lambda x: x.objectives['sharpe_ratio'])
        print(f"\n  Best Sharpe Ratio Solution:")
        print(f"    Sharpe: {best_sharpe.objectives['sharpe_ratio']:.4f}")
        print(f"    Max Drawdown: {best_sharpe.objectives['max_drawdown']:.4f}")
        print(f"    Win Rate: {best_sharpe.objectives['win_rate']:.4f}")
        print(f"    Key Params: learning_rate={best_sharpe.parameters['learning_rate']:.3f}, "
              f"n_estimators={best_sharpe.parameters['n_estimators']}")
        
        # Sort by low drawdown
        best_drawdown = min(non_dominated, key=lambda x: x.objectives['max_drawdown'])
        print(f"\n  Best Drawdown Solution:")
        print(f"    Sharpe: {best_drawdown.objectives['sharpe_ratio']:.4f}")
        print(f"    Max Drawdown: {best_drawdown.objectives['max_drawdown']:.4f}")
        print(f"    Win Rate: {best_drawdown.objectives['win_rate']:.4f}")
        print(f"    Key Params: learning_rate={best_drawdown.parameters['learning_rate']:.3f}, "
              f"n_estimators={best_drawdown.parameters['n_estimators']}")
    
    # Show optimization summary
    summary = optimizer.get_optimization_summary()
    print(f"\n  Optimization Summary:")
    print(f"    Final Population: {summary['final_population_size']}")
    print(f"    Pareto Front: {summary['pareto_front_size']} solutions")
    
    # Show objective ranges
    print(f"    Objective Ranges:")
    for obj in objectives:
        if f'{obj.name}_stats' in summary:
            stats = summary[f'{obj.name}_stats']
            print(f"      {obj.name}: {stats['min']:.4f} to {stats['max']:.4f} (mean: {stats['mean']:.4f})")
    
    print(f"\n✅ Comprehensive optimization demo completed!")


def main():
    """Run all hyperparameter optimization demos."""
    print("🚀 Hyperparameter Optimization Framework Demo (Phase 5D.2)")
    print("=" * 60)
    
    try:
        # Run individual demos
        demo_single_objective_optimization()
        demo_multi_objective_optimization()
        demo_cross_validation()
        demo_model_optimizer()
        
        # Run comprehensive integration demo
        demo_comprehensive_optimization()
        
        print("\n" + "="*60)
        print("🎉 All hyperparameter optimization demos completed successfully!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error running optimization demos: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
