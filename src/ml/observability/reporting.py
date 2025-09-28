"""
Reporting system for ML observability.
Provides automated report generation and scheduling.
"""

import json
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ReportFormat(Enum):
    """Report output formats."""
    JSON = "json"
    HTML = "html"
    PDF = "pdf"
    CSV = "csv"
    MARKDOWN = "markdown"


@dataclass
class ReportTemplate:
    """Container for report template configuration."""
    template_id: str
    name: str
    description: str
    sections: List[Dict[str, Any]] = field(default_factory=list)
    format: ReportFormat = ReportFormat.HTML
    parameters: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'template_id': self.template_id,
            'name': self.name,
            'description': self.description,
            'sections': self.sections,
            'format': self.format.value,
            'parameters': self.parameters,
            'created_at': self.created_at.isoformat()
        }


@dataclass
class ReportScheduler:
    """Container for report scheduling configuration."""
    schedule_id: str
    template_id: str
    name: str
    schedule_type: str  # "daily", "weekly", "monthly", "custom"
    schedule_config: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    recipients: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'schedule_id': self.schedule_id,
            'template_id': self.template_id,
            'name': self.name,
            'schedule_type': self.schedule_type,
            'schedule_config': self.schedule_config,
            'enabled': self.enabled,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'next_run': self.next_run.isoformat() if self.next_run else None,
            'recipients': self.recipients,
            'created_at': self.created_at.isoformat()
        }


