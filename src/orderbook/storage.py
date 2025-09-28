"""
Order Book Data Storage

Manages storage and retrieval of order book snapshots and events
for historical replay and analysis.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Iterator, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import json
import gzip
import sqlite3
from dataclasses import asdict

from .models import OrderBookSnapshot, OrderBookEvent, OrderBookMetrics


class OrderBookStorage:
    """Base class for order book data storage."""

    def store_snapshot(self, snapshot: OrderBookSnapshot) -> bool:
        """Store an order book snapshot."""
        raise NotImplementedError

    def store_event(self, event: OrderBookEvent) -> bool:
        """Store an order book event."""
        raise NotImplementedError

    def get_snapshots(
        self, symbol: str, start_time: datetime, end_time: datetime
    ) -> Iterator[OrderBookSnapshot]:
        """Get snapshots within time range."""
        raise NotImplementedError

    def get_events(
        self, symbol: str, start_time: datetime, end_time: datetime
    ) -> Iterator[OrderBookEvent]:
        """Get events within time range."""
        raise NotImplementedError

    def close(self):
        """Close storage connection."""
        pass


class JSONLOrderBookStorage(OrderBookStorage):
    """JSONL-based order book storage."""

    def __init__(self, data_dir: str = "./orderbook_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

    def _get_snapshot_file(self, symbol: str, date: datetime) -> Path:
        """Get file path for snapshot storage."""
        date_str = date.strftime("%Y-%m-%d")
        safe_symbol = symbol.replace("/", "_").replace("-", "_")
        return self.data_dir / f"{safe_symbol}_snapshots_{date_str}.jsonl.gz"

    def _get_event_file(self, symbol: str, date: datetime) -> Path:
        """Get file path for event storage."""
        date_str = date.strftime("%Y-%m-%d")
        safe_symbol = symbol.replace("/", "_").replace("-", "_")
        return self.data_dir / f"{safe_symbol}_events_{date_str}.jsonl.gz"

    def store_snapshot(self, snapshot: OrderBookSnapshot) -> bool:
        """Store order book snapshot to JSONL file."""
        try:
            file_path = self._get_snapshot_file(snapshot.symbol, snapshot.timestamp)

            # Convert to dict and add metadata
            data = snapshot.to_dict()
            data["_type"] = "snapshot"

            # Append to compressed file
            with gzip.open(file_path, "at", encoding="utf-8") as f:
                f.write(json.dumps(data) + "\n")

            return True

        except Exception as e:
            print(f"Failed to store snapshot: {e}")
            return False

    def store_event(self, event: OrderBookEvent) -> bool:
        """Store order book event to JSONL file."""
        try:
            file_path = self._get_event_file(event.symbol, event.timestamp)

            # Convert to dict and add metadata
            data = event.to_dict()
            data["_type"] = "event"

            # Append to compressed file
            with gzip.open(file_path, "at", encoding="utf-8") as f:
                f.write(json.dumps(data) + "\n")

            return True

        except Exception as e:
            print(f"Failed to store event: {e}")
            return False

    def get_snapshots(
        self, symbol: str, start_time: datetime, end_time: datetime
    ) -> Iterator[OrderBookSnapshot]:
        """Get snapshots within time range."""
        current_date = start_time.date()
        end_date = end_time.date()

        while current_date <= end_date:
            file_path = self._get_snapshot_file(
                symbol, datetime.combine(current_date, datetime.min.time())
            )

            if file_path.exists():
                try:
                    with gzip.open(file_path, "rt", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue

                            data = json.loads(line)
                            if data.get("_type") != "snapshot":
                                continue

                            snapshot = OrderBookSnapshot.from_dict(data)

                            # Check time range
                            if start_time <= snapshot.timestamp <= end_time:
                                yield snapshot

                except Exception as e:
                    print(f"Error reading snapshot file {file_path}: {e}")

            current_date += timedelta(days=1)

    def get_events(
        self, symbol: str, start_time: datetime, end_time: datetime
    ) -> Iterator[OrderBookEvent]:
        """Get events within time range."""
        current_date = start_time.date()
        end_date = end_time.date()

        while current_date <= end_date:
            file_path = self._get_event_file(
                symbol, datetime.combine(current_date, datetime.min.time())
            )

            if file_path.exists():
                try:
                    with gzip.open(file_path, "rt", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue

                            data = json.loads(line)
                            if data.get("_type") != "event":
                                continue

                            event = OrderBookEvent.from_dict(data)

                            # Check time range
                            if start_time <= event.timestamp <= end_time:
                                yield event

                except Exception as e:
                    print(f"Error reading event file {file_path}: {e}")

            current_date += timedelta(days=1)


class SQLiteOrderBookStorage(OrderBookStorage):
    """SQLite-based order book storage for better performance."""

    def __init__(self, db_path: str = "./orderbook_data/orderbook.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self.connection = sqlite3.connect(self.db_path)
        self._create_tables()

    def _create_tables(self):
        """Create database tables."""
        cursor = self.connection.cursor()

        # Snapshots table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                bids_json TEXT NOT NULL,
                asks_json TEXT NOT NULL,
                last_trade_price REAL,
                last_trade_quantity REAL,
                last_trade_id TEXT,
                sequence_number INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Events table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                bids_update_json TEXT,
                asks_update_json TEXT,
                trade_price REAL,
                trade_quantity REAL,
                trade_side TEXT,
                sequence_number INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Metrics table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                total_bid_liquidity REAL,
                total_ask_liquidity REAL,
                weighted_bid_price REAL,
                weighted_ask_price REAL,
                spread REAL,
                spread_bps REAL,
                mid_price REAL,
                depth_5_levels REAL,
                depth_10_levels REAL,
                depth_20_levels REAL,
                bid_ask_ratio REAL,
                order_imbalance REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Create indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_snapshots_symbol_timestamp ON snapshots(symbol, timestamp)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_symbol_timestamp ON events(symbol, timestamp)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_metrics_symbol_timestamp ON metrics(symbol, timestamp)"
        )

        self.connection.commit()

    def store_snapshot(self, snapshot: OrderBookSnapshot) -> bool:
        """Store order book snapshot to SQLite."""
        try:
            cursor = self.connection.cursor()

            # Convert levels to JSON
            bids_json = json.dumps(
                [(level.price, level.quantity) for level in snapshot.bids.levels]
            )
            asks_json = json.dumps(
                [(level.price, level.quantity) for level in snapshot.asks.levels]
            )

            cursor.execute(
                """
                INSERT INTO snapshots (
                    symbol, timestamp, bids_json, asks_json,
                    last_trade_price, last_trade_quantity, last_trade_id, sequence_number
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    snapshot.symbol,
                    snapshot.timestamp.isoformat(),
                    bids_json,
                    asks_json,
                    snapshot.last_trade_price,
                    snapshot.last_trade_quantity,
                    snapshot.last_trade_id,
                    snapshot.sequence_number,
                ),
            )

            self.connection.commit()
            return True

        except Exception as e:
            print(f"Failed to store snapshot: {e}")
            return False

    def store_event(self, event: OrderBookEvent) -> bool:
        """Store order book event to SQLite."""
        try:
            cursor = self.connection.cursor()

            cursor.execute(
                """
                INSERT INTO events (
                    symbol, timestamp, event_type, bids_update_json, asks_update_json,
                    trade_price, trade_quantity, trade_side, sequence_number
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    event.symbol,
                    event.timestamp.isoformat(),
                    event.event_type.value,
                    json.dumps(event.bids_update),
                    json.dumps(event.asks_update),
                    event.trade_price,
                    event.trade_quantity,
                    event.trade_side,
                    event.sequence_number,
                ),
            )

            self.connection.commit()
            return True

        except Exception as e:
            print(f"Failed to store event: {e}")
            return False

    def store_metrics(self, metrics: OrderBookMetrics) -> bool:
        """Store order book metrics."""
        try:
            cursor = self.connection.cursor()

            cursor.execute(
                """
                INSERT INTO metrics (
                    symbol, timestamp, total_bid_liquidity, total_ask_liquidity,
                    weighted_bid_price, weighted_ask_price, spread, spread_bps,
                    mid_price, depth_5_levels, depth_10_levels, depth_20_levels,
                    bid_ask_ratio, order_imbalance
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    metrics.symbol,
                    metrics.timestamp.isoformat(),
                    metrics.total_bid_liquidity,
                    metrics.total_ask_liquidity,
                    metrics.weighted_bid_price,
                    metrics.weighted_ask_price,
                    metrics.spread,
                    metrics.spread_bps,
                    metrics.mid_price,
                    metrics.depth_5_levels,
                    metrics.depth_10_levels,
                    metrics.depth_20_levels,
                    metrics.bid_ask_ratio,
                    metrics.order_imbalance,
                ),
            )

            self.connection.commit()
            return True

        except Exception as e:
            print(f"Failed to store metrics: {e}")
            return False

    def get_snapshots(
        self, symbol: str, start_time: datetime, end_time: datetime
    ) -> Iterator[OrderBookSnapshot]:
        """Get snapshots within time range."""
        cursor = self.connection.cursor()

        cursor.execute(
            """
            SELECT timestamp, bids_json, asks_json, last_trade_price, 
                   last_trade_quantity, last_trade_id, sequence_number
            FROM snapshots 
            WHERE symbol = ? AND timestamp BETWEEN ? AND ?
            ORDER BY timestamp
        """,
            (symbol, start_time.isoformat(), end_time.isoformat()),
        )

        for row in cursor.fetchall():
            try:
                (
                    timestamp_str,
                    bids_json,
                    asks_json,
                    last_trade_price,
                    last_trade_quantity,
                    last_trade_id,
                    sequence_number,
                ) = row

                # Parse JSON data
                bids_data = json.loads(bids_json)
                asks_data = json.loads(asks_json)

                snapshot = OrderBookSnapshot(
                    symbol=symbol,
                    timestamp=datetime.fromisoformat(timestamp_str),
                    bids=bids_data,
                    asks=asks_data,
                    last_trade_price=last_trade_price,
                    last_trade_quantity=last_trade_quantity,
                    last_trade_id=last_trade_id,
                    sequence_number=sequence_number,
                )

                yield snapshot

            except Exception as e:
                print(f"Error parsing snapshot: {e}")
                continue

    def get_events(
        self, symbol: str, start_time: datetime, end_time: datetime
    ) -> Iterator[OrderBookEvent]:
        """Get events within time range."""
        cursor = self.connection.cursor()

        cursor.execute(
            """
            SELECT timestamp, event_type, bids_update_json, asks_update_json,
                   trade_price, trade_quantity, trade_side, sequence_number
            FROM events 
            WHERE symbol = ? AND timestamp BETWEEN ? AND ?
            ORDER BY timestamp
        """,
            (symbol, start_time.isoformat(), end_time.isoformat()),
        )

        for row in cursor.fetchall():
            try:
                (
                    timestamp_str,
                    event_type,
                    bids_json,
                    asks_json,
                    trade_price,
                    trade_quantity,
                    trade_side,
                    sequence_number,
                ) = row

                # Parse JSON data
                bids_update = json.loads(bids_json) if bids_json else []
                asks_update = json.loads(asks_json) if asks_json else []

                event = OrderBookEvent(
                    symbol=symbol,
                    timestamp=datetime.fromisoformat(timestamp_str),
                    event_type=event_type,
                    bids_update=bids_update,
                    asks_update=asks_update,
                    trade_price=trade_price,
                    trade_quantity=trade_quantity,
                    trade_side=trade_side,
                    sequence_number=sequence_number,
                )

                yield event

            except Exception as e:
                print(f"Error parsing event: {e}")
                continue

    def get_metrics(
        self, symbol: str, start_time: datetime, end_time: datetime
    ) -> Iterator[OrderBookMetrics]:
        """Get metrics within time range."""
        cursor = self.connection.cursor()

        cursor.execute(
            """
            SELECT timestamp, total_bid_liquidity, total_ask_liquidity,
                   weighted_bid_price, weighted_ask_price, spread, spread_bps,
                   mid_price, depth_5_levels, depth_10_levels, depth_20_levels,
                   bid_ask_ratio, order_imbalance
            FROM metrics 
            WHERE symbol = ? AND timestamp BETWEEN ? AND ?
            ORDER BY timestamp
        """,
            (symbol, start_time.isoformat(), end_time.isoformat()),
        )

        for row in cursor.fetchall():
            try:
                (
                    timestamp_str,
                    total_bid_liquidity,
                    total_ask_liquidity,
                    weighted_bid_price,
                    weighted_ask_price,
                    spread,
                    spread_bps,
                    mid_price,
                    depth_5_levels,
                    depth_10_levels,
                    depth_20_levels,
                    bid_ask_ratio,
                    order_imbalance,
                ) = row

                metrics = OrderBookMetrics(
                    symbol=symbol,
                    timestamp=datetime.fromisoformat(timestamp_str),
                    total_bid_liquidity=total_bid_liquidity,
                    total_ask_liquidity=total_ask_liquidity,
                    weighted_bid_price=weighted_bid_price,
                    weighted_ask_price=weighted_ask_price,
                    spread=spread,
                    spread_bps=spread_bps,
                    mid_price=mid_price,
                    depth_5_levels=depth_5_levels,
                    depth_10_levels=depth_10_levels,
                    depth_20_levels=depth_20_levels,
                    bid_ask_ratio=bid_ask_ratio,
                    order_imbalance=order_imbalance,
                )

                yield metrics

            except Exception as e:
                print(f"Error parsing metrics: {e}")
                continue

    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()

    def __del__(self):
        """Ensure connection is closed."""
        self.close()
