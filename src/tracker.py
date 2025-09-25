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
from .risk import RiskParams, compute_stop_levels, compute_trailing_stop
from .fetcher_coingecko import CoingeckoFetcher
from .aggregator import PriceAggregator
from .logger import log_event, configure_file_logging
from .portfolio import Portfolio

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
        self.aggregator = PriceAggregator(self.fetcher, self.cg_fetcher, agreement_max_diff_pct=self.agreement_max_diff_pct)
        self.notifier = Notifier()
        self.global_interval_override = self._get_global_interval_override()
        # In-memory price history for indicators
        self.price_history: Dict[str, deque] = {}
        # Decision settings (safe defaults)
        self.suggestion_threshold: float = 0.5
        self.auto_threshold: float = 0.8
        self.rsi_period: int = 14
        self.short_ma_window: int = 20
        self.long_ma_window: int = 50
        # Phase 3 settings
        self.ttl_seconds: int = 15
        self.auto_trade_enable: bool = False
        self.paper_place_orders: bool = False
        self.trade_default_size_usd: float = 50.0
        self.spread_bps_default: int = 10
        # Paper executor (safe; only used if flags allow)
        self.paper = PaperExecutor()
        # Risk defaults
        self.risk = RiskParams()
        # Paper portfolio (in-memory)
        self.portfolio = Portfolio()
        # Execution guardrails
        self.max_open_positions: int = 999999
        self.per_coin_cooldown_seconds: int = 0
        self._last_close_ts: Dict[str, float] = {}
        # UI format defaults
        self.ui_thresholds = [1.0, 0.1, 0.01]
        self.ui_precisions = [2, 4, 6, 8]
        # Recent orders buffer
        self.recent_orders: deque = deque(maxlen=20)
        self._load_optional_settings()
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
            # price TTL
            price_cfg = (cfg.get('price') or {})
            self.ttl_seconds = int(price_cfg.get('ttl_seconds', self.ttl_seconds))
            # auto trade + paper flags
            at_cfg = (cfg.get('auto_trade') or {})
            self.auto_trade_enable = bool(at_cfg.get('enable', self.auto_trade_enable))
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
            self.agreement_max_diff_pct = float(providers_cfg.get('agreement_max_diff_pct', self.agreement_max_diff_pct))
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

            # Maintain price history for indicators
            hist = self.price_history.setdefault(coin_id, deque(maxlen=max(self.long_ma_window + 5, self.rsi_period + 5)))
            hist.append(float(current_price))

            # Compute indicators and confidence
            rsi_val = compute_rsi(list(hist), period=self.rsi_period)
            sma_short = compute_ma(list(hist), window=self.short_ma_window)
            sma_long = compute_ma(list(hist), window=self.long_ma_window)
            confidence = compute_confidence(float(current_price), coin_config.threshold, rsi_val, sma_short, sma_long)
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
                    if action_rec == "Buy" and pos is None and confidence >= self.auto_threshold:
                        order = self.paper.place_order(symbol=symbol_key, side="buy", size_usd=self.trade_default_size_usd, order_type="limit")
                        self.portfolio.open(symbol=symbol_key, usd_size=self.trade_default_size_usd, price=float(current_price))
                        action_taken = order.status
                        log_event("paper_order", {
                            "symbol": symbol_key,
                            "side": "buy",
                            "size_usd": self.trade_default_size_usd,
                            "price": float(current_price),
                            "confidence": confidence,
                            "signal": signal,
                            "agreement_pct": agreement_pct,
                            "status": order.status,
                        })
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
                        # SL/TP based on entry (compute from entry and risk)
                        sl_from_entry, tp_from_entry = compute_stop_levels(float(pos.entry_price), self.risk)
                        if float(current_price) <= sl_from_entry:
                            closed = self.portfolio.close(symbol_key)
                            log_event("paper_exit", {
                                "symbol": symbol_key,
                                "reason": "stop_loss",
                                "entry": float(closed.entry_price) if closed else None,
                                "exit_price": float(current_price),
                                "pnl_pct": (closed.pnl_pct(float(current_price)) if closed else None),
                            })
                            self.recent_orders.append({
                                "time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                                "symbol": symbol_key,
                                "event": "stop_loss",
                                "price": float(current_price),
                                "status": "closed",
                                "pnl_pct": (closed.pnl_pct(float(current_price)) if closed else None),
                            })
                            action_taken = "SL"
                            self._last_close_ts[symbol_key] = time.time()
                            pos = None
                            pos_units_display = "—"
                            entry_display = "—"
                            pnl_display = "—"
                        elif float(current_price) >= tp_from_entry:
                            closed = self.portfolio.close(symbol_key)
                            log_event("paper_exit", {
                                "symbol": symbol_key,
                                "reason": "take_profit",
                                "entry": float(closed.entry_price) if closed else None,
                                "exit_price": float(current_price),
                                "pnl_pct": (closed.pnl_pct(float(current_price)) if closed else None),
                            })
                            self.recent_orders.append({
                                "time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                                "symbol": symbol_key,
                                "event": "take_profit",
                                "price": float(current_price),
                                "status": "closed",
                                "pnl_pct": (closed.pnl_pct(float(current_price)) if closed else None),
                            })
                            action_taken = "TP"
                            self._last_close_ts[symbol_key] = time.time()
                            pos = None
                            pos_units_display = "—"
                            entry_display = "—"
                            pnl_display = "—"
                        else:
                            # Trailing stop based on peak
                            trailing_level = compute_trailing_stop(float(pos.peak_price), self.risk)
                            if float(current_price) <= trailing_level:
                                closed = self.portfolio.close(symbol_key)
                                log_event("paper_exit", {
                                    "symbol": symbol_key,
                                    "reason": "trailing_stop",
                                    "entry": float(closed.entry_price) if closed else None,
                                    "exit_price": float(current_price),
                                    "pnl_pct": (closed.pnl_pct(float(current_price)) if closed else None),
                                })
                                action_taken = "TRAIL"
                                self._last_close_ts[symbol_key] = time.time()
                                pos = None
                                pos_units_display = "—"
                                entry_display = "—"
                                pnl_display = "—"
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

            # Emit decision log (JSON) for auditability
            try:
                log_event("decision", {
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
                })
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
            console.print(
                f"[blue]Providers:[/] {providers_active} | "
                f"[blue]TTL(s):[/] {self.ttl_seconds} | "
                f"[blue]Agreement max diff(%):[/] {self.agreement_max_diff_pct} | "
                f"[blue]Confidence thresholds (suggest/auto):[/] {self.suggestion_threshold}/{self.auto_threshold} | "
                f"[blue]Max pos:[/] {self.max_open_positions} | "
                f"[blue]Cooldown:[/] {self.per_coin_cooldown_seconds}s" + status_extra
            )
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
