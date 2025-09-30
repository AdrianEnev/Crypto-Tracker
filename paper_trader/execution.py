"""
Execution Simulator

Simulates realistic order execution with configurable slippage, fees,
latency, and market impact models for paper trading.
"""

from __future__ import annotations

import asyncio
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Callable
import numpy as np

from src.order_manager.models import Order, OrderRequest, OrderResult, OrderState, OrderType


class SlippageType(Enum):
    """Types of slippage models."""
    
    FIXED = "fixed"  # Fixed percentage slippage
    LINEAR = "linear"  # Linear slippage based on order size
    SQUARE_ROOT = "square_root"  # Square root slippage (more realistic)
    ORDERBOOK_DEPTH = "orderbook_depth"  # Based on order book depth


class FeeType(Enum):
    """Types of fee structures."""
    
    PERCENTAGE = "percentage"  # Percentage of trade value
    FIXED = "fixed"  # Fixed fee per trade
    TIERED = "tiered"  # Tiered fee structure based on volume


@dataclass
class SlippageConfig:
    """Configuration for slippage simulation."""
    
    slippage_type: SlippageType = SlippageType.SQUARE_ROOT
    base_slippage_bps: float = 5.0  # Base slippage in basis points
    max_slippage_bps: float = 50.0  # Maximum slippage in basis points
    volatility_multiplier: float = 1.0  # Multiplier based on market volatility
    order_size_threshold: float = 10000.0  # USD threshold for size-based slippage
    
    # Order book depth simulation
    orderbook_depth_levels: int = 5
    depth_impact_factor: float = 0.1


@dataclass
class FeeConfig:
    """Configuration for fee simulation."""
    
    fee_type: FeeType = FeeType.PERCENTAGE
    maker_fee_bps: float = 5.0  # Maker fee in basis points
    taker_fee_bps: float = 10.0  # Taker fee in basis points
    fixed_fee_usd: float = 0.0  # Fixed fee in USD
    min_fee_usd: float = 0.01  # Minimum fee in USD
    max_fee_usd: float = 100.0  # Maximum fee in USD
    
    # Tiered fee structure
    volume_tiers: List[Tuple[float, float]] = field(default_factory=lambda: [
        (0, 10.0),      # 0-1M volume: 10 bps
        (1000000, 8.0), # 1M-10M volume: 8 bps
        (10000000, 5.0), # 10M+ volume: 5 bps
    ])


@dataclass
class LatencyConfig:
    """Configuration for execution latency simulation."""
    
    min_latency_ms: float = 50.0
    max_latency_ms: float = 500.0
    mean_latency_ms: float = 200.0
    std_latency_ms: float = 100.0
    network_jitter_ms: float = 20.0


class SlippageModel(ABC):
    """Abstract base class for slippage models."""
    
    @abstractmethod
    def calculate_slippage(
        self, 
        order_size_usd: float, 
        current_price: float,
        side: str,
        orderbook: Optional[Dict[str, Any]] = None,
        volatility: Optional[float] = None
    ) -> float:
        """Calculate slippage for an order."""
        pass


class FixedSlippageModel(SlippageModel):
    """Fixed percentage slippage model."""
    
    def __init__(self, slippage_bps: float):
        self.slippage_bps = slippage_bps
    
    def calculate_slippage(
        self, 
        order_size_usd: float, 
        current_price: float,
        side: str,
        orderbook: Optional[Dict[str, Any]] = None,
        volatility: Optional[float] = None
    ) -> float:
        return self.slippage_bps / 10000.0


class LinearSlippageModel(SlippageModel):
    """Linear slippage model based on order size."""
    
    def __init__(self, config: SlippageConfig):
        self.config = config
    
    def calculate_slippage(
        self, 
        order_size_usd: float, 
        current_price: float,
        side: str,
        orderbook: Optional[Dict[str, Any]] = None,
        volatility: Optional[float] = None
    ) -> float:
        base_slippage = self.config.base_slippage_bps / 10000.0
        
        # Linear increase with order size
        size_factor = min(order_size_usd / self.config.order_size_threshold, 1.0)
        slippage = base_slippage * (1.0 + size_factor)
        
        return min(slippage, self.config.max_slippage_bps / 10000.0)


