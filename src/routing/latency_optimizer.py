"""
Latency optimization system for minimizing execution delays.
Provides geographic routing, connection optimization, and latency monitoring.
"""

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np


@dataclass
class LatencyMetrics:
    """Latency metrics for a connection or route."""
    source: str
    destination: str
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    jitter_ms: float
    packet_loss_rate: float
    connection_stability: float
    last_measured: datetime
    sample_count: int = 0


@dataclass
class Route:
    """Network route information."""
    route_id: str
    source_region: str
    destination_region: str
    venue_id: str
    latency_metrics: LatencyMetrics
    bandwidth_mbps: float
    cost_per_gb: float
    reliability_score: float


class LatencyOptimizer:
    """
    Latency optimization system for minimizing execution delays.
    
    Features:
    - Geographic routing optimization
    - Connection latency monitoring
    - Route selection based on latency and reliability
    - Network performance analytics
    - Real-time latency tracking
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.routes: Dict[str, Route] = {}
        self.latency_history: Dict[str, List[float]] = {}
        
        # Geographic regions and their approximate latencies
        self.region_latencies = {
            'us-east': {'us-west': 70, 'eu-west': 80, 'asia-east': 180, 'asia-west': 200},
            'us-west': {'us-east': 70, 'eu-west': 150, 'asia-east': 120, 'asia-west': 140},
            'eu-west': {'us-east': 80, 'us-west': 150, 'asia-east': 200, 'asia-west': 220},
            'eu-east': {'us-east': 100, 'us-west': 170, 'asia-east': 180, 'asia-west': 200},
            'asia-east': {'us-east': 180, 'us-west': 120, 'eu-west': 200, 'asia-west': 50},
            'asia-west': {'us-east': 200, 'us-west': 140, 'eu-west': 220, 'asia-east': 50}
        }
        
        # Initialize default routes
        self._initialize_default_routes()
    
    def _initialize_default_routes(self) -> None:
        """Initialize default network routes."""
        venues = [
            ('binance', 'asia-east'),
            ('coinbase', 'us-west'),
            ('kraken', 'us-west'),
            ('bitfinex', 'us-east'),
            ('huobi', 'asia-east')
        ]
        
        for venue_id, region in venues:
            # Create routes from different regions to this venue
            for source_region in self.region_latencies.keys():
                if source_region != region:
                    route_id = f"{source_region}-{venue_id}"
                    
                    # Calculate base latency
                    base_latency = self.region_latencies[source_region].get(region, 100)
                    
                    # Add some variation and jitter
                    avg_latency = base_latency + np.random.uniform(-10, 20)
                    jitter = np.random.uniform(5, 15)
                    
                    latency_metrics = LatencyMetrics(
                        source=source_region,
                        destination=region,
                        avg_latency_ms=avg_latency,
                        p50_latency_ms=avg_latency,
                        p95_latency_ms=avg_latency + jitter * 2,
                        p99_latency_ms=avg_latency + jitter * 3,
                        jitter_ms=jitter,
                        packet_loss_rate=np.random.uniform(0.001, 0.01),
                        connection_stability=np.random.uniform(0.95, 0.99),
                        last_measured=datetime.now(timezone.utc),
                        sample_count=100
                    )
                    
                    route = Route(
                        route_id=route_id,
                        source_region=source_region,
                        destination_region=region,
                        venue_id=venue_id,
                        latency_metrics=latency_metrics,
                        bandwidth_mbps=np.random.uniform(100, 1000),
                        cost_per_gb=np.random.uniform(0.01, 0.1),
                        reliability_score=latency_metrics.connection_stability
                    )
                    
                    self.routes[route_id] = route
                    self.latency_history[route_id] = []
    
    def measure_latency(self, route_id: str) -> float:
        """Measure current latency for a route."""
        route = self.routes.get(route_id)
        if not route:
            return 0.0
        
        # Simulate latency measurement
        base_latency = route.latency_metrics.avg_latency_ms
        jitter = np.random.normal(0, route.latency_metrics.jitter_ms)
        measured_latency = max(1.0, base_latency + jitter)
        
        # Update latency history
        self.latency_history[route_id].append(measured_latency)
        
        # Keep only recent measurements (last 100)
        if len(self.latency_history[route_id]) > 100:
            self.latency_history[route_id] = self.latency_history[route_id][-100:]
        
        # Update route metrics
        self._update_route_metrics(route_id, measured_latency)
        
        return measured_latency
    
    def _update_route_metrics(self, route_id: str, new_latency: float) -> None:
        """Update route metrics with new latency measurement."""
        route = self.routes.get(route_id)
        if not route:
            return
        
        history = self.latency_history[route_id]
        
        # Calculate updated metrics
        route.latency_metrics.avg_latency_ms = np.mean(history)
        route.latency_metrics.p50_latency_ms = np.percentile(history, 50)
        route.latency_metrics.p95_latency_ms = np.percentile(history, 95)
        route.latency_metrics.p99_latency_ms = np.percentile(history, 99)
        route.latency_metrics.jitter_ms = np.std(history)
        route.latency_metrics.last_measured = datetime.now(timezone.utc)
        route.latency_metrics.sample_count = len(history)
        
        # Update reliability score based on jitter and packet loss
        jitter_factor = max(0, 1 - (route.latency_metrics.jitter_ms / 50.0))
        packet_loss_factor = max(0, 1 - route.latency_metrics.packet_loss_rate * 100)
        route.reliability_score = (jitter_factor + packet_loss_factor) / 2
    
    def get_best_route(self, source_region: str, venue_id: str, 
                      priority: str = "latency") -> Optional[Route]:
        """
        Get the best route from source region to venue.
        
        Args:
            source_region: Source geographic region
            venue_id: Target venue ID
            priority: Optimization priority ('latency', 'reliability', 'cost')
            
        Returns:
            Best route or None if not found
        """
        candidate_routes = []
        
        for route_id, route in self.routes.items():
            if (route.source_region == source_region and 
                route.venue_id == venue_id):
                candidate_routes.append(route)
        
        if not candidate_routes:
            return None
        
        # Sort routes based on priority
        if priority == "latency":
            candidate_routes.sort(key=lambda r: r.latency_metrics.avg_latency_ms)
        elif priority == "reliability":
            candidate_routes.sort(key=lambda r: r.reliability_score, reverse=True)
        elif priority == "cost":
            candidate_routes.sort(key=lambda r: r.cost_per_gb)
        else:
            # Composite score (latency + reliability + cost)
            def composite_score(route):
                latency_score = 1.0 / (1.0 + route.latency_metrics.avg_latency_ms / 100.0)
                reliability_score = route.reliability_score
                cost_score = 1.0 / (1.0 + route.cost_per_gb)
                return (latency_score * 0.5 + reliability_score * 0.3 + cost_score * 0.2)
            
            candidate_routes.sort(key=composite_score, reverse=True)
        
        return candidate_routes[0]
    
    def get_route_score(self, route_id: str, urgency: float = 1.0) -> float:
        """
        Calculate route score considering latency, reliability, and urgency.
        
        Args:
            route_id: Route identifier
            urgency: Urgency factor (higher = prioritize speed)
            
        Returns:
            Route score (0-1, higher is better)
        """
        route = self.routes.get(route_id)
        if not route:
            return 0.0
        
        metrics = route.latency_metrics
        
        # Latency score (lower latency = higher score)
        latency_score = max(0, 1 - (metrics.avg_latency_ms / 500.0))
        
        # Reliability score
        reliability_score = route.reliability_score
        
        # Jitter score (lower jitter = higher score)
        jitter_score = max(0, 1 - (metrics.jitter_ms / 50.0))
        
        # Composite score
        base_score = (latency_score * 0.4 + reliability_score * 0.4 + jitter_score * 0.2)
        
        # Adjust for urgency (higher urgency favors latency over reliability)
        if urgency > 1.0:
            score = base_score * 0.6 + latency_score * 0.4 * urgency
        else:
            score = base_score
        
        return min(1.0, max(0.0, score))
    
    def get_optimal_venue_for_region(self, source_region: str, 
                                   venue_preferences: List[str],
                                   priority: str = "latency") -> Optional[str]:
        """
        Find the optimal venue for a given source region.
        
        Args:
            source_region: Source geographic region
            venue_preferences: List of preferred venue IDs
            priority: Optimization priority
            
        Returns:
            Optimal venue ID or None
        """
        best_venue = None
        best_score = -1
        
        for venue_id in venue_preferences:
            route = self.get_best_route(source_region, venue_id, priority)
            if route:
                score = self.get_route_score(route.route_id)
                if score > best_score:
                    best_score = score
                    best_venue = venue_id
        
        return best_venue
    
    def get_latency_report(self, route_id: Optional[str] = None) -> Dict:
        """Generate latency performance report."""
        if route_id:
            # Single route report
            route = self.routes.get(route_id)
            if not route:
                return {}
            
            return {
                'route_id': route_id,
                'source_region': route.source_region,
                'destination_region': route.destination_region,
                'venue_id': route.venue_id,
                'latency_metrics': {
                    'avg_latency_ms': route.latency_metrics.avg_latency_ms,
                    'p50_latency_ms': route.latency_metrics.p50_latency_ms,
                    'p95_latency_ms': route.latency_metrics.p95_latency_ms,
                    'p99_latency_ms': route.latency_metrics.p99_latency_ms,
                    'jitter_ms': route.latency_metrics.jitter_ms,
                    'packet_loss_rate': route.latency_metrics.packet_loss_rate
                },
                'performance_metrics': {
                    'reliability_score': route.reliability_score,
                    'route_score': self.get_route_score(route_id),
                    'sample_count': route.latency_metrics.sample_count,
                    'last_measured': route.latency_metrics.last_measured.isoformat()
                }
            }
        else:
            # All routes summary
            summary = {}
            for route_id, route in self.routes.items():
                summary[route_id] = {
                    'venue_id': route.venue_id,
                    'source_region': route.source_region,
                    'destination_region': route.destination_region,
                    'avg_latency_ms': route.latency_metrics.avg_latency_ms,
                    'reliability_score': route.reliability_score,
                    'route_score': self.get_route_score(route_id)
                }
            
            return summary
    
    def simulate_network_conditions(self, route_id: str, duration_seconds: int = 60) -> List[float]:
        """Simulate network conditions for testing purposes."""
        route = self.routes.get(route_id)
        if not route:
            return []
        
        latencies = []
        start_time = time.time()
        
        while time.time() - start_time < duration_seconds:
            # Simulate latency with some realistic variation
            base_latency = route.latency_metrics.avg_latency_ms
            jitter = np.random.normal(0, route.latency_metrics.jitter_ms)
            
            # Occasionally simulate network issues
            if np.random.random() < 0.05:  # 5% chance of network issue
                jitter += np.random.uniform(50, 200)  # Extra latency
            
            latency = max(1.0, base_latency + jitter)
            latencies.append(latency)
            
            # Update route with simulated measurement
            self._update_route_metrics(route_id, latency)
            
            time.sleep(0.1)  # 100ms intervals
        
        return latencies
