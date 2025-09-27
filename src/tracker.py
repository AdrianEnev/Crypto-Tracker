import os
import sys
import time
import yaml
import schedule
from pathlib import Path
from typing import Dict, Any
from collections import deque
from rich.console import Console
from rich.table import Table
from rich.progress import track
from dotenv import load_dotenv
# Import local modules
from datetime import datetime, timezone
from .models import CoinConfig, AppConfig, MarketSnapshot, Decision
from .fetcher import PriceFetcher
from .notifier import Notifier
from .decision import compute_rsi, compute_ma, compute_confidence, recommend_action
from .liquidity import estimate_slippage
from .executor import PaperExecutor
from .risk import (
    RiskParams,
    compute_stop_levels,
    compute_trailing_stop,
    ATRRiskParams,
    compute_stop_levels_atr,
    compute_trailing_stop_atr,
)
from .fetcher_coingecko import CoingeckoFetcher
from .aggregator import PriceAggregator
from .fetcher_ccxt import CCXTPriceFetcher
from .logger import log_event, configure_file_logging, log_order_csv, log_decision_csv
from .executor_ccxt import CCXTLiveExecutor
from .portfolio import Portfolio
from .persistence.sqlite_store import SQLiteStore
from .data.ohlcv import get_candles
from .data.ccxt_ohlcv import get_candles_ccxt
from .indicators.core import rsi as rsi_series, ema as ema_series, atr as atr_series

# Set up console
console = Console()