class ReportGenerator:
    """
    Report generator for ML observability.
    """
    
    def __init__(self, output_directory: str = "reports"):
        self.output_directory = output_directory
        self.templates: Dict[str, ReportTemplate] = {}
        self.schedulers: Dict[str, ReportScheduler] = {}
        
        # Ensure output directory exists
        os.makedirs(output_directory, exist_ok=True)
        
        logger.info(f"Initialized report generator: output_directory={output_directory}")
    
    def add_template(self, template: ReportTemplate) -> None:
        """Add a report template."""
        self.templates[template.template_id] = template
        logger.info(f"Added report template: {template.name}")
    
    def remove_template(self, template_id: str) -> bool:
        """Remove a report template."""
        if template_id in self.templates:
            del self.templates[template_id]
            logger.info(f"Removed report template: {template_id}")
            return True
        return False
    
    def add_scheduler(self, scheduler: ReportScheduler) -> None:
        """Add a report scheduler."""
        self.schedulers[scheduler.schedule_id] = scheduler
        logger.info(f"Added report scheduler: {scheduler.name}")
    
    def generate_report(self, 
                       template_id: str,
                       output_filename: Optional[str] = None,
                       parameters: Optional[Dict[str, Any]] = None) -> str:
        """Generate a report from a template."""
        if template_id not in self.templates:
            raise ValueError(f"Template not found: {template_id}")
        
        template = self.templates[template_id]
        parameters = parameters or {}
        
        # Merge template parameters with provided parameters
        merged_params = {**template.parameters, **parameters}
        
        # Generate report content
        content = self._generate_report_content(template, merged_params)
        
        # Determine output filename
        if output_filename is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            output_filename = f"{template.name}_{timestamp}.{template.format.value}"
        
        # Write report to file
        output_path = os.path.join(self.output_directory, output_filename)
        self._write_report(content, output_path, template.format)
        
        logger.info(f"Generated report: {output_path}")
        return output_path
    
    def _generate_report_content(self, template: ReportTemplate, parameters: Dict[str, Any]) -> str:
        """Generate report content based on template."""
        if template.format == ReportFormat.JSON:
            return self._generate_json_report(template, parameters)
        elif template.format == ReportFormat.HTML:
            return self._generate_html_report(template, parameters)
        elif template.format == ReportFormat.MARKDOWN:
            return self._generate_markdown_report(template, parameters)
        elif template.format == ReportFormat.CSV:
            return self._generate_csv_report(template, parameters)
        else:
            return self._generate_text_report(template, parameters)
    
    def _generate_json_report(self, template: ReportTemplate, parameters: Dict[str, Any]) -> str:
        """Generate JSON format report."""
        report_data = {
            'template': template.to_dict(),
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'parameters': parameters,
            'sections': []
        }
        
        for section in template.sections:
            section_data = self._generate_section_data(section, parameters)
            report_data['sections'].append(section_data)
        
        return json.dumps(report_data, indent=2, default=str)
    
    def _generate_html_report(self, template: ReportTemplate, parameters: Dict[str, Any]) -> str:
        """Generate HTML format report."""
        html_parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            f"<title>{template.name}</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 40px; }",
            "h1, h2, h3 { color: #333; }",
            "table { border-collapse: collapse; width: 100%; }",
            "th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
            "th { background-color: #f2f2f2; }",
            ".metric { background-color: #f9f9f9; padding: 10px; margin: 10px 0; }",
            "</style>",
            "</head>",
            "<body>",
            f"<h1>{template.name}</h1>",
            f"<p>{template.description}</p>",
            f"<p><strong>Generated:</strong> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>",
            "<hr>"
        ]
        
        for section in template.sections:
            section_html = self._generate_section_html(section, parameters)
            html_parts.append(section_html)
        
        html_parts.extend([
            "</body>",
            "</html>"
        ])
        
        return "\n".join(html_parts)
    
    def _generate_markdown_report(self, template: ReportTemplate, parameters: Dict[str, Any]) -> str:
        """Generate Markdown format report."""
        md_parts = [
            f"# {template.name}",
            f"{template.description}",
            "",
            f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
            "---",
            ""
        ]
        
        for section in template.sections:
            section_md = self._generate_section_markdown(section, parameters)
            md_parts.append(section_md)
        
        return "\n".join(md_parts)
    
    def _generate_csv_report(self, template: ReportTemplate, parameters: Dict[str, Any]) -> str:
        """Generate CSV format report."""
        csv_parts = []
        
        # Header
        csv_parts.append("Section,Field,Value")
        
        for section in template.sections:
            section_name = section.get('name', 'Unknown')
            section_data = self._generate_section_data(section, parameters)
            
            if isinstance(section_data, dict):
                for key, value in section_data.items():
                    csv_parts.append(f"{section_name},{key},{value}")
            else:
                csv_parts.append(f"{section_name},data,{section_data}")
        
        return "\n".join(csv_parts)
    
    def _generate_text_report(self, template: ReportTemplate, parameters: Dict[str, Any]) -> str:
        """Generate plain text format report."""
        text_parts = [
            f"{template.name}",
            "=" * len(template.name),
            f"{template.description}",
            "",
            f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
            "-" * 50,
            ""
        ]
        
        for section in template.sections:
            section_text = self._generate_section_text(section, parameters)
            text_parts.append(section_text)
        
        return "\n".join(text_parts)
    
    def _generate_section_data(self, section: Dict[str, Any], parameters: Dict[str, Any]) -> Any:
        """Generate data for a report section."""
        section_type = section.get('type', 'text')
        
        if section_type == 'metrics':
            return self._generate_metrics_data(section, parameters)
        elif section_type == 'chart':
            return self._generate_chart_data(section, parameters)
        elif section_type == 'table':
            return self._generate_table_data(section, parameters)
        elif section_type == 'summary':
            return self._generate_summary_data(section, parameters)
        else:
            return self._generate_text_data(section, parameters)
    
    def _generate_metrics_data(self, section: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate metrics data for a section."""
        return {
            'cpu_usage': 65.5,
            'memory_usage': 78.2,
            'disk_usage': 45.8,
            'network_io': 125.7
        }
    
    def _generate_chart_data(self, section: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate chart data for a section."""
        return {
            'chart_type': 'line',
            'title': 'Performance Over Time',
            'data': [
                {'timestamp': '2024-01-01T00:00:00Z', 'value': 85.5},
                {'timestamp': '2024-01-01T01:00:00Z', 'value': 87.2},
                {'timestamp': '2024-01-01T02:00:00Z', 'value': 83.8}
            ]
        }
    
    def _generate_table_data(self, section: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate table data for a section."""
        return {
            'headers': ['Model', 'Accuracy', 'Status'],
            'rows': [
                ['Model A', '0.92', 'Active'],
                ['Model B', '0.89', 'Active'],
                ['Model C', '0.85', 'Training']
            ]
        }
    
    def _generate_summary_data(self, section: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary data for a section."""
        return {
            'total_models': 5,
            'active_models': 3,
            'total_requests': 125000,
            'average_response_time': 89.5,
            'error_rate': 0.02
        }
    
    def _generate_text_data(self, section: Dict[str, Any], parameters: Dict[str, Any]) -> str:
        """Generate text data for a section."""
        return section.get('content', 'No content available')
    
    def _generate_section_html(self, section: Dict[str, Any], parameters: Dict[str, Any]) -> str:
        """Generate HTML for a section."""
        section_name = section.get('name', 'Section')
        section_data = self._generate_section_data(section, parameters)
        
        html_parts = [f"<h2>{section_name}</h2>"]
        
        if isinstance(section_data, dict):
            if 'headers' in section_data and 'rows' in section_data:
                # Table
                html_parts.extend([
                    "<table>",
                    "<thead><tr>"
                ])
                for header in section_data['headers']:
                    html_parts.append(f"<th>{header}</th>")
                html_parts.extend([
                    "</tr></thead>",
                    "<tbody>"
                ])
                for row in section_data['rows']:
                    html_parts.append("<tr>")
                    for cell in row:
                        html_parts.append(f"<td>{cell}</td>")
                    html_parts.append("</tr>")
                html_parts.extend(["</tbody>", "</table>"])
            else:
                # Key-value pairs
                for key, value in section_data.items():
                    html_parts.append(f"<div class='metric'><strong>{key}:</strong> {value}</div>")
        else:
            html_parts.append(f"<p>{section_data}</p>")
        
        return "\n".join(html_parts)
    
    def _generate_section_markdown(self, section: Dict[str, Any], parameters: Dict[str, Any]) -> str:
        """Generate Markdown for a section."""
        section_name = section.get('name', 'Section')
        section_data = self._generate_section_data(section, parameters)
        
        md_parts = [f"## {section_name}", ""]
        
        if isinstance(section_data, dict):
            if 'headers' in section_data and 'rows' in section_data:
                # Table
                md_parts.append("| " + " | ".join(section_data['headers']) + " |")
                md_parts.append("| " + " | ".join(["---"] * len(section_data['headers'])) + " |")
                for row in section_data['rows']:
                    md_parts.append("| " + " | ".join(str(cell) for cell in row) + " |")
            else:
                # Key-value pairs
                for key, value in section_data.items():
                    md_parts.append(f"**{key}:** {value}")
        else:
            md_parts.append(str(section_data))
        
        md_parts.append("")
        return "\n".join(md_parts)
    
    def _generate_section_text(self, section: Dict[str, Any], parameters: Dict[str, Any]) -> str:
        """Generate plain text for a section."""
        section_name = section.get('name', 'Section')
        section_data = self._generate_section_data(section, parameters)
        
        text_parts = [f"{section_name}", "-" * len(section_name), ""]
        
        if isinstance(section_data, dict):
            for key, value in section_data.items():
                text_parts.append(f"{key}: {value}")
        else:
            text_parts.append(str(section_data))
        
        text_parts.append("")
        return "\n".join(text_parts)
    
    def _write_report(self, content: str, output_path: str, format: ReportFormat) -> None:
        """Write report content to file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def list_reports(self) -> List[str]:
        """List generated reports."""
        if not os.path.exists(self.output_directory):
            return []
        
        return [
            f for f in os.listdir(self.output_directory)
            if os.path.isfile(os.path.join(self.output_directory, f))
        ]
    
    def get_report_info(self) -> Dict[str, Any]:
        """Get report generator information."""
        return {
            'output_directory': self.output_directory,
            'total_templates': len(self.templates),
            'total_schedulers': len(self.schedulers),
            'generated_reports': len(self.list_reports())
        }
