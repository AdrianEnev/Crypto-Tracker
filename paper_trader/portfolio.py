"""
Paper Portfolio Management

Manages simulated portfolio state including cash, positions, PnL tracking,
and risk management for paper trading.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from decimal import Decimal, ROUND_DOWN

from .broker import AccountBalance, Position, AccountInfo


@dataclass
class Trade:
    """Individual trade record."""
    
    id: str
    symbol: str
    side: str  # "buy" | "sell"
    quantity: float
    price: float
    fee: float
    timestamp: datetime
    order_id: str
    strategy_id: Optional[str] = None
    
    @property
    def value(self) -> float:
        """Trade value (quantity * price)."""
        return self.quantity * self.price
    
    @property
    def net_value(self) -> float:
        """Net trade value including fees."""
        if self.side == "buy":
            return self.value + self.fee
        else:
            return self.value - self.fee


@dataclass
class PositionSnapshot:
    """Snapshot of a position at a point in time."""
    
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    timestamp: datetime
    
    @property
    def market_value(self) -> float:
        """Current market value."""
        return self.quantity * self.current_price
    
    @property
    def total_pnl(self) -> float:
        """Total PnL (realized + unrealized)."""
        return self.realized_pnl + self.unrealized_pnl


@dataclass
class AccountSnapshot:
    """Snapshot of account state at a point in time."""
    
    timestamp: datetime
    cash: float
    total_equity: float
    unrealized_pnl: float
    realized_pnl: float
    positions: List[PositionSnapshot]
    
    @property
    def total_pnl(self) -> float:
        """Total PnL (realized + unrealized)."""
        return self.realized_pnl + self.unrealized_pnl


class PaperPortfolio:
    """Manages simulated portfolio state and trading operations."""
    
    def __init__(
        self,
        initial_cash: float = 100000.0,
        base_currency: str = "USDT",
        precision: int = 8
    ):
        self.initial_cash = initial_cash
        self.base_currency = base_currency
        self.precision = precision
        
        # Account state
        self.cash = initial_cash
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.account_history: List[AccountSnapshot] = []
        
        # PnL tracking
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        
        # Statistics
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_fees = 0.0
        
    def get_account_info(self) -> AccountInfo:
        """Get current account information."""
        balances = [AccountBalance(
            currency=self.base_currency,
            free=self.cash,
            used=0.0,  # No margin in spot trading
            total=self.cash
        )]
        
        # Add position balances
        for symbol, position in self.positions.items():
            base_asset = symbol.split('/')[0] if '/' in symbol else symbol
            quote_asset = symbol.split('/')[1] if '/' in symbol else self.base_currency
            
            # Add base asset balance
            balances.append(AccountBalance(
                currency=base_asset,
                free=position.size,
                used=0.0,
                total=position.size
            ))
        
        return AccountInfo(
            balances=balances,
            positions=list(self.positions.values()),
            total_equity=self.get_total_equity(),
            margin_used=0.0,
            margin_available=self.cash,
            timestamp=datetime.now(timezone.utc)
        )
    
    def get_balance(self, currency: str) -> Optional[AccountBalance]:
        """Get balance for a specific currency."""
        if currency == self.base_currency:
            return AccountBalance(
                currency=currency,
                free=self.cash,
                used=0.0,
                total=self.cash
            )
        
        # Check positions for base asset balances
        for symbol, position in self.positions.items():
            base_asset = symbol.split('/')[0] if '/' in symbol else symbol
            if base_asset == currency:
                return AccountBalance(
                    currency=currency,
                    free=position.size,
                    used=0.0,
                    total=position.size
                )
        
        return None
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a specific symbol."""
        return self.positions.get(symbol)
    
    def get_total_equity(self) -> float:
        """Calculate total equity (cash + position values)."""
        total_value = self.cash
        
        for position in self.positions.values():
            total_value += position.market_value
        
        return total_value
    
    def update_position_prices(self, price_updates: Dict[str, float]):
        """Update position prices and calculate unrealized PnL."""
        for symbol, price in price_updates.items():
            if symbol in self.positions:
                position = self.positions[symbol]
                position.current_price = price
                position.unrealized_pnl = self._calculate_unrealized_pnl(position)
        
        # Update total unrealized PnL
        self.unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
    
    def execute_trade(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        fee: float,
        order_id: str,
        strategy_id: Optional[str] = None
    ) -> bool:
        """Execute a trade and update portfolio state."""
        
        # Create trade record
        trade = Trade(
            id=str(uuid.uuid4()),
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            fee=fee,
            timestamp=datetime.now(timezone.utc),
            order_id=order_id,
            strategy_id=strategy_id
        )
        
        # Validate trade
        if not self._validate_trade(trade):
            return False
        
        # Execute trade
        if side == "buy":
            success = self._execute_buy_trade(trade)
        else:
            success = self._execute_sell_trade(trade)
        
        if success:
            self.trades.append(trade)
            self.total_trades += 1
            self.total_fees += fee
            
            # Update trade statistics
            if trade.side == "sell":
                # Calculate realized PnL for sell trades
                pnl = self._calculate_realized_pnl(trade)
                self.realized_pnl += pnl
                
                if pnl > 0:
                    self.winning_trades += 1
                else:
                    self.losing_trades += 1
        
        return success
    
    def _validate_trade(self, trade: Trade) -> bool:
        """Validate trade before execution."""
        
        if trade.side == "buy":
            # Check if we have enough cash
            required_cash = trade.net_value
            if self.cash < required_cash:
                return False
        
        elif trade.side == "sell":
            # Check if we have enough position
            if trade.symbol not in self.positions:
                return False
            
            position = self.positions[trade.symbol]
            if position.size < trade.quantity:
                return False
        
        return True
    
    def _execute_buy_trade(self, trade: Trade) -> bool:
        """Execute a buy trade."""
        
        # Deduct cash
        self.cash -= trade.net_value
        
        # Update or create position
        if trade.symbol in self.positions:
            position = self.positions[trade.symbol]
            # Calculate new average price
            total_cost = (position.size * position.entry_price) + trade.value
            total_quantity = position.size + trade.quantity
            position.entry_price = total_cost / total_quantity
            position.size = total_quantity
        else:
            # Create new position
            self.positions[trade.symbol] = Position(
                symbol=trade.symbol,
                side="long",
                size=trade.quantity,
                entry_price=trade.price,
                current_price=trade.price,
                unrealized_pnl=0.0,
                realized_pnl=0.0
            )
        
        return True
    
    def _execute_sell_trade(self, trade: Trade) -> bool:
        """Execute a sell trade."""
        
        position = self.positions[trade.symbol]
        
        # Add cash
        self.cash += trade.net_value
        
        # Update position
        position.size -= trade.quantity
        
        # Remove position if fully closed
        if position.size <= 0:
            del self.positions[trade.symbol]
        
        return True
    
    def _calculate_unrealized_pnl(self, position: Position) -> float:
        """Calculate unrealized PnL for a position."""
        if position.side == "long":
            return (position.current_price - position.entry_price) * position.size
        else:
            return (position.entry_price - position.current_price) * position.size
    
    def _calculate_realized_pnl(self, trade: Trade) -> float:
        """Calculate realized PnL for a sell trade."""
        if trade.symbol not in self.positions:
            return 0.0
        
        position = self.positions[trade.symbol]
        
        if position.side == "long":
            return (trade.price - position.entry_price) * trade.quantity
        else:
            return (position.entry_price - trade.price) * trade.quantity
    
    def create_account_snapshot(self, price_updates: Dict[str, float]) -> AccountSnapshot:
        """Create a snapshot of current account state."""
        
        # Update position prices
        self.update_position_prices(price_updates)
        
        # Create position snapshots
        position_snapshots = []
        for symbol, position in self.positions.items():
            position_snapshots.append(PositionSnapshot(
                symbol=symbol,
                quantity=position.size,
                entry_price=position.entry_price,
                current_price=position.current_price,
                unrealized_pnl=position.unrealized_pnl,
                realized_pnl=position.realized_pnl,
                timestamp=datetime.now(timezone.utc)
            ))
        
        snapshot = AccountSnapshot(
            timestamp=datetime.now(timezone.utc),
            cash=self.cash,
            total_equity=self.get_total_equity(),
            unrealized_pnl=self.unrealized_pnl,
            realized_pnl=self.realized_pnl,
            positions=position_snapshots
        )
        
        self.account_history.append(snapshot)
        return snapshot
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get portfolio performance metrics."""
        
        if not self.trades:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "realized_pnl": 0.0,
                "unrealized_pnl": 0.0,
                "total_fees": 0.0,
                "net_pnl": 0.0,
                "return_pct": 0.0,
            }
        
        total_pnl = self.realized_pnl + self.unrealized_pnl
        net_pnl = total_pnl - self.total_fees
        return_pct = (net_pnl / self.initial_cash) * 100.0
        
        win_rate = 0.0
        if self.total_trades > 0:
            win_rate = (self.winning_trades / self.total_trades) * 100.0
        
        return {
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "total_fees": self.total_fees,
            "net_pnl": net_pnl,
            "return_pct": return_pct,
            "total_equity": self.get_total_equity(),
            "cash": self.cash,
        }
    
    def get_trade_history(self) -> List[Trade]:
        """Get complete trade history."""
        return self.trades.copy()
    
    def get_account_history(self) -> List[AccountSnapshot]:
        """Get account history snapshots."""
        return self.account_history.copy()
    
    def reset(self, initial_cash: Optional[float] = None):
        """Reset portfolio to initial state."""
        if initial_cash is not None:
            self.initial_cash = initial_cash
        
        self.cash = self.initial_cash
        self.positions.clear()
        self.trades.clear()
        self.account_history.clear()
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_fees = 0.0
