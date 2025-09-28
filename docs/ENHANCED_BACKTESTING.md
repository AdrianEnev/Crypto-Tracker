# Enhanced Backtesting System

This document describes the advanced backtesting capabilities implemented in Phases 3 and 4, including realistic fee modeling, advanced slippage calculation, and order book simulation.

## Overview

The enhanced backtesting system provides:

- **Realistic Fee Models**: Exchange-specific fee structures with maker/taker differentiation and volume-based tiers
- **Advanced Slippage Models**: Multiple slippage calculation methods including depth-based, volume-based, and market impact models
- **Order Book Simulation**: Historical order book replay and realistic order execution simulation
- **Comprehensive Cost Analysis**: Detailed breakdown of all execution costs and performance metrics

## Architecture

### Phase 3: Advanced Fee & Slippage Modeling

#### Fee Models (`src/fees/`)

- **`models.py`**: Core fee data structures and enums
- **`exchange_fees.py`**: Exchange-specific fee configurations for major exchanges
- **`calculator.py`**: Main fee calculation engine
- **`backtest_fees.py`**: Backtest-specific fee calculator with statistics tracking

#### Slippage Models (`src/slippage/`)

- **`models.py`**: Slippage calculation data structures
- **`depth_based.py`**: Order book depth-based slippage calculation
- **`volume_based.py`**: Volume-based slippage modeling
- **`market_impact.py`**: Market impact calculation for large orders
- **`backtest_slippage.py`**: Backtest-specific slippage calculator

### Phase 4: Order Book Simulation

#### Order Book System (`src/orderbook/`)

- **`models.py`**: Order book data structures and models
- **`fetcher.py`**: Order book data fetching from exchanges
- **`storage.py`**: Data storage and retrieval (SQLite and JSONL)
- **`replay_engine.py`**: Historical order book replay
- **`simulator.py`**: Order execution simulation

## Key Features

### 1. Realistic Fee Modeling

#### Exchange-Specific Fee Structures

```python
from fees import FeeCalculator, FeeCalculationMode

# Initialize fee calculator
fee_calc = FeeCalculator(FeeCalculationMode.REALISTIC)

# Calculate fees for a trade
context = OrderFeeContext(
    order_value_usd=10000.0,
    side="buy",
    order_type="market",
    exchange="binance",
    monthly_volume_usd=50000.0
)

fees = fee_calc.calculate_fees(context)
print(f"Trading fee: ${fees.trading_fee_usd:.2f}")
print(f"Fee type: {fees.fee_type_used.value}")
print(f"Volume tier: {fees.volume_tier}")
```

#### Supported Exchanges

- **Binance**: 10 VIP tiers with volume-based fee reductions
- **Coinbase Pro**: 8 tiers with maker/taker fee differentiation
- **Bybit**: 8 VIP levels with aggressive maker rebates
- **Kraken**: 9 tiers with competitive fees
- **OKX**: 9 VIP levels with volume-based pricing

#### Fee Calculation Modes

- **`ZERO`**: No fees (for testing)
- **`SIMPLIFIED`**: Flat 5 bps fee for all trades
- **`REALISTIC`**: Exchange-specific fees with volume tiers

### 2. Advanced Slippage Models

#### Depth-Based Slippage

Simulates realistic order execution against order book depth:

```python
from slippage import DepthBasedSlippage
from orderbook import OrderBookSnapshot

# Create order book snapshot
snapshot = OrderBookSnapshot(
    symbol="BTC/USDT",
    timestamp=datetime.now(),
    bids=[(50000.0, 1.0), (49999.0, 2.0)],
    asks=[(50001.0, 1.0), (50002.0, 2.0)]
)

# Calculate slippage
slippage_calc = DepthBasedSlippage()
context = SlippageContext(
    symbol="BTC/USDT",
    side="buy",
    quantity=2.0,
    order_type="market",
    order_book=snapshot
)

result = slippage_calc.calculate_slippage(context)
print(f"Slippage: {result.slippage_bps:.2f} bps")
print(f"Effective price: ${result.effective_price:.2f}")
```

