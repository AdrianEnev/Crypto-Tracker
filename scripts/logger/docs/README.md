# Crypto Price Logger

A lightweight 24/7 cryptocurrency price monitoring system that sends email alerts via Amazon SES when specific price targets are reached.

## 🎯 Features

- **Real-time Price Monitoring**: Track cryptocurrency prices using CCXT exchange integration
- **Email Alerts**: Receive instant notifications via Amazon SES when price conditions are met
- **Rate Limiting**: Intelligent API rate limiting to respect exchange limits
- **Markdown Logging**: Track progress, alerts, and errors in human-readable markdown files
- **Alert Cooldown**: Prevent spam with configurable cooldown periods
- **24/7 Operation**: Designed to run continuously as a system service
- **Minimal Resource Usage**: ~50-100MB RAM, <1% CPU
- **Graceful Error Handling**: Automatic retry with exponential backoff

## 📁 Directory Structure

```
scripts/logger/
├── README.md                    # This file
├── crypto_price_logger.py       # Main monitoring script
├── email_notifier.py            # Amazon SES email sender
├── rate_limiter.py              # API rate limiting utilities
├── test_email.py                # Test email functionality
├── test_price_fetcher.py        # Test price fetching
├── crypto-price-logger.service  # Systemd service file
├── config/
│   ├── alert_config.yaml        # Your alert configurations
│   └── config_example.yaml      # Example configuration
└── markdown_logs/
    ├── progress.md              # Progress tracking
    ├── todo.md                  # Todo list
    ├── alerts_history.md        # Alert history
    └── errors.md                # Error tracking
```

## 🚀 Quick Start

### 1. Prerequisites

