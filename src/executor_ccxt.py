from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import ccxt  # type: ignore


@dataclass
class LiveOrderResult:
    id: str
    status: str
    symbol: str
    side: str
    type: str
    price: Optional[float]
    amount: Optional[float]
    cost: Optional[float]


class CCXTLiveExecutor:
    """Minimal live executor using CCXT.

    Notes:
    - Expects API/secret to be set for the exchange.
    - Conforms to market precision and min notional where possible.
    - size_usd is converted to base-asset amount using the latest price.
    - For simplicity, TP/SL are not placed as OCO here; those can be added later per-exchange.
    """

    def __init__(self, exchange_name: str, api_key: str, api_secret: str):
        ex_cls = getattr(ccxt, exchange_name)
        self.ex = ex_cls({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
        })
        self.markets = self.ex.load_markets()

    def _conform_amount(self, market: Dict[str, Any], amount: float) -> float:
        try:
            step = market.get('limits', {}).get('amount', {}).get('step')
            if step and step > 0:
                amount = (amount // step) * step
        except Exception:
            pass
        precision = market.get('precision', {}).get('amount')
        if isinstance(precision, int) and precision >= 0:
            amount = float(f"{amount:.{precision}f}")
        return max(amount, 0.0)

    def _conform_price(self, market: Dict[str, Any], price: float) -> float:
        precision = market.get('precision', {}).get('price')
        if isinstance(precision, int) and precision >= 0:
            price = float(f"{price:.{precision}f}")
        return max(price, 0.0)

    def _min_notional_ok(self, market: Dict[str, Any], amount: float, price: float) -> bool:
        try:
            min_cost = market.get('limits', {}).get('cost', {}).get('min')
            if min_cost is not None:
                return (amount * price) >= float(min_cost)
        except Exception:
            pass
        return True

    def _last_price(self, symbol: str) -> Optional[float]:
        try:
            t = self.ex.fetch_ticker(symbol)
            px = t.get('last') or t.get('close') or t.get('ask') or t.get('bid')
            return float(px) if px is not None else None
        except Exception:
            return None

    def place_order(self, symbol: str, side: str, size_usd: float, order_type: str = "market", price: Optional[float] = None) -> LiveOrderResult:
        """Place a live order sized in USD. Returns a normalized order result.

        side: "buy" or "sell"
        order_type: "market" or "limit"
        """
        if size_usd is None or size_usd <= 0:
            raise ValueError("size_usd must be positive")
        market = self.markets.get(symbol)
        if market is None:
            raise ValueError(f"Unknown market {symbol}")
        px = price if (order_type == "limit" and price is not None) else self._last_price(symbol)
        if px is None or px <= 0:
            raise RuntimeError("Could not obtain price for sizing")
        amount = size_usd / float(px)
        amount = self._conform_amount(market, amount)
        px_use = self._conform_price(market, float(px)) if order_type == "limit" and price is not None else None
        # Enforce min notional if available
        if not self._min_notional_ok(market, amount, float(px)):
            raise RuntimeError("Order notional below exchange minimum")

        params: Dict[str, Any] = {}
        try:
            order = self.ex.create_order(symbol=symbol, type=order_type, side=side, amount=amount, price=px_use, params=params)
            return LiveOrderResult(
                id=str(order.get('id')),
                status=str(order.get('status', 'open')),
                symbol=symbol,
                side=side,
                type=order_type,
                price=float(order.get('price') or px_use or 0.0) if (order.get('price') or px_use) is not None else None,
                amount=float(order.get('amount')) if order.get('amount') is not None else None,
                cost=float(order.get('cost')) if order.get('cost') is not None else None,
            )
        except Exception as ex:
            raise RuntimeError(f"Exchange order error: {ex}")

    def place_oco_sell(self, symbol: str, quantity: float, tp_price: float, sl_stop_price: float, sl_limit_price: Optional[float] = None) -> bool:
        """Attempt to place an OCO sell (TP + SL) on supported exchanges (Binance).
        Returns True if submitted, False if unsupported or failed.
        """
        try:
            market = self.markets.get(symbol)
            if market is None:
                return False
            # Conform amounts and prices
            qty = self._conform_amount(market, float(quantity))
            tp_p = self._conform_price(market, float(tp_price))
            sl_stop = self._conform_price(market, float(sl_stop_price))
            sl_lim = self._conform_price(market, float(sl_limit_price if sl_limit_price is not None else sl_stop))
            # Only attempt direct OCO on binance; other exchanges likely unsupported via ccxt
            if getattr(self.ex, 'id', '') != 'binance':
                return False
            # Binance OCO via ccxt params
            params = {
                'type': 'OCO',
                'stopPrice': sl_stop,
                'stopLimitPrice': sl_lim,
                'stopLimitTimeInForce': 'GTC',
            }
            # For OCO, ccxt expects a limit leg price and amount; pass TP as limit price
            order = self.ex.create_order(symbol=symbol, type='limit', side='sell', amount=qty, price=tp_p, params=params)
            _ = order  # not used beyond this
            return True
        except Exception:
            return False
