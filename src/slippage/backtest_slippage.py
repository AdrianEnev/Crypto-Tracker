"""
Backtest-Specific Slippage Calculator

Combines multiple slippage models for comprehensive backtesting with
statistics tracking and performance analysis.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field

# Note: SlippageCalculator is not implemented yet, using individual calculators directly
from .models import SlippageResult, SlippageContext, SlippageType, MarketCondition


@dataclass
class SlippageStats:
    """Statistics for slippage analysis during backtesting."""
    total_slippage_usd: float = 0.0
    total_slippage_bps: float = 0.0
    avg_slippage_bps: float = 0.0
    max_slippage_bps: float = 0.0
    min_slippage_bps: float = float('inf')
    
    # Breakdown by order type
    market_order_slippage: float = 0.0
    limit_order_slippage: float = 0.0
    market_order_count: int = 0
    limit_order_count: int = 0
    
    # Breakdown by side
    buy_slippage: float = 0.0
    sell_slippage: float = 0.0
    buy_count: int = 0
    sell_count: int = 0
    
    # Breakdown by market condition
    slippage_by_condition: Dict[MarketCondition, float] = field(default_factory=dict)
    trades_by_condition: Dict[MarketCondition, int] = field(default_factory=dict)
    
    # Volume and size metrics
    total_volume_usd: float = 0.0
    total_quantity: float = 0.0
    avg_order_size_usd: float = 0.0
    
    def add_trade(self, slippage_result: SlippageResult, trade_value_usd: float, quantity: float) -> None:
        """Add a trade to the statistics."""
        self.total_slippage_usd += slippage_result.slippage_usd
        self.total_slippage_bps += slippage_result.slippage_bps
        self.max_slippage_bps = max(self.max_slippage_bps, slippage_result.slippage_bps)
        self.min_slippage_bps = min(self.min_slippage_bps, slippage_result.slippage_bps)
        
        # Track by order type (assuming market/limit from context)
        if slippage_result.slippage_type == SlippageType.DEPTH_BASED:
            self.market_order_slippage += slippage_result.slippage_bps
            self.market_order_count += 1
        else:
            self.limit_order_slippage += slippage_result.slippage_bps
            self.limit_order_count += 1
        
        # Track by market condition
        condition = slippage_result.market_condition
        if condition not in self.slippage_by_condition:
            self.slippage_by_condition[condition] = 0.0
            self.trades_by_condition[condition] = 0
        
        self.slippage_by_condition[condition] += slippage_result.slippage_bps
        self.trades_by_condition[condition] += 1
        
        self.total_volume_usd += trade_value_usd
        self.total_quantity += quantity
        
        # Update averages
        total_trades = self.market_order_count + self.limit_order_count
        if total_trades > 0:
            self.avg_slippage_bps = self.total_slippage_bps / total_trades
            self.avg_order_size_usd = self.total_volume_usd / total_trades
    
    @property
    def slippage_efficiency_score(self) -> float:
        """Calculate slippage efficiency score (lower is better)."""
        if self.total_volume_usd == 0:
            return 0.0
        return self.total_slippage_usd / self.total_volume_usd
    
    @property
    def market_condition_breakdown(self) -> Dict[str, Dict[str, float]]:
        """Get breakdown of slippage by market condition."""
        breakdown = {}
        for condition, slippage in self.slippage_by_condition.items():
            trades = self.trades_by_condition.get(condition, 1)
            breakdown[condition.value] = {
                "total_slippage_bps": slippage,
                "trade_count": trades,
                "avg_slippage_bps": slippage / trades,
                "percentage_of_trades": (trades / (self.market_order_count + self.limit_order_count)) * 100
            }
        return breakdown


class BacktestSlippageCalculator:
    """Enhanced slippage calculator for backtesting with statistics tracking."""
    
    def __init__(self, slippage_model: SlippageType = SlippageType.DEPTH_BASED):
        self.slippage_model = slippage_model
        self.slippage_history: List[Tuple[datetime, SlippageResult, float, float]] = []  # (timestamp, result, trade_value, quantity)
        self.stats = SlippageStats()
        
        # Initialize the appropriate slippage calculator
        if slippage_model == SlippageType.DEPTH_BASED:
            from .depth_based import DepthBasedSlippage
            self.calculator = DepthBasedSlippage()
        elif slippage_model == SlippageType.VOLUME_BASED:
            from .volume_based import VolumeBasedSlippage
            self.calculator = VolumeBasedSlippage()
        elif slippage_model == SlippageType.MARKET_IMPACT:
            from .market_impact import MarketImpactCalculator
            self.calculator = MarketImpactCalculator()
        else:
            # Default to depth-based
            from .depth_based import DepthBasedSlippage
            self.calculator = DepthBasedSlippage()
    
    def calculate_slippage_with_tracking(
        self, 
        context: SlippageContext, 
        trade_value_usd: float,
        quantity: float
    ) -> SlippageResult:
        """
        Calculate slippage and track statistics for backtesting.
        
        Args:
            context: Slippage calculation context
            trade_value_usd: Value of the trade for statistics
            quantity: Quantity of the trade
            
        Returns:
            SlippageResult with calculated slippage information
        """
        slippage_result = self.calculator.calculate_slippage(context)
        
        # Track statistics
        self.slippage_history.append((datetime.now(), slippage_result, trade_value_usd, quantity))
        self.stats.add_trade(slippage_result, trade_value_usd, quantity)
        
        return slippage_result
    
    def get_slippage_statistics(self) -> SlippageStats:
        """Get current slippage statistics."""
        return self.stats
    
    def get_slippage_history(self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None) -> List[Tuple[datetime, SlippageResult, float, float]]:
        """Get slippage history within a time range."""
        if start_time is None and end_time is None:
            return self.slippage_history.copy()
        
        filtered_history = []
        for timestamp, slippage_result, trade_value, quantity in self.slippage_history:
            if start_time and timestamp < start_time:
                continue
            if end_time and timestamp > end_time:
                continue
            filtered_history.append((timestamp, slippage_result, trade_value, quantity))
        
        return filtered_history
    
    def get_slippage_by_period(self, period_hours: int = 24) -> Dict[datetime, SlippageStats]:
        """Get slippage statistics grouped by time periods."""
        if not self.slippage_history:
            return {}
        
        periods: Dict[datetime, SlippageStats] = {}
        
        for timestamp, slippage_result, trade_value, quantity in self.slippage_history:
            # Round timestamp to period boundary
            period_start = timestamp.replace(
                minute=0, second=0, microsecond=0
            ) - timedelta(hours=timestamp.hour % period_hours)
            
            if period_start not in periods:
                periods[period_start] = SlippageStats()
            
            periods[period_start].add_trade(slippage_result, trade_value, quantity)
        
        return periods
    
    def reset_statistics(self) -> None:
        """Reset all statistics and history."""
        self.slippage_history.clear()
        self.stats = SlippageStats()
    
    def export_slippage_report(self) -> Dict[str, any]:
        """Export comprehensive slippage report for analysis."""
        return {
            "summary": {
                "total_slippage_usd": self.stats.total_slippage_usd,
                "total_slippage_bps": self.stats.total_slippage_bps,
                "avg_slippage_bps": self.stats.avg_slippage_bps,
                "max_slippage_bps": self.stats.max_slippage_bps,
                "min_slippage_bps": self.stats.min_slippage_bps,
                "total_volume_usd": self.stats.total_volume_usd,
                "total_quantity": self.stats.total_quantity,
                "avg_order_size_usd": self.stats.avg_order_size_usd,
                "slippage_efficiency_score": self.stats.slippage_efficiency_score
            },
            "breakdown": {
                "market_order_slippage": self.stats.market_order_slippage,
                "limit_order_slippage": self.stats.limit_order_slippage,
                "market_order_count": self.stats.market_order_count,
                "limit_order_count": self.stats.limit_order_count,
                "buy_slippage": self.stats.buy_slippage,
                "sell_slippage": self.stats.sell_slippage,
                "buy_count": self.stats.buy_count,
                "sell_count": self.stats.sell_count
            },
            "market_conditions": self.stats.market_condition_breakdown,
            "slippage_model": self.slippage_model.value,
            "total_trades": self.stats.market_order_count + self.stats.limit_order_count
        }
    
    def analyze_slippage_trends(self, window_hours: int = 24) -> Dict[str, List[float]]:
        """Analyze slippage trends over time."""
        if not self.slippage_history:
            return {"timestamps": [], "slippage_bps": [], "trade_values": []}
        
        # Group by time windows
        periods = self.get_slippage_by_period(window_hours)
        
        timestamps = []
        avg_slippage_bps = []
        total_trade_values = []
        
        for period_start, stats in sorted(periods.items()):
            timestamps.append(period_start.isoformat())
            avg_slippage_bps.append(stats.avg_slippage_bps)
            total_trade_values.append(stats.total_volume_usd)
        
        return {
            "timestamps": timestamps,
            "slippage_bps": avg_slippage_bps,
            "trade_values": total_trade_values
        }
    
    def compare_slippage_models(self, context: SlippageContext) -> Dict[SlippageType, SlippageResult]:
        """Compare slippage across different models for the same order."""
        from .depth_based import DepthBasedSlippage
        from .volume_based import VolumeBasedSlippage
        from .market_impact import MarketImpactCalculator
        
        results = {}
        
        # Test depth-based model
        try:
            depth_calculator = DepthBasedSlippage()
            results[SlippageType.DEPTH_BASED] = depth_calculator.calculate_slippage(context)
        except Exception:
            pass
        
        # Test volume-based model
        try:
            volume_calculator = VolumeBasedSlippage()
            results[SlippageType.VOLUME_BASED] = volume_calculator.calculate_slippage(context)
        except Exception:
            pass
        
        # Test market impact model
        try:
            impact_calculator = MarketImpactCalculator()
            results[SlippageType.MARKET_IMPACT] = impact_calculator.calculate_market_impact(context)
        except Exception:
            pass
        
        return results
    
    def optimize_order_sizing(self, total_quantity: float, context: SlippageContext, max_slippage_bps: float) -> Dict[str, any]:
        """Find optimal order sizing strategy to minimize slippage."""
        if self.slippage_model == SlippageType.DEPTH_BASED and hasattr(self.calculator, 'get_optimal_order_size'):
            optimal_size = self.calculator.get_optimal_order_size(context.order_book.get_market_depth(), context.side, max_slippage_bps)
            num_slices = max(1, int(total_quantity / optimal_size))
        elif self.slippage_model == SlippageType.VOLUME_BASED and hasattr(self.calculator, 'get_optimal_order_size'):
            optimal_size = self.calculator.get_optimal_order_size(context, max_slippage_bps)
            num_slices = max(1, int(total_quantity / optimal_size))
        else:
            # Default slicing strategy
            num_slices = max(5, int(total_quantity / (context.quantity * 0.1)))
        
        slice_size = total_quantity / num_slices
        estimated_total_slippage = 0.0
        
        # Estimate total slippage for the strategy
        for i in range(num_slices):
            slice_context = SlippageContext(
                symbol=context.symbol,
                side=context.side,
                quantity=slice_size,
                order_type=context.order_type,
                limit_price=context.limit_price,
                timestamp=context.timestamp,
                current_price=context.current_price,
                volume_24h=context.volume_24h,
                volatility=context.volatility,
                market_condition=context.market_condition
            )
            
            slice_result = self.calculator.calculate_slippage(slice_context)
            estimated_total_slippage += slice_result.slippage_bps
        
        return {
            "optimal_num_slices": num_slices,
            "slice_size": slice_size,
            "estimated_total_slippage_bps": estimated_total_slippage,
            "estimated_avg_slippage_bps": estimated_total_slippage / num_slices,
            "strategy": "uniform_slicing"
        }
