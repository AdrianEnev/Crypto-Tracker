"""
Order Book Simulator

Simulates realistic order execution based on historical order book data
for advanced backtesting and strategy testing.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Callable, Any
from datetime import datetime
from dataclasses import dataclass, field
import time
import random

from .models import (
    OrderBookSnapshot, OrderLevel, FillResult, OrderBookMetrics,
    BidDepth, AskDepth
)
# Note: SlippageResult, SlippageType, MarketCondition are imported from slippage.models
# but we'll define them locally to avoid import issues
from enum import Enum

class SlippageType(Enum):
    """Types of slippage models."""
    STATIC = "static"
    DEPTH_BASED = "depth_based"
    VOLUME_BASED = "volume_based"
    MARKET_IMPACT = "market_impact"
    ADAPTIVE = "adaptive"

class MarketCondition(Enum):
    """Market condition classifications."""
    CALM = "calm"
    NORMAL = "normal"
    VOLATILE = "volatile"
    ILLIQUID = "illiquid"
    STRESSED = "stressed"

@dataclass
class SlippageResult:
    """Result of slippage calculation."""
    slippage_bps: float
    slippage_usd: float
    effective_price: float
    reference_price: float
    slippage_type: SlippageType
    market_condition: MarketCondition
    
    # Additional metadata
    liquidity_used: float = 0.0
    depth_levels_used: int = 0
    market_impact_bps: float = 0.0
    
    # Fill simulation results
    fill_quantity: float = 0.0
    unfilled_quantity: float = 0.0
    partial_fill: bool = False


@dataclass
class SimulatedOrder:
    """Represents an order to be simulated."""
    order_id: str
    symbol: str
    side: str  # "buy" or "sell"
    order_type: str  # "market", "limit", "stop", etc.
    quantity: float
    price: Optional[float] = None  # For limit orders
    stop_price: Optional[float] = None  # For stop orders
    time_in_force: str = "GTC"  # Good Till Canceled
    timestamp: Optional[datetime] = None
    
    # Execution parameters
    max_slippage_bps: Optional[float] = None
    min_fill_size: Optional[float] = None
    
    # Metadata
    strategy_id: Optional[str] = None
    tags: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SimulatedFill:
    """Result of order simulation."""
    order_id: str
    symbol: str
    side: str
    filled_quantity: float
    remaining_quantity: float
    average_price: float
    total_cost: float
    
    # Execution details
    fill_timestamp: datetime
    execution_time_ms: float
    slippage_bps: float
    market_impact_bps: float
    
    # Order book impact
    levels_consumed: int
    liquidity_consumed: float
    
    # Partial fill information
    is_partial_fill: bool
    is_completely_filled: bool
    
    @property
    def fill_percentage(self) -> float:
        """Calculate fill percentage."""
        total_quantity = self.filled_quantity + self.remaining_quantity
        if total_quantity == 0:
            return 0.0
        return (self.filled_quantity / total_quantity) * 100.0


class OrderBookSimulator:
    """Simulates order execution against historical order book data."""
    
    def __init__(
        self,
        latency_ms: float = 50.0,  # Simulated network latency
        partial_fill_probability: float = 0.1,  # Probability of partial fills
        rejection_probability: float = 0.01,  # Probability of order rejection
        market_impact_factor: float = 0.001  # Market impact scaling factor
    ):
        self.latency_ms = latency_ms
        self.partial_fill_probability = partial_fill_probability
        self.rejection_probability = rejection_probability
        self.market_impact_factor = market_impact_factor
        
        # Simulation state
        self.current_order_book: Optional[OrderBookSnapshot] = None
        self.order_counter = 0
        self.simulation_results: List[SimulatedFill] = []
    
    def set_order_book(self, order_book: OrderBookSnapshot) -> None:
        """Set the current order book state."""
        self.current_order_book = order_book
    
    def simulate_order(self, order: SimulatedOrder) -> SimulatedFill:
        """
        Simulate order execution against current order book.
        
        Args:
            order: Order to simulate
            
        Returns:
            SimulatedFill with execution results
        """
        if not self.current_order_book:
            raise ValueError("No order book set. Call set_order_book() first.")
        
        if not self.current_order_book.is_valid():
            raise ValueError("Current order book is invalid")
        
        # Simulate network latency
        execution_start = datetime.now()
        time.sleep(self.latency_ms / 1000.0)
        
        # Check for order rejection
        import random
        if random.random() < self.rejection_probability:
            return self._create_rejected_fill(order, execution_start)
        
        # Simulate order execution based on type
        if order.order_type.lower() == "market":
            return self._simulate_market_order(order, execution_start)
        elif order.order_type.lower() == "limit":
            return self._simulate_limit_order(order, execution_start)
        elif order.order_type.lower() == "stop":
            return self._simulate_stop_order(order, execution_start)
        else:
            # Default to market order
            return self._simulate_market_order(order, execution_start)
    
    def _simulate_market_order(self, order: SimulatedOrder, execution_start: datetime) -> SimulatedFill:
        """Simulate market order execution."""
        if order.side.lower() == "buy":
            return self._simulate_buy_market_order(order, execution_start)
        else:
            return self._simulate_sell_market_order(order, execution_start)
    
    def _simulate_buy_market_order(self, order: SimulatedOrder, execution_start: datetime) -> SimulatedFill:
        """Simulate buy market order against ask side."""
        asks = self.current_order_book.asks
        
        # Check if we have enough liquidity
        total_liquidity = sum(level.quantity for level in asks.levels)
        if total_liquidity < order.quantity:
            # Partial fill with available liquidity
            return self._simulate_partial_fill(order, asks, execution_start, "buy")
        
        # Simulate fill against ask side
        filled_quantity, average_price, levels_consumed = asks.simulate_fill(order.quantity)
        
        # Calculate slippage
        reference_price = self.current_order_book.best_ask
        slippage_bps = ((average_price - reference_price) / reference_price) * 10000
        
        # Calculate market impact
        market_impact_bps = self._calculate_market_impact(order.quantity, total_liquidity)
        
        execution_time = (datetime.now() - execution_start).total_seconds() * 1000
        
        return SimulatedFill(
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            filled_quantity=filled_quantity,
            remaining_quantity=order.quantity - filled_quantity,
            average_price=average_price,
            total_cost=filled_quantity * average_price,
            fill_timestamp=execution_start,
            execution_time_ms=execution_time,
            slippage_bps=slippage_bps,
            market_impact_bps=market_impact_bps,
            levels_consumed=levels_consumed,
            liquidity_consumed=filled_quantity,
            is_partial_fill=filled_quantity < order.quantity,
            is_completely_filled=filled_quantity >= order.quantity
        )
    
    def _simulate_sell_market_order(self, order: SimulatedOrder, execution_start: datetime) -> SimulatedFill:
        """Simulate sell market order against bid side."""
        bids = self.current_order_book.bids
        
        # Check if we have enough liquidity
        total_liquidity = sum(level.quantity for level in bids.levels)
        if total_liquidity < order.quantity:
            # Partial fill with available liquidity
            return self._simulate_partial_fill(order, bids, execution_start, "sell")
        
        # Simulate fill against bid side
        filled_quantity, average_price, levels_consumed = bids.simulate_fill(order.quantity)
        
        # Calculate slippage
        reference_price = self.current_order_book.best_bid
        slippage_bps = ((reference_price - average_price) / reference_price) * 10000
        
        # Calculate market impact
        market_impact_bps = self._calculate_market_impact(order.quantity, total_liquidity)
        
        execution_time = (datetime.now() - execution_start).total_seconds() * 1000
        
        return SimulatedFill(
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            filled_quantity=filled_quantity,
            remaining_quantity=order.quantity - filled_quantity,
            average_price=average_price,
            total_cost=filled_quantity * average_price,
            fill_timestamp=execution_start,
            execution_time_ms=execution_time,
            slippage_bps=slippage_bps,
            market_impact_bps=market_impact_bps,
            levels_consumed=levels_consumed,
            liquidity_consumed=filled_quantity,
            is_partial_fill=filled_quantity < order.quantity,
            is_completely_filled=filled_quantity >= order.quantity
        )
    
    def _simulate_limit_order(self, order: SimulatedOrder, execution_start: datetime) -> SimulatedFill:
        """Simulate limit order execution."""
        if order.price is None:
            raise ValueError("Limit orders require a price")
        
        if order.side.lower() == "buy":
            # Buy limit order - executes if price <= best ask
            if self.current_order_book.best_ask and order.price >= self.current_order_book.best_ask:
                # Execute immediately at best ask or better
                execution_price = min(order.price, self.current_order_book.best_ask)
                return self._create_immediate_fill(order, execution_price, execution_start)
            else:
                # Order would be placed in order book
                return self._create_unfilled_fill(order, execution_start)
        else:
            # Sell limit order - executes if price >= best bid
            if self.current_order_book.best_bid and order.price <= self.current_order_book.best_bid:
                # Execute immediately at best bid or better
                execution_price = max(order.price, self.current_order_book.best_bid)
                return self._create_immediate_fill(order, execution_price, execution_start)
            else:
                # Order would be placed in order book
                return self._create_unfilled_fill(order, execution_start)
    
    def _simulate_stop_order(self, order: SimulatedOrder, execution_start: datetime) -> SimulatedFill:
        """Simulate stop order execution."""
        if order.stop_price is None:
            raise ValueError("Stop orders require a stop price")
        
        current_price = self.current_order_book.mid_price
        if current_price is None:
            return self._create_rejected_fill(order, execution_start)
        
        # Check if stop price is triggered
        if order.side.lower() == "buy":
            # Buy stop - triggers if price rises above stop price
            if current_price > order.stop_price:
                # Convert to market order
                market_order = SimulatedOrder(
                    order_id=order.order_id,
                    symbol=order.symbol,
                    side=order.side,
                    order_type="market",
                    quantity=order.quantity,
                    timestamp=order.timestamp,
                    strategy_id=order.strategy_id,
                    tags=order.tags
                )
                return self._simulate_market_order(market_order, execution_start)
        else:
            # Sell stop - triggers if price falls below stop price
            if current_price < order.stop_price:
                # Convert to market order
                market_order = SimulatedOrder(
                    order_id=order.order_id,
                    symbol=order.symbol,
                    side=order.side,
                    order_type="market",
                    quantity=order.quantity,
                    timestamp=order.timestamp,
                    strategy_id=order.strategy_id,
                    tags=order.tags
                )
                return self._simulate_market_order(market_order, execution_start)
        
        # Stop not triggered
        return self._create_unfilled_fill(order, execution_start)
    
    def _simulate_partial_fill(self, order: SimulatedOrder, depth, execution_start: datetime, side: str) -> SimulatedFill:
        """Simulate partial fill when insufficient liquidity."""
        total_liquidity = sum(level.quantity for level in depth.levels)
        filled_quantity = total_liquidity * 0.95  # Fill 95% of available liquidity
        
        filled_quantity, average_price, levels_consumed = depth.simulate_fill(filled_quantity)
        
        # Calculate slippage
        if side == "buy":
            reference_price = self.current_order_book.best_ask
            slippage_bps = ((average_price - reference_price) / reference_price) * 10000
        else:
            reference_price = self.current_order_book.best_bid
            slippage_bps = ((reference_price - average_price) / reference_price) * 10000
        
        execution_time = (datetime.now() - execution_start).total_seconds() * 1000
        
        return SimulatedFill(
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            filled_quantity=filled_quantity,
            remaining_quantity=order.quantity - filled_quantity,
            average_price=average_price,
            total_cost=filled_quantity * average_price,
            fill_timestamp=execution_start,
            execution_time_ms=execution_time,
            slippage_bps=slippage_bps,
            market_impact_bps=self._calculate_market_impact(filled_quantity, total_liquidity),
            levels_consumed=levels_consumed,
            liquidity_consumed=filled_quantity,
            is_partial_fill=True,
            is_completely_filled=False
        )
    
    def _create_immediate_fill(self, order: SimulatedOrder, price: float, execution_start: datetime) -> SimulatedFill:
        """Create immediate fill for limit orders."""
        execution_time = (datetime.now() - execution_start).total_seconds() * 1000
        
        return SimulatedFill(
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            filled_quantity=order.quantity,
            remaining_quantity=0.0,
            average_price=price,
            total_cost=order.quantity * price,
            fill_timestamp=execution_start,
            execution_time_ms=execution_time,
            slippage_bps=0.0,  # No slippage for limit orders at or better than market
            market_impact_bps=0.0,
            levels_consumed=1,
            liquidity_consumed=order.quantity,
            is_partial_fill=False,
            is_completely_filled=True
        )
    
    def _create_unfilled_fill(self, order: SimulatedOrder, execution_start: datetime) -> SimulatedFill:
        """Create unfilled fill for orders that would be placed in order book."""
        execution_time = (datetime.now() - execution_start).total_seconds() * 1000
        
        return SimulatedFill(
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            filled_quantity=0.0,
            remaining_quantity=order.quantity,
            average_price=0.0,
            total_cost=0.0,
            fill_timestamp=execution_start,
            execution_time_ms=execution_time,
            slippage_bps=0.0,
            market_impact_bps=0.0,
            levels_consumed=0,
            liquidity_consumed=0.0,
            is_partial_fill=False,
            is_completely_filled=False
        )
    
    def _create_rejected_fill(self, order: SimulatedOrder, execution_start: datetime) -> SimulatedFill:
        """Create rejected fill for orders that are rejected."""
        execution_time = (datetime.now() - execution_start).total_seconds() * 1000
        
        return SimulatedFill(
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            filled_quantity=0.0,
            remaining_quantity=order.quantity,
            average_price=0.0,
            total_cost=0.0,
            fill_timestamp=execution_start,
            execution_time_ms=execution_time,
            slippage_bps=0.0,
            market_impact_bps=0.0,
            levels_consumed=0,
            liquidity_consumed=0.0,
            is_partial_fill=False,
            is_completely_filled=False
        )
    
    def _calculate_market_impact(self, order_quantity: float, available_liquidity: float) -> float:
        """Calculate market impact in basis points."""
        if available_liquidity <= 0:
            return 1000.0  # Maximum impact
        
        impact_ratio = order_quantity / available_liquidity
        impact_bps = impact_ratio * self.market_impact_factor * 10000
        
        return min(impact_bps, 1000.0)  # Cap at 10%
    
    def simulate_multiple_orders(self, orders: List[SimulatedOrder]) -> List[SimulatedFill]:
        """Simulate multiple orders against the same order book."""
        results = []
        
        for order in orders:
            try:
                fill = self.simulate_order(order)
                results.append(fill)
                self.simulation_results.append(fill)
            except Exception as e:
                print(f"Error simulating order {order.order_id}: {e}")
                # Create a rejected fill
                rejected_fill = self._create_rejected_fill(order, datetime.now())
                results.append(rejected_fill)
        
        return results
    
    def get_simulation_statistics(self) -> Dict[str, Any]:
        """Get statistics about simulation results."""
        if not self.simulation_results:
            return {
                "total_orders": 0,
                "filled_orders": 0,
                "partial_fills": 0,
                "rejected_orders": 0,
                "fill_rate": 0.0,
                "avg_execution_time_ms": 0.0,
                "avg_slippage_bps": 0.0,
                "avg_market_impact_bps": 0.0
            }
        
        total_orders = len(self.simulation_results)
        filled_orders = sum(1 for fill in self.simulation_results if fill.filled_quantity > 0)
        partial_fills = sum(1 for fill in self.simulation_results if fill.is_partial_fill)
        rejected_orders = sum(1 for fill in self.simulation_results if fill.filled_quantity == 0)
        
        avg_execution_time = sum(fill.execution_time_ms for fill in self.simulation_results) / total_orders
        avg_slippage = sum(fill.slippage_bps for fill in self.simulation_results) / total_orders
        avg_market_impact = sum(fill.market_impact_bps for fill in self.simulation_results) / total_orders
        
        return {
            "total_orders": total_orders,
            "filled_orders": filled_orders,
            "partial_fills": partial_fills,
            "rejected_orders": rejected_orders,
            "fill_rate": (filled_orders / total_orders) * 100.0,
            "avg_execution_time_ms": avg_execution_time,
            "avg_slippage_bps": avg_slippage,
            "avg_market_impact_bps": avg_market_impact
        }
    
    def clear_results(self) -> None:
        """Clear simulation results."""
        self.simulation_results.clear()
    
    def create_order(self, symbol: str, side: str, order_type: str, quantity: float, **kwargs) -> SimulatedOrder:
        """Create a new simulated order."""
        self.order_counter += 1
        order_id = f"sim_{self.order_counter}_{int(datetime.now().timestamp())}"
        
        return SimulatedOrder(
            order_id=order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            timestamp=datetime.now(),
            **kwargs
        )
