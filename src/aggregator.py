from __future__ import annotations
from statistics import median
from typing import Dict, List, Optional, Tuple
import time

from rich.console import Console

from .fetcher import PriceFetcher  # CMC
from .fetcher_coingecko import CoingeckoFetcher  # Coingecko
from .fetcher_ccxt import CCXTPriceFetcher  # CCXT spot
from .fetcher_websocket import WebSocketPriceFetcher

console = Console()


class PriceAggregator:
    """Fetch prices from multiple providers and compute an aggregate price
    with an agreement metric.
    """

    def __init__(
        self,
        cmc: PriceFetcher,
        cg: CoingeckoFetcher,
        agreement_max_diff_pct: float = 0.5,
        enabled_sources: Optional[List[str]] = None,
        ccxt: CCXTPriceFetcher | None = None,
        websocket: WebSocketPriceFetcher | None = None,
        cache_ttl: int = 2,
    ):
        self.cmc = cmc
        self.cg = cg
        self.ccxt = ccxt
        self.websocket = websocket
        self.agreement_max_diff_pct = agreement_max_diff_pct
        # enabled_sources can be a subset of {"cmc","coingecko","ccxt"}
        if enabled_sources is None:
            self.enabled_sources = ["cmc", "coingecko"]
        else:
            self.enabled_sources = list(enabled_sources)
        self.cache = {}
        self.cache_ttl = cache_ttl

    def aggregate_prices(
        self, id_to_symbol: Dict[str, str], cg_ids: Optional[Dict[str, str]] = None
    ) -> Dict[str, Dict[str, Optional[object]]]:
        """Return a mapping coin_id -> {
            'price': float|None,            # aggregated price
            'providers': List[str],         # providers that returned a price
            'agreement_diff_pct': float|None  # max deviation from median across providers in %
        }
        """
        # Fetch from configured sources
        out: Dict[str, Dict[str, Optional[object]]] = {}
        now = time.time()
        cached_results = {}
        uncached_id_to_symbol = {}

        for cid, symbol in id_to_symbol.items():
            if cid in self.cache and (now - self.cache[cid]["timestamp"]) < self.cache_ttl:
                cached_results[cid] = self.cache[cid]["data"]
            else:
                uncached_id_to_symbol[cid] = symbol

        if not uncached_id_to_symbol:
            return cached_results
        if "cmc" in self.enabled_sources:
            try:
                cmc_prices = self.cmc.get_prices_by_symbols(id_to_symbol)
            except Exception:
                cmc_prices = {cid: None for cid in id_to_symbol.keys()}
        else:
            cmc_prices = {cid: None for cid in id_to_symbol.keys()}
        if "coingecko" in self.enabled_sources:
            try:
                # If a mapping is provided, translate our coin_ids to CoinGecko ids
                ids = list(id_to_symbol.keys())
                if cg_ids:
                    cg_query_ids = [cg_ids.get(cid, cid) for cid in ids]
                    cg_raw = self.cg.get_prices_by_ids(cg_query_ids)
                    # Map back to our coin_ids
                    cg_prices = {}
                    for cid, qid in zip(ids, cg_query_ids):
                        cg_prices[cid] = cg_raw.get(qid)
                else:
                    cg_prices = self.cg.get_prices_by_ids(ids)
            except Exception:
                cg_prices = {cid: None for cid in id_to_symbol.keys()}
        else:
            cg_prices = {cid: None for cid in id_to_symbol.keys()}
        if "websocket" in self.enabled_sources and self.websocket is not None:
            try:
                ws_prices = self.websocket.get_prices()
            except Exception:
                ws_prices = {cid: None for cid in id_to_symbol.keys()}
        else:
            ws_prices = {cid: None for cid in id_to_symbol.keys()}

        if "ccxt" in self.enabled_sources and self.ccxt is not None:
            try:
                ccxt_prices = self.ccxt.get_prices_by_symbols(id_to_symbol)
            except Exception:
                ccxt_prices = {cid: None for cid in id_to_symbol.keys()}
        else:
            ccxt_prices = {cid: None for cid in id_to_symbol.keys()}

        for cid in uncached_id_to_symbol.keys():
            vals: List[Tuple[str, float]] = []
            providers: List[str] = []
            cmc_val = cmc_prices.get(cid)
            if cmc_val is not None:
                vals.append(("cmc", float(cmc_val)))
                providers.append("cmc")
            cg_val = cg_prices.get(cid)
            if cg_val is not None:
                vals.append(("coingecko", float(cg_val)))
                providers.append("coingecko")
            ccxt_val = ccxt_prices.get(cid)
            if ccxt_val is not None:
                vals.append(("ccxt", float(ccxt_val)))
                providers.append("ccxt")

            ws_val = ws_prices.get(id_to_symbol[cid])
            if ws_val is not None:
                vals.append(("websocket", float(ws_val)))
                providers.append("websocket")

            if not vals:
                out[cid] = {
                    "price": None,
                    "providers": providers,
                    "agreement_diff_pct": None,
                    "stability_score": 0.0,
                }
                continue

            prices_only = [v for _, v in vals]
            # Ensure self.enabled_sources is treated as a list for indexed access.
            # This handles cases where it might have been inadvertently set to a set
            # or another non-subscriptable iterable. It also handles empty collections.
            primary_source_key = None
            if self.enabled_sources:
                enabled_sources_list = list(self.enabled_sources)
                if enabled_sources_list:
                    primary_source_key = enabled_sources_list[0]

            primary_price = next((p for s, p in vals if s == primary_source_key), None)
            med = median(prices_only)
            final_price = primary_price if primary_price is not None else med
            # If we only have a single provider, do not compute agreement; show None
            if len(prices_only) < 2:
                diff_pct_val: Optional[float] = None
            else:
                # max deviation from median in percent
                if med == 0:
                    diff_pct_val = 0.0
                else:
                    diff_pct_val = max(abs(v - med) / med for v in prices_only) * 100.0
                diff_pct_val = round(diff_pct_val, 4)

            # Stability score (0..1): combine provider count and inverse of variance proxy
            try:
                prov_factor = min(1.0, len(providers) / 3.0)  # up to 3 providers
                if diff_pct_val is None:
                    var_factor = 0.6  # unknown variance, neutral-ish if only one provider
                else:
                    # If agreement is within threshold, high score; decay beyond ~4x threshold
                    denom = max(1e-6, float(self.agreement_max_diff_pct) * 4.0)
                    var_factor = max(0.0, 1.0 - float(diff_pct_val) / denom)
                stability_score = 0.5 * prov_factor + 0.5 * var_factor
                stability_score = max(0.0, min(1.0, float(stability_score)))
            except Exception:
                stability_score = 0.0

            out[cid] = {
                "price": float(med),
                "providers": providers,
                "agreement_diff_pct": diff_pct_val,
                "stability_score": float(stability_score),
            }
        for cid, data in out.items():
            self.cache[cid] = {"timestamp": now, "data": data}

        out.update(cached_results)
        return out
