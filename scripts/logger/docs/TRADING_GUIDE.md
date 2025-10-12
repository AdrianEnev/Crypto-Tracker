# Trading Automation Guide

Complete guide to automated trading features integrated with the price logger.

## 🎯 Overview

The trading automation system extends the price logger with **real trading execution** capabilities. It's designed as a **strategy automation tool**, not an AI trading bot - you define the rules, and it executes them consistently.

### Key Features

✅ **Multiple Order Types**
- Limit orders (recommended for better fills)
- Market orders (instant execution)
- Stop-loss orders
- Take-profit orders
- OCO (One-Cancels-Other) orders

✅ **Risk Management**
- Position sizing based on risk
- Maximum loss per trade
- Maximum open positions
- Daily/weekly loss limits
- Circuit breaker protection

✅ **Advanced Exit Strategies**
- Fixed stop-loss and take-profit
- Trailing stop-loss
- Partial position exits
- Time-based exits

✅ **Trading Strategies**
- Alert-triggered entries
- Breakout trading
- DCA (Dollar Cost Averaging)
- Grid trading
- Manual entry + auto exit

✅ **Safety Features**
- Paper trading mode (test strategies without risk)
- Confirmation required option
- Maximum slippage protection
- Liquidity checks
- Trading hour blacklists

---

## 🚀 Quick Start

### 1. Enable Trading in Config

Edit `config/alert_config.yaml`:
```yaml
trading:
  enabled: false        # Change to true when ready
  paper_trading: true   # Start with paper trading!
```

### 2. Define Your First Strategy

Edit `config/trading_config.yaml`:
```yaml
strategies:
  - id: aster_manual
    name: "ASTER Manual Entry + Auto Exit"
    enabled: true
    
    trigger:
      type: alert
      symbol: ASTERUSDT           # Note: USDT not USDC (more liquid)
      alert_id: alert_001         # Links to your price alert
    
    entry:
      side: BUY
      order_type: limit
      position_size_usd: 50.0     # Risk $50 per trade
    
    exit:
      stop_loss_pct: 3.0          # Auto stop-loss at -3%
      take_profit_pct: 7.0        # Auto take-profit at +7%
      trailing_stop: true
      trailing_stop_pct: 2.0      # Trail 2% below peak
```

### 3. Link Alert to Strategy

In `config/trading_config.yaml`, add alert trading rule:
```yaml
alert_trading:
  rules:
    - alert_id: alert_001      # Your ASTER alert
      action: BUY
      strategy_id: aster_manual
```

### 4. Test in Paper Trading

```bash
# Run with paper trading enabled
python crypto_price_logger.py

# Watch for:
# - [PAPER TRADE] messages
# - Trades logged to markdown_logs/trades.md
```

### 5. Go Live (When Ready)

```yaml
trading:
  enabled: true
  paper_trading: false    # ⚠️  REAL MONEY!
```

---

## 📊 Trading Strategies Explained

### Strategy 1: Alert-Triggered Trading

**Use Case**: Automate entries when price alerts trigger

```yaml
strategies:
  - id: aster_breakout
    name: "ASTER Breakout"
    enabled: true
    
    trigger:
      type: alert
      symbol: ASTERUSDT
      alert_id: alert_001
    
    entry:
      side: BUY
      order_type: limit
      limit_offset_pct: 0.1       # Buy 0.1% below current price
      position_size_usd: 100.0
    
    exit:
      stop_loss_pct: 2.0          # -2% stop loss
      take_profit_pct: 5.0        # +5% take profit
      trailing_stop: true
      trailing_stop_pct: 1.5
```

**How it works:**
1. Price alert triggers (e.g., ASTER >= $1.50)
2. System places limit BUY order at $1.499 (0.1% below)
3. When filled, automatically places stop-loss at -2% and take-profit at +5%
4. Trailing stop activates, protecting profits

### Strategy 2: DCA (Dollar Cost Averaging)

**Use Case**: Accumulate position over time, regardless of price

