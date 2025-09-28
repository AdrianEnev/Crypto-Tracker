# Order Management System

A comprehensive, professional-grade order management system for cryptocurrency trading that supports advanced order types, smart routing, retry logic, and reconciliation.

## 🚀 Features

### Core Order Management
- **Order State Machine**: Complete order lifecycle tracking (NEW → PENDING → PARTIALLY_FILLED → FILLED → CANCELED)
- **Multiple Order Types**: Market, Limit, Stop-Limit, TWAP, VWAP, Iceberg
- **Order Validation**: Comprehensive validation with detailed error reporting
- **Order Tracking**: Real-time order status and fill tracking

### Advanced Order Types
- **TWAP (Time-Weighted Average Price)**: Execute large orders over time to minimize market impact
- **VWAP (Volume-Weighted Average Price)**: Execute orders based on market volume patterns
- **Smart Order Routing**: Intelligent exchange selection based on liquidity, fees, and reliability
- **Order Slicing**: Automatic order splitting for optimal execution

### Robust Error Handling
- **Retry Logic**: Exponential backoff with jitter for API failures
- **Circuit Breaker**: Automatic failure detection and recovery
- **Error Classification**: Distinguish between retryable and non-retryable errors
- **Graceful Degradation**: Fallback mechanisms for exchange failures

### Order Reconciliation
- **State Reconciliation**: Automatic reconciliation between local and exchange states
- **Discrepancy Detection**: Identify and handle order state mismatches
- **Orphaned Order Handling**: Detect and manage orphaned orders
- **Audit Trail**: Complete order lifecycle tracking

### Risk Management
- **Position Limits**: Configurable position size limits
- **Order Limits**: Maximum daily order limits
- **Slippage Control**: Maximum slippage protection
- **Circuit Breakers**: Automatic trading halt on excessive failures

## 📁 Architecture

```
src/order_manager/
├── __init__.py              # Main exports
├── models.py                # Order models and data structures
├── state_machine.py         # Order state machine
├── manager.py               # Main order manager orchestrator
├── executors.py             # Exchange executors (paper, CCXT)
├── routing.py               # Smart order routing
├── retry.py                 # Retry logic and circuit breaker
├── cancellation.py          # Order cancellation management
├── reconciliation.py        # Order reconciliation
├── twap.py                  # TWAP implementation
├── vwap.py                  # VWAP implementation
└── integration.py           # Integration with existing system
```

## 🛠️ Installation

The order management system is integrated into the existing trading bot. No additional installation is required.

## 📖 Usage

### Basic Order Placement

```python
from src.order_manager import OrderManager, OrderRequest, OrderType, OrderState

# Create order manager
config = OrderManagerConfig()
order_manager = OrderManager(config_manager, portfolio_manager, risk_manager, config)

# Register executors
paper_executor = EnhancedPaperExecutor()
order_manager.register_executor("paper", paper_executor)

# Place a market order
order_request = OrderRequest(
    symbol="BTC/USDT",
    side="buy",
    order_type=OrderType.MARKET,
    quantity=0.1,
    strategy_id="my_strategy"
)

order = order_manager.place_order(order_request)
print(f"Order placed: {order.id}, State: {order.state.value}")
```

### TWAP Orders

```python
# Place a TWAP order
twap_request = OrderRequest(
    symbol="ETH/USDT",
    side="buy",
    order_type=OrderType.TWAP,
    quantity=10.0,
    price=3000.0,
    twap_duration_seconds=1800,  # 30 minutes
    strategy_id="twap_strategy"
)

twap_order = order_manager.place_order(twap_request)

# Monitor TWAP execution
twap_status = order_manager.get_twap_status(twap_order.id)
print(f"TWAP Progress: {twap_status['completed_slices']}/{twap_status['total_slices']}")
```

### VWAP Orders

```python
# Place a VWAP order
vwap_request = OrderRequest(
    symbol="SOL/USDT",
    side="buy",
    order_type=OrderType.VWAP,
    quantity=100.0,
    price=100.0,
    vwap_participation_rate=0.1,  # 10% participation
    strategy_id="vwap_strategy"
)

vwap_order = order_manager.place_order(vwap_request)

# Monitor VWAP execution
vwap_status = order_manager.get_vwap_status(vwap_order.id)
print(f"VWAP Progress: {vwap_status['total_filled']}/{vwap_status['remaining_quantity']}")
```

