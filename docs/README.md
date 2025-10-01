# Social Media Integration Documentation

This directory contains comprehensive documentation for the social media integration system.

## 📚 Documentation Structure

### API Setup Guides
- **[Twitter API Setup](api_setup/TWITTER_API_SETUP.md)** - Configure Twitter API for social metrics
- **[Reddit API Setup](api_setup/REDDIT_API_SETUP.md)** - Configure Reddit API for subreddit monitoring

### Integration Guides
- **[Cost Optimization Plan](COST_OPTIMIZATION_PLAN.md)** - Complete cost savings strategy
- **[Crypto Discovery Guide](CRYPTO_DISCOVERY_GUIDE.md)** - Using the crypto discovery scanner
- **[Testing Guide](TESTING_GUIDE.md)** - How to test the integration

## 🎯 Quick Start

### 1. Set Up API Keys
```bash
# Twitter API (optional - free tier available)
export TWITTER_API_KEY="your_twitter_api_key"
export TWITTER_BEARER_TOKEN="your_twitter_bearer_token"

# Reddit API (optional - free tier available)
export REDDIT_CLIENT_ID="your_reddit_client_id"
export REDDIT_CLIENT_SECRET="your_reddit_client_secret"

# Dune Analytics (optional - free tier available)
export DUNE_API_KEY="your_dune_api_key"

# News API (you already have this)
export NEWS_API_KEY="your_news_api_key"

# Santiment (you already have this)
export SANTIMENT_API_KEY="your_santiment_api_key"
```

### 2. Run Tests
```bash
# Run all integration tests
python3 tests/run_integration_tests.py

# Run specific tests
python3 tests/integration/test_twitter_integration.py
python3 tests/integration/test_reddit_integration.py
python3 tests/integration/test_exchange_api_integration.py
python3 tests/integration/test_dune_analytics_integration.py
```

### 3. Use the Scanner
```bash
# Run crypto discovery scanner
python3 crypto_discovery_scanner.py

# Run quick scanner
python3 quick_crypto_scanner.py
```

## 💰 Cost Savings Summary

| Service | Replaced | Monthly Savings |
|---------|----------|----------------|
| Twitter API | LunarCrush | $1000+ |
| Reddit API | LunarCrush | $500+ |
| Exchange APIs | CryptoQuant | $1000+ |
| Dune Analytics | Glassnode | $1000+ |
| **Total** | | **$3500+** |

## 🔧 Data Sources

### Enabled by Default (No API Keys Required)
- **Google Trends** - Search trend analysis
- **Exchange APIs** - Funding rates, open interest, derivatives data

### Optional (Require API Keys)
- **Santiment** - Social + on-chain data (you have API key)
- **News API** - Headline sentiment analysis (you have API key)
- **Twitter API** - Social metrics and engagement
- **Reddit API** - Subreddit monitoring and sentiment
- **Dune Analytics** - On-chain metrics and whale movements

## 📊 Features Provided

### Social Signals
- Social volume and engagement metrics
- Sentiment analysis from multiple sources
- Hot topic identification
- Influencer activity tracking

### Market Data
- Real-time funding rates from 5 exchanges
- Open interest and long/short ratios
- Exchange flow analysis
- Derivatives market sentiment

### On-chain Data
- Transaction volume and active addresses
- Whale movement tracking
- DeFi TVL and protocol metrics
- Network activity analysis

### Trend Analysis
- Google Trends integration
- Search volume patterns
- Interest tracking over time

## 🚀 Production Ready

The system is production-ready with:
- ✅ Comprehensive error handling
- ✅ Rate limiting and caching
- ✅ Configurable data sources
- ✅ Real-time monitoring
- ✅ Cost-effective operation

## 📞 Support

For questions or issues:
1. Check the specific API setup guides
2. Run the integration tests
3. Review the testing guide
4. Check the cost optimization plan for details
