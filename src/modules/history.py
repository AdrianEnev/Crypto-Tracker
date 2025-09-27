from __future__ import annotations


def preload_history(tracker) -> None:
    """Wrapper to allow extraction of _preload_history without editing tracker.py now."""
    try:
        orig = getattr(tracker, "_preload_history_orig", None)
        if callable(orig):
            return orig()
    except Exception:
        pass
    return None


def refresh_history_tail(tracker) -> None:
    """Wrapper to allow extraction of _refresh_history_tail without editing tracker.py now."""
    try:
        orig = getattr(tracker, "_refresh_history_tail_orig", None)
        if callable(orig):
            return orig()
    except Exception:
        pass
    return None
