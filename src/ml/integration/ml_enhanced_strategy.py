"""
ML-Enhanced Strategy Wrapper.
Integrates ML models with existing trading strategies to provide intelligent enhancement.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Union, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..models import ParameterOptimizer, RegimeDetector, SignalEnhancer, PricePredictor
from ..feature_engineering import FeaturePipeline
from ...strategies.base import BaseStrategy


@dataclass
class MLStrategyConfig:
    """Configuration for ML-enhanced strategy."""
    strategy_name: str
    base_strategy: Any  # Instance of base strategy
    enable_parameter_optimization: bool = True
    enable_regime_detection: bool = True
    enable_signal_enhancement: bool = True
    enable_price_prediction: bool = True
    parameter_optimization_frequency: int = 100  # Optimize every N signals
    regime_detection_frequency: int = 10  # Check regime every N signals
    signal_enhancement_threshold: float = 0.5  # Minimum quality for enhancement
    prediction_confidence_threshold: float = 0.6  # Minimum confidence for predictions
    fallback_to_base: bool = True  # Fall back to base strategy if ML fails
    ml_models_config: Dict[str, Dict] = field(default_factory=dict)
    
    def __post_init__(self):
        """Set default ML model configurations."""
        if not self.ml_models_config:
            self.ml_models_config = {
                'parameter_optimizer': {
                    'optimization_method': 'xgboost',
                    'parameter_ranges': {},
                    'baseline_parameters': {}
                },
                'regime_detector': {
                    'regime_type': 'volatility_regime',
                    'detection_method': 'hmm',
                    'n_regimes': 3
                },
                'signal_enhancer': {
                    'enhancement_method': 'xgboost',
                    'enhancement_type': 'confidence_scoring'
                },
                'price_predictor': {
                    'prediction_horizon': 1,
                    'prediction_type': 'direction_magnitude',
                    'model_method': 'xgboost'
                }
            }


class MLEnhancedStrategy:
    """
    ML-Enhanced Strategy Wrapper.
    
    This class wraps existing trading strategies and enhances them with ML capabilities:
    - Dynamic parameter optimization based on market conditions
    - Market regime detection and regime-aware trading
    - Signal quality assessment and enhancement
    - Price prediction integration
    """
    
    def __init__(self, config: MLStrategyConfig):
        self.config = config
        self.strategy_name = config.strategy_name
        self.base_strategy = config.base_strategy
        
        # Initialize ML models
        self.parameter_optimizer = None
        self.regime_detector = None
        self.signal_enhancer = None
        self.price_predictor = None
        
        # Initialize feature pipeline
        self.feature_pipeline = FeaturePipeline()
        
        # State tracking
        self.signal_count = 0
        self.last_regime_check = 0
        self.last_parameter_optimization = 0
        self.current_regime = None
        self.optimized_parameters = {}
        
        # Performance tracking
        self.ml_enhancement_history = []
        self.performance_metrics = {}
        
        # Initialize ML models based on configuration
        self._initialize_ml_models()
        
    def _initialize_ml_models(self):
        """Initialize ML models based on configuration."""
        
        if self.config.enable_parameter_optimization:
            optimizer_config = self.config.ml_models_config['parameter_optimizer']
            self.parameter_optimizer = ParameterOptimizer(
                strategy_name=self.strategy_name,
                optimization_method=optimizer_config['optimization_method']
            )
            
            # Set parameter ranges if provided
            if 'parameter_ranges' in optimizer_config and optimizer_config['parameter_ranges']:
                self.parameter_optimizer.set_parameter_ranges(optimizer_config['parameter_ranges'])
            
            if 'baseline_parameters' in optimizer_config and optimizer_config['baseline_parameters']:
                self.parameter_optimizer.set_baseline_parameters(optimizer_config['baseline_parameters'])
        
        if self.config.enable_regime_detection:
            regime_config = self.config.ml_models_config['regime_detector']
            self.regime_detector = RegimeDetector(
                regime_type=regime_config['regime_type'],
                detection_method=regime_config['detection_method'],
                n_regimes=regime_config['n_regimes']
            )
        
        if self.config.enable_signal_enhancement:
            enhancer_config = self.config.ml_models_config['signal_enhancer']
            self.signal_enhancer = SignalEnhancer(
                strategy_name=self.strategy_name,
                enhancement_method=enhancer_config['enhancement_method'],
                enhancement_type=enhancer_config['enhancement_type']
            )
        
        if self.config.enable_price_prediction:
            predictor_config = self.config.ml_models_config['price_predictor']
            self.price_predictor = PricePredictor(
                prediction_horizon=predictor_config['prediction_horizon'],
                prediction_type=predictor_config['prediction_type'],
                model_method=predictor_config['model_method']
            )
    
    def train_ml_models(self, 
                       historical_data: pd.DataFrame,
                       training_periods: int = 1000,
                       validation_periods: int = 200) -> Dict[str, Any]:
        """
        Train all ML models using historical data.
        
        Args:
            historical_data: Historical market data with features
            training_periods: Number of periods for training
            validation_periods: Number of periods for validation
            
        Returns:
            Dictionary with training results for each model
        """
        print(f"Training ML models for {self.strategy_name}...")
        
        # Prepare training data
        training_data = historical_data.iloc[:training_periods]
        validation_data = historical_data.iloc[training_periods:training_periods + validation_periods]
        
        training_results = {}
        
        # Create features using feature pipeline
        try:
            features = self.feature_pipeline.create_features(training_data)
        except Exception as e:
            print(f"Warning: Feature pipeline failed, using basic features: {e}")
            # Fall back to basic features
            feature_columns = ['volatility_20d', 'returns_20d', 'atr_14', 'rsi_14', 'ema_20', 'ema_50']
            available_columns = [col for col in feature_columns if col in training_data.columns]
            features = training_data[available_columns].dropna()
        
        # Train regime detector
        if self.regime_detector and self.config.enable_regime_detection:
            try:
                regime_features = features[['volatility_20d', 'returns_20d', 'atr_14', 'rsi_14']].dropna()
                if len(regime_features) > 50:  # Minimum data requirement
                    training_results['regime_detector'] = self.regime_detector.train(regime_features, y=None)
                    print("✅ Regime detector trained successfully")
                else:
                    print("⚠️ Insufficient data for regime detector training")
            except Exception as e:
                print(f"❌ Regime detector training failed: {e}")
                self.config.enable_regime_detection = False
        
        # Train parameter optimizer
        if self.parameter_optimizer and self.config.enable_parameter_optimization:
            try:
                # Create training data for parameter optimization
                if hasattr(self.base_strategy, 'create_parameter_training_data'):
                    param_features, param_targets = self.base_strategy.create_parameter_training_data(training_data)
                else:
                    # Use mock training data generation
                    param_features, param_targets = self._create_mock_parameter_training_data(training_data)
                
                if len(param_features) > 50:
                    training_results['parameter_optimizer'] = self.parameter_optimizer.train(
                        param_features, param_targets
                    )
                    print("✅ Parameter optimizer trained successfully")
                else:
                    print("⚠️ Insufficient data for parameter optimizer training")
            except Exception as e:
                print(f"❌ Parameter optimizer training failed: {e}")
                self.config.enable_parameter_optimization = False
        
        # Train signal enhancer
        if self.signal_enhancer and self.config.enable_signal_enhancement:
            try:
                # Create training data for signal enhancement
                signal_features, signal_targets = self._create_signal_training_data(training_data)
                
                if len(signal_features) > 50:
                    training_results['signal_enhancer'] = self.signal_enhancer.train(
                        signal_features, signal_targets
                    )
                    print("✅ Signal enhancer trained successfully")
                else:
                    print("⚠️ Insufficient data for signal enhancer training")
            except Exception as e:
                print(f"❌ Signal enhancer training failed: {e}")
                self.config.enable_signal_enhancement = False
        
        # Train price predictor
        if self.price_predictor and self.config.enable_price_prediction:
            try:
                # Create training data for price prediction
                if 'close' in training_data.columns:
                    pred_features, pred_targets = self.price_predictor.create_training_data(
                        training_data, price_column='close'
                    )
                    
                    if len(pred_features) > 50:
                        training_results['price_predictor'] = self.price_predictor.train(
                            pred_features, pred_targets
                        )
                        print("✅ Price predictor trained successfully")
                    else:
                        print("⚠️ Insufficient data for price predictor training")
                else:
                    print("⚠️ No price data available for price predictor training")
            except Exception as e:
                print(f"❌ Price predictor training failed: {e}")
                self.config.enable_price_prediction = False
        
        print(f"ML model training completed for {self.strategy_name}")
        return training_results
    
    def _create_mock_parameter_training_data(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """Create mock training data for parameter optimization."""
        # Generate mock parameter combinations and their performance
        n_samples = min(100, len(data) // 10)
        features = []
        targets = []
        
        for i in range(n_samples):
            # Use random market features
            market_features = data.iloc[i % len(data)]
            features.append(market_features[['volatility_20d', 'returns_20d', 'atr_14', 'rsi_14']])
            
            # Mock performance based on market conditions
            volatility = market_features.get('volatility_20d', 0.02)
            returns = market_features.get('returns_20d', 0.0)
            
            # Higher performance for moderate volatility and positive returns
            performance = 0.5 + (0.3 if 0.01 < volatility < 0.05 else -0.2) + (0.2 if returns > 0 else -0.1)
            targets.append(max(0, min(1, performance)))  # Clamp between 0 and 1
        
        features_df = pd.DataFrame(features)
        targets_series = pd.Series(targets, name='performance')
        
        return features_df, targets_series
    
    def _create_signal_training_data(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """Create training data for signal enhancement."""
        features = []
        targets = []
        
        for i in range(len(data) - 5):  # Need 5 periods for forward performance
            current_data = data.iloc[i:i+1]
            
            # Generate mock signal
            volatility = current_data.iloc[0].get('volatility_20d', 0.02)
            rsi = current_data.iloc[0].get('rsi_14', 50)
            
            # Mock signal generation
            if volatility > 0.03 and rsi < 40:
                action = 'buy'
                strength = 0.8
            elif volatility > 0.03 and rsi > 60:
                action = 'sell'
                strength = 0.6
            else:
                action = 'hold'
                strength = 0.0
            
            # Create signal features
            signal_features = {
                'volatility_20d': volatility,
                'returns_20d': current_data.iloc[0].get('returns_20d', 0.0),
                'atr_14': current_data.iloc[0].get('atr_14', 0.02),
                'rsi_14': rsi,
                'signal_action_buy': 1 if action == 'buy' else 0,
                'signal_action_sell': 1 if action == 'sell' else 0,
                'signal_action_hold': 1 if action == 'hold' else 0,
                'signal_strength': strength
            }
            
            features.append(signal_features)
            
            # Calculate forward performance (mock)
            forward_performance = np.random.normal(0, 0.02)
            if action == 'buy' and forward_performance > 0.01:
                success = 1
            elif action == 'sell' and forward_performance < -0.01:
                success = 1
            elif action == 'hold':
                success = 1  # Hold is neutral
            else:
                success = 0
            
            targets.append(success)
        
        features_df = pd.DataFrame(features)
        targets_series = pd.Series(targets, name='signal_success')
        
        return features_df, targets_series
    
    def generate_signal(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate enhanced trading signal using ML models.
        
        Args:
            market_data: Current market data
            
        Returns:
            Enhanced trading signal with ML insights
        """
        self.signal_count += 1
        
        try:
            # Step 1: Detect market regime (if enabled and frequency met)
            current_regime = None
            regime_confidence = 0.0
            
            if (self.regime_detector and 
                self.config.enable_regime_detection and 
                self.signal_count % self.config.regime_detection_frequency == 0):
                
                try:
                    regime_features = market_data[['volatility_20d', 'returns_20d', 'atr_14', 'rsi_14']].dropna()
                    if len(regime_features) > 0 and self.regime_detector.is_trained:
                        current_regime, regime_probs = self.regime_detector.predict_regime(
                            regime_features, return_probabilities=True
                        )
                        regime_confidence = max(regime_probs)
                        self.current_regime = current_regime
                        self.last_regime_check = self.signal_count
                except Exception as e:
                    print(f"Regime detection failed: {e}")
            
            # Use last known regime if current detection failed
            if current_regime is None:
                current_regime = self.current_regime
            
            # Step 2: Optimize parameters (if enabled and frequency met)
            if (self.parameter_optimizer and 
                self.config.enable_parameter_optimization and 
                self.signal_count % self.config.parameter_optimization_frequency == 0):
                
                try:
                    param_features = market_data[['volatility_20d', 'returns_20d', 'atr_14', 'rsi_14']].dropna()
                    if len(param_features) > 0 and self.parameter_optimizer.is_trained:
                        # Get parameter names from base strategy
                        param_names = getattr(self.base_strategy, 'parameter_names', ['volatility_threshold'])
                        optimized_params = self.parameter_optimizer.optimize_parameters(
                            param_features, param_names
                        )
                        
                        # Update base strategy parameters
                        for param_name, param_value in optimized_params.items():
                            if hasattr(self.base_strategy, param_name):
                                setattr(self.base_strategy, param_name, param_value)
                        
                        self.optimized_parameters = optimized_params
                        self.last_parameter_optimization = self.signal_count
                except Exception as e:
                    print(f"Parameter optimization failed: {e}")
            
            # Step 3: Generate base signal
            base_signal = self.base_strategy.generate_signal(market_data)
            
            # Convert base signal to dictionary format
            if hasattr(base_signal, 'action') and hasattr(base_signal, 'strength'):
                signal_dict = {
                    'action': base_signal.action,
                    'strength': base_signal.strength,
                    'timestamp': datetime.now(timezone.utc)
                }
            else:
                # Handle different signal formats
                signal_dict = {
                    'action': getattr(base_signal, 'action', 'hold'),
                    'strength': getattr(base_signal, 'strength', 0.0),
                    'timestamp': datetime.now(timezone.utc)
                }
            
            # Step 4: Enhance signal with ML models
            enhanced_signal = signal_dict.copy()
            
            # Add price prediction insights
            if self.price_predictor and self.config.enable_price_prediction:
                try:
                    pred_features = market_data[['volatility_20d', 'returns_20d', 'atr_14', 'rsi_14']].dropna()
                    if len(pred_features) > 0 and self.price_predictor.is_trained:
                        current_price = market_data.iloc[-1].get('close', 100)
                        price_prediction, confidence = self.price_predictor.predict_price_movement(
                            pred_features, current_price, return_confidence=True
                        )
                        
                        if confidence >= self.config.prediction_confidence_threshold:
                            enhanced_signal['price_prediction'] = price_prediction
                            enhanced_signal['prediction_confidence'] = confidence
                            
                            # Adjust signal strength based on prediction alignment
                            if signal_dict['action'] == 'buy' and price_prediction['direction'] == 'up':
                                enhanced_signal['strength'] *= 1.1
                            elif signal_dict['action'] == 'sell' and price_prediction['direction'] == 'down':
                                enhanced_signal['strength'] *= 1.1
                            elif signal_dict['action'] != 'hold':
                                enhanced_signal['strength'] *= 0.9  # Reduce strength for misaligned signals
                except Exception as e:
                    print(f"Price prediction failed: {e}")
            
            # Add signal enhancement
            if self.signal_enhancer and self.config.enable_signal_enhancement:
                try:
                    enhancer_features = market_data[['volatility_20d', 'returns_20d', 'atr_14', 'rsi_14']].dropna()
                    if len(enhancer_features) > 0 and self.signal_enhancer.is_trained:
                        enhanced_signal = self.signal_enhancer.enhance_signal(
                            enhancer_features, enhanced_signal
                        )
                except Exception as e:
                    print(f"Signal enhancement failed: {e}")
            
            # Step 5: Add ML metadata
            enhanced_signal.update({
                'ml_enhanced': True,
                'signal_count': self.signal_count,
                'current_regime': current_regime,
                'regime_confidence': regime_confidence,
                'optimized_parameters': self.optimized_parameters,
                'base_strategy': self.strategy_name,
                'ml_models_used': self._get_active_ml_models()
            })
            
            # Step 6: Store enhancement history
            self.ml_enhancement_history.append({
                'timestamp': enhanced_signal['timestamp'],
                'signal_count': self.signal_count,
                'base_signal': signal_dict,
                'enhanced_signal': enhanced_signal,
                'regime': current_regime,
                'parameters': self.optimized_parameters
            })
            
            return enhanced_signal
            
        except Exception as e:
            print(f"ML enhancement failed: {e}")
            
            if self.config.fallback_to_base:
                # Fall back to base strategy
                base_signal = self.base_strategy.generate_signal(market_data)
                return {
                    'action': getattr(base_signal, 'action', 'hold'),
                    'strength': getattr(base_signal, 'strength', 0.0),
                    'timestamp': datetime.now(timezone.utc),
                    'ml_enhanced': False,
                    'fallback_reason': str(e)
                }
            else:
                raise e
    
    def _get_active_ml_models(self) -> List[str]:
        """Get list of active ML models."""
        active_models = []
        
        if self.regime_detector and self.config.enable_regime_detection:
            active_models.append('regime_detector')
        
        if self.parameter_optimizer and self.config.enable_parameter_optimization:
            active_models.append('parameter_optimizer')
        
        if self.signal_enhancer and self.config.enable_signal_enhancement:
            active_models.append('signal_enhancer')
        
        if self.price_predictor and self.config.enable_price_prediction:
            active_models.append('price_predictor')
        
        return active_models
    
    def get_ml_insights(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Get ML insights without generating a trading signal.
        
        Args:
            market_data: Current market data
            
        Returns:
            Dictionary with ML insights
        """
        insights = {
            'timestamp': datetime.now(timezone.utc),
            'signal_count': self.signal_count,
            'current_regime': self.current_regime,
            'optimized_parameters': self.optimized_parameters,
            'active_models': self._get_active_ml_models()
        }
        
        # Get regime insights
        if self.regime_detector and self.config.enable_regime_detection:
            try:
                regime_features = market_data[['volatility_20d', 'returns_20d', 'atr_14', 'rsi_14']].dropna()
                if len(regime_features) > 0 and self.regime_detector.is_trained:
                    regime_name, regime_probs = self.regime_detector.predict_regime(
                        regime_features, return_probabilities=True
                    )
                    insights['regime_prediction'] = {
                        'regime': regime_name,
                        'probabilities': dict(zip(
                            [f'regime_{i}' for i in range(len(regime_probs))],
                            regime_probs
                        ))
                    }
            except Exception as e:
                insights['regime_error'] = str(e)
        
        # Get price prediction insights
        if self.price_predictor and self.config.enable_price_prediction:
            try:
                pred_features = market_data[['volatility_20d', 'returns_20d', 'atr_14', 'rsi_14']].dropna()
                if len(pred_features) > 0 and self.price_predictor.is_trained:
                    current_price = market_data.iloc[-1].get('close', 100)
                    price_prediction, confidence = self.price_predictor.predict_price_movement(
                        pred_features, current_price, return_confidence=True
                    )
                    insights['price_prediction'] = {
                        'prediction': price_prediction,
                        'confidence': confidence
                    }
            except Exception as e:
                insights['price_prediction_error'] = str(e)
        
        return insights
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the ML-enhanced strategy."""
        if not self.ml_enhancement_history:
            return {}
        
        # Calculate basic metrics
        total_signals = len(self.ml_enhancement_history)
        enhanced_signals = sum(1 for h in self.ml_enhancement_history if h['enhanced_signal'].get('ml_enhanced', False))
        
        # Calculate regime distribution
        regimes = [h['regime'] for h in self.ml_enhancement_history if h['regime']]
        regime_distribution = pd.Series(regimes).value_counts().to_dict() if regimes else {}
        
        # Calculate parameter optimization frequency
        param_optimizations = sum(1 for h in self.ml_enhancement_history if h['parameters'])
        
        return {
            'total_signals': total_signals,
            'enhanced_signals': enhanced_signals,
            'enhancement_rate': enhanced_signals / total_signals if total_signals > 0 else 0,
            'regime_distribution': regime_distribution,
            'parameter_optimizations': param_optimizations,
            'active_ml_models': self._get_active_ml_models(),
            'current_regime': self.current_regime,
            'last_regime_check': self.last_regime_check,
            'last_parameter_optimization': self.last_parameter_optimization
        }
    
    def reset_state(self):
        """Reset the strategy state."""
        self.signal_count = 0
        self.last_regime_check = 0
        self.last_parameter_optimization = 0
        self.current_regime = None
        self.optimized_parameters = {}
        self.ml_enhancement_history = []
        self.performance_metrics = {}
        
        print(f"ML-enhanced strategy {self.strategy_name} state reset")
