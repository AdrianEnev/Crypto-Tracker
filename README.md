# Crypto Tracker

A cryptocurrency trading bot that tracks selected coins, analyzes market data, and automates trading actions based on configurable technical strategies and risk controls.

## Trading Strategies

### Mean Reversion Strategy
RSI-based strategy that buys when oversold (<30) and sells when overbought (>70). Optional Bollinger Bands confluence for enhanced signals.

### Momentum Strategy  
EMA crossover strategy that follows trend direction. Fast EMA crossing above slow EMA triggers buy signals, with optional RSI and MACD filters.

### Breakout Strategy
Bollinger Squeeze breakout strategy that identifies low volatility periods and trades breakouts above/below bands with volume confirmation.

### Cross-Exchange Arbitrage
Detects price discrepancies between exchanges and calculates arbitrage opportunities after accounting for fees and buffers.

## Risk Management

- **Stop Loss**: Fixed percentage (3%) or ATR-based (1.5x ATR)
- **Take Profit**: Fixed percentage (6%) or ATR-based (3x ATR)  
- **Trailing Stop**: Fixed percentage (4%) or ATR-based (2x ATR)
- **Position Sizing**: Risk-based sizing (0.5% risk budget per trade)
- **Regime Filter**: EMA-based market regime detection
- **Volatility Gate**: Blocks trades in low/high volatility conditions

## Quick Start

1. **Configure**: Edit `config/config.yaml` to set up tracked coins and strategy parameters
2. **Start**: Run the application using the entry point:
   ```bash
   python src/entry.py
   ```
3. **Monitor**: The bot will track prices, generate signals, and execute trades based on your configuration

The application supports both paper trading and live trading modes with comprehensive backtesting capabilities.