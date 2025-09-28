"""
Volume-Weighted Average Price (VWAP) execution engine.
Implements intelligent order slicing based on historical volume patterns.
"""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..order_manager.models import Order, OrderRequest, OrderType, OrderState


@dataclass
class VWAPConfig:
    """Configuration for VWAP execution."""
    duration_minutes: int = 60
    slices: int = 20
    participation_rate: float = 0.15  # Max 15% of average volume per slice
    min_slice_size: float = 0.005  # Minimum 0.5% of total order
    max_slice_size: float = 0.20  # Maximum 20% of total order
    volume_lookback_days: int = 30  # Days of historical volume data to analyze
    adaptive_timing: bool = True
    market_hours_only: bool = True
    urgency_factor: float = 1.0


class VWAPExecutor:
    """
    VWAP execution engine with volume-based order slicing.
    
    Features:
    - Historical volume pattern analysis
    - Dynamic slice timing based on volume profiles
    - Market hours optimization
    - Participation rate control
    - Real-time volume monitoring and adjustment
    """
    
    def __init__(self, config: VWAPConfig):
        self.config = config
        self.active_executions: Dict[str, VWAPExecution] = {}
        self.execution_history: List[Dict] = []
        self.volume_profiles: Dict[str, pd.DataFrame] = {}
        
    def execute_vwap(self, 
                    symbol: str, 
                    side: str, 
                    quantity: float,
                    start_time: Optional[datetime] = None) -> str:
        """
        Execute VWAP order with volume-based slice sizing.
        
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
        execution_id = f"vwap_{symbol}_{side}_{int(start_time.timestamp())}"
        
        # Get volume profile for symbol
        volume_profile = self._get_volume_profile(symbol)
        
        # Calculate VWAP slice schedule
        slice_schedule = self._calculate_vwap_slices(symbol, side, quantity, start_time, volume_profile)
        
        # Create VWAP execution
        execution = VWAPExecution(
            execution_id=execution_id,
            symbol=symbol,
            side=side,
            total_quantity=quantity,
            start_time=start_time,
            slice_schedule=slice_schedule,
            volume_profile=volume_profile,
            config=self.config
        )
        
        self.active_executions[execution_id] = execution
        
        # Start execution
        self._start_execution(execution)
        
        return execution_id
    
    def _get_volume_profile(self, symbol: str) -> pd.DataFrame:
        """
        Get historical volume profile for symbol.
        
        Returns DataFrame with columns:
        - hour: Hour of day (0-23)
        - avg_volume: Average volume in this hour
        - volume_std: Standard deviation
        - volume_percentile_25/50/75: Volume percentiles
        - participation_ratio: Optimal participation ratio
        """
        if symbol in self.volume_profiles:
            return self.volume_profiles[symbol]
        
        # Generate mock volume profile (in real implementation, fetch from database)
        volume_profile = self._generate_mock_volume_profile()
        self.volume_profiles[symbol] = volume_profile
        
        return volume_profile
    
    def _generate_mock_volume_profile(self) -> pd.DataFrame:
        """Generate mock volume profile for demonstration."""
        hours = list(range(24))
        
        # Create realistic volume pattern (higher during US/EU hours)
        base_volumes = []
        for hour in hours:
            if 13 <= hour <= 22:  # US/EU overlap - highest volume
                base_volume = np.random.normal(1.5, 0.2)
            elif 8 <= hour <= 16:  # EU hours - medium volume
                base_volume = np.random.normal(1.0, 0.15)
            elif 22 <= hour or hour <= 2:  # US hours - medium-high volume
                base_volume = np.random.normal(1.2, 0.18)
            else:  # Asian hours - lower volume
                base_volume = np.random.normal(0.6, 0.1)
            
            base_volumes.append(max(0.1, base_volume))  # Ensure positive
        
        # Create DataFrame
        volume_profile = pd.DataFrame({
            'hour': hours,
            'avg_volume': base_volumes,
            'volume_std': [v * 0.3 for v in base_volumes],  # 30% std dev
            'volume_percentile_25': [v * 0.7 for v in base_volumes],
            'volume_percentile_50': base_volumes,
            'volume_percentile_75': [v * 1.3 for v in base_volumes],
            'participation_ratio': [min(0.2, v * 0.1) for v in base_volumes]
        })
        
        return volume_profile
    
    def _calculate_vwap_slices(self, 
                              symbol: str, 
                              side: str, 
                              quantity: float,
                              start_time: datetime,
                              volume_profile: pd.DataFrame) -> List[Dict]:
        """
        Calculate VWAP slice schedule based on volume profile.
        """
        # Determine execution window
        end_time = start_time + timedelta(minutes=self.config.duration_minutes)
        
        # Calculate total expected volume in execution window
        total_expected_volume = self._calculate_expected_volume(start_time, end_time, volume_profile)
        
        # Calculate target participation rate
        target_participation = min(self.config.participation_rate, 
                                  quantity / total_expected_volume)
        
        # Generate slice schedule
        slices = []
        current_time = start_time
        slice_duration = timedelta(minutes=self.config.duration_minutes / self.config.slices)
        
        remaining_quantity = quantity
        
        for i in range(self.config.slices):
            slice_end_time = current_time + slice_duration
            
            # Calculate expected volume in this slice period
            slice_volume = self._calculate_expected_volume(current_time, slice_end_time, volume_profile)
            
            # Calculate slice quantity based on volume participation
            slice_quantity = min(
                remaining_quantity,
                slice_volume * target_participation,
                quantity * self.config.max_slice_size
            )
            
            # Ensure minimum slice size
            slice_quantity = max(slice_quantity, quantity * self.config.min_slice_size)
            
            # Adjust for urgency factor
            slice_quantity *= self.config.urgency_factor
            
            slice_spec = {
                'slice_number': i + 1,
                'start_time': current_time,
                'end_time': slice_end_time,
                'quantity': slice_quantity,
                'expected_volume': slice_volume,
                'participation_rate': slice_quantity / slice_volume if slice_volume > 0 else 0,
                'volume_weight': slice_volume / total_expected_volume if total_expected_volume > 0 else 0
            }
            
            slices.append(slice_spec)
            
            remaining_quantity -= slice_quantity
            current_time = slice_end_time
            
            if remaining_quantity <= 0:
                break
        
        return slices
    
    def _calculate_expected_volume(self, start_time: datetime, end_time: datetime, 
                                 volume_profile: pd.DataFrame) -> float:
        """Calculate expected volume in given time window."""
        total_volume = 0.0
        
        current_time = start_time
        while current_time < end_time:
            hour = current_time.hour
            
            # Get volume for this hour
            hour_data = volume_profile[volume_profile['hour'] == hour]
            if not hour_data.empty:
                avg_volume = hour_data['avg_volume'].iloc[0]
                
                # Calculate fraction of hour covered
                hour_start = current_time.replace(minute=0, second=0, microsecond=0)
                hour_end = hour_start + timedelta(hours=1)
                
                period_start = max(current_time, hour_start)
                period_end = min(end_time, hour_end)
                
                fraction = (period_end - period_start).total_seconds() / 3600.0
                total_volume += avg_volume * fraction
            
            current_time = (current_time.replace(minute=0, second=0, microsecond=0) + 
                          timedelta(hours=1))
        
        return total_volume
    
    def _start_execution(self, execution: 'VWAPExecution') -> None:
        """Start VWAP execution process."""
        execution.status = 'active'
        execution.start_time = datetime.now()
        
        # Schedule first slice
        self._schedule_next_slice(execution)
    
    def _schedule_next_slice(self, execution: 'VWAPExecution') -> None:
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
        
        # Schedule next slice based on VWAP timing
        next_slice_time = current_slice['end_time']
        execution.current_slice += 1
        
        # In real implementation, schedule timer for next slice
        self._schedule_slice_execution(execution, next_slice_time)
    
    def _calculate_slice_price(self, symbol: str, side: str) -> float:
        """Calculate optimal price for slice execution."""
        # Get current market data
        market_data = self._get_market_data(symbol)
        mid_price = market_data['price']
        spread = market_data['bid_ask_spread']
        
        if side == "buy":
            # For VWAP, use more aggressive pricing to match volume timing
            return mid_price * (1 + spread * 0.2)
        else:
            return mid_price * (1 - spread * 0.2)
    
    def _get_market_data(self, symbol: str) -> Dict:
        """Get current market data."""
        # Mock implementation
        return {
            'symbol': symbol,
            'price': 50000.0,
            'bid_ask_spread': 0.0002,
            'volume_24h': 2000000
        }
    
    def _schedule_slice_execution(self, execution: 'VWAPExecution', execution_time: datetime) -> None:
        """Schedule slice execution at specified time."""
        # In real implementation, this would use a scheduler
        print(f"Scheduled VWAP slice {execution.current_slice} execution at {execution_time}")
    
    def _complete_execution(self, execution: 'VWAPExecution') -> None:
        """Complete VWAP execution and generate report."""
        execution.status = 'completed'
        execution.end_time = datetime.now()
        
        # Calculate VWAP metrics
        vwap_metrics = self._calculate_vwap_metrics(execution)
        
        # Store execution history
        self.execution_history.append({
            'execution_id': execution.execution_id,
            'symbol': execution.symbol,
            'side': execution.side.value,
            'total_quantity': execution.total_quantity,
            'executed_quantity': vwap_metrics['executed_quantity'],
            'execution_time': (execution.end_time - execution.start_time).total_seconds(),
            'avg_execution_price': vwap_metrics['avg_execution_price'],
            'vwap_deviation': vwap_metrics['vwap_deviation'],
            'volume_participation': vwap_metrics['volume_participation'],
            'market_impact': vwap_metrics['market_impact']
        })
        
        # Remove from active executions
        if execution.execution_id in self.active_executions:
            del self.active_executions[execution.execution_id]
    
    def _calculate_vwap_metrics(self, execution: 'VWAPExecution') -> Dict:
        """Calculate VWAP execution quality metrics."""
        # Calculate volume-weighted average price
        total_volume = 0
        total_value = 0
        
        for order in execution.active_orders:
            if order.state == OrderState.FILLED:
                total_volume += order.filled_quantity
                total_value += order.filled_quantity * order.filled_price
        
        vwap = total_value / total_volume if total_volume > 0 else 0
        
        # Calculate market VWAP for comparison
        market_vwap = self._calculate_market_vwap(execution.symbol, 
                                                 execution.start_time, 
                                                 execution.end_time)
        
        # Calculate deviation from market VWAP
        vwap_deviation = (vwap - market_vwap) / market_vwap if market_vwap > 0 else 0
        
        return {
            'executed_quantity': total_volume,
            'avg_execution_price': vwap,
            'market_vwap': market_vwap,
            'vwap_deviation': vwap_deviation,
            'volume_participation': total_volume / execution.total_quantity if execution.total_quantity > 0 else 0,
            'market_impact': abs(vwap_deviation) * 0.5  # Simplified impact calculation
        }
    
    def _calculate_market_vwap(self, symbol: str, start_time: datetime, end_time: datetime) -> float:
        """Calculate market VWAP for comparison."""
        # Mock implementation - in real system would fetch actual market data
        return 50000.0 * 1.001  # Slightly higher than mid price
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict]:
        """Get current status of VWAP execution."""
        if execution_id in self.active_executions:
            execution = self.active_executions[execution_id]
            return {
                'execution_id': execution_id,
                'status': execution.status,
                'progress': execution.current_slice / len(execution.slice_schedule),
                'executed_quantity': sum(order.filled_quantity for order in execution.active_orders),
                'remaining_quantity': execution.total_quantity - sum(order.filled_quantity for order in execution.active_orders),
                'current_vwap': self._calculate_current_vwap(execution)
            }
        return None
    
    def _calculate_current_vwap(self, execution: 'VWAPExecution') -> float:
        """Calculate current VWAP for active execution."""
        total_volume = 0
        total_value = 0
        
        for order in execution.active_orders:
            if order.state == OrderState.FILLED:
                total_volume += order.filled_quantity
                total_value += order.filled_quantity * order.filled_price
        
        return total_value / total_volume if total_volume > 0 else 0
    
    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel active VWAP execution."""
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
        """Get history of completed VWAP executions."""
        return self.execution_history.copy()


class VWAPExecution:
    """Represents an active VWAP execution."""
    
    def __init__(self, execution_id: str, symbol: str, side: str, 
                 total_quantity: float, start_time: datetime, 
                 slice_schedule: List[Dict], volume_profile: pd.DataFrame, 
                 config: VWAPConfig):
        self.execution_id = execution_id
        self.symbol = symbol
        self.side = side
        self.total_quantity = total_quantity
        self.start_time = start_time
        self.end_time: Optional[datetime] = None
        self.slice_schedule = slice_schedule
        self.volume_profile = volume_profile
        self.config = config
        self.status = 'pending'
        self.current_slice = 0
        self.active_orders: List[Order] = []
        self.completed_orders: List[Order] = []