### Order Cancellation

```python
# Cancel a single order
success = order_manager.cancel_order(order_id, "manual_cancellation")

# Cancel all orders for a symbol
cancelled_count = order_manager.cancel_all_orders("BTC/USDT", "bulk_cancel")

# Cancel orders by strategy
strategy_orders = order_manager.get_orders_by_strategy("my_strategy")
for order in strategy_orders:
    order_manager.cancel_order(order.id, "strategy_cancel")
```

### Order Reconciliation

```python
# Manual reconciliation
reconciliation_result = order_manager.reconcile_orders(force=True)

print(f"Orders checked: {reconciliation_result.total_orders_checked}")
print(f"Discrepancies found: {len(reconciliation_result.discrepancies)}")

for discrepancy in reconciliation_result.discrepancies:
    print(f"Order {discrepancy.order_id}: {discrepancy.discrepancy_type}")
```

### Integration with Existing System

```python
from src.order_manager.integration import integrate_order_manager

# Integrate with existing tracker
success = integrate_order_manager(tracker, config={
    'order_manager': {
        'enabled': True,
        'max_active_orders': 1000,
        'reconciliation': {'enabled': True, 'interval_minutes': 5}
    }
})

if success:
    print("Order manager integrated successfully")
    # Existing execution_manager is now replaced with order manager
```

## ⚙️ Configuration

### Order Manager Configuration

```yaml
order_manager:
  enabled: true
  
  # Order limits and timeouts
  max_active_orders: 1000
  order_timeout_minutes: 60
  
  # Reconciliation settings
  reconciliation:
    enabled: true
    interval_minutes: 5
    auto_cancel_missing: false
  
  # Smart order routing
  routing:
    enabled: true
    preferred_exchanges: ["binance", "bybit", "coinbase"]
    liquidity_threshold: 10000  # USD
    max_slippage_bps: 50
    
  # TWAP settings
  twap:
    min_slice_size_usd: 100
    max_slices: 20
    min_slice_interval_seconds: 30
    max_slice_interval_seconds: 300
    randomization_factor: 0.1
    
  # VWAP settings
  vwap:
    participation_rate: 0.1  # 10% of market volume
    max_participation_rate: 0.2  # Maximum 20% participation
    min_slice_size_usd: 100
    max_slice_size_usd: 10000
    volume_lookback_hours: 24
    slice_duration_minutes: 5
    randomization_factor: 0.05
    
  # Retry and error handling
  retry:
    max_attempts: 3
    base_delay_seconds: 1.0
    max_delay_seconds: 30.0
    backoff_multiplier: 2.0
    jitter_range: 0.1
    
  # Circuit breaker settings
  circuit_breaker:
    enabled: true
    failure_threshold: 5
    timeout_seconds: 60
    
  # Risk controls
  risk:
    max_order_size_usd: 10000
    max_daily_orders: 100
    position_size_limit_pct: 0.1  # 10% of portfolio
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all order manager tests
python -m pytest tests/test_order_manager.py -v

# Run specific test categories
python -m pytest tests/test_order_manager.py::TestOrderModels -v
python -m pytest tests/test_order_manager.py::TestTWAPExecution -v
python -m pytest tests/test_order_manager.py::TestVWAPExecution -v
```

### Demo Script

Run the demo script to see the order management system in action:

```bash
python demo_order_manager.py
```

## 📊 Monitoring and Statistics

### Order Statistics

```python
# Get comprehensive order statistics
stats = order_manager.get_order_statistics()

print(f"Total orders: {stats['total_orders']}")
print(f"Active orders: {stats['active_orders']}")
print(f"Orders by state: {stats['orders_by_state']}")
print(f"Orders by exchange: {stats['orders_by_exchange']}")
print(f"Retry statistics: {stats['retry_statistics']}")
```

### Order Lifecycle Tracking

