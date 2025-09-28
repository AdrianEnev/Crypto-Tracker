"""
Time-Weighted Average Price (TWAP) execution engine.
Implements intelligent order slicing with market impact minimization.
"""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..order_manager.models import Order, OrderRequest, OrderType, OrderState


@dataclass
class TWAPConfig:
    """Configuration for TWAP execution."""
    duration_minutes: int = 30
    slices: int = 10
    min_slice_size: float = 0.01  # Minimum 1% of total order
    max_slice_size: float = 0.25  # Maximum 25% of total order
    slice_interval_seconds: int = 60
    market_impact_threshold: float = 0.001  # 0.1% market impact threshold
    urgency_factor: float = 1.0  # 1.0 = normal, >1.0 = more urgent
    adaptive_sizing: bool = True
    volume_participation_rate: float = 0.1  # Max 10% of average volume per slice


class TWAPExecutor:
    """
    TWAP execution engine with intelligent order slicing and market impact minimization.
    
    Features:
    - Adaptive slice sizing based on market conditions
    - Market impact modeling and minimization
    - Volume-based participation rate control
    - Dynamic timing adjustment based on volatility
    - Real-time execution monitoring and adjustment
    """
    
    def __init__(self, config: TWAPConfig):
        self.config = config
        self.active_executions: Dict[str, TWAPExecution] = {}
        self.execution_history: List[Dict] = []
        
    def execute_twap(self, 
                    symbol: str, 
                    side: str, 
                    quantity: float,
                    start_time: Optional[datetime] = None) -> str:
        """
        Execute TWAP order with optimal slice sizing.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC-USDT')
            side: Order side (BUY or SELL)
            quantity: Total quantity to execute
            start_time: When to start execution (default: now)
            
        Returns:
            Execution ID for tracking
        """
        if start_time is None:
            start_time = datetime.now()
        
        # Generate execution ID
        execution_id = f"twap_{symbol}_{side}_{int(start_time.timestamp())}"
        
        # Calculate optimal slice schedule
        slice_schedule = self._calculate_optimal_slices(symbol, side, quantity, start_time)
        
        # Create TWAP execution
        execution = TWAPExecution(
            execution_id=execution_id,
            symbol=symbol,
            side=side,
            total_quantity=quantity,
            start_time=start_time,
            slice_schedule=slice_schedule,
            config=self.config
        )
        
        self.active_executions[execution_id] = execution
        
        # Start execution
        self._start_execution(execution)
        
        return execution_id
    
    def _calculate_optimal_slices(self, 
                                symbol: str, 
                                side: str, 
                                quantity: float,
                                start_time: datetime) -> List[Dict]:
        """
        Calculate optimal slice sizes using market microstructure analysis.
        
        Returns:
            List of slice specifications with timing and sizing
        """
        # Get market data for analysis
        market_data = self._get_market_data(symbol)
        
        # Calculate base slice size
        base_slice_size = quantity / self.config.slices
        
        # Adjust for market conditions
        adjusted_slices = []
        
        for i in range(self.config.slices):
            slice_time = start_time + timedelta(seconds=i * self.config.slice_interval_seconds)
            
            # Calculate adaptive slice size
            adaptive_size = self._calculate_adaptive_slice_size(
                symbol, side, base_slice_size, slice_time, market_data
            )
            
            # Ensure slice size is within bounds
            slice_size = self._constrain_slice_size(adaptive_size, quantity)
            
            slice_spec = {
                'slice_number': i + 1,
                'scheduled_time': slice_time,
                'quantity': slice_size,
                'market_impact_estimate': self._estimate_market_impact(symbol, slice_size, market_data),
                'execution_probability': self._calculate_execution_probability(symbol, slice_size, slice_time, market_data)
            }
            
            adjusted_slices.append(slice_spec)
        
        return adjusted_slices
    
    def _calculate_adaptive_slice_size(self, 
                                     symbol: str, 
                                     side: str, 
                                     base_size: float,
                                     slice_time: datetime,
                                     market_data: Dict) -> float:
        """
        Calculate adaptive slice size based on market conditions.
        """
        # Base size
        adaptive_size = base_size
        
        # Adjust for volatility
        volatility = market_data.get('volatility', 0.02)
        volatility_factor = 1.0 + (volatility - 0.02) * 0.5  # Scale volatility impact
        adaptive_size *= volatility_factor
        
        # Adjust for time of day (liquidity patterns)
        hour = slice_time.hour
        time_factor = self._get_time_liquidity_factor(hour)
        adaptive_size *= time_factor
        
        # Adjust for recent volume
        avg_volume = market_data.get('avg_volume', 1000000)
        recent_volume = market_data.get('recent_volume', avg_volume)
        volume_factor = min(2.0, recent_volume / avg_volume)  # Cap at 2x
        adaptive_size *= volume_factor
        
        # Adjust for urgency
        adaptive_size *= self.config.urgency_factor
        
        return adaptive_size
    
    def _constrain_slice_size(self, size: float, total_quantity: float) -> float:
        """Constrain slice size to configured bounds."""
        min_size = total_quantity * self.config.min_slice_size
        max_size = total_quantity * self.config.max_slice_size
        
        return max(min_size, min(max_size, size))
    
    def _estimate_market_impact(self, symbol: str, quantity: float, market_data: Dict) -> float:
        """
        Estimate market impact of executing given quantity.
        
        Uses simplified market impact model:
        Impact = k * (quantity / avg_volume)^0.5 * volatility
        """
        avg_volume = market_data.get('avg_volume', 1000000)
        volatility = market_data.get('volatility', 0.02)
        
        # Market impact constant (varies by market)
        k = 0.001  # 0.1% impact constant
        
        # Calculate participation rate
        participation_rate = quantity / avg_volume
        
        # Estimate impact using square root model
        impact = k * math.sqrt(participation_rate) * volatility
        
        return min(impact, 0.01)  # Cap at 1% impact
    
    def _calculate_execution_probability(self, symbol: str, quantity: float, 
                                       execution_time: datetime, market_data: Dict) -> float:
        """
        Calculate probability of successful execution at given time.
        
        Based on:
        - Market depth
        - Historical fill rates
        - Time of day
        - Recent volatility
        """
        base_probability = 0.95
        
        # Adjust for market depth
        depth = market_data.get('market_depth', 1.0)
        depth_factor = min(1.0, depth)
        
        # Adjust for volatility
        volatility = market_data.get('volatility', 0.02)
        volatility_factor = max(0.5, 1.0 - (volatility - 0.02) * 10)
        
        # Adjust for time of day
        hour = execution_time.hour
        time_factor = self._get_time_execution_factor(hour)
        
        # Calculate final probability
        probability = base_probability * depth_factor * volatility_factor * time_factor
        
        return max(0.1, min(1.0, probability))
    
    def _get_time_liquidity_factor(self, hour: int) -> float:
        """Get liquidity factor based on time of day."""
        # Simplified model - higher liquidity during US/EU trading hours
        if 13 <= hour <= 22:  # US/EU overlap
            return 1.2
        elif 8 <= hour <= 16:  # EU hours
            return 1.1
        elif 22 <= hour or hour <= 2:  # US hours
            return 1.1
        else:  # Asian hours
            return 0.8
    
    def _get_time_execution_factor(self, hour: int) -> float:
        """Get execution probability factor based on time of day."""
        # Similar to liquidity but with slight differences
        if 13 <= hour <= 22:  # US/EU overlap
            return 1.0
        elif 8 <= hour <= 16:  # EU hours
            return 0.95
        elif 22 <= hour or hour <= 2:  # US hours
            return 0.9
        else:  # Asian hours
            return 0.85
    
    def _get_market_data(self, symbol: str) -> Dict:
        """
        Get market data for analysis.
        
        In a real implementation, this would fetch:
        - Recent price data
        - Volume data
        - Order book depth
        - Volatility metrics
        """
        # Mock market data for demonstration
        return {
            'symbol': symbol,
            'price': 50000.0,
            'volatility': 0.025,  # 2.5% daily volatility
            'avg_volume': 1500000,
            'recent_volume': 1200000,
            'market_depth': 1.2,
            'bid_ask_spread': 0.0002  # 0.02%
        }
    
    def _start_execution(self, execution: 'TWAPExecution') -> None:
        """Start TWAP execution process."""
        execution.status = 'active'
        execution.start_time = datetime.now()
        
        # Schedule first slice
        self._schedule_next_slice(execution)
    
    def _schedule_next_slice(self, execution: 'TWAPExecution') -> None:
        """Schedule next slice execution."""
        if execution.current_slice >= len(execution.slice_schedule):
            # All slices completed
            self._complete_execution(execution)
            return
        
        current_slice = execution.slice_schedule[execution.current_slice]
        
        # Create order for this slice
        order_request = OrderRequest(
            symbol=execution.symbol,
            side=execution.side,
            order_type=OrderType.LIMIT,
            quantity=current_slice['quantity'],
            price=self._calculate_slice_price(execution.symbol, execution.side),
            time_in_force='GTC'
        )
        
        # Submit order (in real implementation, this would go to order manager)
        order_id = f"{execution.execution_id}_slice_{execution.current_slice + 1}"
        
        # Simulate order creation
        order = Order(
            id=order_id,
            client_order_id=order_id,
            symbol=execution.symbol,
            side=execution.side,
            order_type=OrderType.LIMIT,
            state=OrderState.PENDING,
            quantity=current_slice['quantity'],
            price=order_request.price,
            stop_price=None,
            time_in_force=order_request.time_in_force,
            exchange="mock_exchange"
        )
        
        execution.active_orders.append(order)
        
        # Schedule next slice
        next_slice_time = current_slice['scheduled_time']
        execution.current_slice += 1
        
        # In real implementation, schedule timer for next slice
        self._schedule_slice_execution(execution, next_slice_time)
    
    def _calculate_slice_price(self, symbol: str, side: str) -> float:
        """
        Calculate optimal price for slice execution.
        
        Uses smart pricing to improve fill probability while minimizing market impact.
        """
        market_data = self._get_market_data(symbol)
        mid_price = market_data['price']
        spread = market_data['bid_ask_spread']
        
        if side == "buy":
            # For buy orders, price slightly above mid to improve fill probability
            return mid_price * (1 + spread * 0.3)
        else:
            # For sell orders, price slightly below mid
            return mid_price * (1 - spread * 0.3)
    
    def _schedule_slice_execution(self, execution: 'TWAPExecution', execution_time: datetime) -> None:
        """Schedule slice execution at specified time."""
        # In real implementation, this would use a scheduler
        # For now, just log the scheduling
        print(f"Scheduled slice {execution.current_slice} execution at {execution_time}")
    
    def _complete_execution(self, execution: 'TWAPExecution') -> None:
        """Complete TWAP execution and generate report."""
        execution.status = 'completed'
        execution.end_time = datetime.now()
        
        # Calculate execution metrics
        execution_metrics = self._calculate_execution_metrics(execution)
        
        # Store execution history
        self.execution_history.append({
            'execution_id': execution.execution_id,
            'symbol': execution.symbol,
            'side': execution.side.value,
            'total_quantity': execution.total_quantity,
            'executed_quantity': execution_metrics['executed_quantity'],
            'execution_time': (execution.end_time - execution.start_time).total_seconds(),
            'avg_execution_price': execution_metrics['avg_execution_price'],
            'market_impact': execution_metrics['market_impact'],
            'slippage': execution_metrics['slippage']
        })
        
        # Remove from active executions
        if execution.execution_id in self.active_executions:
            del self.active_executions[execution.execution_id]
    
    def _calculate_execution_metrics(self, execution: 'TWAPExecution') -> Dict:
        """Calculate execution quality metrics."""
        # Mock implementation - in real system would use actual fill data
        return {
            'executed_quantity': execution.total_quantity * 0.98,  # 98% filled
            'avg_execution_price': self._get_market_data(execution.symbol)['price'] * 1.001,
            'market_impact': 0.0005,  # 0.05% impact
            'slippage': 0.0003,  # 0.03% slippage
            'fill_rate': 0.98,
            'num_fills': len(execution.active_orders)
        }
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict]:
        """Get current status of TWAP execution."""
        if execution_id in self.active_executions:
            execution = self.active_executions[execution_id]
            return {
                'execution_id': execution_id,
                'status': execution.status,
                'progress': execution.current_slice / len(execution.slice_schedule),
                'executed_quantity': sum(order.filled_quantity for order in execution.active_orders),
                'remaining_quantity': execution.total_quantity - sum(order.filled_quantity for order in execution.active_orders)
            }
        return None
    
    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel active TWAP execution."""
        if execution_id in self.active_executions:
            execution = self.active_executions[execution_id]
            execution.status = 'cancelled'
            
            # Cancel all active orders
            for order in execution.active_orders:
                if order.state in [OrderState.PENDING, OrderState.PARTIALLY_FILLED]:
                    order.state = OrderState.CANCELLED
            
            del self.active_executions[execution_id]
            return True
        return False
    
    def get_execution_history(self) -> List[Dict]:
        """Get history of completed TWAP executions."""
        return self.execution_history.copy()


class TWAPExecution:
    """Represents an active TWAP execution."""
    
    def __init__(self, execution_id: str, symbol: str, side: str, 
                 total_quantity: float, start_time: datetime, 
                 slice_schedule: List[Dict], config: TWAPConfig):
        self.execution_id = execution_id
        self.symbol = symbol
        self.side = side
        self.total_quantity = total_quantity
        self.start_time = start_time
        self.end_time: Optional[datetime] = None
        self.slice_schedule = slice_schedule
        self.config = config
        self.status = 'pending'
        self.current_slice = 0
        self.active_orders: List[Order] = []
        self.completed_orders: List[Order] = []
