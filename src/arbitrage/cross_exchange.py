from __future__ import annotations
from typing import Dict, List, Optional, Tuple

# Lightweight scaffolding for cross-exchange arbitrage checks.
# Intentionally minimal and safe: does NOT place orders.


def find_spreads(
    orderbooks: Dict[str, Dict[str, float]], fee_bps: float = 10.0, buffer_bps: float = 10.0
) -> List[Dict[str, float]]:
    """
    Given a mapping: exchange -> { 'bid': float, 'ask': float }, compute cross-exchange spreads.
    Returns a list of opportunities with gross and net bps.
    """
    exchs = list(orderbooks.keys())
    out: List[Dict[str, float]] = []
    for i in range(len(exchs)):
        for j in range(len(exchs)):
            if i == j:
                continue
            a = exchs[i]
            b = exchs[j]
            ob_a = orderbooks[a]
            ob_b = orderbooks[b]
            bid = float(ob_b.get("bid", 0.0))
            ask = float(ob_a.get("ask", 0.0))
            if bid <= 0 or ask <= 0:
                continue
            gross_bps = (bid / ask - 1.0) * 10000.0
            # account for taker fees both sides + buffer
            net_bps = gross_bps - (2 * float(fee_bps)) - float(buffer_bps)
            if net_bps > 0:
                out.append(
                    {
                        "buy_exchange": a,
                        "sell_exchange": b,
                        "ask": ask,
                        "bid": bid,
                        "gross_bps": gross_bps,
                        "net_bps": net_bps,
                    }
                )
    # Sort by net bps desc
    out.sort(key=lambda x: x["net_bps"], reverse=True)
    return out
