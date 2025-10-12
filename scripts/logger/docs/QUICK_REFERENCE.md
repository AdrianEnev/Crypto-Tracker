# Quick Reference Card - Trading Automation

## 🚀 Enable Trading (3 Steps)

### 1. Enable in Main Config
```yaml
# config/alert_config.yaml
trading:
  enabled: true
  paper_trading: true  # Start here!
```

### 2. Configure Strategy
```yaml
# config/trading_config.yaml
strategies:
  - id: aster_strategy
    enabled: true
    trigger:
      type: alert
      alert_id: alert_001
    entry:
      side: BUY
      position_size_usd: 50.0
    exit:
      stop_loss_pct: 3.0
      take_profit_pct: 7.0
```

### 3. Link Alert to Strategy
```yaml
# config/trading_config.yaml
alert_trading:
  rules:
    - alert_id: alert_001
      action: BUY
      strategy_id: aster_strategy
```

---

## 📊 Monitor Trading

### View Trades
```bash
tail -f markdown_logs/trades.md
```

### Check Positions
```bash
cat trading_positions.json | python -m json.tool
```

### Watch Terminal
```bash
python crypto_price_logger.py
# Look for [STRATEGY] and [PAPER TRADE] messages
```

---

## ⚙️ Common Configurations

### Conservative (Low Risk)
```yaml
risk:
  max_position_size_usd: 50.0
  max_loss_per_trade_pct: 1.0
  max_open_positions: 3

strategy exit:
  stop_loss_pct: 2.0
  take_profit_pct: 4.0  # 2:1 reward:risk
```

### Moderate (Medium Risk)
```yaml
risk:
  max_position_size_usd: 100.0
  max_loss_per_trade_pct: 2.0
  max_open_positions: 5

strategy exit:
  stop_loss_pct: 3.0
  take_profit_pct: 7.0  # 2.3:1 reward:risk
  trailing_stop: true
```

### Aggressive (Higher Risk)
```yaml
risk:
  max_position_size_usd: 200.0
  max_loss_per_trade_pct: 3.0
  max_open_positions: 8

strategy exit:
  stop_loss_pct: 5.0
  take_profit_pct: 15.0  # 3:1 reward:risk
  partial_exits: true
```

---

## 🎯 Strategy Templates

### Alert-Triggered Entry
```yaml
strategies:
  - id: alert_entry
    trigger:
      type: alert
      alert_id: alert_001
    entry:
      side: BUY
      position_size_usd: 100.0
    exit:
      stop_loss_pct: 2.0
      take_profit_pct: 5.0
```

### DCA (Buy Every 24h)
```yaml
strategies:
  - id: btc_dca
    trigger:
      type: time_based
      interval_hours: 24
    entry:
      symbol: BTCUSDT
      fixed_usd_amount: 50.0
    exit:
      take_profit_pct: 20.0
```

### Breakout Trading
```yaml
strategies:
  - id: breakout
    trigger:
      type: price_breakout
      symbol: ETHUSDT
      breakout_price: 3500.0
    entry:
      side: BUY
    exit:
      stop_loss_pct: 3.0
      take_profit_pct: 10.0
```

---

## 🛡️ Risk Settings

### Position Sizing Methods

**Risk-Based** (Recommended):
```yaml
risk:
  position_sizing:
    method: risk_based
    risk_per_trade_usd: 20.0
```

**Fixed USD**:
```yaml
risk:
  position_sizing:
    method: fixed_usd
    fixed_position_size_usd: 100.0
```

**Account Percentage**:
```yaml
risk:
  position_sizing:
    method: fixed_percent
    account_percent: 10.0
```

---

## 📈 Exit Strategy Options

### Basic
```yaml
exit:
  stop_loss_pct: 2.0
  take_profit_pct: 5.0
```

### With Trailing Stop
```yaml
exit:
  stop_loss_pct: 2.0
  take_profit_pct: 5.0
  trailing_stop: true
  trailing_stop_pct: 1.5
```

### Partial Exits
```yaml
exit:
  partial_exits:
    - profit_pct: 2.0
      position_pct: 30.0
    - profit_pct: 4.0
      position_pct: 30.0
  trailing_stop: true
  trailing_stop_pct: 2.0
```

