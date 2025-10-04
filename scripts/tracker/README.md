# Tracker Scripts

This folder contains all scripts related to meme coin discovery and insider tracking functionality.

## 📁 Scripts Overview

### 🔍 Discovery Scripts

#### `meme_coin_discovery.py`
- **Purpose**: Discovers potential meme coins using DexScreener API
- **Features**: 
  - Filters by liquidity, market cap, age, holder distribution
  - Calculates risk and potential scores
  - Generates detailed reports with DexScreener links
- **Usage**: `python scripts/tracker/meme_coin_discovery.py`

#### `insider_discovery.py`
- **Purpose**: Finds potential crypto insiders by analyzing golden ticket tokens
- **Features**:
  - Searches for boosted/golden ticket tokens on DexScreener
  - Analyzes trader patterns (low buy, high sell)
  - Automatically updates config with new insiders
- **Usage**: `python scripts/tracker/insider_discovery.py`

### 🔄 Tracking Scripts

#### `insider_tracker.py`
- **Purpose**: 24/7 monitoring of identified insider wallets
- **Features**:
  - Continuous wallet monitoring (30-second intervals)
  - Auto-discovery integration (every 2 hours)
  - Real-time alerts for profitable trades
  - Graceful Ctrl+C shutdown with cleanup
- **Usage**: `python scripts/tracker/insider_tracker.py`

#### `manage_insiders.py`
- **Purpose**: Manual management of insider wallets
- **Features**:
  - Add/remove insider wallets
  - Toggle wallet status
  - List all tracked wallets
  - Interactive wallet management
- **Usage**: `python scripts/tracker/manage_insiders.py`

## ⚙️ Configuration

All scripts use `config/config.yaml` for configuration:

- **Meme Coin Discovery**: `meme_coin_discovery` section
- **Insider Discovery**: `insider_discovery` section  
- **Insider Tracking**: `insider_tracking` section
- **Dynamic Configs**: Stored in `config/dynamic_configs/` directory

## 🚀 Quick Start

1. **Discover Meme Coins**:
   ```bash
   python scripts/tracker/meme_coin_discovery.py
   ```

2. **Find Insiders**:
   ```bash
   python scripts/tracker/insider_discovery.py
   ```

3. **Start 24/7 Tracking**:
   ```bash
   python scripts/tracker/insider_tracker.py
   ```

4. **Manage Wallets**:
   ```bash
   python scripts/tracker/manage_insiders.py
   ```

## 📊 Features

- **Auto-Discovery**: Tracker automatically finds new insiders every 2 hours
- **Fast Monitoring**: 30-second scan intervals to catch price spikes
- **Graceful Shutdown**: Proper cleanup on Ctrl+C
- **Real-time Alerts**: Instant notifications for profitable trades
- **Database Storage**: SQLite database for trade history
- **Config Management**: YAML-based configuration system

## 🔧 Dependencies

- `aiohttp`: Async HTTP requests
- `sqlite3`: Database storage
- `yaml`: Configuration management
- `asyncio`: Async programming
- `logging`: Logging system

## 📈 Performance

- **API Rate Limits**: Respects DexScreener API limits
- **Concurrent Processing**: Up to 15 concurrent wallet scans
- **Memory Efficient**: Minimal memory footprint
- **Error Handling**: Robust error handling and recovery
