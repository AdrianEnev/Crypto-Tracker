# Crypto Insider Discovery & Tracking System

A comprehensive system for discovering and tracking crypto "insiders" - wallets that consistently make early investments in profitable meme coins.

## 🎯 Overview

This system consists of three main components:

1. **Insider Discovery Script** (`insider_discovery.py`) - Finds potential insiders by analyzing early investment patterns
2. **24/7 Insider Tracker** (`insider_tracker.py`) - Monitors identified insiders' wallets in real-time
3. **Wallet Manager** (`manage_insiders.py`) - Manually add, remove, and manage insider wallets

## 🔍 How It Works

### Configuration-Based System

The system uses `config.yaml` to manage tracked wallets:

- **Discovery Script**: Automatically adds new insiders to `insider_tracking.tracked_wallets`
- **Manual Management**: Use `manage_insiders.py` to add wallets to `insider_tracking.manual_wallets`
- **24/7 Tracker**: Reads from both lists and monitors all active wallets

### Insider Discovery Process

1. **Golden Ticket Detection**: Searches for tokens with premium indicators (golden, ticket, boost, VIP, etc.)
2. **Trader Analysis**: Analyzes top traders for early investment patterns
3. **Insider Identification**: Identifies wallets that:
   - Bought low amounts ($50-300)
   - Sold for high amounts ($10k+)
   - Achieved high profit multipliers (20x+)
4. **Config Update**: Automatically adds new insiders to `config.yaml`
5. **Database Storage**: Stores potential insiders for historical tracking

### 24/7 Tracking Process

1. **Config Reading**: Loads tracked wallets from `config.yaml`
2. **Wallet Monitoring**: Continuously monitors insider wallets
3. **Trade Detection**: Detects new buy/sell activities
4. **Profit Analysis**: Analyzes potential profit of new trades
5. **Alert System**: Sends alerts for high-potential trades
6. **Database Updates**: Maintains comprehensive trade history

## 📁 Files

- `scripts/insider_discovery.py` - Main discovery script
- `scripts/insider_tracker.py` - 24/7 tracking script
- `scripts/manage_insiders.py` - Manual wallet management
- `scripts/test_insider_tracker.py` - Test script for tracker functionality
- `data/insiders.db` - SQLite database storing insider data
- `config/config.yaml` - Configuration settings

## 🚀 Usage

### 1. Discover Insiders

```bash
python scripts/insider_discovery.py
```

This will:
- Search for golden ticket tokens
- Analyze trader patterns
- Identify potential insiders
- **Automatically add new insiders to config.yaml**
- Store results in database
- Export findings to JSON

### 2. Manually Manage Wallets

```bash
python scripts/manage_insiders.py
```

Interactive menu:
- **List tracked wallets**
- **Add wallet manually**
- **Remove wallet**
- **Toggle wallet status**

### 3. Start 24/7 Tracking

```bash
python scripts/insider_tracker.py
```

This will:
- Load insiders from config.yaml
- Start continuous monitoring
- Send alerts for new trades
- Update trade history

### 4. Test Tracker

```bash
python scripts/test_insider_tracker.py
```

This will:
- Test database connectivity
- Show current stats
- Verify tracker functionality

## ⚙️ Configuration

The system uses `config.yaml` for all settings:

### Golden Ticket Filters
```yaml
insider_discovery:
  golden_ticket_filters:
    search_terms: ["golden", "ticket", "boost", "premium", "vip"]
    min_volume_24h_usd: 1000000
    min_liquidity_usd: 500000
    max_age_hours: 168
```

### Insider Criteria
```yaml
insider_criteria:
  min_buy_amount_usd: 50
  max_buy_amount_usd: 300
  min_sell_amount_usd: 10000
  min_profit_multiplier: 20
  min_confidence_score: 0.7
```

### Tracked Wallets (Auto-Updated)
```yaml
insider_tracking:
  tracked_wallets:
    - wallet_address: "0x1234567890abcdef1234567890abcdef12345678"
      nickname: "Insider Alpha"
      confidence_score: 0.85
      total_profits_usd: 50000
      successful_trades: 15
      avg_profit_multiplier: 25.5
      added_by: "discovery_script"
      added_at: "2025-10-03T12:00:00"
      is_active: true
```

### Manual Wallets
```yaml
insider_tracking:
  manual_wallets:
    - wallet_address: "0xYourWalletAddressHere"
      nickname: "My Insider"
      confidence_score: 0.9
      added_by: "manual"
      is_active: true
```

## 📊 Database Schema

### Insiders Table
- `wallet_address` - Unique wallet identifier
- `total_profits_usd` - Total profits across all trades
- `successful_trades` - Number of profitable trades
- `total_trades` - Total number of trades
- `avg_profit_multiplier` - Average profit multiplier
- `confidence_score` - Confidence in insider status
- `first_discovered` - When first discovered
- `last_updated` - Last activity timestamp

