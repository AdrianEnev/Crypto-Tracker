from __future__ import annotations
import json
import sys
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict
import csv


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


def _append_csv(filename: str, headers: list[str], row: Dict[str, Any]) -> None:
    """Append a row to a CSV file under the configured log directory.
    Creates file with headers if missing. No-ops if file logging is disabled.
    """
    global _log_dir
    if _log_dir is None:
        return
    try:
        fp = _log_dir / filename
        file_exists = fp.exists()
        with fp.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=headers)
            if not file_exists:
                w.writeheader()
            # filter only known headers to avoid arbitrary columns expansion
            row_filtered = {k: row.get(k) for k in headers}
            w.writerow(row_filtered)
    except Exception:
        # Never fail on logging
        pass


def log_decision_csv(row: Dict[str, Any]) -> None:
    headers = [
        "ts",
        "coin_id",
        "symbol",
        "price",
        "threshold",
        "status",
        "signal",
        "confidence",
        "agreement_pct",
        "providers",
        "stale",
        "action_recommended",
    ]
    _append_csv("decisions.csv", headers, row)


def log_order_csv(row: Dict[str, Any]) -> None:
    headers = ["ts", "symbol", "side", "size_usd", "price", "status", "reason", "pnl_pct"]
    _append_csv("orders.csv", headers, row)
