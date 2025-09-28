from __future__ import annotations

from pathlib import Path
from typing import List

# Third-party
import ccxt  # type: ignore

from .ohlcv import Candle, _cache_path, _ensure_dir, load_jsonl, save_jsonl


def get_candles_ccxt(
    exchange_name: str,
    market: str,
    timeframe: str = "1h",
    cache_dir: str | Path = "./data_cache",
    limit: int = 2000,
    use_cache: bool = True,
) -> List[Candle]:
    """Fetch candles from a CCXT exchange for a given market/timeframe.

    - exchange_name: e.g., "binance", "bybit", "coinbase"
    - market: e.g., "SOL/USDT"
    - timeframe: "1h", "4h", "1d" (must be supported by the exchange)
    - limit: max number of candles to fetch (exchange-dependent)
    - Caches to JSONL keyed by exchange+market+timeframe+limit
    """
    cache_dir_p = Path(cache_dir)
    _ensure_dir(cache_dir_p)
    safe_id = f"{exchange_name}_{market.replace('/', '-')}_{timeframe}_n{limit}"
    cache_file = _cache_path(cache_dir_p, safe_id, timeframe)

    if use_cache and cache_file.exists():
        try:
            rows = load_jsonl(cache_file)
            return [Candle(**r) for r in rows]
        except Exception:
            pass

    # Initialize exchange
    ex_cls = getattr(ccxt, exchange_name)
    ex = ex_cls(
        {
            "enableRateLimit": True,
            # If the user wants, they can set API keys for private endpoints;
            # not needed for public OHLCV.
        }
    )

    # Fetch OHLCV: returns [[ms, o, h, l, c, v], ...]
    ohlcv = ex.fetch_ohlcv(symbol=market, timeframe=timeframe, limit=limit)
    candles: List[Candle] = []
    for row in ohlcv:
        ts, o, h, l, c, v = row
        candles.append(
            Candle(ts=int(ts), o=float(o), h=float(h), l=float(l), c=float(c), v=float(v))
        )

    rows = [c.__dict__ for c in candles]
    save_jsonl(cache_file, rows)
    return candles
