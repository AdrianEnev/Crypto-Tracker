"""
Paper Trading Engine for Wallet Tracker

This module implements a paper trading system that simulates trading
based on the tracked wallet's transactions with configurable delays
and position sizing.
"""

import asyncio
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json
import uuid

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

console = Console()

@dataclass
class PaperTrade:
    """Represents a paper trading transaction"""
    trade_id: str
    session_id: str
    trade_type: str  # 'buy' or 'sell'
    token_symbol: str
    token_address: str
    amount_usd: float
    price_per_token: float
    quantity: float
    portfolio_balance_before: float
    portfolio_balance_after: float
    profit_loss_usd: Optional[float]
    execution_delay_ms: int
    timestamp: datetime
    created_at: datetime

@dataclass
class Position:
    """Represents a current position in a token"""
    token_address: str
    token_symbol: str
    quantity: float
    avg_price: float
    total_cost_usd: float
    current_value_usd: float
    unrealized_pnl: float

class PaperTrader:
    """Paper trading engine with configurable balance and delays"""
    
    def __init__(self, config: dict, db_path: Path, session_manager):
        self.config = config
        self.db_path = db_path
        self.session_manager = session_manager
        
        # Paper trading configuration
        self.enabled = config.get('enabled', True)
        self.initial_balance = config.get('initial_balance_usd', 1000.0)
        self.execution_delay_ms = config.get('execution_delay_ms', 3000)
        self.position_size_pct = config.get('position_size_pct', 0.1)
        self.alerts_enabled = config.get('alerts_enabled', True)
        
        # Current state
        self.current_balance = self.initial_balance
        self.positions: Dict[str, Position] = {}
        self.trade_history: List[PaperTrade] = []
        self.max_balance = self.initial_balance
        self.max_drawdown = 0.0
        
        # Logger
        self.logger = logging.getLogger(__name__)
        
        # Setup database
        self._setup_database()
        
        if not self.enabled:
            self.logger.info("Paper trading is disabled")
            return
            
        self.logger.info(f"Paper trading initialized with ${self.initial_balance:,.2f} balance")
    
    def _setup_database(self):
        """Setup paper trading database tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create paper_trades table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS paper_trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        trade_id TEXT UNIQUE NOT NULL,
                        session_id TEXT NOT NULL,
                        trade_type TEXT NOT NULL,
                        token_symbol TEXT NOT NULL,
                        token_address TEXT NOT NULL,
                        amount_usd REAL NOT NULL,
                        price_per_token REAL NOT NULL,
                        quantity REAL NOT NULL,
                        portfolio_balance_before REAL NOT NULL,
                        portfolio_balance_after REAL NOT NULL,
                        profit_loss_usd REAL,
                        execution_delay_ms INTEGER,
                        timestamp DATETIME NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.commit()
                self.logger.info("Paper trading database tables created successfully")
                
        except Exception as e:
            self.logger.error(f"Failed to setup paper trading database: {e}")
            raise
    
    async def execute_paper_trade(self, trade_data: dict) -> Optional[PaperTrade]:
        """
        Execute a paper trade based on tracked wallet transaction
        
        Args:
            trade_data: Dictionary containing trade information from tracked wallet
            
        Returns:
            PaperTrade object if successful, None if failed
        """
        if not self.enabled:
            return None
            
        try:
            # Extract trade information
            trade_type = trade_data.get('trade_type', '').lower()
            token_symbol = trade_data.get('token_symbol', 'UNKNOWN')
            token_address = trade_data.get('token_address', '')
            tracked_amount_usd = trade_data.get('amount_usd', 0.0)
            price_per_token = trade_data.get('price_per_token', 0.0)
            
            if not token_symbol or token_symbol == 'UNKNOWN':
                self.logger.warning(f"Cannot execute paper trade: Unknown token symbol")
                return None
                
            if tracked_amount_usd <= 0:
                self.logger.warning(f"Cannot execute paper trade: Invalid amount ${tracked_amount_usd}")
                return None
            
            # Calculate our position size based on config percentage
            max_position_usd = self.config.get('max_position_size_usd', 1000.0)
            our_position_size_usd = tracked_amount_usd * self.position_size_pct
            
            # Ensure we don't exceed our available balance
            our_position_size_usd = min(our_position_size_usd, self.current_balance)
            
            if our_position_size_usd <= 0:
                self.logger.warning(f"Cannot execute paper trade: Insufficient balance ${self.current_balance:,.2f}")
                return None
            
            # Simulate execution delay
            if self.execution_delay_ms > 0:
                await asyncio.sleep(self.execution_delay_ms / 1000.0)
            
            # Execute the trade
            if trade_type == 'buy':
                return await self._execute_buy(
                    token_symbol, token_address, our_position_size_usd, price_per_token
                )
            elif trade_type == 'sell':
                return await self._execute_sell(
                    token_symbol, token_address, price_per_token
                )
            else:
                self.logger.warning(f"Unknown trade type: {trade_type}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to execute paper trade: {e}")
            return None
    
    async def _execute_buy(self, token_symbol: str, token_address: str, 
                          amount_usd: float, price_per_token: float) -> PaperTrade:
        """Execute a buy order"""
        try:
            # Calculate quantity
            quantity = amount_usd / price_per_token if price_per_token > 0 else 0
            
            if quantity <= 0:
                raise ValueError(f"Invalid quantity calculated: {quantity}")
            
            # Record balance before trade
            balance_before = self.current_balance
            
            # Update balance
            self.current_balance -= amount_usd
            
            # Update or create position
            if token_address in self.positions:
                # Add to existing position
                pos = self.positions[token_address]
                total_cost = pos.total_cost_usd + amount_usd
                total_quantity = pos.quantity + quantity
                avg_price = total_cost / total_quantity if total_quantity > 0 else 0
                
                pos.quantity = total_quantity
                pos.avg_price = avg_price
                pos.total_cost_usd = total_cost
            else:
                # Create new position
                self.positions[token_address] = Position(
                    token_address=token_address,
                    token_symbol=token_symbol,
                    quantity=quantity,
                    avg_price=price_per_token,
                    total_cost_usd=amount_usd,
                    current_value_usd=amount_usd,
                    unrealized_pnl=0.0
                )
            
            # Update tracking metrics
            self.max_balance = max(self.max_balance, self.current_balance)
            current_drawdown = (self.max_balance - self.current_balance) / self.max_balance
            self.max_drawdown = max(self.max_drawdown, current_drawdown)
            
            # Create trade record
            trade = PaperTrade(
                trade_id=str(uuid.uuid4()),
                session_id=self.session_manager.current_session_id,
                trade_type='buy',
                token_symbol=token_symbol,
                token_address=token_address,
                amount_usd=amount_usd,
                price_per_token=price_per_token,
                quantity=quantity,
                portfolio_balance_before=balance_before,
                portfolio_balance_after=self.current_balance,
                profit_loss_usd=None,  # No P&L on buy
                execution_delay_ms=self.execution_delay_ms,
                timestamp=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc)
            )
            
            # Save to database
            await self._save_trade(trade)
            
            # Add to history
            self.trade_history.append(trade)
            
            # Send alert
            if self.alerts_enabled:
                await self._send_buy_alert(trade)
            
            self.logger.info(f"Paper BUY executed: {token_symbol} ${amount_usd:,.2f} @ ${price_per_token:.8f}")
            return trade
            
        except Exception as e:
            self.logger.error(f"Failed to execute buy order: {e}")
            raise
    
    async def _execute_sell(self, token_symbol: str, token_address: str, 
                           price_per_token: float) -> Optional[PaperTrade]:
        """Execute a sell order"""
        try:
            # Check if we have a position
            if token_address not in self.positions:
                self.logger.warning(f"No position found for {token_symbol} to sell")
                return None
            
            pos = self.positions[token_address]
            
            if pos.quantity <= 0:
                self.logger.warning(f"Invalid position quantity for {token_symbol}: {pos.quantity}")
                return None
            
            # Calculate sell value
            sell_value_usd = pos.quantity * price_per_token
            
            # Record balance before trade
            balance_before = self.current_balance
            
            # Update balance
            self.current_balance += sell_value_usd
            
            # Calculate profit/loss
            profit_loss_usd = sell_value_usd - pos.total_cost_usd
            
            # Update tracking metrics
            self.max_balance = max(self.max_balance, self.current_balance)
            current_drawdown = (self.max_balance - self.current_balance) / self.max_balance
            self.max_drawdown = max(self.max_drawdown, current_drawdown)
            
            # Create trade record
            trade = PaperTrade(
                trade_id=str(uuid.uuid4()),
                session_id=self.session_manager.current_session_id,
                trade_type='sell',
                token_symbol=token_symbol,
                token_address=token_address,
                amount_usd=sell_value_usd,
                price_per_token=price_per_token,
                quantity=pos.quantity,
                portfolio_balance_before=balance_before,
                portfolio_balance_after=self.current_balance,
                profit_loss_usd=profit_loss_usd,
                execution_delay_ms=self.execution_delay_ms,
                timestamp=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc)
            )
            
            # Save to database
            await self._save_trade(trade)
            
            # Add to history
            self.trade_history.append(trade)
            
            # Remove position (we sell everything)
            del self.positions[token_address]
            
            # Send alert
            if self.alerts_enabled:
                await self._send_sell_alert(trade)
            
            self.logger.info(f"Paper SELL executed: {token_symbol} ${sell_value_usd:,.2f} @ ${price_per_token:.8f} (P&L: ${profit_loss_usd:+,.2f})")
            return trade
            
        except Exception as e:
            self.logger.error(f"Failed to execute sell order: {e}")
            raise
    
    async def _save_trade(self, trade: PaperTrade):
        """Save trade to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO paper_trades (
                        trade_id, session_id, trade_type, token_symbol, token_address,
                        amount_usd, price_per_token, quantity, portfolio_balance_before,
                        portfolio_balance_after, profit_loss_usd, execution_delay_ms,
                        timestamp, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trade.trade_id, trade.session_id, trade.trade_type,
                    trade.token_symbol, trade.token_address, trade.amount_usd,
                    trade.price_per_token, trade.quantity, trade.portfolio_balance_before,
                    trade.portfolio_balance_after, trade.profit_loss_usd,
                    trade.execution_delay_ms, trade.timestamp.isoformat(),
                    trade.created_at.isoformat()
                ))
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to save trade to database: {e}")
            raise
    
    async def _send_buy_alert(self, trade: PaperTrade):
        """Send buy alert to console"""
        try:
            # Calculate position size percentage
            position_pct = (trade.amount_usd / self.config.get('max_position_size_usd', 1000.0)) * 100
            
            # Create rich alert
            alert_text = Text()
            alert_text.append("📈 BOUGHT ", style="bold green")
            alert_text.append(f"'{trade.token_symbol}'", style="bold white")
            alert_text.append(f" for ${trade.price_per_token:.8f}", style="green")
            
            details = Text()
            details.append(f"💰 Position Size: ${trade.amount_usd:,.2f} ({position_pct:.1f}% of max)\n", style="cyan")
            details.append(f"📊 Portfolio: ${trade.portfolio_balance_before:,.2f} → ${trade.portfolio_balance_after:,.2f}\n", style="blue")
            details.append(f"⏱️  Execution Delay: {trade.execution_delay_ms/1000:.1f}s", style="yellow")
            
            panel = Panel(
                details,
                title=alert_text,
                border_style="green",
                padding=(0, 1)
            )
            
            console.print(panel)
            
        except Exception as e:
            self.logger.error(f"Failed to send buy alert: {e}")
    
    async def _send_sell_alert(self, trade: PaperTrade):
        """Send sell alert to console"""
        try:
            # Create rich alert
            alert_text = Text()
            alert_text.append("📉 SOLD ", style="bold red")
            alert_text.append(f"'{trade.token_symbol}'", style="bold white")
            alert_text.append(f" for ${trade.price_per_token:.8f}", style="red")
            
            details = Text()
            details.append(f"💰 Amount Sold: ${trade.amount_usd:,.2f}\n", style="cyan")
            details.append(f"📊 Portfolio: ${trade.portfolio_balance_before:,.2f} → ${trade.portfolio_balance_after:,.2f}\n", style="blue")
            
            if trade.profit_loss_usd is not None:
                pnl_style = "green" if trade.profit_loss_usd >= 0 else "red"
                pnl_sign = "+" if trade.profit_loss_usd >= 0 else ""
                pnl_pct = (trade.profit_loss_usd / (trade.portfolio_balance_before - trade.amount_usd)) * 100 if trade.portfolio_balance_before > trade.amount_usd else 0
                details.append(f"💵 Profit: {pnl_sign}${trade.profit_loss_usd:,.2f} ({pnl_pct:+.2f}%)", style=pnl_style)
            
            panel = Panel(
                details,
                title=alert_text,
                border_style="red",
                padding=(0, 1)
            )
            
            console.print(panel)
            
        except Exception as e:
            self.logger.error(f"Failed to send sell alert: {e}")
    
    def get_portfolio_summary(self) -> dict:
        """Get current portfolio summary"""
        total_positions_value = sum(pos.current_value_usd for pos in self.positions.values())
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        
        return {
            'current_balance': self.current_balance,
            'total_value': self.current_balance + total_positions_value,
            'total_positions_value': total_positions_value,
            'total_unrealized_pnl': total_unrealized_pnl,
            'max_balance': self.max_balance,
            'max_drawdown': self.max_drawdown,
            'total_trades': len(self.trade_history),
            'profitable_trades': len([t for t in self.trade_history if t.profit_loss_usd and t.profit_loss_usd > 0]),
            'positions': {addr: {
                'symbol': pos.token_symbol,
                'quantity': pos.quantity,
                'avg_price': pos.avg_price,
                'current_value': pos.current_value_usd,
                'unrealized_pnl': pos.unrealized_pnl
            } for addr, pos in self.positions.items()}
        }
    
    def get_session_stats(self) -> dict:
        """Get current session statistics"""
        if not self.trade_history:
            return {
                'total_trades': 0,
                'profitable_trades': 0,
                'total_profit_loss': 0.0,
                'win_rate': 0.0
            }
        
        profitable_trades = len([t for t in self.trade_history if t.profit_loss_usd and t.profit_loss_usd > 0])
        total_profit_loss = sum(t.profit_loss_usd or 0 for t in self.trade_history)
        win_rate = (profitable_trades / len(self.trade_history)) * 100 if self.trade_history else 0
        
        return {
            'total_trades': len(self.trade_history),
            'profitable_trades': profitable_trades,
            'total_profit_loss': total_profit_loss,
            'win_rate': win_rate,
            'initial_balance': self.initial_balance,
            'current_balance': self.current_balance,
            'total_return_pct': ((self.current_balance - self.initial_balance) / self.initial_balance) * 100
        }
    
    def display_portfolio_summary(self):
        """Display current portfolio summary in console"""
        try:
            summary = self.get_portfolio_summary()
            
            # Create portfolio table
            table = Table(title="📊 Paper Trading Portfolio Summary")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="white")
            
            table.add_row("Current Balance", f"${summary['current_balance']:,.2f}")
            table.add_row("Total Value", f"${summary['total_value']:,.2f}")
            table.add_row("Positions Value", f"${summary['total_positions_value']:,.2f}")
            table.add_row("Unrealized P&L", f"${summary['total_unrealized_pnl']:+,.2f}")
            table.add_row("Max Balance", f"${summary['max_balance']:,.2f}")
            table.add_row("Max Drawdown", f"{summary['max_drawdown']*100:.2f}%")
            table.add_row("Total Trades", str(summary['total_trades']))
            table.add_row("Profitable Trades", str(summary['profitable_trades']))
            
            console.print(table)
            
            # Display positions if any
            if summary['positions']:
                pos_table = Table(title="💼 Current Positions")
                pos_table.add_column("Token", style="cyan")
                pos_table.add_column("Quantity", style="white")
                pos_table.add_column("Avg Price", style="green")
                pos_table.add_column("Current Value", style="blue")
                pos_table.add_column("Unrealized P&L", style="yellow")
                
                for addr, pos in summary['positions'].items():
                    pnl_style = "green" if pos['unrealized_pnl'] >= 0 else "red"
                    pos_table.add_row(
                        pos['symbol'],
                        f"{pos['quantity']:.6f}",
                        f"${pos['avg_price']:.8f}",
                        f"${pos['current_value']:,.2f}",
                        f"${pos['unrealized_pnl']:+,.2f}",
                        style=pnl_style
                    )
                
                console.print(pos_table)
            
        except Exception as e:
            self.logger.error(f"Failed to display portfolio summary: {e}")
    
    def reset_portfolio(self):
        """Reset portfolio to initial state"""
        self.current_balance = self.initial_balance
        self.positions.clear()
        self.trade_history.clear()
        self.max_balance = self.initial_balance
        self.max_drawdown = 0.0
        
        self.logger.info(f"Portfolio reset to initial balance: ${self.initial_balance:,.2f}")
