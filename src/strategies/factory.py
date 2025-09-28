import importlib
from .base import BaseStrategy


def get_strategy(strategy_name: str, strategy_config: dict) -> BaseStrategy:
    """
    Factory function to get a strategy instance by name.
    """
    try:
        module_name = f"src.strategies.{strategy_name.lower()}"
        # Convert snake_case to PascalCase for class names
        words = strategy_name.split("_")
        strategy_class_name = "".join(word.capitalize() for word in words) + "Strategy"

        strategy_module = importlib.import_module(module_name)
        strategy_class = getattr(strategy_module, strategy_class_name)

        return strategy_class(strategy_config)
    except (ImportError, AttributeError) as e:
        raise ValueError(f"Could not find strategy '{strategy_name}'. {e}")
