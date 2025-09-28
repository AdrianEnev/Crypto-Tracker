"""
Execution quality analytics and reporting system.
Provides comprehensive analysis of order execution performance.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..order_manager.models import Order, OrderState


@dataclass
class ExecutionMetrics:
    """Execution quality metrics."""
    total_orders: int = 0
    filled_orders: int = 0
    cancelled_orders: int = 0
    rejected_orders: int = 0
    
    # Timing metrics
    avg_fill_time_seconds: float = 0.0
    median_fill_time_seconds: float = 0.0
    fill_time_p95_seconds: float = 0.0
    
    # Slippage metrics
    avg_slippage_bps: float = 0.0
    median_slippage_bps: float = 0.0
    slippage_p95_bps: float = 0.0
    positive_slippage_rate: float = 0.0
    
    # Cost metrics
    avg_execution_cost_bps: float = 0.0
    total_execution_cost: float = 0.0
    
    # Market impact
    avg_market_impact_bps: float = 0.0
    max_market_impact_bps: float = 0.0
    
    # Fill rate
    overall_fill_rate: float = 0.0
    partial_fill_rate: float = 0.0


@dataclass
class ExecutionReport:
    """Comprehensive execution quality report."""
    analysis_period: Tuple[datetime, datetime]
    total_orders_analyzed: int
    metrics: ExecutionMetrics
    performance_by_symbol: Dict[str, ExecutionMetrics]
    performance_by_side: Dict[str, ExecutionMetrics]
    performance_by_time_of_day: Dict[str, ExecutionMetrics]
    recommendations: List[str]
    quality_score: float
    benchmark_comparison: Optional[Dict] = None


class ExecutionAnalytics:
    """
    Comprehensive execution quality analysis and reporting system.
    
    Features:
    - Multi-dimensional performance analysis
    - Slippage and market impact analysis
    - Timing efficiency metrics
    - Cost breakdown and optimization suggestions
    - Benchmark comparison capabilities
    - Performance degradation detection
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.benchmark_data: Dict = {}
        
    def analyze_execution_quality(self, 
                                orders: List[Order],
                                analysis_period: Optional[Tuple[datetime, datetime]] = None) -> ExecutionReport:
        """
        Analyze execution quality across multiple dimensions.
        
        Args:
            orders: List of orders to analyze
            analysis_period: Optional time period for analysis
            
        Returns:
            Comprehensive execution quality report
        """
        if not orders:
            return self._create_empty_report(analysis_period)
        
        # Filter orders by time period if specified
        if analysis_period:
            start_time, end_time = analysis_period
            # Make sure all datetimes are timezone-aware
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=timezone.utc)
            
            orders = [order for order in orders 
                     if start_time <= order.created_at <= end_time]
        
        if not orders:
            return self._create_empty_report(analysis_period)
        
        # Calculate overall metrics
        overall_metrics = self._calculate_overall_metrics(orders)
        
        # Performance breakdowns
        symbol_performance = self._analyze_by_symbol(orders)
        side_performance = self._analyze_by_side(orders)
        time_performance = self._analyze_by_time_of_day(orders)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(overall_metrics, symbol_performance, side_performance)
        
        # Calculate quality score
        quality_score = self._calculate_quality_score(overall_metrics)
        
        # Benchmark comparison (if available)
        benchmark_comparison = self._compare_with_benchmarks(overall_metrics)
        
        return ExecutionReport(
            analysis_period=analysis_period or (orders[0].created_at, orders[-1].created_at),
            total_orders_analyzed=len(orders),
            metrics=overall_metrics,
            performance_by_symbol=symbol_performance,
            performance_by_side=side_performance,
            performance_by_time_of_day=time_performance,
            recommendations=recommendations,
            quality_score=quality_score,
            benchmark_comparison=benchmark_comparison
        )
    
    def _calculate_overall_metrics(self, orders: List[Order]) -> ExecutionMetrics:
        """Calculate overall execution metrics."""
        filled_orders = [order for order in orders if order.state == OrderState.FILLED]
        cancelled_orders = [order for order in orders if order.state == OrderState.CANCELED]
        rejected_orders = [order for order in orders if order.state == OrderState.REJECTED]
        
        # Basic counts
        total_orders = len(orders)
        filled_count = len(filled_orders)
        cancelled_count = len(cancelled_orders)
        rejected_count = len(rejected_orders)
        
        # Fill rate
        overall_fill_rate = filled_count / total_orders if total_orders > 0 else 0
        partial_fill_rate = len([order for order in orders if order.state == OrderState.PARTIALLY_FILLED]) / total_orders
        
        # Timing metrics
        fill_times = []
        for order in filled_orders:
            if order.filled_at and order.created_at:
                fill_time = (order.filled_at - order.created_at).total_seconds()
                fill_times.append(fill_time)
        
        avg_fill_time = np.mean(fill_times) if fill_times else 0
        median_fill_time = np.median(fill_times) if fill_times else 0
        fill_time_p95 = np.percentile(fill_times, 95) if fill_times else 0
        
        # Slippage metrics
        slippages = []
        for order in filled_orders:
            slippage = self._calculate_order_slippage(order)
            if slippage is not None:
                slippages.append(slippage)
        
        avg_slippage = np.mean(slippages) if slippages else 0
        median_slippage = np.median(slippages) if slippages else 0
        slippage_p95 = np.percentile(slippages, 95) if slippages else 0
        positive_slippage_rate = len([s for s in slippages if s > 0]) / len(slippages) if slippages else 0
        
        # Cost metrics
        total_cost = sum(self._calculate_order_cost(order) for order in filled_orders)
        avg_cost = total_cost / filled_count if filled_count > 0 else 0
        
        # Market impact
        market_impacts = [self._calculate_market_impact(order) for order in filled_orders]
        market_impacts = [impact for impact in market_impacts if impact is not None]
        
        avg_market_impact = np.mean(market_impacts) if market_impacts else 0
        max_market_impact = np.max(market_impacts) if market_impacts else 0
        
        return ExecutionMetrics(
            total_orders=total_orders,
            filled_orders=filled_count,
            cancelled_orders=cancelled_count,
            rejected_orders=rejected_count,
            avg_fill_time_seconds=avg_fill_time,
            median_fill_time_seconds=median_fill_time,
            fill_time_p95_seconds=fill_time_p95,
            avg_slippage_bps=avg_slippage * 10000,  # Convert to basis points
            median_slippage_bps=median_slippage * 10000,
            slippage_p95_bps=slippage_p95 * 10000,
            positive_slippage_rate=positive_slippage_rate,
            avg_execution_cost_bps=avg_cost * 10000,
            total_execution_cost=total_cost,
            avg_market_impact_bps=avg_market_impact * 10000,
            max_market_impact_bps=max_market_impact * 10000,
            overall_fill_rate=overall_fill_rate,
            partial_fill_rate=partial_fill_rate
        )
    
    def _calculate_order_slippage(self, order: Order) -> Optional[float]:
        """Calculate slippage for a filled order."""
        if not order.filled_at or not order.average_fill_price:
            return None
        
        # For market orders, compare filled price to market price at time of order
        # For limit orders, slippage is typically zero or negative (price improvement)
        
        # Mock implementation - in real system would fetch historical market data
        market_price_at_order = order.price * 1.0001  # Assume slight market impact
        
        if order.side == "buy":
            slippage = (order.average_fill_price - market_price_at_order) / market_price_at_order
        else:
            slippage = (market_price_at_order - order.average_fill_price) / market_price_at_order
        
        return slippage
    
    def _calculate_order_cost(self, order: Order) -> float:
        """Calculate total execution cost for an order."""
        if not order.average_fill_price or not order.filled_quantity:
            return 0.0
        
        # Include fees and slippage
        notional_value = order.average_fill_price * order.filled_quantity
        
        # Trading fees (mock - would use actual fee structure)
        trading_fees = notional_value * 0.001  # 0.1% trading fee
        
        # Slippage cost
        slippage = self._calculate_order_slippage(order)
        slippage_cost = abs(slippage) * notional_value if slippage else 0
        
        return trading_fees + slippage_cost
    
    def _calculate_market_impact(self, order: Order) -> Optional[float]:
        """Calculate market impact of an order."""
        if not order.average_fill_price or not order.filled_quantity:
            return None
        
        # Simplified market impact calculation
        # In real implementation, would compare to market price before order
        
        # Mock implementation
        market_price_before = order.average_fill_price * 0.999  # Assume 0.1% impact
        
        if order.side == "buy":
            impact = (order.average_fill_price - market_price_before) / market_price_before
        else:
            impact = (market_price_before - order.average_fill_price) / market_price_before
        
        return abs(impact)
    
    def _analyze_by_symbol(self, orders: List[Order]) -> Dict[str, ExecutionMetrics]:
        """Analyze execution performance by trading symbol."""
        symbol_groups = {}
        
        for order in orders:
            symbol = order.symbol
            if symbol not in symbol_groups:
                symbol_groups[symbol] = []
            symbol_groups[symbol].append(order)
        
        symbol_performance = {}
        for symbol, symbol_orders in symbol_groups.items():
            symbol_performance[symbol] = self._calculate_overall_metrics(symbol_orders)
        
        return symbol_performance
    
    def _analyze_by_side(self, orders: List[Order]) -> Dict[str, ExecutionMetrics]:
        """Analyze execution performance by order side."""
        buy_orders = [order for order in orders if order.side == "buy"]
        sell_orders = [order for order in orders if order.side == "sell"]
        
        return {
            'BUY': self._calculate_overall_metrics(buy_orders),
            'SELL': self._calculate_overall_metrics(sell_orders)
        }
    
    def _analyze_by_time_of_day(self, orders: List[Order]) -> Dict[str, ExecutionMetrics]:
        """Analyze execution performance by time of day."""
        time_groups = {
            'asian_hours': [],    # 0-8 UTC
            'european_hours': [], # 8-16 UTC
            'us_hours': [],       # 16-24 UTC
        }
        
        for order in orders:
            hour = order.created_at.hour
            
            if 0 <= hour < 8:
                time_groups['asian_hours'].append(order)
            elif 8 <= hour < 16:
                time_groups['european_hours'].append(order)
            else:
                time_groups['us_hours'].append(order)
        
        time_performance = {}
        for period, period_orders in time_groups.items():
            if period_orders:
                time_performance[period] = self._calculate_overall_metrics(period_orders)
        
        return time_performance
    
    def _generate_recommendations(self, 
                                overall_metrics: ExecutionMetrics,
                                symbol_performance: Dict[str, ExecutionMetrics],
                                side_performance: Dict[str, ExecutionMetrics]) -> List[str]:
        """Generate improvement recommendations based on analysis."""
        recommendations = []
        
        # Fill rate recommendations
        if overall_metrics.overall_fill_rate < 0.8:
            recommendations.append(
                f"Low fill rate ({overall_metrics.overall_fill_rate:.1%}). "
                "Consider using more aggressive pricing or market orders for time-sensitive trades."
            )
        
        # Slippage recommendations
        if overall_metrics.avg_slippage_bps > 5:
            recommendations.append(
                f"High average slippage ({overall_metrics.avg_slippage_bps:.1f} bps). "
                "Consider using TWAP/VWAP execution for large orders."
            )
        
        # Timing recommendations
        if overall_metrics.avg_fill_time_seconds > 300:  # 5 minutes
            recommendations.append(
                f"Slow execution times ({overall_metrics.avg_fill_time_seconds:.0f}s average). "
                "Consider improving order routing or using more liquid venues."
            )
        
        # Symbol-specific recommendations
        for symbol, metrics in symbol_performance.items():
            if metrics.avg_slippage_bps > 10:
                recommendations.append(
                    f"High slippage on {symbol} ({metrics.avg_slippage_bps:.1f} bps). "
                    "Consider alternative execution strategies for this symbol."
                )
        
        # Side-specific recommendations
        if side_performance.get('BUY', ExecutionMetrics()).avg_slippage_bps > \
           side_performance.get('SELL', ExecutionMetrics()).avg_slippage_bps * 1.5:
            recommendations.append(
                "Buy orders showing higher slippage than sell orders. "
                "Consider adjusting buy order pricing strategy."
            )
        
        return recommendations
    
    def _calculate_quality_score(self, metrics: ExecutionMetrics) -> float:
        """Calculate overall execution quality score (0-100)."""
        score = 100.0
        
        # Deduct points for poor fill rate
        if metrics.overall_fill_rate < 0.9:
            score -= (0.9 - metrics.overall_fill_rate) * 100
        
        # Deduct points for high slippage
        if metrics.avg_slippage_bps > 2:
            score -= min(30, (metrics.avg_slippage_bps - 2) * 5)
        
        # Deduct points for slow execution
        if metrics.avg_fill_time_seconds > 60:
            score -= min(20, (metrics.avg_fill_time_seconds - 60) / 10)
        
        # Deduct points for high market impact
        if metrics.avg_market_impact_bps > 5:
            score -= min(25, (metrics.avg_market_impact_bps - 5) * 2)
        
        return max(0, score)
    
    def _compare_with_benchmarks(self, metrics: ExecutionMetrics) -> Optional[Dict]:
        """Compare execution metrics with benchmarks."""
        if not self.benchmark_data:
            return None
        
        # Mock benchmark comparison
        benchmark = {
            'avg_slippage_bps': 2.5,
            'avg_fill_time_seconds': 45,
            'fill_rate': 0.95,
            'market_impact_bps': 3.0
        }
        
        comparison = {}
        
        # Slippage comparison
        slippage_vs_benchmark = metrics.avg_slippage_bps - benchmark['avg_slippage_bps']
        comparison['slippage_vs_benchmark'] = {
            'difference_bps': slippage_vs_benchmark,
            'performance': 'better' if slippage_vs_benchmark < 0 else 'worse'
        }
        
        # Fill time comparison
        time_vs_benchmark = metrics.avg_fill_time_seconds - benchmark['avg_fill_time_seconds']
        comparison['fill_time_vs_benchmark'] = {
            'difference_seconds': time_vs_benchmark,
            'performance': 'better' if time_vs_benchmark < 0 else 'worse'
        }
        
        return comparison
    
    def _create_empty_report(self, analysis_period: Optional[Tuple[datetime, datetime]]) -> ExecutionReport:
        """Create empty report when no orders to analyze."""
        return ExecutionReport(
            analysis_period=analysis_period or (datetime.now(), datetime.now()),
            total_orders_analyzed=0,
            metrics=ExecutionMetrics(),
            performance_by_symbol={},
            performance_by_side={},
            performance_by_time_of_day={},
            recommendations=["No orders found for analysis"],
            quality_score=0.0
        )
    
    def set_benchmark_data(self, benchmark_data: Dict) -> None:
        """Set benchmark data for comparison."""
        self.benchmark_data = benchmark_data
    
    def generate_execution_report_summary(self, report: ExecutionReport) -> str:
        """Generate human-readable execution report summary."""
        summary = []
        summary.append("=" * 60)
        summary.append("EXECUTION QUALITY REPORT")
        summary.append("=" * 60)
        summary.append(f"Analysis Period: {report.analysis_period[0]} to {report.analysis_period[1]}")
        summary.append(f"Total Orders Analyzed: {report.total_orders_analyzed}")
        summary.append(f"Overall Quality Score: {report.quality_score:.1f}/100")
        summary.append("")
        
        # Key metrics
        summary.append("KEY METRICS:")
        summary.append(f"  Fill Rate: {report.metrics.overall_fill_rate:.1%}")
        summary.append(f"  Average Slippage: {report.metrics.avg_slippage_bps:.1f} bps")
        summary.append(f"  Average Fill Time: {report.metrics.avg_fill_time_seconds:.1f} seconds")
        summary.append(f"  Market Impact: {report.metrics.avg_market_impact_bps:.1f} bps")
        summary.append("")
        
        # Recommendations
        if report.recommendations:
            summary.append("RECOMMENDATIONS:")
            for i, rec in enumerate(report.recommendations, 1):
                summary.append(f"  {i}. {rec}")
            summary.append("")
        
        # Benchmark comparison
        if report.benchmark_comparison:
            summary.append("BENCHMARK COMPARISON:")
            slippage_comp = report.benchmark_comparison.get('slippage_vs_benchmark', {})
            time_comp = report.benchmark_comparison.get('fill_time_vs_benchmark', {})
            
            summary.append(f"  Slippage: {slippage_comp.get('difference_bps', 0):+.1f} bps vs benchmark")
            summary.append(f"  Fill Time: {time_comp.get('difference_seconds', 0):+.1f}s vs benchmark")
            summary.append("")
        
        summary.append("=" * 60)
        
        return "\n".join(summary)
