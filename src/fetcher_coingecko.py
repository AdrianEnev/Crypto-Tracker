from __future__ import annotations
import requests
from typing import Dict, Optional, Iterable
from rich.console import Console

console = Console()


class CoingeckoFetcher:
    def __init__(self, base_url: str = "https://api.coingecko.com/api/v3", timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def get_prices_by_ids(self, ids: Iterable[str]) -> Dict[str, Optional[float]]:
        """Fetch current USD prices for given Coingecko coin ids.
        Returns mapping id -> price (float) or None on failure/missing.
        """
        ids = [c for c in ids]
        if not ids:
            return {}
        try:
            url = f"{self.base_url}/simple/price"
            params = {
                "ids": ",".join(ids),
                "vs_currencies": "usd",
            }
            resp = self.session.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
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
