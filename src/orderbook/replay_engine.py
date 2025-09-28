"""
Order Book Replay Engine

Replays historical order book data for realistic backtesting and simulation.
"""

from __future__ import annotations
from typing import Iterator, Optional, Dict, List, Callable, Any
from datetime import datetime, timedelta
import asyncio
import time

from .models import OrderBookSnapshot, OrderBookEvent, OrderBookEventType, OrderBookState
from .storage import OrderBookStorage


class OrderBookReplayEngine:
    """Replays historical order book data for simulation."""

    def __init__(
        self,
        storage: OrderBookStorage,
        replay_speed: float = 1.0,  # 1.0 = real time, 2.0 = 2x speed, 0.5 = half speed
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ):
        self.storage = storage
        self.replay_speed = replay_speed
        self.start_time = start_time
        self.end_time = end_time
        self.state = OrderBookState.PAUSED
        self.current_time: Optional[datetime] = None
        self.event_handlers: List[Callable[[OrderBookEvent], None]] = []
        self.snapshot_handlers: List[Callable[[OrderBookSnapshot], None]] = []

    def add_event_handler(self, handler: Callable[[OrderBookEvent], None]) -> None:
        """Add event handler for order book events."""
        self.event_handlers.append(handler)

    def add_snapshot_handler(self, handler: Callable[[OrderBookSnapshot], None]) -> None:
        """Add handler for order book snapshots."""
        self.snapshot_handlers.append(handler)

    def replay_snapshots(
        self,
        symbol: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Iterator[OrderBookSnapshot]:
        """
        Replay order book snapshots.

        Args:
            symbol: Trading symbol
            start_time: Start time for replay
            end_time: End time for replay

        Yields:
            OrderBookSnapshot objects in chronological order
        """
        start = start_time or self.start_time
        end = end_time or self.end_time

        if not start or not end:
            raise ValueError("Start and end times must be specified")

        print(f"Replaying order book snapshots for {symbol} from {start} to {end}")

        snapshots = list(self.storage.get_snapshots(symbol, start, end))

        if not snapshots:
            print(f"No snapshots found for {symbol} in the specified time range")
            return

        print(f"Found {len(snapshots)} snapshots")

        # Sort by timestamp
        snapshots.sort(key=lambda x: x.timestamp)

        last_timestamp = None

        for snapshot in snapshots:
            if self.state == OrderBookState.CLOSED:
                break

            # Wait if replay is paused
            while self.state == OrderBookState.PAUSED:
                time.sleep(0.1)

            if self.state == OrderBookState.ERROR:
                break

            # Calculate delay for realistic replay
            if last_timestamp and self.replay_speed > 0:
                actual_delay = (snapshot.timestamp - last_timestamp).total_seconds()
                replay_delay = actual_delay / self.replay_speed

                if replay_delay > 0:
                    time.sleep(replay_delay)

            self.current_time = snapshot.timestamp

            # Notify handlers
            for handler in self.snapshot_handlers:
                try:
                    handler(snapshot)
                except Exception as e:
                    print(f"Error in snapshot handler: {e}")

            yield snapshot
            last_timestamp = snapshot.timestamp

    async def replay_snapshots_async(
        self,
        symbol: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Iterator[OrderBookSnapshot]:
        """
        Async replay of order book snapshots.

        Args:
            symbol: Trading symbol
            start_time: Start time for replay
            end_time: End time for replay

        Yields:
            OrderBookSnapshot objects in chronological order
        """
        start = start_time or self.start_time
        end = end_time or self.end_time

        if not start or not end:
            raise ValueError("Start and end times must be specified")

        snapshots = list(self.storage.get_snapshots(symbol, start, end))

        if not snapshots:
            return

        # Sort by timestamp
        snapshots.sort(key=lambda x: x.timestamp)

        last_timestamp = None

        for snapshot in snapshots:
            if self.state == OrderBookState.CLOSED:
                break

            # Wait if replay is paused
            while self.state == OrderBookState.PAUSED:
                await asyncio.sleep(0.1)

            if self.state == OrderBookState.ERROR:
                break

            # Calculate delay for realistic replay
            if last_timestamp and self.replay_speed > 0:
                actual_delay = (snapshot.timestamp - last_timestamp).total_seconds()
                replay_delay = actual_delay / self.replay_speed

                if replay_delay > 0:
                    await asyncio.sleep(replay_delay)

            self.current_time = snapshot.timestamp

            # Notify handlers
            for handler in self.snapshot_handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(snapshot)
                    else:
                        handler(snapshot)
                except Exception as e:
                    print(f"Error in snapshot handler: {e}")

            yield snapshot
            last_timestamp = snapshot.timestamp

    def replay_events(
        self,
        symbol: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Iterator[OrderBookEvent]:
        """
        Replay order book events.

        Args:
            symbol: Trading symbol
            start_time: Start time for replay
            end_time: End time for replay

        Yields:
            OrderBookEvent objects in chronological order
        """
        start = start_time or self.start_time
        end = end_time or self.end_time

        if not start or not end:
            raise ValueError("Start and end times must be specified")

        print(f"Replaying order book events for {symbol} from {start} to {end}")

        events = list(self.storage.get_events(symbol, start, end))

        if not events:
            print(f"No events found for {symbol} in the specified time range")
            return

        print(f"Found {len(events)} events")

        # Sort by timestamp
        events.sort(key=lambda x: x.timestamp)

        last_timestamp = None

        for event in events:
            if self.state == OrderBookState.CLOSED:
                break

            # Wait if replay is paused
            while self.state == OrderBookState.PAUSED:
                time.sleep(0.1)

            if self.state == OrderBookState.ERROR:
                break

            # Calculate delay for realistic replay
            if last_timestamp and self.replay_speed > 0:
                actual_delay = (event.timestamp - last_timestamp).total_seconds()
                replay_delay = actual_delay / self.replay_speed

                if replay_delay > 0:
                    time.sleep(replay_delay)

            self.current_time = event.timestamp

            # Notify handlers
            for handler in self.event_handlers:
                try:
                    handler(event)
                except Exception as e:
                    print(f"Error in event handler: {e}")

            yield event
            last_timestamp = event.timestamp

    def start_replay(self) -> None:
        """Start the replay engine."""
        self.state = OrderBookState.ACTIVE
        print("Replay engine started")

    def pause_replay(self) -> None:
        """Pause the replay engine."""
        self.state = OrderBookState.PAUSED
        print("Replay engine paused")

    def stop_replay(self) -> None:
        """Stop the replay engine."""
        self.state = OrderBookState.CLOSED
        print("Replay engine stopped")

    def set_replay_speed(self, speed: float) -> None:
        """Set replay speed multiplier."""
        self.replay_speed = max(0.0, speed)
        print(f"Replay speed set to {self.replay_speed}x")

    def get_current_time(self) -> Optional[datetime]:
        """Get current replay time."""
        return self.current_time

    def get_state(self) -> OrderBookState:
        """Get current replay state."""
        return self.state

    def replay_with_simulation(
        self,
        symbol: str,
        simulation_func: Callable[[OrderBookSnapshot], Any],
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Any]:
        """
        Replay snapshots and run simulation function on each one.

        Args:
            symbol: Trading symbol
            simulation_func: Function to run on each snapshot
            start_time: Start time for replay
            end_time: End time for replay

        Returns:
            List of simulation results
        """
        results = []

        for snapshot in self.replay_snapshots(symbol, start_time, end_time):
            try:
                result = simulation_func(snapshot)
                results.append(result)
            except Exception as e:
                print(f"Error in simulation function: {e}")
                results.append(None)

        return results

    def get_replay_statistics(
        self, symbol: str, start_time: datetime, end_time: datetime
    ) -> Dict[str, Any]:
        """Get statistics about the replay data."""
        snapshots = list(self.storage.get_snapshots(symbol, start_time, end_time))
        events = list(self.storage.get_events(symbol, start_time, end_time))

        if not snapshots:
            return {
                "snapshot_count": 0,
                "event_count": 0,
                "duration_hours": 0,
                "avg_snapshot_interval_seconds": 0,
                "avg_event_interval_seconds": 0,
            }

        # Sort by timestamp
        snapshots.sort(key=lambda x: x.timestamp)
        events.sort(key=lambda x: x.timestamp)

        duration = (snapshots[-1].timestamp - snapshots[0].timestamp).total_seconds() / 3600

        # Calculate average intervals
        snapshot_intervals = []
        for i in range(1, len(snapshots)):
            interval = (snapshots[i].timestamp - snapshots[i - 1].timestamp).total_seconds()
            snapshot_intervals.append(interval)

        event_intervals = []
        for i in range(1, len(events)):
            interval = (events[i].timestamp - events[i - 1].timestamp).total_seconds()
            event_intervals.append(interval)

        return {
            "snapshot_count": len(snapshots),
            "event_count": len(events),
            "duration_hours": duration,
            "avg_snapshot_interval_seconds": (
                sum(snapshot_intervals) / len(snapshot_intervals) if snapshot_intervals else 0
            ),
            "avg_event_interval_seconds": (
                sum(event_intervals) / len(event_intervals) if event_intervals else 0
            ),
            "first_snapshot_time": snapshots[0].timestamp.isoformat() if snapshots else None,
            "last_snapshot_time": snapshots[-1].timestamp.isoformat() if snapshots else None,
        }
