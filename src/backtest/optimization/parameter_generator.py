"""
Parameter generation for backtest optimization.
"""

from typing import Dict, List, Any, Iterator
from itertools import product


class ParameterGenerator:
    """Generates parameter combinations for optimization."""

    def __init__(self, config_loader):
        self.config_loader = config_loader

    def generate_parameter_combinations(self, coin_id: str) -> Iterator[Dict[str, Any]]:
        """Generate all parameter combinations for optimization."""
        optimize_config = self.config_loader.get_optimize_config()

        # Get parameter ranges
        ranges = self._get_parameter_ranges(coin_id, optimize_config)

        # Generate all combinations
        param_names = list(ranges.keys())
        param_values = list(ranges.values())

        for combination in product(*param_values):
            params = dict(zip(param_names, combination))
            yield params

    def _get_parameter_ranges(
        self, coin_id: str, optimize_config: Dict[str, Any]
    ) -> Dict[str, List[Any]]:
        """Get parameter ranges for a specific coin."""
        ranges = {}

        # Default parameter ranges
        default_ranges = {
            "rsi": [10, 14, 18, 21, 24],
            "ema_fast": [8, 12, 16, 20, 24],
            "ema_slow": [26, 30, 34, 50, 60],
            "sl_mult": [1.0, 1.25, 1.5, 1.75, 2.0],
            "tp_mult": [2.0, 2.5, 3.0, 3.5, 4.0],
            "risk_budget_pct": [0.002, 0.005, 0.01, 0.02, 0.03],
        }

        # Check for coin-specific overrides
        tracked_coins = self.config_loader.get_tracked_coins_config()
        coin_config = tracked_coins.get(coin_id, {})
        coin_ranges = coin_config.get("optimize_ranges", {})

        # Use coin-specific ranges if available, otherwise use defaults
        for param, default_range in default_ranges.items():
            if param in coin_ranges:
                ranges[param] = coin_ranges[param]
            else:
                ranges[param] = default_range

        # Apply global optimization settings
        if optimize_config.get("disable_regime_filter", False):
            # Remove regime-related parameters
            pass

        if optimize_config.get("disable_vol_gate", False):
            # Remove volatility gate parameters
            pass

        return ranges

    def get_total_combinations(self, coin_id: str) -> int:
        """Get total number of parameter combinations."""
        ranges = self._get_parameter_ranges(coin_id, self.config_loader.get_optimize_config())
        total = 1
        for param_range in ranges.values():
            total *= len(param_range)
        return total

    def filter_combinations(
        self, combinations: Iterator[Dict[str, Any]], filters: Dict[str, Any]
    ) -> Iterator[Dict[str, Any]]:
        """Filter parameter combinations based on constraints."""
        for params in combinations:
            if self._is_valid_combination(params, filters):
                yield params

    def _is_valid_combination(self, params: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if a parameter combination is valid."""
        # Example: EMA fast must be less than EMA slow
        if "ema_fast" in params and "ema_slow" in params:
            if params["ema_fast"] >= params["ema_slow"]:
                return False

        # Example: Risk budget must be within reasonable range
        if "risk_budget_pct" in params:
            if params["risk_budget_pct"] <= 0 or params["risk_budget_pct"] > 0.1:
                return False

        # Example: SL multiplier must be positive
        if "sl_mult" in params:
            if params["sl_mult"] <= 0:
                return False

        # Example: TP multiplier must be greater than SL multiplier
        if "sl_mult" in params and "tp_mult" in params:
            if params["tp_mult"] <= params["sl_mult"]:
                return False

        return True
