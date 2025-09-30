#!/usr/bin/env python3
"""
Social Media Integration Test Runner

Runs all integration tests for the social media data sources.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def run_test(test_name: str, test_file: str):
    """Run a specific test file"""
    print(f"\n{'='*60}")
    print(f"🧪 Running {test_name}")
    print(f"{'='*60}")
    
    try:
        # Import and run the test
        test_module = __import__(f"tests.integration.{test_file.replace('.py', '')}", fromlist=['main'])
        test_module.main()
        print(f"✅ {test_name} completed successfully")
        return True
    except Exception as e:
        print(f"❌ {test_name} failed: {e}")
        return False

def main():
    """Run all integration tests"""
    print("🚀 Social Media Integration Test Suite")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not Path("tests/integration").exists():
        print("❌ Please run this from the project root directory")
        sys.exit(1)
    
    # List of tests to run
    tests = [
        ("Social Media Structure Test", "test_social_structure"),
        ("Santiment Integration", "test_santiment"),
        ("News API Integration", "test_news_api"),
        ("Twitter Integration", "test_twitter_integration"),
        ("Reddit Integration", "test_reddit_integration"),
        ("Exchange API Integration", "test_exchange_api_integration"),
        ("Dune Analytics Integration", "test_dune_analytics_integration"),
        ("Crypto Scanner Test", "test_crypto_scanner"),
        ("New Scoring Test", "test_new_scoring"),
    ]
    
    results = []
    
    for test_name, test_file in tests:
        success = run_test(test_name, test_file)
        results.append((test_name, success))
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 Test Results Summary")
    print(f"{'='*60}")
    
    passed = 0
    failed = 0
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
        else:
            failed += 1
    
    print(f"\n🎯 Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Social media integration is ready.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
