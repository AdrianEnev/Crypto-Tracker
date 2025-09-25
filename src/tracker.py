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
from .risk import RiskParams, compute_stop_levels
from .fetcher_coingecko import CoingeckoFetcher
from .aggregator import PriceAggregator
from .logger import log_event
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
            self.trade_default_size_usd = float(trade_cfg.get('default_size_usd', 50.0))
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
        aggregated = self.aggregator.aggregate_prices(enabled_map)

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
        table.add_column("Action Rec.", justify="left")
        table.add_column("Action Taken", justify="left")

        for coin_id, coin_config in self.config.tracked_coins.items():
            if coin_config.disabled:
                # Show disabled entries too for clarity
                table.add_row(
                    f"{coin_config.name} ({coin_config.symbol.upper()})",
                    "—",
                    f"${coin_config.threshold:,.2f}",
                    "[blue]Disabled",
                    "—",
                    "—",
                    "—",
                    "—",
                    "—",
                    "—",
                    "—",
                    "—",
                    "—",
                    "—",
                    "—",
                    "—",
                    "—",
                    "None",
                )
                continue

            price_data = aggregated.get(coin_id)
            if price_data is None:
                table.add_row(
                    f"{coin_config.name} ({coin_config.symbol.upper()})",
                    "N/A",
                    f"${coin_config.threshold:,.2f}",
                    "[yellow]Error",
                    "CMC",
                    datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    "threshold_check",
                    "—",
                    "—",
                    "—",
                    "—",
                    "Hold",
                    "None",
                )
                # Maintain notifier state silently on errors as no price is available
                continue

            current_price = price_data.get('price')
            if current_price is None:
                table.add_row(
                    f"{coin_config.name} ({coin_config.symbol.upper()})",
                    "N/A",
                    f"${coin_config.threshold:,.2f}",
                    "[yellow]Error",
                    "CMC", # Assuming CMC is the default for error rows
                    datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    "threshold_check",
                    "—",
                    "—",
                    "—",
                    "—",
                    "Hold",
                    "None",
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

            # Display-only stop levels relative to current price (for preview)
            sl_level, tp_level = compute_stop_levels(float(current_price), self.risk)

            # Portfolio state for display
            symbol_key = coin_config.symbol.upper()
            pos = self.portfolio.get(symbol_key)
            pos_units_display = f"{pos.units:.6f}" if pos else "—"
            entry_display = (f"${pos.entry_price:,.4f}" if pos else "—")
            pnl_display = (f"{pos.pnl_pct(float(current_price)):.2f}" if pos else "—")

            # Conditional paper execution (guarded)
            action_taken = "None"
            can_place = (
                self.auto_trade_enable and
                self.paper_place_orders and
                (not is_stale) and
                (agreement_pct is None or agreement_pct <= self.agreement_max_diff_pct)
            )
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
                        # refresh position display
                        pos = self.portfolio.get(symbol_key)
                        pos_units_display = f"{pos.units:.6f}" if pos else "—"
                        entry_display = (f"${pos.entry_price:,.4f}" if pos else "—")
                        pnl_display = (f"{pos.pnl_pct(float(current_price)):.2f}" if pos else "—")
            except Exception as ex:
                log_event("paper_error", {"symbol": symbol_key, "error": str(ex)})
                action_taken = "Error"

            status = "[yellow]Equal" if is_equal else ("[red]Below" if below else "[green]Above")
            table.add_row(
                f"{coin_config.name} ({coin_config.symbol.upper()})",
                f"${current_price:,.2f}",
                f"${coin_config.threshold:,.2f}",
                status,
                "CMC",
                last_checked.strftime("%Y-%m-%d %H:%M:%S"),
                signal,
                f"{confidence:.2f}",
                f"{exp_slip_pct:.2f}",
                (f"{agreement_pct:.2f}" if agreement_pct is not None else "—"),
                (providers_str or "—"),
                f"${sl_level:,.4f}",
                f"${tp_level:,.4f}",
                pos_units_display,
                entry_display,
                pnl_display,
                action_rec,
                action_taken,
            )

        console.print(table)

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
            console.print("\n[green]Starting script. Press Ctrl+C to exit.\n[/]")
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
