import pandas as pd
from .base import BaseStrategy
from src.indicators.core import ema, rsi, macd

class MomentumStrategy(BaseStrategy):
    def __init__(self, strategy_config: dict):
        super().__init__(strategy_config)
        self.fast_ema_period = self.config.get('fast_ema_period', 12)
        self.slow_ema_period = self.config.get('slow_ema_period', 26)
        # Optional filters
        self.use_rsi = bool(self.config.get('use_rsi', False))
        self.rsi_period = int(self.config.get('rsi_period', 14))
        self.rsi_max_buy = float(self.config.get('rsi_max_buy', 70))
        self.rsi_min_sell = float(self.config.get('rsi_min_sell', 30))
        self.use_macd = bool(self.config.get('use_macd', False))
        self.macd_fast = int(self.config.get('macd_fast', 12))
        self.macd_slow = int(self.config.get('macd_slow', 26))
        self.macd_signal = int(self.config.get('macd_signal', 9))

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generates buy/sell signals based on EMA crossover.
        """
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0

        # Calculate EMAs
        closes = data['close'].tolist()
        fast_ema = ema(closes, self.fast_ema_period)
        slow_ema = ema(closes, self.slow_ema_period)

        data['fast_ema'] = fast_ema
        data['slow_ema'] = slow_ema

        # Optional RSI filter
        if self.use_rsi:
            data['rsi'] = rsi(closes, period=self.rsi_period)
        else:
            data['rsi'] = None

        # Optional MACD filter
        if self.use_macd:
            macd_line, signal_line, hist = macd(closes, fast_period=self.macd_fast, slow_period=self.macd_slow, signal_period=self.macd_signal)
            data['macd_line'] = macd_line
            data['macd_signal'] = signal_line
        else:
            data['macd_line'] = None
            data['macd_signal'] = None

        # Generate signals (crossover + optional filters)
        buy_cross = (data['fast_ema'] > data['slow_ema']) & (data['fast_ema'].shift(1) <= data['slow_ema'].shift(1))
        sell_cross = (data['fast_ema'] < data['slow_ema']) & (data['fast_ema'].shift(1) >= data['slow_ema'].shift(1))

        if self.use_rsi:
            buy_cross &= (data['rsi'].astype(float) <= self.rsi_max_buy)
            sell_cross &= (data['rsi'].astype(float) >= self.rsi_min_sell)

        if self.use_macd:
            buy_cross &= (data['macd_line'].astype(float) > data['macd_signal'].astype(float))
            sell_cross &= (data['macd_line'].astype(float) < data['macd_signal'].astype(float))

        signals.loc[buy_cross, 'signal'] = 1
        signals.loc[sell_cross, 'signal'] = -1

        return signals
