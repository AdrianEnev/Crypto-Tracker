"""
Configuration management for the crypto tracker.
Handles loading and validation of configuration settings.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

from src.models import AppConfig, CoinConfig


class ConfigManager:
    """Manages configuration loading and validation."""

    def __init__(self, config_path: str):
        self.config_path = config_path
        self._load_env_vars()

    def _load_env_vars(self):
        """Load environment variables from .env file."""
        # Look for .env in the project root directory (standard convention)
        env_path = Path(self.config_path).parent.parent / ".env"
        if not env_path.exists():
            # Fallback to config/.env for backward compatibility
            env_path = Path(self.config_path).parent / ".env"
        load_dotenv(dotenv_path=env_path)

    def load_config(self) -> AppConfig:
        """Load and parse the main configuration file."""
        return self._load_config(self.config_path)

    def _load_config(self, config_path: str) -> AppConfig:
        """Load configuration from YAML file."""
        try:
            with open(config_path, "r") as f:
                config_data = yaml.safe_load(f) or {}

            # Extract tracked coins
            tracked_coins = {}
            for coin_id, coin_data in config_data.get("tracked_coins", {}).items():
                tracked_coins[coin_id] = CoinConfig(
                    symbol=coin_data["symbol"],
                    name=coin_data["name"],
                    threshold=coin_data["threshold"],
                    check_interval=coin_data["check_interval"],
                    disabled=coin_data.get("disabled", False),
                )

            # Extract API configuration
            api_config = config_data.get("api", {})

            return AppConfig(
                tracked_coins=tracked_coins,
                api_base_url=api_config.get("base_url", "https://pro-api.coinmarketcap.com"),
                api_timeout=api_config.get("timeout", 10),
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load configuration: {e}")

    def load_full_config(self) -> Dict[str, Any]:
        """Load the complete configuration as a dictionary."""
        try:
            with open(self.config_path, "r") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            raise RuntimeError(f"Failed to load full configuration: {e}")

    def get_providers_config(self) -> Dict[str, Any]:
        """Get providers configuration section."""
        try:
            config = self.load_full_config()
            return config.get("providers", {})
        except Exception:
            return {}

    def get_data_config(self) -> Dict[str, Any]:
        """Get data configuration section."""
        try:
            config = self.load_full_config()
            return config.get("data", {})
        except Exception:
            return {}

    def get_indicators_config(self) -> Dict[str, Any]:
        """Get indicators configuration section."""
        try:
            config = self.load_full_config()
            return config.get("indicators", {})
        except Exception:
            return {}

    def get_strategy_config(self) -> Dict[str, Any]:
        """Get strategy configuration section."""
        try:
            config = self.load_full_config()
            return config.get("strategy", {})
        except Exception:
            return {}

    def get_execution_config(self) -> Dict[str, Any]:
        """Get execution configuration section."""
        try:
            config = self.load_full_config()
            return config.get("execution", {})
        except Exception:
            return {}

    def get_risk_config(self) -> Dict[str, Any]:
        """Get risk configuration section."""
        try:
            config = self.load_full_config()
            return config.get("risk", {})
        except Exception:
            return {}

    def get_testing_config(self) -> Dict[str, Any]:
        """Get testing configuration section."""
        try:
            config = self.load_full_config()
            return config.get("testing", {})
        except Exception:
            return {}
