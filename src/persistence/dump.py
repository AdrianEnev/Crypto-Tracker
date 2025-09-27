from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Optional

DEFAULT_DB = Path(__file__).resolve().parents[2] / 'logs' / 'tracker.db'


def dump_table(conn: sqlite3.Connection, table: str, limit: int) -> None:
    cur = conn.cursor()
    table = table.lower()
    if table not in {"orders", "trades", "equity"}:
        print(f"Unknown table '{table}'. Use one of: orders, trades, equity")
        return
    order_col = "id"
    try:
        cur.execute(f"SELECT * FROM {table} ORDER BY {order_col} DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        colnames = [d[0] for d in cur.description]
        print(f"\n== {table.upper()} (last {limit}) ==")
        print(" | ".join(colnames))
        for r in rows:
            print(" | ".join(str(x) if x is not None else "" for x in r))
    except Exception as ex:
        print(f"Error reading {table}: {ex}")


def main():
    ap = argparse.ArgumentParser(description="Dump recent rows from SQLite store")
    ap.add_argument("--db", type=str, default=str(DEFAULT_DB), help="Path to tracker.db")
    ap.add_argument("--last", type=int, default=20, help="How many recent rows to show")
    ap.add_argument("--table", type=str, default="orders", help="Table to dump: orders|trades|equity")
    args = ap.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"DB not found: {db_path}")
        return
    try:
        conn = sqlite3.connect(str(db_path))
        dump_table(conn, args.table, args.last)
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
