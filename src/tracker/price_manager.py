"""
Price management for the crypto tracker.
Handles price fetching, aggregation, and historical data management.
"""

import yaml
from typing import Dict, Any, Optional
from collections import deque
from pathlib import Path

from src.fetcher import PriceFetcher
from src.fetcher_coingecko import CoingeckoFetcher
from src.fetcher_ccxt import CCXTPriceFetcher
from src.fetcher_websocket import WebSocketPriceFetcher
from src.aggregator import PriceAggregator
from src.data.ohlcv import get_candles
from src.data.ccxt_ohlcv import get_candles_ccxt
from src.indicators.core import rsi as rsi_series, ema as ema_series, atr as atr_series
from src.logger import log_event


class PriceManager:
    """Manages price fetching, aggregation, and historical data."""
    
    def __init__(self, config_manager, app_config: Any):
        self.config_manager = config_manager
        self.app_config = app_config
        self.config_path = config_manager.config_path
        
        # Initialize price fetchers
        self.fetcher = PriceFetcher(
            base_url=app_config.api_base_url,
            timeout=app_config.api_timeout
        )
        self.cg_fetcher = CoingeckoFetcher()
        
        # Setup aggregator with multiple sources
        self.aggregator = self._setup_aggregator()
        
        # Price history storage
        self.price_history: Dict[str, deque] = {}
        self.history: Dict[str, Dict[str, Any]] = {}
        self.history_provider = "coingecko"
        self.history_timeframe = "1d"
        
        # Preload historical data
        self._preload_history()
    
    def _setup_aggregator(self) -> PriceAggregator:
        """Setup price aggregator with configured sources."""
        try:
            providers_config = self.config_manager.get_providers_config()
            enabled_sources = providers_config.get('sources', ["cmc", "coingecko"])
            exchange_name = str(providers_config.get('exchange', 'binance')).lower()
            
            # Setup CCXT fetcher if enabled
            ccxt_fetcher = None
            sym_to_mkt = {}
            if any(src.lower() == 'ccxt' for src in enabled_sources):
                try:
                    for cid, coin in self.app_config.tracked_coins.items():
                        sym = coin.symbol.upper()
                        config_data = self.config_manager.load_full_config()
                        cdata = (config_data.get('tracked_coins') or {}).get(cid) or {}
                        market = cdata.get('market') or f"{sym}/USDT"
                        sym_to_mkt[sym] = market
                    
                    ccxt_fetcher = CCXTPriceFetcher(exchange_name, sym_to_mkt)
                except Exception:
                    ccxt_fetcher = None
            
            # Setup WebSocket fetcher if enabled
            ws_fetcher = None
            if 'websocket' in enabled_sources:
                ws_symbols = [mkt for sym, mkt in sym_to_mkt.items()]
                ws_fetcher = WebSocketPriceFetcher(ws_symbols)
                ws_fetcher.start()
            
            return PriceAggregator(
                self.fetcher, 
                self.cg_fetcher,
                agreement_max_diff_pct=0.5,
                enabled_sources=[s.lower() for s in enabled_sources],
                ccxt=ccxt_fetcher,
                websocket=ws_fetcher
            )
        except Exception as e:
            # Fallback to basic aggregator
            return PriceAggregator(
                self.fetcher, 
                self.cg_fetcher,
                agreement_max_diff_pct=0.5,
                enabled_sources=["cmc", "coingecko"]
            )
    
    def _preload_history(self):
        """Preload historical data for indicators."""
        try:
            config_data = self.config_manager.load_full_config()
            data_config = config_data.get('data', {})
            tf = str(data_config.get('timeframe', '1d'))
            days = int(data_config.get('days', 365))
            cache_dir = str(data_config.get('cache_dir', './data_cache'))
            provider = str(data_config.get('provider', 'coingecko')).lower()
            
            self.history_provider = provider
            indicators_config = config_data.get('indicators', {})
            rsi_period = int(indicators_config.get('rsi_period', 14))
            ema_fast = int(indicators_config.get('ema_fast', 20))
            ema_slow = int(indicators_config.get('ema_slow', 50))
            atr_period = int(indicators_config.get('atr_period', 14))
            
            # Optional CoinGecko id mapping
            cg_ids: Dict[str, str] = {}
            for cid, data in config_data.get('tracked_coins', {}).items():
                cgid = (data or {}).get('coingecko_id')
                if cgid:
                    cg_ids[cid] = str(cgid)
            
            loaded = 0
            self.history_timeframe = tf
            
            for coin_id, coin_cfg in self.app_config.tracked_coins.items():
                if coin_cfg.disabled:
                    continue
                    
                cg_key = cg_ids.get(coin_id, coin_id)
                try:
                    # Per-coin indicator overrides
                    cdata = config_data.get('tracked_coins', {}).get(coin_id) or {}
                    ind_over = cdata.get('indicators', {})
                    rsi_p_coin = int(ind_over.get('rsi_period', rsi_period))
                    ema_fast_coin = int(ind_over.get('ema_fast', ema_fast))
                    ema_slow_coin = int(ind_over.get('ema_slow', ema_slow))
                    atr_p_coin = int(ind_over.get('atr_period', atr_period))
                    
                    # Fetch candles per provider
                    if provider == 'ccxt':
                        providers_config = config_data.get('providers', {})
                        exchange_name = str(providers_config.get('exchange', 'binance')).lower()
                        market = cdata.get('market') or f"{coin_cfg.symbol.upper()}/USDT"
                        
                        if tf == '1d':
                            limit = min(int(days), 2000)
                        elif tf == '4h':
                            limit = min(int(days) * 6, 2000)
                        elif tf == '1h':
                            limit = min(int(days) * 24, 2000)
                        else:
                            limit = 1000
                            
                        candles = get_candles_ccxt(
                            exchange_name, market, timeframe=tf, 
                            cache_dir=cache_dir, limit=limit, use_cache=True
                        )
                    else:
                        candles = get_candles(
                            cg_key, timeframe=tf, days=days, 
                            cache_dir=cache_dir, use_cache=True
                        )
                    
                    if not candles:
                        continue
                    
                    # Extract OHLCV data
                    closes = [c.c for c in candles]
                    highs = [c.h for c in candles]
                    lows = [c.l for c in candles]
                    
                    # Compute indicators
                    rsi_vals = rsi_series(closes, rsi_p_coin)
                    ema_fast_vals = ema_series(closes, ema_fast_coin)
                    ema_slow_vals = ema_series(closes, ema_slow_coin)
                    atr_vals = atr_series(highs, lows, closes, atr_p_coin)
                    
                    self.history[coin_id] = {
                        'timeframe': tf,
                        'days': days,
                        'candles': candles,
                        'rsi': rsi_vals,
                        'ema_fast': ema_fast_vals,
                        'ema_slow': ema_slow_vals,
                        'atr': atr_vals,
                        'last': {
                            'rsi': rsi_vals[-1] if rsi_vals else None,
                            'ema_fast': ema_fast_vals[-1] if ema_fast_vals else None,
                            'ema_slow': ema_slow_vals[-1] if ema_slow_vals else None,
                            'atr': atr_vals[-1] if atr_vals else None,
                            'close': closes[-1] if closes else None,
                        }
                    }
                    loaded += 1
                    
                except Exception as ex:
                    log_event('history_load_error', {'coin': coin_id, 'error': str(ex)})
            
            if loaded > 0:
                from rich.console import Console
                console = Console()
                console.print(f"[blue]Preloaded history for {loaded} assets (tf={tf}, days={days}).[/]")
                
        except Exception as ex:
            log_event('history_init_error', {'error': str(ex)})
    
    def get_aggregated_prices(self, enabled_coins: Dict[str, str], cg_ids: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        """Get aggregated prices for enabled coins."""
        return self.aggregator.aggregate_prices(enabled_coins, cg_ids=cg_ids)
    
    def refresh_history_tail(self, coin_id: str) -> bool:
        """Refresh the tail of historical data for a specific coin."""
        try:
            if coin_id not in self.history:
                return False
            
            hist_data = self.history[coin_id]
            tf = hist_data.get('timeframe', '1d')
            days = hist_data.get('days', 365)
            
            config_data = self.config_manager.load_full_config()
            data_config = config_data.get('data', {})
            cache_dir = str(data_config.get('cache_dir', './data_cache'))
            provider = self.history_provider
            
            # Get CoinGecko ID if available
            cdata = config_data.get('tracked_coins', {}).get(coin_id) or {}
            cg_key = cdata.get('coingecko_id', coin_id)
            
            # Fetch latest candles
            if provider == 'ccxt':
                providers_config = config_data.get('providers', {})
                exchange_name = str(providers_config.get('exchange', 'binance')).lower()
                market = cdata.get('market') or f"{self.app_config.tracked_coins[coin_id].symbol.upper()}/USDT"
                
                if tf == '1d':
                    limit = min(int(days), 2000)
                elif tf == '4h':
                    limit = min(int(days) * 6, 2000)
                elif tf == '1h':
                    limit = min(int(days) * 24, 2000)
                else:
                    limit = 1000
                    
                new_candles = get_candles_ccxt(
                    exchange_name, market, timeframe=tf, 
                    cache_dir=cache_dir, limit=limit, use_cache=False
                )
            else:
                new_candles = get_candles(
                    cg_key, timeframe=tf, days=days, 
                    cache_dir=cache_dir, use_cache=False
                )
            
            if not new_candles:
                return False
            
            # Update history with new data
            hist_data['candles'] = new_candles
            
            # Recompute indicators
            closes = [c.c for c in new_candles]
            highs = [c.h for c in new_candles]
            lows = [c.l for c in new_candles]
            
            indicators_config = config_data.get('indicators', {})
            rsi_period = int(indicators_config.get('rsi_period', 14))
            ema_fast = int(indicators_config.get('ema_fast', 20))
            ema_slow = int(indicators_config.get('ema_slow', 50))
            atr_period = int(indicators_config.get('atr_period', 14))
            
            # Per-coin overrides
            ind_over = cdata.get('indicators', {})
            rsi_p_coin = int(ind_over.get('rsi_period', rsi_period))
            ema_fast_coin = int(ind_over.get('ema_fast', ema_fast))
            ema_slow_coin = int(ind_over.get('ema_slow', ema_slow))
            atr_p_coin = int(ind_over.get('atr_period', atr_period))
            
            rsi_vals = rsi_series(closes, rsi_p_coin)
            ema_fast_vals = ema_series(closes, ema_fast_coin)
            ema_slow_vals = ema_series(closes, ema_slow_coin)
            atr_vals = atr_series(highs, lows, closes, atr_p_coin)
            
            hist_data.update({
                'rsi': rsi_vals,
                'ema_fast': ema_fast_vals,
                'ema_slow': ema_slow_vals,
                'atr': atr_vals,
                'last': {
                    'rsi': rsi_vals[-1] if rsi_vals else None,
                    'ema_fast': ema_fast_vals[-1] if ema_fast_vals else None,
                    'ema_slow': ema_slow_vals[-1] if ema_slow_vals else None,
                    'atr': atr_vals[-1] if atr_vals else None,
                    'close': closes[-1] if closes else None,
                }
            })
            
            return True
            
        except Exception as ex:
            log_event('history_refresh_error', {'coin': coin_id, 'error': str(ex)})
            return False
