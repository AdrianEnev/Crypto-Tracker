# 24/7 Paper Trading Deployment Guide

## 🚀 Quick Start for 2-Week Test

### Option 1: Manual Startup (Recommended for Testing)
```bash
# Start the system manually
./scripts/paper_trading_24_7.sh start

# Check status
./scripts/paper_trading_24_7.sh status

# View logs
./scripts/paper_trading_24_7.sh logs

# View performance
./scripts/paper_trading_24_7.sh performance

# Stop when done
./scripts/paper_trading_24_7.sh stop
```

### Option 2: Systemd Service (Production)
```bash
# Install the service
sudo cp paper-trading-24-7.service /etc/systemd/system/

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable paper-trading-24-7
sudo systemctl start paper-trading-24-7

# Check status
sudo systemctl status paper-trading-24-7

# View logs
sudo journalctl -u paper-trading-24-7 -f

# Stop service
sudo systemctl stop paper-trading-24-7
```

## 📊 Monitoring Your 2-Week Test

### Key Metrics to Watch:
- **Total Trades**: Should see trades over 2 weeks
- **Win Rate**: Percentage of profitable trades
- **Total Return**: Overall portfolio performance
- **Runtime**: System uptime and stability
- **Restarts**: Should be minimal (0-2 over 2 weeks)

### Log Locations:
- **Main Log**: `logs/paper_trading_24_7_YYYYMMDD_HHMMSS.log`
- **Output**: `logs/paper_trading_24_7.out`
- **Errors**: `logs/paper_trading_24_7.err`

### Expected Behavior:
- **Heartbeat**: Every 5 minutes showing system status
- **Trades**: Should execute when strategies trigger
- **Recovery**: Automatic restart on errors (max 10 times)
- **Performance**: Regular P&L updates

## ⚙️ Configuration

### Current Settings (`config/paper_24_7.yaml`):
- **Initial Cash**: $100,000
- **Check Interval**: 5 minutes (300 seconds)
- **Max Restarts**: 10 attempts
- **Strategies**: Mean reversion + Momentum
- **Risk Management**: Conservative (20% max position, 5% daily loss)

### Customization:
```bash
# Edit config for different settings
nano config/paper_24_7.yaml

# Restart with new config
./scripts/paper_trading_24_7.sh restart
```

## 🔧 Troubleshooting

### If System Stops:
```bash
# Check status
./scripts/paper_trading_24_7.sh status

# Check errors
./scripts/paper_trading_24_7.sh errors

# Restart manually
./scripts/paper_trading_24_7.sh restart
```

### If No Trades:
- Check if strategies are too conservative
- Verify config settings
- Look at decision logs for "Hold" signals

### If High Restart Count:
- Check error logs for recurring issues
- Verify system resources (memory, CPU)
- Consider increasing check interval

## 📈 Success Criteria for 2-Week Test

### ✅ System Stability:
- Runs continuously for 14+ days
- Minimal restarts (< 5 total)
- No memory leaks or crashes

### ✅ Trading Activity:
- Executes trades when conditions are met
- Proper position sizing and risk management
- Realistic P&L tracking

### ✅ Performance Metrics:
- Reasonable win rate (40-70%)
- Manageable drawdowns (< 10%)
- Consistent strategy execution

## 🎯 Next Steps After 2-Week Test

1. **Analyze Results**: Review logs and performance metrics
2. **Optimize Config**: Adjust strategies based on results
3. **Go Live**: Switch to real trading with confidence
4. **Monitor**: Continue monitoring in production

## 📞 Support

If you encounter issues during your 2-week test:
1. Check logs first: `./scripts/paper_trading_24_7.sh logs`
2. Check errors: `./scripts/paper_trading_24_7.sh errors`
3. Restart if needed: `./scripts/paper_trading_24_7.sh restart`
4. Review this guide for troubleshooting steps
