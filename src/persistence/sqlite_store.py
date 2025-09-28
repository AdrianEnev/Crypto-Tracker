from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class SQLiteStore:
    """Minimal SQLite store for orders, trades (exits) and equity snapshots."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")
        self._create_tables()

    def _create_tables(self) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                symbol TEXT NOT NULL,
                market TEXT,
                side TEXT NOT NULL,
                size_usd REAL,
                price REAL,
                provider TEXT,
                order_id TEXT,
                status TEXT
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                symbol TEXT NOT NULL,
                market TEXT,
                reason TEXT,
                entry_price REAL,
                exit_price REAL,
                pnl_pct REAL,
                order_id TEXT,
                status TEXT
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS equity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                equity_usd REAL
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS positions_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                symbol TEXT NOT NULL,
                units REAL,
                entry_price REAL,
                mark_price REAL,
                pnl_pct REAL
            );
            """
        )
        self._conn.commit()

    def insert_order(self, data: Dict[str, Any]) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO orders (ts, symbol, market, side, size_usd, price, provider, order_id, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("ts") or datetime.now(timezone.utc).isoformat(),
                data.get("symbol"),
                data.get("market"),
                data.get("side"),
                float(data.get("size_usd") or 0.0),
                float(data.get("price") or 0.0),
                data.get("provider"),
                data.get("order_id"),
                data.get("status"),
            ),
        )
        self._conn.commit()

    def insert_trade(self, data: Dict[str, Any]) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO trades (ts, symbol, market, reason, entry_price, exit_price, pnl_pct, order_id, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("ts") or datetime.now(timezone.utc).isoformat(),
                data.get("symbol"),
                data.get("market"),
                data.get("reason"),
                float(data.get("entry_price") or 0.0),
                float(data.get("exit_price") or 0.0),
                float(data.get("pnl_pct") or 0.0),
                data.get("order_id"),
                data.get("status"),
            ),
        )
        self._conn.commit()

    def insert_equity(self, equity_usd: float) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO equity (ts, equity_usd) VALUES (?, ?)
            """,
            (datetime.now(timezone.utc).isoformat(), float(equity_usd)),
        )
        self._conn.commit()

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    def insert_position_snapshot(self, data: Dict[str, Any]) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO positions_snapshots (ts, symbol, units, entry_price, mark_price, pnl_pct)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("ts") or datetime.now(timezone.utc).isoformat(),
                data.get("symbol"),
                float(data.get("units") or 0.0),
                float(data.get("entry_price") or 0.0),
                float(data.get("mark_price") or 0.0),
                float(data.get("pnl_pct") or 0.0),
            ),
        )
        self._conn.commit()

    def get_recent_equity(self, limit: int = 30) -> list[tuple[str, float]]:
        """Return up to 'limit' most recent (ts, equity_usd) rows ordered asc by ts."""
        try:
            cur = self._conn.cursor()
            cur.execute("SELECT ts, equity_usd FROM equity ORDER BY id DESC LIMIT ?", (int(limit),))
            rows = cur.fetchall() or []
            rows.reverse()
            return [(str(ts), float(eq)) for (ts, eq) in rows]
        except Exception:
            return []
