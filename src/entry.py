import sys
import argparse
import asyncio
from pathlib import Path

import yaml

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.validator import validate_config
from src.tracker.core import CryptoTracker
from src.meme_config_generator import MemeConfigGenerator
from src.meme_dynamic_updater import MemeCoinDynamicUpdater


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Crypto Tracker - Advanced cryptocurrency monitoring and trading system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/entry.py                           # Run with default config
  python src/entry.py config/my_config.yaml     # Run with custom config
  python src/entry.py --meme                    # Run meme mode (generates fresh config)
  python src/entry.py --meme config/base.yaml   # Run meme mode using base config for settings
        """
    )
    
    parser.add_argument(
        'config', 
        nargs='?', 
        default='config/config.yaml',
        help='Path to configuration file (default: config/config.yaml)'
    )
    
    parser.add_argument(
        '--meme', 
        action='store_true',
        help='Enable meme coin mode - generates fresh config with discovered meme coins (ignores default tracked_coins)'
    )
    
    parser.add_argument(
        '--phantom', 
        action='store_true',
        help='Enable Phantom wallet mode - trades top 3 trending memecoins from Phantom with volatile-based strategy'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser.parse_args()


async def main():
    """Main entry point for the crypto tracker."""
    args = parse_arguments()
    
    # Validate that only one mode is selected
    if args.meme and args.phantom:
        print("❌ Error: Cannot use both --meme and --phantom modes simultaneously")
        print("Please choose either --meme OR --phantom")
        sys.exit(1)
    
    # Determine config path
    if args.config:
        config_path = Path(args.config)
        if not config_path.is_absolute():
            config_path = project_root / config_path
    else:
        config_path = project_root / "config" / "config.yaml"
    
    # For meme mode, always use the base config to generate meme-specific config
    base_config_path = config_path

    # Handle meme mode
    meme_updater = None
    if args.meme:
        print("🚀 Starting in MEME COIN MODE")
        print("=" * 50)
        
        try:
            # Always generate fresh meme-specific configuration (never use default config)
            print("🔍 Generating fresh meme coin configuration...")
            meme_generator = MemeConfigGenerator(str(base_config_path))
            meme_config_path = await meme_generator.generate_meme_config()
            
            print(f"✅ Fresh meme configuration generated")
            print(f"📁 Using meme-specific config: {meme_config_path}")
            print("⚠️  Note: Using dynamically generated config, not default config")
            
            # Load and validate meme config
            with open(meme_config_path, "r") as f:
                cfg = yaml.safe_load(f) or {}
            
            errors = validate_config(cfg)
            if errors:
                print("Meme configuration validation failed:")
                for e in errors:
                    print(f"  - {e}")
                sys.exit(1)
            
            # Start tracker with meme config (not the original config)
            tracker = CryptoTracker(meme_config_path)
            
            # Initialize dynamic updater for meme mode (use base config for settings)
            meme_updater = MemeCoinDynamicUpdater(str(base_config_path), tracker)
            
            # Extract current meme coin symbols for tracking
            with open(meme_config_path, "r") as f:
                meme_cfg = yaml.safe_load(f) or {}
            current_coins = [coin.get('symbol', '') for coin in meme_cfg.get('tracked_coins', {}).values()]
            meme_updater.update_current_coins(current_coins)
            
            print(f"🔄 Dynamic updater initialized for {len(current_coins)} meme coins")
            
        except Exception as ex:
            print(f"❌ Error setting up meme mode: {ex}")
            print("🔄 Falling back to regular mode...")
            args.meme = False  # Disable meme mode for fallback
    
    # Handle Phantom mode
    phantom_updater = None
    if args.phantom:
        print("🔥 Starting in PHANTOM WALLET MODE")
        print("=" * 50)
        print("⚡ Ultra-fast volatile trading for trending memecoins")
        print("🎯 Target: Top 3 trending memecoins with dynamic expansion")
        print("⏱️  Lifecycle: Maximum 20 hours per memecoin")
        
        try:
            # Import Phantom-specific modules
            from src.phantom_config_generator import PhantomConfigGenerator
            from src.phantom_dynamic_updater import PhantomMemecoinDynamicUpdater
            
            # Generate Phantom-specific configuration
            print("🔍 Generating Phantom memecoin configuration...")
            phantom_generator = PhantomConfigGenerator(str(base_config_path))
            phantom_config_path = await phantom_generator.generate_phantom_config()
            
            print(f"✅ Phantom configuration generated")
            print(f"📁 Using Phantom-specific config: {phantom_config_path}")
            print("⚡ Configured for ultra-fast volatile trading")
            
            # Load and validate Phantom config
            with open(phantom_config_path, "r") as f:
                cfg = yaml.safe_load(f) or {}
            
            errors = validate_config(cfg)
            if errors:
                print("Phantom configuration validation failed:")
                for e in errors:
                    print(f"  - {e}")
                sys.exit(1)
            
            # Start tracker with Phantom config
            tracker = CryptoTracker(phantom_config_path)
            
            # Initialize Phantom dynamic updater
            phantom_updater = PhantomMemecoinDynamicUpdater(str(base_config_path), tracker)
            
            # Extract current memecoin symbols for tracking
            with open(phantom_config_path, "r") as f:
                phantom_cfg = yaml.safe_load(f) or {}
            current_coins = [coin.get('symbol', '') for coin in phantom_cfg.get('tracked_coins', {}).values()]
            phantom_updater.update_current_coins(current_coins)
            
            print(f"🔄 Phantom dynamic updater initialized for {len(current_coins)} memecoins")
            print("⚡ High-frequency monitoring enabled (every 10-30 seconds)")
            
        except Exception as ex:
            print(f"❌ Error setting up Phantom mode: {ex}")
            print("🔄 Falling back to regular mode...")
            args.phantom = False  # Disable Phantom mode for fallback
    
    if not args.meme and not args.phantom:
        # Regular mode - load and validate configuration
        try:
            with open(config_path, "r") as f:
                cfg = yaml.safe_load(f) or {}
            errors = validate_config(cfg)
            if errors:
                print("Configuration validation failed:")
                for e in errors:
                    print(f"  - {e}")
                sys.exit(1)
        except FileNotFoundError:
            print(f"Config not found at {config_path}")
            sys.exit(1)
        except Exception as ex:
            print(f"Could not load/validate config: {ex}")
            sys.exit(1)

        # Start tracker
        tracker = CryptoTracker(str(config_path))
    # Bind helper modules (no direct edits to tracker.py required)
    try:
        from .modules.banner import render_banner
        from .modules.equity import compute_equity, update_daily_equity_baseline

        # Attach helpers for Phase 3 equity/DD usage
        tracker.compute_equity = lambda sym_to_price: compute_equity(tracker, sym_to_price)
        tracker.update_daily_equity_baseline = lambda eq: update_daily_equity_baseline(tracker, eq)
        # Render a supplemental banner line once at startup
        try:
            render_banner(tracker)
        except Exception:
            pass
        # Schedule periodic banner render every 30s
        try:
            import schedule

            schedule.every(30).seconds.do(lambda: render_banner(tracker))
        except Exception:
            pass
    except Exception:
        # Helper modules are optional; continue even if unavailable
        pass
    # Bind exits/protection wrappers capturing originals first
    try:
        import types

        from .modules.exits import manage_live_exits
        from .modules.protection import cancel_orphan_sell_orders, reconcile_live_protection

        # Capture originals if not captured yet
        if getattr(tracker, "_manage_live_exits_orig", None) is None and hasattr(
            tracker, "_manage_live_exits"
        ):
            tracker._manage_live_exits_orig = tracker._manage_live_exits
        if getattr(tracker, "_reconcile_live_protection_orig", None) is None and hasattr(
            tracker, "_reconcile_live_protection"
        ):
            tracker._reconcile_live_protection_orig = tracker._reconcile_live_protection
        if getattr(tracker, "_cancel_orphan_sell_orders_orig", None) is None and hasattr(
            tracker, "_cancel_orphan_sell_orders"
        ):
            tracker._cancel_orphan_sell_orders_orig = tracker._cancel_orphan_sell_orders
        # Bind wrappers - exits now calls module implementation directly
        tracker._manage_live_exits = types.MethodType(manage_live_exits, tracker)
        tracker._reconcile_live_protection = types.MethodType(reconcile_live_protection, tracker)
        tracker._cancel_orphan_sell_orders = types.MethodType(cancel_orphan_sell_orders, tracker)
    except Exception:
        pass
    # Bind history wrappers capturing originals first
    try:
        import types as _types

        from .modules.history import preload_history, refresh_history_tail

        if getattr(tracker, "_preload_history_orig", None) is None and hasattr(
            tracker, "_preload_history"
        ):
            tracker._preload_history_orig = tracker._preload_history
        if getattr(tracker, "_refresh_history_tail_orig", None) is None and hasattr(
            tracker, "_refresh_history_tail"
        ):
            tracker._refresh_history_tail_orig = tracker._refresh_history_tail
        tracker._preload_history = _types.MethodType(preload_history, tracker)
        tracker._refresh_history_tail = _types.MethodType(refresh_history_tail, tracker)
    except Exception:
        pass
    # Kill-switch DD guard using equity helper (runs alongside tracker loop)
    try:
        import schedule

        # Equity snapshot every 60s into SQLite
        def _equity_snapshot_job():
            try:
                if getattr(tracker, "store", None) is None:
                    return
                # Build price map
                enabled_map = {
                    cid: cfg.symbol
                    for cid, cfg in tracker.config.tracked_coins.items()
                    if not cfg.disabled
                }
                aggregated = tracker.aggregator.aggregate_prices(enabled_map)
                sym_to_price = {}
                for cid, pdata in (aggregated or {}).items():
                    try:
                        price = pdata.get("price") if isinstance(pdata, dict) else None
                        sym = (
                            tracker.config.tracked_coins.get(cid).symbol.upper()
                            if cid in tracker.config.tracked_coins
                            else None
                        )
                        if price is not None and sym:
                            sym_to_price[sym] = float(price)
                    except Exception:
                        continue
                eq = (
                    tracker.compute_equity(sym_to_price)
                    if hasattr(tracker, "compute_equity")
                    else 0.0
                )
                tracker.store.insert_equity(eq)
            except Exception:
                pass

        schedule.every(60).seconds.do(_equity_snapshot_job)

        def _dd_guard_job():
            try:
                # Only act if kill switch configured
                ks = getattr(tracker, "kill_dd_intraday_pct", None)
                if ks is None:
                    return
                # Build symbol->price map via aggregator
                enabled_map = {
                    cid: cfg.symbol
                    for cid, cfg in tracker.config.tracked_coins.items()
                    if not cfg.disabled
                }
                aggregated = tracker.aggregator.aggregate_prices(enabled_map)
                sym_to_price = {}
                for cid, pdata in (aggregated or {}).items():
                    try:
                        price = pdata.get("price") if isinstance(pdata, dict) else None
                        sym = (
                            tracker.config.tracked_coins.get(cid).symbol.upper()
                            if cid in tracker.config.tracked_coins
                            else None
                        )
                        if price is not None and sym:
                            sym_to_price[sym] = float(price)
                    except Exception:
                        continue
                eq = (
                    tracker.compute_equity(sym_to_price)
                    if hasattr(tracker, "compute_equity")
                    else 0.0
                )
                if hasattr(tracker, "update_daily_equity_baseline"):
                    tracker.update_daily_equity_baseline(eq)
                ds = float(getattr(tracker, "_daily_equity_start_usd", 0.0) or 0.0)
                dd = 0.0
                if ds > 0:
                    dd = max(0.0, (ds - eq) / ds * 100.0)
                # Toggle kill switch based on computed equity
                if dd >= float(ks):
                    tracker.kill_switch_active = True
                    try:
                        tracker.notifier.alert(
                            "Kill Switch",
                            f"DD {dd:.2f}% >= {float(ks):.2f}% — blocking new entries",
                            style="red",
                        )
                    except Exception:
                        pass
                else:
                    # Only clear if previously active and recover below threshold by some margin
                    if getattr(tracker, "kill_switch_active", False) and dd < max(
                        0.0, float(ks) - 0.5
                    ):
                        tracker.kill_switch_active = False
                        try:
                            tracker.notifier.alert(
                                "Kill Switch",
                                f"Recovered DD {dd:.2f}%, entries allowed",
                                style="green",
                            )
                        except Exception:
                            pass
            except Exception:
                pass

        schedule.every(10).seconds.do(_dd_guard_job)

        def _position_snapshot_job():
            try:
                if (
                    getattr(tracker, "store", None) is None
                    or getattr(tracker, "portfolio", None) is None
                ):
                    return
                positions = tracker.portfolio.positions or {}
                if not positions:
                    return

                enabled_map = {
                    cid: cfg.symbol
                    for cid, cfg in tracker.config.tracked_coins.items()
                    if not cfg.disabled
                }
                aggregated = tracker.aggregator.aggregate_prices(enabled_map)
                sym_to_price = {}
                for cid, pdata in (aggregated or {}).items():
                    try:
                        price = pdata.get("price") if isinstance(pdata, dict) else None
                        sym = (
                            tracker.config.tracked_coins.get(cid).symbol.upper()
                            if cid in tracker.config.tracked_coins
                            else None
                        )
                        if price is not None and sym:
                            sym_to_price[sym] = float(price)
                    except Exception:
                        continue

                for sym, pos in positions.items():
                    mark_price = sym_to_price.get(sym, pos.entry_price)
                    pnl_pct = (mark_price / pos.entry_price - 1) * 100 if pos.entry_price > 0 else 0
                    tracker.store.insert_position_snapshot(
                        {
                            "symbol": sym,
                            "units": pos.units,
                            "entry_price": pos.entry_price,
                            "mark_price": mark_price,
                            "pnl_pct": pnl_pct,
                        }
                    )
            except Exception:
                pass

        schedule.every(5).minutes.do(_position_snapshot_job)
    except Exception:
        pass
    
    # Start the tracker and dynamic updater concurrently
    async def run_tracker_with_updater():
        """Run tracker and updater concurrently."""
        tasks = []
        
        # Start tracker in background
        tracker_task = asyncio.create_task(asyncio.to_thread(tracker.run))
        tasks.append(tracker_task)
        
        # Start dynamic updater if in meme mode
        if meme_updater:
            print("🔄 Starting meme coin dynamic updater...")
            print("📊 Insider monitoring will run concurrently with tracker")
            updater_task = asyncio.create_task(meme_updater.start_monitoring())
            tasks.append(updater_task)
        
        # Start Phantom updater if in Phantom mode
        if phantom_updater:
            print("🔥 Starting Phantom memecoin dynamic updater...")
            print("⚡ High-frequency trending monitoring will run concurrently with tracker")
            phantom_task = asyncio.create_task(phantom_updater.start_monitoring())
            tasks.append(phantom_task)
        
        # Show startup status
        if meme_updater:
            print("✅ Both tracker and insider monitoring are now running concurrently")
        elif phantom_updater:
            print("✅ Both tracker and Phantom memecoin monitoring are now running concurrently")
        else:
            print("✅ Tracker is now running")
        
        # Wait for any task to complete (usually tracker will run indefinitely)
        try:
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            
            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                    
        except KeyboardInterrupt:
            print("\n🛑 Shutdown signal received...")
            # Cancel all tasks
            for task in tasks:
                task.cancel()
            # Wait for tasks to complete cancellation
            await asyncio.gather(*tasks, return_exceptions=True)
    
    # Run the concurrent tasks
    await run_tracker_with_updater()


if __name__ == "__main__":
    asyncio.run(main())