class SquareRootSlippageModel(SlippageModel):
    """Square root slippage model (more realistic for large orders)."""
    
    def __init__(self, config: SlippageConfig):
        self.config = config
    
    def calculate_slippage(
        self, 
        order_size_usd: float, 
        current_price: float,
        side: str,
        orderbook: Optional[Dict[str, Any]] = None,
        volatility: Optional[float] = None
    ) -> float:
        base_slippage = self.config.base_slippage_bps / 10000.0
        
        # Square root increase with order size (more realistic)
        size_factor = np.sqrt(order_size_usd / self.config.order_size_threshold)
        slippage = base_slippage * (1.0 + size_factor)
        
        # Apply volatility multiplier
        if volatility is not None:
            slippage *= (1.0 + volatility * self.config.volatility_multiplier)
        
        return min(slippage, self.config.max_slippage_bps / 10000.0)


class OrderBookDepthSlippageModel(SlippageModel):
    """Slippage model based on order book depth."""
    
    def __init__(self, config: SlippageConfig):
        self.config = config
    
    def calculate_slippage(
        self, 
        order_size_usd: float, 
        current_price: float,
        side: str,
        orderbook: Optional[Dict[str, Any]] = None,
        volatility: Optional[float] = None
    ) -> float:
        if orderbook is None:
            # Fallback to square root model
            return SquareRootSlippageModel(self.config).calculate_slippage(
                order_size_usd, current_price, side, orderbook, volatility
            )
        
        # Calculate slippage based on order book depth
        order_size_base = order_size_usd / current_price
        
        if side == "buy":
            asks = orderbook.get("asks", [])
            if not asks:
                return self.config.base_slippage_bps / 10000.0
            
            cumulative_size = 0.0
            cumulative_cost = 0.0
            
            for price, size in asks[:self.config.orderbook_depth_levels]:
                if cumulative_size >= order_size_base:
                    break
                
                fill_size = min(size, order_size_base - cumulative_size)
                cumulative_size += fill_size
                cumulative_cost += fill_size * price
            
            if cumulative_size > 0:
                avg_price = cumulative_cost / cumulative_size
                slippage = (avg_price - current_price) / current_price
                return max(slippage, self.config.base_slippage_bps / 10000.0)
        
        else:  # sell
            bids = orderbook.get("bids", [])
            if not bids:
                return self.config.base_slippage_bps / 10000.0
            
            cumulative_size = 0.0
            cumulative_cost = 0.0
            
            for price, size in bids[:self.config.orderbook_depth_levels]:
                if cumulative_size >= order_size_base:
                    break
                
                fill_size = min(size, order_size_base - cumulative_size)
                cumulative_size += fill_size
                cumulative_cost += fill_size * price
            
            if cumulative_size > 0:
                avg_price = cumulative_cost / cumulative_size
                slippage = (current_price - avg_price) / current_price
                return max(slippage, self.config.base_slippage_bps / 10000.0)
        
        return self.config.base_slippage_bps / 10000.0


class FeeModel:
    """Fee calculation model."""
    
    def __init__(self, config: FeeConfig):
        self.config = config
    
    def calculate_fee(
        self, 
        order_size_usd: float, 
        is_maker: bool = False,
        monthly_volume_usd: float = 0.0
    ) -> float:
        """Calculate trading fee."""
        
        if self.config.fee_type == FeeType.FIXED:
            fee = self.config.fixed_fee_usd
        
        elif self.config.fee_type == FeeType.PERCENTAGE:
            fee_rate = self.config.maker_fee_bps if is_maker else self.config.taker_fee_bps
            fee = order_size_usd * (fee_rate / 10000.0)
        
        elif self.config.fee_type == FeeType.TIERED:
            fee_rate = self._get_tiered_fee_rate(monthly_volume_usd)
            fee = order_size_usd * (fee_rate / 10000.0)
        
        else:
            fee = order_size_usd * (self.config.taker_fee_bps / 10000.0)
        
        # Apply min/max limits
        fee = max(fee, self.config.min_fee_usd)
        fee = min(fee, self.config.max_fee_usd)
        
        return fee
    
    def _get_tiered_fee_rate(self, monthly_volume_usd: float) -> float:
        """Get fee rate based on monthly volume tier."""
        for volume_threshold, fee_rate in reversed(self.config.volume_tiers):
            if monthly_volume_usd >= volume_threshold:
                return fee_rate
        
        return self.config.taker_fee_bps


