"""
Volatility-based trading strategy.
Implements multiple volatility approaches: mean reversion in low volatility, 
breakouts in expanding volatility, and volatility targeting.
"""

from typing import List, Optional

import pandas as pd

from ..indicators.core import bollinger, rolling_mean, rolling_std

from .base import BaseStrategy


class VolatilityStrategy(BaseStrategy):
    """
    Volatility-based trading strategy with multiple modes.
    
    Config params:
    - mode: str = "mean_reversion" | "breakout" | "adaptive"
    - vol_period: int = 20 (period for volatility calculation)
    - vol_threshold_low: float = 0.5 (low volatility threshold)
    - vol_threshold_high: float = 2.0 (high volatility threshold)
    - bb_period: int = 20 (Bollinger Bands period)
    - bb_stddev: float = 2.0 (Bollinger Bands standard deviation)
    - rsi_period: int = 14 (RSI period for confirmation)
    - rsi_oversold: float = 30 (RSI oversold level)
    - rsi_overbought: float = 70 (RSI overbought level)
    - volume_confirmation: bool = True (require volume confirmation)
    - volume_period: int = 20 (volume average period)
    - volume_mult: float = 1.5 (volume multiplier threshold)
    """

    def __init__(self, strategy_config: dict):
        super().__init__(strategy_config)
        
        # Strategy mode
        self.mode = self.config.get("mode", "adaptive")
        
        # Volatility parameters
        self.vol_period = int(self.config.get("vol_period", 20))
        self.vol_threshold_low = float(self.config.get("vol_threshold_low", 0.5))
        self.vol_threshold_high = float(self.config.get("vol_threshold_high", 2.0))
        
        # Bollinger Bands parameters
        self.bb_period = int(self.config.get("bb_period", 20))
        self.bb_stddev = float(self.config.get("bb_stddev", 2.0))
        
        # RSI parameters
        self.rsi_period = int(self.config.get("rsi_period", 14))
        self.rsi_oversold = float(self.config.get("rsi_oversold", 30))
        self.rsi_overbought = float(self.config.get("rsi_overbought", 70))
        
        # Volume confirmation
        self.volume_confirmation = bool(self.config.get("volume_confirmation", True))
        self.volume_period = int(self.config.get("volume_period", 20))
        self.volume_mult = float(self.config.get("volume_mult", 1.5))
        
        # Additional parameters for adaptive mode
        self.vol_lookback = int(self.config.get("vol_lookback", 100))
        self.vol_percentile_low = float(self.config.get("vol_percentile_low", 25))
        self.vol_percentile_high = float(self.config.get("vol_percentile_high", 75))

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals based on volatility analysis.
        """
        signals = pd.DataFrame(index=data.index)
        signals["signal"] = 0
        
        if len(data) < max(self.vol_period, self.bb_period, self.rsi_period):
            return signals
        
        closes = data["close"].tolist()
        volumes = data["volume"].tolist() if "volume" in data.columns else [0.0] * len(data)
        
        # Calculate volatility indicators
        volatility_data = self._calculate_volatility_indicators(closes, volumes)
        
        # Add volatility data to main dataframe
        for key, value in volatility_data.items():
            data[key] = value
        
        # Generate signals based on mode
        if self.mode == "mean_reversion":
            signals = self._generate_mean_reversion_signals(data)
        elif self.mode == "breakout":
            signals = self._generate_breakout_signals(data)
        elif self.mode == "adaptive":
            signals = self._generate_adaptive_signals(data)
        else:
            raise ValueError(f"Unknown volatility strategy mode: {self.mode}")
        
        return signals

    def _calculate_volatility_indicators(self, closes: List[float], volumes: List[float]) -> dict:
        """Calculate all volatility-related indicators."""
        # Price volatility (standard deviation of returns)
        returns = []
        for i in range(1, len(closes)):
            if closes[i-1] > 0:
                ret = (closes[i] - closes[i-1]) / closes[i-1]
                returns.append(ret)
            else:
                returns.append(0.0)
        
        # Add initial return as 0
        returns = [0.0] + returns
        
        # Rolling volatility
        vol_rolling = rolling_std(returns, self.vol_period)
        
        # Bollinger Bands
        bb_mid, bb_upper, bb_lower, bb_width = bollinger(
            closes, period=self.bb_period, stddev=self.bb_stddev
        )
        
        # Bollinger Band width (volatility proxy)
        bb_width_pct = []
        for i, (width, mid) in enumerate(zip(bb_width, bb_mid)):
            if mid and mid > 0:
                bb_width_pct.append((width / mid) * 100)
            else:
                bb_width_pct.append(None)
        
        # Volume indicators
        vol_avg = rolling_mean(volumes, self.volume_period)
        vol_ratio = []
        for i, (vol, avg) in enumerate(zip(volumes, vol_avg)):
            if avg and avg > 0:
                vol_ratio.append(vol / avg)
            else:
                vol_ratio.append(1.0)
        
        # Volatility percentiles for adaptive mode
        vol_percentiles = self._calculate_volatility_percentiles(bb_width_pct)
        
        return {
            "returns": returns,
            "volatility_rolling": vol_rolling,
            "bb_mid": bb_mid,
            "bb_upper": bb_upper,
            "bb_lower": bb_lower,
            "bb_width": bb_width,
            "bb_width_pct": bb_width_pct,
            "volume_avg": vol_avg,
            "volume_ratio": vol_ratio,
            "vol_percentile_low": vol_percentiles["low"],
            "vol_percentile_high": vol_percentiles["high"],
            "vol_percentile_current": vol_percentiles["current"],
        }

    def _calculate_volatility_percentiles(self, bb_width_pct: List[Optional[float]]) -> dict:
        """Calculate volatility percentiles for adaptive mode."""
        # Filter out None values and get recent data
        valid_widths = [w for w in bb_width_pct if w is not None]
        
        if len(valid_widths) < self.vol_lookback:
            lookback_data = valid_widths
        else:
            lookback_data = valid_widths[-self.vol_lookback:]
        
        if not lookback_data:
            return {
                "low": [None] * len(bb_width_pct),
                "high": [None] * len(bb_width_pct),
                "current": [None] * len(bb_width_pct),
            }
        
        # Calculate percentiles
        low_percentile = self._percentile(lookback_data, self.vol_percentile_low)
        high_percentile = self._percentile(lookback_data, self.vol_percentile_high)
        
        # Create arrays aligned with original data
        low_array = []
        high_array = []
        current_array = []
        
        for i, width in enumerate(bb_width_pct):
            if width is not None:
                current_array.append(width)
                low_array.append(low_percentile)
                high_array.append(high_percentile)
            else:
                current_array.append(None)
                low_array.append(None)
                high_array.append(None)
        
        return {
            "low": low_array,
            "high": high_array,
            "current": current_array,
        }

    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of data."""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        index = int((percentile / 100.0) * (len(sorted_data) - 1))
        return sorted_data[index]

    def _generate_mean_reversion_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate mean reversion signals in low volatility periods."""
        signals = pd.DataFrame(index=data.index)
        signals["signal"] = 0
        
        # Low volatility condition
        low_vol = pd.Series(data["bb_width_pct"]) <= self.vol_threshold_low
        
        # Price near Bollinger Bands
        near_lower_band = data["close"] <= data["bb_lower"] * 1.02  # Within 2% of lower band
        near_upper_band = data["close"] >= data["bb_upper"] * 0.98  # Within 2% of upper band
        
        # Volume confirmation
        volume_ok = pd.Series(data["volume_ratio"]) >= self.volume_mult if self.volume_confirmation else pd.Series([True] * len(data))
        
        # Generate buy signals (oversold in low volatility)
        buy_condition = low_vol & near_lower_band & volume_ok
        signals.loc[buy_condition, "signal"] = 1
        
        # Generate sell signals (overbought in low volatility)
        sell_condition = low_vol & near_upper_band & volume_ok
        signals.loc[sell_condition, "signal"] = -1
        
        return signals

    def _generate_breakout_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate breakout signals in expanding volatility."""
        signals = pd.DataFrame(index=data.index)
        signals["signal"] = 0
        
        # High volatility condition (expanding volatility)
        high_vol = pd.Series(data["bb_width_pct"]) >= self.vol_threshold_high
        
        # Price breakout from Bollinger Bands
        breakout_up = data["close"] > data["bb_upper"]
        breakout_down = data["close"] < data["bb_lower"]
        
        # Volume confirmation
        volume_ok = pd.Series(data["volume_ratio"]) >= self.volume_mult if self.volume_confirmation else pd.Series([True] * len(data))
        
        # Generate buy signals (upward breakout in high volatility)
        buy_condition = high_vol & breakout_up & volume_ok
        signals.loc[buy_condition, "signal"] = 1
        
        # Generate sell signals (downward breakout in high volatility)
        sell_condition = high_vol & breakout_down & volume_ok
        signals.loc[sell_condition, "signal"] = -1
        
        return signals

    def _generate_adaptive_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate adaptive signals based on current volatility regime."""
        signals = pd.DataFrame(index=data.index)
        signals["signal"] = 0
        
        # Determine volatility regime
        current_vol = pd.Series(data["vol_percentile_current"])
        low_vol_threshold = pd.Series(data["vol_percentile_low"])
        high_vol_threshold = pd.Series(data["vol_percentile_high"])
        
        # Regime classification
        low_vol_regime = current_vol <= low_vol_threshold
        high_vol_regime = current_vol >= high_vol_threshold
        normal_vol_regime = ~(low_vol_regime | high_vol_regime)
        
        # Volume confirmation
        volume_ok = pd.Series(data["volume_ratio"]) >= self.volume_mult if self.volume_confirmation else pd.Series([True] * len(data))
        
        # Low volatility regime: mean reversion
        low_vol_buy = low_vol_regime & (data["close"] <= data["bb_lower"] * 1.02) & volume_ok
        low_vol_sell = low_vol_regime & (data["close"] >= data["bb_upper"] * 0.98) & volume_ok
        
        # High volatility regime: breakout following
        high_vol_buy = high_vol_regime & (data["close"] > data["bb_upper"]) & volume_ok
        high_vol_sell = high_vol_regime & (data["close"] < data["bb_lower"]) & volume_ok
        
        # Normal volatility regime: trend following with bands
        normal_vol_buy = normal_vol_regime & (data["close"] > data["bb_mid"]) & (data["close"] > data["bb_lower"]) & volume_ok
        normal_vol_sell = normal_vol_regime & (data["close"] < data["bb_mid"]) & (data["close"] < data["bb_upper"]) & volume_ok
        
        # Combine all signals
        buy_signals = low_vol_buy | high_vol_buy | normal_vol_buy
        sell_signals = low_vol_sell | high_vol_sell | normal_vol_sell
        
        signals.loc[buy_signals, "signal"] = 1
        signals.loc[sell_signals, "signal"] = -1
        
        return signals

    def get_strategy_info(self) -> dict:
        """Get strategy information and parameters."""
        return {
            "name": "Volatility Strategy",
            "mode": self.mode,
            "parameters": {
                "vol_period": self.vol_period,
                "vol_threshold_low": self.vol_threshold_low,
                "vol_threshold_high": self.vol_threshold_high,
                "bb_period": self.bb_period,
                "bb_stddev": self.bb_stddev,
                "rsi_period": self.rsi_period,
                "volume_confirmation": self.volume_confirmation,
                "volume_period": self.volume_period,
                "volume_mult": self.volume_mult,
            },
            "description": f"Volatility-based strategy in {self.mode} mode. "
                          f"Uses Bollinger Band width as volatility proxy and "
                          f"{'requires' if self.volume_confirmation else 'ignores'} volume confirmation.",
        }
