from __future__ import annotations

import random
import time
from typing import Dict, Iterable, Optional

import requests
from rich.console import Console

console = Console()


class CoingeckoFetcher:
    def __init__(self, base_url: str = "https://api.coingecko.com/api/v3", timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        # retry config
        self.max_retries = 2
        self.backoff_base = 0.3  # seconds
        # provider rate-limit backoff
        self.backoff_until_ts: float = 0.0
        self.backoff_seconds: int = 0
        self.backoff_cap: int = 600  # 10 minutes cap

    def _request_with_retries(self, url: str, params: Dict[str, str]):
        last_exc = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
                resp.raise_for_status()
                return resp
            except requests.RequestException as e:
                last_exc = e
                # If 429, set/extend provider backoff
                try:
                    status = getattr(e.response, "status_code", None)
                except Exception:
                    status = None
                if status == 429:
                    # Exponential backoff starting at 120s
                    self.backoff_seconds = min(
                        max(120, self.backoff_seconds * 2 or 120), self.backoff_cap
                    )
                    self.backoff_until_ts = time.time() + self.backoff_seconds
                    console.print(
                        f"[yellow]Coingecko rate-limited. Backing off for {self.backoff_seconds}s.[/yellow]"
                    )
                    break
                if attempt < self.max_retries:
                    sleep_s = self.backoff_base * (2**attempt) + random.uniform(0, 0.2)
                    time.sleep(sleep_s)
                else:
                    break
        raise last_exc

    def get_prices_by_ids(self, ids: Iterable[str]) -> Dict[str, Optional[float]]:
        """Fetch current USD prices for given Coingecko coin ids.
        Returns mapping id -> price (float) or None on failure/missing.
        """
        ids = [c for c in ids]
        if not ids:
            return {}
        # Respect active provider backoff window
        if time.time() < self.backoff_until_ts:
            return {cid: None for cid in ids}
        try:
            url = f"{self.base_url}/simple/price"
            params = {
                "ids": ",".join(ids),
                "vs_currencies": "usd",
            }
            resp = self._request_with_retries(url, params)
            data = resp.json()  # {"bitcoin": {"usd": 12345.6}, ...}
            out: Dict[str, Optional[float]] = {}
            for cid in ids:
                val = data.get(cid, {})
                price = val.get("usd")
                out[cid] = float(price) if price is not None else None
            return out
        except requests.RequestException as e:
            console.print(f"[red]Error fetching prices from Coingecko: {e}[/red]")
            return {cid: None for cid in ids}
