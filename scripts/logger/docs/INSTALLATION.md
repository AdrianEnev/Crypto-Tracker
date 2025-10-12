# Installation & Testing Guide

## Prerequisites

Ensure you're in the project's virtual environment:

```bash
cd /Users/adrian/Desktop/Code/Trading/tracker
source .venv/bin/activate
```

All required dependencies are already in `requirements.txt`:
- ✅ ccxt==4.3.42
- ✅ pyyaml==6.0.1
- ✅ python-dotenv==1.0.0
- ✅ boto3>=1.26.0

## Quick Validation (30 seconds)

Run the quick test suite:

```bash
cd scripts/logger
python quick_test.py
```

Expected output:
```
1️⃣  Testing configuration... ✅
2️⃣  Testing email connection... ✅
3️⃣  Testing exchange connection... ✅
4️⃣  Testing price fetch... ✅ (BTC: $92,450.23)
5️⃣  Testing markdown logs... ✅

Results: 5/5 tests passed
🎉 All tests passed! System is ready to run.
```

## Individual Component Tests

### Test Email System
```bash
python test_email.py
```

This will:
1. Test SMTP connection to Amazon SES
2. Optionally send a test email

### Test Price Fetching
```bash
python test_price_fetcher.py
```

This will:
1. Connect to Binance exchange
2. Fetch prices for BTC, ETH, SOL, ADA, DOT
3. Show rate limiter status

## Configuration

### 1. Update Email Recipient

Edit `config/alert_config.yaml`:

```yaml
global:
  email_recipient: your@email.com  # ← CHANGE THIS!
```

### 2. Configure Alerts

Add or modify alerts in `config/alert_config.yaml`:

```yaml
alerts:
  - id: alert_001
    name: "ASTER Price Target"
    cryptocurrency: ASTER
    symbol: ASTER/USDT
    condition: ">="
    target_price: 1.805
    enabled: true
```

## Running the Logger

### Dry Run (No Emails)
```bash
python crypto_price_logger.py --dry-run
```

Press Ctrl+C after verifying it starts correctly.

### Production Run
```bash
python crypto_price_logger.py
```

The system will:
- Check prices every 60 seconds
- Send email alerts when conditions are met
- Log progress to `markdown_logs/`
- Run until you press Ctrl+C

## Monitoring

### View Logs in Real-Time
```bash
tail -f markdown_logs/progress.md
```

### Check Alert History
```bash
cat markdown_logs/alerts_history.md
```

### Check for Errors
```bash
cat markdown_logs/errors.md
```

## Running 24/7

See `QUICKSTART.md` for instructions on setting up as a background service.

## Troubleshooting

### "No module named 'yaml'" or similar

Make sure you're in the virtual environment:
```bash
source /Users/adrian/Desktop/Code/Trading/tracker/.venv/bin/activate
```

### "Email connection test failed"

Check your `.env` file has the correct SES credentials:
- SES_SMTP_HOST
- SES_SMTP_PORT
- SES_SMTP_USER
- SES_SMTP_PASS
- EMAIL_FROM

### "Exchange connection failed"

Check your internet connection and try again. Binance public API doesn't require authentication.

### "Symbol not found"

Verify the symbol exists on Binance:
- Visit https://www.binance.com/en/markets
- Use format: CRYPTO/USDT (e.g., BTC/USDT, not BTCUSDT)

## File Permissions

For security, set appropriate permissions:

```bash
chmod 600 config/alert_config.yaml
chmod 700 *.py
```

## Next Steps

1. ✅ Run `python quick_test.py` to validate setup
2. ✅ Update `email_recipient` in config
3. ✅ Run `python crypto_price_logger.py --dry-run` to test
4. ✅ Run `python crypto_price_logger.py` for production
5. ✅ Set up as background service (optional)

---

**Need help?** Check `README.md` for detailed documentation.
