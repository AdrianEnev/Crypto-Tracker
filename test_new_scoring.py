#!/usr/bin/env python3
"""
Quick Test - New Scoring

Test the new scoring system with the actual values from your scan.
"""

def test_new_scoring():
    """Test the new scoring formula with your actual values."""
    print("🧪 Testing New Scoring Formula")
    print("=" * 40)
    
    # Your actual values from the scan
    sms = 0.060
    sentiment = 0.000
    volume_velocity = 0.0  # Assuming this is also low
    influencer_activity = 0.0  # Assuming this is also low
    
    print(f"Input values:")
    print(f"  SMS: {sms}")
    print(f"  Sentiment: {sentiment}")
    print(f"  Volume Velocity: {volume_velocity}")
    print(f"  Influencer Activity: {influencer_activity}")
    
    # New scoring formula
    base_score = (
        abs(sms) * 0.4 +           # Social momentum
        abs(sentiment) * 0.3 +     # Sentiment strength
        volume_velocity * 0.2 +    # Volume growth
        influencer_activity * 0.1  # Influencer activity
    )
    
    print(f"\nCalculation:")
    print(f"  Base Score: {base_score:.6f}")
    print(f"    SMS component: {abs(sms) * 0.4:.6f}")
    print(f"    Sentiment component: {abs(sentiment) * 0.3:.6f}")
    print(f"    Volume component: {volume_velocity * 0.2:.6f}")
    print(f"    Influencer component: {influencer_activity * 0.1:.6f}")
    
    # Apply multipliers (more realistic)
    quality_multiplier = 0.6  # More realistic minimum
    validation_multiplier = 0.5  # More realistic minimum
    
    discovery_score = base_score * quality_multiplier * validation_multiplier
    
    print(f"\nMultipliers:")
    print(f"  Quality Multiplier: {quality_multiplier}")
    print(f"  Validation Multiplier: {validation_multiplier}")
    print(f"  Score before scaling: {discovery_score:.6f}")
    
    # Final scaling
    final_score = discovery_score * 100  # Back to realistic multiplier
    final_score = min(100.0, max(0.0, final_score))
    
    print(f"\nFinal Score: {final_score:.1f}")
    
    # Test with different scenarios
    print(f"\n📊 Different Scenarios:")
    
    scenarios = [
        ("Current (weak signals)", sms, sentiment, volume_velocity, influencer_activity),
        ("Better SMS", 0.100, sentiment, volume_velocity, influencer_activity),
        ("Some sentiment", sms, 0.050, volume_velocity, influencer_activity),
        ("Volume spike", sms, sentiment, 0.200, influencer_activity),
        ("All improved", 0.100, 0.050, 0.200, 0.100),
    ]
    
    for name, test_sms, test_sentiment, test_volume, test_influencer in scenarios:
        test_base = (
            abs(test_sms) * 0.4 +
            abs(test_sentiment) * 0.3 +
            test_volume * 0.2 +
            test_influencer * 0.1
        )
        test_final = min(100.0, max(0.0, test_base * 0.6 * 0.5 * 100))
        print(f"  {name}: {test_final:.1f}")
    
    print(f"\n✅ With the realistic formula, your scores should be around {final_score:.1f}")
    print(f"✅ This will NOT pass the minimum threshold of 10.0 (as expected with limited data)")
    print(f"✅ But when you add more data sources, scores will increase significantly!")


if __name__ == "__main__":
    test_new_scoring()
