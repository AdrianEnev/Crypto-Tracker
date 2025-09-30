#!/bin/bash
# Quick setup and test for News API integration

echo "🚀 Setting up News API integration..."

# Set the API key
export NEWS_API_KEY="64a0dabedd4b416aa2affe08f84ded36"

echo "✅ API key set: $NEWS_API_KEY"

# Test the integration
echo "🧪 Testing News API integration..."
python3 test_news_api.py

echo "🎯 If the test passed, you can now run:"
echo "  python3 crypto_discovery_scanner.py"
echo "  python3 quick_crypto_scanner.py"
