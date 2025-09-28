"""
Market impact modeling for execution cost estimation.
Implements various market impact models for order sizing optimization.
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np


@dataclass
class MarketImpactConfig:
    """Configuration for market impact modeling."""
    model_type: str = "square_root"  # "square_root", "linear", "power_law"
    impact_constant: float = 0.001  # Base impact constant
    participation_rate_exponent: float = 0.5  # Exponent for participation rate
    volatility_multiplier: float = 1.0  # Volatility impact multiplier
    time_decay_factor: float = 0.1  # Impact decay over time
    permanent_impact_ratio: float = 0.5  # Ratio of permanent vs temporary impact


@dataclass
class MarketImpactResult:
    """Market impact calculation result."""
    temporary_impact: float  # Temporary impact (reverts quickly)
    permanent_impact: float  # Permanent impact (persists)
    total_impact: float  # Total impact
    confidence_interval: Tuple[float, float]  # 95% confidence interval
    impact_attribution: Dict[str, float]  # Breakdown by factors


class MarketImpactModel:
    """
    Market impact modeling system for execution cost estimation.
    
    Implements multiple impact models:
    - Square root model (Almgren-Chriss)
    - Linear model
    - Power law model
    - Adaptive model based on market conditions
    """
    
    def __init__(self, config: MarketImpactConfig):
        self.config = config
        self.historical_data: Dict[str, List[float]] = {}
        
    def calculate_market_impact(self, 
                              symbol: str,
                              order_size: float,
                              current_price: float,
                              market_volume: float,
                              volatility: float,
                              execution_time_minutes: Optional[int] = None) -> MarketImpactResult:
        """
        Calculate market impact for given order parameters.
        
        Args:
            symbol: Trading symbol
            order_size: Size of order in base currency
            current_price: Current market price
            market_volume: Average daily market volume
            volatility: Daily price volatility (standard deviation)
            execution_time_minutes: Expected execution time in minutes
            
        Returns:
            Market impact calculation result
        """
        # Calculate participation rate
        participation_rate = order_size / market_volume
        
        # Get model-specific impact calculation
        if self.config.model_type == "square_root":
            impact = self._square_root_model(participation_rate, volatility)
        elif self.config.model_type == "linear":
            impact = self._linear_model(participation_rate, volatility)
        elif self.config.model_type == "power_law":
            impact = self._power_law_model(participation_rate, volatility)
        else:
            impact = self._adaptive_model(participation_rate, volatility, symbol)
        
        # Separate temporary and permanent impact
        permanent_impact = impact * self.config.permanent_impact_ratio
        temporary_impact = impact * (1 - self.config.permanent_impact_ratio)
        
        # Adjust for execution time if provided
        if execution_time_minutes:
            time_adjustment = self._calculate_time_adjustment(execution_time_minutes)
            temporary_impact *= time_adjustment
            permanent_impact *= (1 - time_adjustment * 0.5)
        
        total_impact = temporary_impact + permanent_impact
        
        # Calculate confidence interval
        confidence_interval = self._calculate_confidence_interval(total_impact, volatility)
        
        # Create impact attribution
        impact_attribution = {
            'participation_rate': participation_rate,
            'volatility_contribution': volatility * self.config.volatility_multiplier,
            'base_impact': self.config.impact_constant,
            'model_contribution': impact,
            'time_adjustment': time_adjustment if execution_time_minutes else 1.0
        }
        
        return MarketImpactResult(
            temporary_impact=temporary_impact,
            permanent_impact=permanent_impact,
            total_impact=total_impact,
            confidence_interval=confidence_interval,
            impact_attribution=impact_attribution
        )
    
    def _square_root_model(self, participation_rate: float, volatility: float) -> float:
        """
        Square root market impact model (Almgren-Chriss).
        
        Impact = k * sqrt(participation_rate) * volatility
        """
        if participation_rate <= 0:
            return 0.0
        
        impact = (self.config.impact_constant * 
                 math.sqrt(participation_rate) * 
                 volatility * 
                 self.config.volatility_multiplier)
        
        return min(impact, 0.1)  # Cap at 10% impact
    
    def _linear_model(self, participation_rate: float, volatility: float) -> float:
        """
        Linear market impact model.
        
        Impact = k * participation_rate * volatility
        """
        impact = (self.config.impact_constant * 
                 participation_rate * 
                 volatility * 
                 self.config.volatility_multiplier)
        
        return min(impact, 0.1)  # Cap at 10% impact
    
    def _power_law_model(self, participation_rate: float, volatility: float) -> float:
        """
        Power law market impact model.
        
        Impact = k * participation_rate^alpha * volatility
        """
        if participation_rate <= 0:
            return 0.0
        
        impact = (self.config.impact_constant * 
                 (participation_rate ** self.config.participation_rate_exponent) * 
                 volatility * 
                 self.config.volatility_multiplier)
        
        return min(impact, 0.1)  # Cap at 10% impact
    
    def _adaptive_model(self, participation_rate: float, volatility: float, symbol: str) -> float:
        """
        Adaptive market impact model based on historical data and market conditions.
        """
        # Get historical impact data for symbol
        historical_impacts = self.historical_data.get(symbol, [])
        
        if len(historical_impacts) < 10:
            # Fall back to square root model if insufficient data
            return self._square_root_model(participation_rate, volatility)
        
        # Calculate adaptive parameters based on historical data
        historical_volatility = np.std(historical_impacts)
        historical_mean = np.mean(historical_impacts)
        
        # Adjust base impact constant based on historical performance
        adaptive_constant = self.config.impact_constant * (1 + historical_volatility)
        
        # Use weighted combination of models
        square_root_impact = self._square_root_model(participation_rate, volatility)
        linear_impact = self._linear_model(participation_rate, volatility)
        
        # Weight based on historical accuracy
        square_root_weight = 0.7  # Default weight
        linear_weight = 0.3
        
        # Adjust weights based on historical performance
        if historical_mean > 0.005:  # High historical impact
            square_root_weight = 0.8
            linear_weight = 0.2
        elif historical_mean < 0.002:  # Low historical impact
            square_root_weight = 0.6
            linear_weight = 0.4
        
        adaptive_impact = (square_root_weight * square_root_impact + 
                          linear_weight * linear_impact)
        
        return min(adaptive_impact, 0.1)  # Cap at 10% impact
    
    def _calculate_time_adjustment(self, execution_time_minutes: int) -> float:
        """
        Calculate impact adjustment based on execution time.
        
        Longer execution times reduce temporary impact but may increase permanent impact.
        """
        if execution_time_minutes <= 0:
            return 1.0
        
        # Time decay factor - impact reduces with longer execution time
        time_adjustment = 1.0 - (execution_time_minutes * self.config.time_decay_factor / 60)
        
        return max(0.1, min(1.0, time_adjustment))  # Keep between 0.1 and 1.0
    
    def _calculate_confidence_interval(self, impact: float, volatility: float) -> Tuple[float, float]:
        """
        Calculate 95% confidence interval for impact estimate.
        """
        # Standard error based on volatility
        standard_error = impact * volatility * 0.5
        
        # 95% confidence interval (approximately ±2 standard deviations)
        margin_of_error = 2 * standard_error
        
        lower_bound = max(0, impact - margin_of_error)
        upper_bound = impact + margin_of_error
        
        return (lower_bound, upper_bound)
    
    def update_historical_data(self, symbol: str, actual_impact: float) -> None:
        """
        Update historical impact data with actual execution results.
        
        Args:
            symbol: Trading symbol
            actual_impact: Actual measured market impact
        """
        if symbol not in self.historical_data:
            self.historical_data[symbol] = []
        
        self.historical_data[symbol].append(actual_impact)
        
        # Keep only recent data (last 100 observations)
        if len(self.historical_data[symbol]) > 100:
            self.historical_data[symbol] = self.historical_data[symbol][-100:]
    
    def optimize_order_size(self, 
                          symbol: str,
                          total_quantity: float,
                          current_price: float,
                          market_volume: float,
                          volatility: float,
                          max_impact_threshold: float = 0.005) -> Tuple[float, int]:
        """
        Optimize order size to stay within impact threshold.
        
        Args:
            symbol: Trading symbol
            total_quantity: Total quantity to execute
            current_price: Current market price
            market_volume: Average daily market volume
            volatility: Daily price volatility
            max_impact_threshold: Maximum acceptable impact (e.g., 0.005 for 0.5%)
            
        Returns:
            Tuple of (optimal_order_size, number_of_slices)
        """
        # Start with single order
        optimal_size = total_quantity
        num_slices = 1
        
        # Check if single order exceeds impact threshold
        impact_result = self.calculate_market_impact(
            symbol, optimal_size, current_price, market_volume, volatility
        )
        
        if impact_result.total_impact <= max_impact_threshold:
            return optimal_size, num_slices
        
        # Binary search for optimal slice size
        min_slices = 1
        max_slices = 100  # Reasonable upper bound
        
        while min_slices < max_slices:
            num_slices = (min_slices + max_slices) // 2
            slice_size = total_quantity / num_slices
            
            # Calculate impact for slice
            impact_result = self.calculate_market_impact(
                symbol, slice_size, current_price, market_volume, volatility
            )
            
            if impact_result.total_impact <= max_impact_threshold:
                max_slices = num_slices
                optimal_size = slice_size
            else:
                min_slices = num_slices + 1
        
        return optimal_size, num_slices
    
    def estimate_execution_cost(self, 
                              symbol: str,
                              order_size: float,
                              current_price: float,
                              market_volume: float,
                              volatility: float,
                              execution_time_minutes: int = 30) -> Dict[str, float]:
        """
        Estimate total execution cost including market impact and fees.
        
        Returns:
            Dictionary with cost breakdown
        """
        # Calculate market impact
        impact_result = self.calculate_market_impact(
            symbol, order_size, current_price, market_volume, volatility, execution_time_minutes
        )
        
        # Calculate trading fees (mock implementation)
        notional_value = order_size * current_price
        trading_fees = notional_value * 0.001  # 0.1% trading fee
        
        # Calculate impact cost
        impact_cost = impact_result.total_impact * notional_value
        
        # Calculate timing cost (opportunity cost of delayed execution)
        timing_cost = self._calculate_timing_cost(order_size, current_price, execution_time_minutes)
        
        total_cost = trading_fees + impact_cost + timing_cost
        
        return {
            'trading_fees': trading_fees,
            'market_impact_cost': impact_cost,
            'timing_cost': timing_cost,
            'total_cost': total_cost,
            'cost_bps': (total_cost / notional_value) * 10000,
            'temporary_impact': impact_result.temporary_impact,
            'permanent_impact': impact_result.permanent_impact
        }
    
    def _calculate_timing_cost(self, order_size: float, current_price: float, 
                             execution_time_minutes: int) -> float:
        """
        Calculate timing cost (opportunity cost of delayed execution).
        
        This represents the cost of not executing immediately.
        """
        # Simplified timing cost calculation
        # In practice, this would consider price drift and volatility
        
        # Assume 0.01% per minute of delay (very conservative estimate)
        timing_cost_rate = 0.0001 * execution_time_minutes
        
        notional_value = order_size * current_price
        timing_cost = notional_value * timing_cost_rate
        
        return timing_cost
    
    def get_model_performance_metrics(self, symbol: str) -> Dict[str, float]:
        """
        Get performance metrics for the market impact model.
        
        Returns:
            Dictionary with performance metrics
        """
        if symbol not in self.historical_data or len(self.historical_data[symbol]) < 5:
            return {
                'data_points': 0,
                'mean_error': 0.0,
                'rmse': 0.0,
                'accuracy_score': 0.0
            }
        
        impacts = self.historical_data[symbol]
        
        # Calculate basic statistics
        mean_impact = np.mean(impacts)
        std_impact = np.std(impacts)
        
        # Calculate model accuracy (simplified)
        # In practice, would compare predictions vs actuals
        accuracy_score = max(0, 1 - std_impact / mean_impact) if mean_impact > 0 else 0
        
        return {
            'data_points': len(impacts),
            'mean_impact': mean_impact,
            'std_impact': std_impact,
            'accuracy_score': accuracy_score,
            'recent_trend': np.mean(impacts[-5:]) - np.mean(impacts[:-5]) if len(impacts) >= 10 else 0
        }
