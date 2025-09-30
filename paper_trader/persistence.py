"""
Persistence Layer

Handles storage and retrieval of paper trading data including orders,
trades, account history, and performance metrics.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import pandas as pd

from .portfolio import Trade, AccountSnapshot, PositionSnapshot
from .broker import Order


class PaperTradingPersistence:
    """Handles persistence of paper trading data."""
    
    def __init__(self, data_directory: str = "./data/paper_runs"):
        self.data_directory = Path(data_directory)
        self.data_directory.mkdir(parents=True, exist_ok=True)
        
        # Database connection
        self.db_path = self.data_directory / "paper_trading.db"
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with required tables."""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create trades table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL NOT NULL,
                    fee REAL NOT NULL,
                    timestamp DATETIME NOT NULL,
                    order_id TEXT NOT NULL,
                    strategy_id TEXT,
                    run_id TEXT NOT NULL
                )
            """)
            
            # Create orders table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id TEXT PRIMARY KEY,
                    client_order_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    order_type TEXT NOT NULL,
                    state TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL,
                    stop_price REAL,
                    time_in_force TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    strategy_id TEXT,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    filled_at DATETIME,
                    canceled_at DATETIME,
                    run_id TEXT NOT NULL
                )
            """)
            
            # Create account snapshots table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS account_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    cash REAL NOT NULL,
                    total_equity REAL NOT NULL,
                    unrealized_pnl REAL NOT NULL,
                    realized_pnl REAL NOT NULL,
                    run_id TEXT NOT NULL
                )
            """)
            
            # Create position snapshots table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS position_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    current_price REAL NOT NULL,
                    unrealized_pnl REAL NOT NULL,
                    realized_pnl REAL NOT NULL,
                    timestamp DATETIME NOT NULL,
                    FOREIGN KEY (snapshot_id) REFERENCES account_snapshots (id)
                )
            """)
            
            # Create runs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME,
                    mode TEXT NOT NULL,
                    config TEXT NOT NULL,
                    initial_cash REAL NOT NULL,
                    final_equity REAL,
                    total_trades INTEGER DEFAULT 0,
                    total_pnl REAL DEFAULT 0.0,
                    status TEXT DEFAULT 'running'
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_run_id ON trades (run_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades (timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_run_id ON orders (run_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_account_snapshots_run_id ON account_snapshots (run_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_position_snapshots_snapshot_id ON position_snapshots (snapshot_id)")
            
            conn.commit()
    
    def create_run(self, run_id: str, config: Dict[str, Any], initial_cash: float) -> bool:
        """Create a new paper trading run."""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO runs (id, start_time, mode, config, initial_cash, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    run_id,
                    datetime.now(timezone.utc).isoformat(),
                    config.get("mode", "paper"),
                    json.dumps(config),
                    initial_cash,
                    "running"
                ))
                
                conn.commit()
                return True
        
        except sqlite3.Error as e:
            print(f"Error creating run: {e}")
            return False
    
    def update_run(self, run_id: str, **kwargs) -> bool:
        """Update run information."""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Build update query dynamically
                set_clauses = []
                values = []
                
                for key, value in kwargs.items():
                    if key in ["end_time", "final_equity", "total_trades", "total_pnl", "status"]:
                        set_clauses.append(f"{key} = ?")
                        values.append(value)
                
                if not set_clauses:
                    return False
                
                query = f"UPDATE runs SET {', '.join(set_clauses)} WHERE id = ?"
                values.append(run_id)
                
                cursor.execute(query, values)
                conn.commit()
                return True
        
        except sqlite3.Error as e:
            print(f"Error updating run: {e}")
            return False
    
    def save_trade(self, trade: Trade, run_id: str) -> bool:
        """Save a trade to the database."""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO trades (
                        id, symbol, side, quantity, price, fee, timestamp,
                        order_id, strategy_id, run_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trade.id,
                    trade.symbol,
                    trade.side,
                    trade.quantity,
                    trade.price,
                    trade.fee,
                    trade.timestamp.isoformat(),
                    trade.order_id,
                    trade.strategy_id,
                    run_id
                ))
                
                conn.commit()
                return True
        
        except sqlite3.Error as e:
            print(f"Error saving trade: {e}")
            return False
    
    def save_order(self, order: Order, run_id: str) -> bool:
        """Save an order to the database."""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO orders (
                        id, client_order_id, symbol, side, order_type, state,
                        quantity, price, stop_price, time_in_force, exchange,
                        strategy_id, created_at, updated_at, filled_at, canceled_at, run_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    order.id,
                    order.client_order_id,
                    order.symbol,
                    order.side,
                    order.order_type.value,
                    order.state.value,
                    order.quantity,
                    order.price,
                    order.stop_price,
                    order.time_in_force.value,
                    order.exchange,
                    order.strategy_id,
                    order.created_at.isoformat(),
                    order.updated_at.isoformat(),
                    order.filled_at.isoformat() if order.filled_at else None,
                    order.canceled_at.isoformat() if order.canceled_at else None,
                    run_id
                ))
                
                conn.commit()
                return True
        
        except sqlite3.Error as e:
            print(f"Error saving order: {e}")
            return False
    
    def save_account_snapshot(self, snapshot: AccountSnapshot, run_id: str) -> bool:
        """Save an account snapshot to the database."""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Insert account snapshot
                cursor.execute("""
                    INSERT INTO account_snapshots (
                        timestamp, cash, total_equity, unrealized_pnl, realized_pnl, run_id
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    snapshot.timestamp.isoformat(),
                    snapshot.cash,
                    snapshot.total_equity,
                    snapshot.unrealized_pnl,
                    snapshot.realized_pnl,
                    run_id
                ))
                
                snapshot_id = cursor.lastrowid
                
                # Insert position snapshots
                for position in snapshot.positions:
                    cursor.execute("""
                        INSERT INTO position_snapshots (
                            snapshot_id, symbol, quantity, entry_price, current_price,
                            unrealized_pnl, realized_pnl, timestamp
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        snapshot_id,
                        position.symbol,
                        position.quantity,
                        position.entry_price,
                        position.current_price,
                        position.unrealized_pnl,
                        position.realized_pnl,
                        position.timestamp.isoformat()
                    ))
                
                conn.commit()
                return True
        
        except sqlite3.Error as e:
            print(f"Error saving account snapshot: {e}")
            return False
    
    def get_trades(self, run_id: str) -> List[Trade]:
        """Get all trades for a run."""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, symbol, side, quantity, price, fee, timestamp,
                           order_id, strategy_id
                    FROM trades
                    WHERE run_id = ?
                    ORDER BY timestamp
                """, (run_id,))
                
                trades = []
                for row in cursor.fetchall():
                    trade = Trade(
                        id=row[0],
                        symbol=row[1],
                        side=row[2],
                        quantity=row[3],
                        price=row[4],
                        fee=row[5],
                        timestamp=datetime.fromisoformat(row[6]),
                        order_id=row[7],
                        strategy_id=row[8]
                    )
                    trades.append(trade)
                
                return trades
        
        except sqlite3.Error as e:
            print(f"Error getting trades: {e}")
            return []
    
    def get_orders(self, run_id: str) -> List[Order]:
        """Get all orders for a run."""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, client_order_id, symbol, side, order_type, state,
                           quantity, price, stop_price, time_in_force, exchange,
                           strategy_id, created_at, updated_at, filled_at, canceled_at
                    FROM orders
                    WHERE run_id = ?
                    ORDER BY created_at
                """, (run_id,))
                
                orders = []
                for row in cursor.fetchall():
                    # This is a simplified version - you'd need to reconstruct the full Order object
                    # For now, we'll return basic information
                    order_data = {
                        "id": row[0],
                        "client_order_id": row[1],
                        "symbol": row[2],
                        "side": row[3],
                        "order_type": row[4],
                        "state": row[5],
                        "quantity": row[6],
                        "price": row[7],
                        "stop_price": row[8],
                        "time_in_force": row[9],
                        "exchange": row[10],
                        "strategy_id": row[11],
                        "created_at": datetime.fromisoformat(row[12]),
                        "updated_at": datetime.fromisoformat(row[13]),
                        "filled_at": datetime.fromisoformat(row[14]) if row[14] else None,
                        "canceled_at": datetime.fromisoformat(row[15]) if row[15] else None,
                    }
                    orders.append(order_data)
                
                return orders
        
        except sqlite3.Error as e:
            print(f"Error getting orders: {e}")
            return []
    
    def get_account_history(self, run_id: str) -> List[AccountSnapshot]:
        """Get account history for a run."""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, timestamp, cash, total_equity, unrealized_pnl, realized_pnl
                    FROM account_snapshots
                    WHERE run_id = ?
                    ORDER BY timestamp
                """, (run_id,))
                
                snapshots = []
                for row in cursor.fetchall():
                    snapshot_id = row[0]
                    
                    # Get position snapshots
                    cursor.execute("""
                        SELECT symbol, quantity, entry_price, current_price,
                               unrealized_pnl, realized_pnl, timestamp
                        FROM position_snapshots
                        WHERE snapshot_id = ?
                    """, (snapshot_id,))
                    
                    positions = []
                    for pos_row in cursor.fetchall():
                        position = PositionSnapshot(
                            symbol=pos_row[0],
                            quantity=pos_row[1],
                            entry_price=pos_row[2],
                            current_price=pos_row[3],
                            unrealized_pnl=pos_row[4],
                            realized_pnl=pos_row[5],
                            timestamp=datetime.fromisoformat(pos_row[6])
                        )
                        positions.append(position)
                    
                    snapshot = AccountSnapshot(
                        timestamp=datetime.fromisoformat(row[1]),
                        cash=row[2],
                        total_equity=row[3],
                        unrealized_pnl=row[4],
                        realized_pnl=row[5],
                        positions=positions
                    )
                    snapshots.append(snapshot)
                
                return snapshots
        
        except sqlite3.Error as e:
            print(f"Error getting account history: {e}")
            return []
    
    def export_to_csv(self, run_id: str, output_dir: Optional[str] = None) -> Dict[str, str]:
        """Export run data to CSV files."""
        
        output_dir = Path(output_dir) if output_dir else self.data_directory / run_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        exported_files = {}
        
        try:
            # Export trades
            trades = self.get_trades(run_id)
            if trades:
                trades_df = pd.DataFrame([
                    {
                        "id": trade.id,
                        "symbol": trade.symbol,
                        "side": trade.side,
                        "quantity": trade.quantity,
                        "price": trade.price,
                        "fee": trade.fee,
                        "timestamp": trade.timestamp,
                        "order_id": trade.order_id,
                        "strategy_id": trade.strategy_id,
                    }
                    for trade in trades
                ])
                trades_file = output_dir / "trades.csv"
                trades_df.to_csv(trades_file, index=False)
                exported_files["trades"] = str(trades_file)
            
            # Export account history
            account_history = self.get_account_history(run_id)
            if account_history:
                account_df = pd.DataFrame([
                    {
                        "timestamp": snapshot.timestamp,
                        "cash": snapshot.cash,
                        "total_equity": snapshot.total_equity,
                        "unrealized_pnl": snapshot.unrealized_pnl,
                        "realized_pnl": snapshot.realized_pnl,
                        "total_pnl": snapshot.total_pnl,
                    }
                    for snapshot in account_history
                ])
                account_file = output_dir / "account_history.csv"
                account_df.to_csv(account_file, index=False)
                exported_files["account_history"] = str(account_file)
            
            # Export orders
            orders = self.get_orders(run_id)
            if orders:
                orders_df = pd.DataFrame(orders)
                orders_file = output_dir / "orders.csv"
                orders_df.to_csv(orders_file, index=False)
                exported_files["orders"] = str(orders_file)
            
        except Exception as e:
            print(f"Error exporting to CSV: {e}")
        
        return exported_files
    
    def export_to_parquet(self, run_id: str, output_dir: Optional[str] = None) -> Dict[str, str]:
        """Export run data to Parquet files."""
        
        output_dir = Path(output_dir) if output_dir else self.data_directory / run_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        exported_files = {}
        
        try:
            # Export trades
            trades = self.get_trades(run_id)
            if trades:
                trades_df = pd.DataFrame([
                    {
                        "id": trade.id,
                        "symbol": trade.symbol,
                        "side": trade.side,
                        "quantity": trade.quantity,
                        "price": trade.price,
                        "fee": trade.fee,
                        "timestamp": trade.timestamp,
                        "order_id": trade.order_id,
                        "strategy_id": trade.strategy_id,
                    }
                    for trade in trades
                ])
                trades_file = output_dir / "trades.parquet"
                trades_df.to_parquet(trades_file, index=False)
                exported_files["trades"] = str(trades_file)
            
            # Export account history
            account_history = self.get_account_history(run_id)
            if account_history:
                account_df = pd.DataFrame([
                    {
                        "timestamp": snapshot.timestamp,
                        "cash": snapshot.cash,
                        "total_equity": snapshot.total_equity,
                        "unrealized_pnl": snapshot.unrealized_pnl,
                        "realized_pnl": snapshot.realized_pnl,
                        "total_pnl": snapshot.total_pnl,
                    }
                    for snapshot in account_history
                ])
                account_file = output_dir / "account_history.parquet"
                account_df.to_parquet(account_file, index=False)
                exported_files["account_history"] = str(account_file)
            
        except Exception as e:
            print(f"Error exporting to Parquet: {e}")
        
        return exported_files
    
    def get_run_summary(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get summary information for a run."""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, start_time, end_time, mode, config, initial_cash,
                           final_equity, total_trades, total_pnl, status
                    FROM runs
                    WHERE id = ?
                """, (run_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                return {
                    "id": row[0],
                    "start_time": row[1],
                    "end_time": row[2],
                    "mode": row[3],
                    "config": json.loads(row[4]) if row[4] else {},
                    "initial_cash": row[5],
                    "final_equity": row[6],
                    "total_trades": row[7],
                    "total_pnl": row[8],
                    "status": row[9],
                }
        
        except sqlite3.Error as e:
            print(f"Error getting run summary: {e}")
            return None
    
    def list_runs(self) -> List[Dict[str, Any]]:
        """List all paper trading runs."""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, start_time, end_time, mode, initial_cash,
                           final_equity, total_trades, total_pnl, status
                    FROM runs
                    ORDER BY start_time DESC
                """)
                
                runs = []
                for row in cursor.fetchall():
                    runs.append({
                        "id": row[0],
                        "start_time": row[1],
                        "end_time": row[2],
                        "mode": row[3],
                        "initial_cash": row[4],
                        "final_equity": row[5],
                        "total_trades": row[6],
                        "total_pnl": row[7],
                        "status": row[8],
                    })
                
                return runs
        
        except sqlite3.Error as e:
            print(f"Error listing runs: {e}")
            return []
