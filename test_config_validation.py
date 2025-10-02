#!/usr/bin/env python3
"""
Configuration validation test - validates configs without starting infinite loops
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import yaml
from src.config.validator import validate_config
from src.tracker.core import CryptoTracker


def test_config_loading(config_path: str) -> bool:
    """Test that a configuration file loads and validates correctly."""
    print(f"🔧 Testing configuration: {config_path}")
    
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f) or {}
        
        errors = validate_config(config)
        if errors:
            print("❌ Configuration validation failed:")
            for e in errors:
                print(f"  - {e}")
            return False
        
        print("✅ Configuration validation passed")
        return True
        
    except FileNotFoundError:
        print(f"❌ Error loading configuration: {config_path} not found")
        return False
    except Exception as ex:
        print(f"❌ Error loading configuration: {ex}")
        return False


def test_tracker_initialization(config_path: str) -> bool:
    """Test that CryptoTracker initializes successfully without running."""
    print(f"🚀 Testing CryptoTracker initialization: {config_path}")
    
    try:
        tracker = CryptoTracker(config_path)
        
        print("✅ CryptoTracker initialized successfully!")
        print(f"✅ Monitoring enabled: {tracker.monitoring_enabled}")
        print(f"✅ Performance tracker: {tracker.performance_tracker.enabled}")
        print(f"✅ Parameter optimizer: {tracker.parameter_optimizer.enabled}")
        print(f"✅ Enhanced reporter: {tracker.enhanced_reporter.enabled}")
        print(f"✅ Social integration: {bool(tracker.social_integration)}")
        print(f"✅ Market analyzer: {bool(tracker.market_analyzer)}")
        
        # Test that schedules can be set up without running
        tracker.setup_schedules()
        print("✅ Scheduled tasks setup completed")
        
        return True
        
    except Exception as ex:
        print(f"❌ Error initializing CryptoTracker: {ex}")
        return False


def test_enhanced_features_config(config_path: str) -> bool:
    """Test that enhanced features are correctly configured."""
    print(f"🎯 Testing enhanced features configuration: {config_path}")
    
    try:
        tracker = CryptoTracker(config_path)
        full_config = tracker.config_manager.load_full_config()

        # Check social media
        social_config = full_config.get("enhanced_features", {}).get("social_media", {})
        if social_config.get("enabled"):
            print("✅ Social Media Integration: Enabled")
        else:
            print("ℹ️  Social Media Integration: Disabled")

        # Check LLM
        llm_config = full_config.get("enhanced_features", {}).get("llm", {})
        if llm_config.get("enabled"):
            print("✅ LLM Integration: Enabled")
        else:
            print("ℹ️  LLM Integration: Disabled")

        # Check Monitoring
        monitoring_config = full_config.get("monitoring", {})
        if monitoring_config.get("enabled"):
            print("✅ Monitoring System: Enabled")
        else:
            print("ℹ️  Monitoring System: Disabled")

        # Check Performance Metrics
        performance_config = full_config.get("performance_metrics", {})
        if performance_config.get("enabled"):
            print("✅ Performance Metrics: Enabled")
        else:
            print("ℹ️  Performance Metrics: Disabled")

        # Check Enhanced Reporting
        reporting_config = full_config.get("reporting", {})
        if reporting_config.get("enabled"):
            print("✅ Enhanced Reporting: Enabled")
        else:
            print("ℹ️  Enhanced Reporting: Disabled")

        return True
        
    except Exception as ex:
        print(f"❌ Error testing enhanced features: {ex}")
        return False


def main():
    """Run configuration validation tests."""
    print("🧪 CONFIGURATION VALIDATION TESTING")
    print("==================================================")
    
    # Test configurations
    configs_to_test = [
        "config/config.yaml",
        "config/config_testing.yaml"
    ]
    
    all_passed = True
    
    for config_path in configs_to_test:
        print(f"\n📁 Testing {config_path}")
        print("-" * 50)
        
        # Test 1: Config loading and validation
        if not test_config_loading(config_path):
            all_passed = False
            continue
        
        # Test 2: Tracker initialization
        if not test_tracker_initialization(config_path):
            all_passed = False
            continue
        
        # Test 3: Enhanced features configuration
        if not test_enhanced_features_config(config_path):
            all_passed = False
            continue
        
        print(f"✅ All tests passed for {config_path}")
    
    print("\n==================================================")
    if all_passed:
        print("🎉 ALL CONFIGURATION TESTS PASSED!")
        print("\n📋 Summary:")
        print("  ✅ Main production config (config/config.yaml) is valid")
        print("  ✅ Enhanced testing config (config/config_testing.yaml) is valid")
        print("  ✅ All enhanced features are properly configured")
        print("  ✅ CryptoTracker initializes correctly with both configs")
        print("\n🚀 Ready to run the enhanced system:")
        print("   python src/entry.py config/config_testing.yaml")
        print("\n⚠️  Remember: This will start the infinite trading loop!")
        print("   Use Ctrl+C to stop when testing is complete.")
    else:
        print("❌ Some configuration tests failed.")
        print("   Please check the errors above before running the system.")


if __name__ == "__main__":
    main()
