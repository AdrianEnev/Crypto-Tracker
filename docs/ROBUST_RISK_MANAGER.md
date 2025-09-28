# Robust Risk Manager

A comprehensive, centralized risk management system designed to prevent catastrophic losses and enforce portfolio constraints in cryptocurrency trading.

## Overview

The Robust Risk Manager provides multi-layered protection through:

- **Portfolio-level exposure limits** (max exposure per coin, total exposure, correlation limits)
- **Per-trade risk controls** (max loss % of equity, position sizing limits)
- **Multi-timeframe drawdown monitoring** (daily, weekly, maximum drawdown limits)
- **Automated kill-switch system** with configurable triggers
- **Leverage and margin management** for perpetual futures
- **Funding rate exposure limits** for perpetual positions

## Architecture

### Core Components

```
src/risk/
├── __init__.py              # Module exports
├── models.py                # Data models and enums
├── robust_manager.py        # Main risk manager orchestrator
├── exposure_tracker.py      # Portfolio exposure tracking
├── drawdown_manager.py      # Drawdown monitoring
└── kill_switch.py           # Emergency kill switch system
```

### Integration Points

- **Order Manager**: Pre-trade risk validation
- **Portfolio Manager**: Enhanced exposure tracking
- **Execution Manager**: Risk-aware position sizing
- **Configuration System**: Centralized risk parameters

## Configuration

### Basic Configuration

Add to `config/config.yaml`:

```yaml
robust_risk:
  enabled: true
  strict_mode: false  # Blocks all trading on any violation
  
  # Portfolio-level risk limits
  portfolio_limits:
    max_exposure_per_coin_pct: 15.0      # Max 15% per coin
    max_total_exposure_pct: 80.0         # Max 80% total exposure
    max_open_positions: 8                # Max concurrent positions
    max_correlation_exposure_pct: 25.0   # Max exposure to correlated assets
  
  # Per-trade risk limits
  per_trade_limits:
    max_loss_pct_equity: 2.0             # Max 2% equity risk per trade
    max_position_size_pct: 10.0          # Max 10% of equity per position
    min_risk_reward_ratio: 1.5           # Minimum R:R ratio
  
  # Drawdown limits
  drawdown_limits:
    daily_max_drawdown_pct: 5.0          # 5% daily limit
    weekly_max_drawdown_pct: 12.0        # 12% weekly limit
    max_drawdown_pct: 20.0               # 20% absolute limit
    kill_switch_drawdown_pct: 15.0       # Kill switch at 15%
  
  # Leverage and margin limits
  leverage_limits:
    max_leverage: 3.0                    # Max 3x leverage
    margin_requirement_buffer: 1.2       # 20% buffer above margin req
    max_margin_utilization_pct: 75.0     # Max 75% margin used
  
  # Funding rate exposure limits
  funding_rate_limits:
    max_funding_rate_exposure: 0.01      # Max 1% funding rate cost
    funding_rate_cost_limit_daily: 0.005 # Max 0.5% daily funding cost
    perpetual_exposure_limit_pct: 50.0   # Max 50% in perpetuals
  
  # Risk monitoring configuration
  monitoring:
    risk_check_interval_seconds: 30      # Risk checks every 30s
    alert_thresholds:
      exposure_warning_pct: 70.0         # Warn at 70% exposure
      drawdown_warning_pct: 10.0         # Warn at 10% drawdown
      leverage_warning_pct: 80.0         # Warn at 80% leverage
  
  # Asset correlation matrix
  correlation_matrix:
    BTC: {ETH: 0.8, LTC: 0.7, BCH: 0.6}
    ETH: {BTC: 0.8, DOT: 0.5, LINK: 0.6}
    # ... more correlations
  
  # Asset categories for group risk management
  asset_categories:
    major_crypto: [BTC, ETH, LTC, BCH]
    altcoins: [DOT, LINK, UNI, AAVE]
    memecoins: [DOGE, SHIB]
    stablecoins: [USDT, USDC]
```

## Usage

### Basic Integration

```python
from src.risk import RobustRiskManager
from src.tracker.config_manager import ConfigManager
from src.tracker.portfolio_manager import PortfolioManager

# Initialize
config_manager = ConfigManager("config/config.yaml")
portfolio_manager = PortfolioManager(config_manager, config)
robust_risk_manager = RobustRiskManager(config_manager, portfolio_manager)

# Check if trading is allowed
if robust_risk_manager.is_trading_allowed():
    print("Trading is allowed")
else:
    print("Trading is blocked by risk management")

# Perform risk assessment
sym_to_price = {"BTC": 45000.0, "ETH": 3000.0}
risk_status = robust_risk_manager.perform_risk_assessment(sym_to_price)
print(f"Risk Level: {risk_status.overall_risk_level}")

# Pre-trade risk check
risk_check = robust_risk_manager.check_pre_trade_risk(
    symbol="BTC",
    side="buy", 
    quantity=0.1,
    price=45000.0,
    stop_loss=43000.0
)

if risk_check.is_valid:
    print("Trade passed risk checks")
else:
    print("Trade rejected:", [v.message for v in risk_check.violations])
```

### Order Manager Integration

The risk manager is automatically integrated with the order management system:

```python
# Orders are automatically validated through robust risk manager
order_request = OrderRequest(
    symbol="BTC",
    side="buy",
    quantity=0.1,
    price=45000.0
)

try:
    order = order_manager.place_order(order_request)
    print("Order placed successfully")
except OrderValidationError as e:
    print("Order rejected by risk management:", e.message)
```

