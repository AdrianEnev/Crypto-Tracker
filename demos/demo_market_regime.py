"""
Demo script for the Advanced Market Regime Detection System.
Shows volatility clustering, trend analysis, and regime classification.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from src.market_regime import MarketRegimeDetector


def generate_sample_market_data():
    """Generate sample market data with different regimes."""
    np.random.seed(42)
    
    n_days = 1000
    dates = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(n_days)]
    
    # Generate different market regimes
    prices = []
    volumes = []
    
    # Start with bull market (days 0-200)
    trend = np.cumsum(np.random.randn(200) * 0.005 + 0.001)  # Upward trend
    noise = np.random.randn(200) * 0.01
    bull_prices = 100 * np.exp(trend + noise)
    bull_volumes = np.random.randint(1000000, 2000000, 200)
    
    # Bear market (days 200-400)
    trend = np.cumsum(np.random.randn(200) * 0.005 - 0.002)  # Downward trend
    noise = np.random.randn(200) * 0.015  # Higher volatility
    bear_prices = bull_prices[-1] * np.exp(trend + noise)
    bear_volumes = np.random.randint(1500000, 3000000, 200)
    
    # High volatility period (days 400-600)
    trend = np.cumsum(np.random.randn(200) * 0.002)  # Flat trend
    noise = np.random.randn(200) * 0.03  # Very high volatility
    high_vol_prices = bear_prices[-1] * np.exp(trend + noise)
    high_vol_volumes = np.random.randint(2000000, 5000000, 200)
    
    # Sideways market (days 600-800)
    trend = np.cumsum(np.random.randn(200) * 0.001)  # Very flat trend
    noise = np.random.randn(200) * 0.008  # Low volatility
    sideways_prices = high_vol_prices[-1] * np.exp(trend + noise)
    sideways_volumes = np.random.randint(800000, 1500000, 200)
    
    # Crisis period (days 800-1000)
    trend = np.cumsum(np.random.randn(200) * 0.01 - 0.005)  # Sharp decline
    noise = np.random.randn(200) * 0.05  # Extreme volatility
    crisis_prices = sideways_prices[-1] * np.exp(trend + noise)
    crisis_volumes = np.random.randint(3000000, 8000000, 200)
    
    # Combine all periods
    all_prices = np.concatenate([bull_prices, bear_prices, high_vol_prices, sideways_prices, crisis_prices])
    all_volumes = np.concatenate([bull_volumes, bear_volumes, high_vol_volumes, sideways_volumes, crisis_volumes])
    
    return {
        'prices': all_prices.tolist(),
        'volumes': all_volumes.tolist(),
        'dates': dates,
        'regimes': ['bull_market'] * 200 + ['bear_market'] * 200 + ['high_volatility'] * 200 + 
                  ['sideways'] * 200 + ['crisis'] * 200
    }


def demo_regime_detection():
    """Demo the market regime detection system."""
    print("=== Advanced Market Regime Detection Demo ===\n")
    
    # Generate sample data
    print("Generating sample market data with different regimes...")
    data = generate_sample_market_data()
    
    print(f"Generated {len(data['prices'])} days of data")
    print("Regimes: Bull Market (0-200), Bear Market (200-400), High Volatility (400-600),")
    print("         Sideways (600-800), Crisis (800-1000)")
    
    # Test different configurations
    configs = [
        {
            "name": "Standard",
            "config": {
                "vol_period": 20,
                "vol_threshold_low": 0.15,
                "vol_threshold_high": 0.35,
                "vol_threshold_extreme": 0.50,
                "trend_period": 50,
                "trend_threshold": 0.02,
                "clustering_window": 60,
                "crisis_vol_mult": 2.0,
                "crisis_drawdown_threshold": 0.20
            }
        },
        {
            "name": "Sensitive",
            "config": {
                "vol_period": 15,
                "vol_threshold_low": 0.10,
                "vol_threshold_high": 0.25,
                "vol_threshold_extreme": 0.35,
                "trend_period": 30,
                "trend_threshold": 0.015,
                "clustering_window": 40,
                "crisis_vol_mult": 1.5,
                "crisis_drawdown_threshold": 0.15
            }
        },
        {
            "name": "Conservative",
            "config": {
                "vol_period": 30,
                "vol_threshold_low": 0.20,
                "vol_threshold_high": 0.40,
                "vol_threshold_extreme": 0.60,
                "trend_period": 75,
                "trend_threshold": 0.03,
                "clustering_window": 90,
                "crisis_vol_mult": 2.5,
                "crisis_drawdown_threshold": 0.25
            }
        }
    ]
    
    for config_info in configs:
        print(f"\n--- Testing {config_info['name']} Configuration ---")
        
        # Create detector
        detector = MarketRegimeDetector(config_info["config"])
        
        # Process data day by day
        detected_regimes = []
        regime_confidences = []
        
        for i in range(50, len(data['prices'])):  # Start after minimum data requirement
            prices_window = data['prices'][:i+1]
            volumes_window = data['volumes'][:i+1]
            timestamps_window = data['dates'][:i+1]
            
            result = detector.detect_regime(prices_window, volumes_window, timestamps_window)
            
            detected_regimes.append(result["regime"])
            regime_confidences.append(result["confidence"])
        
        # Analyze results
        print(f"Regime detection results:")
        
        # Count detected regimes
        regime_counts = {}
        for regime in detected_regimes:
            regime_counts[regime] = regime_counts.get(regime, 0) + 1
        
        for regime, count in regime_counts.items():
            percentage = count / len(detected_regimes) * 100
            print(f"  {regime}: {count} days ({percentage:.1f}%)")
        
        # Calculate accuracy for known periods
        accuracy_scores = {}
        known_regimes = data['regimes'][50:]  # Match detected regime indices
        
        for i, (detected, known) in enumerate(zip(detected_regimes, known_regimes)):
            if known not in accuracy_scores:
                accuracy_scores[known] = []
            accuracy_scores[known].append(1 if detected == known else 0)
        
        print(f"\nAccuracy by regime:")
        for regime, scores in accuracy_scores.items():
            accuracy = np.mean(scores) * 100
            print(f"  {regime}: {accuracy:.1f}%")
        
        # Overall accuracy
        overall_accuracy = np.mean([1 if d == k else 0 for d, k in zip(detected_regimes, known_regimes)]) * 100
        avg_confidence = np.mean(regime_confidences) * 100
        print(f"\nOverall accuracy: {overall_accuracy:.1f}%")
        print(f"Average confidence: {avg_confidence:.1f}%")


def demo_regime_analysis():
    """Demo advanced regime analysis features."""
    print("\n=== Advanced Regime Analysis Demo ===\n")
    
    # Generate data
    data = generate_sample_market_data()
    
    # Create detector with standard config
    detector = MarketRegimeDetector()
    
    # Process all data
    print("Processing full dataset...")
    for i in range(50, len(data['prices'])):
        prices_window = data['prices'][:i+1]
        volumes_window = data['volumes'][:i+1]
        timestamps_window = data['dates'][:i+1]
        
        detector.detect_regime(prices_window, volumes_window, timestamps_window)
    
    # Get regime statistics
    stats = detector.get_regime_statistics()
    print(f"\nRegime Statistics:")
    print(f"Total observations: {stats['total_observations']}")
    print(f"Number of transitions: {stats['num_transitions']}")
    
    print(f"\nRegime Distribution:")
    for regime, percentage in stats['regime_percentages'].items():
        print(f"  {regime}: {percentage:.1f}%")
    
    print(f"\nAverage Confidence by Regime:")
    for regime, confidence in stats['avg_confidence_by_regime'].items():
        print(f"  {regime}: {confidence:.3f}")
    
    # Get regime transitions
    transitions = detector.get_regime_transitions()
    print(f"\nRegime Transitions (first 10):")
    for i, transition in enumerate(transitions[:10]):
        print(f"  {i+1}. {transition['from_regime']} → {transition['to_regime']} "
              f"(confidence: {transition['confidence']:.3f})")
    
    # Analyze regime persistence
    print(f"\nRegime Persistence Analysis:")
    history = detector.get_regime_history(days=50)
    
    if history:
        regime_changes = 0
        for i in range(1, len(history)):
            if history[i]['regime'] != history[i-1]['regime']:
                regime_changes += 1
        
        persistence = 1.0 - (regime_changes / len(history))
        print(f"  Recent persistence: {persistence:.3f}")
        print(f"  Regime changes in last 50 days: {regime_changes}")


def demo_indicator_analysis():
    """Demo detailed indicator analysis."""
    print("\n=== Indicator Analysis Demo ===\n")
    
    # Generate data
    data = generate_sample_market_data()
    
    # Create detector
    detector = MarketRegimeDetector()
    
    # Process data and analyze indicators at specific points
    analysis_points = [250, 500, 750, 900]  # Different regime periods
    
    for point in analysis_points:
        if point < len(data['prices']):
            prices_window = data['prices'][:point+1]
            volumes_window = data['volumes'][:point+1]
            timestamps_window = data['dates'][:point+1]
            
            result = detector.detect_regime(prices_window, volumes_window, timestamps_window)
            
            print(f"Analysis at day {point} (Expected: {data['regimes'][point]}):")
            print(f"  Detected regime: {result['regime']}")
            print(f"  Confidence: {result['confidence']:.3f}")
            
            indicators = result['indicators']
            print(f"  Key indicators:")
            print(f"    Volatility: {indicators.get('volatility', 0):.3f}")
            print(f"    Trend strength: {indicators.get('trend_strength', 0):.3f}")
            print(f"    Trend direction: {indicators.get('trend_direction', 0):.3f}")
            print(f"    Crisis probability: {indicators.get('crisis_probability', 0):.3f}")
            print(f"    Stress level: {indicators.get('stress_level', 0):.3f}")
            print(f"    Volume trend: {indicators.get('volume_trend', 0):.3f}")
            print()


if __name__ == "__main__":
    demo_regime_detection()
    demo_regime_analysis()
    demo_indicator_analysis()
    
    print("\n=== Demo Complete ===")
    print("\nKey Features of Market Regime Detection:")
    print("1. VOLATILITY CLUSTERING: Detects periods of persistent high/low volatility")
    print("2. TREND ANALYSIS: Identifies trend strength and direction using regression")
    print("3. CRISIS DETECTION: Recognizes extreme market stress conditions")
    print("4. REGIME PERSISTENCE: Tracks regime stability and transitions")
    print("5. MULTI-INDICATOR SYNTHESIS: Combines multiple signals for robust classification")
    print("\nDetected Regimes:")
    print("- BULL MARKET: Strong uptrend with moderate volatility")
    print("- BEAR MARKET: Strong downtrend with moderate volatility")
    print("- SIDEWAYS: Range-bound with low volatility")
    print("- HIGH VOLATILITY: Elevated volatility regardless of trend")
    print("- CRISIS: Extreme volatility and stress conditions")
    print("- TRANSITION: Unclear or changing market conditions")
