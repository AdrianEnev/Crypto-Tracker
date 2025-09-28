"""
Smart Order Routing

Intelligent routing of orders across multiple exchanges based on
liquidity, fees, latency, and other factors.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import time

from .models import Order, OrderRequest
from .executors import BaseExecutor


@dataclass
class ExchangeMetrics:
    """Metrics for exchange evaluation."""
    exchange_name: str
    liquidity_score: float  # 0-1
    fee_score: float  # 0-1 (higher is better)
    latency_score: float  # 0-1 (higher is better)
    reliability_score: float  # 0-1
    price_improvement_score: float  # 0-1
    total_score: float  # Weighted combination
    
    def __post_init__(self):
        """Calculate total score."""
        weights = {
            'liquidity': 0.3,
            'fees': 0.25,
            'latency': 0.2,
            'reliability': 0.15,
            'price_improvement': 0.1
        }
        
        self.total_score = (
            self.liquidity_score * weights['liquidity'] +
            self.fee_score * weights['fees'] +
            self.latency_score * weights['latency'] +
            self.reliability_score * weights['reliability'] +
            self.price_improvement_score * weights['price_improvement']
        )


class SmartOrderRouter:
    """Intelligent order routing across multiple exchanges."""
    
    def __init__(self):
        self.executors: Dict[str, BaseExecutor] = {}
        self.exchange_metrics: Dict[str, ExchangeMetrics] = {}
        self.liquidity_cache: Dict[str, Dict[str, float]] = {}
        self.fee_cache: Dict[str, Dict[str, float]] = {}
        self.latency_cache: Dict[str, List[float]] = {}
        self.reliability_cache: Dict[str, List[bool]] = {}
        
        # Cache TTL
        self.cache_ttl = timedelta(minutes=5)
        self.last_update: Dict[str, datetime] = {}
        
        # Routing preferences
        self.preferred_exchanges: List[str] = []
        self.blacklisted_exchanges: List[str] = []
        self.min_liquidity_threshold = 10000  # USD
        self.max_slippage_bps = 50  # 0.5%
    
    def register_executor(self, exchange_name: str, executor: BaseExecutor) -> None:
        """Register an executor for routing."""
        self.executors[exchange_name] = executor
        self._initialize_metrics(exchange_name)
    
    def unregister_executor(self, exchange_name: str) -> None:
        """Unregister an executor."""
        if exchange_name in self.executors:
            del self.executors[exchange_name]
        if exchange_name in self.exchange_metrics:
            del self.exchange_metrics[exchange_name]
    
    def set_preferred_exchanges(self, exchanges: List[str]) -> None:
        """Set preferred exchange order."""
        self.preferred_exchanges = exchanges
    
    def blacklist_exchange(self, exchange_name: str) -> None:
        """Blacklist an exchange from routing."""
        if exchange_name not in self.blacklisted_exchanges:
            self.blacklisted_exchanges.append(exchange_name)
    
    def whitelist_exchange(self, exchange_name: str) -> None:
        """Remove exchange from blacklist."""
        if exchange_name in self.blacklisted_exchanges:
            self.blacklisted_exchanges.remove(exchange_name)
    
    def select_executor(self, order_request: OrderRequest) -> BaseExecutor:
        """Select best executor for order execution."""
        available_exchanges = self._get_available_exchanges(order_request)
        
        if not available_exchanges:
            raise RuntimeError("No available exchanges for order execution")
        
        # Update metrics if needed
        self._update_metrics_if_needed(available_exchanges)
        
        # Score exchanges
        exchange_scores = {}
        for exchange in available_exchanges:
            score = self._calculate_exchange_score(exchange, order_request)
            exchange_scores[exchange] = score
        
        # Select best exchange
        best_exchange = max(exchange_scores, key=exchange_scores.get)
        return self.executors[best_exchange]
    
    def get_routing_recommendation(self, order_request: OrderRequest) -> Dict[str, any]:
        """Get detailed routing recommendation."""
        available_exchanges = self._get_available_exchanges(order_request)
        
        recommendations = []
        for exchange in available_exchanges:
            metrics = self.exchange_metrics.get(exchange)
            if metrics:
                recommendations.append({
                    'exchange': exchange,
                    'score': metrics.total_score,
                    'metrics': {
                        'liquidity': metrics.liquidity_score,
                        'fees': metrics.fee_score,
                        'latency': metrics.latency_score,
                        'reliability': metrics.reliability_score,
                        'price_improvement': metrics.price_improvement_score
                    },
                    'recommended': False
                })
        
        # Sort by score
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        
        # Mark best as recommended
        if recommendations:
            recommendations[0]['recommended'] = True
        
        return {
            'order_request': {
                'symbol': order_request.symbol,
                'side': order_request.side,
                'quantity': order_request.quantity,
                'order_type': order_request.order_type.value
            },
            'recommendations': recommendations,
            'total_exchanges': len(available_exchanges)
        }
    
    def _get_available_exchanges(self, order_request: OrderRequest) -> List[str]:
        """Get list of available exchanges for order."""
        available = []
        
        for exchange_name, executor in self.executors.items():
            # Check if exchange is blacklisted
            if exchange_name in self.blacklisted_exchanges:
                continue
            
            # Check if exchange supports the symbol
            if order_request.symbol not in executor.get_supported_symbols():
                continue
            
            # Check if exchange supports the order type
            if order_request.order_type.value not in executor.get_supported_order_types():
                continue
            
            # Check if exchange is connected
            if not executor.is_connected:
                continue
            
            available.append(exchange_name)
        
        # Apply preferred order
        if self.preferred_exchanges:
            preferred_available = [ex for ex in self.preferred_exchanges if ex in available]
            other_available = [ex for ex in available if ex not in self.preferred_exchanges]
            available = preferred_available + other_available
        
        return available
    
    def _calculate_exchange_score(self, exchange_name: str, order_request: OrderRequest) -> float:
        """Calculate score for exchange based on order requirements."""
        metrics = self.exchange_metrics.get(exchange_name)
        if not metrics:
            return 0.0
        
        base_score = metrics.total_score
        
        # Adjust for order-specific factors
        adjustments = 0.0
        
        # Large orders prefer higher liquidity
        if order_request.quantity > 1000:  # Large order threshold
            adjustments += metrics.liquidity_score * 0.1
        
        # Market orders prefer lower latency
        if order_request.order_type.value == 'market':
            adjustments += metrics.latency_score * 0.1
        
        # Limit orders can tolerate higher latency for better price
        if order_request.order_type.value == 'limit':
            adjustments += metrics.price_improvement_score * 0.1
        
        return base_score + adjustments
    
    def _initialize_metrics(self, exchange_name: str) -> None:
        """Initialize metrics for new exchange."""
        self.exchange_metrics[exchange_name] = ExchangeMetrics(
            exchange_name=exchange_name,
            liquidity_score=0.5,  # Default neutral score
            fee_score=0.5,
            latency_score=0.5,
            reliability_score=0.5,
            price_improvement_score=0.5,
            total_score=0.5
        )
    
    def _update_metrics_if_needed(self, exchanges: List[str]) -> None:
        """Update metrics if cache is stale."""
        now = datetime.now()
        
        for exchange in exchanges:
            last_update = self.last_update.get(exchange)
            if last_update is None or (now - last_update) > self.cache_ttl:
                self._update_exchange_metrics(exchange)
                self.last_update[exchange] = now
    
    def _update_exchange_metrics(self, exchange_name: str) -> None:
        """Update metrics for specific exchange."""
        metrics = self.exchange_metrics.get(exchange_name)
        if not metrics:
            return
        
        # Update liquidity score
        metrics.liquidity_score = self._calculate_liquidity_score(exchange_name)
        
        # Update fee score
        metrics.fee_score = self._calculate_fee_score(exchange_name)
        
        # Update latency score
        metrics.latency_score = self._calculate_latency_score(exchange_name)
        
        # Update reliability score
        metrics.reliability_score = self._calculate_reliability_score(exchange_name)
        
        # Update price improvement score
        metrics.price_improvement_score = self._calculate_price_improvement_score(exchange_name)
        
        # Recalculate total score
        metrics.__post_init__()
    
    def _calculate_liquidity_score(self, exchange_name: str) -> float:
        """Calculate liquidity score for exchange."""
        # This would typically fetch real liquidity data
        # For now, return a simulated score
        import random
        return random.uniform(0.3, 0.9)
    
    def _calculate_fee_score(self, exchange_name: str) -> float:
        """Calculate fee score for exchange (higher is better)."""
        # Simulate fee calculation
        fee_scores = {
            'binance': 0.8,
            'bybit': 0.7,
            'coinbase': 0.6,
            'kraken': 0.7,
            'paper': 1.0
        }
        return fee_scores.get(exchange_name, 0.5)
    
    def _calculate_latency_score(self, exchange_name: str) -> float:
        """Calculate latency score for exchange."""
        # Simulate latency measurement
        latencies = {
            'binance': 0.8,
            'bybit': 0.7,
            'coinbase': 0.6,
            'kraken': 0.7,
            'paper': 1.0
        }
        return latencies.get(exchange_name, 0.5)
    
    def _calculate_reliability_score(self, exchange_name: str) -> float:
        """Calculate reliability score for exchange."""
        # This would track historical uptime and success rates
        reliability_scores = {
            'binance': 0.9,
            'bybit': 0.8,
            'coinbase': 0.9,
            'kraken': 0.8,
            'paper': 1.0
        }
        return reliability_scores.get(exchange_name, 0.7)
    
    def _calculate_price_improvement_score(self, exchange_name: str) -> float:
        """Calculate price improvement score for exchange."""
        # This would measure how often orders get better prices than expected
        improvement_scores = {
            'binance': 0.7,
            'bybit': 0.6,
            'coinbase': 0.8,
            'kraken': 0.7,
            'paper': 0.5
        }
        return improvement_scores.get(exchange_name, 0.5)
    
    def record_execution_result(self, exchange_name: str, order_result, execution_time_ms: float) -> None:
        """Record execution result for metrics calculation."""
        # Update latency cache
        if exchange_name not in self.latency_cache:
            self.latency_cache[exchange_name] = []
        
        self.latency_cache[exchange_name].append(execution_time_ms)
        
        # Keep only last 100 measurements
        if len(self.latency_cache[exchange_name]) > 100:
            self.latency_cache[exchange_name] = self.latency_cache[exchange_name][-100:]
        
        # Update reliability cache
        if exchange_name not in self.reliability_cache:
            self.reliability_cache[exchange_name] = []
        
        success = order_result.success if hasattr(order_result, 'success') else True
        self.reliability_cache[exchange_name].append(success)
        
        # Keep only last 100 measurements
        if len(self.reliability_cache[exchange_name]) > 100:
            self.reliability_cache[exchange_name] = self.reliability_cache[exchange_name][-100:]
    
    def get_exchange_statistics(self) -> Dict[str, any]:
        """Get statistics for all registered exchanges."""
        stats = {}
        
        for exchange_name in self.executors.keys():
            metrics = self.exchange_metrics.get(exchange_name)
            if metrics:
                stats[exchange_name] = {
                    'metrics': {
                        'liquidity_score': metrics.liquidity_score,
                        'fee_score': metrics.fee_score,
                        'latency_score': metrics.latency_score,
                        'reliability_score': metrics.reliability_score,
                        'price_improvement_score': metrics.price_improvement_score,
                        'total_score': metrics.total_score
                    },
                    'latency_samples': len(self.latency_cache.get(exchange_name, [])),
                    'reliability_samples': len(self.reliability_cache.get(exchange_name, [])),
                    'connected': self.executors[exchange_name].is_connected
                }
        
        return stats