```python
# Get detailed lifecycle information for an order
lifecycle = order_manager.get_order_lifecycle_summary(order_id)

print(f"Order transitions: {lifecycle['transitions']}")
print(f"Duration: {lifecycle['duration_seconds']} seconds")
print(f"Final state: {lifecycle['final_state']}")
```

### Smart Routing Statistics

```python
# Get routing statistics
routing_stats = order_manager.smart_router.get_exchange_statistics()

for exchange, metrics in routing_stats.items():
    print(f"{exchange}: Score {metrics['metrics']['total_score']:.3f}")
    print(f"  Latency: {metrics['metrics']['latency_score']:.3f}")
    print(f"  Reliability: {metrics['metrics']['reliability_score']:.3f}")
```

## 🔧 Advanced Features

### Custom Event Handlers

```python
def on_order_filled(order):
    print(f"Order {order.id} filled at {order.average_fill_price}")

def on_order_canceled(order):
    print(f"Order {order.id} canceled: {order.cancellation_reason}")

# Register event handlers
order_manager.add_event_handler('order_filled', on_order_filled)
order_manager.add_event_handler('order_canceled', on_order_canceled)
```

### Circuit Breaker Management

```python
# Check circuit breaker status
retry_stats = order_manager.retry_manager.get_retry_statistics()
print(f"Circuit breakers: {retry_stats['circuit_breakers']}")

# Manually reset circuit breaker
order_manager.retry_manager.reset_circuit_breaker("binance")
```

### Custom Executors

```python
class CustomExecutor(BaseExecutor):
    def __init__(self):
        super().__init__("custom_exchange")
    
    def connect(self) -> bool:
        # Implement connection logic
        return True
    
    def place_order(self, order_request: OrderRequest) -> OrderResult:
        # Implement order placement
        return OrderResult(order_id="custom-1", success=True)
    
    # Implement other required methods...

# Register custom executor
custom_executor = CustomExecutor()
order_manager.register_executor("custom", custom_executor)
```

## 🚨 Error Handling

The order management system provides comprehensive error handling:

### Common Exceptions

- `OrderValidationError`: Invalid order parameters
- `OrderNotFoundError`: Order not found
- `OrderAlreadyExistsError`: Duplicate order ID
- `MaxRetriesExceededError`: Maximum retry attempts exceeded
- `ExchangeError`: Exchange-specific errors

### Error Recovery

```python
try:
    order = order_manager.place_order(order_request)
except OrderValidationError as e:
    print(f"Order validation failed: {e}")
    # Handle validation errors
except MaxRetriesExceededError as e:
    print(f"Order failed after retries: {e}")
    # Handle retry exhaustion
except Exception as e:
    print(f"Unexpected error: {e}")
    # Handle unexpected errors
```

## 🔄 Migration from Existing System

The order management system is designed to be backward compatible. To migrate:

1. **Enable Order Manager**: Set `order_manager.enabled: true` in config
2. **Configure Settings**: Adjust order manager settings as needed
3. **Test Integration**: Run in paper mode first
4. **Monitor Performance**: Watch order execution and reconciliation
5. **Gradual Rollout**: Enable for specific strategies first

## 📈 Performance Considerations

- **Memory Usage**: Order manager maintains order state in memory
- **CPU Usage**: TWAP/VWAP algorithms require periodic execution
- **Network Usage**: Reconciliation requires exchange API calls
- **Storage**: Order history is maintained for audit purposes

## 🤝 Contributing

When contributing to the order management system:

1. **Follow Architecture**: Maintain separation of concerns
2. **Add Tests**: Include comprehensive tests for new features
3. **Update Documentation**: Keep this README current
4. **Consider Performance**: Optimize for high-frequency trading
5. **Handle Errors**: Implement proper error handling

## 📝 License

This order management system is part of the crypto trading bot project and follows the same license terms.

## 🆘 Support

For issues and questions:

1. Check the test suite for usage examples
2. Review the demo script for implementation patterns
3. Examine the integration module for system integration
4. Consult the configuration documentation for settings

---

**Note**: This order management system is designed for professional trading environments. Always test thoroughly in paper mode before using with real funds.
