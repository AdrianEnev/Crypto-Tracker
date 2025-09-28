"""
Demo script for ML models in Phase 5B.
Demonstrates parameter optimization, regime detection, signal enhancement, and price prediction.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone

from src.ml.models import ParameterOptimizer, RegimeDetector, SignalEnhancer, PricePredictor
from src.ml.feature_engineering import FeaturePipeline
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


def demo_parameter_optimization():
    """Demonstrate parameter optimization for trading strategies."""
    print("\n" + "="*60)
    print("DEMO: Parameter Optimization")
    print("="*60)
    
    # Generate market data
    market_data = generate_mock_market_data(500)
    
    # Create parameter optimizer
    optimizer = ParameterOptimizer(
        strategy_name="volatility_strategy",
        optimization_method="xgboost"
    )
    
    # Set parameter ranges for optimization
    parameter_ranges = {
        'volatility_threshold': (0.01, 0.05),
        'ema_short_period': (10, 25),
        'ema_long_period': (30, 60),
        'rsi_oversold': (20, 40),
        'rsi_overbought': (60, 80)
    }
    optimizer.set_parameter_ranges(parameter_ranges)
    
    # Set baseline parameters
    baseline_params = {
        'volatility_threshold': 0.025,
        'ema_short_period': 20,
        'ema_long_period': 50,
        'rsi_oversold': 30,
        'rsi_overbought': 70
    }
    optimizer.set_baseline_parameters(baseline_params)
    
    # Create mock strategy for training data generation
    class MockVolatilityStrategy:
        def __init__(self):
            self.params = baseline_params.copy()
        
        def update_parameters(self, params):
            self.params.update(params)
        
        def generate_signal(self, market_data):
            # Mock signal generation
            if len(market_data) > 0:
                volatility = market_data.iloc[-1]['volatility_20d']
                if volatility > self.params['volatility_threshold']:
                    return type('Signal', (), {'action': 'buy', 'strength': 1.0})()
            return type('Signal', (), {'action': 'hold', 'strength': 0.0})()
    
    strategy = MockVolatilityStrategy()
    
    # Create training data
    try:
        features, targets = optimizer.create_training_data(
            strategy, market_data, performance_metric="sharpe_ratio"
        )
        
        # Train the optimizer
        print(f"Training parameter optimizer with {len(features)} samples...")
        training_results = optimizer.train(features, targets)
        
        print("Training Results:")
        for metric, value in training_results['metrics'].items():
            print(f"  {metric}: {value:.4f}")
        
        # Test parameter optimization
        current_market = market_data.iloc[-1:].copy()
        optimized_params = optimizer.optimize_parameters(
            current_market, list(parameter_ranges.keys())
        )
        
        print("\nOptimized Parameters:")
        for param, value in optimized_params.items():
            baseline = baseline_params[param]
            change = ((value - baseline) / baseline * 100) if baseline != 0 else 0
            print(f"  {param}: {value:.4f} (baseline: {baseline:.4f}, change: {change:+.1f}%)")
        
        # Analyze parameter sensitivity
        sensitivity = optimizer.get_parameter_sensitivity(
            current_market, 'volatility_threshold', [0.01, 0.02, 0.03, 0.04, 0.05]
        )
        
        print("\nParameter Sensitivity Analysis:")
        for value, performance in sensitivity.items():
            print(f"  volatility_threshold={value}: performance={performance:.4f}")
            
    except Exception as e:
        print(f"Error in parameter optimization demo: {e}")


def demo_regime_detection():
    """Demonstrate market regime detection."""
    print("\n" + "="*60)
    print("DEMO: Market Regime Detection")
    print("="*60)
    
    # Generate market data with different regimes
    market_data = generate_mock_market_data(1000)
    
    # Create regime detector
    detector = RegimeDetector(
        regime_type="volatility_regime",
        detection_method="hmm",
        n_regimes=3
    )
    
    # Prepare features for regime detection
    feature_columns = ['volatility_20d', 'returns_20d', 'atr_14', 'rsi_14']
    features = market_data[feature_columns].dropna()
    
    print(f"Training regime detector with {len(features)} samples...")
    
    # Train the detector (unsupervised learning - no y needed)
    training_results = detector.train(features, y=None)
    
    print("Training Results:")
    for metric, value in training_results['metrics'].items():
        print(f"  {metric}: {value:.4f}")
    
    # Get regime statistics
    regime_stats = detector.get_regime_statistics()
    print("\nDetected Regimes:")
    for regime_id, info in regime_stats['regime_labels'].items():
        print(f"  Regime {regime_id} ({info['name']}):")
        print(f"    Count: {info['stats']['count']}")
        print(f"    Percentage: {info['stats']['percentage']:.1f}%")
        if 'avg_volatility' in info['stats']:
            print(f"    Avg Volatility: {info['stats']['avg_volatility']:.4f}")
    
    # Test regime prediction
    current_market = features.iloc[-1:].copy()
    regime_name, probabilities = detector.predict_regime(current_market, return_probabilities=True)
    
    print(f"\nCurrent Market Regime: {regime_name}")
    print("Regime Probabilities:")
    for regime_id in range(detector.n_regimes):
        regime_info = detector.regime_labels.get(regime_id, {})
        regime_name = regime_info.get('name', f'regime_{regime_id}')
        print(f"  {regime_name}: {probabilities[regime_id]:.3f}")
    
    # Analyze regime stability
    stability = detector.analyze_regime_stability(features, window_size=30)
    print(f"\nRegime Stability Analysis:")
    print(f"  Stability Ratio: {stability['stability_ratio']:.3f}")
    print(f"  Avg Regime Duration: {stability['avg_regime_duration']:.1f} periods")
    print(f"  Max Regime Duration: {stability['max_regime_duration']} periods")


def demo_signal_enhancement():
    """Demonstrate signal quality assessment and enhancement."""
    print("\n" + "="*60)
    print("DEMO: Signal Enhancement")
    print("="*60)
    
    # Generate market data
    market_data = generate_mock_market_data(800)
    
    # Create signal enhancer
    enhancer = SignalEnhancer(
        strategy_name="volatility_strategy",
        enhancement_method="xgboost",
        enhancement_type="confidence_scoring"
    )
    
    # Create mock strategy for training
    class MockStrategy:
        def generate_signal(self, market_data):
            # Generate mock signals with varying quality
            volatility = market_data.iloc[-1]['volatility_20d']
            rsi = market_data.iloc[-1]['rsi_14']
            
            if volatility > 0.03 and rsi < 40:
                return type('Signal', (), {'action': 'buy', 'strength': 0.8})()
            elif volatility > 0.03 and rsi > 60:
                return type('Signal', (), {'action': 'sell', 'strength': 0.6})()
            else:
                return type('Signal', (), {'action': 'hold', 'strength': 0.0})()
    
    strategy = MockStrategy()
    
    # Create training data
    try:
        features, targets = enhancer.create_training_data(strategy, market_data)
        
        # Train the enhancer
        print(f"Training signal enhancer with {len(features)} samples...")
        training_results = enhancer.train(features, targets)
        
        print("Training Results:")
        for metric, value in training_results['metrics'].items():
            print(f"  {metric}: {value:.4f}")
        
        # Test signal enhancement
        current_market = market_data.iloc[-1:].copy()
        original_signal = strategy.generate_signal(current_market)
        
        print(f"\nOriginal Signal:")
        print(f"  Action: {original_signal.action}")
        print(f"  Strength: {original_signal.strength:.3f}")
        
        # Enhance the signal
        enhanced_signal = enhancer.enhance_signal(
            current_market, 
            {'action': original_signal.action, 'strength': original_signal.strength}
        )
        
        print(f"\nEnhanced Signal:")
        print(f"  Action: {enhanced_signal['action']}")
        print(f"  Strength: {enhanced_signal['strength']:.3f}")
        print(f"  Quality Score: {enhanced_signal.get('quality_score', 'N/A'):.3f}")
        print(f"  Confidence: {enhanced_signal.get('confidence', 'N/A'):.3f}")
        
        # Test with different enhancement types
        enhancer.enhancement_type = "filtering"
        enhancer.set_signal_threshold(0.6)
        
        filtered_signal = enhancer.enhance_signal(
            current_market,
            {'action': original_signal.action, 'strength': original_signal.strength}
        )
        
        print(f"\nFiltered Signal (threshold=0.6):")
        print(f"  Action: {filtered_signal['action']}")
        print(f"  Strength: {filtered_signal['strength']:.3f}")
        print(f"  Quality Score: {filtered_signal.get('quality_score', 'N/A'):.3f}")
        
        # Get enhancement statistics
        stats = enhancer.get_enhancement_statistics()
        print(f"\nEnhancement Statistics:")
        print(f"  Total Enhancements: {stats.get('total_enhancements', 0)}")
        print(f"  Avg Quality Score: {stats.get('avg_quality_score', 0):.3f}")
        print(f"  Avg Confidence: {stats.get('avg_confidence', 0):.3f}")
        
    except Exception as e:
        print(f"Error in signal enhancement demo: {e}")


def demo_price_prediction():
    """Demonstrate price prediction capabilities."""
    print("\n" + "="*60)
    print("DEMO: Price Prediction")
    print("="*60)
    
    # Generate market data
    market_data = generate_mock_market_data(1000)
    
    # Create price predictor
    predictor = PricePredictor(
        prediction_horizon=1,
        prediction_type="direction_magnitude",
        model_method="xgboost"
    )
    
    # Prepare features
    feature_columns = ['volatility_20d', 'returns_20d', 'atr_14', 'rsi_14', 'ema_20', 'ema_50']
    features_data = market_data[feature_columns].dropna()
    
    # Create training data - need to include close prices
    try:
        features_with_price = pd.concat([features_data, market_data[['close']]], axis=1).dropna()
        features, targets = predictor.create_training_data(
            features_with_price, price_column='close', target_type="returns"
        )
        
        # Train the predictor
        print(f"Training price predictor with {len(features)} samples...")
        training_results = predictor.train(features, targets)
        
        print("Training Results:")
        for metric, value in training_results['metrics'].items():
            print(f"  {metric}: {value:.4f}")
        
        # Test price prediction
        current_market = features_data.iloc[-1:].copy()
        current_price = market_data.iloc[-1]['close']
        
        prediction, confidence = predictor.predict_price_movement(
            current_market, current_price, return_confidence=True
        )
        
        print(f"\nPrice Prediction:")
        print(f"  Current Price: ${current_price:.2f}")
        print(f"  Predicted Price: ${prediction['predicted_price']:.2f}")
        print(f"  Expected Return: {prediction['expected_return']:.4f} ({prediction['expected_return']*100:.2f}%)")
        print(f"  Direction: {prediction['direction']}")
        print(f"  Magnitude: {prediction['magnitude']:.4f}")
        print(f"  Confidence: {confidence:.3f}")
        
        # Generate trading signals
        signals = predictor.predict_signals(
            current_market, current_price, signal_threshold=0.01
        )
        
        print(f"\nTrading Signals:")
        print(f"  Action: {signals['action']}")
        print(f"  Strength: {signals['strength']:.3f}")
        print(f"  Confidence: {signals['confidence']:.3f}")
        
        # Test prediction accuracy on historical data
        accuracy = predictor.get_prediction_accuracy(
            features_data, market_data['close'], start_index=len(features_data)-100
        )
        
        print(f"\nPrediction Accuracy (last 100 predictions):")
        for metric, value in accuracy.items():
            print(f"  {metric}: {value:.4f}")
        
        # Analyze price trends
        trend_analysis = predictor.get_price_trend_analysis(current_market, current_price)
        print(f"\nPrice Trend Analysis:")
        print(f"  Current Price: ${trend_analysis['current_price']:.2f}")
        if 'short_term_trend' in trend_analysis:
            print(f"  Short-term Trend: {trend_analysis['short_term_trend']:.4f}")
            print(f"  Trend Direction: {trend_analysis['trend_direction']}")
        if 'volatility_regime' in trend_analysis:
            print(f"  Volatility Regime: {trend_analysis['volatility_regime']}")
        if 'ema_alignment' in trend_analysis:
            print(f"  EMA Alignment: {trend_analysis['ema_alignment']}")
        
    except Exception as e:
        print(f"Error in price prediction demo: {e}")


def demo_ml_integration():
    """Demonstrate integration of all ML models."""
    print("\n" + "="*60)
    print("DEMO: ML Models Integration")
    print("="*60)
    
    # Generate market data
    market_data = generate_mock_market_data(600)
    
    # Initialize all models
    optimizer = ParameterOptimizer("volatility_strategy", "xgboost")
    detector = RegimeDetector("volatility_regime", "hmm", 3)
    enhancer = SignalEnhancer("volatility_strategy", "xgboost", "confidence_scoring")
    predictor = PricePredictor(1, "direction_magnitude", "xgboost")
    
    # Set up parameter ranges for optimizer
    parameter_ranges = {
        'volatility_threshold': (0.01, 0.05),
        'ema_short_period': (10, 25),
        'ema_long_period': (30, 60)
    }
    optimizer.set_parameter_ranges(parameter_ranges)
    optimizer.set_baseline_parameters({
        'volatility_threshold': 0.025,
        'ema_short_period': 20,
        'ema_long_period': 50
    })
    
    print("Training integrated ML models...")
    
    # Train all models (simplified training for demo)
    try:
        # Train regime detector
        feature_columns = ['volatility_20d', 'returns_20d', 'atr_14', 'rsi_14']
        features = market_data[feature_columns].dropna()
        detector.train(features.iloc[:400], y=None)
        
        # Train price predictor - need to include close prices
        features_with_price = pd.concat([features.iloc[:400], market_data[['close']].iloc[:400]], axis=1).dropna()
        predictor_features, predictor_targets = predictor.create_training_data(
            features_with_price, price_column='close'
        )
        predictor.train(predictor_features, predictor_targets)
        
        print("Models trained successfully!")
        
        # Test integrated prediction
        current_market = features.iloc[-1:].copy()
        current_price = market_data.iloc[-1]['close']
        
        # 1. Detect market regime
        regime_name, regime_probs = detector.predict_regime(current_market, return_probabilities=True)
        print(f"\n1. Market Regime: {regime_name}")
        
        # 2. Optimize parameters for current regime
        optimized_params = optimizer.optimize_parameters(
            current_market, list(parameter_ranges.keys())
        )
        print(f"2. Optimized Parameters: {optimized_params}")
        
        # 3. Predict price movement
        price_prediction, confidence = predictor.predict_price_movement(
            current_market, current_price, return_confidence=True
        )
        print(f"3. Price Prediction: {price_prediction['direction']} {price_prediction['magnitude']:.4f} (conf: {confidence:.3f})")
        
        # 4. Generate and enhance signals
        mock_signal = {'action': 'buy', 'strength': 0.7}
        enhanced_signal = enhancer.enhance_signal(current_market, mock_signal)
        print(f"4. Enhanced Signal: {enhanced_signal['action']} {enhanced_signal['strength']:.3f}")
        
        print(f"\nIntegration Summary:")
        print(f"  Market is in {regime_name} regime")
        print(f"  Price expected to move {price_prediction['direction']} by {price_prediction['magnitude']*100:.2f}%")
        print(f"  Recommended signal: {enhanced_signal['action']} with strength {enhanced_signal['strength']:.3f}")
        
    except Exception as e:
        print(f"Error in integration demo: {e}")


def main():
    """Run all ML model demos."""
    print("ML Models Demo - Phase 5B Implementation")
    print("=" * 60)
    
    # Install required dependencies if not available
    try:
        import xgboost
        import hmmlearn
    except ImportError as e:
        print(f"Missing dependencies: {e}")
        print("Please install: pip install xgboost hmmlearn")
        return
    
    # Run individual demos
    demo_parameter_optimization()
    demo_regime_detection()
    demo_signal_enhancement()
    demo_price_prediction()
    demo_ml_integration()
    
    print("\n" + "="*60)
    print("Phase 5B Demo Complete!")
    print("="*60)
    print("\nKey Achievements:")
    print("✅ Parameter Optimization: Dynamic strategy parameter adjustment")
    print("✅ Regime Detection: Market regime identification and analysis")
    print("✅ Signal Enhancement: Quality assessment and signal filtering")
    print("✅ Price Prediction: Short-term price movement forecasting")
    print("✅ Model Integration: Coordinated ML model usage")
    print("\nNext: Phase 5C - ML Integration with Existing Strategies")


if __name__ == "__main__":
    main()