#### Volume-Based Slippage

Calculates slippage based on order size relative to daily volume:

```python
from slippage import VolumeBasedSlippage

slippage_calc = VolumeBasedSlippage()
context = SlippageContext(
    symbol="BTC/USDT",
    side="buy",
    quantity=1.0,
    current_price=50000.0,
    volume_24h=10000000.0,  # $10M daily volume
    volatility=0.02  # 2% volatility
)

result = slippage_calc.calculate_slippage(context)
```

#### Market Impact Calculation

For large orders that significantly impact market prices:

```python
from slippage import MarketImpactCalculator

impact_calc = MarketImpactCalculator()
context = SlippageContext(
    symbol="BTC/USDT",
    side="buy",
    quantity=100.0,  # Large order
    current_price=50000.0,
    volume_24h=10000000.0
)

result = impact_calc.calculate_market_impact(context)
print(f"Market impact: {result.slippage_bps:.2f} bps")
```

### 3. Order Book Simulation

#### Historical Replay

```python
from orderbook import SQLiteOrderBookStorage, OrderBookReplayEngine

# Create storage and replay engine
storage = SQLiteOrderBookStorage("./orderbook_data.db")
replay_engine = OrderBookReplayEngine(storage, replay_speed=2.0)

# Replay historical data
for snapshot in replay_engine.replay_snapshots(
    "BTC/USDT", 
    start_time, 
    end_time
):
    print(f"Replay: {snapshot.timestamp} - Bid: ${snapshot.best_bid}")
```

#### Order Execution Simulation

```python
from orderbook import OrderBookSimulator, SimulatedOrder

# Create simulator
simulator = OrderBookSimulator()
simulator.set_order_book(snapshot)

# Simulate order execution
order = SimulatedOrder(
    order_id="test_1",
    symbol="BTC/USDT",
    side="buy",
    order_type="market",
    quantity=1.0
)

fill = simulator.simulate_order(order)
print(f"Filled: {fill.filled_quantity} BTC at ${fill.average_price}")
print(f"Slippage: {fill.slippage_bps:.2f} bps")
```

### 4. Enhanced Backtesting

#### Using the Enhanced Simulator

```python
from backtest.simulation.enhanced_simulator import EnhancedTradingSimulator

# Create enhanced simulator
simulator = EnhancedTradingSimulator(
    exchange="binance",
    fee_mode=FeeCalculationMode.REALISTIC,
    slippage_model=SlippageType.DEPTH_BASED,
    monthly_volume_usd=100000.0
)

# Run backtest with enhanced cost modeling
result = simulator.simulate_on_series(
    closes=closes,
    highs=highs,
    lows=lows,
    times=times,
    symbol="BTC/USDT",
    use_enhanced_costs=True
)

# Access detailed cost analysis
print(f"Total fees: ${result.total_fees_usd:.2f}")
print(f"Total slippage: ${result.total_slippage_usd:.2f}")
print(f"Cost efficiency score: {result.cost_efficiency_score:.4f}")
```

## Configuration

### Advanced Configuration File

Use `config/backtest_advanced.yaml` for comprehensive configuration:

```yaml
# Fee configuration
fees:
  mode: "realistic"
  exchanges:
    binance:
      maker_bps: 2.0
      taker_bps: 4.0
      volume_tiers:
        - volume_usd: 0
          maker_bps: 2.0
          taker_bps: 4.0

# Slippage configuration
slippage:
  model: "depth_based"
  max_slippage_bps: 1000.0
  market_impact_factor: 0.1

# Order book simulation
orderbook:
  enabled: true
  data_source: "ccxt"
  storage:
    type: "sqlite"
    path: "./orderbook_data"
```

## Performance Considerations

### Optimization Features

- **Caching**: Fee and slippage calculations are cached for repeated scenarios
- **Parallel Processing**: Multiple orders can be simulated in parallel
- **Memory Management**: Efficient data structures for large order book datasets
- **Lazy Loading**: Order book data is loaded on-demand during replay

