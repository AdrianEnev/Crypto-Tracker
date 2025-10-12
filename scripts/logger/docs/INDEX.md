# Crypto Price Logger - Documentation Index

Welcome! This directory contains a complete 24/7 cryptocurrency price monitoring system with email alerts.

## 🚀 Getting Started (Choose Your Path)

### Path 1: Super Quick (5 minutes)
1. Read: [`QUICKSTART.md`](QUICKSTART.md)
2. Update email in `config/alert_config.yaml`
3. Run: `./start.sh --dry-run`

### Path 2: Detailed Setup (15 minutes)
1. Read: [`INSTALLATION.md`](INSTALLATION.md)
2. Run tests: `python quick_test.py`
3. Configure alerts: `config/alert_config.yaml`
4. Deploy: Follow service setup instructions

### Path 3: Full Understanding (30 minutes)
1. Read: [`PROJECT_SUMMARY.md`](PROJECT_SUMMARY.md)
2. Read: [`README.md`](README.md)
3. Review code: `crypto_price_logger.py`
4. Customize and deploy

---

## 📚 Documentation Files

### Quick Reference
- **[QUICKSTART.md](QUICKSTART.md)** - Get running in 5 minutes
- **[INSTALLATION.md](INSTALLATION.md)** - Detailed installation guide
- **[INDEX.md](INDEX.md)** - This file

### Comprehensive Guides
- **[README.md](README.md)** - Complete documentation (400+ lines)
  - Features and architecture
  - Configuration guide
  - Deployment instructions
  - Troubleshooting
  - Advanced usage

- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Project overview
  - What was built
  - Architecture diagram
  - File structure
  - Performance metrics
  - Future roadmap

### Trading Automation (NEW! 🔥)
- **[TRADING_GUIDE.md](TRADING_GUIDE.md)** - Complete trading guide (8,000+ words)
  - Trading strategies explained
  - Risk management
  - Exit strategies
  - Paper trading
  - Live trading setup
  
- **[TRADING_SYSTEM_SUMMARY.md](TRADING_SYSTEM_SUMMARY.md)** - System overview
  - Architecture and components
  - How it works
  - Quick start guide
  - Best practices
  
- **[AUTO_INCREMENT_FEATURE.md](AUTO_INCREMENT_FEATURE.md)** - Auto-increment feature
  - Dynamic target adjustment
  - Ladder strategies
  - Configuration examples

### Configuration
- **[config/alert_config.yaml](config/alert_config.yaml)** - Main configuration
- **[config/config_example.yaml](config/config_example.yaml)** - Example template

---

## 🔧 Core Scripts

### Main Application
- **`crypto_price_logger.py`** - Main monitoring script
  - Usage: `python crypto_price_logger.py [--config FILE] [--dry-run]`
  - 400+ lines of production-ready code

### Supporting Modules
- **`email_notifier.py`** - Amazon SES email system
- **`rate_limiter.py`** - API rate limiting
- **`start.sh`** - Quick start helper script

### Trading Modules (NEW! 🔥)
- **`trading_executor.py`** - Trade execution engine (500+ lines)
  - Order placement and management
  - Position tracking
  - Risk management
  - Paper trading simulation
  
- **`strategy_manager.py`** - Strategy coordination (300+ lines)
  - Alert-triggered trading
  - Strategy execution
  - Safety checks
  - Position updates

### Testing Scripts
- **`quick_test.py`** - Fast validation (< 30 seconds)
  - Tests all components
  - Usage: `python quick_test.py`

- **`test_email.py`** - Email system testing
  - Tests SMTP connection
  - Sends test email
  - Usage: `python test_email.py`

- **`test_price_fetcher.py`** - Exchange testing
  - Tests price fetching
  - Shows rate limiter status
  - Usage: `python test_price_fetcher.py`

---

## 📊 Monitoring & Logs

### Markdown Logs (Auto-Updated)
- **`markdown_logs/progress.md`** - System progress and heartbeats
- **`markdown_logs/alerts_history.md`** - Table of triggered alerts
- **`markdown_logs/todo.md`** - Feature roadmap
- **`markdown_logs/errors.md`** - Error tracking

### Viewing Logs
```bash
# Watch progress in real-time
tail -f markdown_logs/progress.md

# View alert history
cat markdown_logs/alerts_history.md

# Check for errors
cat markdown_logs/errors.md
```

---

## 🎯 Common Tasks

### First Time Setup
```bash
# 1. Navigate to directory
cd /Users/adrian/Desktop/Code/Trading/tracker/scripts/logger

# 2. Activate virtual environment
source ../../.venv/bin/activate

# 3. Update email in config
nano config/alert_config.yaml

# 4. Run quick test
python quick_test.py

# 5. Test run (no emails)
python crypto_price_logger.py --dry-run

# 6. Production run
python crypto_price_logger.py
```