```yaml
strategies:
  - id: btc_dca
    name: "Bitcoin DCA"
    enabled: true
    
    trigger:
      type: time_based
      interval_hours: 24          # Buy every 24 hours
    
    entry:
      side: BUY
      symbol: BTCUSDT
      fixed_usd_amount: 50.0      # Buy $50 worth each time
    
    exit:
      take_profit_pct: 20.0       # Long-term hold
      stop_loss_pct: 10.0
```

**How it works:**
1. Every 24 hours, buys $50 worth of BTC
2. Averages entry price over time
3. Exits only at significant gains/losses

### Strategy 3: Grid Trading

**Use Case**: Profit from price oscillation in a range

```yaml
strategies:
  - id: aster_grid
    name: "ASTER Grid"
    enabled: true
    
    trigger:
      type: grid
      symbol: ASTERUSDT
      grid_levels: 10
      price_range_low: 1.30
      price_range_high: 1.70
      grid_spacing_pct: 2.0       # 2% between levels
    
    entry:
      order_type: limit
      position_size_per_grid: 20.0
    
    exit:
      take_profit_per_grid_pct: 2.0
      no_stop_loss: true          # Grid doesn't use stop-loss
```

**How it works:**
1. Places 10 buy orders from $1.30 to $1.70 (2% apart)
2. When price drops and hits a buy level, executes trade
3. Immediately places sell order 2% above
4. Profits from price bouncing within range

### Strategy 4: Breakout Trading

**Use Case**: Enter when price breaks key levels with momentum

```yaml
strategies:
  - id: eth_breakout
    name: "ETH Breakout"
    enabled: true
    
    trigger:
      type: price_breakout
      symbol: ETHUSDT
      breakout_price: 3500.0
      confirmation_candles: 2     # Wait for 2 candles above
    
    entry:
      side: BUY
      position_size_method: risk_based
    
    exit:
      stop_loss_pct: 3.0
      take_profit_pct: 10.0
      max_hold_time_hours: 48     # Exit after 48h regardless
```

---

## 🛡️ Risk Management

### Position Sizing

**Risk-Based Sizing** (Recommended):
```yaml
risk:
  position_sizing:
    method: risk_based
    risk_per_trade_usd: 20.0      # Risk $20 per trade
```

If you set stop-loss at 2%, position size will be calculated so that if SL hits, you lose exactly $20.

**Fixed USD Sizing**:
```yaml
risk:
  position_sizing:
    method: fixed_usd
    fixed_position_size_usd: 100.0  # Always trade $100
```

**Percentage of Account**:
```yaml
risk:
  position_sizing:
    method: fixed_percent
    account_percent: 10.0           # Use 10% of account balance
```

### Loss Limits

```yaml
risk:
  max_loss_per_trade_pct: 2.0      # Never risk more than 2% per trade
  max_daily_loss_usd: 50.0         # Stop trading if daily loss >$50
  max_weekly_loss_usd: 150.0       # Stop trading if weekly loss >$150
  max_open_positions: 5            # Max 5 concurrent positions
```

### Circuit Breaker

Automatically stops ALL trading if portfolio drops too much:

```yaml
safety:
  circuit_breaker:
    enabled: true
    trigger_loss_pct: 5.0          # Stop if portfolio drops 5%
    cooldown_minutes: 60           # Wait 1 hour before resuming
```

---

## 📈 Exit Strategies

### 1. Fixed Stop-Loss and Take-Profit

Simple and effective:
```yaml
exit:
  stop_loss_pct: 2.0              # Exit at -2%
  take_profit_pct: 5.0            # Exit at +5%
```

### 2. Trailing Stop-Loss

Lock in profits as price moves in your favor:
```yaml
exit:
  trailing_stop: true
  trailing_stop_pct: 2.0          # Trail 2% below peak
  activate_after_profit_pct: 1.0  # Start trailing after +1% profit
```

**Example:**
- Entry: $1.50
- Price rises to $1.60 (+6.7%)
- Trailing stop activates at $1.568 (2% below $1.60)
- Price continues to $1.65
- Trailing stop moves to $1.617
- Price drops and hits trailing stop
- **Profit locked in!**

