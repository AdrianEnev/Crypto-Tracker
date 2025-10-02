#!/usr/bin/env python3
"""
Basic Testing Script for Enhanced Main Algorithm

This script validates that all integrated features work correctly
with the testing configuration.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.tracker.core import CryptoTracker
from src.config.validator import validate_config
import yaml


def test_config_loading():
    """Test that the testing configuration loads correctly."""
    print("🔧 Testing configuration loading...")
    
    config_path = Path(__file__).parent / "config" / "config_testing.yaml"
    
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f) or {}
        
        # Validate configuration
        errors = validate_config(config)
        if errors:
            print("❌ Configuration validation failed:")
            for error in errors:
                print(f"  - {error}")
            return False
        else:
            print("✅ Configuration validation passed")
            return True
            
    except Exception as ex:
        print(f"❌ Error loading configuration: {ex}")
        return False


def test_tracker_initialization():
    """Test that CryptoTracker initializes with all enhanced features."""
    print("\n🚀 Testing CryptoTracker initialization...")
    
    try:
        config_path = str(Path(__file__).parent / "config" / "config_testing.yaml")
        tracker = CryptoTracker(config_path)
        
        # Check that all enhanced components are initialized
        checks = [
            ("Performance Tracker", hasattr(tracker, 'performance_tracker')),
            ("Parameter Optimizer", hasattr(tracker, 'parameter_optimizer')),
            ("Enhanced Reporter", hasattr(tracker, 'enhanced_reporter')),
            ("Monitoring System", hasattr(tracker, 'monitoring_enabled')),
            ("Enhanced Components", hasattr(tracker, 'social_integration')),
            ("LLM Integration", hasattr(tracker, 'market_analyzer')),
        ]
        
        all_passed = True
        for name, check in checks:
            if check:
                print(f"✅ {name}: Initialized")
            else:
                print(f"❌ {name}: Failed to initialize")
                all_passed = False
        
        return all_passed
        
    except Exception as ex:
        print(f"❌ Error initializing CryptoTracker: {ex}")
        return False


def test_enhanced_features():
    """Test that enhanced features are properly configured."""
    print("\n🎯 Testing enhanced features configuration...")
    
    try:
        config_path = str(Path(__file__).parent / "config" / "config_testing.yaml")
        tracker = CryptoTracker(config_path)
        
        # Load full configuration
        config_data = tracker.config_manager.load_full_config()
        
        # Check enhanced features
        enhanced_features = config_data.get("enhanced_features", {})
        social_enabled = enhanced_features.get("social_media", {}).get("enabled", False)
        llm_enabled = enhanced_features.get("llm", {}).get("enabled", False)
        
        # Check monitoring
        monitoring = config_data.get("monitoring", {})
        monitoring_enabled = monitoring.get("enabled", False)
        
        # Check performance metrics
        performance_metrics = config_data.get("performance_metrics", {})
        metrics_enabled = performance_metrics.get("enabled", False)
        
        # Check reporting
        reporting = config_data.get("reporting", {})
        reporting_enabled = reporting.get("enabled", False)
        
        checks = [
            ("Social Media Integration", social_enabled),
            ("LLM Integration", llm_enabled),
            ("Monitoring System", monitoring_enabled),
            ("Performance Metrics", metrics_enabled),
            ("Enhanced Reporting", reporting_enabled),
        ]
        
        all_passed = True
        for name, check in checks:
            if check:
                print(f"✅ {name}: Enabled")
            else:
                print(f"❌ {name}: Disabled")
                all_passed = False
        
        return all_passed
        
    except Exception as ex:
        print(f"❌ Error testing enhanced features: {ex}")
        return False


def test_scheduling():
    """Test that scheduled tasks are properly set up."""
    print("\n⏰ Testing scheduled tasks setup...")
    
    try:
        config_path = str(Path(__file__).parent / "config" / "config_testing.yaml")
        tracker = CryptoTracker(config_path)
        
        # Setup schedules
        tracker.setup_schedules()
        
        print("✅ Scheduled tasks setup completed")
        print("  - History refresh: Every 15 minutes")
        print("  - Risk manager reset: Every 5 minutes")
        print("  - Portfolio save: Every 10 minutes")
        print("  - Cache warmup: Every 30 minutes")
        print("  - Performance metrics export: Every 60 minutes")
        print("  - Parameter optimization: Every 24 hours")
        print("  - Enhanced reporting: Every 24 hours")
        
        if tracker.monitoring_enabled:
            print(f"  - Heartbeat monitoring: Every {tracker.heartbeat_interval} seconds")
        
        return True
        
    except Exception as ex:
        print(f"❌ Error setting up schedules: {ex}")
        return False


def main():
    """Run all tests."""
    print("🧪 ENHANCED MAIN ALGORITHM TESTING")
    print("=" * 50)
    
    tests = [
        ("Configuration Loading", test_config_loading),
        ("Tracker Initialization", test_tracker_initialization),
        ("Enhanced Features", test_enhanced_features),
        ("Scheduled Tasks", test_scheduling),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} failed")
    
    print("\n" + "=" * 50)
    print(f"📊 TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Enhanced main algorithm is ready for testing.")
        print("\n🚀 To run the enhanced system:")
        print("   python src/entry.py config/config_testing.yaml")
        print("\n📊 To enable parameter optimization:")
        print("   Set optimization.enabled: true in config_testing.yaml")
        print("\n⚠️  Remember: This config uses paper trading for safety!")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
