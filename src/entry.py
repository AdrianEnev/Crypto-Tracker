import sys
from pathlib import Path

import yaml

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.validator import validate_config
from src.tracker.core import CryptoTracker


def main():
    # Get config path from command line arguments or use default
    if len(sys.argv) > 1:
        config_path = Path(sys.argv[1])
        if not config_path.is_absolute():
            config_path = project_root / config_path
    else:
        # Default config path
        config_path = project_root / "config" / "config.yaml"

    # Load and validate configuration before starting the app
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
    tracker.run()


if __name__ == "__main__":
    main()
