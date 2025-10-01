"""
LLM Configuration Manager

Manages LLM configuration and integration with the existing configuration system.
"""

import logging
from typing import Any, Dict, Optional

from .client import LLMConfig, LLMProvider


class LLMConfigManager:
    """Manages LLM configuration and initialization"""
    
    def __init__(self, config_manager, secrets_manager=None):
        self.config_manager = config_manager
        self.secrets_manager = secrets_manager
        self.logger = logging.getLogger(__name__)
        
        # Load LLM configuration
        self.llm_config = self._load_llm_config()
    
    def _load_llm_config(self) -> Dict[str, Any]:
        """Load LLM configuration from main config"""
        try:
            # Load raw YAML config directly
            import yaml
            with open(self.config_manager.config_path, "r") as f:
                config_data = yaml.safe_load(f) or {}
            return config_data.get("llm", {})
        except Exception as e:
            self.logger.error(f"Error loading LLM config: {e}")
            return {}
    
    def is_enabled(self) -> bool:
        """Check if LLM integration is enabled"""
        return self.llm_config.get("enabled", False)
    
    def get_provider(self) -> LLMProvider:
        """Get configured LLM provider"""
        provider_str = self.llm_config.get("provider", "openai")
        try:
            return LLMProvider(provider_str)
        except ValueError:
            self.logger.warning(f"Unknown provider '{provider_str}', defaulting to OpenAI")
            return LLMProvider.OPENAI
    
    def get_model(self) -> str:
        """Get configured model"""
        return self.llm_config.get("model", "gpt-4o-mini")
    
    def get_api_key(self) -> Optional[str]:
        """Get API key from environment variables or secrets manager"""
        import os
        
        # Try environment variable first (most secure)
        provider = self.get_provider()
        env_key_name = f"{provider.value.upper()}_API_KEY"
        api_key = os.getenv(env_key_name)
        if api_key:
            self.logger.debug(f"Using API key from environment variable {env_key_name}")
            return api_key
        
        # Try secrets manager second
        if self.secrets_manager:
            key_name = f"{provider.value}_api_key"
            api_key = self.secrets_manager.get_secret(key_name)
            if api_key:
                self.logger.debug(f"Using API key from secrets manager")
                return api_key
        
        # No fallback to config file - API key must be in environment or secrets
        self.logger.error(f"No API key found. Please set {env_key_name} environment variable or use secrets manager")
        return None
    
    def get_base_url(self) -> Optional[str]:
        """Get base URL for API"""
        return self.llm_config.get("base_url")
    
    def create_llm_config(self) -> LLMConfig:
        """Create LLMConfig object from configuration"""
        return LLMConfig(
            provider=self.get_provider(),
            model=self.get_model(),
            api_key=self.get_api_key(),
            base_url=self.get_base_url(),
            max_tokens=self.llm_config.get("max_tokens", 4000),
            temperature=self.llm_config.get("temperature", 0.1),
            timeout=self.llm_config.get("timeout", 30),
            max_retries=self.llm_config.get("max_retries", 3),
            rate_limit_per_minute=self.llm_config.get("rate_limit_per_minute", 60),
            enable_caching=self.llm_config.get("enable_caching", True),
            cache_ttl_seconds=self.llm_config.get("cache_ttl_seconds", 300)
        )
    
    def get_analysis_config(self) -> Dict[str, Any]:
        """Get analysis configuration"""
        return self.llm_config.get("analysis", {})
    
    def get_crisis_thresholds(self) -> Dict[str, float]:
        """Get crisis detection thresholds"""
        analysis_config = self.get_analysis_config()
        return analysis_config.get("crisis_thresholds", {
            "government_crisis": 0.8,
            "economic_crisis": 0.7,
            "regulatory_crisis": 0.8,
            "market_crisis": 0.9
        })
    
    def get_analysis_interval(self) -> int:
        """Get analysis interval in minutes"""
        analysis_config = self.get_analysis_config()
        return analysis_config.get("analysis_interval_minutes", 15)
    
    def get_crisis_check_interval(self) -> int:
        """Get crisis check interval in minutes"""
        analysis_config = self.get_analysis_config()
        return analysis_config.get("crisis_check_interval_minutes", 5)
    
    def should_integrate_with_decisions(self) -> bool:
        """Check if LLM should integrate with trading decisions"""
        analysis_config = self.get_analysis_config()
        return analysis_config.get("integrate_with_decisions", True)
    
    def should_fallback_to_technical(self) -> bool:
        """Check if should fallback to technical analysis"""
        analysis_config = self.get_analysis_config()
        return analysis_config.get("fallback_to_technical", True)
    
    def get_default_analysis_mode(self) -> str:
        """Get default analysis mode"""
        analysis_config = self.get_analysis_config()
        return analysis_config.get("default_mode", "normal")
    
    def validate_config(self) -> bool:
        """Validate LLM configuration"""
        if not self.is_enabled():
            return True  # Not enabled, so config is valid
        
        # Check required fields
        if not self.get_api_key():
            self.logger.error("LLM enabled but no API key configured")
            return False
        
        # Validate provider
        try:
            self.get_provider()
        except Exception as e:
            self.logger.error(f"Invalid LLM provider: {e}")
            return False
        
        self.logger.info("LLM configuration validated successfully")
        return True
