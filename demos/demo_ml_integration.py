"""
Demo script for ML Integration in Phase 5C.
Demonstrates ML-enhanced strategies, ensembles, and strategy management.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone

from src.ml.integration import MLEnhancedStrategy, MLStrategyConfig, StrategyEnsemble, EnsembleConfig, EnsembleMethod, MLStrategyManager, MLStrategyManagerConfig
from src.strategies.volatility import VolatilityStrategy


def generate_mock_market_data(n_points: int = 1000, start_date: datetime = datetime(2020, 1, 1, tzinfo=timezone.utc)) -> pd.DataFrame:
    """Generate mock market data for testing."""
    dates = pd.date_range(start=start_date, periods=n_points, freq='4h')
    
    # Generate price data with trends and volatility
    np.random.seed(42)
    returns = np.random.normal(0.0001, 0.02, n_points)  # Small positive drift with 2% volatility
    
    # Add some regime changes
    regime_changes = [200, 400, 600, 800]
    for change_point in regime_changes:
        if change_point < n_points:
            # High volatility regime
            returns[change_point:change_point+50] *= 3
    
    prices = [100]  # Starting price
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    data = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices],
        'close': prices,
        'volume': np.random.lognormal(10, 1, n_points)
    })
    
    # Add technical indicators
    data['ema_20'] = data['close'].ewm(span=20).mean()
    data['ema_50'] = data['close'].ewm(span=50).mean()
    data['rsi_14'] = 50 + 20 * np.sin(np.arange(n_points) * 0.1)  # Mock RSI
    data['atr_14'] = data['close'].rolling(14).std()
    data['volatility_20d'] = data['close'].pct_change().rolling(20).std()
    data['returns_20d'] = data['close'].pct_change(20)
    
    return data


class MockVolatilityStrategy:
    """Mock volatility strategy for testing."""
    
    def __init__(self, name: str = "mock_volatility"):
        self.name = name
        self.volatility_threshold = 0.025
        self.parameter_names = ['volatility_threshold']
    
    def generate_signal(self, market_data):
        """Generate mock trading signal."""
        if len(market_data) > 0:
            volatility = market_data.iloc[-1].get('volatility_20d', 0.02)
            rsi = market_data.iloc[-1].get('rsi_14', 50)
            
            if volatility > self.volatility_threshold and rsi < 40:
                return type('Signal', (), {'action': 'buy', 'strength': 0.8})()
            elif volatility > self.volatility_threshold and rsi > 60:
                return type('Signal', (), {'action': 'sell', 'strength': 0.6})()
        
        return type('Signal', (), {'action': 'hold', 'strength': 0.0})()


def demo_ml_enhanced_strategy():
    """Demonstrate ML-enhanced strategy."""
    print("\n" + "="*60)
    print("DEMO: ML-Enhanced Strategy")
    print("="*60)
    
    # Generate market data
    market_data = generate_mock_market_data(800)
    
    # Create base strategy
    base_strategy = MockVolatilityStrategy("volatility_base")
    
    # Create ML-enhanced strategy configuration
    ml_config = MLStrategyConfig(
        strategy_name="ml_volatility_strategy",
        base_strategy=base_strategy,
        enable_parameter_optimization=True,
        enable_regime_detection=True,
        enable_signal_enhancement=True,
        enable_price_prediction=True,
        parameter_optimization_frequency=50,
        regime_detection_frequency=10,
        ml_models_config={
            'parameter_optimizer': {
                'optimization_method': 'xgboost',
                'parameter_ranges': {
                    'volatility_threshold': (0.01, 0.05)
                },
                'baseline_parameters': {
                    'volatility_threshold': 0.025
                }
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
    )
    
    # Create ML-enhanced strategy
    ml_strategy = MLEnhancedStrategy(ml_config)
    
    # Train the strategy
    print("Training ML-enhanced strategy...")
    training_results = ml_strategy.train_ml_models(market_data, training_periods=400, validation_periods=100)
    
    print("Training Results Summary:")
    for model_name, results in training_results.items():
        if 'error' not in results:
            print(f"  ✅ {model_name}: Trained successfully")
        else:
            print(f"  ❌ {model_name}: {results['error']}")
    
    # Test signal generation
    print("\nTesting ML-enhanced signal generation...")
    
    test_signals = []
    for i in range(10):
        test_data = market_data.iloc[500+i:501+i]
        signal = ml_strategy.generate_signal(test_data)
        test_signals.append(signal)
        
        print(f"  Signal {i+1}: {signal['action']} (strength: {signal['strength']:.3f}, "
              f"ML enhanced: {signal.get('ml_enhanced', False)}, "
              f"regime: {signal.get('current_regime', 'unknown')})")
    
    # Get ML insights
    print("\nML Insights:")
    insights = ml_strategy.get_ml_insights(market_data.iloc[-1:])
    print(f"  Current regime: {insights.get('current_regime', 'unknown')}")
    print(f"  Active ML models: {insights.get('active_models', [])}")
    if 'regime_prediction' in insights:
        regime_pred = insights['regime_prediction']
        print(f"  Regime probabilities: {regime_pred.get('probabilities', {})}")
    
    # Get performance metrics
    print("\nPerformance Metrics:")
    metrics = ml_strategy.get_performance_metrics()
    print(f"  Total signals: {metrics.get('total_signals', 0)}")
    print(f"  Enhancement rate: {metrics.get('enhancement_rate', 0):.2%}")
    print(f"  Active ML models: {metrics.get('active_ml_models', [])}")


def demo_strategy_ensemble():
    """Demonstrate strategy ensemble."""
    print("\n" + "="*60)
    print("DEMO: Strategy Ensemble")
    print("="*60)
    
    # Generate market data
    market_data = generate_mock_market_data(600)
    
    # Create multiple base strategies
    strategies = [
        MockVolatilityStrategy("volatility_strategy_1"),
        MockVolatilityStrategy("volatility_strategy_2"),
        MockVolatilityStrategy("volatility_strategy_3")
    ]
    
    # Create ML-enhanced strategies
    ml_strategies = []
    for i, base_strategy in enumerate(strategies):
        config = MLStrategyConfig(
            strategy_name=base_strategy.name,
            base_strategy=base_strategy,
            enable_parameter_optimization=True,
            enable_regime_detection=True,
            enable_signal_enhancement=False,  # Disable for faster demo
            enable_price_prediction=False,    # Disable for faster demo
            parameter_optimization_frequency=100,
            regime_detection_frequency=20
        )
        
        ml_strategy = MLEnhancedStrategy(config)
        ml_strategies.append(ml_strategy)
    
    # Create ensemble configuration
    ensemble_config = EnsembleConfig(
        ensemble_name="volatility_ensemble",
        strategies=ml_strategies,
        ensemble_method=EnsembleMethod.WEIGHTED_AVERAGE,
        rebalancing_frequency=50,
        performance_window=30,
        enable_dynamic_reweighting=True
    )
    
    # Create ensemble
    ensemble = StrategyEnsemble(ensemble_config)
    
    # Train ensemble
    print("Training strategy ensemble...")
    training_results = ensemble.train_ensemble(market_data, training_periods=300, validation_periods=100)
    
    print("Ensemble Training Results:")
    for strategy_name, results in training_results.items():
        if 'error' not in results:
            print(f"  ✅ {strategy_name}: Trained successfully")
        else:
            print(f"  ❌ {strategy_name}: {results['error']}")
    
    # Test ensemble signal generation
    print("\nTesting ensemble signal generation...")
    
    ensemble_signals = []
    for i in range(15):
        test_data = market_data.iloc[400+i:401+i]
        signal = ensemble.generate_ensemble_signal(test_data)
        ensemble_signals.append(signal)
        
        print(f"  Signal {i+1}: {signal['action']} (strength: {signal['strength']:.3f}, "
              f"method: {signal.get('ensemble_method', 'unknown')})")
        
        # Show strategy contributions
        if 'strategy_details' in signal:
            print(f"    Strategy contributions:")
            for detail in signal['strategy_details'][:2]:  # Show first 2 strategies
                print(f"      {detail['strategy']}: {detail['action']} ({detail['weight']:.3f})")
    
    # Get ensemble insights
    print("\nEnsemble Insights:")
    insights = ensemble.get_ensemble_insights(market_data.iloc[-1:])
    print(f"  Ensemble method: {insights.get('ensemble_method', 'unknown')}")
    print(f"  Strategy count: {insights.get('strategy_count', 0)}")
    print(f"  Current weights: {insights.get('current_weights', {})}")
    
    # Get ensemble metrics
    print("\nEnsemble Metrics:")
    metrics = ensemble.get_ensemble_metrics()
    print(f"  Total signals: {metrics.get('total_signals', 0)}")
    print(f"  Action distribution: {metrics.get('action_distribution', {})}")
    print(f"  Average strength: {metrics.get('average_strength', 0):.3f}")


def demo_ml_strategy_manager():
    """Demonstrate ML strategy manager."""
    print("\n" + "="*60)
    print("DEMO: ML Strategy Manager")
    print("="*60)
    
    # Generate market data
    market_data = generate_mock_market_data(800)
    
    # Create multiple strategies
    base_strategies = [
        MockVolatilityStrategy("volatility_strategy_1"),
        MockVolatilityStrategy("volatility_strategy_2")
    ]
    
    # Create ML strategy configurations
    strategy_configs = []
    for base_strategy in base_strategies:
        config = MLStrategyConfig(
            strategy_name=base_strategy.name,
            base_strategy=base_strategy,
            enable_parameter_optimization=True,
            enable_regime_detection=True,
            enable_signal_enhancement=False,  # Disable for faster demo
            enable_price_prediction=False,    # Disable for faster demo
            parameter_optimization_frequency=100,
            regime_detection_frequency=20
        )
        strategy_configs.append(config)
    
    # Create ensemble configuration (will be populated by manager)
    ensemble_config = None  # Will be created after strategies are initialized
    
    # Create manager configuration
    manager_config = MLStrategyManagerConfig(
        manager_name="demo_manager",
        strategies=strategy_configs,
        ensembles=[],  # No ensembles for this demo
        enable_auto_retraining=False,  # Disable for demo
        retraining_frequency=100,
        performance_monitoring=True,
        enable_strategy_switching=True,
        enable_backup_strategies=True,
        backup_frequency=50,
        enable_performance_alerts=True,
        performance_threshold=0.3
    )
    
    # Create manager
    manager = MLStrategyManager(manager_config)
    
    # Train all models
    print("Training all models through manager...")
    training_results = manager.train_all_models(market_data, training_periods=300, validation_periods=100)
    
    print("Manager Training Results:")
    print(f"  Strategies trained: {len(training_results['strategies'])}")
    print(f"  Ensembles trained: {len(training_results['ensembles'])}")
    
    # Test signal generation through manager
    print("\nTesting signal generation through manager...")
    
    manager_signals = []
    for i in range(20):
        test_data = market_data.iloc[500+i:501+i]
        signal = manager.generate_signal(test_data)
        manager_signals.append(signal)
        
        print(f"  Signal {i+1}: {signal['action']} (strength: {signal['strength']:.3f}, "
              f"source: {signal.get('source_name', 'unknown')}, "
              f"type: {signal.get('source_type', 'unknown')})")
    
    # Test strategy switching
    print("\nTesting strategy switching...")
    if len(manager.strategies) > 1:
        strategy_names = list(manager.strategies.keys())
        original_strategy = manager.active_strategy
        new_strategy = strategy_names[1] if strategy_names[1] != original_strategy else strategy_names[0]
        
        success = manager.switch_strategy(new_strategy)
        if success:
            print(f"  ✅ Successfully switched from {original_strategy} to {new_strategy}")
        else:
            print(f"  ❌ Failed to switch to {new_strategy}")
    
    # Get manager status
    print("\nManager Status:")
    status = manager.get_manager_status()
    print(f"  Manager name: {status['manager_name']}")
    print(f"  Total signals: {status['total_signals']}")
    print(f"  Active strategy: {status['active_strategy']}")
    print(f"  Strategies: {status['strategies']}")
    print(f"  Ensembles: {status['ensembles']}")
    
    # Get performance summary
    print("\nPerformance Summary:")
    performance = manager.get_performance_summary()
    print(f"  Total signals: {performance['total_signals']}")
    print(f"  Alerts: {performance['alerts']}")
    
    for strategy_name, strategy_perf in performance['strategies'].items():
        print(f"  {strategy_name}:")
        print(f"    Recent performance: {strategy_perf.get('recent_performance', 0):.3f}")
        print(f"    Total signals: {strategy_perf.get('total_signals', 0)}")
        print(f"    Performance trend: {strategy_perf.get('performance_trend', 0):.3f}")
    
    # Get recent alerts
    print("\nRecent Alerts:")
    alerts = manager.get_recent_alerts(limit=5)
    for alert in alerts:
        print(f"  {alert['timestamp']}: {alert['type']} - {alert.get('strategy_name', 'N/A')}")


def demo_comprehensive_integration():
    """Demonstrate comprehensive ML integration."""
    print("\n" + "="*60)
    print("DEMO: Comprehensive ML Integration")
    print("="*60)
    
    # Generate market data with multiple regimes
    market_data = generate_mock_market_data(1000)
    
    # Create a complete ML-enhanced trading system
    base_strategy = MockVolatilityStrategy("comprehensive_strategy")
    
    # Create comprehensive ML configuration
    ml_config = MLStrategyConfig(
        strategy_name="comprehensive_ml_strategy",
        base_strategy=base_strategy,
        enable_parameter_optimization=True,
        enable_regime_detection=True,
        enable_signal_enhancement=True,
        enable_price_prediction=True,
        parameter_optimization_frequency=30,
        regime_detection_frequency=5,
        signal_enhancement_threshold=0.5,
        prediction_confidence_threshold=0.6,
        ml_models_config={
            'parameter_optimizer': {
                'optimization_method': 'xgboost',
                'parameter_ranges': {
                    'volatility_threshold': (0.01, 0.05)
                },
                'baseline_parameters': {
                    'volatility_threshold': 0.025
                }
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
    )
    
    # Create ML-enhanced strategy
    ml_strategy = MLEnhancedStrategy(ml_config)
    
    # Train the strategy
    print("Training comprehensive ML strategy...")
    training_results = ml_strategy.train_ml_models(market_data, training_periods=500, validation_periods=100)
    
    # Simulate live trading
    print("\nSimulating live trading with ML enhancement...")
    
    trading_results = {
        'signals': [],
        'regimes': [],
        'parameter_changes': [],
        'enhancements': []
    }
    
    for i in range(50):
        # Get current market data
        current_data = market_data.iloc[600+i:601+i]
        
        # Generate enhanced signal
        signal = ml_strategy.generate_signal(current_data)
        
        # Record results
        trading_results['signals'].append({
            'timestamp': signal['timestamp'],
            'action': signal['action'],
            'strength': signal['strength'],
            'ml_enhanced': signal.get('ml_enhanced', False),
            'regime': signal.get('current_regime', 'unknown')
        })
        
        if signal.get('current_regime'):
            trading_results['regimes'].append(signal['current_regime'])
        
        if signal.get('optimized_parameters'):
            trading_results['parameter_changes'].append(signal['optimized_parameters'])
        
        if signal.get('quality_score'):
            trading_results['enhancements'].append(signal['quality_score'])
        
        # Print every 10th signal
        if (i + 1) % 10 == 0:
            print(f"  Signal {i+1}: {signal['action']} (strength: {signal['strength']:.3f}, "
                  f"regime: {signal.get('current_regime', 'unknown')}, "
                  f"ML: {signal.get('ml_enhanced', False)})")
    
    # Analyze results
    print("\nTrading Results Analysis:")
    
    signals_df = pd.DataFrame(trading_results['signals'])
    
    print(f"  Total signals: {len(signals_df)}")
    print(f"  ML enhanced signals: {signals_df['ml_enhanced'].sum()}")
    print(f"  Enhancement rate: {signals_df['ml_enhanced'].mean():.2%}")
    
    action_dist = signals_df['action'].value_counts()
    print(f"  Action distribution: {action_dist.to_dict()}")
    
    avg_strength = signals_df['strength'].mean()
    print(f"  Average signal strength: {avg_strength:.3f}")
    
    # Regime analysis
    if trading_results['regimes']:
        regime_dist = pd.Series(trading_results['regimes']).value_counts()
        print(f"  Regime distribution: {regime_dist.to_dict()}")
    
    # Parameter optimization analysis
    if trading_results['parameter_changes']:
        print(f"  Parameter optimizations: {len(trading_results['parameter_changes'])}")
    
    # Signal enhancement analysis
    if trading_results['enhancements']:
        avg_quality = np.mean(trading_results['enhancements'])
        print(f"  Average signal quality: {avg_quality:.3f}")
    
    # Get final performance metrics
    print("\nFinal Performance Metrics:")
    metrics = ml_strategy.get_performance_metrics()
    print(f"  Total signals: {metrics.get('total_signals', 0)}")
    print(f"  Enhancement rate: {metrics.get('enhancement_rate', 0):.2%}")
    print(f"  Active ML models: {metrics.get('active_ml_models', [])}")
    print(f"  Current regime: {metrics.get('current_regime', 'unknown')}")


def main():
    """Run all ML integration demos."""
    print("ML Integration Demo - Phase 5C Implementation")
    print("=" * 60)
    
    # Run individual demos
    demo_ml_enhanced_strategy()
    demo_strategy_ensemble()
    demo_ml_strategy_manager()
    demo_comprehensive_integration()
    
    print("\n" + "="*60)
    print("Phase 5C Demo Complete!")
    print("="*60)
    print("\nKey Achievements:")
    print("✅ ML-Enhanced Strategy: Dynamic parameter optimization and regime detection")
    print("✅ Strategy Ensemble: Intelligent combination of multiple strategies")
    print("✅ ML Strategy Manager: Centralized management and coordination")
    print("✅ Comprehensive Integration: Full ML-enhanced trading system")
    print("\nNext: Phase 5D - Optimization and Monitoring")


if __name__ == "__main__":
    main()
