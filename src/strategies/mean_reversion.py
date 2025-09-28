import pandas as pd
from .base import BaseStrategy
from src.indicators.core import rsi, bollinger

class MeanReversionStrategy(BaseStrategy):
    def __init__(self, strategy_config: dict):
        super().__init__(strategy_config)
        self.rsi_period = self.config.get('rsi_period', 14)
        self.buy_threshold = self.config.get('buy_threshold', 30)
        self.sell_threshold = self.config.get('sell_threshold', 70)
        # Optional Bollinger parameters
        bb_cfg = self.config.get('bollinger', {}) if isinstance(self.config.get('bollinger', {}), dict) else {}
        # Backwards-compat flags: allow flat flags at top-level as well
        self.use_bollinger = bool(self.config.get('use_bollinger', bb_cfg.get('use', False)))
        self.bb_period = int(self.config.get('bb_period', bb_cfg.get('period', 20)))
        self.bb_stddev = float(self.config.get('bb_stddev', bb_cfg.get('stddev', 2.0)))
        # If require both RSI + BB conditions, else use RSI-only
        self.require_confluence = bool(self.config.get('require_confluence', bb_cfg.get('require_confluence', True)))

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generates buy signals when RSI is oversold and sell signals when overbought.
        """
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0

        # Calculate RSI
        rsi_values = rsi(data['close'].tolist(), self.rsi_period)
        data['rsi'] = rsi_values

        # Optional Bollinger Bands
        if self.use_bollinger:
            mid, up, lo, width = bollinger(data['close'].tolist(), period=self.bb_period, stddev=self.bb_stddev)
            data['bb_mid'] = mid
            data['bb_up'] = up
            data['bb_lo'] = lo
        else:
            data['bb_lo'] = None
            data['bb_up'] = None

        # Generate signals with optional confluence
        buy_mask = data['rsi'] < self.buy_threshold
        sell_mask = data['rsi'] > self.sell_threshold
        if self.use_bollinger and self.require_confluence:
            buy_mask &= data['close'] <= data['bb_lo']
            sell_mask &= data['close'] >= data['bb_up']
        elif self.use_bollinger and not self.require_confluence:
            # Either RSI oversold OR touching lower band (loose mode)
            buy_mask = (data['rsi'] < self.buy_threshold) | (data['close'] <= data['bb_lo'])
            sell_mask = (data['rsi'] > self.sell_threshold) | (data['close'] >= data['bb_up'])

        signals.loc[buy_mask, 'signal'] = 1  # Buy signal
        signals.loc[sell_mask, 'signal'] = -1 # Sell signal

        return signals