Ensure you have the required dependencies (already in project's `requirements.txt`):
- `ccxt==4.3.42`
- `pyyaml==6.0.1`
- `python-dotenv==1.0.0`
- `boto3>=1.26.0`

### 2. Configure Environment Variables

Your `.env` file should already contain the Amazon SES credentials:

```bash
***REMOVED***
***REMOVED***
***REMOVED***
***REMOVED***
***REMOVED***
***REMOVED***
***REMOVED***
***REMOVED***
```

### 3. Configure Alerts

Edit `config/alert_config.yaml`:

```yaml
global:
  check_interval_seconds: 60
  alert_cooldown_minutes: 60
  email_recipient: your@email.com  # CHANGE THIS!

exchange:
  name: binance
  enable_rate_limit: true
  max_requests_per_minute: 60

alerts:
  - id: alert_001
    name: "ASTER Price Target"
    cryptocurrency: ASTER
    symbol: ASTER/USDT
    condition: ">="
    target_price: 1.805
    enabled: true
```

**Important**: Update `email_recipient` with your actual email address!

### 4. Test the System

```bash
# Navigate to logger directory
cd scripts/logger

# Test email system
python test_email.py

# Test price fetching
python test_price_fetcher.py

# Dry run (no emails sent)
python crypto_price_logger.py --dry-run
```

### 5. Run Manually

```bash
# Run with default config
python crypto_price_logger.py

# Run with custom config
python crypto_price_logger.py --config config/my_alerts.yaml

# Stop with Ctrl+C
```

## 🔧 Configuration Guide

### Alert Conditions

- `>=` - Alert when price is **greater than or equal** to target (price going up)
- `<=` - Alert when price is **less than or equal** to target (price going down)
- `==` - Alert when price **equals** target (within 0.1% tolerance)

### Example Configurations

#### Monitor Price Increase
```yaml
- id: moon_shot
  name: "Solana Moon Shot"
  cryptocurrency: Solana
  symbol: SOL/USDT
  condition: ">="
  target_price: 200
  enabled: true
```

#### Monitor Price Decrease (Buy Opportunity)
```yaml
- id: dip_alert
  name: "Bitcoin Dip"
  cryptocurrency: Bitcoin
  symbol: BTC/USDT
  condition: "<="
  target_price: 85000
  enabled: true
```

#### Temporarily Disable Alert
```yaml
- id: eth_alert
  name: "Ethereum Target"
  cryptocurrency: Ethereum
  symbol: ETH/USDT
  condition: ">="
  target_price: 4000
  enabled: false  # Won't trigger
```

#### Auto-Increment Target (NEW!)
```yaml
- id: aster_ladder
  name: "ASTER Ladder Alert"
  cryptocurrency: ASTER
  symbol: ASTER/USDT
  condition: ">="
  target_price: 1.40
  enabled: true
  auto_increment: true      # Auto-update target after alert
  increment_amount: 0.05    # Increase by $0.05 each time
```

**How it works:**
- When ASTER reaches $1.40, email is sent
- Target automatically updates to $1.45
- Next alert triggers at $1.45, then $1.50, etc.
- Perfect for tracking upward trends!

**For downward alerts (<=):**
```yaml
- id: btc_dip_ladder
  name: "Bitcoin Dip Ladder"
  cryptocurrency: Bitcoin
  symbol: BTC/USDT
  condition: "<="
  target_price: 90000
  enabled: true
  auto_increment: true
  increment_amount: 1000    # Decrease by $1000 each time
```
- Alerts at $90k, then $89k, then $88k, etc.

### Finding Symbol Names

Use the test script to find available symbols:

```bash
python test_price_fetcher.py
```

Or check the exchange directly:
- Binance: https://www.binance.com/en/markets
- Format: `CRYPTO/USDT` (e.g., `BTC/USDT`, `ETH/USDT`, `SOL/USDT`)

## 🖥️ Running as a Service (24/7)

### macOS (launchd)

1. Create launch agent:

```bash
# Create plist file
cat > ~/Library/LaunchAgents/com.crypto.price.logger.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.crypto.price.logger</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/adrian/Desktop/Code/Trading/tracker/.venv/bin/python3</string>
        <string>/Users/adrian/Desktop/Code/Trading/tracker/scripts/logger/crypto_price_logger.py</string>
        <string>--config</string>
        <string>config/alert_config.yaml</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/adrian/Desktop/Code/Trading/tracker/scripts/logger</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/adrian/Desktop/Code/Trading/tracker/scripts/logger/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/adrian/Desktop/Code/Trading/tracker/scripts/logger/stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/Users/adrian/Desktop/Code/Trading/tracker/.venv/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
EOF

# Load the service
launchctl load ~/Library/LaunchAgents/com.crypto.price.logger.plist

# Start the service
launchctl start com.crypto.price.logger
```

2. Manage the service:

```bash
# Check status
launchctl list | grep crypto

# Stop service
launchctl stop com.crypto.price.logger

# Unload service
launchctl unload ~/Library/LaunchAgents/com.crypto.price.logger.plist

# View logs
tail -f ~/Desktop/Code/Trading/tracker/scripts/logger/stdout.log
tail -f ~/Desktop/Code/Trading/tracker/scripts/logger/stderr.log
```

### Linux (systemd)

1. Install service:

```bash
# Copy service file
sudo cp crypto-price-logger.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable crypto-price-logger

# Start service
sudo systemctl start crypto-price-logger
```

2. Manage the service:

```bash
# Check status
sudo systemctl status crypto-price-logger

# Stop service
sudo systemctl stop crypto-price-logger

# Restart service
sudo systemctl restart crypto-price-logger

# View logs
sudo journalctl -u crypto-price-logger -f

# View recent logs
sudo journalctl -u crypto-price-logger -n 100
```

## 📊 Monitoring

### Markdown Logs

The system maintains several markdown log files:

#### `markdown_logs/progress.md`
Tracks system operation, heartbeats, and alerts:
```markdown
### 2025-10-12 14:32:15 - Alert Triggered
- **Alert**: ASTER Price Target
- **Cryptocurrency**: ASTER
- **Current Price**: $1.80500000
- **Status**: ✅ Email Sent
```

#### `markdown_logs/alerts_history.md`
Table of all triggered alerts:
```markdown
| Timestamp | Cryptocurrency | Condition | Target | Actual | Status |
|-----------|---------------|-----------|--------|--------|--------|
| 2025-10-12 14:32:15 | ASTER | >= | $1.805 | $1.805 | ✅ Sent |
```

#### `markdown_logs/errors.md`
Error tracking and debugging:
```markdown
### 2025-10-12 15:20:00
- **Error**: SMTP timeout after 30 seconds
```

### Console Output

By default, only warnings and errors are shown. To see more:

```yaml
# In config/alert_config.yaml
logging:
  console_level: info  # Show heartbeats and alerts
```

## 🔍 Troubleshooting

### Email Not Sending

1. Test email configuration:
```bash
python test_email.py
```

2. Check `.env` file has correct SES credentials

3. Verify SES sending limits in AWS console

4. Check `markdown_logs/errors.md` for details

### Prices Not Fetching

1. Test exchange connection:
```bash
python test_price_fetcher.py
```

2. Verify symbol format (e.g., `BTC/USDT` not `BTCUSDT`)

3. Check if symbol is available on the exchange

4. Review rate limiter settings

### Service Not Starting

**macOS:**
```bash
# Check logs
tail -f ~/Desktop/Code/Trading/tracker/scripts/logger/stderr.log

# Verify plist syntax
plutil ~/Library/LaunchAgents/com.crypto.price.logger.plist
```

**Linux:**
```bash
# Check service status
sudo systemctl status crypto-price-logger

# View detailed logs
sudo journalctl -u crypto-price-logger -n 50
```

### High CPU/Memory Usage

1. Increase check interval:
```yaml
global:
  check_interval_seconds: 120  # Check every 2 minutes
```

2. Reduce number of alerts

3. Check for errors in `markdown_logs/errors.md`

## 🔒 Security Best Practices

1. **Never commit `.env` file** - Already gitignored
2. **Use SES IAM user with minimal permissions** - Only `ses:SendEmail`
3. **Rotate credentials regularly** - Every 30-60 days
4. **Monitor SES usage** - Check AWS console for anomalies
5. **Set file permissions**:
```bash
chmod 600 .env
chmod 600 config/alert_config.yaml
```

## 📈 Performance

- **Memory**: ~50-100 MB
- **CPU**: <1% average
- **Network**: 1-5 KB per price check
- **Disk**: <10 MB logs per month

## 🛠️ Advanced Usage

### Multiple Alert Configurations

Run different instances for different strategies:

```bash
# Conservative alerts
python crypto_price_logger.py --config config/conservative.yaml

# Aggressive alerts
python crypto_price_logger.py --config config/aggressive.yaml
```

### Custom Rate Limits

Adjust in `config/alert_config.yaml`:

```yaml
exchange:
  name: binance
  max_requests_per_minute: 30  # More conservative
```

### Logging Levels

```yaml
logging:
  console_level: debug    # debug, info, warning, error
  file_level: debug
  log_api_calls: true     # Log every API call
```

## 📝 Maintenance

### Daily Tasks
- Review `markdown_logs/alerts_history.md` for triggered alerts
- Check `markdown_logs/errors.md` for issues

### Weekly Tasks
- Review and update `markdown_logs/todo.md`
- Verify service is running: `launchctl list | grep crypto` (macOS) or `systemctl status crypto-price-logger` (Linux)

### Monthly Tasks
- Archive old log entries (>30 days)
- Review alert configurations
- Check SES sending quota

## 🔄 Updating Configuration

The system automatically reloads configuration every check interval. To update alerts:

1. Edit `config/alert_config.yaml`
2. Save the file
3. Changes take effect on next check (no restart needed)

## 🐛 Debugging

Enable detailed logging:

```yaml
logging:
  console_level: debug
  file_level: debug
  log_api_calls: true
```

Then run:
```bash
python crypto_price_logger.py
```

Watch for detailed output including API calls and rate limiting.

## 📞 Support

For issues or questions:
1. Check `markdown_logs/errors.md`
2. Review this README
3. Test components individually (`test_email.py`, `test_price_fetcher.py`)
4. Check exchange status (e.g., Binance status page)

## 📄 License

Part of the Crypto Tracker project.

---

**Happy Monitoring! 🚀**