### 3. Partial Exits

Take profits incrementally:
```yaml
exit:
  partial_exits:
    - profit_pct: 3.0             # At +3%, sell 40% of position
      position_pct: 40.0
    - profit_pct: 5.0             # At +5%, sell another 30%
      position_pct: 30.0
  # Remaining 30% rides with trailing stop
  trailing_stop: true
  trailing_stop_pct: 2.0
```

### 4. Time-Based Exits

Exit after a certain time regardless of P&L:
```yaml
exit:
  max_hold_time_hours: 72         # Exit after 72 hours
  stop_loss_pct: 3.0              # Or if SL hits first
  take_profit_pct: 10.0           # Or if TP hits first
```

---

## ⚙️ Order Execution

### Limit Orders (Recommended)

Better prices, but not guaranteed to fill:
```yaml
execution:
  default_order_type: limit
  limit_offset_pct: 0.1           # Place 0.1% from current price
  timeout_seconds: 300            # Cancel after 5 minutes if not filled
```

**Example:**
- Current price: $1.50
- Limit BUY order: $1.4985 (0.1% below)
- Saves on slippage!

### Market Orders

Instant execution, but worse price:
```yaml
execution:
  default_order_type: market
```

Use market orders when:
- High volatility
- Need immediate entry
- Very liquid markets

---

## 🧪 Paper Trading

Test strategies without risking real money:

```yaml
paper_trading:
  balances:
    USDT: 1000.0                  # Start with $1000
    ASTER: 0.0
    BTC: 0.0
  
  fees:
    maker_fee_pct: 0.1            # Simulates 0.1% fees
    taker_fee_pct: 0.1
  
  slippage:
    enabled: true
    market_order_slippage_pct: 0.2
    limit_order_fill_rate: 0.8    # 80% of limit orders fill
```

**Paper trading includes:**
- Realistic fee simulation
- Slippage modeling
- Order fill rates
- Balance tracking
- Full logging

**Monitor paper trading:**
```bash
# Watch trades log
tail -f markdown_logs/trades.md

# Check positions
cat trading_positions.json
```

---

## 🔗 Integration with Price Alerts

The trading system works seamlessly with the price logger:

**1. Define alert** (`config/alert_config.yaml`):
```yaml
alerts:
  - id: alert_001
    name: "ASTER Breakout"
    symbol: ASTERUSDT
    condition: ">="
    target_price: 1.50
    enabled: true
```

**2. Define trading strategy** (`config/trading_config.yaml`):
```yaml
strategies:
  - id: aster_strategy
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

**3. Link them** (`config/trading_config.yaml`):
```yaml
alert_trading:
  rules:
    - alert_id: alert_001
      action: BUY
      strategy_id: aster_strategy
```

**Result:**
- Price alert triggers
- Email sent (as usual)
- Trade automatically executed
- Stop-loss and take-profit placed
- Position tracked
- Exits automated

---

## 📊 Monitoring & Logs

### Real-Time Terminal Output

```
[15:23:45] ASTER      $1.50123456 (target: >=1.50) ✓
[ALERT] 🚨 ASTER Breakout triggered at $1.50123456 - Email sent!
[PAPER TRADE] BUY 66.6 ASTERUSDT @ 1.499
[PAPER TRADE] Stop-loss: SELL 66.6 ASTERUSDT @ stop=1.469
[POSITION OPENED] ASTERUSDT - Entry: $1.499, SL: $1.469, TP: $1.574
```

### Markdown Logs

**`markdown_logs/trades.md`**:
```markdown
### 2025-10-12 15:23:45 - ENTRY
- **Symbol**: ASTERUSDT
- **Side**: BUY
- **Price**: $1.49900000
- **Quantity**: 66.6
- **Stop Loss**: $1.46902000
- **Take Profit**: $1.57395000

