# Paper Trading Migration Guide

## Overview

This guide explains how to migrate from the existing simple paper trading system to the new comprehensive paper trading system while maintaining backward compatibility.

## Current State

### Old System (`src/executor.py`)
- **Simple PaperExecutor**: Basic order simulation
- **Limited Features**: No portfolio tracking, no realistic execution simulation
- **Simple Interface**: `place_order(symbol, side, size_usd, order_type)`
- **Basic Order Model**: Simple dataclass with minimal fields

### New System (`paper_trader/`)
- **Comprehensive PaperBroker**: Full portfolio management and execution simulation
- **Advanced Features**: Slippage models, fees, latency, performance analytics
- **Rich Interface**: `OrderRequest` objects with detailed configuration
- **Complete Order Model**: State tracking, metadata, and comprehensive fields

## Migration Options

### Option 1: Gradual Migration (Recommended)

Use the compatibility adapter to bridge both systems:

```python
# Old way (still works)
from src.executor import PaperExecutor
executor = PaperExecutor()

# New way with compatibility
from paper_trader.compatibility import PaperExecutorAdapter
executor = PaperExecutorAdapter()  # Uses new system under the hood

# Or with configuration
from paper_trader.compatibility import create_enhanced_paper_executor
executor = create_enhanced_paper_executor("config/paper.yaml")
```

### Option 2: Direct Migration

Replace the old system entirely:

```python
# Replace in ExecutionManager
from paper_trader import PaperBroker

# Old
self.paper = PaperExecutor()

# New
self.paper = PaperBroker(
    initial_cash=100000.0,
    base_currency="USDT"
)
```

### Option 3: Hybrid Approach

Use both systems for different purposes:

```python
# Simple testing
simple_executor = PaperExecutor()

# Advanced simulation
advanced_broker = PaperBroker(config)
```

## Step-by-Step Migration

### Step 1: Install New System

The new paper trading system is already included. No additional installation needed.

### Step 2: Test Compatibility

```python
# Test that existing code still works
from paper_trader.compatibility import PaperExecutorAdapter

executor = PaperExecutorAdapter()
order = executor.place_order("BTC/USDT", "buy", 1000.0, "market")
print(f"Order placed: {order.id}, Status: {order.status}")
```

### Step 3: Enable Enhanced Features

```python
# Use enhanced features
executor = PaperExecutorAdapter()

# Get portfolio summary
portfolio = executor.get_portfolio_summary()
print(f"Total P&L: {portfolio['net_pnl']}")

# Update market data for realistic simulation
executor.update_market_data("BTC/USDT", 50000.0, volume=1000)
```

### Step 4: Migrate to Full New System

```python
# Full migration to new system
from paper_trader import PaperBroker, PaperTradingConfig

config = PaperTradingConfig.from_file("config/paper.yaml")
broker = PaperBroker(
    initial_cash=config.initial_cash,
    base_currency=config.base_currency,
    slippage_config=config.slippage_config,
    fee_config=config.fee_config,
    latency_config=config.latency_config
)

# Use new order interface
from src.order_manager.models import OrderRequest, OrderType

order_request = OrderRequest(
    symbol="BTC/USDT",
    side="buy",
    order_type=OrderType.MARKET,
    quantity=0.02
)

result = broker.place_order(order_request)
```

## Configuration Migration

### Old System
No configuration - just basic simulation.

### New System
Rich configuration in `config/paper.yaml`:

```yaml
# Basic settings
initial_cash: 100000.0
base_currency: "USDT"

# Execution simulation
execution:
  slippage:
    type: "square_root"
    base_slippage_bps: 5.0
  fees:
    taker_fee_bps: 10.0
  latency:
    mean_latency_ms: 200.0

# Market data
market_data:
  mode: "replay"
  symbols: ["BTC/USDT", "ETH/USDT"]
```

## Feature Comparison

| Feature | Old System | New System |
|---------|------------|------------|
| Order Simulation | ✅ Basic | ✅ Advanced |
| Portfolio Tracking | ❌ | ✅ Complete |
| P&L Calculation | ❌ | ✅ Real-time |
| Slippage Simulation | ❌ | ✅ Multiple models |
| Fee Simulation | ❌ | ✅ Configurable |
| Latency Simulation | ❌ | ✅ Realistic |
| Market Data Replay | ❌ | ✅ Historical |
| Live Data Streaming | ❌ | ✅ Real-time |
| Performance Analytics | ❌ | ✅ Comprehensive |
| Safety Checks | ❌ | ✅ Multiple layers |
| CLI Interface | ❌ | ✅ Full featured |
| Configuration | ❌ | ✅ YAML based |
| Reporting | ❌ | ✅ JSON/HTML/Jupyter |

## Backward Compatibility

### What Still Works
- All existing `PaperExecutor` calls
- Simple `place_order()` interface
- Basic order status checking

### What's Enhanced
- More realistic execution simulation
- Portfolio and P&L tracking
- Performance metrics
- Safety validation

### What's New
- Advanced configuration
- Market data replay
- Comprehensive reporting
- CLI interface

## Testing Migration

### Test Existing Functionality
```python
def test_backward_compatibility():
    from paper_trader.compatibility import PaperExecutorAdapter
    
    executor = PaperExecutorAdapter()
    
    # Test old interface
    order = executor.place_order("BTC/USDT", "buy", 1000.0, "market")
    assert order.status == "Filled"
    assert order.symbol == "BTC/USDT"
```

### Test New Features
```python
def test_enhanced_features():
    from paper_trader import PaperBroker
    
    broker = PaperBroker(initial_cash=10000.0)
    
    # Test portfolio tracking
    account_info = broker.get_account_info()
    assert account_info.total_equity == 10000.0
    
    # Test performance metrics
    metrics = broker.get_performance_metrics()
    assert "total_trades" in metrics
```

## Rollback Plan

If issues arise, you can easily rollback:

```python
# Rollback to old system
from src.executor import PaperExecutor
executor = PaperExecutor()  # Simple, reliable
```

## Recommendations

### For Development
- Use the compatibility adapter for existing code
- Gradually migrate to new features
- Test thoroughly before production

### For Production
- Use the new system for comprehensive testing
- Keep the old system as fallback
- Implement proper monitoring and logging

### For New Projects
- Use the new system directly
- Leverage all advanced features
- Follow the comprehensive documentation

## Support

If you encounter issues during migration:

1. Check the compatibility adapter
2. Review the configuration files
3. Test with simple examples first
4. Use the safety checks to validate setup
5. Check the logs for detailed error information

The new system is designed to be backward compatible while providing significant enhancements for paper trading simulation.
