"""
Multi-Objective Optimization for ML trading models.
Implements Pareto-optimal solutions for multiple conflicting objectives.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


@dataclass
class Objective:
    """Container for optimization objectives."""
    name: str
    weight: float = 1.0
    direction: str = 'maximize'  # 'maximize' or 'minimize'
    target_value: Optional[float] = None
    constraint_type: Optional[str] = None  # 'greater_than', 'less_than', 'equal_to'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'weight': self.weight,
            'direction': self.direction,
            'target_value': self.target_value,
            'constraint_type': self.constraint_type
        }


@dataclass
class ParetoPoint:
    """Container for a Pareto-optimal point."""
    parameters: Dict[str, Any]
    objectives: Dict[str, float]
    dominated: bool = False
    rank: int = 0
    crowding_distance: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'parameters': self.parameters,
            'objectives': self.objectives,
            'dominated': self.dominated,
            'rank': self.rank,
            'crowding_distance': self.crowding_distance
        }


@dataclass
class ParetoFront:
    """Container for Pareto-optimal solutions."""
    points: List[ParetoPoint] = field(default_factory=list)
    objectives: List[Objective] = field(default_factory=list)
    generation: int = 0
    
    def add_point(self, point: ParetoPoint) -> None:
        """Add a point to the Pareto front."""
        self.points.append(point)
        self._update_domination()
    
    def _update_domination(self) -> None:
        """Update domination relationships between points."""
        for i, point1 in enumerate(self.points):
            for j, point2 in enumerate(self.points):
                if i != j:
                    if self._dominates(point1, point2):
                        point2.dominated = True
                    elif self._dominates(point2, point1):
                        point1.dominated = True
    
    def _dominates(self, point1: ParetoPoint, point2: ParetoPoint) -> bool:
        """Check if point1 dominates point2."""
        better_in_any = False
        
        for obj in self.objectives:
            val1 = point1.objectives[obj.name]
            val2 = point2.objectives[obj.name]
            
            if obj.direction == 'maximize':
                if val1 < val2:
                    return False
                elif val1 > val2:
                    better_in_any = True
            else:  # minimize
                if val1 > val2:
                    return False
                elif val1 < val2:
                    better_in_any = True
        
        return better_in_any
    
    def get_non_dominated(self) -> List[ParetoPoint]:
        """Get non-dominated points."""
        return [point for point in self.points if not point.dominated]
    
    def get_ranked_fronts(self) -> List[List[ParetoPoint]]:
        """Get points organized by Pareto rank."""
        fronts = []
        remaining_points = self.points.copy()
        
        rank = 0
        while remaining_points:
            current_front = []
            
            for point in remaining_points[:]:
                point.dominated = False
                
                # Check if point is dominated by any other remaining point
                for other_point in remaining_points:
                    if point != other_point and self._dominates(other_point, point):
                        point.dominated = True
                        break
                
                if not point.dominated:
                    point.rank = rank
                    current_front.append(point)
                    remaining_points.remove(point)
            
            if current_front:
                fronts.append(current_front)
                rank += 1
            else:
                break
        
        return fronts
    
    def calculate_crowding_distance(self, front: List[ParetoPoint]) -> None:
        """Calculate crowding distance for points in a front."""
        if len(front) <= 2:
            for point in front:
                point.crowding_distance = float('inf')
            return
        
        n_objectives = len(self.objectives)
        
        for point in front:
            point.crowding_distance = 0.0
        
        for obj in self.objectives:
            # Sort points by this objective
            sorted_front = sorted(front, key=lambda p: p.objectives[obj.name])
            
            # Set boundary points to infinity
            sorted_front[0].crowding_distance = float('inf')
            sorted_front[-1].crowding_distance = float('inf')
            
            # Calculate range for normalization
            obj_values = [p.objectives[obj.name] for p in sorted_front]
            obj_range = max(obj_values) - min(obj_values)
            
            if obj_range == 0:
                continue
            
            # Add crowding distance contribution
            for i in range(1, len(sorted_front) - 1):
                distance = (sorted_front[i + 1].objectives[obj.name] - 
                           sorted_front[i - 1].objectives[obj.name]) / obj_range
                sorted_front[i].crowding_distance += distance
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'points': [point.to_dict() for point in self.points],
            'objectives': [obj.to_dict() for obj in self.objectives],
            'generation': self.generation
        }


class MultiObjectiveOptimizer:
    """
    Multi-objective optimization using NSGA-II algorithm.
    """
    
    def __init__(self, 
                 objectives: List[Objective],
                 parameter_space: Dict[str, Any],
                 population_size: int = 50,
                 n_generations: int = 100,
                 mutation_rate: float = 0.1,
                 crossover_rate: float = 0.8,
                 random_seed: Optional[int] = None):
        """
        Initialize multi-objective optimizer.
        
        Args:
            objectives: List of objectives to optimize
            parameter_space: Parameter space definition
            population_size: Size of the population
            n_generations: Number of generations
            mutation_rate: Probability of mutation
            crossover_rate: Probability of crossover
            random_seed: Random seed for reproducibility
        """
        self.objectives = objectives
        self.parameter_space = parameter_space
        self.population_size = population_size
        self.n_generations = n_generations
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        
        if random_seed is not None:
            np.random.seed(random_seed)
        
        self.population: List[ParetoPoint] = []
        self.pareto_front = ParetoFront(objectives=objectives)
        self.generation_history: List[Dict[str, Any]] = []
        
        logger.info(f"Initialized multi-objective optimizer with {len(objectives)} objectives")
    
    def optimize(self, 
                 objective_functions: Dict[str, Callable[[Dict[str, Any]], float]]) -> ParetoFront:
        """
        Run multi-objective optimization.
        
        Args:
            objective_functions: Dictionary mapping objective names to evaluation functions
            
        Returns:
            ParetoFront with optimized solutions
        """
        logger.info(f"Starting multi-objective optimization for {self.n_generations} generations")
        
        # Initialize population
        self._initialize_population()
        
        # Evaluate initial population
        self._evaluate_population(objective_functions)
        
        # Evolution loop
        for generation in range(self.n_generations):
            logger.info(f"Generation {generation + 1}/{self.n_generations}")
            
            # Create offspring through selection, crossover, and mutation
            offspring = self._create_offspring()
            
            # Evaluate offspring
            self._evaluate_population(objective_functions, offspring)
            
            # Combine parent and offspring populations
            combined_population = self.population + offspring
            
            # Select new population using NSGA-II selection
            self.population = self._nsga2_selection(combined_population)
            
            # Update Pareto front
            self._update_pareto_front()
            
            # Record generation statistics
            self._record_generation_stats(generation)
        
        logger.info(f"Multi-objective optimization completed")
        logger.info(f"Found {len(self.pareto_front.get_non_dominated())} Pareto-optimal solutions")
        
        return self.pareto_front
    
    def _initialize_population(self) -> None:
        """Initialize random population."""
        self.population = []
        
        for _ in range(self.population_size):
            params = self._random_sample_parameters()
            point = ParetoPoint(
                parameters=params,
                objectives={obj.name: 0.0 for obj in self.objectives}
            )
            self.population.append(point)
    
    def _random_sample_parameters(self) -> Dict[str, Any]:
        """Sample random parameters from parameter space."""
        params = {}
        
        for param_name, param_config in self.parameter_space.items():
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
    
    def _evaluate_population(self, 
                           objective_functions: Dict[str, Callable], 
                           population: Optional[List[ParetoPoint]] = None) -> None:
        """Evaluate population objectives."""
        if population is None:
            population = self.population
        
        for point in population:
            for obj in self.objectives:
                try:
                    score = objective_functions[obj.name](point.parameters)
                    point.objectives[obj.name] = score
                except Exception as e:
                    logger.warning(f"Error evaluating objective {obj.name}: {e}")
                    point.objectives[obj.name] = float('-inf') if obj.direction == 'maximize' else float('inf')
    
    def _create_offspring(self) -> List[ParetoPoint]:
        """Create offspring through selection, crossover, and mutation."""
        offspring = []
        
        while len(offspring) < self.population_size:
            # Tournament selection
            parent1 = self._tournament_selection()
            parent2 = self._tournament_selection()
            
            # Crossover
            if np.random.random() < self.crossover_rate:
                child1, child2 = self._crossover(parent1, parent2)
            else:
                child1 = ParetoPoint(
                    parameters=parent1.parameters.copy(),
                    objectives={obj.name: 0.0 for obj in self.objectives}
                )
                child2 = ParetoPoint(
                    parameters=parent2.parameters.copy(),
                    objectives={obj.name: 0.0 for obj in self.objectives}
                )
            
            # Mutation
            child1 = self._mutate(child1)
            child2 = self._mutate(child2)
            
            offspring.extend([child1, child2])
        
        return offspring[:self.population_size]
    
    def _tournament_selection(self, tournament_size: int = 2) -> ParetoPoint:
        """Tournament selection."""
        tournament = np.random.choice(self.population, tournament_size, replace=False)
        
        # Simple tournament selection based on number of dominated objectives
        best = tournament[0]
        for candidate in tournament[1:]:
            if self._better_than(candidate, best):
                best = candidate
        
        return best
    
    def _better_than(self, point1: ParetoPoint, point2: ParetoPoint) -> bool:
        """Check if point1 is better than point2."""
        return self.pareto_front._dominates(point1, point2)
    
    def _crossover(self, parent1: ParetoPoint, parent2: ParetoPoint) -> Tuple[ParetoPoint, ParetoPoint]:
        """Uniform crossover."""
        child1_params = {}
        child2_params = {}
        
        for param_name in parent1.parameters.keys():
            if np.random.random() < 0.5:
                child1_params[param_name] = parent1.parameters[param_name]
                child2_params[param_name] = parent2.parameters[param_name]
            else:
                child1_params[param_name] = parent2.parameters[param_name]
                child2_params[param_name] = parent1.parameters[param_name]
        
        child1 = ParetoPoint(
            parameters=child1_params,
            objectives={obj.name: 0.0 for obj in self.objectives}
        )
        child2 = ParetoPoint(
            parameters=child2_params,
            objectives={obj.name: 0.0 for obj in self.objectives}
        )
        
        return child1, child2
    
    def _mutate(self, point: ParetoPoint) -> ParetoPoint:
        """Gaussian mutation."""
        if np.random.random() > self.mutation_rate:
            return point
        
        mutated_params = point.parameters.copy()
        
        for param_name, param_config in self.parameter_space.items():
            if np.random.random() < 0.3:  # 30% chance to mutate each parameter
                if isinstance(param_config, dict):
                    param_type = param_config.get('type', 'uniform')
                    
                    if param_type in ['uniform', 'loguniform']:
                        current_value = mutated_params[param_name]
                        noise = np.random.normal(0, 0.1 * abs(current_value))
                        new_value = current_value + noise
                        
                        # Clamp to bounds
                        low = param_config['low']
                        high = param_config['high']
                        new_value = np.clip(new_value, low, high)
                        mutated_params[param_name] = new_value
                        
                    elif param_type == 'int':
                        current_value = mutated_params[param_name]
                        noise = int(np.random.normal(0, 1))
                        new_value = current_value + noise
                        
                        low = param_config['low']
                        high = param_config['high']
                        new_value = np.clip(new_value, low, high)
                        mutated_params[param_name] = int(new_value)
        
        return ParetoPoint(
            parameters=mutated_params,
            objectives={obj.name: 0.0 for obj in self.objectives}
        )
    
    def _nsga2_selection(self, combined_population: List[ParetoPoint]) -> List[ParetoPoint]:
        """NSGA-II selection algorithm."""
        # Calculate Pareto ranks
        fronts = self._calculate_pareto_fronts(combined_population)
        
        # Select new population
        new_population = []
        
        for front in fronts:
            if len(new_population) + len(front) <= self.population_size:
                new_population.extend(front)
            else:
                # Need to select some points from this front
                needed = self.population_size - len(new_population)
                self._calculate_crowding_distance(front)
                
                # Sort by crowding distance (descending)
                front.sort(key=lambda p: p.crowding_distance, reverse=True)
                new_population.extend(front[:needed])
                break
        
        return new_population
    
    def _calculate_pareto_fronts(self, population: List[ParetoPoint]) -> List[List[ParetoPoint]]:
        """Calculate Pareto fronts using non-dominated sorting."""
        fronts = []
        remaining = population.copy()
        
        rank = 0
        while remaining:
            current_front = []
            
            for point in remaining[:]:
                point.dominated = False
                
                for other_point in remaining:
                    if point != other_point and self.pareto_front._dominates(other_point, point):
                        point.dominated = True
                        break
                
                if not point.dominated:
                    point.rank = rank
                    current_front.append(point)
                    remaining.remove(point)
            
            if current_front:
                fronts.append(current_front)
                rank += 1
            else:
                break
        
        return fronts
    
    def _calculate_crowding_distance(self, front: List[ParetoPoint]) -> None:
        """Calculate crowding distance for points in a front."""
        if len(front) <= 2:
            for point in front:
                point.crowding_distance = float('inf')
            return
        
        for point in front:
            point.crowding_distance = 0.0
        
        for obj in self.objectives:
            # Sort points by this objective
            sorted_front = sorted(front, key=lambda p: p.objectives[obj.name])
            
            # Set boundary points to infinity
            sorted_front[0].crowding_distance = float('inf')
            sorted_front[-1].crowding_distance = float('inf')
            
            # Calculate range for normalization
            obj_values = [p.objectives[obj.name] for p in sorted_front]
            obj_range = max(obj_values) - min(obj_values)
            
            if obj_range == 0:
                continue
            
            # Add crowding distance contribution
            for i in range(1, len(sorted_front) - 1):
                distance = (sorted_front[i + 1].objectives[obj.name] - 
                           sorted_front[i - 1].objectives[obj.name]) / obj_range
                sorted_front[i].crowding_distance += distance
    
    def _update_pareto_front(self) -> None:
        """Update the Pareto front with current population."""
        for point in self.population:
            self.pareto_front.add_point(point)
    
    def _record_generation_stats(self, generation: int) -> None:
        """Record generation statistics."""
        non_dominated = self.pareto_front.get_non_dominated()
        
        stats = {
            'generation': generation,
            'population_size': len(self.population),
            'pareto_front_size': len(non_dominated),
            'avg_objectives': {}
        }
        
        for obj in self.objectives:
            values = [point.objectives[obj.name] for point in non_dominated]
            if values:
                stats['avg_objectives'][obj.name] = np.mean(values)
        
        self.generation_history.append(stats)
    
    def get_optimization_summary(self) -> Dict[str, Any]:
        """Get summary of optimization results."""
        non_dominated = self.pareto_front.get_non_dominated()
        
        summary = {
            'total_generations': len(self.generation_history),
            'final_population_size': len(self.population),
            'pareto_front_size': len(non_dominated),
            'objectives': [obj.to_dict() for obj in self.objectives],
            'generation_history': self.generation_history
        }
        
        # Objective statistics
        for obj in self.objectives:
            values = [point.objectives[obj.name] for point in non_dominated]
            if values:
                summary[f'{obj.name}_stats'] = {
                    'min': np.min(values),
                    'max': np.max(values),
                    'mean': np.mean(values),
                    'std': np.std(values)
                }
        
        return summary
