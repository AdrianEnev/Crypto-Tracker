"""
Data fetching for backtest optimization.
"""

import os
from typing import Dict, Any, Optional, Tuple, List
from .config_loader import ConfigLoader
from src.data.ohlcv import get_candles
from src.data.ccxt_ohlcv import get_candles_ccxt


class DataFetcher:
    """Fetches market data for optimization."""

    def __init__(self, config_loader: ConfigLoader):
        self.config_loader = config_loader

    def fetch_series(
        self, coin_id: str, timeframe: str, days: int
    ) -> Optional[Tuple[List[float], List[float], List[float], List[int]]]:
        """Fetch OHLCV data series for a coin."""
        try:
            cfg_all = self.config_loader.load_config()
            data_cfg = cfg_all.get("data", {})
            provider = str(data_cfg.get("provider", "coingecko")).lower()
            api_key = os.environ.get("COINGECKO_API_KEY")
            tracked = cfg_all.get("tracked_coins", {})
            per = tracked.get(coin_id, {})
            cg_id = per.get("coingecko_id", coin_id)

            if provider == "ccxt":
                providers_cfg = cfg_all.get("providers", {})
                exchange_name = str(providers_cfg.get("exchange", "binance")).lower()
                market = per.get("market") or f"{per.get('symbol', coin_id).upper()}/USDT"

                # Avoid invalid self-quoted markets (e.g., USDT/USDT) by falling back to CoinGecko
                try:
                    base, quote = market.split("/")
                except ValueError:
                    base, quote = market, "USDT"
                if base.upper() == quote.upper():
                    provider = "coingecko"

            # Calculate limit based on timeframe
            if timeframe == "1d":
                limit = min(int(days), 2000)
            elif timeframe == "4h":
                limit = min(int(days) * 6, 2000)
            elif timeframe == "1h":
                limit = min(int(days) * 24, 2000)
            else:
                limit = 1000

            # Fetch candles
            if provider == "ccxt":
                candles = get_candles_ccxt(
                    exchange_name,
                    market,
                    timeframe=timeframe,
                    cache_dir="./data_cache",
                    limit=limit,
                    use_cache=True,
                )
            else:
                candles = get_candles(
                    cg_id,
                    timeframe=timeframe,
                    days=days,
                    cache_dir="./data_cache",
                    use_cache=True,
                    api_key=api_key,
                )

            if not candles:
                return None

            # Extract OHLCV data
            closes = [c.c for c in candles]
            highs = [c.h for c in candles]
            lows = [c.l for c in candles]
            times = [getattr(c, "ts", i) for i, c in enumerate(candles)]

            return closes, highs, lows, times

        except Exception as ex:
            print(f"  Data fetch failed for {coin_id}: {ex} (skipping).")
            return None

    def fetch_multiple_series(
        self, coin_ids: List[str], timeframe: str, days: int
    ) -> Dict[str, Tuple[List[float], List[float], List[float], List[int]]]:
        """Fetch series for multiple coins."""
        results = {}
        for coin_id in coin_ids:
            series = self.fetch_series(coin_id, timeframe, days)
            if series is not None:
                results[coin_id] = series
        return results
