"""
Order State Machine

Manages order state transitions and enforces valid state changes
throughout the order lifecycle.
"""

from __future__ import annotations
from typing import Dict, Set, Optional
from datetime import datetime, timezone

from .models import Order, OrderState, OrderValidationError


class OrderStateMachine:
    """Manages order state transitions with validation."""

    # Define valid state transitions
    VALID_TRANSITIONS: Dict[OrderState, Set[OrderState]] = {
        OrderState.NEW: {OrderState.PENDING, OrderState.REJECTED, OrderState.CANCELED},
        OrderState.PENDING: {
            OrderState.PARTIALLY_FILLED,
            OrderState.FILLED,
            OrderState.CANCELED,
            OrderState.REJECTED,
            OrderState.EXPIRED,
        },
        OrderState.PARTIALLY_FILLED: {OrderState.FILLED, OrderState.CANCELED, OrderState.REJECTED},
        OrderState.FILLED: set(),  # Terminal state
        OrderState.CANCELED: set(),  # Terminal state
        OrderState.REJECTED: set(),  # Terminal state
        OrderState.EXPIRED: set(),  # Terminal state
    }

    # States that allow modifications
    MODIFIABLE_STATES = {OrderState.NEW, OrderState.PENDING, OrderState.PARTIALLY_FILLED}

    # States that allow cancellation
    CANCELLABLE_STATES = {OrderState.NEW, OrderState.PENDING, OrderState.PARTIALLY_FILLED}

    def __init__(self):
        self._transition_history: Dict[str, list] = {}

    def can_transition(self, from_state: OrderState, to_state: OrderState) -> bool:
        """Check if transition from one state to another is valid."""
        return to_state in self.VALID_TRANSITIONS.get(from_state, set())

    def transition(self, order: Order, new_state: OrderState, reason: Optional[str] = None) -> bool:
        """
        Transition order to new state with validation.

        Args:
            order: Order to transition
            new_state: Target state
            reason: Optional reason for transition

        Returns:
            True if transition was successful, False otherwise

        Raises:
            OrderValidationError: If transition is invalid
        """
        if not self.can_transition(order.state, new_state):
            from .models import OrderValidationResult

            validation_result = OrderValidationResult(is_valid=False)
            validation_result.add_error(
                f"Invalid state transition from {order.state.value} to {new_state.value}"
            )
            raise OrderValidationError(validation_result)

        # Record transition
        self._record_transition(order.id, order.state, new_state, reason)

        # Update order state
        old_state = order.state
        order.state = new_state
        order.updated_at = datetime.now(timezone.utc)

        # Set specific timestamps based on state
        if new_state == OrderState.CANCELED:
            order.canceled_at = order.updated_at
        elif new_state == OrderState.FILLED and order.filled_at is None:
            order.filled_at = order.updated_at

        return True

    def can_modify(self, order: Order) -> bool:
        """Check if order can be modified."""
        return order.state in self.MODIFIABLE_STATES

    def can_cancel(self, order: Order) -> bool:
        """Check if order can be canceled."""
        return order.state in self.CANCELLABLE_STATES

    def is_terminal_state(self, state: OrderState) -> bool:
        """Check if state is terminal (no further transitions possible)."""
        return len(self.VALID_TRANSITIONS.get(state, set())) == 0

    def get_next_possible_states(self, current_state: OrderState) -> Set[OrderState]:
        """Get all possible next states from current state."""
        return self.VALID_TRANSITIONS.get(current_state, set()).copy()

    def get_transition_history(self, order_id: str) -> list:
        """Get transition history for an order."""
        return self._transition_history.get(order_id, []).copy()

    def _record_transition(
        self, order_id: str, from_state: OrderState, to_state: OrderState, reason: Optional[str]
    ):
        """Record state transition for audit purposes."""
        if order_id not in self._transition_history:
            self._transition_history[order_id] = []

        transition_record = {
            "timestamp": datetime.now(timezone.utc),
            "from_state": from_state.value,
            "to_state": to_state.value,
            "reason": reason,
        }

        self._transition_history[order_id].append(transition_record)

    def validate_order_state(self, order: Order) -> bool:
        """Validate that order state is consistent with its properties."""
        # Check if filled quantity is consistent with state
        if order.state == OrderState.FILLED and order.filled_quantity < order.quantity:
            return False

        if order.state == OrderState.PARTIALLY_FILLED and order.filled_quantity <= 0:
            return False

        if order.state == OrderState.PENDING and order.filled_quantity > 0:
            return False

        # Check if remaining quantity is consistent
        expected_remaining = order.quantity - order.filled_quantity
        if abs(order.remaining_quantity - expected_remaining) > 0.001:
            return False

        return True

    def get_order_lifecycle_summary(self, order_id: str) -> Dict[str, any]:
        """Get summary of order lifecycle."""
        history = self.get_transition_history(order_id)
        if not history:
            return {"order_id": order_id, "transitions": 0, "duration_seconds": 0}

        first_transition = history[0]["timestamp"]
        last_transition = history[-1]["timestamp"]
        duration = (last_transition - first_transition).total_seconds()

        return {
            "order_id": order_id,
            "transitions": len(history),
            "duration_seconds": duration,
            "first_state": history[0]["from_state"],
            "final_state": history[-1]["to_state"],
            "transition_history": history,
        }
