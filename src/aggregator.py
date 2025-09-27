from __future__ import annotations
from statistics import median
from typing import Dict, List, Optional, Tuple

from rich.console import Console

from .fetcher import PriceFetcher  # CMC
from .fetcher_coingecko import CoingeckoFetcher  # Coingecko

console = Console()


class PriceAggregator:
    """Fetch prices from multiple providers and compute an aggregate price
    with an agreement metric.
    """

    def __init__(self, cmc: PriceFetcher, cg: CoingeckoFetcher, agreement_max_diff_pct: float = 0.5,
                 enabled_sources: Optional[List[str]] = None):
        self.cmc = cmc
        self.cg = cg
        self.agreement_max_diff_pct = agreement_max_diff_pct
        # enabled_sources can be a subset of {"cmc","coingecko"}
        self.enabled_sources = set((enabled_sources or ["cmc", "coingecko"]))

    def aggregate_prices(self, id_to_symbol: Dict[str, str], cg_ids: Optional[Dict[str, str]] = None) -> Dict[str, Dict[str, Optional[object]]]:
        """Return a mapping coin_id -> {
            'price': float|None,            # aggregated price
            'providers': List[str],         # providers that returned a price
            'agreement_diff_pct': float|None  # max deviation from median across providers in %
        }
        """
        # Fetch from both sources
        out: Dict[str, Dict[str, Optional[object]]] = {}
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

        for cid in id_to_symbol.keys():
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

            if not vals:
                out[cid] = {
                    'price': None,
                    'providers': providers,
                    'agreement_diff_pct': None,
                }
                continue

            prices_only = [v for _, v in vals]
            med = median(prices_only)
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

            out[cid] = {
                'price': float(med),
                'providers': providers,
                'agreement_diff_pct': diff_pct_val,
            }
        return out
