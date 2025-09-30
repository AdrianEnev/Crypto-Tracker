#!/bin/bash
# Quick test script for Santiment social media integration

echo "🧪 Testing Santiment Social Media Integration"
echo "=============================================="

# Check if SANTIMENT_API_KEY is set
if [ -z "$SANTIMENT_API_KEY" ]; then
    echo "❌ SANTIMENT_API_KEY not set"
    echo "💡 Set it with: export SANTIMENT_API_KEY='your_api_key'"
    echo "💡 Or create a .env file with your API key"
    exit 1
fi

echo "✅ SANTIMENT_API_KEY is set"

# Install dependencies if needed
echo "📦 Checking dependencies..."
python3 -c "import aiohttp" 2>/dev/null || {
    echo "📥 Installing aiohttp..."
    pip3 install aiohttp
}

python3 -c "import yaml" 2>/dev/null || {
    echo "📥 Installing pyyaml..."
    pip3 install pyyaml
}

# Run the Santiment test
echo "🚀 Running Santiment integration test..."
python3 test_santiment.py

echo ""
echo "📋 Next Steps:"
echo "1. If tests pass, you can run the enhanced paper trading system:"
echo "   python3 scripts/enhanced_paper_trading_24_7.py --config config/paper_24_7.yaml"
echo ""
echo "2. To disable social media integration:"
echo "   python3 scripts/enhanced_paper_trading_24_7.py --disable-social"
echo ""
echo "3. Monitor the logs for social media signals and trading decisions"
