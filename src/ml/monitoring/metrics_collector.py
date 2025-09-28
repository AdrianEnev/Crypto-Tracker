"""
Metrics Collection for ML trading systems.
Collects and aggregates various system and model metrics.
"""

import time
import threading
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """Container for system-level metrics."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_used_gb: float
    disk_available_gb: float
    network_bytes_sent: int
    network_bytes_received: int
    load_average: Optional[float] = None
    process_count: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class TradingMetrics:
    """Container for trading-specific metrics."""
    timestamp: datetime
    total_trades: int
    successful_trades: int
    failed_trades: int
    total_volume: float
    total_pnl: float
    daily_pnl: float
    max_drawdown: float
    sharpe_ratio: Optional[float] = None
    win_rate: Optional[float] = None
    avg_trade_duration: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class MetricsCollector:
    """
    Comprehensive metrics collection for ML trading systems.
    """
    
    def __init__(self, 
                 collection_interval: int = 30,
                 max_history_size: int = 10000,
                 enable_system_metrics: bool = True,
                 enable_trading_metrics: bool = True):
        """
        Initialize metrics collector.
        
        Args:
            collection_interval: Interval between metric collections (seconds)
            max_history_size: Maximum number of metric records to keep
            enable_system_metrics: Whether to collect system metrics
            enable_trading_metrics: Whether to collect trading metrics
        """
        self.collection_interval = collection_interval
        self.max_history_size = max_history_size
        self.enable_system_metrics = enable_system_metrics
        self.enable_trading_metrics = enable_trading_metrics
        
        # Metrics storage
        self.system_metrics_history: deque = deque(maxlen=max_history_size)
        self.trading_metrics_history: deque = deque(maxlen=max_history_size)
        self.custom_metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history_size))
        
        # Collection state
        self.is_collecting = False
        self.collection_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Trading metrics tracking
        self.trading_stats = {
            'total_trades': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'total_volume': 0.0,
            'total_pnl': 0.0,
            'daily_pnl': 0.0,
            'max_drawdown': 0.0,
            'trade_durations': deque(maxlen=1000),
            'pnl_history': deque(maxlen=1000),
            'last_reset_date': datetime.now(timezone.utc).date()
        }
        
        # Custom metrics callbacks
        self.custom_metrics_callbacks: Dict[str, Callable[[], Any]] = {}
        
        # Network metrics tracking
        self.last_network_stats = None
        
        logger.info("Initialized metrics collector")
    
    def start_collection(self) -> None:
        """Start automatic metrics collection."""
        if self.is_collecting:
            logger.warning("Metrics collection is already running")
            return
        
        self.is_collecting = True
        self.stop_event.clear()
        self.collection_thread = threading.Thread(target=self._collection_loop, daemon=True)
        self.collection_thread.start()
        
        logger.info(f"Started metrics collection with {self.collection_interval}s interval")
    
    def stop_collection(self) -> None:
        """Stop automatic metrics collection."""
        if not self.is_collecting:
            return
        
        self.is_collecting = False
        self.stop_event.set()
        
        if self.collection_thread:
            self.collection_thread.join(timeout=5)
        
        logger.info("Stopped metrics collection")
    
    def _collection_loop(self) -> None:
        """Main collection loop."""
        while not self.stop_event.is_set():
            try:
                # Collect system metrics
                if self.enable_system_metrics:
                    system_metrics = self._collect_system_metrics()
                    if system_metrics:
                        self.system_metrics_history.append(system_metrics)
                
                # Collect trading metrics
                if self.enable_trading_metrics:
                    trading_metrics = self._collect_trading_metrics()
                    if trading_metrics:
                        self.trading_metrics_history.append(trading_metrics)
                
                # Collect custom metrics
                for metric_name, callback in self.custom_metrics_callbacks.items():
                    try:
                        value = callback()
                        timestamp = datetime.now(timezone.utc)
                        self.custom_metrics_history[metric_name].append((timestamp, value))
                    except Exception as e:
                        logger.error(f"Error collecting custom metric {metric_name}: {e}")
                
                # Wait for next collection
                self.stop_event.wait(self.collection_interval)
                
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
                self.stop_event.wait(5)  # Wait 5 seconds before retrying
    
    def _collect_system_metrics(self) -> Optional[SystemMetrics]:
        """Collect system resource metrics."""
        try:
            import psutil
            
            # CPU and memory
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_available = disk.free if hasattr(disk, 'free') else (disk.total - disk.used)
            
            # Network I/O
            network = psutil.net_io_counters()
            network_bytes_sent = network.bytes_sent
            network_bytes_received = network.bytes_recv
            
            # Update network tracking for delta calculation
            if self.last_network_stats:
                network_bytes_sent -= self.last_network_stats['bytes_sent']
                network_bytes_received -= self.last_network_stats['bytes_recv']
            
            self.last_network_stats = {
                'bytes_sent': network.bytes_sent,
                'bytes_recv': network.bytes_recv
            }
            
            # Load average (Unix-like systems)
            try:
                load_avg = psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else None
            except AttributeError:
                load_avg = None
            
            # Process count
            try:
                process_count = len(psutil.pids())
            except:
                process_count = None
            
            return SystemMetrics(
                timestamp=datetime.now(timezone.utc),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / 1024 / 1024,
                memory_available_mb=memory.available / 1024 / 1024,
                disk_usage_percent=(disk.used / disk.total) * 100,
                disk_used_gb=disk.used / 1024 / 1024 / 1024,
                disk_available_gb=disk_available / 1024 / 1024 / 1024,
                network_bytes_sent=network_bytes_sent,
                network_bytes_received=network_bytes_received,
                load_average=load_avg,
                process_count=process_count
            )
            
        except ImportError:
            logger.warning("psutil not available for system metrics collection")
            return None
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return None
    
    def _collect_trading_metrics(self) -> Optional[TradingMetrics]:
        """Collect trading-specific metrics."""
        try:
            # Calculate win rate
            total_trades = self.trading_stats['total_trades']
            win_rate = None
            if total_trades > 0:
                win_rate = self.trading_stats['successful_trades'] / total_trades
            
            # Calculate Sharpe ratio (simplified)
            sharpe_ratio = None
            if len(self.trading_stats['pnl_history']) > 1:
                pnl_values = list(self.trading_stats['pnl_history'])
                if len(pnl_values) > 10:  # Need sufficient data
                    returns = np.diff(pnl_values)
                    if len(returns) > 0 and np.std(returns) > 0:
                        sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)  # Annualized
            
            # Calculate average trade duration
            avg_trade_duration = None
            if self.trading_stats['trade_durations']:
                avg_trade_duration = np.mean(list(self.trading_stats['trade_durations']))
            
            # Check if we need to reset daily PnL
            current_date = datetime.now(timezone.utc).date()
            if current_date != self.trading_stats['last_reset_date']:
                self.trading_stats['daily_pnl'] = 0.0
                self.trading_stats['last_reset_date'] = current_date
            
            return TradingMetrics(
                timestamp=datetime.now(timezone.utc),
                total_trades=total_trades,
                successful_trades=self.trading_stats['successful_trades'],
                failed_trades=self.trading_stats['failed_trades'],
                total_volume=self.trading_stats['total_volume'],
                total_pnl=self.trading_stats['total_pnl'],
                daily_pnl=self.trading_stats['daily_pnl'],
                max_drawdown=self.trading_stats['max_drawdown'],
                sharpe_ratio=sharpe_ratio,
                win_rate=win_rate,
                avg_trade_duration=avg_trade_duration
            )
            
        except Exception as e:
            logger.error(f"Error collecting trading metrics: {e}")
            return None
    
    def record_trade(self, 
                    success: bool, 
                    volume: float, 
                    pnl: float, 
                    duration_seconds: Optional[float] = None) -> None:
        """
        Record a trade for metrics tracking.
        
        Args:
            success: Whether the trade was successful
            volume: Trade volume
            pnl: Profit/Loss from the trade
            duration_seconds: Trade duration in seconds
        """
        self.trading_stats['total_trades'] += 1
        self.trading_stats['total_volume'] += volume
        self.trading_stats['total_pnl'] += pnl
        self.trading_stats['daily_pnl'] += pnl
        
        if success:
            self.trading_stats['successful_trades'] += 1
        else:
            self.trading_stats['failed_trades'] += 1
        
        # Track trade duration
        if duration_seconds is not None:
            self.trading_stats['trade_durations'].append(duration_seconds)
        
        # Track PnL history for drawdown calculation
        self.trading_stats['pnl_history'].append(self.trading_stats['total_pnl'])
        
        # Update max drawdown
        if len(self.trading_stats['pnl_history']) > 1:
            pnl_values = list(self.trading_stats['pnl_history'])
            peak = pnl_values[0]
            max_dd = 0
            
            for value in pnl_values:
                if value > peak:
                    peak = value
                drawdown = (peak - value) / peak if peak > 0 else 0
                max_dd = max(max_dd, drawdown)
            
            self.trading_stats['max_drawdown'] = max_dd
    
    def register_custom_metric(self, name: str, callback: Callable[[], Any]) -> None:
        """
        Register a custom metric to be collected.
        
        Args:
            name: Name of the metric
            callback: Function that returns the metric value
        """
        self.custom_metrics_callbacks[name] = callback
        logger.info(f"Registered custom metric: {name}")
    
    def unregister_custom_metric(self, name: str) -> None:
        """Unregister a custom metric."""
        if name in self.custom_metrics_callbacks:
            del self.custom_metrics_callbacks[name]
            logger.info(f"Unregistered custom metric: {name}")
    
    def get_system_metrics(self, hours: int = 24) -> List[SystemMetrics]:
        """Get recent system metrics."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        return [
            metrics for metrics in self.system_metrics_history
            if metrics.timestamp > cutoff_time
        ]
    
    def get_trading_metrics(self, hours: int = 24) -> List[TradingMetrics]:
        """Get recent trading metrics."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        return [
            metrics for metrics in self.trading_metrics_history
            if metrics.timestamp > cutoff_time
        ]
    
    def get_custom_metrics(self, name: str, hours: int = 24) -> List[tuple]:
        """Get recent custom metrics by name."""
        if name not in self.custom_metrics_history:
            return []
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        return [
            (timestamp, value) for timestamp, value in self.custom_metrics_history[name]
            if timestamp > cutoff_time
        ]
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        summary = {
            'collection_status': {
                'is_collecting': self.is_collecting,
                'collection_interval': self.collection_interval,
                'total_system_metrics': len(self.system_metrics_history),
                'total_trading_metrics': len(self.trading_metrics_history),
                'custom_metrics_count': len(self.custom_metrics_callbacks)
            },
            'trading_summary': {
                'total_trades': self.trading_stats['total_trades'],
                'successful_trades': self.trading_stats['successful_trades'],
                'failed_trades': self.trading_stats['failed_trades'],
                'win_rate': self.trading_stats['successful_trades'] / max(self.trading_stats['total_trades'], 1),
                'total_volume': self.trading_stats['total_volume'],
                'total_pnl': self.trading_stats['total_pnl'],
                'daily_pnl': self.trading_stats['daily_pnl'],
                'max_drawdown': self.trading_stats['max_drawdown']
            }
        }
        
        # Add recent system metrics summary
        recent_system_metrics = self.get_system_metrics(hours=1)
        if recent_system_metrics:
            latest = recent_system_metrics[-1]
            summary['current_system_status'] = {
                'cpu_percent': latest.cpu_percent,
                'memory_percent': latest.memory_percent,
                'disk_usage_percent': latest.disk_usage_percent,
                'timestamp': latest.timestamp.isoformat()
            }
        
        return summary
    
    def export_metrics(self, format: str = 'json', hours: int = 24) -> str:
        """Export metrics in specified format."""
        if format == 'json':
            import json
            
            data = {
                'summary': self.get_metrics_summary(),
                'system_metrics': [m.to_dict() for m in self.get_system_metrics(hours)],
                'trading_metrics': [m.to_dict() for m in self.get_trading_metrics(hours)],
                'custom_metrics': {
                    name: [{'timestamp': t.isoformat(), 'value': v} for t, v in self.get_custom_metrics(name, hours)]
                    for name in self.custom_metrics_callbacks.keys()
                }
            }
            return json.dumps(data, indent=2)
        
        elif format == 'csv':
            import pandas as pd
            
            # Export system metrics
            system_df = pd.DataFrame([m.to_dict() for m in self.get_system_metrics(hours)])
            system_csv = system_df.to_csv(index=False) if not system_df.empty else ""
            
            # Export trading metrics
            trading_df = pd.DataFrame([m.to_dict() for m in self.get_trading_metrics(hours)])
            trading_csv = trading_df.to_csv(index=False) if not trading_df.empty else ""
            
            return f"System Metrics:\n{system_csv}\n\nTrading Metrics:\n{trading_csv}"
        
        else:
            raise ValueError(f"Unsupported format: {format}")