### Adding New Alerts
```bash
# Edit configuration
nano config/alert_config.yaml

# Add new alert:
# - id: alert_new
#   name: "My Alert"
#   cryptocurrency: Bitcoin
#   symbol: BTC/USDT
#   condition: ">="
#   target_price: 95000
#   enabled: true

# Changes take effect within 60 seconds (no restart needed)
```

### Running as Service

**macOS**:
```bash
# See QUICKSTART.md section "Run 24/7"
launchctl load ~/Library/LaunchAgents/com.crypto.price.logger.plist
```

**Linux**:
```bash
sudo systemctl enable crypto-price-logger
sudo systemctl start crypto-price-logger
```

### Troubleshooting
```bash
# Test email
python test_email.py

# Test price fetching
python test_price_fetcher.py

# Check errors
cat markdown_logs/errors.md

# Run with debug logging
# Edit config/alert_config.yaml:
# logging:
#   console_level: debug
```

---

## 📁 File Structure

```
scripts/logger/
├── Documentation
│   ├── INDEX.md                 ← You are here
│   ├── QUICKSTART.md            ← 5-minute guide
│   ├── INSTALLATION.md          ← Setup guide
│   ├── README.md                ← Full documentation
│   └── PROJECT_SUMMARY.md       ← Project overview
│
├── Core Scripts
│   ├── crypto_price_logger.py   ← Main script
│   ├── email_notifier.py        ← Email system
│   ├── rate_limiter.py          ← Rate limiting
│   └── start.sh                 ← Quick start helper
│
├── Testing
│   ├── quick_test.py            ← Fast validation
│   ├── test_email.py            ← Email testing
│   └── test_price_fetcher.py    ← Exchange testing
│
├── Configuration
│   └── config/
│       ├── alert_config.yaml    ← Your config
│       └── config_example.yaml  ← Template
│
├── Logs (Auto-Generated)
│   └── markdown_logs/
│       ├── progress.md          ← Progress log
│       ├── alerts_history.md    ← Alert history
│       ├── todo.md              ← Roadmap
│       └── errors.md            ← Error log
│
└── Deployment
    └── crypto-price-logger.service  ← Systemd service
```

---

## 🎓 Learning Path

### Beginner
1. Read [`QUICKSTART.md`](QUICKSTART.md)
2. Run `./start.sh --dry-run`
3. Watch `markdown_logs/progress.md`

### Intermediate
1. Read [`README.md`](README.md) - Configuration section
2. Customize `config/alert_config.yaml`
3. Set up as background service

### Advanced
1. Read [`PROJECT_SUMMARY.md`](PROJECT_SUMMARY.md) - Architecture
2. Review source code
3. Extend functionality (see `markdown_logs/todo.md`)

---

## 🔗 Quick Links

### Configuration
- [Alert Configuration](config/alert_config.yaml)
- [Example Config](config/config_example.yaml)
- [Environment Variables](../../.env)

### Logs
- [Progress Log](markdown_logs/progress.md)
- [Alert History](markdown_logs/alerts_history.md)
- [Error Log](markdown_logs/errors.md)
- [Todo List](markdown_logs/todo.md)

### Documentation
- [Full README](README.md)
- [Quick Start](QUICKSTART.md)
- [Installation](INSTALLATION.md)
- [Project Summary](PROJECT_SUMMARY.md)

---

## ❓ FAQ

**Q: How do I get started?**
A: Read [`QUICKSTART.md`](QUICKSTART.md) and run `./start.sh --dry-run`

**Q: How do I add more alerts?**
A: Edit `config/alert_config.yaml` and add new alert entries

**Q: How do I run 24/7?**
A: See the "Run 24/7" section in [`QUICKSTART.md`](QUICKSTART.md)

**Q: Where are the logs?**
A: Check `markdown_logs/` directory

**Q: How do I test without sending emails?**
A: Run with `--dry-run` flag: `python crypto_price_logger.py --dry-run`

**Q: Something's not working, what do I do?**
A: Run `python quick_test.py` and check `markdown_logs/errors.md`

---

## 📞 Support

1. Check [`README.md`](README.md) - Troubleshooting section
2. Run `python quick_test.py` to diagnose issues
3. Review `markdown_logs/errors.md` for error details
4. Test components individually:
   - `python test_email.py`
   - `python test_price_fetcher.py`

---

## ✅ Checklist

Before running in production:

- [ ] Updated `email_recipient` in `config/alert_config.yaml`
- [ ] Ran `python quick_test.py` successfully
- [ ] Tested with `--dry-run` flag
- [ ] Configured desired alerts
- [ ] Reviewed security settings
- [ ] Set up log monitoring

---

**Ready to start? Run:** `./start.sh --dry-run`

**Need help? Read:** [`QUICKSTART.md`](QUICKSTART.md)

**Want details? Read:** [`README.md`](README.md)