class ExecutionSimulator:
    """Simulates realistic order execution with slippage, fees, and latency."""
    
    def __init__(
        self,
        slippage_config: SlippageConfig,
        fee_config: FeeConfig,
        latency_config: LatencyConfig,
        random_seed: Optional[int] = None
    ):
        self.slippage_config = slippage_config
        self.fee_config = fee_config
        self.latency_config = latency_config
        
        # Initialize random number generator
        if random_seed is not None:
            random.seed(random_seed)
            np.random.seed(random_seed)
        
        # Initialize slippage model
        self.slippage_model = self._create_slippage_model()
        self.fee_model = FeeModel(fee_config)
        
        # Execution statistics
        self.total_orders = 0
        self.total_fees = 0.0
        self.total_slippage = 0.0
    
    def _create_slippage_model(self) -> SlippageModel:
        """Create slippage model based on configuration."""
        if self.slippage_config.slippage_type == SlippageType.FIXED:
            return FixedSlippageModel(self.slippage_config.base_slippage_bps)
        elif self.slippage_config.slippage_type == SlippageType.LINEAR:
            return LinearSlippageModel(self.slippage_config)
        elif self.slippage_config.slippage_type == SlippageType.SQUARE_ROOT:
            return SquareRootSlippageModel(self.slippage_config)
        elif self.slippage_config.slippage_type == SlippageType.ORDERBOOK_DEPTH:
            return OrderBookDepthSlippageModel(self.slippage_config)
        else:
            return SquareRootSlippageModel(self.slippage_config)
    
    async def simulate_execution(
        self,
        order_request: OrderRequest,
        current_price: float,
        orderbook: Optional[Dict[str, Any]] = None,
        volatility: Optional[float] = None
    ) -> Tuple[float, float, float]:
        """
        Simulate order execution and return (execution_price, fee, slippage).
        
        Args:
            order_request: The order to execute
            current_price: Current market price
            orderbook: Optional order book data
            volatility: Optional market volatility
            
        Returns:
            Tuple of (execution_price, fee_usd, slippage_pct)
        """
        
        # Simulate network latency
        await self._simulate_latency()
        
        # Calculate slippage
        order_size_usd = order_request.quantity * (order_request.price or current_price)
        slippage_pct = self.slippage_model.calculate_slippage(
            order_size_usd, current_price, order_request.side, orderbook, volatility
        )
        
        # Calculate execution price
        if order_request.side == "buy":
            execution_price = current_price * (1.0 + slippage_pct)
        else:
            execution_price = current_price * (1.0 - slippage_pct)
        
        # Calculate fee
        is_maker = order_request.order_type == OrderType.LIMIT
        fee_usd = self.fee_model.calculate_fee(order_size_usd, is_maker)
        
        # Update statistics
        self.total_orders += 1
        self.total_fees += fee_usd
        self.total_slippage += slippage_pct * order_size_usd
        
        return execution_price, fee_usd, slippage_pct
    
    async def _simulate_latency(self):
        """Simulate network latency."""
        # Generate latency using normal distribution
        latency_ms = np.random.normal(
            self.latency_config.mean_latency_ms,
            self.latency_config.std_latency_ms
        )
        
        # Apply min/max bounds
        latency_ms = max(latency_ms, self.latency_config.min_latency_ms)
        latency_ms = min(latency_ms, self.latency_config.max_latency_ms)
        
        # Add network jitter
        jitter_ms = random.uniform(-self.latency_config.network_jitter_ms, 
                                 self.latency_config.network_jitter_ms)
        total_latency_ms = latency_ms + jitter_ms
        
        # Simulate delay
        await asyncio.sleep(total_latency_ms / 1000.0)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get execution statistics."""
        return {
            "total_orders": self.total_orders,
            "total_fees_usd": self.total_fees,
            "total_slippage_usd": self.total_slippage,
            "avg_fee_per_order": self.total_fees / max(self.total_orders, 1),
            "avg_slippage_per_order": self.total_slippage / max(self.total_orders, 1),
        }
