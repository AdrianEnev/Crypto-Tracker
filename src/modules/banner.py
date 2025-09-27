from __future__ import annotations
from typing import Dict
from rich.console import Console

from .equity import compute_equity, update_daily_equity_baseline

console = Console()


def render_banner(tracker) -> None:
    """Render supplemental banner lines (providers, safety, portfolio, equity)."""
    try:
        # Providers overview
        providers_active = ",".join(sorted(list(getattr(tracker.aggregator, 'enabled_sources', {"cmc"}))))
        ttl = getattr(tracker, 'ttl_seconds', 15)
        agreement = getattr(tracker, 'agreement_max_diff_pct', 0.5)
        console.print(f"Providers: {providers_active} | TTL(s): {ttl} | Agreement max diff(%): {agreement}")
    except Exception:
        pass
    # Safety/Portfolio lines are already printed by tracker.run(); equity below is additive.
    try:
        # Build a symbol->price map from last aggregator run
        enabled_map = {cid: cfg.symbol for cid, cfg in tracker.config.tracked_coins.items() if not cfg.disabled}
        aggregated = tracker.aggregator.aggregate_prices(enabled_map)
        sym_to_price: Dict[str, float] = {}
        for cid, pdata in (aggregated or {}).items():
            try:
                price = pdata.get('price') if isinstance(pdata, dict) else None
                sym = (tracker.config.tracked_coins.get(cid).symbol.upper() if cid in tracker.config.tracked_coins else None)
                if price is not None and sym:
                    sym_to_price[sym] = float(price)
            except Exception:
                continue
        eq = compute_equity(tracker, sym_to_price)
        update_daily_equity_baseline(tracker, eq)
        ds = float(tracker._daily_equity_start_usd) if getattr(tracker, '_daily_equity_start_usd', None) is not None else 0.0
        dd = 0.0
        if ds > 0:
            dd = max(0.0, (ds - eq) / ds * 100.0)
        console.print(f"[blue]Equity:[/] ${eq:,.2f} | [blue]DayStart:[/] ${ds:,.2f} | [blue]DD:[/] {dd:.2f}%")
    except Exception:
        pass

    # Queue visibility
    try:
        queue = getattr(tracker, '_stagger_queue', [])
        if queue:
            import time
            now = time.time()
            next_dequeue_ts = min(item.get('available_after', now) for item in queue)
            next_dequeue_in = max(0, next_dequeue_ts - now)
            console.print(f"[blue]Queue:[/] {len(queue)} entries | [blue]Next dequeue in:[/] {next_dequeue_in:.1f}s")
    except Exception:
        pass
