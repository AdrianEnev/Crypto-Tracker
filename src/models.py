from dataclasses import dataclass
from datetime import datetime
from typing import Dict


@dataclass
class CoinConfig:
    symbol: str
    name: str
    threshold: float
    check_interval: int
    disabled: bool = False


@dataclass
class AppConfig:
    tracked_coins: Dict[str, CoinConfig]
    api_base_url: str
    api_timeout: int


@dataclass
class MarketSnapshot:
    """Represents a point-in-time market view for a coin."""

    price: float
    exchange: str  # e.g., "CMC" for CoinMarketCap
    last_checked: datetime  # UTC timestamp


@dataclass
class Decision:
    """Represents a recommendation and its meta for display/logging."""

    signal: str  # e.g., "threshold_check"
    confidence: float  # 0.0 - 1.0
    action_recommended: str  # "Buy" | "Sell" | "Hold" | "Manual"
    action_taken: str = "None"  # "None" | "Placed" | "Filled" | "Rejected"
    reason: str = ""
