import os
import sys
import time
import yaml
import schedule
from pathlib import Path
from typing import Dict, Any
from rich.console import Console
from rich.table import Table
from rich.progress import track
from dotenv import load_dotenv
# Import local modules
from .models import CoinConfig, AppConfig
from .fetcher import PriceFetcher
from .notifier import Notifier

# Set up console
console = Console()

class CryptoTracker:
    def __init__(self, config_path: str = "../config/config.yaml"):
        """Initialize the crypto tracker with configuration."""
        # Load env vars first so overrides are available while loading config
        load_dotenv(dotenv_path=Path(__file__).parent.parent / 'config' / '.env')
        self.config = self._load_config(config_path)
        self.fetcher = PriceFetcher(
            base_url=self.config.api_base_url,
            timeout=self.config.api_timeout
        )
        self.notifier = Notifier()
        self.global_interval_override = self._get_global_interval_override()
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
            f"[blue]Using {'global ' if self.global_interval_override else ''}interval: every {interval}s (batched checks).[/]"
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
        prices = self.fetcher.get_prices_by_symbols(enabled_map)

        # Build and print a single table for this batch
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Coin", width=20)
        table.add_column("Price (USD)", justify="right")
        table.add_column("Threshold", justify="right")
        table.add_column("Status", justify="center")

        for coin_id, coin_config in self.config.tracked_coins.items():
            if coin_config.disabled:
                # Show disabled entries too for clarity
                table.add_row(
                    f"{coin_config.name} ({coin_config.symbol.upper()})",
                    "—",
                    f"${coin_config.threshold:,.2f}",
                    "[blue]Disabled",
                )
                continue

            current_price = prices.get(coin_id)
            if current_price is None:
                table.add_row(
                    f"{coin_config.name} ({coin_config.symbol.upper()})",
                    "N/A",
                    f"${coin_config.threshold:,.2f}",
                    "[yellow]Error",
                )
                # Maintain notifier state silently on errors as no price is available
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

            status = "[yellow]Equal" if is_equal else ("[red]Below" if below else "[green]Above")
            table.add_row(
                f"{coin_config.name} ({coin_config.symbol.upper()})",
                f"${current_price:,.2f}",
                f"${coin_config.threshold:,.2f}",
                status,
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
        for coin_id, coin_config in self.config.tracked_coins.items():
            if coin_config.disabled:
                status = "[blue]Disabled"
                table.add_row(
                    f"{coin_config.name} ({coin_config.symbol.upper()})",
                    "—",
                    f"${coin_config.threshold:,.2f}",
                    status,
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
            )
        console.print(table)

    def run(self):
        """Run the tracker main loop."""
        try:
            console.print("\n-----[green]🚀 Starting price tracker. Press Ctrl+C to exit.-----[/]")
            console.print("[blue]-------------------------------------------------------------[/]")
            self.check_all_prices()
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            console.print("\n---------------[blue]👋 Shutting down gracefully...---------------[/]")
            sys.exit(0)

if __name__ == "__main__":
    # Get the directory of the current script
    script_dir = Path(__file__).parent
    config_path = script_dir.parent / "config" / "config.yaml"
    # Initialize and run the tracker
    tracker = CryptoTracker(str(config_path))
    tracker.run()
