# 🎯 Solana Wallet Tracker

A high-performance real-time wallet tracking system with paper trading capabilities for monitoring the famous memecoin trader's Solana wallet.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Virtual environment activated
- API keys configured in `.env` file

### Running the Wallet Tracker

```bash
# Navigate to the wallet tracker directory
cd scripts/wallet-tracker

# Activate virtual environment
source ../../venv/bin/activate

# Start the wallet tracker
python3 wallet_tracker.py
```

### Stopping the Wallet Tracker

- **First Ctrl+C**: Graceful shutdown with session summary
- **Second Ctrl+C**: Force shutdown

## 📊 Features

### 🔍 Real-Time Monitoring
- **Helius Geyser WebSocket**: Fastest detection method
- **QuickNode Fallback**: Redundant monitoring
- **Sub-second Detection**: Competitive advantage for trading

### 📈 Paper Trading
- **Configurable Balance**: Default $1,000 starting balance
- **3-Second Delay**: Realistic execution simulation
- **Position Sizing**: Configurable % of max position per trade
- **Rich Alerts**: Beautiful console notifications

### 📅 Session Management
- **Daily Sessions**: Auto-incrementing session IDs
- **Graceful Shutdown**: Ctrl+C handling with P&L summary
- **Historical Data**: JSON storage for previous sessions
- **Today-Only Reporting**: Current day P&L on shutdown

## ⚙️ Configuration

### Environment Variables (`.env` file)
```bash
# Required API Keys
HELIUS_API_KEY=your_helius_api_key
QUICKNODE_API_KEY=your_quicknode_api_key

# Wallet Configuration
TARGET_WALLET_ADDRESS=sAdNbe1cKNMDqDsa4npB3TfL62T14uAo2MsUQfLvzLT
TRADER_NAME=Famous Memecoin Trader
```

### Configuration File (`config/wallet_config.yaml`)
```yaml
wallet_tracking:
  paper_trading:
    enabled: true
    initial_balance_usd: 1000
    execution_delay_ms: 3000
    position_size_pct: 0.1
    alerts_enabled: true
    
  session_tracking:
    enabled: true
    save_directory: "sessions"
    daily_summary: true
    graceful_shutdown: true
```

## 📁 File Structure

```
scripts/wallet-tracker/
├── wallet_tracker.py          # Main wallet tracker script
├── paper_trader.py           # Paper trading engine
├── session_manager.py        # Session management
├── config/
│   └── wallet_config.yaml   # Configuration file
├── data/
│   ├── wallet_trades.db     # SQLite database
│   └── sessions/            # Session data directory
└── logs/
    └── wallet_tracker.log   # System logs
```

## 🧪 Testing

### Test Paper Trading System
```bash
python3 test_paper_trading.py
```

### Test Graceful Shutdown
```bash
python3 test_graceful_shutdown.py
```

## 📊 Sample Output

```
🚀 Starting Real Wallet Tracker
👤 Target: Famous Memecoin Trader
📍 Wallet: sAdNbe1cKN...MsUQfLvzLT
⚡ Mode: Helius Geyser WebSocket
📊 Paper Trading: Enabled
💰 Initial Balance: $1,000.00

📈 BOUGHT 'PEPE' for $0.00000123
   💰 Position Size: $100.00 (10.0% of max)
   📊 Portfolio: $1,000.00 → $900.00
   ⏱️  Execution Delay: 3.2s

📉 SOLD 'PEPE' for $0.00000189
   💰 Amount Sold: $153.66
   📊 Portfolio: $900.00 → $1,153.66
   💵 Profit: +$153.66 (+15.37%)

^C
🛑 Received signal 2, initiating graceful shutdown...

📊 Session Summary - 2025-01-05_session_001
💰 Final Balance: $1,153.66
📈 Total Profit: +$153.66 (+15.37%)
📊 Total Trades: 2
✅ Profitable Trades: 1/2 (50.00%)
📅 Session Duration: 6m 40s

✅ Shutdown complete
```

## 🎯 Target Wallet

**Wallet Address**: `sAdNbe1cKNMDqDsa4npB3TfL62T14uAo2MsUQfLvzLT`  
**Trader**: Famous Memecoin Trader  
**Confidence**: High-performance memecoin trading

## 🔧 Troubleshooting

### Common Issues

1. **API Key Errors**: Ensure API keys are correctly set in `.env` file
2. **Connection Issues**: Check internet connection and API key validity
3. **Permission Errors**: Ensure write permissions for `data/` and `logs/` directories

### Logs
Check `logs/wallet_tracker.log` for detailed system logs and error messages.

## 📈 Performance

- **Detection Latency**: < 1 second (Helius Geyser)
- **Paper Trading Delay**: 3 seconds (configurable)
- **Database**: SQLite for fast local storage
- **Session Tracking**: Real-time P&L calculation

---

*Last Updated: January 2025*  
*Status: Production Ready*  
*Version: 1.0.0*