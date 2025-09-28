"""
Order Retry Logic

Comprehensive retry mechanism with exponential backoff,
error classification, and circuit breaker patterns.
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from .models import ExchangeError, MaxRetriesExceededError, Order, OrderResult


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    backoff_multiplier: float = 2.0
    jitter_range: float = 0.1  # 10% jitter
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60  # seconds


@dataclass
class RetryAttempt:
    """Record of a retry attempt."""

    attempt_number: int
    timestamp: datetime
    error: Optional[str] = None
    delay_seconds: Optional[float] = None
    success: bool = False


class CircuitBreaker:
    """Circuit breaker pattern for exchange failures."""

    def __init__(self, threshold: int, timeout: int):
        self.threshold = threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def can_execute(self) -> bool:
        """Check if execution is allowed."""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
                return True
            return False
        elif self.state == "HALF_OPEN":
            return True
        return False

    def record_success(self) -> None:
        """Record successful execution."""
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            self.failure_count = 0

    def record_failure(self) -> None:
        """Record failed execution."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.threshold:
            self.state = "OPEN"

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True

        time_since_failure = datetime.now() - self.last_failure_time
        return time_since_failure.total_seconds() >= self.timeout


class OrderRetryManager:
    """Manages retry logic for order execution."""

    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self.retry_counts: Dict[str, int] = {}
        self.retry_history: Dict[str, List[RetryAttempt]] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.logger = logging.getLogger(__name__)

        # Error classification
        self.retryable_errors = {
            "timeout",
            "connection_error",
            "rate_limit",
            "temporary_unavailable",
            "network_error",
        }

        self.non_retryable_errors = {
            "invalid_order",
            "insufficient_funds",
            "invalid_symbol",
            "order_not_found",
            "permission_denied",
        }

    def execute_with_retry(
        self, order: Order, executor: Any, execution_func: Callable[[Order], OrderResult]
    ) -> OrderResult:
        """Execute order with retry logic."""
        order_id = order.id
        exchange = order.exchange

        # Initialize retry tracking
        if order_id not in self.retry_counts:
            self.retry_counts[order_id] = 0
        if order_id not in self.retry_history:
            self.retry_history[order_id] = []

        # Check circuit breaker
        circuit_breaker = self._get_circuit_breaker(exchange)
        if not circuit_breaker.can_execute():
            error_msg = f"Circuit breaker OPEN for exchange {exchange}"
            self.logger.warning(error_msg)
            return OrderResult(order_id=order_id, success=False, error_message=error_msg)

        # Execute with retries
        last_error = None
        retry_count = self.retry_counts[order_id]

        while retry_count < self.config.max_retries:
            try:
                # Record attempt
                attempt = RetryAttempt(attempt_number=retry_count + 1, timestamp=datetime.now())

                # Execute order
                start_time = time.time()
                result = execution_func(order)
                execution_time = (time.time() - start_time) * 1000  # ms

                attempt.success = result.success
                attempt.delay_seconds = 0

                if result.success:
                    # Success - record and return
                    circuit_breaker.record_success()
                    attempt.error = None
                    self.retry_history[order_id].append(attempt)

                    # Record execution metrics
                    self._record_execution_metrics(exchange, result, execution_time)

                    return result
                else:
                    # Failed but might be retryable
                    last_error = result.error_message
                    attempt.error = last_error

                    if not self._is_retryable_error(last_error):
                        # Non-retryable error
                        circuit_breaker.record_failure()
                        self.retry_history[order_id].append(attempt)
                        return result

            except Exception as e:
                last_error = str(e)
                attempt.error = last_error

                if not self._is_retryable_error(last_error):
                    # Non-retryable exception
                    circuit_breaker.record_failure()
                    self.retry_history[order_id].append(attempt)
                    raise

            # Retryable error - prepare for retry
            retry_count += 1
            self.retry_counts[order_id] = retry_count

            if retry_count < self.config.max_retries:
                # Calculate delay
                delay = self._calculate_delay(retry_count)
                attempt.delay_seconds = delay

                # Log retry attempt
                self.logger.warning(
                    f"Retry {retry_count}/{self.config.max_retries} for order {order_id}: {last_error}"
                )

                # Wait before retry
                time.sleep(delay)

            self.retry_history[order_id].append(attempt)

        # Max retries exceeded
        circuit_breaker.record_failure()

        error_msg = f"Max retries ({self.config.max_retries}) exceeded for order {order_id}"
        self.logger.error(f"{error_msg}. Last error: {last_error}")

        raise MaxRetriesExceededError(error_msg)

    def _get_circuit_breaker(self, exchange: str) -> CircuitBreaker:
        """Get or create circuit breaker for exchange."""
        if exchange not in self.circuit_breakers:
            self.circuit_breakers[exchange] = CircuitBreaker(
                threshold=self.config.circuit_breaker_threshold,
                timeout=self.config.circuit_breaker_timeout,
            )
        return self.circuit_breakers[exchange]

    def _is_retryable_error(self, error_message: str) -> bool:
        """Determine if error is retryable."""
        if not error_message:
            return True

        error_lower = error_message.lower()

        # Check for non-retryable errors first
        for non_retryable in self.non_retryable_errors:
            if non_retryable in error_lower:
                return False

        # Check for retryable errors
        for retryable in self.retryable_errors:
            if retryable in error_lower:
                return True

        # Default to retryable for unknown errors
        return True

    def _calculate_delay(self, retry_count: int) -> float:
        """Calculate delay for retry with exponential backoff and jitter."""
        # Exponential backoff
        delay = self.config.base_delay_seconds * (
            self.config.backoff_multiplier ** (retry_count - 1)
        )

        # Cap at max delay
        delay = min(delay, self.config.max_delay_seconds)

        # Add jitter to prevent thundering herd
        jitter = random.uniform(-self.config.jitter_range, self.config.jitter_range) * delay
        delay += jitter

        return max(0, delay)

    def _record_execution_metrics(
        self, exchange: str, result: OrderResult, execution_time_ms: float
    ) -> None:
        """Record execution metrics for analysis."""
        # This could be used to update exchange rankings
        # For now, just log the metrics
        self.logger.debug(
            f"Execution metrics - Exchange: {exchange}, "
            f"Success: {result.success}, "
            f"Time: {execution_time_ms}ms"
        )

    def get_retry_statistics(self, order_id: Optional[str] = None) -> Dict[str, any]:
        """Get retry statistics."""
        if order_id:
            return {
                "order_id": order_id,
                "retry_count": self.retry_counts.get(order_id, 0),
                "retry_history": self.retry_history.get(order_id, []),
            }

        # Global statistics
        total_orders = len(self.retry_counts)
        total_retries = sum(self.retry_counts.values())
        avg_retries = total_retries / total_orders if total_orders > 0 else 0

        circuit_breaker_stats = {}
        for exchange, cb in self.circuit_breakers.items():
            circuit_breaker_stats[exchange] = {
                "state": cb.state,
                "failure_count": cb.failure_count,
                "last_failure_time": cb.last_failure_time,
            }

        return {
            "total_orders": total_orders,
            "total_retries": total_retries,
            "average_retries_per_order": avg_retries,
            "circuit_breakers": circuit_breaker_stats,
        }

    def reset_circuit_breaker(self, exchange: str) -> bool:
        """Manually reset circuit breaker for exchange."""
        if exchange in self.circuit_breakers:
            cb = self.circuit_breakers[exchange]
            cb.state = "CLOSED"
            cb.failure_count = 0
            cb.last_failure_time = None
            return True
        return False

    def clear_retry_history(self, order_id: Optional[str] = None) -> None:
        """Clear retry history."""
        if order_id:
            if order_id in self.retry_counts:
                del self.retry_counts[order_id]
            if order_id in self.retry_history:
                del self.retry_history[order_id]
        else:
            self.retry_counts.clear()
            self.retry_history.clear()

    def update_retry_config(self, config: RetryConfig) -> None:
        """Update retry configuration."""
        self.config = config

        # Update circuit breaker configs
        for cb in self.circuit_breakers.values():
            cb.threshold = config.circuit_breaker_threshold
            cb.timeout = config.circuit_breaker_timeout
