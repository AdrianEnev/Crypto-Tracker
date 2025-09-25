# Crypto Price Tracker

A simple terminal application to track cryptocurrency prices and get alerts when they drop below specified thresholds.

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and configure if needed
4. Update `config/config.yaml` with your preferred cryptocurrencies and thresholds

## Usage

Run the tracker:
```bash
python -m src.tracker
```

The application will check prices at the specified intervals and show alerts in the console.

## Configuration

Edit `config/config.yaml` to:
- Add/remove cryptocurrencies
- Set price thresholds
- Adjust check intervals

auto_trade
    enable: false
    mode: paper | live

decision
    confidence_thresholds.suggestion: 0.5
    confidence_thresholds.auto: 0.8

price
    ttl_seconds: 15

paper
    place_orders: false
    exits_enable: false

trade
    default_size_usd: 50.0

liquidity
    spread_bps_default: 10

risk
    stop_loss_pct: 0.03
    take_profit_pct: 0.06
    trailing_stop_pct: 0.04

providers
    sources: ["cmc","coingecko"]
    agreement_max_diff_pct: 0.5

tracked_coins
    coingecko_id: optional per coin (e.g., xrp: ripple, binance-coin: binancecoin, avalanche: avalanche-2, near-protocol: near)

Examples
Only CMC:
```yaml
providers:
  sources: ["cmc"]
  agreement_max_diff_pct: 0.5
```
Enable safe paper mode with exits:
```yaml
auto_trade:
  enable: true
  mode: paper
paper:
  place_orders: true
  exits_enable: true
trade:
  default_size_usd: 25.0
```
Add CoinGecko ID override (XRP):
```yaml
tracked_coins:
  xrp:
    symbol: xrp
    name: XRP
    threshold: 1.0
    check_interval: 300
    coingecko_id: ripple
```