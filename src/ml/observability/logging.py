"""
Structured logging system for ML observability.
Provides structured logging with context and audit capabilities.
"""

import json
import sys
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
import traceback
from pathlib import Path

logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """Log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogContext:
    """Container for log context information."""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    deployment_id: Optional[str] = None
    environment: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'user_id': self.user_id,
            'session_id': self.session_id,
            'request_id': self.request_id,
            'model_name': self.model_name,
            'model_version': self.model_version,
            'deployment_id': self.deployment_id,
            'environment': self.environment,
            'tags': self.tags,
            'metadata': self.metadata
        }


class StructuredLogger:
    """
    Structured logger for ML observability.
    """
    
    def __init__(self, 
                 name: str,
                 log_file: Optional[str] = None,
                 level: LogLevel = LogLevel.INFO,
                 format_type: str = "json"):
        self.name = name
        self.log_file = log_file
        self.level = level
        self.format_type = format_type
        self.context: Optional[LogContext] = None
        self._lock = threading.Lock()
        
        # Setup logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.value))
        
        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Add console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.value))
        
        if format_type == "json":
            formatter = logging.Formatter('%(message)s')
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # Add file handler if specified
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(getattr(logging, level.value))
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        
        # Prevent propagation to root logger
        self.logger.propagate = False
    
    def set_context(self, context: LogContext) -> None:
        """Set logging context."""
        self.context = context
    
    def update_context(self, **kwargs) -> None:
        """Update logging context with new values."""
        if self.context is None:
            self.context = LogContext()
        
        for key, value in kwargs.items():
            if hasattr(self.context, key):
                setattr(self.context, key, value)
            else:
                self.context.metadata[key] = value
    
    def _create_log_entry(self, 
                         level: LogLevel, 
                         message: str, 
                         extra: Optional[Dict[str, Any]] = None,
                         exception: Optional[Exception] = None) -> Dict[str, Any]:
        """Create a structured log entry."""
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'logger': self.name,
            'level': level.value,
            'message': message,
            'thread_id': threading.get_ident()
        }
        
        # Add context if available
        if self.context:
            log_entry['context'] = self.context.to_dict()
        
        # Add extra fields
        if extra:
            log_entry['extra'] = extra
        
        # Add exception information
        if exception:
            log_entry['exception'] = {
                'type': type(exception).__name__,
                'message': str(exception),
                'traceback': traceback.format_exc()
            }
        
        return log_entry
    
    def _log(self, level: LogLevel, message: str, extra: Optional[Dict[str, Any]] = None, exception: Optional[Exception] = None) -> None:
        """Internal logging method."""
        with self._lock:
            log_entry = self._create_log_entry(level, message, extra, exception)
            
            if self.format_type == "json":
                log_message = json.dumps(log_entry, default=str)
            else:
                # Simple format for non-JSON logging
                context_str = ""
                if self.context:
                    context_parts = []
                    if self.context.user_id:
                        context_parts.append(f"user={self.context.user_id}")
                    if self.context.request_id:
                        context_parts.append(f"req={self.context.request_id}")
                    if self.context.model_name:
                        context_parts.append(f"model={self.context.model_name}")
                    if context_parts:
                        context_str = f" [{', '.join(context_parts)}]"
                
                log_message = f"{log_entry['timestamp']} - {level.value} - {message}{context_str}"
                if extra:
                    log_message += f" - {json.dumps(extra, default=str)}"
                if exception:
                    log_message += f" - Exception: {str(exception)}"
            
            # Log using the appropriate level
            if level == LogLevel.DEBUG:
                self.logger.debug(log_message)
            elif level == LogLevel.INFO:
                self.logger.info(log_message)
            elif level == LogLevel.WARNING:
                self.logger.warning(log_message)
            elif level == LogLevel.ERROR:
                self.logger.error(log_message)
            elif level == LogLevel.CRITICAL:
                self.logger.critical(log_message)
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self._log(LogLevel.DEBUG, message, kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self._log(LogLevel.INFO, message, kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self._log(LogLevel.WARNING, message, kwargs)
    
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs) -> None:
        """Log error message."""
        self._log(LogLevel.ERROR, message, kwargs, exception)
    
    def critical(self, message: str, exception: Optional[Exception] = None, **kwargs) -> None:
        """Log critical message."""
        self._log(LogLevel.CRITICAL, message, kwargs, exception)
    
    def log_metric(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Log a metric."""
        extra = {
            'metric_name': metric_name,
            'metric_value': value,
            'metric_type': 'gauge'
        }
        
        if tags:
            extra['metric_tags'] = tags
        
        self.info(f"Metric: {metric_name} = {value}", **extra)
    
    def log_event(self, event_name: str, event_data: Optional[Dict[str, Any]] = None) -> None:
        """Log an event."""
        extra = {
            'event_name': event_name,
            'event_type': 'business_event'
        }
        
        if event_data:
            extra['event_data'] = event_data
        
        self.info(f"Event: {event_name}", **extra)
    
    def log_model_inference(self, 
                          model_name: str,
                          model_version: str,
                          input_data: Dict[str, Any],
                          output_data: Dict[str, Any],
                          latency_ms: float,
                          success: bool) -> None:
        """Log model inference."""
        extra = {
            'model_name': model_name,
            'model_version': model_version,
            'input_size': len(str(input_data)),
            'output_size': len(str(output_data)),
            'latency_ms': latency_ms,
            'success': success,
            'event_type': 'model_inference'
        }
        
        level = LogLevel.INFO if success else LogLevel.ERROR
        message = f"Model inference: {model_name}:{model_version} - {latency_ms:.2f}ms"
        
        self._log(level, message, extra)
    
    def log_model_training(self,
                         model_name: str,
                         training_data_size: int,
                         training_time_seconds: float,
                         metrics: Dict[str, float],
                         success: bool) -> None:
        """Log model training."""
        extra = {
            'model_name': model_name,
            'training_data_size': training_data_size,
            'training_time_seconds': training_time_seconds,
            'training_metrics': metrics,
            'success': success,
            'event_type': 'model_training'
        }
        
        level = LogLevel.INFO if success else LogLevel.ERROR
        message = f"Model training: {model_name} - {training_time_seconds:.2f}s"
        
        self._log(level, message, extra)
    
    def log_deployment(self,
                     deployment_id: str,
                     model_name: str,
                     model_version: str,
                     environment: str,
                     action: str,
                     success: bool) -> None:
        """Log deployment action."""
        extra = {
            'deployment_id': deployment_id,
            'model_name': model_name,
            'model_version': model_version,
            'environment': environment,
            'deployment_action': action,
            'success': success,
            'event_type': 'deployment'
        }
        
        level = LogLevel.INFO if success else LogLevel.ERROR
        message = f"Deployment {action}: {model_name}:{model_version} to {environment}"
        
        self._log(level, message, extra)
    
    def log_performance(self,
                      component: str,
                      operation: str,
                      duration_ms: float,
                      success: bool,
                      metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log performance metrics."""
        extra = {
            'component': component,
            'operation': operation,
            'duration_ms': duration_ms,
            'success': success,
            'event_type': 'performance'
        }
        
        if metadata:
            extra['performance_metadata'] = metadata
        
        level = LogLevel.INFO if success else LogLevel.WARNING
        message = f"Performance: {component}.{operation} - {duration_ms:.2f}ms"
        
        self._log(level, message, extra)


class AuditLogger:
    """
    Specialized logger for audit trails.
    """
    
    def __init__(self, audit_file: str = "audit.log"):
        self.audit_file = audit_file
        self.logger = StructuredLogger(
            name="audit",
            log_file=audit_file,
            level=LogLevel.INFO,
            format_type="json"
        )
    
    def log_user_action(self,
                       user_id: str,
                       action: str,
                       resource: str,
                       resource_id: Optional[str] = None,
                       success: bool = True,
                       metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log user action for audit."""
        context = LogContext(
            user_id=user_id,
            tags=["audit", "user_action"]
        )
        
        self.logger.set_context(context)
        
        extra = {
            'action': action,
            'resource': resource,
            'resource_id': resource_id,
            'success': success,
            'event_type': 'user_action'
        }
        
        if metadata:
            extra['action_metadata'] = metadata
        
        level = LogLevel.INFO if success else LogLevel.WARNING
        message = f"User action: {user_id} performed {action} on {resource}"
        
        self.logger._log(level, message, extra)
    
    def log_system_event(self,
                        event: str,
                        component: str,
                        severity: LogLevel = LogLevel.INFO,
                        metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log system event for audit."""
        context = LogContext(
            tags=["audit", "system_event"]
        )
        
        self.logger.set_context(context)
        
        extra = {
            'system_event': event,
            'component': component,
            'event_type': 'system_event'
        }
        
        if metadata:
            extra['system_metadata'] = metadata
        
        message = f"System event: {event} in {component}"
        
        self.logger._log(severity, message, extra)
    
    def log_security_event(self,
                          event: str,
                          user_id: Optional[str] = None,
                          ip_address: Optional[str] = None,
                          severity: LogLevel = LogLevel.WARNING,
                          metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log security event for audit."""
        context = LogContext(
            user_id=user_id,
            tags=["audit", "security_event"]
        )
        
        self.logger.set_context(context)
        
        extra = {
            'security_event': event,
            'ip_address': ip_address,
            'event_type': 'security_event'
        }
        
        if metadata:
            extra['security_metadata'] = metadata
        
        message = f"Security event: {event}"
        if user_id:
            message += f" for user {user_id}"
        if ip_address:
            message += f" from {ip_address}"
        
        self.logger._log(severity, message, extra)
    
    def log_data_access(self,
                       user_id: str,
                       data_type: str,
                       operation: str,
                       success: bool = True,
                       metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log data access for audit."""
        context = LogContext(
            user_id=user_id,
            tags=["audit", "data_access"]
        )
        
        self.logger.set_context(context)
        
        extra = {
            'data_type': data_type,
            'data_operation': operation,
            'success': success,
            'event_type': 'data_access'
        }
        
        if metadata:
            extra['data_metadata'] = metadata
        
        level = LogLevel.INFO if success else LogLevel.WARNING
        message = f"Data access: {user_id} performed {operation} on {data_type}"
        
        self.logger._log(level, message, extra)
