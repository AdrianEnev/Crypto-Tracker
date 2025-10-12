# Auto-Increment Feature Guide

## Overview

The auto-increment feature automatically updates your target price after an alert is triggered. This is perfect for tracking trends without manually updating your configuration.

## How It Works

### Upward Trend (>= condition)
```yaml
- id: alert_001
  name: "ASTER Price Target"
  cryptocurrency: ASTER
  symbol: ASTER/USDC
  condition: ">="
  target_price: 1.4
  enabled: true
  auto_increment: true      # Enable auto-increment
  increment_amount: 0.05    # Add $0.05 each time
```

**Sequence:**
1. ASTER reaches $1.40 → Email sent, target becomes $1.45
2. ASTER reaches $1.45 → Email sent, target becomes $1.50
3. ASTER reaches $1.50 → Email sent, target becomes $1.55
4. And so on...

### Downward Trend (<= condition)
```yaml
- id: btc_dip
  name: "Bitcoin Dip Alerts"
  cryptocurrency: Bitcoin
  symbol: BTC/USDC
  condition: "<="
  target_price: 90000
  enabled: true
  auto_increment: true
  increment_amount: 1000    # Subtract $1000 each time
```

**Sequence:**
1. BTC drops to $90,000 → Email sent, target becomes $89,000
2. BTC drops to $89,000 → Email sent, target becomes $88,000
3. BTC drops to $88,000 → Email sent, target becomes $87,000
4. And so on...

## Configuration Options

### Required Fields
- `auto_increment: true` - Enables the feature
- `increment_amount: X` - Amount to add/subtract

### Behavior by Condition

| Condition | Auto-Increment Behavior |
|-----------|------------------------|
| `>=` | **Adds** increment_amount to target |
| `<=` | **Subtracts** increment_amount from target |
| `==` | **Not supported** (doesn't make sense) |

## Example Use Cases

### 1. Profit Taking Ladder
Track your gains as price rises:
```yaml
- id: profit_ladder
  name: "ETH Profit Ladder"
  cryptocurrency: Ethereum
  symbol: ETH/USDC
  condition: ">="
  target_price: 3500
  auto_increment: true
  increment_amount: 100
```
Alerts at: $3,500 → $3,600 → $3,700 → $3,800...

### 2. Buy the Dip Ladder
Get notified as price drops:
```yaml
- id: dip_ladder
  name: "SOL Dip Ladder"
  cryptocurrency: Solana
  symbol: SOL/USDC
  condition: "<="
  target_price: 150
  auto_increment: true
  increment_amount: 10
```
Alerts at: $150 → $140 → $130 → $120...

### 3. Small Increments for Volatile Coins
```yaml
- id: meme_tracker
  name: "DOGE Micro Tracker"
  cryptocurrency: Dogecoin
  symbol: DOGE/USDC
  condition: ">="
  target_price: 0.10
  auto_increment: true
  increment_amount: 0.01  # 1 cent increments
```
Alerts at: $0.10 → $0.11 → $0.12 → $0.13...

## What Happens When Alert Triggers

1. **Email Sent** - You receive the alert email
2. **Target Updated** - New target calculated and saved
3. **Config File Updated** - `alert_config.yaml` is automatically modified
4. **Cooldown Applied** - Alert cooldown period starts (default 3 minutes)
5. **Console Message** - Shows old and new target:
   ```
   [AUTO-INCREMENT] Target price updated: $1.40 → $1.45
   ```
6. **Markdown Log** - Records the change in `progress.md`:
   ```markdown
   ### 2025-10-12 15:10:23 - Auto-Increment
   - **Alert**: ASTER Price Target
   - **Old Target**: $1.40
   - **New Target**: $1.45
   - **Increment**: $0.05
   ```

## Important Notes

### ✅ Advantages
- **Hands-free tracking** - No manual config updates needed
- **Trend following** - Automatically adjusts to market movement
- **Persistent** - Changes saved to config file
- **Logged** - All changes tracked in markdown logs

### ⚠️ Considerations
- **One direction only** - Only tracks in the direction of the condition
- **No reversal** - Won't automatically reverse if price goes back down
- **Cooldown applies** - Each alert has a cooldown period (default 3 min)
- **Config file changes** - Your YAML file will be modified automatically

### 🛑 Limitations
- Not supported for `==` condition (equality alerts)
- Requires both `auto_increment: true` and `increment_amount: X`
- If `increment_amount` is missing, defaults to 0.05

## Disabling Auto-Increment

To disable for a specific alert:
```yaml
auto_increment: false  # or just remove the line
```

To stop and reset manually:
1. Stop the logger (Ctrl+C)
2. Edit `alert_config.yaml`
3. Set `auto_increment: false`
4. Manually set `target_price` to desired value
5. Restart the logger

## Monitoring Auto-Increments

### Check Current Target
View your config file:
```bash
cat config/alert_config.yaml
```

### View Auto-Increment History
Check the progress log:
```bash
grep -A 5 "Auto-Increment" markdown_logs/progress.md
```

### Real-Time Monitoring
Watch the terminal output - you'll see:
```
[15:10:23] ASTER      $1.40000000 (target: >=1.40) ✓
[ALERT] 🚨 ASTER Price Target triggered at $1.40000000 - Email sent!
[AUTO-INCREMENT] Target price updated: $1.40 → $1.45
[15:10:53] ASTER      $1.41000000 (target: >=1.45) ○
```

## Combining with Multiple Alerts

You can have multiple alerts with different behaviors:

```yaml
alerts:
  # Auto-incrementing upward alert
  - id: aster_up
    name: "ASTER Upward Ladder"
    cryptocurrency: ASTER
    symbol: ASTER/USDC
    condition: ">="
    target_price: 1.40
    auto_increment: true
    increment_amount: 0.05
    enabled: true
  
  # Static downward alert (no auto-increment)
  - id: aster_down
    name: "ASTER Support Level"
    cryptocurrency: ASTER
    symbol: ASTER/USDC
    condition: "<="
    target_price: 1.20
    enabled: true
  
  # Different crypto with auto-increment
  - id: btc_ladder
    name: "BTC Profit Ladder"
    cryptocurrency: Bitcoin
    symbol: BTC/USDC
    condition: ">="
    target_price: 92000
    auto_increment: true
    increment_amount: 1000
    enabled: true
```

## Troubleshooting

**Q: Auto-increment not working?**
- Check `auto_increment: true` is set
- Verify `increment_amount` is specified
- Ensure alert actually triggered (check email)
- Look for errors in `markdown_logs/errors.md`

**Q: Want to reset the target?**
- Stop the logger
- Edit `config/alert_config.yaml`
- Change `target_price` to desired value
- Restart logger

**Q: Can I change increment_amount while running?**
- Yes! Edit the config file
- Changes take effect on next alert trigger
- No restart needed

---

**Happy trend tracking! 📈**
