from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict


def utc_iso(dt: datetime | None = None) -> str:
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.isoformat()


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
