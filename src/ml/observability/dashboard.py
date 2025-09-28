"""
Dashboard system for ML observability and monitoring.
Provides real-time dashboards with customizable widgets and metrics.
"""

import time
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import uuid

logger = logging.getLogger(__name__)


class WidgetType(Enum):
    """Dashboard widget types."""
    METRIC_CARD = "metric_card"
    LINE_CHART = "line_chart"
    BAR_CHART = "bar_chart"
    PIE_CHART = "pie_chart"
    TABLE = "table"
    HEATMAP = "heatmap"
    GAUGE = "gauge"
    ALERT_LIST = "alert_list"
    LOG_VIEWER = "log_viewer"
    STATUS_GRID = "status_grid"


class MetricType(Enum):
    """Metric types for widgets."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"
    CUSTOM = "custom"


@dataclass
class DashboardWidget:
    """Container for dashboard widget configuration."""
    widget_id: str
    widget_type: WidgetType
    title: str
    description: str = ""
    position: Dict[str, int] = field(default_factory=lambda: {"x": 0, "y": 0, "w": 4, "h": 3})
    config: Dict[str, Any] = field(default_factory=dict)
    refresh_interval: int = 30  # seconds
    data_source: Optional[str] = None
    filters: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'widget_id': self.widget_id,
            'widget_type': self.widget_type.value,
            'title': self.title,
            'description': self.description,
            'position': self.position,
            'config': self.config,
            'refresh_interval': self.refresh_interval,
            'data_source': self.data_source,
            'filters': self.filters,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


@dataclass
class DashboardConfig:
    """Configuration for dashboard."""
    dashboard_id: str
    name: str
    description: str = ""
    layout: str = "grid"  # "grid", "flex", "custom"
    theme: str = "light"  # "light", "dark", "auto"
    auto_refresh: bool = True
    refresh_interval: int = 60  # seconds
    time_range: str = "1h"  # "5m", "15m", "1h", "6h", "24h", "7d", "30d"
    timezone: str = "UTC"
    permissions: Dict[str, List[str]] = field(default_factory=dict)
    created_by: str = "system"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'dashboard_id': self.dashboard_id,
            'name': self.name,
            'description': self.description,
            'layout': self.layout,
            'theme': self.theme,
            'auto_refresh': self.auto_refresh,
            'refresh_interval': self.refresh_interval,
            'time_range': self.time_range,
            'timezone': self.timezone,
            'permissions': self.permissions,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class Dashboard:
    """
    Dashboard system for ML observability.
    """
    
    def __init__(self, config: DashboardConfig):
        self.config = config
        self.widgets: Dict[str, DashboardWidget] = {}
        self.data_providers: Dict[str, Callable] = {}
        self.refresh_tasks: Dict[str, Any] = {}
        self.is_active = False
        
        logger.info(f"Initialized dashboard: {config.name}")
    
    def add_widget(self, widget: DashboardWidget) -> None:
        """Add a widget to the dashboard."""
        self.widgets[widget.widget_id] = widget
        
        # Register data provider if specified
        if widget.data_source:
            self._register_data_provider(widget)
        
        logger.info(f"Added widget {widget.title} to dashboard {self.config.name}")
    
    def remove_widget(self, widget_id: str) -> bool:
        """Remove a widget from the dashboard."""
        if widget_id in self.widgets:
            del self.widgets[widget_id]
            
            # Clean up refresh task
            if widget_id in self.refresh_tasks:
                del self.refresh_tasks[widget_id]
            
            logger.info(f"Removed widget {widget_id} from dashboard {self.config.name}")
            return True
        return False
    
    def update_widget(self, widget_id: str, updates: Dict[str, Any]) -> bool:
        """Update widget configuration."""
        if widget_id not in self.widgets:
            return False
        
        widget = self.widgets[widget_id]
        
        # Update fields
        for key, value in updates.items():
            if hasattr(widget, key):
                setattr(widget, key, value)
        
        widget.updated_at = datetime.now(timezone.utc)
        
        logger.info(f"Updated widget {widget_id}")
        return True
    
    def get_widget_data(self, widget_id: str, time_range: Optional[str] = None) -> Dict[str, Any]:
        """Get data for a specific widget."""
        if widget_id not in self.widgets:
            return {"error": "Widget not found"}
        
        widget = self.widgets[widget_id]
        
        # Use provided time range or widget default
        effective_time_range = time_range or self.config.time_range
        
        try:
            # Get data from provider
            if widget.data_source and widget.data_source in self.data_providers:
                data = self.data_providers[widget.data_source](widget, effective_time_range)
            else:
                # Generate mock data based on widget type
                data = self._generate_mock_data(widget, effective_time_range)
            
            return {
                "widget_id": widget_id,
                "data": data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "time_range": effective_time_range
            }
            
        except Exception as e:
            logger.error(f"Error getting data for widget {widget_id}: {e}")
            return {"error": str(e)}
    
    def get_dashboard_data(self, time_range: Optional[str] = None) -> Dict[str, Any]:
        """Get data for all widgets in the dashboard."""
        effective_time_range = time_range or self.config.time_range
        
        dashboard_data = {
            "dashboard_id": self.config.dashboard_id,
            "name": self.config.name,
            "time_range": effective_time_range,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "widgets": {}
        }
        
        for widget_id, widget in self.widgets.items():
            try:
                widget_data = self.get_widget_data(widget_id, effective_time_range)
                dashboard_data["widgets"][widget_id] = widget_data
            except Exception as e:
                logger.error(f"Error getting data for widget {widget_id}: {e}")
                dashboard_data["widgets"][widget_id] = {"error": str(e)}
        
        return dashboard_data
    
    def register_data_provider(self, name: str, provider: Callable) -> None:
        """Register a data provider function."""
        self.data_providers[name] = provider
        logger.info(f"Registered data provider: {name}")
    
    def _register_data_provider(self, widget: DashboardWidget) -> None:
        """Register data provider for a widget."""
        if widget.data_source not in self.data_providers:
            # Create a default provider
            self.data_providers[widget.data_source] = lambda w, tr: self._generate_mock_data(w, tr)
    
    def _generate_mock_data(self, widget: DashboardWidget, time_range: str) -> Dict[str, Any]:
        """Generate mock data for a widget."""
        now = datetime.now(timezone.utc)
        
        # Parse time range
        time_delta = self._parse_time_range(time_range)
        start_time = now - time_delta
        
        if widget.widget_type == WidgetType.METRIC_CARD:
            return {
                "value": 85.6,
                "unit": "%",
                "trend": "up",
                "trend_value": 2.3,
                "status": "good"
            }
        
        elif widget.widget_type == WidgetType.LINE_CHART:
            # Generate time series data
            points = []
            current_time = start_time
            interval = timedelta(seconds=time_delta.total_seconds() / 100)
            
            for i in range(100):
                points.append({
                    "timestamp": current_time.isoformat(),
                    "value": 50 + 30 * (i / 100) + (i % 10) * 2
                })
                current_time += interval
            
            return {
                "series": [
                    {
                        "name": "Metric",
                        "data": points
                    }
                ]
            }
        
        elif widget.widget_type == WidgetType.BAR_CHART:
            return {
                "categories": ["Model A", "Model B", "Model C", "Model D"],
                "series": [
                    {
                        "name": "Accuracy",
                        "data": [0.85, 0.92, 0.78, 0.89]
                    },
                    {
                        "name": "Precision",
                        "data": [0.82, 0.89, 0.75, 0.86]
                    }
                ]
            }
        
        elif widget.widget_type == WidgetType.PIE_CHART:
            return {
                "series": [
                    {"name": "Success", "value": 75, "color": "#28a745"},
                    {"name": "Warning", "value": 15, "color": "#ffc107"},
                    {"name": "Error", "value": 10, "color": "#dc3545"}
                ]
            }
        
        elif widget.widget_type == WidgetType.TABLE:
            return {
                "columns": ["Model", "Accuracy", "Status", "Last Update"],
                "rows": [
                    ["Model A", "0.92", "Active", "2 min ago"],
                    ["Model B", "0.89", "Active", "5 min ago"],
                    ["Model C", "0.85", "Training", "10 min ago"],
                    ["Model D", "0.78", "Error", "1 hour ago"]
                ]
            }
        
        elif widget.widget_type == WidgetType.GAUGE:
            return {
                "value": 75.5,
                "min": 0,
                "max": 100,
                "unit": "%",
                "thresholds": [
                    {"value": 80, "color": "green"},
                    {"value": 60, "color": "yellow"},
                    {"value": 40, "color": "red"}
                ]
            }
        
        elif widget.widget_type == WidgetType.ALERT_LIST:
            return {
                "alerts": [
                    {
                        "id": "alert-1",
                        "severity": "warning",
                        "message": "Model accuracy below threshold",
                        "timestamp": (now - timedelta(minutes=5)).isoformat(),
                        "status": "active"
                    },
                    {
                        "id": "alert-2",
                        "severity": "info",
                        "message": "New model deployed successfully",
                        "timestamp": (now - timedelta(minutes=15)).isoformat(),
                        "status": "resolved"
                    }
                ]
            }
        
        elif widget.widget_type == WidgetType.STATUS_GRID:
            return {
                "services": [
                    {"name": "Model Server", "status": "healthy", "uptime": "99.9%"},
                    {"name": "Load Balancer", "status": "healthy", "uptime": "99.8%"},
                    {"name": "Database", "status": "warning", "uptime": "98.5%"},
                    {"name": "Cache", "status": "healthy", "uptime": "99.7%"}
                ]
            }
        
        else:
            return {"message": f"Mock data for {widget.widget_type.value}"}
    
    def _parse_time_range(self, time_range: str) -> timedelta:
        """Parse time range string to timedelta."""
        time_range_map = {
            "5m": timedelta(minutes=5),
            "15m": timedelta(minutes=15),
            "1h": timedelta(hours=1),
            "6h": timedelta(hours=6),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30)
        }
        return time_range_map.get(time_range, timedelta(hours=1))
    
    def export_dashboard(self) -> Dict[str, Any]:
        """Export dashboard configuration and data."""
        return {
            "config": self.config.to_dict(),
            "widgets": [widget.to_dict() for widget in self.widgets.values()],
            "exported_at": datetime.now(timezone.utc).isoformat()
        }
    
    def import_dashboard(self, data: Dict[str, Any]) -> bool:
        """Import dashboard configuration."""
        try:
            # Import config
            config_data = data.get("config", {})
            self.config.name = config_data.get("name", self.config.name)
            self.config.description = config_data.get("description", self.config.description)
            self.config.layout = config_data.get("layout", self.config.layout)
            self.config.theme = config_data.get("theme", self.config.theme)
            
            # Import widgets
            widgets_data = data.get("widgets", [])
            for widget_data in widgets_data:
                widget = DashboardWidget(
                    widget_id=widget_data["widget_id"],
                    widget_type=WidgetType(widget_data["widget_type"]),
                    title=widget_data["title"],
                    description=widget_data.get("description", ""),
                    position=widget_data.get("position", {"x": 0, "y": 0, "w": 4, "h": 3}),
                    config=widget_data.get("config", {}),
                    refresh_interval=widget_data.get("refresh_interval", 30),
                    data_source=widget_data.get("data_source"),
                    filters=widget_data.get("filters", {})
                )
                self.widgets[widget.widget_id] = widget
            
            logger.info(f"Imported dashboard: {self.config.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error importing dashboard: {e}")
            return False
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get dashboard summary information."""
        widget_types = {}
        for widget in self.widgets.values():
            widget_type = widget.widget_type.value
            widget_types[widget_type] = widget_types.get(widget_type, 0) + 1
        
        return {
            "dashboard_id": self.config.dashboard_id,
            "name": self.config.name,
            "total_widgets": len(self.widgets),
            "widget_types": widget_types,
            "layout": self.config.layout,
            "theme": self.config.theme,
            "auto_refresh": self.config.auto_refresh,
            "refresh_interval": self.config.refresh_interval,
            "created_at": self.config.created_at.isoformat(),
            "updated_at": self.config.updated_at.isoformat()
        }
