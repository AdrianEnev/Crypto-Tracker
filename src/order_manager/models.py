"""
Enhanced Order Models

Comprehensive order models supporting advanced order management features
including state tracking, metadata, and various order types.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List
import uuid


class OrderState(Enum):
    """Order state enumeration following standard order lifecycle."""

    NEW = "NEW"
    PENDING = "PENDING"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class OrderType(Enum):
    """Supported order types."""

    MARKET = "market"
    LIMIT = "limit"
    STOP_LIMIT = "stop_limit"
    TWAP = "twap"
    VWAP = "vwap"
    ICEBERG = "iceberg"


class TimeInForce(Enum):
    """Time in force options."""

    GTC = "GTC"  # Good Till Canceled
    IOC = "IOC"  # Immediate or Cancel
    FOK = "FOK"  # Fill or Kill


@dataclass
class OrderRequest:
    """Request object for creating new orders."""

    symbol: str
    side: str  # "buy" | "sell"
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: TimeInForce = TimeInForce.GTC

    # Exchange and routing
    preferred_exchange: Optional[str] = None
    exchange: Optional[str] = None

    # Risk management
    max_slippage_bps: Optional[int] = None
    min_fill_size: Optional[float] = None

    # TWAP/VWAP specific
    twap_duration_seconds: Optional[int] = None
    twap_slice_size: Optional[float] = None
    vwap_reference_price: Optional[float] = None
    vwap_participation_rate: Optional[float] = None

    # Metadata
    strategy_id: Optional[str] = None
    client_order_id: Optional[str] = None
    tags: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Order:
    """Enhanced order model with comprehensive state tracking."""

    # Core order details (no defaults)
    id: str
    client_order_id: str
    symbol: str
    side: str  # "buy" | "sell"
    order_type: OrderType
    state: OrderState
    quantity: float
    price: Optional[float]
    stop_price: Optional[float]
    time_in_force: TimeInForce
    exchange: str

    # Fields with defaults
    # Execution details
    filled_quantity: float = 0.0
    average_fill_price: Optional[float] = None
    remaining_quantity: float = 0.0
    total_fill_cost: float = 0.0

    # Exchange and routing
    exchange_order_id: Optional[str] = None

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    filled_at: Optional[datetime] = None
    canceled_at: Optional[datetime] = None

    # Metadata
    strategy_id: Optional[str] = None
    parent_order_id: Optional[str] = None  # For sliced orders
    child_order_ids: List[str] = field(default_factory=list)

    # TWAP/VWAP specific
    twap_duration_seconds: Optional[int] = None
    twap_slice_size: Optional[float] = None
    twap_slice_count: Optional[int] = None
    twap_slice_interval: Optional[int] = None
    vwap_reference_price: Optional[float] = None
    vwap_participation_rate: Optional[float] = None

    # Risk management
    max_slippage_bps: Optional[int] = None
    min_fill_size: Optional[float] = None

    # Error handling
    retry_count: int = 0
    last_error: Optional[str] = None
    cancellation_reason: Optional[str] = None

    # Additional metadata
    tags: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize computed fields after object creation."""
        if self.remaining_quantity == 0.0:
            self.remaining_quantity = self.quantity
        if self.client_order_id is None:
            self.client_order_id = str(uuid.uuid4())

    @property
    def is_active(self) -> bool:
        """Check if order is in an active state."""
        return self.state in [OrderState.NEW, OrderState.PENDING, OrderState.PARTIALLY_FILLED]

    @property
    def is_terminal(self) -> bool:
        """Check if order is in a terminal state."""
        return self.state in [
            OrderState.FILLED,
            OrderState.CANCELED,
            OrderState.REJECTED,
            OrderState.EXPIRED,
        ]

    @property
    def fill_percentage(self) -> float:
        """Calculate fill percentage."""
        if self.quantity <= 0:
            return 0.0
        return (self.filled_quantity / self.quantity) * 100.0

    @property
    def unfilled_value_usd(self) -> float:
        """Calculate unfilled value in USD."""
        if self.price is None or self.remaining_quantity <= 0:
            return 0.0
        return self.remaining_quantity * self.price

    def update_fill(
        self, fill_quantity: float, fill_price: float, timestamp: Optional[datetime] = None
    ) -> None:
        """Update order with new fill information."""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        # Update fill quantities
        self.filled_quantity += fill_quantity
        self.remaining_quantity = max(0.0, self.quantity - self.filled_quantity)

        # Update average fill price
        if self.average_fill_price is None:
            self.average_fill_price = fill_price
        else:
            # Weighted average
            total_cost = (self.average_fill_price * (self.filled_quantity - fill_quantity)) + (
                fill_price * fill_quantity
            )
            self.average_fill_price = total_cost / self.filled_quantity

        # Update total fill cost
        self.total_fill_cost += fill_quantity * fill_price

        # Update timestamps
        self.updated_at = timestamp
        if self.filled_quantity >= self.quantity:
            self.filled_at = timestamp

        # Update state
        if self.remaining_quantity <= 0:
            self.state = OrderState.FILLED
        elif self.state == OrderState.PENDING:
            self.state = OrderState.PARTIALLY_FILLED


@dataclass
class OrderResult:
    """Result object returned from order execution."""

    order_id: str
    success: bool
    exchange_order_id: Optional[str] = None
    state: Optional[OrderState] = None
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None

    @property
    def is_successful(self) -> bool:
        """Check if order execution was successful."""
        return self.success and self.error_message is None


@dataclass
class OrderValidationResult:
    """Result of order validation."""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, error: str) -> None:
        """Add validation error."""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str) -> None:
        """Add validation warning."""
        self.warnings.append(warning)


class OrderValidationError(Exception):
    """Exception raised when order validation fails."""

    def __init__(self, validation_result: OrderValidationResult):
        self.validation_result = validation_result
        super().__init__(f"Order validation failed: {', '.join(validation_result.errors)}")


class MaxRetriesExceededError(Exception):
    """Exception raised when maximum retry attempts are exceeded."""

    pass


class ExchangeError(Exception):
    """Exception raised for exchange-specific errors."""

    def __init__(self, message: str, exchange: str, error_code: Optional[str] = None):
        self.exchange = exchange
        self.error_code = error_code
        super().__init__(message)


class OrderNotFoundError(Exception):
    """Exception raised when order is not found."""

    pass


class OrderAlreadyExistsError(Exception):
    """Exception raised when trying to create duplicate order."""

    pass
