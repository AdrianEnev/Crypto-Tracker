"""
ML Strategy Manager for coordinating and managing ML-enhanced trading strategies.
Provides centralized management, monitoring, and optimization of ML strategies.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Union, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path

from .ml_enhanced_strategy import MLEnhancedStrategy, MLStrategyConfig
from .strategy_ensemble import StrategyEnsemble, EnsembleConfig, EnsembleMethod


@dataclass
class MLStrategyManagerConfig:
    """Configuration for ML Strategy Manager."""
    manager_name: str
    strategies: List[MLStrategyConfig]
    ensembles: List[EnsembleConfig] = field(default_factory=list)
    enable_auto_retraining: bool = True
    retraining_frequency: int = 1000  # Retrain every N signals
    performance_monitoring: bool = True
    enable_strategy_switching: bool = True
    model_persistence_path: str = "models/"
    enable_backup_strategies: bool = True
    backup_frequency: int = 100  # Backup every N signals
    enable_performance_alerts: bool = True
    performance_threshold: float = 0.3  # Alert if performance drops below this
    enable_regime_switching: bool = True
    regime_switching_threshold: float = 0.7  # Confidence threshold for regime switching


class MLStrategyManager:
    """
    ML Strategy Manager for coordinating and managing ML-enhanced trading strategies.
    
    Provides:
    - Centralized strategy management
    - Automatic model retraining
    - Performance monitoring and alerts
    - Strategy ensemble coordination
    - Model persistence and backup
    - Regime-aware strategy switching
    """
    
    def __init__(self, config: MLStrategyManagerConfig):
        self.config = config
        self.manager_name = config.manager_name
        
        # Initialize strategies
        self.strategies: Dict[str, MLEnhancedStrategy] = {}
        self.ensembles: Dict[str, StrategyEnsemble] = {}
        
        # State tracking
        self.total_signals = 0
        self.last_retraining = datetime.now(timezone.utc)
        self.last_backup = datetime.now(timezone.utc)
        self.active_strategy = None
        self.current_regime = None
        
        # Performance tracking
        self.performance_history: Dict[str, List[float]] = {}
        self.regime_performance: Dict[Tuple[str, str], List[float]] = {}
        self.alert_history: List[Dict[str, Any]] = []
        
        # Model persistence
        self.model_path = Path(config.model_persistence_path)
        self.model_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize strategies and ensembles
        self._initialize_strategies()
        self._initialize_ensembles()
        
        # Set active strategy
        if self.strategies:
            self.active_strategy = list(self.strategies.keys())[0]
        
    def _initialize_strategies(self):
        """Initialize all ML-enhanced strategies."""
        print(f"Initializing {len(self.config.strategies)} strategies...")
        
        for strategy_config in self.config.strategies:
            try:
                strategy = MLEnhancedStrategy(strategy_config)
                self.strategies[strategy.strategy_name] = strategy
                self.performance_history[strategy.strategy_name] = []
                print(f"✅ Initialized strategy: {strategy.strategy_name}")
            except Exception as e:
                print(f"❌ Failed to initialize strategy {strategy_config.strategy_name}: {e}")
        
        print(f"Initialized {len(self.strategies)} strategies successfully")
    
    def _initialize_ensembles(self):
        """Initialize all strategy ensembles."""
        if not self.config.ensembles:
            return
        
        print(f"Initializing {len(self.config.ensembles)} ensembles...")
        
        for ensemble_config in self.config.ensembles:
            try:
                # Get strategy instances for ensemble
                ensemble_strategies = []
                for strategy_config in ensemble_config.strategies:
                    if strategy_config.strategy_name in self.strategies:
                        ensemble_strategies.append(self.strategies[strategy_config.strategy_name])
                    else:
                        print(f"⚠️ Strategy {strategy_config.strategy_name} not found for ensemble {ensemble_config.ensemble_name}")
                
                if ensemble_strategies:
                    # Update ensemble config with actual strategy instances
                    ensemble_config.strategies = ensemble_strategies
                    ensemble = StrategyEnsemble(ensemble_config)
                    self.ensembles[ensemble.ensemble_name] = ensemble
                    print(f"✅ Initialized ensemble: {ensemble.ensemble_name}")
                else:
                    print(f"❌ No valid strategies found for ensemble {ensemble_config.ensemble_name}")
                    
            except Exception as e:
                print(f"❌ Failed to initialize ensemble {ensemble_config.ensemble_name}: {e}")
        
        print(f"Initialized {len(self.ensembles)} ensembles successfully")
    
    def train_all_models(self, 
                        historical_data: pd.DataFrame,
                        training_periods: int = 1000,
                        validation_periods: int = 200) -> Dict[str, Any]:
        """
        Train all ML models for all strategies and ensembles.
        
        Args:
            historical_data: Historical market data
            training_periods: Number of periods for training
            validation_periods: Number of periods for validation
            
        Returns:
            Dictionary with training results for all strategies and ensembles
        """
        print(f"Training all models for manager '{self.manager_name}'...")
        
        training_results = {
            'strategies': {},
            'ensembles': {},
            'training_timestamp': datetime.now(timezone.utc).isoformat(),
            'training_periods': training_periods,
            'validation_periods': validation_periods
        }
        
        # Train individual strategies
        for strategy_name, strategy in self.strategies.items():
            print(f"Training strategy: {strategy_name}")
            try:
                results = strategy.train_ml_models(
                    historical_data, training_periods, validation_periods
                )
                training_results['strategies'][strategy_name] = results
                print(f"✅ {strategy_name} trained successfully")
            except Exception as e:
                print(f"❌ {strategy_name} training failed: {e}")
                training_results['strategies'][strategy_name] = {'error': str(e)}
        
        # Train ensembles
        for ensemble_name, ensemble in self.ensembles.items():
            print(f"Training ensemble: {ensemble_name}")
            try:
                results = ensemble.train_ensemble(
                    historical_data, training_periods, validation_periods
                )
                training_results['ensembles'][ensemble_name] = results
                print(f"✅ {ensemble_name} trained successfully")
            except Exception as e:
                print(f"❌ {ensemble_name} training failed: {e}")
                training_results['ensembles'][ensemble_name] = {'error': str(e)}
        
        # Save training results
        self._save_training_results(training_results)
        
        print(f"Training completed for manager '{self.manager_name}'")
        return training_results
    
    def generate_signal(self, 
                       market_data: pd.DataFrame,
                       strategy_name: Optional[str] = None,
                       ensemble_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate trading signal from specified strategy or ensemble.
        
        Args:
            market_data: Current market data
            strategy_name: Name of strategy to use (if None, uses active strategy)
            ensemble_name: Name of ensemble to use (overrides strategy)
            
        Returns:
            Trading signal with manager metadata
        """
        self.total_signals += 1
        
        try:
            # Determine which strategy/ensemble to use
            if ensemble_name and ensemble_name in self.ensembles:
                # Use ensemble
                signal = self.ensembles[ensemble_name].generate_ensemble_signal(market_data)
                signal['source_type'] = 'ensemble'
                signal['source_name'] = ensemble_name
                
            elif strategy_name and strategy_name in self.strategies:
                # Use specified strategy
                signal = self.strategies[strategy_name].generate_signal(market_data)
                signal['source_type'] = 'strategy'
                signal['source_name'] = strategy_name
                
            elif self.active_strategy and self.active_strategy in self.strategies:
                # Use active strategy
                signal = self.strategies[self.active_strategy].generate_signal(market_data)
                signal['source_type'] = 'strategy'
                signal['source_name'] = self.active_strategy
                
            else:
                # Fallback to first available strategy
                if self.strategies:
                    first_strategy = list(self.strategies.keys())[0]
                    signal = self.strategies[first_strategy].generate_signal(market_data)
                    signal['source_type'] = 'strategy'
                    signal['source_name'] = first_strategy
                else:
                    # No strategies available
                    signal = {
                        'action': 'hold',
                        'strength': 0.0,
                        'timestamp': datetime.now(timezone.utc),
                        'source_type': 'fallback',
                        'source_name': 'none',
                        'error': 'No strategies available'
                    }
            
            # Add manager metadata
            signal.update({
                'manager_name': self.manager_name,
                'signal_number': self.total_signals,
                'active_strategy': self.active_strategy,
                'current_regime': self.current_regime,
                'total_strategies': len(self.strategies),
                'total_ensembles': len(self.ensembles)
            })
            
            # Update performance tracking
            self._update_performance_tracking(signal)
            
            # Check for retraining
            if (self.config.enable_auto_retraining and 
                self.total_signals % self.config.retraining_frequency == 0):
                self._schedule_retraining(market_data)
            
            # Check for backup
            if (self.config.enable_backup_strategies and 
                self.total_signals % self.config.backup_frequency == 0):
                self._backup_models()
            
            # Check for performance alerts
            if self.config.enable_performance_alerts:
                self._check_performance_alerts()
            
            return signal
            
        except Exception as e:
            print(f"Signal generation failed: {e}")
            return {
                'action': 'hold',
                'strength': 0.0,
                'timestamp': datetime.now(timezone.utc),
                'source_type': 'error',
                'source_name': 'none',
                'error': str(e),
                'manager_name': self.manager_name,
                'signal_number': self.total_signals
            }
    
    def switch_strategy(self, new_strategy_name: str) -> bool:
        """
        Switch to a different strategy.
        
        Args:
            new_strategy_name: Name of strategy to switch to
            
        Returns:
            True if switch was successful, False otherwise
        """
        if new_strategy_name not in self.strategies:
            print(f"Strategy {new_strategy_name} not found")
            return False
        
        old_strategy = self.active_strategy
        self.active_strategy = new_strategy_name
        
        print(f"Switched from {old_strategy} to {new_strategy_name}")
        
        # Log strategy switch
        self.alert_history.append({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'type': 'strategy_switch',
            'old_strategy': old_strategy,
            'new_strategy': new_strategy_name,
            'reason': 'manual_switch'
        })
        
        return True
    
    def switch_to_regime_strategy(self, market_data: pd.DataFrame) -> bool:
        """
        Automatically switch strategy based on detected market regime.
        
        Args:
            market_data: Current market data
            
        Returns:
            True if switch was successful, False otherwise
        """
        if not self.config.enable_regime_switching:
            return False
        
        # Get regime information from strategies
        regime_info = self._get_regime_consensus(market_data)
        
        if not regime_info:
            return False
        
        regime, confidence = regime_info
        
        if confidence < self.config.regime_switching_threshold:
            return False
        
        # Find best strategy for this regime
        best_strategy = self._get_best_strategy_for_regime(regime)
        
        if best_strategy and best_strategy != self.active_strategy:
            return self.switch_strategy(best_strategy)
        
        return False
    
    def _get_regime_consensus(self, market_data: pd.DataFrame) -> Optional[Tuple[str, float]]:
        """Get regime consensus from all strategies."""
        regime_predictions = []
        
        for strategy in self.strategies.values():
            try:
                insights = strategy.get_ml_insights(market_data)
                if 'regime_prediction' in insights:
                    regime_info = insights['regime_prediction']
                    regime_predictions.append((
                        regime_info['regime'],
                        max(regime_info['probabilities'].values())
                    ))
            except Exception as e:
                print(f"Error getting regime from {strategy.strategy_name}: {e}")
        
        if not regime_predictions:
            return None
        
        # Get consensus regime
        regime_counts = {}
        for regime, confidence in regime_predictions:
            regime_counts[regime] = regime_counts.get(regime, 0) + confidence
        
        if regime_counts:
            consensus_regime = max(regime_counts.keys(), key=lambda k: regime_counts[k])
            consensus_confidence = regime_counts[consensus_regime] / len(regime_predictions)
            return consensus_regime, consensus_confidence
        
        return None
    
    def _get_best_strategy_for_regime(self, regime: str) -> Optional[str]:
        """Get the best performing strategy for a given regime."""
        if not self.regime_performance:
            return None
        
        regime_performances = {}
        for (strategy_name, strategy_regime), performances in self.regime_performance.items():
            if strategy_regime == regime:
                regime_performances[strategy_name] = np.mean(performances[-50:]) if performances else 0.0
        
        if regime_performances:
            return max(regime_performances.keys(), key=lambda k: regime_performances[k])
        
        return None
    
    def _update_performance_tracking(self, signal: Dict[str, Any]):
        """Update performance tracking for all strategies."""
        # This is a simplified implementation
        # In practice, you would track actual returns and calculate performance metrics
        
        source_name = signal.get('source_name', 'unknown')
        source_type = signal.get('source_type', 'unknown')
        
        # Calculate performance score based on signal quality
        signal_quality = signal.get('strength', 0.0)
        confidence = signal.get('prediction_confidence', 0.5)
        ml_enhanced = signal.get('ml_enhanced', False)
        
        performance_score = 0.5  # Base score
        performance_score += signal_quality * 0.3
        performance_score += confidence * 0.2
        if ml_enhanced:
            performance_score += 0.1
        
        performance_score = max(0.0, min(1.0, performance_score))
        
        # Track performance
        if source_type == 'strategy' and source_name in self.performance_history:
            self.performance_history[source_name].append(performance_score)
            
            # Keep only recent history
            if len(self.performance_history[source_name]) > 1000:
                self.performance_history[source_name] = self.performance_history[source_name][-500:]
        
        # Track regime performance
        if self.current_regime:
            regime_key = (source_name, self.current_regime)
            if regime_key not in self.regime_performance:
                self.regime_performance[regime_key] = []
            
            self.regime_performance[regime_key].append(performance_score)
            
            # Keep only recent regime performance
            if len(self.regime_performance[regime_key]) > 200:
                self.regime_performance[regime_key] = self.regime_performance[regime_key][-100:]
    
    def _check_performance_alerts(self):
        """Check for performance alerts and trigger if necessary."""
        for strategy_name, performance_history in self.performance_history.items():
            if len(performance_history) >= 50:  # Need sufficient history
                recent_performance = np.mean(performance_history[-50:])
                
                if recent_performance < self.config.performance_threshold:
                    self._trigger_performance_alert(strategy_name, recent_performance)
    
    def _trigger_performance_alert(self, strategy_name: str, performance: float):
        """Trigger a performance alert."""
        alert = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'type': 'performance_alert',
            'strategy_name': strategy_name,
            'performance': performance,
            'threshold': self.config.performance_threshold,
            'action': 'consider_strategy_switch'
        }
        
        self.alert_history.append(alert)
        print(f"🚨 Performance Alert: {strategy_name} performance {performance:.3f} below threshold {self.config.performance_threshold}")
    
    def _schedule_retraining(self, market_data: pd.DataFrame):
        """Schedule model retraining."""
        print(f"🔄 Scheduling retraining (signal #{self.total_signals})")
        
        # In a real implementation, you would schedule this asynchronously
        # For now, we just log it
        self.alert_history.append({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'type': 'retraining_scheduled',
            'signal_number': self.total_signals,
            'reason': 'scheduled_retraining'
        })
    
    def _backup_models(self):
        """Backup current models."""
        print(f"💾 Creating model backup (signal #{self.total_signals})")
        
        backup_timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_path = self.model_path / f"backup_{backup_timestamp}"
        backup_path.mkdir(exist_ok=True)
        
        # Save strategy states
        for strategy_name, strategy in self.strategies.items():
            try:
                strategy_file = backup_path / f"{strategy_name}_state.json"
                strategy_info = strategy.get_model_info()
                with open(strategy_file, 'w') as f:
                    json.dump(strategy_info, f, indent=2, default=str)
            except Exception as e:
                print(f"Failed to backup {strategy_name}: {e}")
        
        # Save ensemble states
        for ensemble_name, ensemble in self.ensembles.items():
            try:
                ensemble_file = backup_path / f"{ensemble_name}_state.json"
                ensemble_metrics = ensemble.get_ensemble_metrics()
                with open(ensemble_file, 'w') as f:
                    json.dump(ensemble_metrics, f, indent=2, default=str)
            except Exception as e:
                print(f"Failed to backup {ensemble_name}: {e}")
        
        self.last_backup = datetime.now(timezone.utc)
        
        self.alert_history.append({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'type': 'model_backup',
            'backup_path': str(backup_path),
            'signal_number': self.total_signals
        })
    
    def _save_training_results(self, training_results: Dict[str, Any]):
        """Save training results to file."""
        results_file = self.model_path / f"training_results_{self.manager_name}.json"
        
        try:
            with open(results_file, 'w') as f:
                json.dump(training_results, f, indent=2, default=str)
        except Exception as e:
            print(f"Failed to save training results: {e}")
    
    def get_manager_status(self) -> Dict[str, Any]:
        """Get comprehensive manager status."""
        return {
            'manager_name': self.manager_name,
            'total_signals': self.total_signals,
            'active_strategy': self.active_strategy,
            'current_regime': self.current_regime,
            'strategies': list(self.strategies.keys()),
            'ensembles': list(self.ensembles.keys()),
            'last_retraining': self.last_retraining.isoformat(),
            'last_backup': self.last_backup.isoformat(),
            'auto_retraining': self.config.enable_auto_retraining,
            'performance_monitoring': self.config.performance_monitoring,
            'regime_switching': self.config.enable_regime_switching
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for all strategies."""
        summary = {
            'total_signals': self.total_signals,
            'strategies': {},
            'ensembles': {},
            'alerts': len(self.alert_history)
        }
        
        # Strategy performance
        for strategy_name, performance_history in self.performance_history.items():
            if performance_history:
                summary['strategies'][strategy_name] = {
                    'recent_performance': np.mean(performance_history[-50:]) if len(performance_history) >= 50 else np.mean(performance_history),
                    'total_signals': len(performance_history),
                    'performance_trend': np.mean(performance_history[-10:]) - np.mean(performance_history[-50:-10]) if len(performance_history) >= 50 else 0.0
                }
        
        # Ensemble performance
        for ensemble_name, ensemble in self.ensembles.items():
            try:
                ensemble_metrics = ensemble.get_ensemble_metrics()
                summary['ensembles'][ensemble_name] = ensemble_metrics
            except Exception as e:
                summary['ensembles'][ensemble_name] = {'error': str(e)}
        
        return summary
    
    def get_recent_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent alerts."""
        return self.alert_history[-limit:] if self.alert_history else []
    
    def reset_manager_state(self):
        """Reset manager state."""
        self.total_signals = 0
        self.last_retraining = datetime.now(timezone.utc)
        self.last_backup = datetime.now(timezone.utc)
        self.active_strategy = None
        self.current_regime = None
        self.performance_history = {name: [] for name in self.strategies.keys()}
        self.regime_performance = {}
        self.alert_history = []
        
        # Reset strategy states
        for strategy in self.strategies.values():
            strategy.reset_state()
        
        # Reset ensemble states
        for ensemble in self.ensembles.values():
            ensemble.reset_ensemble_state()
        
        print(f"Manager '{self.manager_name}' state reset")
