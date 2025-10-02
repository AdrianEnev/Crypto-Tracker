"""
Base classes for intelligence tiers
"""

from abc import ABC, abstractmethod
from typing import Any
import logging


class BaseIntelligence(ABC):
    """Base class for all intelligence tiers"""
    
    def __init__(self, config, logger_name: str = None):
        self.config = config
        self.logger = logging.getLogger(logger_name or self.__class__.__name__)
        self.enabled = True
        self.failure_count = 0
        self.max_failures = 10
    
    @abstractmethod
    async def analyze(self, *args, **kwargs) -> Any:
        """Main analysis method - must be implemented by subclasses"""
        pass
    
    def is_enabled(self) -> bool:
        """Check if this intelligence tier is enabled"""
        return self.enabled and self.failure_count < self.max_failures
    
    def record_failure(self, error: Exception):
        """Record a failure"""
        self.failure_count += 1
        self.logger.error(f"Failure #{self.failure_count}: {error}")
        
        if self.failure_count >= self.max_failures:
            self.enabled = False
            self.logger.critical(f"Intelligence tier disabled after {self.failure_count} failures")
    
    def record_success(self):
        """Record a success - reset failure count"""
        if self.failure_count > 0:
            self.logger.info(f"Success after {self.failure_count} failures - resetting counter")
        self.failure_count = 0
    
    def reset(self):
        """Reset the intelligence tier"""
        self.enabled = True
        self.failure_count = 0
        self.logger.info("Intelligence tier reset")
