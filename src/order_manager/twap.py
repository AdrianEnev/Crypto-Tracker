"""
TWAP (Time-Weighted Average Price) Implementation

Implements time-weighted average price order execution by
slicing large orders into smaller pieces executed over time.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import schedule

from .executors import BaseExecutor
from .models import Order, OrderRequest, OrderState, OrderType


@dataclass
class TWAPConfig:
    """Configuration for TWAP execution."""

    min_slice_size_usd: float = 100.0
    max_slices: int = 20
    min_slice_interval_seconds: int = 30
    max_slice_interval_seconds: int = 300
    slice_size_percentage: float = 0.1  # 10% of total order per slice
    randomization_factor: float = 0.1  # 10% randomization


class TWAPSlicer:
    """Handles TWAP order slicing and execution."""

    def __init__(self, config: Optional[TWAPConfig] = None):
        self.config = config or TWAPConfig()
        self.logger = logging.getLogger(__name__)
        self.active_twap_orders: Dict[str, TWAPExecution] = {}
        self.scheduled_slices: Dict[str, List[schedule.Job]] = {}

    def create_twap_order(self, parent_order: Order, executor: BaseExecutor) -> Order:
        """Create TWAP order with time-based slicing."""
        try:
            # Validate TWAP order
            if not self._validate_twap_order(parent_order):
                raise ValueError("Invalid TWAP order configuration")

            # Calculate slice parameters
            slice_params = self._calculate_slice_parameters(parent_order)

            # Create TWAP execution
            twap_execution = TWAPExecution(
                parent_order=parent_order, executor=executor, slice_params=slice_params, slicer=self
            )

            # Store execution
            self.active_twap_orders[parent_order.id] = twap_execution

            # Schedule slices
            self._schedule_slices(twap_execution)

            # Update parent order
            parent_order.twap_slice_count = slice_params.slice_count
            parent_order.twap_slice_interval = slice_params.slice_interval

            self.logger.info(
                f"Created TWAP order {parent_order.id} with {slice_params.slice_count} slices, "
                f"interval {slice_params.slice_interval}s"
            )

            return parent_order

        except Exception as e:
            self.logger.error(f"Error creating TWAP order {parent_order.id}: {e}")
            raise

    def execute_twap_slice(self, twap_execution: TWAPExecution, slice_index: int) -> bool:
        """Execute a single TWAP slice."""
        try:
            parent_order = twap_execution.parent_order

            # Check if order is still active
            if not parent_order.is_active:
                self.logger.warning(f"TWAP order {parent_order.id} is no longer active")
                return False

            # Calculate slice size
            slice_size = self._calculate_slice_size(twap_execution, slice_index)
            if slice_size <= 0:
                self.logger.warning(f"Invalid slice size for TWAP order {parent_order.id}")
                return False

            # Create slice order request
            slice_request = OrderRequest(
                symbol=parent_order.symbol,
                side=parent_order.side,
                order_type=OrderType.MARKET,  # Execute slices as market orders
                quantity=slice_size,
                price=parent_order.price,  # Use parent price as reference
                client_order_id=f"{parent_order.id}_slice_{slice_index}",
                strategy_id=parent_order.strategy_id,
            )

            # Execute slice
            slice_result = twap_execution.executor.place_order(slice_request)

            if slice_result.success:
                # Update parent order with fill
                parent_order.update_fill(slice_size, slice_result.price or parent_order.price)

                # Update TWAP execution
                twap_execution.completed_slices += 1
                twap_execution.total_filled += slice_size

                self.logger.info(
                    f"Executed TWAP slice {slice_index} for order {parent_order.id}: "
                    f"{slice_size} @ {slice_result.price}"
                )

                # Check if TWAP is complete
                if twap_execution.completed_slices >= twap_execution.slice_params.slice_count:
                    self._complete_twap_execution(twap_execution)

                return True
            else:
                self.logger.error(
                    f"Failed to execute TWAP slice {slice_index} for order {parent_order.id}: "
                    f"{slice_result.error_message}"
                )
                return False

        except Exception as e:
            self.logger.error(f"Error executing TWAP slice: {e}")
            return False

    def cancel_twap_order(self, order_id: str) -> bool:
        """Cancel TWAP order and all scheduled slices."""
        try:
            if order_id not in self.active_twap_orders:
                return False

            twap_execution = self.active_twap_orders[order_id]

            # Cancel scheduled slices
            if order_id in self.scheduled_slices:
                for job in self.scheduled_slices[order_id]:
                    schedule.cancel_job(job)
                del self.scheduled_slices[order_id]

            # Update parent order state
            twap_execution.parent_order.state = OrderState.CANCELED

            # Remove from active orders
            del self.active_twap_orders[order_id]

            self.logger.info(f"Cancelled TWAP order {order_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error cancelling TWAP order {order_id}: {e}")
            return False

    def get_twap_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get status of TWAP order."""
        if order_id not in self.active_twap_orders:
            return None

        twap_execution = self.active_twap_orders[order_id]

        return {
            "order_id": order_id,
            "total_slices": twap_execution.slice_params.slice_count,
            "completed_slices": twap_execution.completed_slices,
            "remaining_slices": twap_execution.slice_params.slice_count
            - twap_execution.completed_slices,
            "total_filled": twap_execution.total_filled,
            "remaining_quantity": twap_execution.parent_order.remaining_quantity,
            "slice_interval": twap_execution.slice_params.slice_interval,
            "is_active": twap_execution.parent_order.is_active,
        }

    def _validate_twap_order(self, order: Order) -> bool:
        """Validate TWAP order configuration."""
        if order.order_type != OrderType.TWAP:
            return False

        if order.twap_duration_seconds is None or order.twap_duration_seconds <= 0:
            return False

        if order.quantity <= 0:
            return False

        return True

    def _calculate_slice_parameters(self, order: Order) -> "SliceParameters":
        """Calculate optimal slice parameters for TWAP order."""
        duration_seconds = order.twap_duration_seconds
        total_quantity = order.quantity

        # Calculate slice count based on duration and minimum interval
        max_possible_slices = duration_seconds // self.config.min_slice_interval_seconds
        optimal_slices = min(max_possible_slices, self.config.max_slices)

        # Ensure minimum slice count
        slice_count = max(optimal_slices, 1)

        # Calculate slice interval
        slice_interval = duration_seconds // slice_count

        # Ensure interval is within bounds
        slice_interval = max(slice_interval, self.config.min_slice_interval_seconds)
        slice_interval = min(slice_interval, self.config.max_slice_interval_seconds)

        return SliceParameters(
            slice_count=slice_count,
            slice_interval=slice_interval,
            base_slice_size=total_quantity / slice_count,
        )

    def _calculate_slice_size(self, twap_execution: TWAPExecution, slice_index: int) -> float:
        """Calculate size for specific slice with randomization."""
        import random

        base_size = twap_execution.slice_params.base_slice_size

        # Apply randomization to avoid predictable patterns
        randomization = random.uniform(
            1 - self.config.randomization_factor, 1 + self.config.randomization_factor
        )

        slice_size = base_size * randomization

        # Ensure we don't exceed remaining quantity
        remaining = twap_execution.parent_order.remaining_quantity
        slice_size = min(slice_size, remaining)

        # Ensure minimum slice size
        if slice_size < self.config.min_slice_size_usd / (twap_execution.parent_order.price or 1.0):
            slice_size = 0

        return slice_size

    def _schedule_slices(self, twap_execution: TWAPExecution) -> None:
        """Schedule execution of TWAP slices."""
        parent_order = twap_execution.parent_order
        order_id = parent_order.id

        # Clear any existing scheduled slices
        if order_id in self.scheduled_slices:
            for job in self.scheduled_slices[order_id]:
                schedule.cancel_job(job)

        self.scheduled_slices[order_id] = []

        # Schedule each slice
        for slice_index in range(twap_execution.slice_params.slice_count):
            delay_seconds = slice_index * twap_execution.slice_params.slice_interval

            job = schedule.every(delay_seconds).seconds.do(
                self.execute_twap_slice, twap_execution, slice_index
            )

            self.scheduled_slices[order_id].append(job)

    def _complete_twap_execution(self, twap_execution: TWAPExecution) -> None:
        """Complete TWAP execution."""
        parent_order = twap_execution.parent_order

        # Clean up scheduled slices
        if parent_order.id in self.scheduled_slices:
            for job in self.scheduled_slices[parent_order.id]:
                schedule.cancel_job(job)
            del self.scheduled_slices[parent_order.id]

        # Update order state
        if parent_order.filled_quantity >= parent_order.quantity:
            parent_order.state = OrderState.FILLED
        else:
            parent_order.state = OrderState.PARTIALLY_FILLED

        # Remove from active TWAP orders
        del self.active_twap_orders[parent_order.id]

        self.logger.info(f"Completed TWAP execution for order {parent_order.id}")


@dataclass
class SliceParameters:
    """Parameters for order slicing."""

    slice_count: int
    slice_interval: int
    base_slice_size: float


@dataclass
class TWAPExecution:
    """Represents an active TWAP execution."""

    parent_order: Order
    executor: BaseExecutor
    slice_params: SliceParameters
    slicer: TWAPSlicer
    completed_slices: int = 0
    total_filled: float = 0.0
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
