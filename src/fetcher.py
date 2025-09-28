import os
import requests
import time
import random
from typing import Dict, Optional
from rich.console import Console

console = Console()


class PriceFetcher:
    def __init__(self, base_url: str, timeout: int = 10):
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
        self.api_key = os.getenv("COINMARKETCAP_API_KEY")
        # retry config
        self.max_retries = 2
        self.backoff_base = 0.3  # seconds

    def _request_with_retries(self, url: str, headers: Dict[str, str], params: Dict[str, str]):
        last_exc = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = self.session.get(url, headers=headers, params=params, timeout=self.timeout)
                resp.raise_for_status()
                return resp
            except requests.RequestException as e:
                last_exc = e
                if attempt < self.max_retries:
                    sleep_s = self.backoff_base * (2**attempt) + random.uniform(0, 0.2)
                    time.sleep(sleep_s)
                else:
                    break
        raise last_exc

    def get_prices_by_symbols(self, id_to_symbol: Dict[str, str]) -> Dict[str, Optional[float]]:
        """Fetch current USD prices for the given mapping of coin IDs to symbols.

        Params:
            id_to_symbol: mapping of our internal coin_id (from YAML keys) to symbol strings (e.g., 'btc', 'eth').
        Returns:
            Dict mapping coin_id -> price (float) or None on failure/missing.
        """
        if not id_to_symbol:
            return {}

        missing_key_result = {cid: None for cid in id_to_symbol.keys()}

        if not self.api_key:
            console.print(
                "[red]COINMARKETCAP_API_KEY is not set. Please set it in .env file in project root[/red]"
            )
            return missing_key_result

        try:
            # Build symbols comma-separated, CoinMarketCap expects uppercase symbols
            symbols = ",".join(sorted({sym.upper() for sym in id_to_symbol.values()}))
            url = f"{self.base_url}/v2/cryptocurrency/quotes/latest"
            headers = {"X-CMC_PRO_API_KEY": self.api_key}
            params = {"symbol": symbols, "convert": "USD"}
            response = self._request_with_retries(url, headers, params)
            data = response.json()

            # Data shape: { 'data': { 'BTC': [{...}], 'ETH': [{...}], ... } }
            quotes = data.get("data", {})
            out: Dict[str, Optional[float]] = {}
            for cid, sym in id_to_symbol.items():
                sym_up = sym.upper()
                entry = quotes.get(sym_up)
                price = None
                if isinstance(entry, list) and entry:
                    # Some plans return a list with one dict
                    quote = entry[0].get("quote", {}).get("USD", {})
                    price = quote.get("price")
                elif isinstance(entry, dict):
                    # Some responses may return a dict directly
                    quote = entry.get("quote", {}).get("USD", {})
                    price = quote.get("price")
                out[cid] = price
            return out

        except requests.RequestException as e:
            console.print(f"[red]Error fetching prices from CoinMarketCap: {e}[/red]")
            return {cid: None for cid in id_to_symbol.keys()}
