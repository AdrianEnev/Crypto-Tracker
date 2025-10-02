#!/bin/bash
# Setup script for Intelligence System

echo "🚀 Setting up Intelligence System..."

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements_intelligence.txt

# Download NLTK data
echo "📚 Downloading NLTK data..."
python -c "import nltk; nltk.download('punkt'); nltk.download('vader_lexicon')"

# Download TextBlob corpora
echo "📚 Downloading TextBlob corpora..."
python -m textblob.download_corpora

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs
mkdir -p models
mkdir -p data/cache

# Set up environment variables template
echo "📝 Creating .env template..."
cat > .env.template << EOF
# Twitter API
TWITTER_API_KEY=your_twitter_bearer_token_here

# Reddit API
REDDIT_CLIENT_ID=your_reddit_client_id_here
REDDIT_CLIENT_SECRET=your_reddit_client_secret_here

# OpenAI (for LLM)
OPENAI_API_KEY=your_openai_api_key_here

# On-chain data uses free APIs (no keys required)
# Free APIs: Etherscan, Blockchair, mempool.space

# Optional: Telegram alerts
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here

# Optional: Email alerts
EMAIL_PASSWORD=your_email_password_here
EOF

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Copy .env.template to .env and fill in your API keys"
echo "2. Run: source .env"
echo "3. Test the system: python scripts/test_intelligence.py"
echo "4. Start paper trading: python src/entry.py"