class CryptoTracker:
    def __init__(self, config_path: str = "../config/config.yaml"):
        """Initialize the crypto tracker with configuration."""
        # Load env vars first so overrides are available while loading config
        load_dotenv(dotenv_path=Path(__file__).parent.parent / 'config' / '.env')
        self.config_path = config_path
        self.config = self._load_config(config_path)
        self.fetcher = PriceFetcher(
            base_url=self.config.api_base_url,
            timeout=self.config.api_timeout
        )
        # Additional provider (Coingecko) and aggregator (Phase 5)
        self.cg_fetcher = CoingeckoFetcher()
        self.agreement_max_diff_pct: float = 0.5
        # Providers config: sources and optional ccxt exchange & markets
        try:
            with open(self.config_path, 'r') as f:
                _cfg_all = yaml.safe_load(f) or {}
            providers_cfg = (_cfg_all.get('providers') or {})
            enabled_sources = providers_cfg.get('sources') or ["cmc", "coingecko"]
            exchange_name = str(providers_cfg.get('exchange', 'binance')).lower()
        except Exception:
            enabled_sources = ["cmc", "coingecko"]
            exchange_name = 'binance'
        # Optional CCXT fetcher if requested
        ccxt_fetcher = None
        if any(src.lower() == 'ccxt' for src in enabled_sources):
            sym_to_mkt = {}
            try:
                for cid, coin in self.config.tracked_coins.items():
                    sym = coin.symbol.upper()
                    # read per-coin market if provided
                    with open(self.config_path, 'r') as f:
                        _cfg_all2 = yaml.safe_load(f) or {}
                    cdata = (_cfg_all2.get('tracked_coins') or {}).get(cid) or {}
                    market = cdata.get('market') or f"{sym}/USDT"
                    sym_to_mkt[sym] = market
            except Exception:
                pass
            try:
                ccxt_fetcher = CCXTPriceFetcher(exchange_name, sym_to_mkt)
            except Exception:
                ccxt_fetcher = None
        self.aggregator = PriceAggregator(self.fetcher, self.cg_fetcher,
                                          agreement_max_diff_pct=self.agreement_max_diff_pct,
                                          enabled_sources=[s.lower() for s in enabled_sources],
                                          ccxt=ccxt_fetcher)
        self.notifier = Notifier()
        self.global_interval_override = self._get_global_interval_override()
        # In-memory price history for indicators
        self.price_history: Dict[str, deque] = {}
        # Decision settings (safe defaults)
        self.suggestion_threshold: float = 0.5
        self.auto_threshold: float = 0.8
        # Higher auto threshold in bear regimes (defaults to auto_threshold if not configured)
        self.auto_threshold_bear: float = self.auto_threshold
        self.rsi_period: int = 14
        self.short_ma_window: int = 20
        self.long_ma_window: int = 50
        # MTF confirmation (optional)
        self.mtf_confirm_tf: str | None = None
        self.mtf_require_trend_agree: bool = False
        # Phase 3 settings
        self.ttl_seconds: int = 15
        self.auto_trade_enable: bool = False
        self.auto_trade_mode: str = "paper"  # paper|live
        self.paper_place_orders: bool = False
        self.trade_default_size_usd: float = 50.0
        self.spread_bps_default: int = 10
        # Fees and taxes (bps)
        self.fee_bps_default: float = 10.0
        self.tax_bps_default: float = 0.0
        # Edge requirements
        self.min_reward_to_risk: float = 1.3
        self.min_tp_edge_bps: float = 30.0
        # Paper executor (safe; only used if flags allow)
        self.paper = PaperExecutor()
        # Optional live executor (initialized if mode=live and keys available)
        self.live_executor: CCXTLiveExecutor | None = None
        self.live_exits_enable: bool = True
        # Live exits backoff state per symbol
        self._live_exit_backoff: Dict[str, Dict[str, float]] = {}
        # Last OCO placement status for UI
        self._last_oco_status: Dict[str, str] | None = None
        # Paper-mode break-even armed flags per symbol
        self._breakeven_armed: Dict[str, bool] = {}
        # Live-mode break-even armed flags per symbol
        self._live_be_armed: Dict[str, bool] = {}
        # Live-mode last trailing level per symbol (to avoid redundant updates)
        self._live_last_trail: Dict[str, float] = {}
        # Drawdown-based de-leveraging state
        self._equity_peak_usd: float | None = None
        self._dd_risk_factor: float = 1.0
        # SQLite persistence store
        try:
            db_path = (Path(__file__).parent.parent / 'logs' / 'tracker.db')
            self.store = SQLiteStore(db_path)
        except Exception:
            self.store = None
        try:
            with open(self.config_path, 'r') as f:
                _cfg_all_live = yaml.safe_load(f) or {}
            providers_cfg = (_cfg_all_live.get('providers') or {})
            exch_name = str(providers_cfg.get('exchange', 'binance')).lower()
            if self.auto_trade_mode == 'live':
                # Try EXCHANGE_API_KEY/SECRET; fallback to BINANCE
                key = os.environ.get(f"{exch_name.upper()}_API_KEY") or os.environ.get("BINANCE_API_KEY")
                secret = os.environ.get(f"{exch_name.upper()}_SECRET") or os.environ.get("BINANCE_SECRET")
                if key and secret:
                    self.live_executor = CCXTLiveExecutor(exch_name, key, secret)
                else:
                    console.print(f"[yellow]Live mode requested but API keys not found for {exch_name}. Staying in paper.[/]")
                    self.auto_trade_mode = 'paper'
        except Exception:
            self.live_executor = None
        # Risk defaults
        self.risk = RiskParams()
        # Portfolio state path and load persisted state if available
        self.state_path = (Path(__file__).parent.parent / 'logs' / 'state.json')
        loaded_port = None
        try:
            loaded_port = Portfolio.load_state(self.state_path)
        except Exception:
            loaded_port = None
        # Paper portfolio (in-memory)
        self.portfolio = loaded_port or Portfolio(initial_cash_usd=10000.0)
        # Execution guardrails
        self.max_open_positions: int = 999999
        self.per_coin_cooldown_seconds: int = 0
        self.max_exposure_pct: float = 1.0  # of reference equity; 1.0 = 100%
        self.max_exposure_usd: float | None = None
        self.daily_loss_cap_pct: float = 0.0  # disable new entries if daily equity drawdown beyond this
        self._daily_equity_start_usd: float | None = None
        self._last_equity_day: str | None = None
        self._last_close_ts: Dict[str, float] = {}
        # Position sizing defaults
        self.risk_budget_pct: float = 0.005  # 0.5% of equity by default
        self.max_size_usd: float | None = None
        self.min_size_usd: float | None = None
        # Volatility gating (ATR%) defaults
        self.vol_gate_min_atr_pct: float | None = None
        self.vol_gate_max_atr_pct: float | None = None
        # UI format defaults
        self.ui_thresholds = [1.0, 0.1, 0.01]
        self.ui_precisions = [2, 4, 6, 8]
        # Recent orders buffer
        self.recent_orders: deque = deque(maxlen=20)
        # Testing harness defaults
        self.testing_enabled: bool = False
        self.testing_force_auto_on_suggest: bool = False
        self.testing_global_price_offset_pct: float = 0.0
        self.testing_per_coin_price_offset_pct: Dict[str, float] = {}
        # Historical cache for indicators
        self.history: Dict[str, Dict[str, Any]] = {}
        # Strategy/risk toggles
        self.use_regime_filter: bool = False
        self.atr_params: ATRRiskParams | None = None
        self.atr_params_map: Dict[str, ATRRiskParams] = {}
        self._load_optional_settings()
        # Preload historical candles and indicators (non-blocking if provider fails)
        self._preload_history()

    def _preload_history(self):
        """Preload historical data for indicators."""
        try:
            with open(self.config_path, 'r') as f:
                cfg_all = yaml.safe_load(f) or {}
            data_cfg = (cfg_all.get('data') or {})
            tf = str(data_cfg.get('timeframe', '1d'))
            days = int(data_cfg.get('days', 365))
            cache_dir = str(data_cfg.get('cache_dir', './data_cache'))
            provider = str(data_cfg.get('provider', 'coingecko')).lower()
            # Save provider for UI
            self.history_provider = provider
            ind_cfg = (cfg_all.get('indicators') or {})
            rsi_p = int(ind_cfg.get('rsi_period', 14))
            ema_fast = int(ind_cfg.get('ema_fast', 20))
            ema_slow = int(ind_cfg.get('ema_slow', 50))
            atr_p = int(ind_cfg.get('atr_period', 14))

            # Optional CoinGecko id mapping from config
            cg_ids: Dict[str, str] = {}
            for cid, data in (cfg_all.get('tracked_coins') or {}).items():
                cgid = (data or {}).get('coingecko_id')
                if cgid:
                    cg_ids[cid] = str(cgid)

            loaded = 0
            # Save selected timeframe for refresh scheduling
            self.history_timeframe = tf
            for coin_id, coin_cfg in self.config.tracked_coins.items():
                if coin_cfg.disabled:
                    continue
                cg_key = cg_ids.get(coin_id, coin_id)
                try:
                    # Per-coin indicator overrides
                    cdata = (cfg_all.get('tracked_coins') or {}).get(coin_id) or {}
                    ind_over = (cdata.get('indicators') or {})
                    rsi_p_coin = int(ind_over.get('rsi_period', rsi_p))
                    ema_fast_coin = int(ind_over.get('ema_fast', ema_fast))
                    ema_slow_coin = int(ind_over.get('ema_slow', ema_slow))
                    atr_p_coin = int(ind_over.get('atr_period', atr_p))

                    # Fetch candles per provider
                    if provider == 'ccxt':
                        providers_cfg = (cfg_all.get('providers') or {})
                        exchange_name = str(providers_cfg.get('exchange', 'binance')).lower()
                        market = cdata.get('market') or f"{coin_cfg.symbol.upper()}/USDT"
                        if tf == '1d':
                            limit = min(int(days), 2000)
                        elif tf == '4h':
                            limit = min(int(days) * 6, 2000)
                        elif tf == '1h':
                            limit = min(int(days) * 24, 2000)
                        else:
                            limit = 1000
                        candles = get_candles_ccxt(exchange_name, market, timeframe=tf, cache_dir=cache_dir, limit=limit, use_cache=True)
                    else:
                        candles = get_candles(cg_key, timeframe=tf, days=days, cache_dir=cache_dir, use_cache=True)
                    if not candles:
                        continue
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
                    # Optional MTF confirmation timeframe preload (EMA only)
                    if self.mtf_confirm_tf and self.mtf_confirm_tf != tf:
                        try:
                            if provider == 'ccxt':
                                providers_cfg = (cfg_all.get('providers') or {})
                                exchange_name = str(providers_cfg.get('exchange', 'binance')).lower()
                                market = cdata.get('market') or f"{coin_cfg.symbol.upper()}/USDT"
                                if self.mtf_confirm_tf == '1d':
                                    limit2 = min(int(days), 2000)
                                elif self.mtf_confirm_tf == '4h':
                                    limit2 = min(int(days) * 6, 2000)
                                elif self.mtf_confirm_tf == '1h':
                                    limit2 = min(int(days) * 24, 2000)
                                else:
                                    limit2 = 1000
                                candles2 = get_candles_ccxt(exchange_name, market, timeframe=self.mtf_confirm_tf, cache_dir=cache_dir, limit=limit2, use_cache=True)
                            else:
                                candles2 = get_candles(cg_key, timeframe=self.mtf_confirm_tf, days=days, cache_dir=cache_dir, use_cache=True)
                            closes2 = [c.c for c in candles2]
                            ema_fast2 = ema_series(closes2, ema_fast_coin)
                            ema_slow2 = ema_series(closes2, ema_slow_coin)
                            self.history[coin_id]['confirm'] = {
                                'timeframe': self.mtf_confirm_tf,
                                'ema_fast': ema_fast2[-1] if ema_fast2 else None,
                                'ema_slow': ema_slow2[-1] if ema_slow2 else None,
                            }
                        except Exception:
                            pass
                    loaded += 1
                except Exception as ex:
                    log_event('history_load_error', {'coin': coin_id, 'error': str(ex)})
            if loaded > 0:
                console.print(f"[blue]Preloaded history for {loaded} assets (tf={tf}, days={days}).[/]")
                # Show history provider summary
                try:
                    providers_cfg = (cfg_all.get('providers') or {})
                    exchange_name = str(providers_cfg.get('exchange', 'binance')).lower()
                except Exception:
                    exchange_name = 'binance'
                hist_provider = provider.upper()
                hist_extra = f", exchange={exchange_name}" if provider == 'ccxt' else ""
                console.print(f"[blue]History provider: {hist_provider}{hist_extra}.[/]")
        except Exception as ex:
            log_event('history_init_error', {'error': str(ex)})
        self.setup_schedules()
    
    def _load_config(self, config_path: str) -> AppConfig:
        """Load configuration from YAML file, applying env overrides."""
        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)

            # Parse tracked coins from YAML
            tracked_coins = {
                coin_id: CoinConfig(
                    symbol=data['symbol'],
                    name=data['name'],
                    threshold=float(data['threshold']),
                    check_interval=int(data.get('check_interval', 300)),
                    disabled=bool(data.get('disabled', False))
                )
                for coin_id, data in config_data.get('tracked_coins', {}).items()
            }

            # ENV override: TRACKED_COINS to dynamically select which coins to track
            env_tracked = os.environ.get('TRACKED_COINS')
            if env_tracked:
                requested_ids = [c.strip() for c in env_tracked.split(',') if c.strip()]
                tracked_coins = {k: v for k, v in tracked_coins.items() if k in requested_ids}

            # ENV override: COIN_THRESHOLDS like "bitcoin=48000,ethereum=2900"
            env_thresholds = os.environ.get('COIN_THRESHOLDS')
            if env_thresholds:
                pairs = [p.strip() for p in env_thresholds.split(',') if p.strip()]
                for pair in pairs:
                    if '=' in pair:
                        cid, val = pair.split('=', 1)
                        cid = cid.strip()
                        try:
                            if cid in tracked_coins:
                                tracked_coins[cid].threshold = float(val)
                            else:
                                console.print(f"[yellow]Threshold provided for unknown coin '{cid}'. Define it in config.yaml or add it to TRACKED_COINS if needed.[/]")
                        except ValueError:
                            console.print(f"[yellow]Invalid threshold value '{val}' for coin '{cid}' in COIN_THRESHOLDS. Skipping.[/]")


            return AppConfig(
                tracked_coins=tracked_coins,
                api_base_url=config_data['api']['base_url'],
                api_timeout=config_data['api'].get('timeout', 10)
            )

        except Exception as e:
            console.print(f"[red]Error loading configuration: {e}[/red]")
            sys.exit(1)

    def _load_optional_settings(self):
        """Load optional non-critical settings from YAML (decision thresholds, etc.)."""
        try:
            with open(self.config_path, 'r') as f:
                cfg = yaml.safe_load(f) or {}
            # decision thresholds
            decision = (cfg.get('decision') or {})
            thresholds = (decision.get('confidence_thresholds') or {})
            self.suggestion_threshold = float(thresholds.get('suggestion', 0.5))
            self.auto_threshold = float(thresholds.get('auto', self.auto_threshold))
            try:
                ab = thresholds.get('auto_bear', None)
                self.auto_threshold_bear = float(ab) if ab is not None else self.auto_threshold
            except Exception:
                self.auto_threshold_bear = self.auto_threshold
            # price TTL
            price_cfg = (cfg.get('price') or {})
            self.ttl_seconds = int(price_cfg.get('ttl_seconds', self.ttl_seconds))
            # auto trade + paper flags
            at_cfg = (cfg.get('auto_trade') or {})
            self.auto_trade_enable = bool(at_cfg.get('enable', self.auto_trade_enable))
            try:
                self.auto_trade_mode = str(at_cfg.get('mode', self.auto_trade_mode)).lower()
            except Exception:
                self.auto_trade_mode = "paper"
            paper_cfg = (cfg.get('paper') or {})
            self.paper_place_orders = bool(paper_cfg.get('place_orders', self.paper_place_orders))
            # paper exits flag (used by trailing/SL/TP logic)
            self.paper_exits_enable = bool(paper_cfg.get('exits_enable', getattr(self, 'paper_exits_enable', False)))
            # trade sizing
            trade_cfg = (cfg.get('trade') or {})
            self.trade_default_size_usd = float(trade_cfg.get('default_size_usd', self.trade_default_size_usd))
            # liquidity
            liq_cfg = (cfg.get('liquidity') or {})
            self.spread_bps_default = int(liq_cfg.get('spread_bps_default', 10))
            # risk
            risk_cfg = (cfg.get('risk') or {})
            self.risk = RiskParams(
                stop_loss_pct=float(risk_cfg.get('stop_loss_pct', 0.03)),
                take_profit_pct=float(risk_cfg.get('take_profit_pct', 0.06)),
                trailing_stop_pct=float(risk_cfg.get('trailing_stop_pct', 0.04)),
            )
            # Providers & agreement
            providers_cfg = (cfg.get('providers') or {})
            sources = providers_cfg.get('sources') or None
            if sources and isinstance(sources, list):
                try:
                    self.aggregator.enabled_sources = set(sources)
                except Exception:
                    pass
                # Pyramiding: add on ATR-based advances
                try:
                    if pos.adds_count < self.pyr_max_adds:
                        # Determine anchor price (last add or entry)
                        anchor_px = float(pos.last_add_price or pos.entry_price)
                        # Need ATR for trigger
                        atr_last = None
                        coin_id = None
                        for cid, cfgc in self.config.tracked_coins.items():
                            if cfgc.symbol.upper() == sym:
                                coin_id = cid
                                break
                        if coin_id is not None:
                            atr_last = (self.history.get(coin_id, {}) or {}).get('last', {}).get('atr')
                        if atr_last is not None and float(atr_last) > 0:
                            if float(current_price) >= anchor_px + self.pyr_atr_trigger * float(atr_last):
                                # Compute add size in USD
                                frac = self.pyr_add_fracs[min(pos.adds_count, len(self.pyr_add_fracs)-1)] if self.pyr_add_fracs else 0.5
                                add_size_usd = float(self.trade_default_size_usd) * float(self._dd_risk_factor) * float(frac)
                                # Edge check again
                                can_add = True
                                try:
                                    sl0, tp0 = compute_stop_levels(float(current_price), self.risk)
                                    if sl0 is not None and tp0 is not None and float(current_price) > 0:
                                        rr = (tp0 - float(current_price)) / max(1e-12, float(current_price) - sl0)
                                        fees_total_bps = float(self.fee_bps_default) * 2.0 + float(self.tax_bps_default) + float(self.spread_bps_default)
                                        tp_edge_bps = (tp0 - float(current_price)) / float(current_price) * 10000.0
                                        if rr < float(self.min_reward_to_risk) or tp_edge_bps <= (fees_total_bps + float(self.min_tp_edge_bps)):
                                            can_add = False
                                except Exception:
                                    pass
                                if can_add:
                                    market_pair = self._symbol_to_market(sym)
                                    if self.auto_trade_mode == 'live' and self.live_executor is not None:
                                        try:
                                            live_order = self.live_executor.place_order(symbol=market_pair, side='buy', size_usd=add_size_usd, order_type='market')
                                            exec_price = float(live_order.price or current_price)
                                            self.portfolio.add_to_position(sym, usd_size=add_size_usd, price=exec_price, fee_bps=self.fee_bps_default)
                                            log_event('live_pyramid_add', {
                                                'symbol': sym,
                                                'market': market_pair,
                                                'add_usd': add_size_usd,
                                                'price': exec_price,
                                                'adds_count': int(self.portfolio.get(sym).adds_count if self.portfolio.get(sym) else 0),
                                                'order_id': live_order.id,
                                                'status': live_order.status,
                                            })
                                            # Persist order
                                            try:
                                                if self.store is not None:
                                                    self.store.insert_order({
                                                        'symbol': sym,
                                                        'market': market_pair,
                                                        'side': 'buy',
                                                        'size_usd': add_size_usd,
                                                        'price': exec_price,
                                                        'provider': 'ccxt',
                                                        'order_id': live_order.id,
                                                        'status': live_order.status,
                                                    })
                                            except Exception:
                                                pass
                                            # Update protective stop to new trailing (reuse live adaptive logic)
                                            # Will be handled by subsequent loop iteration raising trailing
                                        except Exception as ex:
                                            log_event('live_pyramid_error', {'symbol': sym, 'error': str(ex)})
                                    else:
                                        # Paper add
                                        self.portfolio.add_to_position(sym, usd_size=add_size_usd, price=float(current_price), fee_bps=self.fee_bps_default)
                                        log_event('paper_pyramid_add', {
                                            'symbol': sym,
                                            'add_usd': add_size_usd,
                                            'price': float(current_price),
                                            'adds_count': int(self.portfolio.get(sym).adds_count if self.portfolio.get(sym) else 0),
                                        })
                                        try:
                                            self.portfolio.save_state(self.state_path)
                                        except Exception:
                                            pass
                except Exception:
                    pass
                # Live adaptive trailing: attempt to update protective stop upwards when conditions tighten
                try:
                    if self.live_executor is not None:
                        entry_px = float(pos.entry_price)
                        # reuse ATR/tighten logic similar to paper
                        atr_last = None
                        coin_id = None
                        for cid, cfgc in self.config.tracked_coins.items():
                            if cfgc.symbol.upper() == sym:
                                coin_id = cid
                                break
                        if coin_id is not None:
                            atr_last = (self.history.get(coin_id, {}) or {}).get('last', {}).get('atr')
                        atr_pct_now = (float(atr_last) / float(current_price) * 100.0) if (atr_last is not None and float(current_price) > 0) else 0.0
                        # Estimate base trailing as fraction from peak using current ATR params
                        coin_atr_params = self.atr_params_map.get(coin_id, self.atr_params)
                        if (coin_atr_params is not None) and (atr_last is not None) and (float(atr_last) > 0):
                            trailing_level_base = compute_trailing_stop_atr(float(pos.peak_price), float(atr_last), coin_atr_params) or compute_trailing_stop(float(pos.peak_price), self.risk)
                        else:
                            trailing_level_base = compute_trailing_stop(float(pos.peak_price), self.risk)
                        trailing_level_eff = float(trailing_level_base)
                        # Momentum as R multiple
                        # Risk from initial SL estimate
                        try:
                            sl0, _ = compute_stop_levels(entry_px, self.risk)
                            rr_unrealized = (float(current_price) - entry_px) / max(1e-12, (entry_px - float(sl0)))
                        except Exception:
                            rr_unrealized = 0.0
                        if rr_unrealized >= self.trail_up_momentum_r or atr_pct_now >= self.trail_up_atr_pct_min:
                            tighten_to = entry_px + (float(current_price) - entry_px) * (1.0 - self.trail_up_tighten_factor)
                            trailing_level_eff = max(trailing_level_eff, tighten_to)
                        # Respect break-even
                        if self._live_be_armed.get(sym, False):
                            trailing_level_eff = max(trailing_level_eff, entry_px)
                        # If we can raise the last trailing level, try placing a new protective stop-limit
                        prev = float(self._live_last_trail.get(sym, 0.0))
                        if trailing_level_eff > prev and float(current_price) > trailing_level_eff:
                            limit_px = trailing_level_eff * 0.999
                            ok2 = self.live_executor.place_stop_limit_sell(
                                symbol=self._symbol_to_market(sym),
                                quantity=float(pos.units),
                                stop_price=trailing_level_eff,
                                limit_price=limit_px,
                            )
                            if ok2:
                                self._live_last_trail[sym] = trailing_level_eff
                                log_event('live_trail_update', {
                                    'symbol': sym,
                                    'stop_price': trailing_level_eff,
                                    'limit_price': limit_px,
                                })
                except Exception:
                    pass
            self.agreement_max_diff_pct = float(providers_cfg.get('agreement_max_diff_pct', self.agreement_max_diff_pct))
            # Execution fees/taxes
            exec_cfg = (cfg.get('execution') or {})
            try:
                self.fee_bps_default = float(exec_cfg.get('fee_bps', self.fee_bps_default))
            except Exception:
                pass
            try:
                self.tax_bps_default = float(exec_cfg.get('tax_bps', self.tax_bps_default))
            except Exception:
                pass
            # Edge gating
            strat2b = (cfg.get('strategy') or {})
            try:
                self.min_reward_to_risk = float(strat2b.get('min_reward_to_risk', self.min_reward_to_risk))
            except Exception:
                pass
            try:
                self.min_tp_edge_bps = float(strat2b.get('min_tp_edge_bps', self.min_tp_edge_bps))
            except Exception:
                pass
            # De-leveraging thresholds (drawdown tiers)
            self.dd_t1_pct = float((strat2b.get('dd_tier1_pct', 5.0)))   # 5%
            self.dd_t2_pct = float((strat2b.get('dd_tier2_pct', 10.0)))  # 10%
            self.dd_t1_factor = float((strat2b.get('dd_tier1_factor', 0.75)))
            self.dd_t2_factor = float((strat2b.get('dd_tier2_factor', 0.50)))
            # Adaptive trailing upgrade thresholds
            tr_up = (strat2b.get('trail_upgrade') or {})
            self.trail_up_atr_pct_min = float(tr_up.get('atr_pct_min', 6.0))   # tighten if ATR% high
            self.trail_up_momentum_r = float(tr_up.get('momentum_r', 1.5))     # tighten if R>=1.5
            self.trail_up_tighten_factor = float(tr_up.get('tighten_factor', 0.7))  # 30% tighter
            # Pyramiding controls
            pyr = (strat2b.get('pyramiding') or {})
            self.pyr_max_adds = int(pyr.get('max_adds', 2))
            self.pyr_atr_trigger = float(pyr.get('atr_trigger', 1.0))
            self.pyr_add_fracs = pyr.get('add_fracs', [0.5, 0.33])
            try:
                self.pyr_add_fracs = [float(x) for x in self.pyr_add_fracs]
            except Exception:
                self.pyr_add_fracs = [0.5, 0.33]
            # MTF confirmation
            data_cfg2 = (cfg.get('data') or {})
            try:
                tf2 = data_cfg2.get('confirmation_timeframe')
                self.mtf_confirm_tf = str(tf2) if tf2 else None
            except Exception:
                self.mtf_confirm_tf = None
            strat2 = (cfg.get('strategy') or {})
            try:
                self.mtf_require_trend_agree = bool(strat2.get('mtf_require_trend_agree', self.mtf_require_trend_agree))
            except Exception:
                pass
            # Per-coin overrides: ATR, regime, vol gate, thresholds
            self.atr_params_map: Dict[str, ATRRiskParams] = getattr(self, 'atr_params_map', {})
            self.per_coin_use_regime: Dict[str, bool] = {}
            self.per_coin_vol_gate: Dict[str, Dict[str, float | None]] = {}
            self.per_coin_auto_thr: Dict[str, float] = {}
            self.per_coin_auto_thr_bear: Dict[str, float | None] = {}
            self.per_coin_suggest_thr: Dict[str, float] = {}
            tcoins = (cfg.get('tracked_coins') or {})
            for cid, cdata in tcoins.items():
                try:
                    # ATR
                    atrc = (cdata or {}).get('atr') or {}
                    if atrc:
                        slm = float(atrc.get('sl_mult')) if atrc.get('sl_mult') is not None else None
                        tpm = float(atrc.get('tp_mult')) if atrc.get('tp_mult') is not None else None
                        trm = float(atrc.get('trail_mult')) if atrc.get('trail_mult') is not None else None
                        if any(v is not None for v in (slm, tpm, trm)):
                            base = self.atr_params
                            self.atr_params_map[cid] = ATRRiskParams(
                                atr_period=getattr(base, 'atr_period', 14),
                                sl_mult=slm if slm is not None else getattr(base, 'sl_mult', 1.5),
                                tp_mult=tpm if tpm is not None else getattr(base, 'tp_mult', 3.0),
                                trail_mult=trm if trm is not None else getattr(base, 'trail_mult', 2.0),
                            )
                    # Strategy
                    sc = (cdata or {}).get('strategy') or {}
                    if 'use_regime_filter' in sc:
                        self.per_coin_use_regime[cid] = bool(sc.get('use_regime_filter'))
                    vg = (sc.get('vol_gate') or {})
                    if vg:
                        vmin = float(vg.get('min_atr_pct')) if vg.get('min_atr_pct') is not None else None
                        vmax = float(vg.get('max_atr_pct')) if vg.get('max_atr_pct') is not None else None
                        self.per_coin_vol_gate[cid] = { 'min': vmin, 'max': vmax }
                    # Decision thresholds
                    dc = (cdata or {}).get('decision') or {}
                    th = (dc.get('thresholds') or {})
                    if th:
                        if th.get('auto') is not None:
                            self.per_coin_auto_thr[cid] = float(th.get('auto'))
                        if th.get('auto_bear') is not None:
                            self.per_coin_auto_thr_bear[cid] = float(th.get('auto_bear'))
                        if th.get('suggestion') is not None:
                            self.per_coin_suggest_thr[cid] = float(th.get('suggestion'))
                except Exception:
                    continue
            # UI formatting
            ui_cfg = (cfg.get('ui') or {})
            pf = (ui_cfg.get('price_format') or {})
            th = pf.get('thresholds')
            pr = pf.get('precisions')
            if isinstance(th, list) and len(th) == 3:
                self.ui_thresholds = [float(x) for x in th]
            if isinstance(pr, list) and len(pr) == 4:
                self.ui_precisions = [int(x) for x in pr]
            # Execution guardrails
            exe = (cfg.get('execution') or {})
            self.max_open_positions = int(exe.get('max_open_positions', self.max_open_positions))
            self.per_coin_cooldown_seconds = int(exe.get('per_coin_cooldown_seconds', self.per_coin_cooldown_seconds))
            # ATR-based sizing knobs
            try:
                self.risk_budget_pct = float(exe.get('risk_budget_pct', self.risk_budget_pct))
            except Exception:
                pass
            try:
                msu = exe.get('max_size_usd')
                self.max_size_usd = float(msu) if msu is not None else self.max_size_usd
            except Exception:
                pass
            try:
                mns = exe.get('min_size_usd')
                self.min_size_usd = float(mns) if mns is not None else self.min_size_usd
            except Exception:
                pass
            # Logging
            logging_cfg = (cfg.get('logging') or {})
            log_dir = logging_cfg.get('dir')
            try:
                # default to project logs/ if not provided
                if log_dir is None:
                    default_logs = (Path(__file__).parent.parent / 'logs')
                    configure_file_logging(str(default_logs))
                else:
                    configure_file_logging(str(log_dir))
            except Exception:
                configure_file_logging(None)
            # Testing harness
            testing_cfg = (cfg.get('testing') or {})
            self.testing_enabled = bool(testing_cfg.get('enabled', False))
            self.testing_force_auto_on_suggest = bool(testing_cfg.get('force_auto_on_suggest', False))
            try:
                self.testing_global_price_offset_pct = float(testing_cfg.get('global_price_offset_pct', 0.0))
            except Exception:
                self.testing_global_price_offset_pct = 0.0
            per_coin = testing_cfg.get('per_coin_price_offset_pct') or {}
            if isinstance(per_coin, dict):
                try:
                    self.testing_per_coin_price_offset_pct = {str(k): float(v) for k, v in per_coin.items()}
                except Exception:
                    self.testing_per_coin_price_offset_pct = {}
            # Strategy toggles
            strat = (cfg.get('strategy') or {})
            self.use_regime_filter = bool(strat.get('use_regime_filter', self.use_regime_filter))
            # Volatility gating
            vg = (strat.get('vol_gate') or {})
            try:
                mnp = vg.get('min_atr_pct')
                self.vol_gate_min_atr_pct = float(mnp) if mnp is not None else self.vol_gate_min_atr_pct
            except Exception:
                pass
            try:
                mxp = vg.get('max_atr_pct')
                self.vol_gate_max_atr_pct = float(mxp) if mxp is not None else self.vol_gate_max_atr_pct
            except Exception:
                pass
            # ATR risk params
            risk_cfg2 = (cfg.get('risk') or {})
            atr_cfg = (risk_cfg2.get('atr') or {})
            try:
                self.atr_params = ATRRiskParams(
                    atr_period=int(atr_cfg.get('period', 14)),
                    sl_mult=float(atr_cfg.get('sl_mult', 1.5)),
                    tp_mult=float(atr_cfg.get('tp_mult', 3.0)),
                    trail_mult=float(atr_cfg.get('trail_mult', 2.0)),
                )
            except Exception:
                self.atr_params = None
            # Per-coin ATR overrides
            self.atr_params_map = {}
            try:
                for cid, cdata in (cfg.get('tracked_coins') or {}).items():
                    rc = ((cdata or {}).get('risk') or {})
                    ac = (rc.get('atr') or {})
                    if ac:
                        try:
                            self.atr_params_map[cid] = ATRRiskParams(
                                atr_period=int(ac.get('period', self.atr_params.atr_period if self.atr_params else 14)),
                                sl_mult=float(ac.get('sl_mult', self.atr_params.sl_mult if self.atr_params else 1.5)),
                                tp_mult=float(ac.get('tp_mult', self.atr_params.tp_mult if self.atr_params else 3.0)),
                                trail_mult=float(ac.get('trail_mult', self.atr_params.trail_mult if self.atr_params else 2.0)),
                            )
                        except Exception:
                            continue
            except Exception:
                pass
        except Exception:
            # Keep defaults on any error
            pass

    def _get_global_interval_override(self) -> int | None:
        """Read CHECK_INTERVAL_SECONDS env to override per-coin intervals."""
        val = os.environ.get('CHECK_INTERVAL_SECONDS')
        if not val:
            return None
        try:
            seconds = int(val)
            if seconds <= 0:
                raise ValueError("Interval must be positive")
            return seconds
        except ValueError:
            console.print("[yellow]Invalid CHECK_INTERVAL_SECONDS. Using per-coin intervals from config.yaml.[/]")
            return None

    def setup_schedules(self):
        """Set up a single batched job for all enabled coins."""
        schedule.clear()
        # Choose interval: global override if set, else minimum of enabled coins' intervals
        enabled = [cfg for cfg in self.config.tracked_coins.values() if not cfg.disabled]
        if not enabled:
            console.print("[yellow]No enabled coins to track.[/]")
            return
        if self.global_interval_override:
            interval = self.global_interval_override
        else:
            interval = min(cfg.check_interval for cfg in enabled)
        schedule.every(interval).seconds.do(self.check_all_prices)
        console.print(
            f"[blue]Using {'global ' if self.global_interval_override else ''}interval: every {interval}s.[/]"
        )
        # Schedule periodic history tail refresh to keep indicators fresh
        try:
            tf = getattr(self, 'history_timeframe', '1d')
            if tf == '1d':
                refresh_seconds = 300  # 5 minutes
            elif tf in ('4h', '1h'):
                refresh_seconds = 60   # 1 minute
            else:
                refresh_seconds = max(60, interval)
            schedule.every(refresh_seconds).seconds.do(self._refresh_history_tail)
            # Live exits manager runs frequently if live mode
            if getattr(self, 'auto_trade_mode', 'paper') == 'live' and self.live_executor is not None and self.live_exits_enable:
                schedule.every(5).seconds.do(self._manage_live_exits)
        except Exception:
            # Best-effort scheduling; ignore errors
            pass

    def _refresh_history_tail(self):
        """Refresh the latest candles and update last indicator values for tracked coins."""
        try:
            with open(self.config_path, 'r') as f:
                cfg_all = yaml.safe_load(f) or {}
            data_cfg = (cfg_all.get('data') or {})
            tf = str(data_cfg.get('timeframe', getattr(self, 'history_timeframe', '1d')))
            days = int(data_cfg.get('days', 365))
            cache_dir = str(data_cfg.get('cache_dir', './data_cache'))
            provider = str(data_cfg.get('provider', 'coingecko')).lower()
            ind_cfg = (cfg_all.get('indicators') or {})
            rsi_p = int(ind_cfg.get('rsi_period', 14))
            ema_fast = int(ind_cfg.get('ema_fast', 20))
            ema_slow = int(ind_cfg.get('ema_slow', 50))
            atr_p = int(ind_cfg.get('atr_period', 14))

            cg_ids: Dict[str, str] = {}
            for cid, data in (cfg_all.get('tracked_coins') or {}).items():
                cgid = (data or {}).get('coingecko_id')
                if cgid:
                    cg_ids[cid] = str(cgid)

            for coin_id, coin_cfg in self.config.tracked_coins.items():
                if coin_cfg.disabled:
                    continue
                cg_key = cg_ids.get(coin_id, coin_id)
                try:
                    if provider == 'ccxt':
                        providers_cfg = (cfg_all.get('providers') or {})
                        exchange_name = str(providers_cfg.get('exchange', 'binance')).lower()
                        cdata = (cfg_all.get('tracked_coins') or {}).get(coin_id) or {}
                        market = cdata.get('market') or f"{coin_cfg.symbol.upper()}/USDT"
                        if tf == '1d':
                            limit = min(int(days), 2000)
                        elif tf == '4h':
                            limit = min(int(days) * 6, 2000)
                        elif tf == '1h':
                            limit = min(int(days) * 24, 2000)
                        else:
                            limit = 1000
                        candles = get_candles_ccxt(exchange_name, market, timeframe=tf, cache_dir=cache_dir, limit=limit, use_cache=False)
                    else:
                        candles = get_candles(cg_key, timeframe=tf, days=days, cache_dir=cache_dir, use_cache=False)
                    if not candles:
                        continue
                    closes = [c.c for c in candles]
                    highs = [c.h for c in candles]
                    lows = [c.l for c in candles]
                    rsi_vals = rsi_series(closes, rsi_p)
                    ema_fast_vals = ema_series(closes, ema_fast)
                    ema_slow_vals = ema_series(closes, ema_slow)
                    atr_vals = atr_series(highs, lows, closes, atr_p)
                    # Update only the 'last' snapshot to avoid memory churn
                    h = self.history.setdefault(coin_id, {})
                    h['last'] = {
                        'rsi': rsi_vals[-1] if rsi_vals else None,
                        'ema_fast': ema_fast_vals[-1] if ema_fast_vals else None,
                        'ema_slow': ema_slow_vals[-1] if ema_slow_vals else None,
                        'atr': atr_vals[-1] if atr_vals else None,
                        'close': closes[-1] if closes else None,
                    }
                    h['timeframe'] = tf
                    # Refresh confirmation timeframe EMA last values if configured
                    if self.mtf_confirm_tf and self.mtf_confirm_tf != tf:
                        try:
                            if provider == 'ccxt':
                                if self.mtf_confirm_tf == '1d':
                                    limit2 = min(int(days), 2000)
                                elif self.mtf_confirm_tf == '4h':
                                    limit2 = min(int(days) * 6, 2000)
                                elif self.mtf_confirm_tf == '1h':
                                    limit2 = min(int(days) * 24, 2000)
                                else:
                                    limit2 = 1000
                                candles2 = get_candles_ccxt(exchange_name, market, timeframe=self.mtf_confirm_tf, cache_dir=cache_dir, limit=limit2, use_cache=False)
                            else:
                                candles2 = get_candles(cg_key, timeframe=self.mtf_confirm_tf, days=days, cache_dir=cache_dir, use_cache=False)
                            closes2 = [c.c for c in candles2]
                            ema_fast2 = ema_series(closes2, ema_fast)
                            ema_slow2 = ema_series(closes2, ema_slow)
                            h['confirm'] = {
                                'timeframe': self.mtf_confirm_tf,
                                'ema_fast': ema_fast2[-1] if ema_fast2 else None,
                                'ema_slow': ema_slow2[-1] if ema_slow2 else None,
                            }
                        except Exception:
                            pass
                except Exception:
                    # Ignore refresh errors per coin
                    pass
        except Exception:
            # Ignore outer refresh errors
            pass

    def _manage_live_exits(self):
        """Best-effort manager for live positions: if SL/TP/trailing is hit, submit a market sell via CCXT and persist state.
        This is intentionally simple for safety; it acts only when live mode is enabled and an executor exists.
        """
        try:
            if self.auto_trade_mode != 'live' or self.live_executor is None:
                return
            # Map symbols to current prices via aggregator results
            enabled_map = {cid: cfg.symbol for cid, cfg in self.config.tracked_coins.items() if not cfg.disabled}
            aggregated = self.aggregator.aggregate_prices(enabled_map)
            sym_to_price: Dict[str, float] = {}
            for cid, pdata in (aggregated or {}).items():
                try:
                    price = pdata.get('price') if isinstance(pdata, dict) else None
                    sym = (self.config.tracked_coins.get(cid).symbol.upper() if cid in self.config.tracked_coins else None)
                    if price is not None and sym:
                        sym_to_price[sym] = float(price)
                except Exception:
                    continue
            # For each open position, check exits
            for sym, pos in list(self.portfolio.positions.items()):
                # Backoff handling: skip symbol if in backoff window
                try:
                    st = self._live_exit_backoff.get(sym)
                    if st and time.time() < float(st.get('next_ts', 0.0)):
                        continue
                except Exception:
                    pass
                current_price = sym_to_price.get(sym)
                if current_price is None:
                    continue
                # Update peak
                pos.update_peak(float(current_price))
                # Live break-even: if unrealized R>=1 and not armed yet, arm a stop at entry
                try:
                    if self.live_executor is not None and not self._live_be_armed.get(sym, False):
                        # Compute RR vs current SL estimate based on ATR params
                        coin_id = None
                        for cid, cfgc in self.config.tracked_coins.items():
                            if cfgc.symbol.upper() == sym:
                                coin_id = cid
                                break
                        sl_from_entry = None
                        if coin_id:
                            atr_last = (self.history.get(coin_id, {}) or {}).get('last', {}).get('atr')
                            coin_atr_params = self.atr_params_map.get(coin_id, self.atr_params)
                            if (coin_atr_params is not None) and (atr_last is not None) and (float(atr_last) > 0):
                                sl_tmp, _tp_tmp = compute_stop_levels_atr(float(pos.entry_price), float(atr_last), coin_atr_params)
                                sl_from_entry = sl_tmp
                        if sl_from_entry is None:
                            sl_from_entry, _ = compute_stop_levels(float(pos.entry_price), self.risk)
                        entry_px = float(pos.entry_price)
                        risk_per_unit = max(1e-12, entry_px - float(sl_from_entry))
                        rr_unrealized = (float(current_price) - entry_px) / risk_per_unit
                        if rr_unrealized >= 1.0:
                            # Place/Update protective stop at entry (stop-limit a hair below)
                            limit_px = entry_px * 0.999
                            try:
                                ok = self.live_executor.place_stop_limit_sell(
                                    symbol=self._symbol_to_market(sym),
                                    quantity=float(pos.units),
                                    stop_price=entry_px,
                                    limit_price=limit_px,
                                )
                                if ok:
                                    self._live_be_armed[sym] = True
                                    log_event('live_be_armed', {
                                        'symbol': sym,
                                        'entry': entry_px,
                                        'stop_price': entry_px,
                                        'limit_price': limit_px,
                                        'rr_now': rr_unrealized,
                                    })
                            except Exception as ex:
                                log_event('live_be_error', {'symbol': sym, 'error': str(ex)})
                except Exception:
                    pass
                # Get ATR params and last ATR for this coin if available
                coin_id = None
                for cid, cfgc in self.config.tracked_coins.items():
                    if cfgc.symbol.upper() == sym:
                        coin_id = cid
                        break
                coin_atr_params = self.atr_params_map.get(coin_id, self.atr_params)
                atr_last = None
                if coin_id is not None:
                    atr_last = (self.history.get(coin_id, {}) or {}).get('last', {}).get('atr')
                # Compute SL/TP
                if (coin_atr_params is not None) and (atr_last is not None) and (float(atr_last) > 0):
                    sl_from_entry, tp_from_entry = compute_stop_levels_atr(float(pos.entry_price), float(atr_last), coin_atr_params)
                    if sl_from_entry is None or tp_from_entry is None:
                        sl_from_entry, tp_from_entry = compute_stop_levels(float(pos.entry_price), self.risk)
                    trailing_level = compute_trailing_stop_atr(float(pos.peak_price), float(atr_last), coin_atr_params) or compute_trailing_stop(float(pos.peak_price), self.risk)
                else:
                    sl_from_entry, tp_from_entry = compute_stop_levels(float(pos.entry_price), self.risk)
                    trailing_level = compute_trailing_stop(float(pos.peak_price), self.risk)
                reason = None
                if float(current_price) <= float(sl_from_entry):
                    reason = 'stop_loss'
                elif float(current_price) >= float(tp_from_entry):
                    reason = 'take_profit'
                elif float(current_price) <= float(trailing_level):
                    reason = 'trailing_stop'
                if reason is None:
                    continue
                # Resolve market pair
                try:
                    with open(self.config_path, 'r') as f:
                        cfg_all2 = yaml.safe_load(f) or {}
                    per_coin = (cfg_all2.get('tracked_coins') or {}).get(coin_id) or {}
                    market_pair = per_coin.get('market') or f"{sym}/USDT"
                except Exception:
                    market_pair = f"{sym}/USDT"
                # Place market sell for full position value in USD
                try:
                    size_usd = float(current_price) * float(pos.units)
                    if size_usd <= 0:
                        continue
                    live_order = self.live_executor.place_order(symbol=market_pair, side='sell', size_usd=size_usd, order_type='market')
                    # Close position in portfolio at execution price
                    exec_price = float(live_order.price or current_price)
                    closed = self.portfolio.close(sym, price=exec_price)
                    log_event('live_exit', {
                        'symbol': sym,
                        'market': market_pair,
                        'reason': reason,
                        'order_id': live_order.id,
                        'status': live_order.status,
                        'exit_price': exec_price,
                        'pnl_pct': (closed.get('pnl_pct') if closed else None),
                    })
                    try:
                        self.portfolio.save_state(self.state_path)
                    except Exception:
                        pass
                    # Persist trade in SQLite
                    try:
                        if self.store is not None:
                            self.store.insert_trade({
                                'symbol': sym,
                                'market': market_pair,
                                'reason': reason,
                                'entry_price': float(closed.get('entry_price')) if closed else None,
                                'exit_price': exec_price,
                                'pnl_pct': (closed.get('pnl_pct') if closed else None),
                                'order_id': live_order.id,
                                'status': live_order.status,
                            })
                    except Exception:
                        pass
                    # reset backoff state on success
                    try:
                        if sym in self._live_exit_backoff:
                            del self._live_exit_backoff[sym]
                    except Exception:
                        pass
                except Exception as ex:
                    log_event('live_exit_error', {'symbol': sym, 'reason': reason, 'error': str(ex)})
                    # increase backoff for this symbol
                    try:
                        st = self._live_exit_backoff.get(sym) or {"retries": 0.0, "next_ts": 0.0}
                        retries = float(st.get('retries', 0.0)) + 1.0
                        delay = min(60.0, max(2.0, 2.0 ** retries))
                        self._live_exit_backoff[sym] = {"retries": retries, "next_ts": time.time() + delay}
                    except Exception:
                        pass
        except Exception:
            # Never raise from background manager
            pass

    def check_coin_price(self, coin_id: str, coin_config: CoinConfig):
        """Check and log the price of a single cryptocurrency."""
        console.print(f"🔍 Checking {coin_config.name} ({coin_config.symbol.upper()})...")
        prices = self.fetcher.get_prices_by_symbols({coin_id: coin_config.symbol})
        current_price = prices.get(coin_id)
        if current_price is not None:
            price_str = f"${current_price:,.2f}"
            threshold_str = f"${coin_config.threshold:,.2f}"
            # Determine equality with a small epsilon to avoid float noise
            eps = 1e-9
            if abs(current_price - coin_config.threshold) <= eps:
                status = "[yellow]="
            else:
                status = "[green]✓" if current_price > coin_config.threshold else "[red]✗"
            console.print(f"   {status} {coin_config.name}: {price_str} (Threshold: {threshold_str})[/]")
            self.notifier.check_thresholds(
                coin_id=coin_id,
                coin_name=coin_config.name,
                current_price=current_price,
                threshold=coin_config.threshold
            )
        else:
            console.print(f"   [yellow]⚠ Could not fetch price for {coin_config.name}[/]")

    def check_all_prices(self):
        """Batched check: fetch all enabled coins in one API call and process alerts."""
        enabled_map = {cid: cfg.symbol for cid, cfg in self.config.tracked_coins.items() if not cfg.disabled}
        if not enabled_map:
            return
        # Build optional CoinGecko ID mapping from config if provided per coin
        cg_ids = {}
        try:
            with open(self.config_path, 'r') as f:
                cfg_all = yaml.safe_load(f) or {}
            for cid, data in (cfg_all.get('tracked_coins') or {}).items():
                cg_id = (data or {}).get('coingecko_id')
                if cg_id:
                    cg_ids[cid] = str(cg_id)
        except Exception:
            pass
        aggregated = self.aggregator.aggregate_prices(enabled_map, cg_ids=cg_ids or None)
        # Compute portfolio exposure and daily equity state
        # Map symbol->price using aggregated results (where available)
        sym_to_price: Dict[str, float] = {}
        for cid, pdata in (aggregated or {}).items():
            try:
                price = pdata.get('price') if isinstance(pdata, dict) else None
                sym = (self.config.tracked_coins.get(cid).symbol.upper() if cid in self.config.tracked_coins else None)
                if price is not None and sym:
                    sym_to_price[sym] = float(price)
            except Exception:
                continue
        # Current portfolio equity (positions only; paper mode has no cash tracking yet)
        equity_now = 0.0
        for sym, pos in self.portfolio.positions.items():
            px = sym_to_price.get(sym)
            if px is not None:
                equity_now += float(pos.units) * float(px)
        # Persist equity snapshot
        try:
            if getattr(self, 'store', None) is not None:
                self.store.insert_equity(equity_now)
        except Exception:
            pass
        # Update equity peak and DD-based risk factor
        try:
            if self._equity_peak_usd is None or equity_now > float(self._equity_peak_usd):
                self._equity_peak_usd = float(equity_now)
            dd_pct = 0.0
            if self._equity_peak_usd and self._equity_peak_usd > 0:
                dd_pct = max(0.0, (self._equity_peak_usd - equity_now) / self._equity_peak_usd * 100.0)
            # Tiers: > t2 -> factor2, > t1 -> factor1, else 1.0
            if dd_pct >= self.dd_t2_pct:
                self._dd_risk_factor = self.dd_t2_factor
            elif dd_pct >= self.dd_t1_pct:
                self._dd_risk_factor = self.dd_t1_factor
            else:
                self._dd_risk_factor = 1.0
        except Exception:
            self._dd_risk_factor = 1.0
        # Daily start reset on UTC day boundary
        day_now = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        if (self._last_equity_day or day_now) != day_now or self._daily_equity_start_usd is None:
            self._daily_equity_start_usd = equity_now
            self._last_equity_day = day_now
        # Exposure
        total_exposure_usd = equity_now
        max_exposure_hit = False
        if self.max_exposure_usd is not None and total_exposure_usd >= self.max_exposure_usd:
            max_exposure_hit = True
        # If we had a reference equity notion, we would compare pct; in paper mode, use 100% baseline of start
        if self.max_exposure_pct is not None and self._daily_equity_start_usd is not None and self._daily_equity_start_usd > 0:
            if total_exposure_usd / self._daily_equity_start_usd > self.max_exposure_pct:
                max_exposure_hit = True
        # Daily loss
        daily_loss_hit = False
        if self.daily_loss_cap_pct and self._daily_equity_start_usd and self._daily_equity_start_usd > 0:
            dd = (equity_now - self._daily_equity_start_usd) / self._daily_equity_start_usd
            if dd <= -abs(self.daily_loss_cap_pct):
                daily_loss_hit = True
        # Apply testing price offsets (if enabled)
        if self.testing_enabled and (self.testing_global_price_offset_pct != 0.0 or self.testing_per_coin_price_offset_pct):
            for cid, pdata in aggregated.items():
                try:
                    if not isinstance(pdata, dict):
                        continue
                    price = pdata.get('price')
                    if price is None:
                        continue
                    offset_pct = self.testing_global_price_offset_pct
                    if cid in self.testing_per_coin_price_offset_pct:
                        offset_pct += self.testing_per_coin_price_offset_pct[cid]
                    pdata['price'] = float(price) * (1.0 + offset_pct)
                except Exception:
                    continue

        # Build and print a single table for this batch
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Coin", width=20)
        table.add_column("Price (USD)", justify="right")
        table.add_column("Threshold", justify="right")
        table.add_column("Status", justify="center")
        table.add_column("Exchange", justify="left")
        table.add_column("Last Checked (UTC)", justify="left")
        table.add_column("Signal", justify="left")
        table.add_column("Confidence", justify="right")
        table.add_column("Exp. Slip (%)", justify="right")
        table.add_column("Agreement (%)", justify="right")
        table.add_column("Providers", justify="left")
        table.add_column("SL", justify="right")
        table.add_column("TP", justify="right")
        table.add_column("Position", justify="right")
        table.add_column("Entry", justify="right")
        table.add_column("P&L%", justify="right")
        table.add_column("Trailing", justify="right")
        table.add_column("Notes", justify="left")
        table.add_column("Action Rec.", justify="left")
        table.add_column("Action Taken", justify="left")

        for coin_id, coin_config in self.config.tracked_coins.items():
            if coin_config.disabled:
                # Show disabled entries too for clarity
                table.add_row(
                    f"{coin_config.name} ({coin_config.symbol.upper()})",  # Coin
                    "—",  # Price
                    f"${coin_config.threshold:,.2f}",  # Threshold
                    "[blue]Disabled",  # Status
                    "—",  # Exchange
                    "—",  # Last Checked
                    "—",  # Signal
                    "—",  # Confidence
                    "—",  # Exp. Slip
                    "—",  # Agreement
                    "—",  # Providers
                    "—",  # SL
                    "—",  # TP
                    "—",  # Position
                    "—",  # Entry
                    "—",  # P&L%
                    "—",  # Trailing
                    "—",  # Notes
                    "—",  # Action Rec.
                    "None",  # Action Taken
                )
                continue

            price_data = aggregated.get(coin_id)
            if not isinstance(price_data, dict):
                table.add_row(
                    f"{coin_config.name} ({coin_config.symbol.upper()})",  # Coin
                    "N/A",  # Price
                    f"${coin_config.threshold:,.2f}",  # Threshold
                    "[yellow]Error",  # Status
                    "—",  # Exchange
                    datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),  # Last Checked
                    "threshold_check",  # Signal
                    "—",  # Confidence
                    "—",  # Exp. Slip
                    "—",  # Agreement
                    "—",  # Providers
                    "—",  # SL
                    "—",  # TP
                    "—",  # Position
                    "—",  # Entry
                    "—",  # P&L%
                    "—",  # Notes
                    "Hold",  # Action Rec.
                    "None",  # Action Taken
                )
                continue

            current_price = price_data.get('price')
            if current_price is None:
                table.add_row(
                    f"{coin_config.name} ({coin_config.symbol.upper()})",  # Coin
                    "N/A",  # Price
                    f"${coin_config.threshold:,.2f}",  # Threshold
                    "[yellow]Error",  # Status
                    "—",  # Exchange
                    datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),  # Last Checked
                    "threshold_check",  # Signal
                    "—",  # Confidence
                    "—",  # Exp. Slip
                    "—",  # Agreement
                    "—",  # Providers
                    "—",  # SL
                    "—",  # TP
                    "—",  # Position
                    "—",  # Entry
                    "—",  # P&L%
                    "—",  # Notes
                    "Hold",  # Action Rec.
                    "None",  # Action Taken
                )
                continue

            # Determine status and update notifier silently (no panels)
            eps = 1e-9
            is_equal = abs(current_price - coin_config.threshold) <= eps
            below = (current_price < coin_config.threshold) and not is_equal
            self.notifier.check_thresholds(
                coin_id=coin_id,
                coin_name=coin_config.name,
                current_price=current_price,
                threshold=coin_config.threshold,
                silent=True,
            )

            # Indicators: prefer preloaded daily history values, fallback to intraday rolling
            hist_last = (self.history.get(coin_id, {}) or {}).get('last', {})
            rsi_val = hist_last.get('rsi')
            ema_fast_last = hist_last.get('ema_fast')
            ema_slow_last = hist_last.get('ema_slow')
            # Fallback rolling if missing
            if rsi_val is None or ema_fast_last is None or ema_slow_last is None:
                hist = self.price_history.setdefault(coin_id, deque(maxlen=max(self.long_ma_window + 5, self.rsi_period + 5)))
                hist.append(float(current_price))
                rsi_val = rsi_val if rsi_val is not None else compute_rsi(list(hist), period=self.rsi_period)
                sma_short = compute_ma(list(hist), window=self.short_ma_window)
                sma_long = compute_ma(list(hist), window=self.long_ma_window)
                ma_short_for_conf = sma_short
                ma_long_for_conf = sma_long
            else:
                ma_short_for_conf = float(ema_fast_last)
                ma_long_for_conf = float(ema_slow_last)
            # Confidence using available MAs
            confidence = compute_confidence(float(current_price), coin_config.threshold, rsi_val, ma_short_for_conf, ma_long_for_conf)
            signal, action_rec, reason = recommend_action(float(current_price), coin_config.threshold, rsi_val, confidence, self.suggestion_threshold)

            # Estimate slippage for default size
            exp_slip_pct = estimate_slippage(self.trade_default_size_usd, spread_bps_default=self.spread_bps_default)

            # TTL check (currently last_checked is 'now' as we fetch fresh; structure in place for future provider timestamps)
            last_checked = datetime.now(timezone.utc)
            is_stale = False
            if self.ttl_seconds > 0:
                is_stale = (datetime.now(timezone.utc) - last_checked).total_seconds() > self.ttl_seconds
                if is_stale:
                    # downgrade action to Manual/Hold if stale
                    action_rec = "Manual"

            # Agreement check
            agreement_pct = None
            providers_str = ""
            if isinstance(price_data, dict):
                agreement_pct = price_data.get('agreement_diff_pct')
                providers = price_data.get('providers') or []
                providers_str = ",".join(providers)
                if agreement_pct is not None and agreement_pct > self.agreement_max_diff_pct:
                    action_rec = "Manual"  # disagreement -> require manual

            # Build notes for veto reasons
            notes_parts = []
            if is_stale:
                notes_parts.append("Stale data")
            if (agreement_pct is not None) and (agreement_pct > self.agreement_max_diff_pct):
                notes_parts.append("Provider disagreement")
            notes_str = ", ".join(notes_parts) if notes_parts else "—"
            # Regime veto: avoid buys in strong downtrend if enabled
            if self.use_regime_filter and (ema_fast_last is not None) and (ema_slow_last is not None):
                if float(ema_fast_last) < float(ema_slow_last) and action_rec == "Buy":
                    action_rec = "Hold"
                    notes_parts = [] if notes_str == "—" else notes_str.split(", ")
                    notes_parts.append("Regime veto")
                    notes_str = ", ".join(notes_parts)

            # Append indicators snapshot for visibility (RSI and EMA relation)
            try:
                ind_parts = []
                if rsi_val is not None:
                    ind_parts.append(f"RSI={float(rsi_val):.1f}")
                if (ema_fast_last is not None) and (ema_slow_last is not None):
                    ind_parts.append("EMAfast>=EMAslow" if float(ema_fast_last) >= float(ema_slow_last) else "EMAfast<EMAslow")
                if ind_parts:
                    base_parts = [] if notes_str == "—" else notes_str.split(", ")
                    base_parts.append(" ".join(ind_parts))
                    notes_str = ", ".join(base_parts)
            except Exception:
                pass
            # Append last OCO placement details if applicable for this symbol
            try:
                if self._last_oco_status and self._last_oco_status.get('symbol') == symbol_key:
                    base_parts = [] if notes_str == "—" else notes_str.split(", ")
                    tp_v = self._last_oco_status.get('tp')
                    sl_v = self._last_oco_status.get('sl')
                    base_parts.append(f"OCO tp={tp_v} sl={sl_v}")
                    notes_str = ", ".join(base_parts)
            except Exception:
                pass

            # Helper to adaptively format currency for tiny-price assets
            def _fmt_usd(v: float) -> str:
                try:
                    av = abs(float(v))
                except Exception:
                    return "—"
                t0, t1, t2 = self.ui_thresholds
                p0, p1, p2, p3 = self.ui_precisions
                if av >= t0:
                    return f"${v:,.{p0}f}"
                elif av >= t1:
                    return f"${v:,.{p1}f}"
                elif av >= t2:
                    return f"${v:,.{p2}f}"
                else:
                    return f"${v:,.{p3}f}"

            # Stop levels for display
            # If in a position, show SL/TP computed from ENTRY (matches exit logic).
            # Otherwise, show preview based on current price.
            # These are only for display; execution uses entry-based levels.
            # Prefer ATR-based preview if available
            atr_last = hist_last.get('atr')
            sl_level: Any
            tp_level: Any
            coin_atr_params = self.atr_params_map.get(coin_id, self.atr_params)
            if (coin_atr_params is not None) and (atr_last is not None) and (float(atr_last) > 0):
                sl_tmp, tp_tmp = compute_stop_levels_atr(float(current_price), float(atr_last), coin_atr_params)
                if sl_tmp is not None and tp_tmp is not None:
                    sl_level, tp_level = sl_tmp, tp_tmp
                else:
                    sl_level, tp_level = compute_stop_levels(float(current_price), self.risk)
            else:
                sl_level, tp_level = compute_stop_levels(float(current_price), self.risk)

            # Portfolio state for display
            symbol_key = coin_config.symbol.upper()
            pos = self.portfolio.get(symbol_key)
            pos_units_display = f"{pos.units:.6f}" if pos else "—"
            entry_display = (_fmt_usd(pos.entry_price) if pos else "—")
            pnl_display = (f"{pos.pnl_pct(float(current_price)):.2f}" if pos else "—")

            # Update trailing peak when in position
            if pos is not None:
                pos.update_peak(float(current_price))
                trailing_level_display = _fmt_usd(compute_trailing_stop(float(pos.peak_price), self.risk))
            else:
                trailing_level_display = "—"

            # Conditional paper execution (guarded)
            action_taken = "None"
            # Execution guardrails
            open_count = len(self.portfolio.positions)
            last_close_ok = True
            if self.per_coin_cooldown_seconds > 0:
                last_ts = self._last_close_ts.get(symbol_key)
                if last_ts is not None:
                    last_close_ok = (time.time() - last_ts) >= self.per_coin_cooldown_seconds
            guard_note: str | None = None
            can_place = (
                self.auto_trade_enable and
                self.paper_place_orders and
                (not is_stale) and
                (agreement_pct is None or agreement_pct <= self.agreement_max_diff_pct) and
                (open_count < self.max_open_positions) and
                last_close_ok
            )
            # Portfolio-level guardrails
            if can_place and max_exposure_hit:
                can_place = False
                guard_note = f"Guard: exposure limit"
            if can_place and daily_loss_hit:
                can_place = False
                guard_note = f"Guard: daily loss cap"
            # Regime filter guard: require EMAfast > EMAslow for longs (allow per-coin override)
            eff_use_regime = self.use_regime_filter
            try:
                if coin_id in self.per_coin_use_regime:
                    eff_use_regime = bool(self.per_coin_use_regime.get(coin_id))
            except Exception:
                pass
            if can_place and eff_use_regime:
                ema_fast_last = (self.history.get(coin_id, {}) or {}).get('last', {}).get('ema_fast')
                ema_slow_last = (self.history.get(coin_id, {}) or {}).get('last', {}).get('ema_slow')
                try:
                    if ema_fast_last is not None and ema_slow_last is not None and float(ema_fast_last) <= float(ema_slow_last):
                        can_place = False
                        guard_note = "Guard: regime filter"
                except Exception:
                    pass
            # MTF confirmation guard: require confirm TF trend agreement if configured
            if can_place and self.mtf_require_trend_agree and self.mtf_confirm_tf:
                try:
                    confirm = (self.history.get(coin_id, {}) or {}).get('confirm', {}) or {}
                    ef2 = confirm.get('ema_fast')
                    es2 = confirm.get('ema_slow')
                    if ef2 is not None and es2 is not None and float(ef2) <= float(es2):
                        can_place = False
                        guard_note = "Guard: MTF confirm"
                except Exception:
                    pass
            # Volatility gate: require min_atr_pct <= ATR% <= max_atr_pct (allow per-coin override)
            vg_min = self.vol_gate_min_atr_pct
            vg_max = self.vol_gate_max_atr_pct
            try:
                if coin_id in self.per_coin_vol_gate:
                    o = self.per_coin_vol_gate.get(coin_id) or {}
                    if o.get('min') is not None:
                        vg_min = float(o.get('min'))
                    if o.get('max') is not None:
                        vg_max = float(o.get('max'))
            except Exception:
                pass
            if can_place and (vg_min is not None or vg_max is not None):
                try:
                    atr_last = (self.history.get(coin_id, {}) or {}).get('last', {}).get('atr')
                    px = float(current_price) if current_price is not None else None
                    if atr_last is not None and px is not None and px > 0:
                        atr_pct = float(atr_last) / px * 100.0
                        too_low = (vg_min is not None and atr_pct < float(vg_min))
                        too_high = (vg_max is not None and atr_pct > float(vg_max))
                        if too_low or too_high:
                            can_place = False
                            guard_note = f"Guard: vol gate (ATR%={atr_pct:.2f})"
                except Exception:
                    pass
            if not can_place:
                if open_count >= self.max_open_positions:
                    guard_note = f"Guard: max {self.max_open_positions} open"
                elif not last_close_ok:
                    guard_note = f"Guard: cooldown {self.per_coin_cooldown_seconds}s"
                # include guard note into notes
                if guard_note:
                    notes_parts = [] if notes_str == "—" else notes_str.split(", ")
                    notes_parts.append(guard_note)
                    notes_str = ", ".join(notes_parts)
            try:
                if can_place:
                    # Simple buy rule for demo: recommend Buy and no existing position
                    # Use a stricter auto threshold in bearish regime if configured
                    regime_down = False
                    try:
                        if self.use_regime_filter and ema_fast_last is not None and ema_slow_last is not None:
                            regime_down = float(ema_fast_last) <= float(ema_slow_last)
                    except Exception:
                        regime_down = False
                    # Per-coin thresholds
                    auto_thr_global = self.auto_threshold_bear if regime_down else self.auto_threshold
                    auto_thr = auto_thr_global
                    try:
                        if regime_down and coin_id in self.per_coin_auto_thr_bear:
                            auto_thr = float(self.per_coin_auto_thr_bear.get(coin_id))
                        elif (coin_id in self.per_coin_auto_thr):
                            auto_thr = float(self.per_coin_auto_thr.get(coin_id)) if not regime_down else auto_thr
                    except Exception:
                        pass
                    allow_auto = (confidence >= auto_thr) or (
                        self.testing_enabled and self.testing_force_auto_on_suggest and confidence >= (
                            float(self.per_coin_suggest_thr.get(coin_id)) if coin_id in self.per_coin_suggest_thr else self.suggestion_threshold
                        )
                    )
                    if action_rec == "Buy" and pos is None and allow_auto:
                        # ATR-based position sizing
                        size_usd = self.trade_default_size_usd
                        try:
                            equity_now = 0.0
                            for _sym, _pos in self.portfolio.positions.items():
                                px = sym_to_price.get(_sym)
                                if px is not None:
                                    equity_now += float(_pos.units) * float(px)
                            budget_usd = max(0.0, equity_now * float(self.risk_budget_pct))
                            atr_last = (self.history.get(coin_id, {}) or {}).get('last', {}).get('atr')
                            coin_atr_params = self.atr_params_map.get(coin_id, self.atr_params)
                            if budget_usd > 0 and atr_last is not None and coin_atr_params is not None and float(atr_last) > 0:
                                sl_price, _tp_price = compute_stop_levels_atr(float(current_price), float(atr_last), coin_atr_params)
                                if sl_price is not None and float(current_price) > float(sl_price):
                                    risk_per_unit = float(current_price) - float(sl_price)
                                    # Protect against division by zero
                                    if risk_per_unit > 0:
                                        units = budget_usd / risk_per_unit
                                        size_usd = float(current_price) * units
                            # Apply min/max caps if configured
                            if self.max_size_usd is not None:
                                size_usd = min(size_usd, float(self.max_size_usd))
                            if self.min_size_usd is not None:
                                size_usd = max(size_usd, float(self.min_size_usd))
                            # Fallback to default if invalid
                            if not (size_usd and size_usd > 0):
                                size_usd = self.trade_default_size_usd
                        except Exception:
                            size_usd = self.trade_default_size_usd
                        # Adjust by drawdown factor (de-leveraging)
                        try:
                            size_usd *= float(self._dd_risk_factor)
                        except Exception:
                            pass
                        # Ensure we don't exceed available cash
                        if hasattr(self.portfolio, 'cash_usd'):
                            size_usd = min(size_usd, float(getattr(self.portfolio, 'cash_usd', size_usd)))
                        # Pre-trade edge check vs fees/taxes and R multiple
                        try:
                            atr_last = (self.history.get(coin_id, {}) or {}).get('last', {}).get('atr')
                            coin_atr_params = self.atr_params_map.get(coin_id, self.atr_params)
                            if (coin_atr_params is not None) and (atr_last is not None) and float(atr_last) > 0:
                                sl_tmp, tp_tmp = compute_stop_levels_atr(float(current_price), float(atr_last), coin_atr_params)
                            else:
                                sl_tmp, tp_tmp = compute_stop_levels(float(current_price), self.risk)
                            if sl_tmp is not None and tp_tmp is not None and float(current_price) > 0:
                                entry = float(current_price)
                                rr = (tp_tmp - entry) / max(1e-12, entry - sl_tmp)
                                fees_total_bps = float(self.fee_bps_default) * 2.0 + float(self.tax_bps_default) + float(self.spread_bps_default)
                                tp_edge_bps = (tp_tmp - entry) / entry * 10000.0
                                if rr < float(self.min_reward_to_risk) or tp_edge_bps <= (fees_total_bps + float(self.min_tp_edge_bps)):
                                    can_place = False
                                    guard_note = f"Guard: edge (R={rr:.2f}, tp_edge={tp_edge_bps:.0f}bps)"
                        except Exception:
                            pass
                        # Place order: live or paper
                        if self.auto_trade_mode == 'live' and self.live_executor is not None:
                            # Resolve market pair for this coin
                            try:
                                with open(self.config_path, 'r') as f:
                                    cfg_all2 = yaml.safe_load(f) or {}
                                per_coin = (cfg_all2.get('tracked_coins') or {}).get(coin_id) or {}
                                market_pair = per_coin.get('market') or f"{coin_config.symbol.upper()}/USDT"
                            except Exception:
                                market_pair = f"{coin_config.symbol.upper()}/USDT"
                            try:
                                live_order = self.live_executor.place_order(symbol=market_pair, side="buy", size_usd=size_usd, order_type="market")
                                exec_price = float(live_order.price or current_price)
                                self.portfolio.open(symbol=symbol_key, usd_size=size_usd, price=exec_price, fee_bps=self.fee_bps_default)
                                action_taken = live_order.status
                                log_event("live_order", {
                                    "symbol": symbol_key,
                                    "market": market_pair,
                                    "side": "buy",
                                    "size_usd": size_usd,
                                    "price": exec_price,
                                    "order_id": live_order.id,
                                    "confidence": confidence,
                                    "signal": signal,
                                    "agreement_pct": agreement_pct,
                                    "status": live_order.status,
                                })
                                # Attempt to arm exchange-side OCO (TP+SL) immediately (Binance only)
                                try:
                                    # Read ATR params and last ATR
                                    atr_last_live = (self.history.get(coin_id, {}) or {}).get('last', {}).get('atr')
                                    coin_atr_params_live = self.atr_params_map.get(coin_id, self.atr_params)
                                    if (coin_atr_params_live is not None) and (atr_last_live is not None) and float(atr_last_live) > 0:
                                        sl_from_entry_live, tp_from_entry_live = compute_stop_levels_atr(exec_price, float(atr_last_live), coin_atr_params_live)
                                    else:
                                        sl_from_entry_live, tp_from_entry_live = compute_stop_levels(exec_price, self.risk)
                                    # Resolve quantity from portfolio
                                    pos_now = self.portfolio.get(symbol_key)
                                    if pos_now is not None and tp_from_entry_live is not None and sl_from_entry_live is not None:
                                        # Use a small buffer for stop-limit below stop
                                        sl_limit = sl_from_entry_live * 0.999
                                        placed = self.live_executor.place_oco_sell(
                                            symbol=market_pair,
                                            quantity=float(pos_now.units),
                                            tp_price=float(tp_from_entry_live),
                                            sl_stop_price=float(sl_from_entry_live),
                                            sl_limit_price=float(sl_limit),
                                        )
                                        if placed:
                                            log_event("live_oco", {
                                                "symbol": symbol_key,
                                                "market": market_pair,
                                                "tp_price": float(tp_from_entry_live),
                                                "sl_stop_price": float(sl_from_entry_live),
                                                "sl_limit_price": float(sl_limit),
                                            })
                                except Exception:
                                    # Best-effort; exit manager will still protect positions
                                    pass
                                # Persist state
                                try:
                                    self.portfolio.save_state(self.state_path)
                                except Exception:
                                    pass
                                # Persist order in SQLite
                                try:
                                    if self.store is not None:
                                        self.store.insert_order({
                                            'symbol': symbol_key,
                                            'market': market_pair,
                                            'side': 'buy',
                                            'size_usd': size_usd,
                                            'price': exec_price,
                                            'provider': 'ccxt',
                                            'order_id': live_order.id,
                                            'status': live_order.status,
                                        })
                                except Exception:
                                    pass
                            except Exception as ex:
                                action_taken = "error"
                                log_event("live_order_error", {"symbol": symbol_key, "error": str(ex)})
                        else:
                            order = self.paper.place_order(symbol=symbol_key, side="buy", size_usd=size_usd, order_type="limit")
                            self.portfolio.open(symbol=symbol_key, usd_size=size_usd, price=float(current_price), fee_bps=self.fee_bps_default)
                            action_taken = order.status
                            log_event("paper_order", {
                                "symbol": symbol_key,
                                "side": "buy",
                                "size_usd": size_usd,
                                "price": float(current_price),
                                "confidence": confidence,
                                "signal": signal,
                                "agreement_pct": agreement_pct,
                                "status": order.status,
                            })
                            # Persist state
                            try:
                                self.portfolio.save_state(self.state_path)
                            except Exception:
                                pass
                            # Persist paper order in SQLite
                            try:
                                if self.store is not None:
                                    self.store.insert_order({
                                        'symbol': symbol_key,
                                        'market': None,
                                        'side': 'buy',
                                        'size_usd': size_usd,
                                        'price': float(current_price),
                                        'provider': 'paper',
                                        'order_id': getattr(order, 'id', None),
                                        'status': order.status,
                                    })
                            except Exception:
                                pass
                        try:
                            log_order_csv({
                                "ts": datetime.now(timezone.utc).isoformat(),
                                "symbol": symbol_key,
                                "side": "buy",
                                "size_usd": size_usd,
                                "price": float(current_price),
                                "status": order.status,
                            })
                        except Exception:
                            pass
                        # record in recent orders
                        self.recent_orders.append({
                            "time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                            "symbol": symbol_key,
                            "event": "buy",
                            "price": float(current_price),
                            "status": order.status,
                        })
                        # refresh position display
                        pos = self.portfolio.get(symbol_key)
                        pos_units_display = f"{pos.units:.6f}" if pos else "—"
                        entry_display = (_fmt_usd(pos.entry_price) if pos else "—")
                        pnl_display = (f"{pos.pnl_pct(float(current_price)):.2f}" if pos else "—")
                    # Paper exits: SL/TP
                    if self.paper_exits_enable and pos is not None:
                        # SL/TP based on entry (prefer ATR if available)
                        atr_last = (self.history.get(coin_id, {}) or {}).get('last', {}).get('atr')
                        coin_atr_params = self.atr_params_map.get(coin_id, self.atr_params)
                        if (coin_atr_params is not None) and (atr_last is not None) and (float(atr_last) > 0):
                            sl_tmp, tp_tmp = compute_stop_levels_atr(float(pos.entry_price), float(atr_last), coin_atr_params)
                            if sl_tmp is not None and tp_tmp is not None:
                                sl_from_entry, tp_from_entry = sl_tmp, tp_tmp
                            else:
                                sl_from_entry, tp_from_entry = compute_stop_levels(float(pos.entry_price), self.risk)
                        else:
                            sl_from_entry, tp_from_entry = compute_stop_levels(float(pos.entry_price), self.risk)
                        # Break-even stop: once unrealized R>=1, raise SL to entry
                        try:
                            entry_px = float(pos.entry_price)
                            risk_per_unit = max(1e-12, entry_px - float(sl_from_entry))
                            rr_unrealized = (float(current_price) - entry_px) / risk_per_unit
                            if rr_unrealized >= 1.0 and not self._breakeven_armed.get(symbol_key, False):
                                self._breakeven_armed[symbol_key] = True
                                log_event("paper_be_armed", {
                                    "symbol": symbol_key,
                                    "entry": entry_px,
                                    "old_sl": float(sl_from_entry),
                                    "new_sl": entry_px,
                                    "rr_now": rr_unrealized,
                                })
                        except Exception:
                            pass
                        # Use effective SL (max of computed SL and entry if BE armed)
                        sl_effective = max(float(sl_from_entry), float(pos.entry_price)) if self._breakeven_armed.get(symbol_key, False) else float(sl_from_entry)
                        if float(current_price) <= sl_effective:
                            closed = self.portfolio.close(symbol_key, price=float(current_price), fee_bps=self.fee_bps_default)
                            log_event("paper_exit", {
                                "symbol": symbol_key,
                                "reason": "stop_loss" if not self._breakeven_armed.get(symbol_key, False) else "break_even",
                                "entry": float(closed.get('entry_price')) if closed else None,
                                "exit_price": float(current_price),
                                "pnl_pct": (closed.get('pnl_pct') if closed else None),
                            })
                            try:
                                log_order_csv({
                                    "ts": datetime.now(timezone.utc).isoformat(),
                                    "symbol": symbol_key,
                                    "side": "sell",
                                    "price": float(current_price),
                                    "status": "closed",
                                    "reason": "stop_loss" if not self._breakeven_armed.get(symbol_key, False) else "break_even",
                                    "pnl_pct": (closed.get('pnl_pct') if closed else None),
                                })
                            except Exception:
                                pass
                            # Persist trade in SQLite
                            try:
                                if self.store is not None:
                                    self.store.insert_trade({
                                        'symbol': symbol_key,
                                        'market': None,
                                        'reason': 'stop_loss' if not self._breakeven_armed.get(symbol_key, False) else 'break_even',
                                        'entry_price': float(closed.get('entry_price')) if closed else None,
                                        'exit_price': float(current_price),
                                        'pnl_pct': (closed.get('pnl_pct') if closed else None),
                                        'order_id': None,
                                        'status': 'closed',
                                    })
                            except Exception:
                                pass
                            self.recent_orders.append({
                                "time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                                "symbol": symbol_key,
                                "event": "stop_loss",
                                "price": float(current_price),
                                "status": "closed",
                                "pnl_pct": (closed.pnl_pct(float(current_price)) if closed else None),
                            })
                            # Persist state
                            try:
                                self.portfolio.save_state(self.state_path)
                            except Exception:
                                pass
                            action_taken = "SL"
                            self._last_close_ts[symbol_key] = time.time()
                            pos = None
                            pos_units_display = "—"
                            entry_display = "—"
                            pnl_display = "—"
                        elif float(current_price) >= tp_from_entry:
                            closed = self.portfolio.close(symbol_key, price=float(current_price), fee_bps=self.fee_bps_default)
                            log_event("paper_exit", {
                                "symbol": symbol_key,
                                "reason": "take_profit",
                                "entry": float(closed.entry_price) if closed else None,
                                "exit_price": float(current_price),
                                "pnl_pct": (closed.pnl_pct(float(current_price)) if closed else None),
                            })
                            try:
                                log_order_csv({
                                    "ts": datetime.now(timezone.utc).isoformat(),
                                    "symbol": symbol_key,
                                    "side": "sell",
                                    "price": float(current_price),
                                    "status": "closed",
                                    "reason": "take_profit",
                                    "pnl_pct": (closed.pnl_pct(float(current_price)) if closed else None),
                                })
                            except Exception:
                                pass
                            # Persist trade in SQLite
                            try:
                                if self.store is not None:
                                    self.store.insert_trade({
                                        'symbol': symbol_key,
                                        'market': None,
                                        'reason': 'take_profit',
                                        'entry_price': float(closed.get('entry_price')) if closed else None,
                                        'exit_price': float(current_price),
                                        'pnl_pct': (closed.get('pnl_pct') if closed else None),
                                        'order_id': None,
                                        'status': 'closed',
                                    })
                            except Exception:
                                pass
                            self.recent_orders.append({
                                "time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                                "symbol": symbol_key,
                                "event": "take_profit",
                                "price": float(current_price),
                                "status": "closed",
                                "pnl_pct": (closed.pnl_pct(float(current_price)) if closed else None),
                            })
                            # Persist state
                            try:
                                self.portfolio.save_state(self.state_path)
                            except Exception:
                                pass
                            action_taken = "TP"
                            self._last_close_ts[symbol_key] = time.time()
                            pos = None
                            pos_units_display = "—"
                            entry_display = "—"
                            pnl_display = "—"
                        else:
                            # Trailing stop based on peak (prefer ATR if available)
                            atr_last = (self.history.get(coin_id, {}) or {}).get('last', {}).get('atr')
                            coin_atr_params = self.atr_params_map.get(coin_id, self.atr_params)
                            if (coin_atr_params is not None) and (atr_last is not None) and (float(atr_last) > 0):
                                trailing_level_base = compute_trailing_stop_atr(float(pos.peak_price), float(atr_last), coin_atr_params) or compute_trailing_stop(float(pos.peak_price), self.risk)
                            else:
                                trailing_level_base = compute_trailing_stop(float(pos.peak_price), self.risk)
                            # Adaptive trailing upgrade: tighten under conditions
                            trailing_level = float(trailing_level_base)
                            try:
                                entry_px = float(pos.entry_price)
                                risk_per_unit = max(1e-12, entry_px - (compute_stop_levels(entry_px, self.risk)[0]))
                                rr_unrealized = (float(current_price) - entry_px) / risk_per_unit if risk_per_unit > 0 else 0.0
                                atr_pct_now = (float(atr_last) / float(current_price) * 100.0) if (atr_last is not None and float(current_price) > 0) else 0.0
                                if rr_unrealized >= self.trail_up_momentum_r or atr_pct_now >= self.trail_up_atr_pct_min:
                                    # Tighten: move trailing closer to price by factor (raise the floor)
                                    # Implement by blending between trailing_level and current price
                                    tighten_to = entry_px + (float(current_price) - entry_px) * (1.0 - self.trail_up_tighten_factor)
                                    trailing_level = max(trailing_level, tighten_to)
                            except Exception:
                                pass
                            # If break-even armed, do not loosen below entry
                            if self._breakeven_armed.get(symbol_key, False):
                                trailing_level = max(float(trailing_level), float(pos.entry_price))
                            if float(current_price) <= trailing_level:
                                closed = self.portfolio.close(symbol_key, price=float(current_price), fee_bps=self.fee_bps_default)
                                log_event("paper_exit", {
                                    "symbol": symbol_key,
                                    "reason": "trailing_stop",
                                    "entry": float(closed.entry_price) if closed else None,
                                    "exit_price": float(current_price),
                                    "pnl_pct": (closed.pnl_pct(float(current_price)) if closed else None),
                                })
                                try:
                                    log_order_csv({
                                        "ts": datetime.now(timezone.utc).isoformat(),
                                        "symbol": symbol_key,
                                        "side": "sell",
                                        "price": float(current_price),
                                        "status": "closed",
                                        "reason": "trailing_stop",
                                        "pnl_pct": (closed.pnl_pct(float(current_price)) if closed else None),
                                    })
                                except Exception:
                                    pass
                                # Persist trade in SQLite
                                try:
                                    if self.store is not None:
                                        self.store.insert_trade({
                                            'symbol': symbol_key,
                                            'market': None,
                                            'reason': 'trailing_stop',
                                            'entry_price': float(closed.get('entry_price')) if closed else None,
                                            'exit_price': float(current_price),
                                            'pnl_pct': (closed.get('pnl_pct') if closed else None),
                                            'order_id': None,
                                            'status': 'closed',
                                        })
                                except Exception:
                                    pass
                                action_taken = "TRAIL"
                                self._last_close_ts[symbol_key] = time.time()
                                pos = None
                                pos_units_display = "—"
                                entry_display = "—"
                                pnl_display = "—"
                                # Persist state
                                try:
                                    self.portfolio.save_state(self.state_path)
                                except Exception:
                                    pass
                                self.recent_orders.append({
                                    "time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                                    "symbol": symbol_key,
                                    "event": "trailing_stop",
                                    "price": float(current_price),
                                    "status": "closed",
                                    "pnl_pct": (closed.pnl_pct(float(current_price)) if closed else None),
                                })
            except Exception as ex:
                log_event("paper_error", {"symbol": symbol_key, "error": str(ex)})
                action_taken = "Error"

            # If a position exists and no new action occurred this tick, show 'Open'
            if (self.portfolio.get(symbol_key) is not None) and (action_taken == "None"):
                action_taken = "Open"

            # When in a position, show SL/TP from entry for clarity
            if self.portfolio.get(symbol_key) is not None:
                entry_sl, entry_tp = compute_stop_levels(float(self.portfolio.get(symbol_key).entry_price), self.risk)
                sl_display = _fmt_usd(entry_sl)
                tp_display = _fmt_usd(entry_tp)
            else:
                sl_display = _fmt_usd(sl_level)
                tp_display = _fmt_usd(tp_level)

            status = "[yellow]Equal" if is_equal else ("[red]Below" if below else "[green]Above")

            # Emit decision logs (JSON + optional CSV) for auditability
            try:
                dec = {
                    "coin_id": coin_id,
                    "symbol": coin_config.symbol.upper(),
                    "price": float(current_price),
                    "threshold": float(coin_config.threshold),
                    "status": ("equal" if is_equal else ("below" if below else "above")),
                    "signal": signal,
                    "confidence": confidence,
                    "agreement_pct": agreement_pct,
                    "providers": providers_str,
                    "stale": is_stale,
                    "action_recommended": action_rec,
                }
                log_event("decision", dec)
                try:
                    dec_csv = {"ts": datetime.now(timezone.utc).isoformat(), **dec}
                    log_decision_csv(dec_csv)
                except Exception:
                    pass
            except Exception:
                pass
            table.add_row(
                f"{coin_config.name} ({coin_config.symbol.upper()})",
                _fmt_usd(float(current_price)),
                f"${coin_config.threshold:,.2f}",
                status,
                "Agg",
                last_checked.strftime("%Y-%m-%d %H:%M:%S"),
                signal,
                f"{confidence:.2f}",
                f"{exp_slip_pct:.2f}",
                (f"{agreement_pct:.2f}" if agreement_pct is not None else "—"),
                (providers_str or "—"),
                sl_display,
                tp_display,
                pos_units_display,
                entry_display,
                pnl_display,
                trailing_level_display,
                notes_str,
                action_rec,
                action_taken,
            )

        console.print(table)

        # Render Recent Orders (if any)
        if self.recent_orders:
            orders_table = Table(show_header=True, header_style="bold cyan")
            orders_table.add_column("Time", justify="left")
            orders_table.add_column("Symbol", justify="left")
            orders_table.add_column("Event", justify="left")
            orders_table.add_column("Price", justify="right")
            orders_table.add_column("P&L%", justify="right")
            orders_table.add_column("Status", justify="left")
            for ev in list(self.recent_orders)[-20:]:
                orders_table.add_row(
                    ev.get("time", "—"),
                    ev.get("symbol", "—"),
                    ev.get("event", "—"),
                    (f"{ev['price']:.6f}" if isinstance(ev.get('price'), (int, float)) else "—"),
                    (f"{ev['pnl_pct']:.2f}" if isinstance(ev.get('pnl_pct'), (int, float)) else "—"),
                    ev.get("status", "—"),
                )
            console.print("\n[bold]Recent Orders[/bold]")
            console.print(orders_table)

    def display_status(self):
        """Display current prices and thresholds for all coins."""
        console.print("\n[bold]📊 Crypto Price Tracker[/bold]")
        console.print("Tracking the following cryptocurrencies:\n")
        # Only fetch prices for enabled coins
        enabled_map = {cid: cfg.symbol for cid, cfg in self.config.tracked_coins.items() if not cfg.disabled}
        prices = self.fetcher.get_prices_by_symbols(enabled_map)
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Coin", width=20)
        table.add_column("Price (USD)", justify="right")
        table.add_column("Threshold", justify="right")
        table.add_column("Status", justify="center")
        table.add_column("Exchange", justify="left")
        table.add_column("Last Checked (UTC)", justify="left")
        table.add_column("Signal", justify="left")
        table.add_column("Confidence", justify="right")
        table.add_column("Action Rec.", justify="left")
        table.add_column("Action Taken", justify="left")
        for coin_id, coin_config in self.config.tracked_coins.items():
            if coin_config.disabled:
                status = "[blue]Disabled"
                table.add_row(
                    f"{coin_config.name} ({coin_config.symbol.upper()})",
                    "—",
                    f"${coin_config.threshold:,.2f}",
                    status,
                    "—",
                    "—",
                    "—",
                    "—",
                    "—",
                    "None",
                )
                continue
            price = prices.get(coin_id)
            price_str = f"${price:,.2f}" if price is not None else "N/A"
            threshold_str = f"${coin_config.threshold:,.2f}"
            if price is None:
                status = "[yellow]Error"
            else:
                eps = 1e-9
                if abs(price - coin_config.threshold) <= eps:
                    status = "[yellow]Equal"
                elif price < coin_config.threshold:
                    status = "[red]Below"
                else:
                    status = "[green]Above"
            table.add_row(
                f"{coin_config.name} ({coin_config.symbol.upper()})",
                price_str,
                threshold_str,
                status,
                ("CMC" if price is not None else "CMC"),
                datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "threshold_check",
                ("0.00" if price is not None else "—"),
                "Hold",
                "None",
            )
        console.print(table)

    def run(self):
        """Run the tracker main loop."""
        try:
            # Startup banner with active providers and thresholds
            providers_active = ",".join(sorted(list(getattr(self.aggregator, 'enabled_sources', {"cmc"}))))
            console.print("\n[green]Starting script. Press Ctrl+C to exit.[/]")
            # Provider status (Coingecko backoff)
            cg_backoff_left = 0
            try:
                import time as _t
                left = getattr(self.cg_fetcher, 'backoff_until_ts', 0.0) - _t.time()
                cg_backoff_left = int(left) if left > 0 else 0
            except Exception:
                cg_backoff_left = 0

            status_extra = ""
            if cg_backoff_left > 0:
                mins = cg_backoff_left // 60
                secs = cg_backoff_left % 60
                status_extra = f" | CG backoff: {mins}m {secs}s left"
            if self.testing_enabled:
                status_extra += " | Testing: ON"
                if self.testing_force_auto_on_suggest:
                    status_extra += " (auto@suggest)"
                if self.testing_global_price_offset_pct:
                    status_extra += f" | Price offset: {self.testing_global_price_offset_pct:+.2%}"

            console.print(
                f"[blue]Providers:[/] {providers_active} | "
                f"[blue]TTL(s):[/] {self.ttl_seconds} | "
                f"[blue]Agreement max diff(%):[/] {self.agreement_max_diff_pct} | "
                f"[blue]Confidence thresholds (suggest/auto):[/] {self.suggestion_threshold}/{self.auto_threshold} | "
                f"[blue]Max pos:[/] {self.max_open_positions} | "
                f"[blue]Cooldown:[/] {self.per_coin_cooldown_seconds}s" + status_extra
            )
            # Append strategy/risk status line for clarity
            regime_str = "ON" if self.use_regime_filter else "OFF"
            atr_str = "ON" if self.atr_params is not None else "OFF"
            console.print(f"[blue]Regime filter:[/] {regime_str} | [blue]ATR exits:[/] {atr_str}")
            # Show de-leveraging status
            try:
                dd_factor = float(getattr(self, '_dd_risk_factor', 1.0))
                peak = getattr(self, '_equity_peak_usd', None)
                dd_txt = f"dd_factor={dd_factor:.2f}"
                if peak is not None and peak > 0:
                    # We cannot easily fetch current equity here, it is printed in cycle; show peak and factor
                    console.print(f"[blue]Risk De-leveraging:[/] {dd_txt}")
            except Exception:
                pass
            # Exec/History/OCO status
            try:
                exch_name = "binance"
                with open(self.config_path, 'r') as f:
                    _cfg_all = yaml.safe_load(f) or {}
                providers_cfg = (_cfg_all.get('providers') or {})
                exch_name = str(providers_cfg.get('exchange', 'binance')).lower()
            except Exception:
                exch_name = "binance"
            exec_str = f"Live/CCXT({exch_name})" if self.auto_trade_mode == 'live' and self.live_executor else "Paper"
            hist_str = f"{getattr(self, 'history_provider', 'unknown').upper()}/{getattr(self, 'history_timeframe','?')}"
            oco_str = "Armed" if self._last_oco_status else "Not armed"
            console.print(f"[blue]Exec:[/] {exec_str} | [blue]OCO:[/] {oco_str} | [blue]History:[/] {hist_str}")

            self.check_all_prices()
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            console.print("\n[blue]Shutting down gracefully...\n[/]")
            sys.exit(0)


if __name__ == "__main__":
    # Get the directory of the current script
    script_dir = Path(__file__).parent
    config_path = script_dir.parent / "config" / "config.yaml"
    # Initialize and run the tracker
    tracker = CryptoTracker(str(config_path))
    tracker.run()