### Time-Based
```yaml
exit:
  stop_loss_pct: 3.0
  take_profit_pct: 10.0
  max_hold_time_hours: 48
```

---

## 🔧 Troubleshooting

### Symbol Not Found
```yaml
# ❌ Wrong
symbol: ASTER/USDC

# ✅ Correct
symbol: ASTER/USDT  # or ASTERUSDT
```

### Trading Not Executing
Check:
1. `trading.enabled: true` in alert_config.yaml
2. Strategy `enabled: true`
3. Alert properly linked in `alert_trading.rules`
4. Symbol format correct (USDT not USDC)

### Stop-Loss Hitting Too Often
```yaml
# Increase stop-loss percentage
exit:
  stop_loss_pct: 5.0  # Wider stop
```

### Position Size Too Large
```yaml
# Reduce position size
risk:
  max_position_size_usd: 50.0
entry:
  position_size_usd: 50.0
```

---

## 📁 File Locations

| File | Purpose |
|------|---------|
| `config/alert_config.yaml` | Price alerts + trading toggle |
| `config/trading_config.yaml` | Full trading configuration |
| `trading_positions.json` | Active positions (auto-generated) |
| `markdown_logs/trades.md` | Trade history log |
| `markdown_logs/progress.md` | System progress |

---

## 🎓 Safety Checklist

Before going live:
- [ ] Tested in paper trading for 1+ week
- [ ] All strategies have stop-loss configured
- [ ] Position sizes are small (start with minimum)
- [ ] Risk limits are conservative
- [ ] API key has correct permissions (no withdraw)
- [ ] IP whitelist enabled on Binance
- [ ] Emergency stop plan documented
- [ ] Monitoring system in place

---

## 🚨 Emergency Procedures

### Stop All Trading Immediately
```yaml
# config/alert_config.yaml
trading:
  enabled: false  # ← Change this
```

Then restart the logger.

### Close All Positions Manually
1. Go to Binance web interface
2. Navigate to Spot Trading
3. Close positions manually
4. Document in trades.md

### Circuit Breaker Triggered
```yaml
# Wait for cooldown period (default 60 min)
# Or reset in trading_config.yaml:
safety:
  circuit_breaker:
    cooldown_minutes: 0  # Reset immediately (not recommended)
```

---

## 📞 Quick Commands

```bash
# Start logger with trading
python crypto_price_logger.py

# Start with dry-run (no emails, no trades)
python crypto_price_logger.py --dry-run

# Test system components
python quick_test.py

# View trades in real-time
tail -f markdown_logs/trades.md

# Check positions
cat trading_positions.json

# View errors
cat markdown_logs/errors.md

# Make executable
chmod +x crypto_price_logger.py
```

---

## 💡 Pro Tips

1. **Start with ONE strategy** - Don't enable all at once
2. **Use trailing stops** - Protect profits automatically
3. **Paper trade first** - Test for at least a week
4. **Review daily** - Check trades.md every day
5. **Small positions** - Start with minimum sizes
6. **Document changes** - Note why you adjusted settings
7. **Set alerts** - Monitor performance metrics
8. **Have a plan** - Know entry/exit before trading
9. **Risk first** - Protect capital above profits
10. **Stay disciplined** - Follow your strategy

---

## 🔗 Documentation Links

- **Full Guide**: [TRADING_GUIDE.md](TRADING_GUIDE.md)
- **System Overview**: [TRADING_SYSTEM_SUMMARY.md](TRADING_SYSTEM_SUMMARY.md)
- **General Docs**: [README.md](README.md)
- **Navigation**: [INDEX.md](INDEX.md)

---

## 📊 Performance Tracking

Track these metrics:
- **Win Rate**: % of profitable trades
- **Avg Profit**: Average $ per winning trade
- **Avg Loss**: Average $ per losing trade
- **Profit Factor**: Total profit / Total loss
- **Max Drawdown**: Largest % portfolio decline

Log in markdown_logs/trades.md and calculate weekly.

---

**Print this page for quick reference while trading! 📄**
