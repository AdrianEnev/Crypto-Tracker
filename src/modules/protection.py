from __future__ import annotations


def reconcile_live_protection(tracker) -> None:
    """Wrapper to allow future extraction of logic without tracker.py edits."""
    try:
        orig = getattr(tracker, "_reconcile_live_protection_orig", None)
        if callable(orig):
            return orig()
    except Exception:
        pass
    return None


def cancel_orphan_sell_orders(tracker) -> None:
    """Wrapper to allow future extraction of logic without tracker.py edits."""
    try:
        orig = getattr(tracker, "_cancel_orphan_sell_orders_orig", None)
        if callable(orig):
            return orig()
    except Exception:
        pass
    return None
