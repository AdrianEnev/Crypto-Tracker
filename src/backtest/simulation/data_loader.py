"""
Data loading for backtest simulation.
"""

import os
from typing import Dict, List, Optional, Tuple
import yaml
from pathlib import Path

from ...data.ohlcv import get_candles
from ...data.ccxt_ohlcv import get_candles_ccxt


class BacktestDataLoader:
    """Loads market data for backtesting."""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            project_root = Path(__file__).resolve().parents[5]
            config_path = project_root / "config" / "config.yaml"
        
        self.config_path = config_path
        self._config = None
    
    def load_config(self) -> Dict:
        """Load configuration from YAML file."""
        if self._config is None:
            with open(self.config_path, "r") as f:
                self._config = yaml.safe_load(f) or {}
        return self._config
    
    def load_coin_data(self, coin_id: str, timeframe: str = None, days: int = None) -> Optional[Tuple[List[float], List[float], List[float], List[int]]]:
        """Load OHLCV data for a specific coin."""
        try:
            cfg_all = self.load_config()
            data_cfg = cfg_all.get("data", {})
            
            # Use provided parameters or defaults from config
            if timeframe is None:
                timeframe = str(data_cfg.get("timeframe", "1d"))
            if days is None:
                days = int(data_cfg.get("days", 365))
            
            provider = str(data_cfg.get("provider", "coingecko")).lower()
            api_key = os.environ.get("COINGECKO_API_KEY")
            
            tracked = cfg_all.get("tracked_coins", {})
            per = tracked.get(coin_id, {})
            cg_id = per.get("coingecko_id", coin_id)
            
            # Handle CCXT provider
            if provider == "ccxt":
                providers_cfg = cfg_all.get("providers", {})
                exchange_name = str(providers_cfg.get("exchange", "binance")).lower()
                market = per.get("market") or f"{per.get('symbol', coin_id).upper()}/USDT"
                
                # Avoid invalid self-quoted markets
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
                    exchange_name, market,
                    timeframe=timeframe,
                    cache_dir="./data_cache",
                    limit=limit,
                    use_cache=True
                )
            else:
                candles = get_candles(
                    cg_id,
                    timeframe=timeframe,
                    days=days,
                    cache_dir="./data_cache",
                    use_cache=True,
                    api_key=api_key
                )
            
            if not candles:
                return None
            
            # Extract OHLCV data
            closes = [c.c for c in candles]
            highs = [c.h for c in candles]
            lows = [c.l for c in candles]
            times = [getattr(c, 'ts', i) for i, c in enumerate(candles)]
            
            return closes, highs, lows, times
            
        except Exception as ex:
            print(f"Failed to load data for {coin_id}: {ex}")
            return None
    
    def load_multiple_coins(self, coin_ids: List[str], timeframe: str = None, days: int = None) -> Dict[str, Tuple[List[float], List[float], List[float], List[int]]]:
        """Load data for multiple coins."""
        results = {}
        for coin_id in coin_ids:
            data = self.load_coin_data(coin_id, timeframe, days)
            if data is not None:
                results[coin_id] = data
        return results
