# Quick Start Guide - Crypto Price Logger

Get your crypto price monitoring system running in 5 minutes!

## ⚡ Quick Setup

### Step 1: Configure Your Email Recipient (30 seconds)

Edit the config file:
```bash
cd /Users/adrian/Desktop/Code/Trading/tracker/scripts/logger
nano config/alert_config.yaml
```

Change this line:
```yaml
email_recipient: your@email.com   # ← CHANGE THIS TO YOUR EMAIL!
```

Save and exit (Ctrl+X, Y, Enter)

### Step 2: Test Email System (30 seconds)

```bash
python test_email.py
```

Expected output:
```
Testing Amazon SES SMTP connection...
✅ SMTP connection successful!
```

If prompted, enter your email to receive a test alert.

### Step 3: Test Price Fetching (30 seconds)

```bash
python test_price_fetcher.py
```

Expected output:
```
✅ Connected to binance
✅ BTC/USDT       $92,450.23
✅ ETH/USDT       $3,845.67
...
```

### Step 4: Run in Dry-Run Mode (1 minute)

Test the full system without sending emails:

```bash
python crypto_price_logger.py --dry-run
```

Press Ctrl+C to stop after you see:
```
[INFO] Crypto Price Logger started at 2025-10-12 14:38:15
[INFO] Monitoring 1 alert(s)
```

### Step 5: Run for Real! (Production)

```bash
python crypto_price_logger.py
```

The system is now monitoring! You'll receive an email when ASTER reaches $1.805.

To stop: Press Ctrl+C

---

## 🎯 Your Current Configuration

The default config monitors:
- **ASTER/USDT** - Alert when price >= $1.805

To add more alerts, edit `config/alert_config.yaml`

---

## 🚀 Run 24/7 (Optional)

### macOS - Run in Background

```bash
# Create launch agent
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
</dict>
</plist>
EOF

# Start the service
launchctl load ~/Library/LaunchAgents/com.crypto.price.logger.plist
launchctl start com.crypto.price.logger

# Check it's running
launchctl list | grep crypto
```

### View Logs

```bash
# Real-time logs
tail -f markdown_logs/progress.md

# Alert history
cat markdown_logs/alerts_history.md

# Errors
cat markdown_logs/errors.md
```

---

## 📝 Adding More Alerts

Edit `config/alert_config.yaml`:

```yaml
alerts:
  # Your existing ASTER alert
  - id: alert_001
    name: "ASTER Price Target"
    cryptocurrency: ASTER
    symbol: ASTER/USDT
    condition: ">="
    target_price: 1.805
    enabled: true
    
  # Add Bitcoin alert
  - id: alert_002
    name: "Bitcoin Dip"
    cryptocurrency: Bitcoin
    symbol: BTC/USDT
    condition: "<="
    target_price: 90000
    enabled: true
    
  # Add Ethereum alert
  - id: alert_003
    name: "Ethereum Moon"
    cryptocurrency: Ethereum
    symbol: ETH/USDT
    condition: ">="
    target_price: 4000
    enabled: true
```

Changes take effect on next check (within 60 seconds) - no restart needed!

---

## 🛑 Stopping the Service

### If running manually:
Press Ctrl+C

### If running as service:
```bash
launchctl stop com.crypto.price.logger
launchctl unload ~/Library/LaunchAgents/com.crypto.price.logger.plist
```

---

## ❓ Troubleshooting

**Email not sending?**
```bash
python test_email.py
```

**Prices not fetching?**
```bash
python test_price_fetcher.py
```

**Need help?**
Check the full README.md for detailed documentation.

---

**You're all set! 🎉**
