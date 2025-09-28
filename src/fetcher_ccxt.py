from __future__ import annotations
from typing import Dict, Optional

import ccxt  # type: ignore


class CCXTPriceFetcher:
    """Simple CCXT-based price fetcher for spot markets.

    - exchange_name: e.g., 'binance', 'bybit', 'coinbase'
    - symbol_to_market: mapping from our symbol (e.g., 'SOL') to exchange market (e.g., 'SOL/USDT')
    """

    def __init__(self, exchange_name: str, symbol_to_market: Dict[str, str]):
        self.exchange_name = exchange_name
        self.symbol_to_market = symbol_to_market
        ex_cls = getattr(ccxt, exchange_name)
        self.ex = ex_cls(
            {
                "enableRateLimit": True,
            }
        )

    def get_prices_by_symbols(self, id_to_symbol: Dict[str, str]) -> Dict[str, Optional[float]]:
        out: Dict[str, Optional[float]] = {}
        for cid, sym in id_to_symbol.items():
            market = self.symbol_to_market.get(sym.upper()) or f"{sym.upper()}/USDT"
            try:
                ticker = self.ex.fetch_ticker(market)
                price = (
                    ticker.get("last")
                    or ticker.get("close")
                    or ticker.get("ask")
                    or ticker.get("bid")
                )
                out[cid] = float(price) if price is not None else None
            except Exception:
                out[cid] = None
        return out
