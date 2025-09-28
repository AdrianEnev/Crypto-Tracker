"""
Order Management System

A comprehensive order management system supporting:
- Order state machine with full lifecycle tracking
- Multiple order types (Market, Limit, TWAP, VWAP)
- Smart order routing across exchanges
- Retry logic with exponential backoff
- Order reconciliation and cancellation
- Risk management and position sizing
"""

from .models import (
    Order,
    OrderState,
    OrderType,
    OrderRequest,
    OrderResult,
    OrderValidationResult,
    OrderValidationError,
    MaxRetriesExceededError,
    ExchangeError,
    OrderNotFoundError,
    OrderAlreadyExistsError,
    TimeInForce,
)

from .state_machine import OrderStateMachine
from .manager import OrderManager, OrderManagerConfig
from .routing import SmartOrderRouter
from .retry import OrderRetryManager, RetryConfig
from .cancellation import OrderCancellationManager
from .reconciliation import OrderReconciler, ReconciliationResult
from .twap import TWAPSlicer, TWAPConfig
from .vwap import VWAPSlicer, VWAPConfig

__all__ = [
    "Order",
    "OrderState",
    "OrderType",
    "OrderRequest",
    "OrderResult",
    "OrderValidationResult",
    "OrderValidationError",
    "MaxRetriesExceededError",
    "ExchangeError",
    "OrderNotFoundError",
    "OrderAlreadyExistsError",
    "TimeInForce",
    "OrderStateMachine",
    "OrderManager",
    "OrderManagerConfig",
    "SmartOrderRouter",
    "OrderRetryManager",
    "RetryConfig",
    "OrderCancellationManager",
    "OrderReconciler",
    "ReconciliationResult",
    "TWAPSlicer",
    "TWAPConfig",
    "VWAPSlicer",
    "VWAPConfig",
]
