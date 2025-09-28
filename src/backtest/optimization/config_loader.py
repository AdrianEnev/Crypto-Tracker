"""
Configuration loading for backtest optimization.
"""

from pathlib import Path
from typing import Dict, Any
import yaml


class ConfigLoader:
    """Loads and manages configuration for optimization."""

    def __init__(self, config_path: str = None):
        if config_path is None:
            project_root = Path(__file__).resolve().parents[4]
            config_path = project_root / "config" / "config.yaml"

        self.config_path = Path(config_path)
        self._config = None

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if self._config is None:
            with open(self.config_path, "r") as f:
                self._config = yaml.safe_load(f) or {}
        return self._config

    def get_data_config(self) -> Dict[str, Any]:
        """Get data configuration section."""
        return self.load_config().get("data", {})

    def get_indicators_config(self) -> Dict[str, Any]:
        """Get indicators configuration section."""
        return self.load_config().get("indicators", {})

    def get_strategy_config(self) -> Dict[str, Any]:
        """Get strategy configuration section."""
        return self.load_config().get("strategy", {})

    def get_risk_config(self) -> Dict[str, Any]:
        """Get risk configuration section."""
        return self.load_config().get("risk", {})

    def get_decision_config(self) -> Dict[str, Any]:
        """Get decision configuration section."""
        return self.load_config().get("decision", {})

    def get_execution_config(self) -> Dict[str, Any]:
        """Get execution configuration section."""
        return self.load_config().get("execution", {})

    def get_optimize_config(self) -> Dict[str, Any]:
        """Get optimization configuration section."""
        return self.load_config().get("optimize", {})

    def get_tracked_coins_config(self) -> Dict[str, Any]:
        """Get tracked coins configuration section."""
        return self.load_config().get("tracked_coins", {})

    def get_providers_config(self) -> Dict[str, Any]:
        """Get providers configuration section."""
        return self.load_config().get("providers", {})
