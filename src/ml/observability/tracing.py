"""
Distributed tracing system for ML observability.
Provides request tracing and performance monitoring capabilities.
"""

import time
import uuid
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class TraceSampler:
    """Trace sampling strategy."""
    
    def __init__(self, sample_rate: float = 1.0):
        self.sample_rate = sample_rate
    
    def should_sample(self, trace_id: str) -> bool:
        """Determine if a trace should be sampled."""
        # Simple hash-based sampling
        hash_val = hash(trace_id) % 100
        return hash_val < (self.sample_rate * 100)


@dataclass
class TraceContext:
    """Container for trace context information."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    baggage: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'trace_id': self.trace_id,
            'span_id': self.span_id,
            'parent_span_id': self.parent_span_id,
            'baggage': self.baggage
        }


@dataclass
class TraceSpan:
    """Container for trace span data."""
    span_id: str
    trace_id: str
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    parent_span_id: Optional[str] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "started"
    
    def finish(self, status: str = "completed") -> None:
        """Finish the span."""
        self.end_time = datetime.now(timezone.utc)
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.status = status
    
    def add_log(self, message: str, level: str = "info", **kwargs) -> None:
        """Add a log entry to the span."""
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'message': message,
            'level': level,
            **kwargs
        }
        self.logs.append(log_entry)
    
    def set_tag(self, key: str, value: Any) -> None:
        """Set a tag on the span."""
        self.tags[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'span_id': self.span_id,
            'trace_id': self.trace_id,
            'operation_name': self.operation_name,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_ms': self.duration_ms,
            'parent_span_id': self.parent_span_id,
            'tags': self.tags,
            'logs': self.logs,
            'status': self.status
        }


class TraceCollector:
    """
    Distributed trace collector for ML observability.
    """
    
    def __init__(self, max_spans: int = 10000):
        self.max_spans = max_spans
        self.spans: Dict[str, TraceSpan] = {}
        self.traces: Dict[str, List[str]] = {}
        self.sampler = TraceSampler(sample_rate=1.0)
        self._lock = threading.RLock()
        
        logger.info(f"Initialized trace collector: max_spans={max_spans}")
    
    def start_span(self, 
                   operation_name: str,
                   trace_id: Optional[str] = None,
                   parent_span_id: Optional[str] = None,
                   tags: Optional[Dict[str, Any]] = None) -> TraceSpan:
        """Start a new trace span."""
        if trace_id is None:
            trace_id = str(uuid.uuid4())
        
        span_id = str(uuid.uuid4())
        
        span = TraceSpan(
            span_id=span_id,
            trace_id=trace_id,
            operation_name=operation_name,
            start_time=datetime.now(timezone.utc),
            parent_span_id=parent_span_id,
            tags=tags or {}
        )
        
        with self._lock:
            self.spans[span_id] = span
            
            # Track spans by trace
            if trace_id not in self.traces:
                self.traces[trace_id] = []
            self.traces[trace_id].append(span_id)
            
            # Enforce max spans limit
            if len(self.spans) > self.max_spans:
                self._evict_oldest_spans()
        
        return span
    
    def finish_span(self, span_id: str, status: str = "completed") -> bool:
        """Finish a trace span."""
        with self._lock:
            if span_id not in self.spans:
                return False
            
            span = self.spans[span_id]
            span.finish(status)
            return True
    
    def get_span(self, span_id: str) -> Optional[TraceSpan]:
        """Get a span by ID."""
        with self._lock:
            return self.spans.get(span_id)
    
    def get_trace(self, trace_id: str) -> List[TraceSpan]:
        """Get all spans for a trace."""
        with self._lock:
            if trace_id not in self.traces:
                return []
            
            span_ids = self.traces[trace_id]
            return [self.spans[span_id] for span_id in span_ids if span_id in self.spans]
    
    def get_trace_summary(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Get summary information for a trace."""
        spans = self.get_trace(trace_id)
        if not spans:
            return None
        
        # Sort spans by start time
        spans.sort(key=lambda s: s.start_time)
        
        total_duration = 0
        if spans:
            start_time = spans[0].start_time
            end_time = max(span.end_time or span.start_time for span in spans)
            total_duration = (end_time - start_time).total_seconds() * 1000
        
        return {
            'trace_id': trace_id,
            'span_count': len(spans),
            'total_duration_ms': total_duration,
            'start_time': spans[0].start_time.isoformat(),
            'end_time': max(span.end_time or span.start_time for span in spans).isoformat(),
            'spans': [span.to_dict() for span in spans]
        }
    
    def _evict_oldest_spans(self) -> None:
        """Evict oldest spans to maintain max_spans limit."""
        # Sort spans by start time
        sorted_spans = sorted(self.spans.items(), key=lambda x: x[1].start_time)
        
        # Remove oldest 10% of spans
        evict_count = max(1, len(sorted_spans) // 10)
        
        for span_id, span in sorted_spans[:evict_count]:
            del self.spans[span_id]
            
            # Remove from traces
            if span.trace_id in self.traces:
                if span_id in self.traces[span.trace_id]:
                    self.traces[span.trace_id].remove(span_id)
                
                # Remove empty traces
                if not self.traces[span.trace_id]:
                    del self.traces[span.trace_id]
    
    def list_traces(self, limit: int = 100) -> List[str]:
        """List recent trace IDs."""
        with self._lock:
            trace_ids = list(self.traces.keys())
            # Sort by most recent activity
            trace_ids.sort(key=lambda tid: max(
                span.start_time for span in self.get_trace(tid)
            ), reverse=True)
            return trace_ids[:limit]
    
    def get_collector_stats(self) -> Dict[str, Any]:
        """Get collector statistics."""
        with self._lock:
            total_spans = len(self.spans)
            total_traces = len(self.traces)
            
            # Calculate average spans per trace
            avg_spans_per_trace = total_spans / total_traces if total_traces > 0 else 0
            
            return {
                'total_spans': total_spans,
                'total_traces': total_traces,
                'max_spans': self.max_spans,
                'avg_spans_per_trace': avg_spans_per_trace,
                'sample_rate': self.sampler.sample_rate
            }
    
    @contextmanager
    def span(self, operation_name: str, **kwargs):
        """Context manager for creating spans."""
        span = self.start_span(operation_name, **kwargs)
        try:
            yield span
        except Exception as e:
            span.set_tag('error', True)
            span.add_log(f"Error in {operation_name}: {str(e)}", level='error')
            span.finish('error')
            raise
        else:
            span.finish('completed')
