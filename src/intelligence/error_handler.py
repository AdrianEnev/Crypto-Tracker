"""
Comprehensive error handling and fallback system for intelligence tiers
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, Set, Optional, Callable
from enum import Enum


class ServiceType(Enum):
    """Types of services that can fail"""
    LLM = "llm"
    SOCIAL_TWITTER = "social_twitter"
    SOCIAL_REDDIT = "social_reddit"
    ORDERBOOK = "orderbook"
    ONCHAIN = "onchain"
    DERIVATIVES = "derivatives"
    ML_MODEL = "ml_model"
    ORCHESTRATOR = "orchestrator"


class IntelligenceFallbackHandler:
    """
    Handles failures in intelligence tiers with graceful degradation.
    
    Features:
    - Track failures per service
    - Auto-disable services after threshold
    - Auto-re-enable after cooldown period
    - Alert callbacks for critical failures
    """
    
    def __init__(self, config: dict = None):
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.config = config or {}
        self.disable_thresholds = self.config.get('max_failures_before_disable', {
            'llm': 5,
            'social_twitter': 10,
            'social_reddit': 10,
            'orderbook': 20,
            'onchain': 15,
            'derivatives': 15,
            'ml_model': 10,
            'orchestrator': 3
        })
        
        self.reenable_after_hours = self.config.get('auto_reenable_after_hours', 1)
        
        # State tracking
        self.failure_counts: Dict[str, int] = defaultdict(int)
        self.disabled_services: Set[str] = set()
        self.disable_timestamps: Dict[str, datetime] = {}
        self.last_error_messages: Dict[str, str] = {}
        
        # Callbacks
        self.alert_callbacks: list[Callable] = []
    
    def handle_failure(self, service: str, error: Exception, context: str = ""):
        """
        Handle a service failure
        
        Args:
            service: Service identifier (e.g., 'llm', 'social_twitter')
            error: The exception that occurred
            context: Additional context about the failure
        """
        self.failure_counts[service] += 1
        self.last_error_messages[service] = str(error)
        
        self.logger.warning(
            f"Service '{service}' failure #{self.failure_counts[service]}: {error}"
            + (f" | Context: {context}" if context else "")
        )
        
        # Check if we should disable the service
        threshold = self.disable_thresholds.get(service, 10)
        if self.failure_counts[service] >= threshold:
            self._disable_service(service, error)
    
    def handle_success(self, service: str):
        """
        Record a successful operation - resets failure count
        
        Args:
            service: Service identifier
        """
        if self.failure_counts[service] > 0:
            self.logger.info(
                f"Service '{service}' succeeded after {self.failure_counts[service]} failures"
            )
            self.failure_counts[service] = 0
    
    def is_enabled(self, service: str) -> bool:
        """
        Check if a service is enabled
        
        Args:
            service: Service identifier
            
        Returns:
            True if service is enabled, False if disabled
        """
        # Check if service should be re-enabled
        if service in self.disabled_services:
            self._check_reenable(service)
        
        return service not in self.disabled_services
    
    def _disable_service(self, service: str, error: Exception):
        """Disable a service due to repeated failures"""
        if service in self.disabled_services:
            return  # Already disabled
        
        self.disabled_services.add(service)
        self.disable_timestamps[service] = datetime.now(timezone.utc)
        
        message = (
            f"⚠️ CRITICAL: Service '{service}' has been disabled after "
            f"{self.failure_counts[service]} consecutive failures. "
            f"Last error: {str(error)[:100]}"
        )
        
        self.logger.critical(message)
        
        # Trigger alert callbacks
        self._trigger_alerts(service, message, level="CRITICAL")
    
    def _check_reenable(self, service: str):
        """Check if a disabled service should be re-enabled"""
        if service not in self.disabled_services:
            return
        
        disable_time = self.disable_timestamps.get(service)
        if not disable_time:
            return
        
        time_since_disable = datetime.now(timezone.utc) - disable_time
        hours_since_disable = time_since_disable.total_seconds() / 3600
        
        if hours_since_disable >= self.reenable_after_hours:
            self._reenable_service(service)
    
    def _reenable_service(self, service: str):
        """Re-enable a previously disabled service"""
        self.disabled_services.discard(service)
        self.failure_counts[service] = 0
        
        if service in self.disable_timestamps:
            disable_time = self.disable_timestamps[service]
            hours_disabled = (datetime.now(timezone.utc) - disable_time).total_seconds() / 3600
            
            message = (
                f"✅ Service '{service}' has been re-enabled after "
                f"{hours_disabled:.1f} hours. Monitoring for stability."
            )
            
            self.logger.info(message)
            self._trigger_alerts(service, message, level="INFO")
    
    def manually_disable(self, service: str, reason: str = "Manual disable"):
        """Manually disable a service"""
        self.disabled_services.add(service)
        self.disable_timestamps[service] = datetime.now(timezone.utc)
        self.logger.warning(f"Service '{service}' manually disabled: {reason}")
    
    def manually_enable(self, service: str):
        """Manually enable a service"""
        if service in self.disabled_services:
            self._reenable_service(service)
        else:
            self.logger.info(f"Service '{service}' is already enabled")
    
    def get_status(self) -> Dict[str, any]:
        """Get current status of all services"""
        return {
            'enabled_services': [s for s in ServiceType if s.value not in self.disabled_services],
            'disabled_services': list(self.disabled_services),
            'failure_counts': dict(self.failure_counts),
            'last_errors': dict(self.last_error_messages)
        }
    
    def register_alert_callback(self, callback: Callable):
        """
        Register a callback to be called when alerts are triggered
        
        Args:
            callback: Function that takes (service, message, level) as arguments
        """
        self.alert_callbacks.append(callback)
    
    def _trigger_alerts(self, service: str, message: str, level: str):
        """Trigger all registered alert callbacks"""
        for callback in self.alert_callbacks:
            try:
                callback(service, message, level)
            except Exception as e:
                self.logger.error(f"Alert callback failed: {e}")
    
    def reset_all(self):
        """Reset all failure tracking (use with caution)"""
        self.failure_counts.clear()
        self.disabled_services.clear()
        self.disable_timestamps.clear()
        self.last_error_messages.clear()
        self.logger.info("All services reset")