### Performance Benchmarks

- **Fee Calculation**: ~0.1ms per calculation
- **Slippage Calculation**: ~0.2ms per calculation  
- **Order Simulation**: ~1ms per order
- **Order Book Replay**: ~10x real-time speed (configurable)

## Usage Examples

### 1. Basic Enhanced Backtest

```python
# Run enhanced backtest with realistic costs
from demos.demo_enhanced_backtest import run_comparison_demo
run_comparison_demo()
```

### 2. Order Book Simulation

```python
# Run order book simulation demo
from demos.demo_orderbook_simulation import main
main()
```

### 3. Exchange Fee Comparison

```python
# Compare fees across exchanges
from fees import FeeCalculator

fee_calc = FeeCalculator()
comparison = fee_calc.compare_exchanges(
    order_value_usd=10000.0,
    symbol="BTC/USDT",
    side="buy",
    order_type="market"
)

for exchange, fees in comparison.items():
    print(f"{exchange}: ${fees.trading_fee_usd:.2f}")
```

## Testing

### Running Tests

```bash
# Run comprehensive tests
python -m pytest tests/test_enhanced_backtest.py -v

# Run performance benchmarks
python -m pytest tests/test_enhanced_backtest.py::test_performance_benchmarks -v
```

### Test Coverage

- Fee calculation accuracy
- Slippage model validation
- Order book simulation correctness
- Integration between components
- Performance benchmarks

## Migration Guide

### From Simple to Enhanced Backtesting

1. **Update imports**:
   ```python
   # Old
   from backtest.simulation.simulator import TradingSimulator
   
   # New
   from backtest.simulation.enhanced_simulator import EnhancedTradingSimulator
   ```

2. **Configure fee and slippage models**:
   ```python
   simulator = EnhancedTradingSimulator(
       exchange="binance",
       fee_mode=FeeCalculationMode.REALISTIC,
       slippage_model=SlippageType.DEPTH_BASED
   )
   ```

3. **Enable enhanced costs**:
   ```python
   result = simulator.simulate_on_series(
       # ... existing parameters ...
       use_enhanced_costs=True
   )
   ```

## Best Practices

### 1. Fee Optimization

- Use limit orders when possible to qualify for maker fees
- Consider volume tiers when planning trading strategies
- Compare fees across exchanges for large volume strategies

### 2. Slippage Management

- Use depth-based slippage for market orders
- Consider order size relative to available liquidity
- Implement order slicing for large orders

### 3. Order Book Simulation

- Use realistic order book data when available
- Consider market conditions during simulation
- Validate simulation results against historical performance

### 4. Performance Optimization

- Cache frequently used calculations
- Use appropriate replay speeds for testing
- Monitor memory usage with large datasets

## Troubleshooting

### Common Issues

1. **High slippage in simulations**: Check order size relative to available liquidity
2. **Unexpected fee calculations**: Verify exchange configuration and volume tiers
3. **Memory issues with large datasets**: Use chunked processing or reduce replay speed
4. **Slow performance**: Enable caching and parallel processing

### Debug Mode

Enable debug logging for detailed execution information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Run simulation with debug output
simulator = EnhancedTradingSimulator()
result = simulator.simulate_on_series(...)
```

## Future Enhancements

### Planned Features

- **Machine Learning Integration**: ML-based slippage and fee prediction
- **Alternative Data Sources**: Sentiment and on-chain data integration
- **Portfolio Optimization**: Multi-asset strategy optimization
- **Real-time Simulation**: Live order book streaming and simulation

### Contributing

See the main project README for contribution guidelines. Focus areas for enhancement:

- Additional exchange fee structures
- Advanced slippage models
- Performance optimizations
- Extended test coverage

## Conclusion

The enhanced backtesting system provides institutional-grade simulation capabilities with realistic cost modeling and order book simulation. This enables more accurate strategy testing and better understanding of execution costs and market impact.

For questions or support, please refer to the main project documentation or create an issue in the project repository.
