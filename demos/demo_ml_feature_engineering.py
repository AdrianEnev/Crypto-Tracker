"""
Demo script for Phase 5A: ML Feature Engineering Pipeline.
Demonstrates the feature engineering system that enhances existing trading strategies.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from datetime import datetime, timezone
from src.ml.feature_engineering.feature_pipeline import FeaturePipeline, FeatureConfig
from src.ml.feature_engineering.technical_features import TechnicalFeatures
from src.ml.feature_engineering.onchain_features import OnChainFeatures
from src.ml.feature_engineering.sentiment_features import SentimentFeatures
from src.ml.feature_engineering.microstructure_features import MicrostructureFeatures


def generate_mock_market_data(symbol: str = "BTC-USDT", days: int = 365) -> pd.DataFrame:
    """Generate realistic mock market data for demonstration."""
    print(f"Generating mock market data for {symbol}...")
    
    dates = pd.date_range(start='2023-01-01', periods=days, freq='D')
    
    # Generate realistic price data with trend and volatility
    np.random.seed(42)
    base_price = 50000.0 if symbol == "BTC-USDT" else 3000.0
    
    # Add trend and volatility
    trend = np.linspace(0, 0.5, days)  # 50% annual trend
    volatility = 0.02  # 2% daily volatility
    returns = np.random.normal(trend / days, volatility, days)
    prices = base_price * np.cumprod(1 + returns)
    
    # Create OHLCV data
    market_data = pd.DataFrame(index=dates)
    market_data['close'] = prices
    
    # Generate realistic OHLC from close prices
    daily_range = np.random.uniform(0.01, 0.05, days)  # 1-5% daily range
    market_data['high'] = market_data['close'] * (1 + daily_range / 2)
    market_data['low'] = market_data['close'] * (1 - daily_range / 2)
    market_data['open'] = market_data['close'].shift(1) * (1 + np.random.normal(0, 0.01, days))
    market_data['open'].iloc[0] = market_data['close'].iloc[0]
    
    # Generate volume data
    base_volume = 10000 if symbol == "BTC-USDT" else 100000
    volume_trend = np.random.uniform(0.8, 1.2, days)
    market_data['volume'] = base_volume * volume_trend
    
    return market_data


def demo_basic_feature_engineering():
    """Demonstrate basic feature engineering pipeline."""
    print("=== Basic Feature Engineering Demo ===\n")
    
    # Generate mock market data
    market_data = generate_mock_market_data("BTC-USDT", 365)
    
    # Configure feature pipeline
    config = FeatureConfig(
        include_technical=True,
        include_onchain=False,  # Skip alternative data for basic demo
        include_sentiment=False,
        include_microstructure=False,
        max_features=50
    )
    
    # Create feature pipeline
    pipeline = FeaturePipeline(config)
    
    # Generate features
    print("Creating features...")
    feature_set = pipeline.create_features(market_data, symbol="BTC-USDT")
    
    print(f"\nResults:")
    print(f"  Market data shape: {market_data.shape}")
    print(f"  Feature set shape: {feature_set.features.shape}")
    print(f"  Number of features: {len(feature_set.feature_names)}")
    print(f"  Data points: {feature_set.metadata['data_points']}")
    print(f"  Date range: {feature_set.metadata['date_range']}")
    
    # Show sample features
    print(f"\nSample technical features:")
    technical_features = [f for f in feature_set.feature_names if any(x in f for x in ['price', 'volume', 'ma', 'rsi', 'macd'])]
    for i, feature in enumerate(technical_features[:10]):
        print(f"  {i+1:2d}. {feature}")
    
    return feature_set


def demo_alternative_data_features():
    """Demonstrate feature engineering with alternative data."""
    print("\n=== Alternative Data Features Demo ===\n")
    
    # Generate mock market data
    market_data = generate_mock_market_data("BTC-USDT", 365)
    
    # Generate alternative data
    onchain_features = OnChainFeatures()
    sentiment_features = SentimentFeatures()
    microstructure_features = MicrostructureFeatures()
    
    # Resample microstructure data to daily
    microstructure_data = microstructure_features.mock_microstructure_data.resample('D').mean()
    
    alternative_data = {
        'onchain': onchain_features.mock_onchain_data,
        'sentiment': sentiment_features.mock_sentiment_data,
        'microstructure': microstructure_data
    }
    
    # Configure feature pipeline with all data sources
    config = FeatureConfig(
        include_technical=True,
        include_onchain=True,
        include_sentiment=True,
        include_microstructure=True,
        max_features=100
    )
    
    # Create feature pipeline
    pipeline = FeaturePipeline(config)
    
    # Generate features
    print("Creating features with alternative data...")
    feature_set = pipeline.create_features(market_data, alternative_data, "BTC-USDT")
    
    print(f"\nResults:")
    print(f"  Total features created: {len(feature_set.feature_names)}")
    print(f"  Data points: {feature_set.metadata['data_points']}")
    
    # Analyze feature types
    feature_types = {
        'technical': len([f for f in feature_set.feature_names if any(x in f for x in ['price', 'volume', 'ma', 'rsi', 'macd', 'bb'])]),
        'onchain': len([f for f in feature_set.feature_names if any(x in f for x in ['tx_', 'active_', 'whale', 'exchange', 'hash_', 'defi'])]),
        'sentiment': len([f for f in feature_set.feature_names if any(x in f for x in ['twitter', 'reddit', 'news', 'sentiment', 'fear_greed'])]),
        'microstructure': len([f for f in feature_set.feature_names if any(x in f for x in ['spread', 'imbalance', 'depth', 'trade', 'impact', 'liquidity'])]),
        'engineered': len([f for f in feature_set.feature_names if any(x in f for x in ['returns', 'volatility', 'position', 'momentum', 'regime'])])
    }
    
    print(f"\nFeature breakdown:")
    for feature_type, count in feature_types.items():
        print(f"  {feature_type.capitalize()}: {count} features")
    
    return feature_set


def demo_feature_selection():
    """Demonstrate feature selection and correlation analysis."""
    print("\n=== Feature Selection Demo ===\n")
    
    # Generate features
    market_data = generate_mock_market_data("BTC-USDT", 365)
    config = FeatureConfig(max_features=50, correlation_threshold=0.8)
    pipeline = FeaturePipeline(config)
    
    feature_set = pipeline.create_features(market_data, symbol="BTC-USDT")
    
    # Generate a mock target variable (future returns)
    target = feature_set.features['close'].pct_change().shift(-1)  # Next day returns
    
    # Calculate feature importance
    importance_df = pipeline.get_feature_importance(feature_set, target)
    
    print(f"Top 10 most important features:")
    for i, (_, row) in enumerate(importance_df.head(10).iterrows()):
        print(f"  {i+1:2d}. {row['feature']:<25} (importance: {row['importance']:.3f})")
    
    # Show correlation analysis
    feature_data = feature_set.features[feature_set.feature_names].dropna()
    corr_matrix = feature_data.corr().abs()
    
    # Find highly correlated pairs
    high_corr_pairs = []
    for i in range(len(corr_matrix.columns)):
        for j in range(i+1, len(corr_matrix.columns)):
            corr_val = corr_matrix.iloc[i, j]
            if corr_val > 0.8:
                high_corr_pairs.append((corr_matrix.columns[i], corr_matrix.columns[j], corr_val))
    
    print(f"\nHighly correlated feature pairs (correlation > 0.8):")
    for feat1, feat2, corr in high_corr_pairs[:5]:
        print(f"  {feat1} <-> {feat2}: {corr:.3f}")


def demo_rolling_features():
    """Demonstrate rolling window features for time series models."""
    print("\n=== Rolling Features Demo ===\n")
    
    # Generate features
    market_data = generate_mock_market_data("BTC-USDT", 365)
    config = FeatureConfig(max_features=30)
    pipeline = FeaturePipeline(config)
    
    feature_set = pipeline.create_features(market_data, symbol="BTC-USDT")
    
    # Create rolling features
    rolling_feature_set = pipeline.create_rolling_features(
        feature_set, 
        window_sizes=[5, 10, 20]
    )
    
    print(f"Original features: {len(feature_set.feature_names)}")
    print(f"Rolling features: {len(rolling_feature_set.feature_names)}")
    print(f"Additional features created: {len(rolling_feature_set.feature_names) - len(feature_set.feature_names)}")
    
    # Show sample rolling features
    rolling_features = [f for f in rolling_feature_set.feature_names if 'rolling' in f]
    print(f"\nSample rolling features:")
    for i, feature in enumerate(rolling_features[:10]):
        print(f"  {i+1:2d}. {feature}")


def demo_feature_quality_assessment():
    """Demonstrate feature quality assessment and validation."""
    print("\n=== Feature Quality Assessment Demo ===\n")
    
    # Generate features with different configurations
    market_data = generate_mock_market_data("BTC-USDT", 365)
    
    configs = [
        ("Basic", FeatureConfig(include_technical=True, max_features=20)),
        ("Advanced", FeatureConfig(include_technical=True, max_features=50)),
        ("Full", FeatureConfig(include_technical=True, include_onchain=True, max_features=100))
    ]
    
    results = []
    
    for name, config in configs:
        pipeline = FeaturePipeline(config)
        
        if config.include_onchain:
            onchain_features = OnChainFeatures()
            alternative_data = {'onchain': onchain_features.mock_onchain_data}
            feature_set = pipeline.create_features(market_data, alternative_data, "BTC-USDT")
        else:
            feature_set = pipeline.create_features(market_data, symbol="BTC-USDT")
        
        # Calculate quality metrics
        feature_data = feature_set.features[feature_set.feature_names].dropna()
        
        quality_metrics = {
            'config': name,
            'total_features': len(feature_set.feature_names),
            'data_points': len(feature_data),
            'missing_ratio': feature_data.isnull().sum().sum() / (len(feature_data) * len(feature_data.columns)),
            'feature_variance': feature_data.var().mean(),
            'correlation_max': feature_data.corr().abs().max().max()
        }
        
        results.append(quality_metrics)
    
    # Display results
    print("Feature quality comparison:")
    print("-" * 80)
    print(f"{'Config':<12} {'Features':<10} {'Data Points':<12} {'Missing %':<10} {'Avg Var':<10} {'Max Corr':<10}")
    print("-" * 80)
    
    for result in results:
        print(f"{result['config']:<12} {result['total_features']:<10} {result['data_points']:<12} "
              f"{result['missing_ratio']*100:<9.1f} {result['feature_variance']:<9.3f} {result['correlation_max']:<9.3f}")


def demo_integration_with_existing_strategies():
    """Demonstrate how features integrate with existing trading strategies."""
    print("\n=== Integration with Existing Strategies Demo ===\n")
    
    # Generate market data and features
    market_data = generate_mock_market_data("BTC-USDT", 365)
    config = FeatureConfig(max_features=50)
    pipeline = FeaturePipeline(config)
    feature_set = pipeline.create_features(market_data, symbol="BTC-USDT")
    
    print("Feature integration examples:")
    print("\n1. Enhanced Volatility Strategy:")
    print("   - Original: EMA(20) > EMA(50) and ATR(14) > threshold")
    print("   - Enhanced: EMA(20) > EMA(50) and ATR(14) > threshold and volatility_regime == 'high'")
    print("   - Additional features: bb_squeeze_20, volatility_ratio_20d, high_vol_regime")
    
    print("\n2. Enhanced Momentum Strategy:")
    print("   - Original: RSI(14) > 70 and MACD > MACD_signal")
    print("   - Enhanced: RSI(14) > 70 and MACD > MACD_signal and momentum_5d > 0.02")
    print("   - Additional features: momentum_5d, price_vs_ema_12, rsi_14_momentum")
    
    print("\n3. Enhanced Mean Reversion Strategy:")
    print("   - Original: Price < Bollinger Lower Band and RSI < 30")
    print("   - Enhanced: Price < Bollinger Lower Band and RSI < 30 and orderbook_imbalance < -0.3")
    print("   - Additional features: bb_position_20, orderbook_imbalance, strong_ask_imbalance")
    
    print(f"\nAvailable features for strategy enhancement: {len(feature_set.feature_names)}")
    print("These features can be used to:")
    print("  - Optimize strategy parameters dynamically")
    print("  - Add market regime filters")
    print("  - Improve signal quality assessment")
    print("  - Enhance risk management")


def main():
    """Run all feature engineering demos."""
    print("Phase 5A: ML Feature Engineering Pipeline Demo")
    print("=" * 60)
    print()
    
    try:
        # Run all demos
        demo_basic_feature_engineering()
        demo_alternative_data_features()
        demo_feature_selection()
        demo_rolling_features()
        demo_feature_quality_assessment()
        demo_integration_with_existing_strategies()
        
        print("\n" + "=" * 60)
        print("Phase 5A Demo completed successfully!")
        print("\nKey achievements:")
        print("✅ Feature engineering pipeline implemented")
        print("✅ Technical indicator features created")
        print("✅ Alternative data integration ready")
        print("✅ Feature selection and correlation analysis")
        print("✅ Rolling window features for time series")
        print("✅ Feature quality assessment")
        print("✅ Integration framework with existing strategies")
        print("\nNext: Phase 5B - Core ML Models")
        
    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
