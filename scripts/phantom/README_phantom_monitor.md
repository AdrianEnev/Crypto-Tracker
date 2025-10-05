# Phantom Memecoin Monitor

A Python script that monitors trending memecoins on Phantom's explore page and alerts when changes are detected in the top 10 list. This helps discover new memecoins early and track emerging trends.

## Features

- 🔥 **Real-time Monitoring**: Continuously monitors Phantom's trending memecoins using Selenium
- 🚨 **Change Detection**: Alerts when tokens are added, removed, or change position
- 📊 **Rich Console Output**: Beautiful tables and panels using Rich library
- 📝 **JSON Logging**: Saves all changes to JSON files for analysis
- ⚙️ **Configurable**: Customizable check intervals, alert thresholds, and more
- 🎯 **Early Discovery**: Helps catch memecoins right after insiders start trading

## Installation

1. Install dependencies:
```bash
pip install selenium beautifulsoup4 requests rich
```

2. Make sure Chrome/Chromium is installed (required for Selenium)

3. Make sure you're in the project directory:
```bash
cd /path/to/tracker
```

## Usage

### Single Check
Run a single check to see current trending memecoins:
```bash
python scripts/phantom_memecoin_monitor.py --single
```

### Continuous Monitoring
Start continuous monitoring (default: checks every 30 seconds):
```bash
python scripts/phantom_memecoin_monitor.py
```

### Configuration

The script uses configuration from `config/config.yaml`. Key settings:

```yaml
phantom_monitor:
  check_interval: 30  # seconds between checks
  alert_threshold: 1  # minimum changes to trigger alert
  max_history: 100    # maximum change history entries
  enable_notifications: true
  log_changes: true
```

## How It Works

1. **Data Fetching**: Uses Selenium WebDriver to load Phantom's explore page with JavaScript
2. **Change Detection**: Compares current list with previous to detect changes
3. **Alerting**: Shows alerts when new tokens appear or positions change
4. **Logging**: Saves all changes to JSON files in `scripts/logs/`

## Output

The script displays:
- Current top 10 trending memecoins in a table
- Alerts when changes are detected
- Token names, prices, and 24h changes
- Real-time data from Phantom's website

## Logs

Change logs are saved to:
- `scripts/logs/phantom_monitor.log` - General log file
- `scripts/logs/phantom_changes_YYYYMMDD.jsonl` - Daily change logs

## Requirements

- **Python 3.7+**
- **Chrome/Chromium browser** (for Selenium WebDriver)
- **Selenium** (automatically installed with requirements.txt)

## Troubleshooting

### Chrome/Chromium Issues
If you get Chrome driver errors:
```bash
# On macOS with Homebrew
brew install chromedriver

# On Ubuntu/Debian
sudo apt-get install chromium-chromedriver
```

### Dependencies
Make sure all required packages are installed:
```bash
pip install -r requirements.txt
```

## Example Output

```
🔥 Phantom Trending Memecoins                          
┏━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ R… ┃ Token            ┃ Price       ┃ 24h      ┃ Raw Data                    ┃
┡━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 1  │ PANDU            │ $0.00016324 │ +30.89%  │ PANDU +30.89%               │
│ 2  │ DOGHOUSE         │ $0.00023662 │ +132.78% │ DOGHOUSE +132.78%           │
│ 3  │ $GREMLY          │ $0.00000001 │ +67.63%  │ $GREMLY +67.63%             │
│ 4  │ PAPER            │ $0.00010171 │ -36.39%  │ PAPER -36.39%               │
└────┴──────────────────┴─────────────┴──────────┴─────────────────────────────┘
```

## Integration

This script can be integrated with your existing trading system to:
- Automatically discover new memecoins
- Trigger alerts for position changes
- Log data for backtesting strategies
- Monitor insider activity patterns

## Notes

- Uses Selenium WebDriver for reliable JavaScript content extraction
- Monitors Phantom's explore page every 30 seconds by default
- Filters out navigation elements and focuses on actual token data
- Provides real-time alerts for maximum trading opportunities
