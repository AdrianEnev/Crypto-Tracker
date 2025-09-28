from abc import ABC, abstractmethod

import pandas as pd


class BaseStrategy(ABC):
    def __init__(self, strategy_config: dict):
        self.config = strategy_config

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generates trading signals for the given data.

        Args:
            data (pd.DataFrame): DataFrame with OHLCV data.

        Returns:
            pd.DataFrame: DataFrame with a 'signal' column (-1 for sell, 1 for buy, 0 for hold).
        """
        pass
