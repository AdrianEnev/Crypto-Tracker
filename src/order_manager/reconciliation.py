"""
Order Cancellation and Reconciliation

Handles order cancellation, reconciliation with exchange state,
and maintains consistency between local and remote order states.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .executors import BaseExecutor
from .models import Order, OrderState


@dataclass
class CancellationRequest:
    """Request to cancel an order."""

    order_id: str
    symbol: str
    reason: str = "manual"
    force: bool = False
    timeout_seconds: int = 30


@dataclass
class CancellationResult:
    """Result of order cancellation."""

    order_id: str
    success: bool
    error_message: Optional[str] = None
    cancellation_time: Optional[datetime] = None
    remaining_quantity: Optional[float] = None


@dataclass
class ReconciliationDiscrepancy:
    """Represents a discrepancy found during reconciliation."""

    order_id: str
    discrepancy_type: str
    local_value: Any
    exchange_value: Any
    severity: str = "warning"  # warning, error, critical


@dataclass
class ReconciliationResult:
    """Result of order reconciliation."""

    reconciliation_time: datetime
    total_orders_checked: int = 0
    discrepancies: List[ReconciliationDiscrepancy] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    orders_reconciled: int = 0
    orders_canceled: int = 0

    def add_discrepancy(
        self,
        order_id: str,
        discrepancy_type: str,
        local_value: Any,
        exchange_value: Any,
        severity: str = "warning",
    ) -> None:
        """Add a reconciliation discrepancy."""
        discrepancy = ReconciliationDiscrepancy(
            order_id=order_id,
            discrepancy_type=discrepancy_type,
            local_value=local_value,
            exchange_value=exchange_value,
            severity=severity,
        )
        self.discrepancies.append(discrepancy)

    def add_error(self, order_id: str, error_message: str) -> None:
        """Add a reconciliation error."""
        self.errors.append(f"Order {order_id}: {error_message}")


class OrderCancellationManager:
    """Manages order cancellation operations."""

    def __init__(self, order_manager):
        self.order_manager = order_manager
        self.logger = logging.getLogger(__name__)
        self.pending_cancellations: Dict[str, CancellationRequest] = {}

    def cancel_order(
        self, order_id: str, reason: str = "manual", force: bool = False
    ) -> CancellationResult:
        """Cancel a single order."""
        try:
            order = self.order_manager.get_order(order_id)
            if not order:
                return CancellationResult(
                    order_id=order_id, success=False, error_message="Order not found"
                )

            # Check if order can be canceled
            if not self._can_cancel_order(order, force):
                return CancellationResult(
                    order_id=order_id,
                    success=False,
                    error_message=f"Order cannot be canceled in state {order.state.value}",
                )

            # Create cancellation request
            cancellation_request = CancellationRequest(
                order_id=order_id, symbol=order.symbol, reason=reason, force=force
            )

            # Execute cancellation
            return self._execute_cancellation(order, cancellation_request)

        except Exception as e:
            self.logger.error(f"Error canceling order {order_id}: {e}")
            return CancellationResult(order_id=order_id, success=False, error_message=str(e))

    def cancel_all_orders(
        self, symbol: Optional[str] = None, reason: str = "bulk_cancel"
    ) -> List[CancellationResult]:
        """Cancel all active orders, optionally filtered by symbol."""
        results = []
        active_orders = self.order_manager.get_active_orders(symbol)

        for order in active_orders:
            result = self.cancel_order(order.id, reason)
            results.append(result)

        return results

    def cancel_orders_by_strategy(
        self, strategy_id: str, reason: str = "strategy_cancel"
    ) -> List[CancellationResult]:
        """Cancel all orders for a specific strategy."""
        results = []
        strategy_orders = self.order_manager.get_orders_by_strategy(strategy_id)

        for order in strategy_orders:
            if order.is_active:
                result = self.cancel_order(order.id, reason)
                results.append(result)

        return results

    def _can_cancel_order(self, order: Order, force: bool = False) -> bool:
        """Check if order can be canceled."""
        if force:
            return True

        return order.state in [OrderState.NEW, OrderState.PENDING, OrderState.PARTIALLY_FILLED]

    def _execute_cancellation(
        self, order: Order, request: CancellationRequest
    ) -> CancellationResult:
        """Execute order cancellation on exchange."""
        try:
            # Get executor for order's exchange
            executor = self.order_manager.get_executor(order.exchange)
            if not executor:
                return CancellationResult(
                    order_id=order.id,
                    success=False,
                    error_message=f"No executor found for exchange {order.exchange}",
                )

            # Cancel on exchange
            success = executor.cancel_order(order.id, order.symbol)

            if success:
                # Update local order state
                self.order_manager.state_machine.transition(
                    order, OrderState.CANCELED, request.reason
                )
                order.cancellation_reason = request.reason

                self.logger.info(f"Successfully canceled order {order.id}")

                return CancellationResult(
                    order_id=order.id,
                    success=True,
                    cancellation_time=datetime.now(),
                    remaining_quantity=order.remaining_quantity,
                )
            else:
                return CancellationResult(
                    order_id=order.id, success=False, error_message="Exchange cancellation failed"
                )

        except Exception as e:
            self.logger.error(f"Error executing cancellation for order {order.id}: {e}")
            return CancellationResult(order_id=order.id, success=False, error_message=str(e))


class OrderReconciler:
    """Reconciles local order state with exchange state."""

    def __init__(self, order_manager):
        self.order_manager = order_manager
        self.logger = logging.getLogger(__name__)
        self.last_reconciliation: Dict[str, datetime] = {}
        self.reconciliation_interval = timedelta(minutes=5)

    def reconcile_orders(self, force: bool = False) -> ReconciliationResult:
        """Reconcile all active orders with exchange state."""
        result = ReconciliationResult(reconciliation_time=datetime.now())

        try:
            # Get all active orders
            active_orders = self.order_manager.get_active_orders()
            result.total_orders_checked = len(active_orders)

            # Group orders by exchange for efficient reconciliation
            orders_by_exchange = self._group_orders_by_exchange(active_orders)

            for exchange, orders in orders_by_exchange.items():
                self._reconcile_exchange_orders(exchange, orders, result)

            # Handle reconciliation results
            self._handle_reconciliation_result(result)

        except Exception as e:
            self.logger.error(f"Error during reconciliation: {e}")
            result.add_error("system", str(e))

        return result

    def reconcile_order(self, order_id: str) -> ReconciliationResult:
        """Reconcile a single order."""
        result = ReconciliationResult(reconciliation_time=datetime.now())

        try:
            order = self.order_manager.get_order(order_id)
            if not order:
                result.add_error(order_id, "Order not found")
                return result

            result.total_orders_checked = 1

            # Get exchange order
            executor = self.order_manager.get_executor(order.exchange)
            if not executor:
                result.add_error(order_id, f"No executor for exchange {order.exchange}")
                return result

            exchange_order = self._fetch_exchange_order(executor, order)
            if exchange_order:
                self._reconcile_order_states(order, exchange_order, result)
            else:
                result.add_discrepancy(
                    order_id, "missing_on_exchange", order.state.value, None, "error"
                )

            self._handle_reconciliation_result(result)

        except Exception as e:
            self.logger.error(f"Error reconciling order {order_id}: {e}")
            result.add_error(order_id, str(e))

        return result

    def _group_orders_by_exchange(self, orders: List[Order]) -> Dict[str, List[Order]]:
        """Group orders by exchange for efficient reconciliation."""
        grouped = {}
        for order in orders:
            if order.exchange not in grouped:
                grouped[order.exchange] = []
            grouped[order.exchange].append(order)
        return grouped

    def _reconcile_exchange_orders(
        self, exchange: str, orders: List[Order], result: ReconciliationResult
    ) -> None:
        """Reconcile orders for a specific exchange."""
        try:
            executor = self.order_manager.get_executor(exchange)
            if not executor:
                result.add_error(exchange, f"No executor found for exchange {exchange}")
                return

            # Fetch all open orders from exchange
            exchange_orders = executor.get_open_orders()
            exchange_order_map = {order.id: order for order in exchange_orders}

            # Reconcile each local order
            for local_order in orders:
                exchange_order = exchange_order_map.get(local_order.id)
                if exchange_order:
                    self._reconcile_order_states(local_order, exchange_order, result)
                else:
                    # Order not found on exchange
                    result.add_discrepancy(
                        local_order.id,
                        "missing_on_exchange",
                        local_order.state.value,
                        None,
                        "error",
                    )

            # Check for orphaned exchange orders (orders on exchange but not in local state)
            local_order_ids = {order.id for order in orders}
            for exchange_order in exchange_orders:
                if exchange_order.id not in local_order_ids:
                    result.add_discrepancy(
                        exchange_order.id,
                        "orphaned_on_exchange",
                        None,
                        exchange_order.state.value,
                        "warning",
                    )

        except Exception as e:
            self.logger.error(f"Error reconciling exchange {exchange}: {e}")
            result.add_error(exchange, str(e))

    def _fetch_exchange_order(self, executor: BaseExecutor, order: Order) -> Optional[Order]:
        """Fetch order from exchange."""
        try:
            exchange_state = executor.get_order_status(order.id, order.symbol)
            if exchange_state:
                # Create a minimal order object for comparison
                return Order(
                    id=order.id,
                    client_order_id=order.client_order_id,
                    symbol=order.symbol,
                    side=order.side,
                    order_type=order.order_type,
                    state=exchange_state,
                    quantity=order.quantity,
                    price=order.price,
                    exchange=order.exchange,
                )
        except Exception as e:
            self.logger.warning(f"Could not fetch order {order.id} from exchange: {e}")

        return None

    def _reconcile_order_states(
        self, local_order: Order, exchange_order: Order, result: ReconciliationResult
    ) -> None:
        """Reconcile states between local and exchange orders."""
        # Check state mismatch
        if local_order.state != exchange_order.state:
            result.add_discrepancy(
                local_order.id,
                "state_mismatch",
                local_order.state.value,
                exchange_order.state.value,
                "error",
            )

        # Check fill quantity mismatch
        if abs(local_order.filled_quantity - exchange_order.filled_quantity) > 0.001:
            result.add_discrepancy(
                local_order.id,
                "fill_quantity_mismatch",
                local_order.filled_quantity,
                exchange_order.filled_quantity,
                "error",
            )

        # Check remaining quantity mismatch
        if abs(local_order.remaining_quantity - exchange_order.remaining_quantity) > 0.001:
            result.add_discrepancy(
                local_order.id,
                "remaining_quantity_mismatch",
                local_order.remaining_quantity,
                exchange_order.remaining_quantity,
                "warning",
            )

        # Check average fill price mismatch
        if (
            local_order.average_fill_price is not None
            and exchange_order.average_fill_price is not None
            and abs(local_order.average_fill_price - exchange_order.average_fill_price) > 0.001
        ):
            result.add_discrepancy(
                local_order.id,
                "average_fill_price_mismatch",
                local_order.average_fill_price,
                exchange_order.average_fill_price,
                "warning",
            )

        result.orders_reconciled += 1

    def _handle_reconciliation_result(self, result: ReconciliationResult) -> None:
        """Handle reconciliation results and take corrective actions."""
        for discrepancy in result.discrepancies:
            if discrepancy.severity == "error":
                self._handle_critical_discrepancy(discrepancy)
            elif discrepancy.severity == "warning":
                self._handle_warning_discrepancy(discrepancy)

    def _handle_critical_discrepancy(self, discrepancy: ReconciliationDiscrepancy) -> None:
        """Handle critical discrepancies that require immediate action."""
        order_id = discrepancy.order_id

        if discrepancy.discrepancy_type == "missing_on_exchange":
            # Order exists locally but not on exchange - mark as canceled
            order = self.order_manager.get_order(order_id)
            if order and order.is_active:
                self.order_manager.state_machine.transition(
                    order, OrderState.CANCELED, "reconciliation"
                )
                self.logger.warning(f"Marked missing order {order_id} as canceled")

        elif discrepancy.discrepancy_type == "state_mismatch":
            # State mismatch - update local state to match exchange
            order = self.order_manager.get_order(order_id)
            if order:
                # This would need to be implemented based on exchange state
                self.logger.warning(
                    f"State mismatch for order {order_id}: "
                    f"{discrepancy.local_value} vs {discrepancy.exchange_value}"
                )

    def _handle_warning_discrepancy(self, discrepancy: ReconciliationDiscrepancy) -> None:
        """Handle warning discrepancies that should be logged."""
        self.logger.warning(
            f"Reconciliation warning for order {discrepancy.order_id}: "
            f"{discrepancy.discrepancy_type} - "
            f"Local: {discrepancy.local_value}, Exchange: {discrepancy.exchange_value}"
        )

    def should_reconcile(self, exchange: str) -> bool:
        """Check if reconciliation should be performed for exchange."""
        last_reconciliation = self.last_reconciliation.get(exchange)
        if last_reconciliation is None:
            return True

        time_since_last = datetime.now() - last_reconciliation
        return time_since_last >= self.reconciliation_interval

    def set_reconciliation_interval(self, interval: timedelta) -> None:
        """Set reconciliation interval."""
        self.reconciliation_interval = interval
