# 🚀 Crypto Discovery Scanner - Usage Guide

## What It Does

The Crypto Discovery Scanner uses your social media integration to identify cryptocurrencies that might be trending or about to spike in growth. It scans multiple coins and ranks them by social momentum, sentiment, and volume velocity.

## Quick Start

### 1. **Set Your API Key**
```bash
export SANTIMENT_API_KEY="your_santiment_api_key_here"
```

### 2. **Run Quick Scanner** (Recommended for beginners)
```bash
python3 quick_crypto_scanner.py
```

### 3. **Run Full Scanner** (More comprehensive)
```bash
python3 crypto_discovery_scanner.py
```

## What You'll See

### **Sample Output**
```
🚀 QUICK CRYPTO DISCOVERY SCAN
============================================================
📅 Scan Time: 2024-01-15 14:30:25
🔍 Coins Scanned: 20

🏆 TOP OPPORTUNITIES
------------------------------------------------------------
🔥  1. SOLANA           | Score:  67.3 | SMS:  0.234 | Sentiment:  0.156 | Risk: low    | Valid: True
📈  2. CARDANO          | Score:  54.2 | SMS:  0.189 | Sentiment:  0.123 | Risk: low    | Valid: True
📈  3. POLKADOT         | Score:  48.7 | SMS:  0.167 | Sentiment:  0.098 | Risk: medium | Valid: True
👀  4. CHAINLINK        | Score:  42.1 | SMS:  0.145 | Sentiment:  0.087 | Risk: low    | Valid: True
👀  5. AVALANCHE-2      | Score:  38.9 | SMS:  0.134 | Sentiment:  0.076 | Risk: medium | Valid: True

💡 QUICK RECOMMENDATIONS
------------------------------------------------------------
Research these top 3 coins:
1. SOLANA (Score: 67.3)
2. CARDANO (Score: 54.2)
3. POLKADOT (Score: 48.7)

Safe picks (low risk, validated):
1. SOLANA (Score: 67.3)
2. CARDANO (Score: 54.2)
3. CHAINLINK (Score: 42.1)
```

## Understanding the Scores

### **Discovery Score (0-100)**
- **80-100**: 🔥 Very high social activity - research immediately
- **60-79**: 📈 High social activity - strong potential
- **40-59**: 👀 Moderate social activity - worth watching
- **20-39**: 📊 Low social activity - monitor
- **0-19**: 💤 Minimal social activity - skip for now

### **Key Metrics**
- **SMS (Social Momentum Score)**: Overall social media momentum
- **Sentiment**: Positive/negative sentiment (-1 to +1)
- **Volume Velocity**: How fast social mentions are growing
- **Risk Level**: low/medium/high based on validation
- **Valid**: Whether the signal passed cross-validation

## How to Use the Results

### **1. Research Phase**
- Look up the top-scoring coins on CoinGecko, CoinMarketCap
- Check recent news and developments
- Look at their fundamentals and use cases
- Check social media for recent discussions

### **2. Add to Watchlist**
- Add promising coins to your trading watchlist
- Set up price alerts
- Monitor their social signals over time

### **3. Paper Trading**
- Test the coins with paper trading first
- See how they perform with your existing strategies
- Monitor their social signals vs. price movements

### **4. Gradual Integration**
- Start with small positions if trading
- Use the social signals as additional confirmation
- Don't rely solely on social signals

## Scanner Types

### **Quick Scanner** (`quick_crypto_scanner.py`)
- **Scans**: 20 most popular cryptocurrencies
- **Speed**: Fast (2-3 minutes)
- **Use case**: Daily quick checks
- **Best for**: Beginners, regular monitoring

### **Full Scanner** (`crypto_discovery_scanner.py`)
- **Scans**: 50+ cryptocurrencies across all categories
- **Speed**: Slower (5-10 minutes)
- **Use case**: Comprehensive weekly scans
- **Best for**: Deep research, finding hidden gems

## Categories Scanned

- **Major Coins**: Bitcoin, Ethereum, etc.
- **Altcoins**: Popular alternatives
- **DeFi Tokens**: Decentralized finance projects
- **Layer 2**: Scaling solutions
- **Meme Coins**: High social activity coins
- **AI Tokens**: Artificial intelligence projects
- **Gaming**: Metaverse and gaming tokens
- **Infrastructure**: Storage and infrastructure
- **Privacy**: Privacy-focused coins

## Safety Features

- **Cross-validation**: Social signals must be confirmed by on-chain data
- **Bot detection**: Identifies potential manipulation
- **Quality scoring**: Only high-quality signals pass through
- **Risk assessment**: Multi-level risk evaluation
- **Validation requirements**: Signals must pass validation checks

## Tips for Best Results

### **1. Run Regularly**
- Quick scanner: Daily
- Full scanner: Weekly
- Compare results over time

### **2. Focus on Trends**
- Look for coins that consistently score high
- Watch for sudden score increases
- Monitor sentiment changes

### **3. Combine with Other Analysis**
- Use social signals as additional confirmation
- Don't ignore technical analysis
- Check fundamentals and news

### **4. Start Small**
- Begin with paper trading
- Use small positions initially
- Gradually increase as you gain confidence

## Troubleshooting

### **"No results found"**
- Check if social media integration is enabled
- Verify your Santiment API key
- Check network connectivity

### **"Low scores"**
- This is normal - most coins have low social activity
- Focus on coins with scores > 20
- Run scans at different times of day

### **"High bot likelihood"**
- Be cautious with these coins
- They might be manipulated
- Look for validated signals instead

## Example Workflow

1. **Morning**: Run quick scanner
2. **Research**: Look up top 3-5 coins
3. **Add to watchlist**: Promising coins
4. **Monitor**: Watch their social signals
5. **Paper trade**: Test with small amounts
6. **Weekly**: Run full scanner for comprehensive view

## Integration with Trading System

You can integrate these discoveries into your trading system:

1. **Add to config**: Add promising coins to your `tracked_coins`
2. **Monitor signals**: Use the social signals in your strategies
3. **Set alerts**: Get notified when scores change significantly
4. **Track performance**: See how social signals correlate with price

---

**⚠️ Important**: This is a research tool. Always do your own research before making any trading decisions. Social media signals should supplement, not replace, your analysis.
