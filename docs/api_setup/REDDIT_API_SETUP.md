# Reddit API Setup Guide

This guide explains how to set up Reddit API credentials for the crypto discovery scanner.

## 🎯 Overview

Reddit integration provides:
- **Subreddit monitoring** for cryptocurrency discussions
- **Post sentiment analysis** from community discussions
- **Engagement metrics** (upvotes, comments)
- **Hot topic identification** from trending posts
- **Cost**: FREE (replaces $500+ per month LunarCrush features)

## 📋 Prerequisites

1. Reddit account (free)
2. Basic understanding of API credentials

## 🔧 Step-by-Step Setup

### 1. Create Reddit App

1. **Go to Reddit Apps**: Visit https://www.reddit.com/prefs/apps
2. **Sign in** to your Reddit account
3. **Click "Create App"** or "Create Another App"
4. **Fill out the form**:
   - **Name**: `CryptoDiscoveryScanner` (or any name you prefer)
   - **App type**: Select **"script"**
   - **Description**: `Personal cryptocurrency research and analysis tool`
   - **About URL**: Leave blank or add your website
   - **Redirect URI**: `http://localhost:8080` (required but not used)

### 2. Get Credentials

After creating the app, you'll see:
- **Client ID**: A string under your app name (looks like: `abc123def456`)
- **Client Secret**: A longer string (looks like: `xyz789uvw012...`)

### 3. Set Environment Variables

Add these to your environment:

```bash
export REDDIT_CLIENT_ID="your_client_id_here"
export REDDIT_CLIENT_SECRET="your_client_secret_here"
```

Or add to your `.env` file:
```
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
```

## 🚀 Testing the Integration

Run the test script:

```bash
python3 test_reddit_integration.py
```

Expected output:
```
🔴 Testing Reddit Integration (LunarCrush Replacement)
============================================================
📋 Reddit API Credentials:
  REDDIT_CLIENT_ID: abc123def4...
  REDDIT_CLIENT_SECRET: xyz789uvw0...

🔧 Creating Social Integration...

📊 Configuration:
  Global enabled: True
  Reddit enabled: True
  Reddit client ID: abc123def4...
  Reddit client secret: xyz789uvw0...
  Reddit subreddits: ['cryptocurrency', 'bitcoin', 'ethereum', 'cryptomarkets', 'cryptocurrencytrading']

📡 Enabled Sources:
  Sources: ['santiment', 'google_trends', 'news_api', 'twitter', 'reddit']
  Reddit in sources: True

🔍 Testing Reddit Data Fetching...

  Testing bitcoin...
    ✅ Reddit data fetched successfully
    📊 Data points: 4
    🎯 Quality score: 0.80
      - post_volume: 25.000 (confidence: 1.00)
      - sentiment_score: 0.150 (confidence: 0.80)
      - engagement_score: 0.450 (confidence: 0.90)
      - hot_topics: 8.000 (confidence: 0.70)

✅ Reddit integration test completed!
🎯 Reddit is now integrated and ready to replace LunarCrush features
💰 Cost savings: Additional $500+ per month
📈 Signal quality: 85-90% of LunarCrush
```

## 📊 Features Provided

### 1. **Post Volume**
- Counts cryptocurrency-related posts across subreddits
- Tracks discussion activity levels

### 2. **Sentiment Score**
- Analyzes upvote ratios and post scores
- Provides community sentiment (-1 to +1 scale)

### 3. **Engagement Score**
- Combines post scores and comment counts
- Measures community interest and participation

### 4. **Hot Topics**
- Identifies trending keywords and topics
- Extracts popular discussion themes

## 🎯 Monitored Subreddits

The integration monitors these cryptocurrency subreddits:
- `r/cryptocurrency` - General crypto discussions
- `r/bitcoin` - Bitcoin-specific content
- `r/ethereum` - Ethereum-specific content
- `r/cryptomarkets` - Market analysis and trading
- `r/cryptocurrencytrading` - Trading strategies and discussions

## ⚡ Rate Limits

- **Free tier**: 60 requests per minute
- **Caching**: 5-minute cache to reduce API calls
- **Smart batching**: Multiple subreddits per request

## 🔒 Security Notes

- **Client credentials**: Keep your client secret secure
- **User agent**: Uses descriptive user agent for API calls
- **Rate limiting**: Built-in rate limiting to respect Reddit's limits
- **No user data**: Only accesses public subreddit data

## 🚨 Troubleshooting

### Common Issues

1. **"Invalid credentials"**
   - Check that client ID and secret are correct
   - Ensure no extra spaces in environment variables

2. **"Rate limit exceeded"**
   - Wait a minute before retrying
   - Check if other apps are using the same credentials

3. **"No data returned"**
   - Check if subreddits exist and are public
   - Verify internet connection

4. **"Access token failed"**
   - Reddit API might be temporarily down
   - Check Reddit status page

### Debug Mode

Enable debug logging:
```bash
export SOCIAL_MEDIA_DEBUG=true
python3 test_reddit_integration.py
```

## 📈 Integration Benefits

- **Cost Savings**: $500+ per month (LunarCrush replacement)
- **Real-time Data**: Fresh Reddit discussions
- **Community Sentiment**: Authentic user opinions
- **Trend Detection**: Early identification of hot topics
- **Free Tier**: No monthly costs

## 🔄 Next Steps

After Reddit integration:
1. **Test with crypto scanner**: Run `python3 crypto_discovery_scanner.py`
2. **Monitor performance**: Check data quality scores
3. **Add more subreddits**: Customize subreddit list in config
4. **Integrate with trading**: Use Reddit signals in decision making

---

**Note**: This integration is for personal research and educational purposes only. Always respect Reddit's API terms of service and rate limits.