### 2025-10-12 16:45:30 - EXIT
- **Symbol**: ASTERUSDT
- **Side**: BUY
- **Price**: $1.57500000
- **Quantity**: 66.6
- **PnL**: 📈 $5.06
- **Reason**: TAKE_PROFIT
```

**`trading_positions.json`**:
```json
{
  "ASTERUSDT_1728745425": {
    "symbol": "ASTERUSDT",
    "side": "BUY",
    "entry_price": 1.499,
    "quantity": 66.6,
    "stop_loss": 1.469,
    "take_profit": 1.574,
    "status": "OPEN",
    "entry_time": "2025-10-12T15:23:45",
    "pnl": 0.0
  }
}
```

---

## ⚠️ Safety Checklist

Before enabling live trading:

- [ ] Test strategies in paper trading mode for at least 1 week
- [ ] Verify API keys have correct permissions (trade, not withdraw)
- [ ] Set appropriate risk limits (max loss per trade, daily loss, etc.)
- [ ] Enable IP whitelist on Binance
- [ ] Start with small position sizes
- [ ] Monitor first few trades closely
- [ ] Have stop-loss on EVERY position
- [ ] Keep emergency contact info ready
- [ ] Document your strategies
- [ ] Set up notifications

---

## 🐛 Troubleshooting

### "Symbol not found" Error

**Problem**: ASTER/USDC doesn't exist on Binance

**Solution**: Use ASTER/USDT instead:
```yaml
symbol: ASTERUSDT    # Not ASTERUSDC
```

Check available symbols:
```python
from binance.client import Client
client = Client()
symbols = [s['symbol'] for s in client.get_all_tickers() if 'ASTER' in s['symbol']]
print(symbols)  # ['ASTERUSDT', 'ASTERBUSD', etc.]
```

### Orders Not Filling

**Problem**: Limit orders sitting unfilled

**Solutions**:
1. Reduce `limit_offset_pct` (get closer to market price)
2. Use market orders for immediate execution
3. Increase `timeout_seconds` and let order wait longer

### Position Sizing Too Large/Small

**Problem**: Trades too big or too small

**Solution**: Adjust risk settings:
```yaml
risk:
  position_sizing:
    method: fixed_usd
    fixed_position_size_usd: 50.0  # Adjust this
```

### Stop-Loss Hit Immediately

**Problem**: Stop-loss too tight

**Solution**: Increase stop-loss percentage:
```yaml
exit:
  stop_loss_pct: 5.0    # Wider stop-loss
```

Consider market volatility when setting stops.

---

## 📚 Example Configurations

### Conservative (Low Risk)
```yaml
risk:
  max_position_size_usd: 50.0
  max_loss_per_trade_pct: 1.0
  max_open_positions: 3

strategies:
  - id: conservative
    exit:
      stop_loss_pct: 2.0
      take_profit_pct: 4.0          # 2:1 reward:risk
      trailing_stop: true
```

### Aggressive (Higher Risk)
```yaml
risk:
  max_position_size_usd: 200.0
  max_loss_per_trade_pct: 3.0
  max_open_positions: 8

strategies:
  - id: aggressive
    exit:
      stop_loss_pct: 5.0
      take_profit_pct: 15.0         # 3:1 reward:risk
      partial_exits: true
```

### Day Trading
```yaml
strategies:
  - id: day_trade
    exit:
      stop_loss_pct: 1.0
      take_profit_pct: 2.0
      max_hold_time_hours: 8        # Close by end of day
      trailing_stop: true
```

---

## 🎓 Best Practices

1. **Start Small**: Begin with minimum position sizes
2. **Paper Trade First**: Test for at least a week
3. **One Strategy at a Time**: Don't enable all strategies immediately
4. **Review Daily**: Check trades.md and positions daily
5. **Keep Stop-Losses**: NEVER trade without a stop-loss
6. **Document Changes**: Note why you adjusted parameters
7. **Monitor Performance**: Track win rate, avg profit/loss
8. **Adjust Gradually**: Make small parameter changes
9. **Have an Edge**: Only trade strategies you understand
10. **Risk Management First**: Protect capital above all

---

**Remember**: This is a strategy automation tool. Success depends on YOUR strategies and risk management, not the automation itself.

**Happy Trading! 📈**
