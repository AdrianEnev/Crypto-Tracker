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
