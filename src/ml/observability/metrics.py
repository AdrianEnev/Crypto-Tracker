"""
Metrics aggregation and querying system for ML observability.
Provides time series metrics collection, aggregation, and querying.
"""

import time
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
import statistics
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class AggregationType(Enum):
    """Metric aggregation types."""
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    MEDIAN = "median"
    PERCENTILE = "percentile"
    RATE = "rate"
    DELTA = "delta"


@dataclass
class TimeSeriesData:
    """Container for time series data point."""
    timestamp: datetime
    value: float
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'value': self.value,
            'tags': self.tags,
            'metadata': self.metadata
        }


@dataclass
class MetricsQuery:
    """Container for metrics query parameters."""
    metric_name: str
    start_time: datetime
    end_time: datetime
    aggregation: AggregationType = AggregationType.AVG
    interval_seconds: int = 60
    tags_filter: Dict[str, str] = field(default_factory=dict)
    group_by: List[str] = field(default_factory=list)
    percentile: Optional[float] = None
    limit: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'metric_name': self.metric_name,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'aggregation': self.aggregation.value,
            'interval_seconds': self.interval_seconds,
            'tags_filter': self.tags_filter,
            'group_by': self.group_by,
            'percentile': self.percentile,
            'limit': self.limit
        }


class MetricsAggregator:
    """
    Metrics aggregator for time series data collection and querying.
    """
    
    def __init__(self, 
                 max_retention_hours: int = 24,
                 aggregation_interval: int = 60,
                 max_points_per_metric: int = 10000):
        self.max_retention_hours = max_retention_hours
        self.aggregation_interval = aggregation_interval
        self.max_points_per_metric = max_points_per_metric
        
        # Storage
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_points_per_metric))
        self.metric_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Threading
        self._lock = threading.RLock()
        self._cleanup_thread: Optional[threading.Thread] = None
        self._stop_cleanup = threading.Event()
        
        # Start cleanup thread
        self._start_cleanup_thread()
        
        logger.info(f"Initialized metrics aggregator: {max_retention_hours}h retention, {aggregation_interval}s interval")
    
    def _start_cleanup_thread(self) -> None:
        """Start background cleanup thread."""
        def cleanup_worker():
            while not self._stop_cleanup.is_set():
                try:
                    self._cleanup_old_metrics()
                    self._stop_cleanup.wait(300)  # Cleanup every 5 minutes
                except Exception as e:
                    logger.error(f"Error in metrics cleanup: {e}")
        
        self._cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self._cleanup_thread.start()
    
    def _cleanup_old_metrics(self) -> None:
        """Remove old metrics data."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.max_retention_hours)
        
        with self._lock:
            for metric_name, data_points in self.metrics.items():
                # Remove old data points
                while data_points and data_points[0].timestamp < cutoff_time:
                    data_points.popleft()
    
    def record_metric(self, 
                     metric_name: str,
                     value: float,
                     tags: Optional[Dict[str, str]] = None,
                     metadata: Optional[Dict[str, Any]] = None,
                     timestamp: Optional[datetime] = None) -> None:
        """
        Record a metric value.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            tags: Optional tags for the metric
            metadata: Optional metadata
            timestamp: Optional timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        data_point = TimeSeriesData(
            timestamp=timestamp,
            value=value,
            tags=tags or {},
            metadata=metadata or {}
        )
        
        with self._lock:
            self.metrics[metric_name].append(data_point)
            
            # Update metadata
            if metric_name not in self.metric_metadata:
                self.metric_metadata[metric_name] = {
                    'first_seen': timestamp,
                    'last_seen': timestamp,
                    'total_points': 0,
                    'min_value': value,
                    'max_value': value
                }
            
            meta = self.metric_metadata[metric_name]
            meta['last_seen'] = timestamp
            meta['total_points'] += 1
            meta['min_value'] = min(meta['min_value'], value)
            meta['max_value'] = max(meta['max_value'], value)
    
    def record_counter(self, 
                      metric_name: str,
                      increment: float = 1.0,
                      tags: Optional[Dict[str, str]] = None,
                      metadata: Optional[Dict[str, Any]] = None,
                      timestamp: Optional[datetime] = None) -> None:
        """Record a counter metric."""
        self.record_metric(metric_name, increment, tags, metadata, timestamp)
    
    def record_gauge(self, 
                    metric_name: str,
                    value: float,
                    tags: Optional[Dict[str, str]] = None,
                    metadata: Optional[Dict[str, Any]] = None,
                    timestamp: Optional[datetime] = None) -> None:
        """Record a gauge metric."""
        self.record_metric(metric_name, value, tags, metadata, timestamp)
    
    def record_timing(self, 
                     metric_name: str,
                     duration_ms: float,
                     tags: Optional[Dict[str, str]] = None,
                     metadata: Optional[Dict[str, Any]] = None,
                     timestamp: Optional[datetime] = None) -> None:
        """Record a timing metric."""
        self.record_metric(metric_name, duration_ms, tags, metadata, timestamp)
    
    def query_metrics(self, query: MetricsQuery) -> List[TimeSeriesData]:
        """
        Query metrics with specified parameters.
        
        Args:
            query: Query parameters
            
        Returns:
            List of aggregated time series data points
        """
        with self._lock:
            if query.metric_name not in self.metrics:
                return []
            
            # Get raw data points
            raw_data = list(self.metrics[query.metric_name])
            
            # Filter by time range
            filtered_data = [
                dp for dp in raw_data
                if query.start_time <= dp.timestamp <= query.end_time
            ]
            
            # Filter by tags
            if query.tags_filter:
                filtered_data = [
                    dp for dp in filtered_data
                    if all(dp.tags.get(k) == v for k, v in query.tags_filter.items())
                ]
            
            if not filtered_data:
                return []
            
            # Group by specified tags
            if query.group_by:
                grouped_data = self._group_by_tags(filtered_data, query.group_by)
                results = []
                
                for group_key, group_data in grouped_data.items():
                    aggregated = self._aggregate_data(group_data, query)
                    results.extend(aggregated)
                
                return results
            else:
                return self._aggregate_data(filtered_data, query)
    
    def _group_by_tags(self, data: List[TimeSeriesData], group_by: List[str]) -> Dict[str, List[TimeSeriesData]]:
        """Group data by specified tags."""
        grouped = defaultdict(list)
        
        for dp in data:
            group_key = tuple(dp.tags.get(tag, '') for tag in group_by)
            grouped[group_key].append(dp)
        
        return grouped
    
    def _aggregate_data(self, data: List[TimeSeriesData], query: MetricsQuery) -> List[TimeSeriesData]:
        """Aggregate data according to query parameters."""
        if not data:
            return []
        
        # Sort by timestamp
        data.sort(key=lambda dp: dp.timestamp)
        
        # Create time buckets
        buckets = self._create_time_buckets(query)
        
        # Assign data points to buckets
        for dp in data:
            bucket_time = self._get_bucket_time(dp.timestamp, query.interval_seconds)
            if bucket_time in buckets:
                buckets[bucket_time].append(dp.value)
        
        # Aggregate each bucket
        results = []
        for bucket_time, values in buckets.items():
            if not values:
                continue
            
            aggregated_value = self._calculate_aggregation(values, query.aggregation, query.percentile)
            
            # Create result data point
            result_dp = TimeSeriesData(
                timestamp=bucket_time,
                value=aggregated_value,
                tags=query.tags_filter.copy(),
                metadata={
                    'aggregation': query.aggregation.value,
                    'bucket_size': len(values),
                    'interval_seconds': query.interval_seconds
                }
            )
            
            results.append(result_dp)
        
        # Sort by timestamp
        results.sort(key=lambda dp: dp.timestamp)
        
        # Apply limit
        if query.limit:
            results = results[-query.limit:]
        
        return results
    
    def _create_time_buckets(self, query: MetricsQuery) -> Dict[datetime, List[float]]:
        """Create time buckets for aggregation."""
        buckets = {}
        current_time = query.start_time
        
        # Round to bucket boundary
        current_time = self._round_to_bucket(current_time, query.interval_seconds)
        
        while current_time <= query.end_time:
            buckets[current_time] = []
            current_time += timedelta(seconds=query.interval_seconds)
        
        return buckets
    
    def _round_to_bucket(self, timestamp: datetime, interval_seconds: int) -> datetime:
        """Round timestamp to bucket boundary."""
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        seconds_since_epoch = int((timestamp - epoch).total_seconds())
        bucket_seconds = (seconds_since_epoch // interval_seconds) * interval_seconds
        return epoch + timedelta(seconds=bucket_seconds)
    
    def _get_bucket_time(self, timestamp: datetime, interval_seconds: int) -> datetime:
        """Get bucket time for a timestamp."""
        return self._round_to_bucket(timestamp, interval_seconds)
    
    def _calculate_aggregation(self, values: List[float], aggregation: AggregationType, percentile: Optional[float] = None) -> float:
        """Calculate aggregation for a list of values."""
        if not values:
            return 0.0
        
        if aggregation == AggregationType.SUM:
            return sum(values)
        elif aggregation == AggregationType.AVG:
            return statistics.mean(values)
        elif aggregation == AggregationType.MIN:
            return min(values)
        elif aggregation == AggregationType.MAX:
            return max(values)
        elif aggregation == AggregationType.COUNT:
            return len(values)
        elif aggregation == AggregationType.MEDIAN:
            return statistics.median(values)
        elif aggregation == AggregationType.PERCENTILE:
            if percentile is not None:
                return self._calculate_percentile(values, percentile)
            else:
                return statistics.median(values)
        elif aggregation == AggregationType.RATE:
            # Calculate rate as difference between first and last value divided by time
            return values[-1] - values[0] if len(values) > 1 else 0.0
        elif aggregation == AggregationType.DELTA:
            # Calculate delta as difference between first and last value
            return values[-1] - values[0] if len(values) > 1 else 0.0
        else:
            return statistics.mean(values)
    
    def _calculate_percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile value."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = (percentile / 100.0) * (len(sorted_values) - 1)
        
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            weight = index - int(index)
            return lower + weight * (upper - lower)
    
    def get_metric_summary(self, metric_name: str) -> Optional[Dict[str, Any]]:
        """Get summary information for a metric."""
        with self._lock:
            if metric_name not in self.metrics:
                return None
            
            data_points = list(self.metrics[metric_name])
            if not data_points:
                return None
            
            values = [dp.value for dp in data_points]
            
            return {
                'metric_name': metric_name,
                'total_points': len(data_points),
                'first_timestamp': data_points[0].timestamp.isoformat(),
                'last_timestamp': data_points[-1].timestamp.isoformat(),
                'min_value': min(values),
                'max_value': max(values),
                'avg_value': statistics.mean(values),
                'median_value': statistics.median(values),
                'std_value': statistics.stdev(values) if len(values) > 1 else 0.0,
                'metadata': self.metric_metadata.get(metric_name, {})
            }
    
    def list_metrics(self) -> List[str]:
        """List all available metrics."""
        with self._lock:
            return list(self.metrics.keys())
    
    def get_metrics_overview(self) -> Dict[str, Any]:
        """Get overview of all metrics."""
        with self._lock:
            metrics_info = {}
            
            for metric_name in self.metrics.keys():
                summary = self.get_metric_summary(metric_name)
                if summary:
                    metrics_info[metric_name] = summary
            
            return {
                'total_metrics': len(metrics_info),
                'total_data_points': sum(info['total_points'] for info in metrics_info.values()),
                'metrics': metrics_info,
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
    
    def delete_metric(self, metric_name: str) -> bool:
        """Delete a metric and all its data."""
        with self._lock:
            if metric_name in self.metrics:
                del self.metrics[metric_name]
                if metric_name in self.metric_metadata:
                    del self.metric_metadata[metric_name]
                logger.info(f"Deleted metric: {metric_name}")
                return True
            return False
    
    def clear_all_metrics(self) -> None:
        """Clear all metrics data."""
        with self._lock:
            self.metrics.clear()
            self.metric_metadata.clear()
            logger.info("Cleared all metrics data")
    
    def close(self) -> None:
        """Close the metrics aggregator and cleanup resources."""
        self._stop_cleanup.set()
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5.0)
        logger.info("Metrics aggregator closed")
