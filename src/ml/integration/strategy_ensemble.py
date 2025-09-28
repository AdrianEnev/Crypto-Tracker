"""
Strategy Ensemble for combining multiple ML-enhanced strategies.
Provides intelligent ensemble methods for strategy combination.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Union, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from .ml_enhanced_strategy import MLEnhancedStrategy, MLStrategyConfig


class EnsembleMethod(Enum):
    """Available ensemble methods."""
    WEIGHTED_AVERAGE = "weighted_average"
    VOTING = "voting"
    STACKING = "stacking"
    DYNAMIC_WEIGHT = "dynamic_weight"
    PERFORMANCE_BASED = "performance_based"
    REGIME_BASED = "regime_based"


@dataclass
class EnsembleConfig:
    """Configuration for strategy ensemble."""
    ensemble_name: str
    strategies: List[MLEnhancedStrategy]
    ensemble_method: EnsembleMethod = EnsembleMethod.WEIGHTED_AVERAGE
    initial_weights: Optional[List[float]] = None
    rebalancing_frequency: int = 100  # Rebalance every N signals
    performance_window: int = 50  # Window for performance calculation
    min_confidence_threshold: float = 0.3  # Minimum confidence for signal inclusion
    enable_dynamic_reweighting: bool = True
    enable_regime_aware_ensemble: bool = True
    fallback_strategy: Optional[str] = None  # Fallback strategy name
    
    def __post_init__(self):
        """Initialize ensemble configuration."""
        if self.initial_weights is None:
            # Equal weights by default
            self.initial_weights = [1.0 / len(self.strategies)] * len(self.strategies)
        
        if len(self.initial_weights) != len(self.strategies):
            raise ValueError("Number of weights must match number of strategies")
        
        # Normalize weights
        weight_sum = sum(self.initial_weights)
        self.initial_weights = [w / weight_sum for w in self.initial_weights]


class StrategyEnsemble:
    """
    Strategy Ensemble for combining multiple ML-enhanced strategies.
    
    Provides various ensemble methods for intelligent strategy combination:
    - Weighted averaging based on performance
    - Voting mechanisms
    - Dynamic weight adjustment
    - Regime-aware ensemble selection
    """
    
    def __init__(self, config: EnsembleConfig):
        self.config = config
        self.ensemble_name = config.ensemble_name
        self.strategies = config.strategies
        self.ensemble_method = config.ensemble_method
        
        # State tracking
        self.current_weights = config.initial_weights.copy()
        self.performance_history = {strategy.strategy_name: [] for strategy in self.strategies}
        self.signal_history = []
        self.ensemble_signals = []
        
        # Performance metrics
        self.ensemble_metrics = {}
        self.strategy_metrics = {strategy.strategy_name: {} for strategy in self.strategies}
        
        # Regime tracking
        self.current_regime = None
        self.regime_performance = {}
        
    def train_ensemble(self, 
                      historical_data: pd.DataFrame,
                      training_periods: int = 1000,
                      validation_periods: int = 200) -> Dict[str, Any]:
        """
        Train all strategies in the ensemble.
        
        Args:
            historical_data: Historical market data
            training_periods: Number of periods for training
            validation_periods: Number of periods for validation
            
        Returns:
            Dictionary with training results for each strategy
        """
        print(f"Training ensemble '{self.ensemble_name}' with {len(self.strategies)} strategies...")
        
        training_results = {}
        
        for strategy in self.strategies:
            print(f"Training strategy: {strategy.strategy_name}")
            try:
                results = strategy.train_ml_models(
                    historical_data, training_periods, validation_periods
                )
                training_results[strategy.strategy_name] = results
                print(f"✅ {strategy.strategy_name} trained successfully")
            except Exception as e:
                print(f"❌ {strategy.strategy_name} training failed: {e}")
                training_results[strategy.strategy_name] = {'error': str(e)}
        
        print(f"Ensemble training completed for '{self.ensemble_name}'")
        return training_results
    
    def generate_ensemble_signal(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate ensemble signal by combining individual strategy signals.
        
        Args:
            market_data: Current market data
            
        Returns:
            Ensemble trading signal
        """
        # Generate signals from all strategies
        strategy_signals = {}
        signal_weights = []
        
        for i, strategy in enumerate(self.strategies):
            try:
                signal = strategy.generate_signal(market_data)
                strategy_signals[strategy.strategy_name] = signal
                
                # Calculate signal weight based on method
                weight = self._calculate_signal_weight(strategy, signal, i)
                signal_weights.append(weight)
                
            except Exception as e:
                print(f"Strategy {strategy.strategy_name} failed: {e}")
                # Use fallback signal
                fallback_signal = {
                    'action': 'hold',
                    'strength': 0.0,
                    'timestamp': datetime.now(timezone.utc),
                    'error': str(e)
                }
                strategy_signals[strategy.strategy_name] = fallback_signal
                signal_weights.append(0.0)  # Zero weight for failed strategies
        
        # Normalize weights
        if sum(signal_weights) > 0:
            signal_weights = [w / sum(signal_weights) for w in signal_weights]
        else:
            signal_weights = [1.0 / len(self.strategies)] * len(self.strategies)
        
        # Combine signals based on ensemble method
        ensemble_signal = self._combine_signals(strategy_signals, signal_weights)
        
        # Store signal history
        self.signal_history.append({
            'timestamp': ensemble_signal['timestamp'],
            'strategy_signals': strategy_signals,
            'weights': signal_weights,
            'ensemble_signal': ensemble_signal
        })
        
        # Update performance tracking
        self._update_performance_tracking(strategy_signals, signal_weights)
        
        # Rebalance weights if needed
        if (len(self.signal_history) % self.config.rebalancing_frequency == 0 and 
            self.config.enable_dynamic_reweighting):
            self._rebalance_weights()
        
        return ensemble_signal
    
    def _calculate_signal_weight(self, 
                               strategy: MLEnhancedStrategy, 
                               signal: Dict[str, Any], 
                               strategy_index: int) -> float:
        """Calculate weight for a strategy signal based on ensemble method."""
        
        if self.ensemble_method == EnsembleMethod.WEIGHTED_AVERAGE:
            # Use current ensemble weights
            return self.current_weights[strategy_index]
        
        elif self.ensemble_method == EnsembleMethod.PERFORMANCE_BASED:
            # Weight based on recent performance
            recent_performance = self._get_recent_performance(strategy.strategy_name)
            return max(0.1, recent_performance)  # Minimum weight of 0.1
        
        elif self.ensemble_method == EnsembleMethod.REGIME_BASED:
            # Weight based on regime performance
            if self.current_regime:
                regime_perf = self.regime_performance.get(
                    (strategy.strategy_name, self.current_regime), 0.5
                )
                return max(0.1, regime_perf)
            else:
                return self.current_weights[strategy_index]
        
        elif self.ensemble_method == EnsembleMethod.DYNAMIC_WEIGHT:
            # Dynamic weight based on signal confidence and recent performance
            base_weight = self.current_weights[strategy_index]
            confidence_multiplier = signal.get('prediction_confidence', 0.5)
            performance_multiplier = self._get_recent_performance(strategy.strategy_name)
            
            dynamic_weight = base_weight * confidence_multiplier * performance_multiplier
            return max(0.05, dynamic_weight)  # Minimum weight of 0.05
        
        else:
            # Default to equal weights
            return 1.0 / len(self.strategies)
    
    def _combine_signals(self, 
                        strategy_signals: Dict[str, Dict[str, Any]], 
                        weights: List[float]) -> Dict[str, Any]:
        """Combine individual strategy signals into ensemble signal."""
        
        if self.ensemble_method == EnsembleMethod.VOTING:
            return self._voting_combination(strategy_signals, weights)
        
        else:
            return self._weighted_combination(strategy_signals, weights)
    
    def _voting_combination(self, 
                          strategy_signals: Dict[str, Dict[str, Any]], 
                          weights: List[float]) -> Dict[str, Any]:
        """Combine signals using voting mechanism."""
        
        # Count votes for each action
        votes = {'buy': 0.0, 'sell': 0.0, 'hold': 0.0}
        
        for i, (strategy_name, signal) in enumerate(strategy_signals.items()):
            action = signal.get('action', 'hold')
            strength = signal.get('strength', 0.0)
            weight = weights[i]
            
            # Weighted voting
            votes[action] += strength * weight
        
        # Select action with highest vote
        ensemble_action = max(votes.keys(), key=lambda k: votes[k])
        
        # Calculate ensemble strength
        if ensemble_action == 'hold':
            ensemble_strength = 0.0
        else:
            ensemble_strength = votes[ensemble_action] / sum(votes.values()) if sum(votes.values()) > 0 else 0.0
        
        return {
            'action': ensemble_action,
            'strength': ensemble_strength,
            'timestamp': datetime.now(timezone.utc),
            'ensemble_method': 'voting',
            'votes': votes,
            'strategy_count': len(strategy_signals),
            'ensemble_name': self.ensemble_name
        }
    
    def _weighted_combination(self, 
                            strategy_signals: Dict[str, Dict[str, Any]], 
                            weights: List[float]) -> Dict[str, Any]:
        """Combine signals using weighted averaging."""
        
        # Convert actions to numerical values for averaging
        action_values = {'buy': 1.0, 'sell': -1.0, 'hold': 0.0}
        
        weighted_action_sum = 0.0
        weighted_strength_sum = 0.0
        total_weight = 0.0
        
        strategy_details = []
        
        for i, (strategy_name, signal) in enumerate(strategy_signals.items()):
            action = signal.get('action', 'hold')
            strength = signal.get('strength', 0.0)
            weight = weights[i]
            
            if weight > 0:
                weighted_action_sum += action_values[action] * strength * weight
                weighted_strength_sum += strength * weight
                total_weight += weight
                
                strategy_details.append({
                    'strategy': strategy_name,
                    'action': action,
                    'strength': strength,
                    'weight': weight,
                    'contribution': action_values[action] * strength * weight
                })
        
        # Determine ensemble action
        if total_weight > 0:
            avg_action_value = weighted_action_sum / total_weight
            avg_strength = weighted_strength_sum / total_weight
            
            if avg_action_value > 0.1:
                ensemble_action = 'buy'
                ensemble_strength = min(1.0, avg_strength)
            elif avg_action_value < -0.1:
                ensemble_action = 'sell'
                ensemble_strength = min(1.0, avg_strength)
            else:
                ensemble_action = 'hold'
                ensemble_strength = 0.0
        else:
            ensemble_action = 'hold'
            ensemble_strength = 0.0
        
        return {
            'action': ensemble_action,
            'strength': ensemble_strength,
            'timestamp': datetime.now(timezone.utc),
            'ensemble_method': self.ensemble_method.value,
            'strategy_details': strategy_details,
            'total_weight': total_weight,
            'avg_action_value': avg_action_value if total_weight > 0 else 0.0,
            'ensemble_name': self.ensemble_name
        }
    
    def _get_recent_performance(self, strategy_name: str) -> float:
        """Get recent performance for a strategy."""
        performance_history = self.performance_history.get(strategy_name, [])
        
        if not performance_history:
            return 0.5  # Neutral performance
        
        # Use recent performance window
        recent_performance = performance_history[-self.config.performance_window:]
        
        if not recent_performance:
            return 0.5
        
        # Calculate average performance (assuming values between 0 and 1)
        return np.mean(recent_performance)
    
    def _update_performance_tracking(self, 
                                   strategy_signals: Dict[str, Dict[str, Any]], 
                                   weights: List[float]):
        """Update performance tracking for all strategies."""
        # This is a simplified implementation
        # In practice, you would track actual returns and calculate performance metrics
        
        for i, (strategy_name, signal) in enumerate(strategy_signals.items()):
            # Mock performance calculation based on signal quality
            signal_quality = signal.get('strength', 0.0)
            confidence = signal.get('prediction_confidence', 0.5)
            ml_enhanced = signal.get('ml_enhanced', False)
            
            # Calculate performance score
            performance_score = 0.5  # Base score
            
            if ml_enhanced:
                performance_score += 0.2  # Bonus for ML enhancement
            
            performance_score += signal_quality * 0.3  # Signal strength contribution
            performance_score += confidence * 0.2  # Confidence contribution
            
            # Clamp between 0 and 1
            performance_score = max(0.0, min(1.0, performance_score))
            
            self.performance_history[strategy_name].append(performance_score)
            
            # Keep only recent history
            if len(self.performance_history[strategy_name]) > self.config.performance_window * 2:
                self.performance_history[strategy_name] = self.performance_history[strategy_name][-self.config.performance_window:]
    
    def _rebalance_weights(self):
        """Rebalance strategy weights based on performance."""
        if not self.config.enable_dynamic_reweighting:
            return
        
        print(f"Rebalancing ensemble weights for '{self.ensemble_name}'...")
        
        # Calculate performance-based weights
        performance_weights = []
        
        for strategy in self.strategies:
            recent_performance = self._get_recent_performance(strategy.strategy_name)
            performance_weights.append(recent_performance)
        
        # Normalize weights
        if sum(performance_weights) > 0:
            performance_weights = [w / sum(performance_weights) for w in performance_weights]
        else:
            performance_weights = [1.0 / len(self.strategies)] * len(self.strategies)
        
        # Smooth weight changes (avoid drastic changes)
        smoothing_factor = 0.3
        for i in range(len(self.current_weights)):
            self.current_weights[i] = (
                smoothing_factor * performance_weights[i] + 
                (1 - smoothing_factor) * self.current_weights[i]
            )
        
        # Renormalize
        weight_sum = sum(self.current_weights)
        self.current_weights = [w / weight_sum for w in self.current_weights]
        
        print(f"New weights: {dict(zip([s.strategy_name for s in self.strategies], self.current_weights))}")
    
    def get_ensemble_insights(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Get comprehensive insights from the ensemble."""
        insights = {
            'timestamp': datetime.now(timezone.utc),
            'ensemble_name': self.ensemble_name,
            'ensemble_method': self.ensemble_method.value,
            'strategy_count': len(self.strategies),
            'current_weights': dict(zip([s.strategy_name for s in self.strategies], self.current_weights)),
            'current_regime': self.current_regime
        }
        
        # Get insights from each strategy
        strategy_insights = {}
        for strategy in self.strategies:
            try:
                strategy_insights[strategy.strategy_name] = strategy.get_ml_insights(market_data)
            except Exception as e:
                strategy_insights[strategy.strategy_name] = {'error': str(e)}
        
        insights['strategy_insights'] = strategy_insights
        
        # Performance summary
        performance_summary = {}
        for strategy in self.strategies:
            recent_performance = self._get_recent_performance(strategy.strategy_name)
            performance_summary[strategy.strategy_name] = {
                'recent_performance': recent_performance,
                'signal_count': len(self.performance_history[strategy.strategy_name])
            }
        
        insights['performance_summary'] = performance_summary
        
        return insights
    
    def get_ensemble_metrics(self) -> Dict[str, Any]:
        """Get comprehensive ensemble performance metrics."""
        if not self.signal_history:
            return {}
        
        # Calculate ensemble metrics
        total_signals = len(self.signal_history)
        
        # Signal distribution
        action_distribution = {}
        for signal_record in self.signal_history:
            action = signal_record['ensemble_signal']['action']
            action_distribution[action] = action_distribution.get(action, 0) + 1
        
        # Average strength
        avg_strength = np.mean([
            signal_record['ensemble_signal']['strength'] 
            for signal_record in self.signal_history
        ])
        
        # Strategy participation
        strategy_participation = {}
        for strategy in self.strategies:
            participation_count = sum(
                1 for signal_record in self.signal_history
                if strategy.strategy_name in signal_record['strategy_signals']
            )
            strategy_participation[strategy.strategy_name] = participation_count / total_signals
        
        # Weight stability
        if len(self.signal_history) > 1:
            weight_changes = []
            for i in range(1, len(self.signal_history)):
                prev_weights = self.signal_history[i-1]['weights']
                curr_weights = self.signal_history[i]['weights']
                weight_change = np.mean([abs(curr_weights[j] - prev_weights[j]) for j in range(len(curr_weights))])
                weight_changes.append(weight_change)
            
            avg_weight_change = np.mean(weight_changes)
        else:
            avg_weight_change = 0.0
        
        return {
            'total_signals': total_signals,
            'action_distribution': action_distribution,
            'average_strength': avg_strength,
            'strategy_participation': strategy_participation,
            'weight_stability': avg_weight_change,
            'ensemble_method': self.ensemble_method.value,
            'current_weights': dict(zip([s.strategy_name for s in self.strategies], self.current_weights)),
            'rebalancing_frequency': self.config.rebalancing_frequency,
            'performance_window': self.config.performance_window
        }
    
    def reset_ensemble_state(self):
        """Reset ensemble state."""
        self.current_weights = self.config.initial_weights.copy()
        self.performance_history = {strategy.strategy_name: [] for strategy in self.strategies}
        self.signal_history = []
        self.ensemble_signals = []
        self.ensemble_metrics = {}
        self.strategy_metrics = {strategy.strategy_name: {} for strategy in self.strategies}
        self.current_regime = None
        self.regime_performance = {}
        
        print(f"Ensemble '{self.ensemble_name}' state reset")
