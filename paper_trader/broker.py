"""
Abstract Broker Interface

Defines the contract that both real and paper brokers must implement,
enabling seamless switching between live and simulated trading.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

from src.order_manager.models import Order, OrderRequest, OrderResult, OrderState


@dataclass
class AccountBalance:
    """Account balance information."""
    
    currency: str
    free: float
    used: float
    total: float
    
    @property
    def available(self) -> float:
        """Available balance for trading."""
        return self.free


@dataclass
class Position:
    """Position information."""
    
    symbol: str
    side: str  # "long" | "short"
    size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float = 0.0
    
    @property
    def market_value(self) -> float:
        """Current market value of the position."""
        return self.size * self.current_price


@dataclass
class AccountInfo:
    """Complete account information."""
    
    balances: List[AccountBalance]
    positions: List[Position]
    total_equity: float
    margin_used: float = 0.0
    margin_available: float = 0.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class AbstractBroker(ABC):
    """Abstract base class for all brokers (real and paper)."""
    
    def __init__(self, name: str):
        self.name = name
        self.is_connected = False
        
    @abstractmethod
    def connect(self) -> bool:
        """Connect to the broker/exchange."""
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """Disconnect from the broker/exchange."""
        pass
    
    @abstractmethod
    def place_order(self, order_request: OrderRequest) -> OrderResult:
        """Place a new order."""
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an existing order."""
        pass
    
    @abstractmethod
    def get_order_status(self, order_id: str, symbol: str) -> Optional[OrderState]:
        """Get current order status."""
        pass
    
    @abstractmethod
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get all open orders."""
        pass
    
    @abstractmethod
    def get_account_info(self) -> AccountInfo:
        """Get complete account information."""
        pass
    
    @abstractmethod
    def get_balance(self, currency: str) -> Optional[AccountBalance]:
        """Get balance for a specific currency."""
        pass
    
    @abstractmethod
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a specific symbol."""
        pass
    
    @abstractmethod
    def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current ticker information for a symbol."""
        pass
    
    @abstractmethod
    def get_orderbook(self, symbol: str, limit: int = 100) -> Optional[Dict[str, Any]]:
        """Get order book for a symbol."""
        pass
    
    @abstractmethod
    def validate_order_request(self, order_request: OrderRequest) -> bool:
        """Validate order request before execution."""
        pass
    
    @property
    @abstractmethod
    def supported_symbols(self) -> List[str]:
        """Get list of supported trading symbols."""
        pass
    
    @property
    @abstractmethod
    def is_paper_trading(self) -> bool:
        """Check if this is a paper trading broker."""
        pass


class BrokerError(Exception):
    """Base exception for broker-related errors."""
    
    def __init__(self, message: str, broker_name: str, error_code: Optional[str] = None):
        self.broker_name = broker_name
        self.error_code = error_code
        super().__init__(message)


class OrderExecutionError(BrokerError):
    """Exception raised when order execution fails."""
    pass


class InsufficientFundsError(BrokerError):
    """Exception raised when there are insufficient funds for an order."""
    pass


class InvalidOrderError(BrokerError):
    """Exception raised when an order is invalid."""
    pass


class ConnectionError(BrokerError):
    """Exception raised when broker connection fails."""
    pass
