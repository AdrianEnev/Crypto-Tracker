from __future__ import annotations
import json
import sys
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict


def utc_iso(dt: datetime | None = None) -> str:
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.isoformat()

_log_dir: Path | None = None

def configure_file_logging(dir_path: str | os.PathLike | None) -> None:
    """Optionally enable file logging to a daily JSONL file under dir_path.
    If dir_path is None, file logging is disabled.
    """
    global _log_dir
    if dir_path is None:
        _log_dir = None
        return
    p = Path(dir_path)
    try:
        p.mkdir(parents=True, exist_ok=True)
        _log_dir = p
    except Exception:
        _log_dir = None
        # keep stdout only if directory invalid


def log_event(event_type: str, payload: Dict[str, Any]) -> None:
    """Emit a one-line JSON event to stdout for simple auditing.

    Example payload keys: symbol, price, decision, confidence, action,
    order_id, error, etc.
    """
    record = {
        "ts": utc_iso(),
        "type": event_type,
        **payload,
    }
    sys.stdout.write(json.dumps(record, separators=(",", ":")) + "\n")
    sys.stdout.flush()
    # Also write to daily JSONL file if configured
    if _log_dir is not None:
        try:
            day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            fp = _log_dir / f"{day}.jsonl"
            with fp.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            # ignore file logging errors to avoid breaking the app
            pass
