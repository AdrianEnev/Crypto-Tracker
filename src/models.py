from dataclasses import dataclass
from typing import Dict, List

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
