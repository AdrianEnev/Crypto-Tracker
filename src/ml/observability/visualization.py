"""
Visualization system for ML observability.
Provides chart generation and visualization capabilities.
"""

import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ChartType(Enum):
    """Chart types for visualization."""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    SCATTER = "scatter"
    AREA = "area"
    HISTOGRAM = "histogram"
    HEATMAP = "heatmap"
    GAUGE = "gauge"
    DONUT = "donut"
    STACKED_BAR = "stacked_bar"


@dataclass
class VisualizationEngine:
    """Visualization engine for generating charts."""
    
    def generate_chart_config(self, 
                             chart_type: ChartType,
                             data: Dict[str, Any],
                             title: str = "",
                             width: int = 800,
                             height: int = 400,
                             theme: str = "light") -> Dict[str, Any]:
        """Generate chart configuration."""
        base_config = {
            "title": {"text": title, "left": "center"},
            "width": width,
            "height": height,
            "theme": theme
        }
        
        if chart_type == ChartType.LINE:
            return self._generate_line_chart_config(data, base_config)
        elif chart_type == ChartType.BAR:
            return self._generate_bar_chart_config(data, base_config)
        elif chart_type == ChartType.PIE:
            return self._generate_pie_chart_config(data, base_config)
        elif chart_type == ChartType.SCATTER:
            return self._generate_scatter_chart_config(data, base_config)
        elif chart_type == ChartType.AREA:
            return self._generate_area_chart_config(data, base_config)
        elif chart_type == ChartType.HISTOGRAM:
            return self._generate_histogram_config(data, base_config)
        elif chart_type == ChartType.HEATMAP:
            return self._generate_heatmap_config(data, base_config)
        elif chart_type == ChartType.GAUGE:
            return self._generate_gauge_config(data, base_config)
        elif chart_type == ChartType.DONUT:
            return self._generate_donut_config(data, base_config)
        elif chart_type == ChartType.STACKED_BAR:
            return self._generate_stacked_bar_config(data, base_config)
        else:
            return base_config
    
    def _generate_line_chart_config(self, data: Dict[str, Any], base_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate line chart configuration."""
        config = base_config.copy()
        config.update({
            "tooltip": {"trigger": "axis"},
            "legend": {"data": data.get("series_names", [])},
            "xAxis": {
                "type": "category",
                "data": data.get("x_data", [])
            },
            "yAxis": {"type": "value"},
            "series": []
        })
        
        for i, series_data in enumerate(data.get("series_data", [])):
            series_name = data.get("series_names", [f"Series {i+1}"])[i] if i < len(data.get("series_names", [])) else f"Series {i+1}"
            config["series"].append({
                "name": series_name,
                "type": "line",
                "data": series_data
            })
        
        return config
    
    def _generate_bar_chart_config(self, data: Dict[str, Any], base_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate bar chart configuration."""
        config = base_config.copy()
        config.update({
            "tooltip": {"trigger": "axis"},
            "legend": {"data": data.get("series_names", [])},
            "xAxis": {
                "type": "category",
                "data": data.get("x_data", [])
            },
            "yAxis": {"type": "value"},
            "series": []
        })
        
        for i, series_data in enumerate(data.get("series_data", [])):
            series_name = data.get("series_names", [f"Series {i+1}"])[i] if i < len(data.get("series_names", [])) else f"Series {i+1}"
            config["series"].append({
                "name": series_name,
                "type": "bar",
                "data": series_data
            })
        
        return config
    
    def _generate_pie_chart_config(self, data: Dict[str, Any], base_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate pie chart configuration."""
        config = base_config.copy()
        config.update({
            "tooltip": {"trigger": "item"},
            "series": [{
                "name": data.get("name", "Data"),
                "type": "pie",
                "radius": "50%",
                "data": data.get("data", []),
                "emphasis": {
                    "itemStyle": {
                        "shadowBlur": 10,
                        "shadowOffsetX": 0,
                        "shadowColor": "rgba(0, 0, 0, 0.5)"
                    }
                }
            }]
        })
        
        return config
    
    def _generate_scatter_chart_config(self, data: Dict[str, Any], base_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate scatter chart configuration."""
        config = base_config.copy()
        config.update({
            "tooltip": {"trigger": "item"},
            "xAxis": {"type": "value"},
            "yAxis": {"type": "value"},
            "series": [{
                "name": data.get("name", "Data"),
                "type": "scatter",
                "data": data.get("data", [])
            }]
        })
        
        return config
    
    def _generate_area_chart_config(self, data: Dict[str, Any], base_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate area chart configuration."""
        config = base_config.copy()
        config.update({
            "tooltip": {"trigger": "axis"},
            "legend": {"data": data.get("series_names", [])},
            "xAxis": {
                "type": "category",
                "data": data.get("x_data", [])
            },
            "yAxis": {"type": "value"},
            "series": []
        })
        
        for i, series_data in enumerate(data.get("series_data", [])):
            series_name = data.get("series_names", [f"Series {i+1}"])[i] if i < len(data.get("series_names", [])) else f"Series {i+1}"
            config["series"].append({
                "name": series_name,
                "type": "line",
                "areaStyle": {},
                "data": series_data
            })
        
        return config
    
    def _generate_histogram_config(self, data: Dict[str, Any], base_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate histogram configuration."""
        config = base_config.copy()
        config.update({
            "tooltip": {"trigger": "axis"},
            "xAxis": {
                "type": "category",
                "data": data.get("bins", [])
            },
            "yAxis": {"type": "value"},
            "series": [{
                "name": data.get("name", "Frequency"),
                "type": "bar",
                "data": data.get("frequencies", [])
            }]
        })
        
        return config
    
    def _generate_heatmap_config(self, data: Dict[str, Any], base_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate heatmap configuration."""
        config = base_config.copy()
        config.update({
            "tooltip": {"position": "top"},
            "xAxis": {
                "type": "category",
                "data": data.get("x_labels", []),
                "splitArea": {"show": True}
            },
            "yAxis": {
                "type": "category",
                "data": data.get("y_labels", []),
                "splitArea": {"show": True}
            },
            "visualMap": {
                "min": data.get("min_value", 0),
                "max": data.get("max_value", 100),
                "calculable": True,
                "orient": "horizontal",
                "left": "center",
                "bottom": "15%"
            },
            "series": [{
                "name": data.get("name", "Heatmap"),
                "type": "heatmap",
                "data": data.get("data", []),
                "label": {"show": True},
                "emphasis": {
                    "itemStyle": {
                        "shadowBlur": 10,
                        "shadowColor": "rgba(0, 0, 0, 0.5)"
                    }
                }
            }]
        })
        
        return config
    
    def _generate_gauge_config(self, data: Dict[str, Any], base_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate gauge configuration."""
        config = base_config.copy()
        config.update({
            "series": [{
                "name": data.get("name", "Gauge"),
                "type": "gauge",
                "detail": {"formatter": "{value}%" if data.get("unit") == "%" else "{value}"},
                "data": [{"value": data.get("value", 0), "name": data.get("name", "Value")}],
                "axisLine": {
                    "lineStyle": {
                        "width": 10
                    }
                },
                "splitLine": {
                    "length": 15,
                    "lineStyle": {
                        "width": 2,
                        "color": "#999"
                    }
                },
                "axisTick": {
                    "length": 8,
                    "lineStyle": {
                        "color": "#999"
                    }
                }
            }]
        })
        
        return config
    
    def _generate_donut_config(self, data: Dict[str, Any], base_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate donut chart configuration."""
        config = base_config.copy()
        config.update({
            "tooltip": {"trigger": "item"},
            "series": [{
                "name": data.get("name", "Data"),
                "type": "pie",
                "radius": ["40%", "70%"],
                "data": data.get("data", []),
                "emphasis": {
                    "itemStyle": {
                        "shadowBlur": 10,
                        "shadowOffsetX": 0,
                        "shadowColor": "rgba(0, 0, 0, 0.5)"
                    }
                }
            }]
        })
        
        return config
    
    def _generate_stacked_bar_config(self, data: Dict[str, Any], base_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate stacked bar chart configuration."""
        config = base_config.copy()
        config.update({
            "tooltip": {"trigger": "axis"},
            "legend": {"data": data.get("series_names", [])},
            "xAxis": {
                "type": "category",
                "data": data.get("x_data", [])
            },
            "yAxis": {"type": "value"},
            "series": []
        })
        
        for i, series_data in enumerate(data.get("series_data", [])):
            series_name = data.get("series_names", [f"Series {i+1}"])[i] if i < len(data.get("series_names", [])) else f"Series {i+1}"
            config["series"].append({
                "name": series_name,
                "type": "bar",
                "stack": "total",
                "data": series_data
            })
        
        return config


class ChartGenerator:
    """
    Chart generator for ML observability.
    """
    
    def __init__(self):
        self.visualization_engine = VisualizationEngine()
        self.chart_templates = {}
        
        logger.info("Initialized chart generator")
    
    def generate_chart(self, 
                      chart_type: ChartType,
                      data: Dict[str, Any],
                      title: str = "",
                      **kwargs) -> Dict[str, Any]:
        """Generate a chart configuration."""
        config = self.visualization_engine.generate_chart_config(
            chart_type=chart_type,
            data=data,
            title=title,
            **kwargs
        )
        
        return config
    
    def generate_time_series_chart(self, 
                                  time_series_data: List[Dict[str, Any]],
                                  title: str = "Time Series",
                                  **kwargs) -> Dict[str, Any]:
        """Generate a time series chart."""
        x_data = []
        series_data = []
        
        for point in time_series_data:
            x_data.append(point.get("timestamp", ""))
            series_data.append(point.get("value", 0))
        
        data = {
            "x_data": x_data,
            "series_data": [series_data],
            "series_names": ["Value"]
        }
        
        return self.generate_chart(ChartType.LINE, data, title, **kwargs)
    
    def generate_metric_comparison_chart(self,
                                       metrics_data: Dict[str, List[float]],
                                       categories: List[str],
                                       title: str = "Metrics Comparison",
                                       **kwargs) -> Dict[str, Any]:
        """Generate a metrics comparison chart."""
        series_data = []
        series_names = []
        
        for metric_name, values in metrics_data.items():
            series_names.append(metric_name)
            series_data.append(values)
        
        data = {
            "x_data": categories,
            "series_data": series_data,
            "series_names": series_names
        }
        
        return self.generate_chart(ChartType.BAR, data, title, **kwargs)
    
    def generate_distribution_chart(self,
                                  values: List[float],
                                  bins: int = 10,
                                  title: str = "Distribution",
                                  **kwargs) -> Dict[str, Any]:
        """Generate a distribution histogram."""
        # Simple binning
        min_val = min(values)
        max_val = max(values)
        bin_width = (max_val - min_val) / bins
        
        bin_edges = [min_val + i * bin_width for i in range(bins + 1)]
        bin_labels = [f"{bin_edges[i]:.1f}-{bin_edges[i+1]:.1f}" for i in range(bins)]
        frequencies = [0] * bins
        
        for value in values:
            bin_index = min(int((value - min_val) / bin_width), bins - 1)
            frequencies[bin_index] += 1
        
        data = {
            "bins": bin_labels,
            "frequencies": frequencies,
            "name": "Frequency"
        }
        
        return self.generate_chart(ChartType.HISTOGRAM, data, title, **kwargs)
    
    def generate_pie_chart(self,
                          data_points: List[Dict[str, Any]],
                          title: str = "Distribution",
                          **kwargs) -> Dict[str, Any]:
        """Generate a pie chart."""
        data = {
            "data": data_points,
            "name": "Distribution"
        }
        
        return self.generate_chart(ChartType.PIE, data, title, **kwargs)
    
    def generate_gauge_chart(self,
                            value: float,
                            min_val: float = 0,
                            max_val: float = 100,
                            unit: str = "%",
                            title: str = "Gauge",
                            **kwargs) -> Dict[str, Any]:
        """Generate a gauge chart."""
        data = {
            "value": value,
            "min": min_val,
            "max": max_val,
            "unit": unit,
            "name": title
        }
        
        return self.generate_chart(ChartType.GAUGE, data, title, **kwargs)
    
    def export_chart_config(self, config: Dict[str, Any], format: str = "json") -> str:
        """Export chart configuration."""
        if format == "json":
            return json.dumps(config, indent=2, default=str)
        else:
            return str(config)
    
    def get_available_chart_types(self) -> List[str]:
        """Get list of available chart types."""
        return [chart_type.value for chart_type in ChartType]
