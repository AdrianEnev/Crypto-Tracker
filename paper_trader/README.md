# Paper Trading System Documentation

## Overview

The Paper Trading System is a comprehensive simulation platform that allows you to test trading strategies using simulated money and realistic market conditions. It provides the same interface as live trading but executes all orders in a simulated environment with configurable slippage, fees, and latency.

## Features

- **Realistic Execution Simulation**: Configurable slippage, fees, and latency models
- **Multiple Data Sources**: Support for historical replay and live market data
- **Comprehensive Portfolio Tracking**: Real-time P&L, position management, and risk metrics
- **Performance Analytics**: Detailed performance metrics and reporting
- **Safety First**: Multiple safety checks to prevent accidental real order execution
- **Flexible Configuration**: YAML-based configuration with environment variable overrides

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Market Data   │    │   Paper Broker  │    │   Portfolio     │
│    Adapter      │───▶│                 │───▶│   Manager       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Sources  │    │  Execution      │    │   Persistence   │
│                 │    │  Simulator      │    │   Layer         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Quick Start

### 1. Installation

The paper trading system is included with the main trading repository. No additional installation is required.

### 2. Create Configuration

```bash
python scripts/run_paper.py --create-config
```

This creates a default configuration file at `config/paper.yaml`.

### 3. Run Historical Replay

```bash
python scripts/run_paper.py --mode replay --data ./data_cache --symbols BTC/USDT ETH/USDT
```

### 4. Run Live Paper Trading

```bash
python scripts/run_paper.py --mode live --symbols BTC/USDT ETH/USDT
```

## Configuration

### Basic Settings

```yaml
# Basic settings
run_id: "my_strategy_test"
mode: "replay"  # replay, live, hybrid
initial_cash: 100000.0
base_currency: "USDT"

# Portfolio settings
max_positions: 10
position_size_limit_pct: 0.1  # 10% of portfolio per position
```

### Execution Simulation

```yaml
execution:
  slippage:
    type: "square_root"  # fixed, linear, square_root, orderbook_depth
    base_slippage_bps: 5.0  # Base slippage in basis points
    max_slippage_bps: 50.0  # Maximum slippage in basis points
  
  fees:
    type: "percentage"  # percentage, fixed, tiered
    maker_fee_bps: 5.0  # Maker fee in basis points
    taker_fee_bps: 10.0  # Taker fee in basis points
  
  latency:
    min_latency_ms: 50.0
    max_latency_ms: 500.0
    mean_latency_ms: 200.0
```

### Market Data

```yaml
market_data:
  mode: "replay"  # replay, live, hybrid
  source: "local_file"  # local_file, ccxt_rest, ccxt_ws
  
  # Replay settings
  replay_speed: 1.0  # Speed multiplier
  start_time: "2024-01-01"
  end_time: "2024-01-31"
  
  # Live settings
  exchange: "binance"
  symbols: ["BTC/USDT", "ETH/USDT"]
  update_interval: 1.0
```

## CLI Usage

### Basic Commands

```bash
# Run historical replay
python scripts/run_paper.py --mode replay --data ./data_cache

# Run live paper trading
python scripts/run_paper.py --mode live --symbols BTC/USDT ETH/USDT

# Use custom configuration
python scripts/run_paper.py --config config/my_strategy.yaml

# Override settings
python scripts/run_paper.py --initial-cash 50000 --slippage-bps 10 --fee-bps 15
```

### Advanced Options

```bash
# Fast replay (10x speed)
python scripts/run_paper.py --mode replay --replay-speed 10.0

# Specific time range
python scripts/run_paper.py --mode replay --start-time 2024-01-01 --end-time 2024-01-31

# Custom output directory
python scripts/run_paper.py --output-dir ./results/my_test

# Skip report generation
python scripts/run_paper.py --no-reports
```

### Utility Commands

```bash
# Create default configuration
python scripts/run_paper.py --create-config

# List previous runs
python scripts/run_paper.py --list-runs
```

## Data Sources

### Historical Data (Replay Mode)

The system supports multiple historical data formats:

- **JSONL**: Line-delimited JSON files
- **CSV**: Comma-separated value files
- **Parquet**: Columnar data format

Data files should be located in the `data_cache` directory and follow naming conventions:
- `binance_BTC-USDT_4h_n2000_4h.jsonl`
- `btc_usdt_1d.csv`
- `eth_usdt_1h.parquet`

### Live Data (Live Mode)

For live paper trading, the system can connect to:

- **CCXT REST API**: Periodic price updates
- **CCXT WebSocket**: Real-time streaming data
- **Custom Providers**: Implement your own data source

## Execution Simulation

### Slippage Models

1. **Fixed**: Constant slippage percentage
2. **Linear**: Slippage increases linearly with order size
3. **Square Root**: More realistic slippage for large orders
4. **Order Book Depth**: Slippage based on available liquidity

### Fee Models

1. **Percentage**: Fee as percentage of trade value
2. **Fixed**: Fixed fee per trade
3. **Tiered**: Fee based on trading volume

### Latency Simulation

The system simulates realistic execution latency including:
- Network latency
- Exchange processing time
- Random jitter

## Portfolio Management

### Position Tracking

- Real-time P&L calculation
- Position sizing limits
- Risk management rules
- Portfolio diversification

### Account State

- Cash balance tracking
- Position valuations
- Margin requirements (if applicable)
- Performance metrics

## Performance Metrics

### Basic Metrics

