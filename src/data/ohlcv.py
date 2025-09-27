from __future__ import annotations
import time
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Tuple, Optional

import requests


@dataclass
class Candle:
    ts: int            # epoch ms
    o: float
    h: float
    l: float
    c: float
    v: float


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _cache_path(cache_dir: Path, coin_id: str, timeframe: str) -> Path:
    safe = coin_id.replace("/", "_")
    return cache_dir / f"{safe}_{timeframe}.jsonl"


def save_jsonl(path: Path, rows: List[Dict]) -> None:
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    tmp.replace(path)


def load_jsonl(path: Path) -> List[Dict]:
    rows: List[Dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def fetch_ohlcv_coingecko(coin_id: str, vs_currency: str = "usd", days: int = 365, interval: str = "daily", api_key: Optional[str] = None) -> List[Candle]:
    """Fetch OHLC-like data from CoinGecko market_chart endpoint.
    Note: CoinGecko provides prices (close), market_caps, total_volumes; true OHLC is on /ohlc for limited days.
    We approximate OHLC from prices as close-only; O=H=L=C for indicator purposes (RSI/EMA/ATR with proxy ATR).
    """
    base = "https://api.coingecko.com/api/v3"
    url = f"{base}/coins/{coin_id}/market_chart"
    params = {
        "vs_currency": vs_currency,
        "days": days,
        "interval": interval,  # 'daily' or 'hourly'
    }
    headers = {}
    if api_key:
        headers["x-cg-pro-api-key"] = api_key
    # Basic retry/backoff for transient errors
    attempt = 0
    last_exc: Optional[Exception] = None
    while attempt < 3:
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            break
        except Exception as ex:
            last_exc = ex
            attempt += 1
            time.sleep(min(2 ** attempt, 5))
    else:
        # Exhausted retries
        raise last_exc or RuntimeError("CoinGecko fetch failed")
    prices = data.get("prices", [])  # [[ts_ms, price], ...]
    vols = data.get("total_volumes", [])  # [[ts_ms, vol], ...]
    vol_map = {int(t): float(v) for t, v in vols if isinstance(t, (int, float))}
    candles: List[Candle] = []
    for item in prices:
        if not isinstance(item, list) or len(item) < 2:
            continue
        ts = int(item[0])
        c = float(item[1])
        v = float(vol_map.get(ts, 0.0))
        candles.append(Candle(ts=ts, o=c, h=c, l=c, c=c, v=v))
    return candles


def get_candles(
    coin_id: str,
    timeframe: str = "1d",
    cache_dir: str | os.PathLike = "./data_cache",
    vs_currency: str = "usd",
    days: int = 365,
    use_cache: bool = True,
    api_key: Optional[str] = None,
) -> List[Candle]:
    """Return candles for coin_id at timeframe. Supports 1d and basic 1h/4h via hourly market_chart.
    Note: CoinGecko returns hourly data reliably up to ~90 days. For days > 90 with 1h/4h, we cap to 90 days.
    Caches JSONL to reduce API calls.
    """
    cache_dir_p = Path(cache_dir)
    _ensure_dir(cache_dir_p)
    if timeframe not in ("1d", "1h", "4h"):
        raise ValueError("Supported timeframes: '1d', '1h', '4h'")
    cache_file = _cache_path(cache_dir_p, coin_id, f"{timeframe}_d{days}")

    if use_cache and cache_file.exists():
        try:
            rows = load_jsonl(cache_file)
            return [Candle(**r) for r in rows]
        except Exception:
            pass

    # Fetch and cache
    if timeframe == "1d":
        interval = "daily"
        candles = fetch_ohlcv_coingecko(coin_id, vs_currency=vs_currency, days=days, interval=interval, api_key=api_key)
        rows = [c.__dict__ for c in candles]
        save_jsonl(cache_file, rows)
        return candles
    else:
        # Hourly source; cap to 90 days to avoid API degradation
        days_req = min(int(days), 90)
        interval = "hourly"
        hourly = fetch_ohlcv_coingecko(coin_id, vs_currency=vs_currency, days=days_req, interval=interval, api_key=api_key)
        if timeframe == "1h":
            rows = [c.__dict__ for c in hourly]
            save_jsonl(cache_file, rows)
            return hourly
        # 4h downsample: take every 4th hourly candle as proxy for 4h close; simple approach
        four_h: List[Candle] = []
        for idx, c in enumerate(hourly):
            if idx % 4 == 3:
                four_h.append(c)
        if not four_h and hourly:
            # if less than 4 samples, return last as single candle
            four_h = [hourly[-1]]
        rows = [c.__dict__ for c in four_h]
        save_jsonl(cache_file, rows)
        return four_h