### Insider Trades Table
- `wallet_address` - Reference to insiders table
- `token_address` - Token contract address
- `token_symbol` - Token symbol
- `trade_type` - 'buy' or 'sell'
- `amount_usd` - Trade amount in USD
- `price_usd` - Token price at time of trade
- `timestamp` - Trade timestamp
- `profit_loss_usd` - Profit/loss from trade
- `profit_multiplier` - Profit multiplier achieved

## 🚨 Alert System

The system can send alerts via:
- Console output
- Log files
- Email (requires setup)
- Discord webhooks (requires setup)
- Telegram bot (requires setup)

### Alert Triggers
- New trades by high-confidence insiders
- Potential profits above threshold
- Significant market movements

## 📈 Example Output

### Discovery Results
```
🎯 DISCOVERED 10 POTENTIAL INSIDERS
================================================================================
Rank Wallet               Buy $      Sell $       Profit     Multiplier   Confidence
================================================================================
1    0x0x7D498449...ins... $150       $25,000      $24,850    166.7x       85.0%     
2    0xGjqpHLGPUt...ins... $200       $18,000      $17,800    90.0x        78.0%     

📝 Added 2 new insiders to tracking config
```

### Manual Wallet Management
```
🔧 Insider Wallet Manager
==============================

Options:
1. List tracked wallets
2. Add wallet manually
3. Remove wallet
4. Toggle wallet status
5. Exit

Enter your choice (1-5): 1

📝 Tracked Wallets (3 total)
================================================================================
Nickname             Address             Status   Confidence Added By        
================================================================================
Insider Alpha        0x1234567890abc... Active   85.0%      discovery_script
Test Insider         0x1234567890abc... Active   90.0%      manual          
```

### Tracking Alerts
```
🚨 INSIDER ALERT 🚨

Wallet: Test Insider (0x1234567890...)
Token: NEWCOIN (New Meme Coin)
Action: BUY
Amount: $500
Buy Price: $0.000001

📊 ANALYSIS:
Current Price: $0.000001
Volume 24h: $1,000,000
Liquidity: $500,000
Risk Level: MEDIUM
Recommendation: BUY

🔗 DexScreener: https://dexscreener.com/search?q=newcoin
```

## 🔧 Manual Wallet Management

### Adding Wallets Manually

1. Run `python scripts/manage_insiders.py`
2. Choose option 2 (Add wallet manually)
3. Enter wallet address
4. Enter nickname (optional)
5. Enter confidence score (0.0-1.0)

### Example Manual Addition

```bash
# Add a wallet you found manually
python scripts/manage_insiders.py

# Choose option 2, then enter:
# Wallet: 0xYourWalletAddressHere
# Nickname: My Insider
# Confidence: 0.9
```

### Managing Existing Wallets

- **List**: See all tracked wallets
- **Remove**: Remove a wallet from tracking
- **Toggle**: Activate/deactivate a wallet

## ⚠️ Important Notes

1. **Research Only**: This system is for research purposes only
2. **Verify Addresses**: Always verify wallet addresses before making decisions
3. **Risk Management**: Crypto investments are highly risky
4. **API Limits**: Respect DexScreener API rate limits
5. **Config Backup**: Regularly backup your config.yaml file
6. **Database Backup**: Regularly backup the insiders database

## 🔧 Technical Requirements

- Python 3.8+
- aiohttp for async HTTP requests
- sqlite3 for database storage
- PyYAML for config management
- DexScreener API access

## 🚀 Workflow Example

1. **Initial Discovery**:
   ```bash
   python scripts/insider_discovery.py
   # Finds 10 potential insiders, adds them to config
   ```

2. **Manual Addition**:
   ```bash
   python scripts/manage_insiders.py
   # Add wallets you found manually
   ```

3. **Start Tracking**:
   ```bash
   python scripts/insider_tracker.py
   # Monitors all wallets 24/7
   ```

4. **Monitor Results**:
   - Check logs in `logs/insider_tracker.log`
   - Review alerts in console
   - Analyze database for patterns

## 🚀 Future Enhancements

- Blockchain explorer integration (Etherscan, BSCScan)
- Real-time transaction monitoring
- Advanced profit prediction algorithms
- Social media sentiment analysis
- Automated trading integration
- Mobile app notifications
- Web dashboard for monitoring

## 📞 Support

For questions or issues:
1. Check the logs in `logs/insider_tracker.log`
2. Verify database connectivity
3. Check API rate limits
4. Review configuration settings
5. Use `test_insider_tracker.py` for diagnostics

---

**Disclaimer**: This system is for educational and research purposes only. Always do your own research before making investment decisions. Cryptocurrency investments are highly volatile and risky.