## Risk Monitoring

### Real-time Risk Assessment

```python
# Get comprehensive risk summary
risk_summary = robust_risk_manager.get_risk_summary()

print(f"Overall Risk Level: {risk_summary['overall_risk_level']}")
print(f"Total Exposure: {risk_summary['exposure_metrics']['total_exposure_pct']:.2f}%")
print(f"Current Drawdown: {risk_summary['drawdown_metrics']['current_drawdown_pct']:.2f}%")
print(f"Kill Switch Active: {risk_summary['kill_switch_active']}")
```

### Risk Violations

The system tracks various types of risk violations:

- `PORTFOLIO_EXPOSURE_EXCEEDED`: Total portfolio exposure limit exceeded
- `PER_COIN_EXPOSURE_EXCEEDED`: Individual coin exposure limit exceeded  
- `MAX_POSITIONS_EXCEEDED`: Maximum number of open positions exceeded
- `DAILY_DRAWDOWN_EXCEEDED`: Daily drawdown limit exceeded
- `WEEKLY_DRAWDOWN_EXCEEDED`: Weekly drawdown limit exceeded
- `MAX_DRAWDOWN_EXCEEDED`: Maximum drawdown limit exceeded
- `LEVERAGE_EXCEEDED`: Leverage limit exceeded
- `MARGIN_UTILIZATION_EXCEEDED`: Margin utilization limit exceeded
- `FUNDING_RATE_EXPOSURE_EXCEEDED`: Funding rate cost limit exceeded
- `KILL_SWITCH_ACTIVATED`: Kill switch triggered

## Kill Switch System

### Automatic Triggers

The kill switch automatically activates when:

1. **Excessive Drawdown**: Current drawdown exceeds kill switch threshold
2. **Excessive Exposure**: Portfolio exposure exceeds limits with buffer
3. **Excessive Leverage**: Leverage utilization exceeds limits with buffer
4. **High Error Rate**: System error rate exceeds threshold (future feature)

### Manual Control

```python
# Activate kill switch manually
robust_risk_manager.force_kill_switch_activation("manual_emergency")

# Check status
status = robust_risk_manager.kill_switch.get_status()
print(f"Active: {status['is_active']}")
print(f"Reason: {status['activation_reason']}")
print(f"Auto-reset in: {status['time_until_reset_minutes']} minutes")

# Deactivate manually
robust_risk_manager.force_kill_switch_deactivation("manual_override")
```

### Emergency Actions

When kill switch activates:

1. **Immediate order cancellation**: All pending orders are cancelled
2. **Trading halt**: New orders are blocked
3. **Alert notifications**: Emergency alerts sent
4. **Position monitoring**: Existing positions monitored for further action

## Advanced Features

### Correlation Risk Management

```python
# Define asset correlations in config
correlation_matrix:
  BTC: {ETH: 0.8, LTC: 0.7, BCH: 0.6}
  ETH: {BTC: 0.8, DOT: 0.5, LINK: 0.6}

# System automatically tracks correlated exposure
# and enforces group exposure limits
```

### Dynamic Position Sizing

The system automatically adjusts position sizes based on:

- Current portfolio exposure
- Risk-reward ratios
- Drawdown levels
- Correlation exposure

### Multi-timeframe Drawdown Tracking

- **Intraday**: Real-time drawdown from daily start
- **Daily**: Rolling 24-hour drawdown
- **Weekly**: Rolling 7-day drawdown  
- **Maximum**: Peak-to-trough drawdown from equity high

## Testing and Validation

### Demo Script

Run the demo to see the risk manager in action:

```bash
python demo_robust_risk_manager.py
```

### Backtesting Integration

The risk manager integrates with the backtesting system to validate risk controls:

```python
# Risk limits are automatically applied during backtesting
# to ensure realistic performance expectations
```

## Performance Considerations

- **Efficient Monitoring**: Risk checks run every 30 seconds by default
- **Minimal Overhead**: Risk calculations are optimized for speed
- **Persistent State**: Risk state is saved to disk for recovery
- **Graceful Degradation**: System continues operating if risk manager fails

## Security Features

- **Fail-Safe Design**: Defaults to blocking trades if risk manager fails
- **State Persistence**: Risk state survives system restarts
- **Audit Trail**: All risk violations and actions are logged
- **Manual Override**: Emergency controls available for manual intervention

## Future Enhancements

Planned features for future releases:

1. **Machine Learning Integration**: Adaptive risk limits based on market conditions
2. **Cross-Exchange Risk**: Unified risk management across multiple exchanges
3. **Advanced Correlation**: Dynamic correlation tracking and adjustment
4. **Risk Attribution**: Detailed breakdown of risk sources
5. **Performance Analytics**: Risk-adjusted performance metrics
6. **Stress Testing**: Automated stress testing of risk scenarios

## Troubleshooting

### Common Issues

1. **Risk Manager Not Loading**: Check configuration file syntax
2. **False Positives**: Adjust risk limits in configuration
3. **Performance Issues**: Increase risk check interval
4. **State Corruption**: Delete state files to reset

### Debug Mode

Enable detailed logging:

```python
import logging
logging.getLogger('src.risk').setLevel(logging.DEBUG)
```

### Configuration Validation

The system validates configuration on startup and logs any issues.

## Support

For issues or questions:

1. Check the configuration file syntax
2. Review the logs for error messages
3. Run the demo script to verify functionality
4. Check the risk summary for current status

The robust risk manager is designed to be your trading system's safety net, providing comprehensive protection while maintaining trading efficiency.
