import pandas as pd
from .base import BaseStrategy
from src.indicators.core import bollinger, rolling_mean
from typing import List, Optional


def _rolling_percentile(
    values: List[Optional[float]], window: int, pct: float
) -> List[Optional[float]]:
    """
    Compute rolling percentile (0-100) for a series with None handling. Returns aligned list.
    Uses a simple per-window sort; acceptable for typical strategy window sizes.
    """
    if window <= 0:
        return [None for _ in values]
    out: List[Optional[float]] = []
    from math import floor

    for i in range(len(values)):
        if i + 1 < window:
            out.append(None)
            continue
        win = [v for v in values[i - window + 1 : i + 1] if v is not None]
        if not win:
            out.append(None)
            continue
        win_sorted = sorted(win)
        # rank position for percentile (nearest-rank method)
        k = max(1, min(len(win_sorted), int(round((pct / 100.0) * len(win_sorted)))))
        out.append(win_sorted[k - 1])
    return out


class BreakoutStrategy(BaseStrategy):
    """
    Bollinger squeeze + breakout strategy with volume confirmation.

    Config params (under strategy.params):
    - bb_period: int = 20
    - bb_stddev: float = 2.0
    - squeeze_window: int = 100
    - squeeze_pctile: float = 20.0   # define squeeze threshold as pctile of width
    - volume_window: int = 20
    - volume_mult: float = 1.5
    - confirm_closes: int = 1        # require N consecutive closes beyond band
    """

    def __init__(self, strategy_config: dict):
        super().__init__(strategy_config)
        self.bb_period = int(self.config.get("bb_period", 20))
        self.bb_stddev = float(self.config.get("bb_stddev", 2.0))
        self.squeeze_window = int(self.config.get("squeeze_window", 100))
        self.squeeze_pctile = float(self.config.get("squeeze_pctile", 20.0))
        self.volume_window = int(self.config.get("volume_window", 20))
        self.volume_mult = float(self.config.get("volume_mult", 1.5))
        self.confirm_closes = int(self.config.get("confirm_closes", 1))

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        signals = pd.DataFrame(index=data.index)
        signals["signal"] = 0

        closes = data["close"].tolist()
        vols = data["volume"].tolist() if "volume" in data.columns else [0.0] * len(data)

        mid, up, lo, width = bollinger(closes, period=self.bb_period, stddev=self.bb_stddev)
        data["bb_mid"] = mid
        data["bb_up"] = up
        data["bb_lo"] = lo
        data["bb_width"] = width

        # Squeeze threshold as rolling percentile of width
        squeeze_thr = _rolling_percentile(
            data["bb_width"].tolist(), self.squeeze_window, self.squeeze_pctile
        )
        data["squeeze_thr"] = squeeze_thr
        data["in_squeeze"] = pd.Series(data["bb_width"]).astype(float) <= pd.Series(
            squeeze_thr
        ).astype(float)

        # Volume confirmation
        vmean = rolling_mean(vols, self.volume_window)
        data["vol_mean"] = vmean
        data["vol_confirm"] = pd.Series(vols).astype(float) > (
            pd.Series(vmean).astype(float) * self.volume_mult
        )

        # Breakout conditions
        close_ser = pd.Series(closes).astype(float)
        above_up = close_ser > pd.Series(up).astype(float)
        below_lo = close_ser < pd.Series(lo).astype(float)

        # Require N consecutive closes beyond bands if confirm_closes > 1
        if self.confirm_closes > 1:
            above_up = (
                above_up.rolling(self.confirm_closes)
                .apply(lambda x: 1.0 if all(x) else 0.0)
                .astype(bool)
            )
            below_lo = (
                below_lo.rolling(self.confirm_closes)
                .apply(lambda x: 1.0 if all(x) else 0.0)
                .astype(bool)
            )

        long_entry = above_up & data["in_squeeze"].astype(bool) & data["vol_confirm"].astype(bool)
        short_entry = below_lo & data["in_squeeze"].astype(bool) & data["vol_confirm"].astype(bool)

        signals.loc[long_entry.index[long_entry], "signal"] = 1
        signals.loc[short_entry.index[short_entry], "signal"] = -1

        return signals
