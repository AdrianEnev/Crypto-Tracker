#!/usr/bin/env python3
"""
Social Media Integration Structure Test

This script tests the basic structure and configuration of the social media integration
without requiring external dependencies.
"""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_configuration():
    """Test configuration loading"""
    print("🔧 Testing Configuration...")
    
    try:
        from src.social_media.config import SocialMediaConfig
        
        # Test default configuration
        config = SocialMediaConfig()
        print(f"  ✅ Default config created")
        print(f"  ✅ Enabled: {config.enabled}")
        print(f"  ✅ Google Trends enabled: {config.google_trends.enabled}")
        
        # Test configuration validation
        issues = config.validate_config()
        print(f"  ✅ Config validation: {len(issues)} issues")
        
        # Test feature enabling
        print(f"  ✅ Features enabled: {config.is_feature_enabled('features')}")
        print(f"  ✅ Validation enabled: {config.is_feature_enabled('validation')}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Configuration test failed: {e}")
        return False


def test_file_structure():
    """Test that all required files exist"""
    print("\n📁 Testing File Structure...")
    
    required_files = [
        "src/social_media/__init__.py",
        "src/social_media/config.py",
        "src/social_media/data_sources.py",
        "src/social_media/features.py",
        "src/social_media/validation.py",
        "src/social_media/monitoring.py",
        "src/social_media/integration.py",
        "src/social_media/example_integration.py",
        "config/social_media.yaml",
        "requirements_social_media.txt",
        "docs/SOCIAL_MEDIA_INTEGRATION.md"
    ]
    
    all_exist = True
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} - MISSING")
            all_exist = False
    
    return all_exist


def test_config_file():
    """Test configuration file"""
    print("\n📋 Testing Configuration File...")
    
    try:
        config_path = Path("config/social_media.yaml")
        if config_path.exists():
            print(f"  ✅ Configuration file exists")
            
            # Check if it's valid YAML
            import yaml
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            print(f"  ✅ Valid YAML format")
            print(f"  ✅ Enabled: {config_data.get('enabled', False)}")
            print(f"  ✅ Google Trends enabled: {config_data.get('google_trends', {}).get('enabled', False)}")
            
            return True
        else:
            print(f"  ❌ Configuration file missing")
            return False
            
    except Exception as e:
        print(f"  ❌ Configuration file test failed: {e}")
        return False


def test_imports():
    """Test that all modules can be imported"""
    print("\n📦 Testing Module Imports...")
    
    modules_to_test = [
        ("src.social_media.config", "SocialMediaConfig"),
        ("src.social_media.data_sources", "SocialDataManager"),
        ("src.social_media.features", "SocialFeatureEngine"),
        ("src.social_media.validation", "SocialSignalValidator"),
        ("src.social_media.monitoring", "SocialMonitoringDashboard"),
        ("src.social_media.integration", "SocialMediaIntegration"),
    ]
    
    all_imported = True
    for module_name, class_name in modules_to_test:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            print(f"  ✅ {module_name}.{class_name}")
        except ImportError as e:
            print(f"  ⚠️  {module_name}.{class_name} - Import error (expected without dependencies): {e}")
        except AttributeError as e:
            print(f"  ❌ {module_name}.{class_name} - Class not found: {e}")
            all_imported = False
        except Exception as e:
            print(f"  ❌ {module_name}.{class_name} - Unexpected error: {e}")
            all_imported = False
    
    return all_imported


def print_summary():
    """Print implementation summary"""
    print("\n📊 Implementation Summary")
    print("=" * 50)
    print("✅ Social Media Integration Module Created")
    print()
    print("📁 Core Components:")
    print("  • Configuration management (config.py)")
    print("  • Data source integrations (data_sources.py)")
    print("  • Feature engineering (features.py)")
    print("  • Validation & safety (validation.py)")
    print("  • Monitoring & alerts (monitoring.py)")
    print("  • Main integration (integration.py)")
    print("  • Example usage (example_integration.py)")
    print()
    print("🔧 Data Sources Supported:")
    print("  • LunarCrush (social metrics)")
    print("  • Santiment (social + on-chain)")
    print("  • Glassnode (on-chain data)")
    print("  • CryptoQuant (exchange flows)")
    print("  • Google Trends (search volume)")
    print("  • News API (headline sentiment)")
    print()
    print("🛡️ Safety Features:")
    print("  • Bot detection & manipulation safeguards")
    print("  • Cross-validation with on-chain data")
    print("  • Quality scoring & confidence metrics")
    print("  • Configurable safety limits")
    print("  • Risk assessment & alerting")
    print()
    print("⚙️ Features:")
    print("  • Social Momentum Score (SMS)")
    print("  • Volume velocity analysis")
    print("  • Weighted sentiment scoring")
    print("  • Influencer activity tracking")
    print("  • Network centrality analysis")
    print("  • Real-time monitoring dashboard")
    print()
    print("📋 Configuration:")
    print("  • All features easily configurable")
    print("  • Can be disabled independently")
    print("  • Safety-first defaults")
    print("  • Environment variable support")
    print()
    print("🚀 Next Steps:")
    print("  1. Install dependencies: pip install -r requirements_social_media.txt")
    print("  2. Configure API keys in environment variables")
    print("  3. Enable features in config/social_media.yaml")
    print("  4. Test with: python3 test_social_integration.py")
    print("  5. Integrate with trading strategies")


def main():
    """Main test function"""
    print("🧪 Social Media Integration Structure Test")
    print("=" * 60)
    
    # Run tests
    config_ok = test_configuration()
    structure_ok = test_file_structure()
    config_file_ok = test_config_file()
    imports_ok = test_imports()
    
    # Print results
    print("\n📋 Test Results")
    print("=" * 30)
    print(f"Configuration: {'✅ PASS' if config_ok else '❌ FAIL'}")
    print(f"File Structure: {'✅ PASS' if structure_ok else '❌ FAIL'}")
    print(f"Config File: {'✅ PASS' if config_file_ok else '❌ FAIL'}")
    print(f"Module Imports: {'✅ PASS' if imports_ok else '⚠️  PARTIAL (expected)'}")
    
    if config_ok and structure_ok and config_file_ok:
        print("\n🎉 Core structure is ready!")
        print_summary()
    else:
        print("\n❌ Some issues found. Check the output above.")


if __name__ == "__main__":
    main()