- **Total Return**: Overall portfolio return
- **Win Rate**: Percentage of profitable trades
- **Average Win/Loss**: Average profit/loss per trade
- **Total Trades**: Number of executed trades

### Risk Metrics

- **Maximum Drawdown**: Largest peak-to-trough decline
- **Sharpe Ratio**: Risk-adjusted return
- **Sortino Ratio**: Downside risk-adjusted return
- **Recovery Factor**: Net profit / Maximum drawdown

### Advanced Metrics

- **Expectancy**: Expected value per trade
- **Profit Factor**: Gross profit / Gross loss
- **Time in Market**: Percentage of time holding positions
- **Annualized Return**: Return adjusted for time period

## Reporting

### Report Formats

1. **JSON**: Machine-readable metrics
2. **HTML**: Human-readable report with charts
3. **Jupyter Notebook**: Interactive analysis

### Report Contents

- Performance summary
- Trade analysis
- Risk metrics
- Portfolio evolution charts
- Configuration details

## Safety Features

### Multiple Safety Checks

1. **Environment Variables**: Check for API keys
2. **Configuration Files**: Validate paper mode settings
3. **Module Imports**: Block real exchange modules
4. **Broker Validation**: Ensure paper broker is used

### Safety Enforcement

```python
from paper_trader.safety import enforce_paper_mode

# This will exit if unsafe conditions are detected
enforce_paper_mode()
```

## Integration with Existing System

### Using with CryptoTracker

The paper trading system integrates seamlessly with the existing `CryptoTracker`:

```python
from src.tracker.core import CryptoTracker
from paper_trader import PaperBroker

# Initialize tracker
tracker = CryptoTracker("config/config.yaml")

# Replace executor with paper broker
paper_broker = PaperBroker(initial_cash=100000.0)
tracker.execution_manager.paper = paper_broker

# Enable paper mode
tracker.execution_manager.auto_trade_mode = "paper"
tracker.execution_manager.auto_trade_enable = True
```

### Custom Strategy Integration

```python
from paper_trader import PaperBroker, MarketDataAdapter
from src.order_manager.models import OrderRequest, OrderType

# Initialize components
broker = PaperBroker(initial_cash=100000.0)
market_data = MarketDataAdapter(config)

# Your strategy logic
def my_strategy(symbol, price, indicators):
    # Analyze market conditions
    if should_buy(indicators):
        order = OrderRequest(
            symbol=symbol,
            side="buy",
            order_type=OrderType.MARKET,
            quantity=calculate_position_size(price)
        )
        broker.place_order(order)
```

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/test_paper_trading.py -v

# Run specific test class
pytest tests/test_paper_trading.py::TestPaperBroker -v

# Run with coverage
pytest tests/test_paper_trading.py --cov=paper_trader --cov-report=html
```

### Test Categories

1. **Unit Tests**: Individual component testing
2. **Integration Tests**: End-to-end workflow testing
3. **Safety Tests**: Security and safety validation
4. **Performance Tests**: Speed and memory usage

## Troubleshooting

### Common Issues

1. **No Market Data**: Check data file paths and formats
2. **Configuration Errors**: Validate YAML syntax and required fields
3. **Import Errors**: Ensure all dependencies are installed
4. **Safety Check Failures**: Remove API keys and real exchange configs

### Debug Mode

```bash
# Enable debug logging
export PAPER_DEBUG=1
python scripts/run_paper.py --mode replay
```

### Log Files

Check log files in the `logs/` directory for detailed error information.

## Best Practices

### Configuration Management

1. Use version control for configuration files
2. Test with small amounts initially
3. Document strategy parameters
4. Use descriptive run IDs

### Data Management

1. Keep historical data organized
2. Use appropriate timeframes for your strategy
3. Validate data quality before running
4. Backup important datasets

### Performance Optimization

1. Use appropriate replay speeds
2. Limit symbol count for live mode
3. Monitor memory usage for large datasets
4. Use efficient data formats (Parquet)

### Safety

1. Always run safety checks before live trading
2. Use separate configurations for paper and live
3. Keep API keys secure
4. Test thoroughly before production deployment

## API Reference

### PaperBroker

```python
class PaperBroker(AbstractBroker):
    def __init__(self, initial_cash: float, base_currency: str, ...)
    def place_order(self, order_request: OrderRequest) -> OrderResult
    def cancel_order(self, order_id: str, symbol: str) -> bool
    def get_account_info(self) -> AccountInfo
    def get_balance(self, currency: str) -> Optional[AccountBalance]
    def get_position(self, symbol: str) -> Optional[Position]
```

### MarketDataAdapter

```python
class MarketDataAdapter:
    def __init__(self, config: MarketDataConfig)
    async def get_historical_data(self, symbol: str, ...) -> List[MarketTick]
    async def start_streaming(self, symbols: List[str])
    async def stop_streaming(self)
    def add_data_callback(self, callback: Callable[[MarketTick], None])
```

### PerformanceMetrics

```python
class PerformanceMetrics:
    def __init__(self, trades: List[Trade], account_history: List[AccountSnapshot], initial_cash: float)
    def get_summary(self) -> Dict[str, Any]
```

## Contributing

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

### Code Style

- Follow PEP 8 guidelines
- Use type hints
- Write comprehensive docstrings
- Add unit tests for new features

## License

This paper trading system is part of the main trading repository and follows the same license terms.

## Support

For issues and questions:

1. Check the troubleshooting section
2. Review existing issues on GitHub
3. Create a new issue with detailed information
4. Include configuration files and error logs

---

*Last updated: 2024-01-01*
