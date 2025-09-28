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

from .cancellation import OrderCancellationManager
from .manager import OrderManager, OrderManagerConfig
from .models import (
    ExchangeError,
    MaxRetriesExceededError,
    Order,
    OrderAlreadyExistsError,
    OrderNotFoundError,
    OrderRequest,
    OrderResult,
    OrderState,
    OrderType,
    OrderValidationError,
    OrderValidationResult,
    TimeInForce,
)
from .reconciliation import OrderReconciler, ReconciliationResult
from .retry import OrderRetryManager, RetryConfig
from .routing import SmartOrderRouter
from .state_machine import OrderStateMachine
from .twap import TWAPConfig, TWAPSlicer
from .vwap import VWAPConfig, VWAPSlicer

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
