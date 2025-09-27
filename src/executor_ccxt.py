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
        # Failure tracking per endpoint
        self._fail_ts: Dict[str, list[float]] = {}

    def _record_fail(self, endpoint: str) -> None:
        try:
            import time
            arr = self._fail_ts.setdefault(endpoint, [])
            now = time.time()
            arr.append(now)
            # keep last 200 and within 120s
            self._fail_ts[endpoint] = [t for t in arr[-200:] if now - t <= 120.0]
        except Exception:
            pass

    def has_high_failure_rate(self, endpoint: str, threshold: int = 5, window_sec: int = 60) -> bool:
        try:
            import time
            now = time.time()
            arr = self._fail_ts.get(endpoint, [])
            cnt = len([t for t in arr if now - t <= window_sec])
            return cnt >= threshold
        except Exception:
            return False

    def _retry(self, fn, endpoint: str, *args, **kwargs):
        import random, time
        attempts = 0
        last_exc = None
        while attempts < 3:
            try:
                return fn(*args, **kwargs)
            except Exception as ex:
                last_exc = ex
                attempts += 1
                self._record_fail(endpoint)
                # jittered backoff: 0.5s, 1s
                time.sleep(min(1.0, 0.5 * (2 ** (attempts - 1))) + random.random() * 0.2)
        raise last_exc or RuntimeError(f"{endpoint} failed")

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

    def place_order(self, symbol: str, side: str, size_usd: float, order_type: str = "market", price: Optional[float] = None, client_order_id: Optional[str] = None) -> LiveOrderResult:
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
        # Pass clientOrderId if supported (Binance, Bybit, etc.)
        try:
            if client_order_id:
                if getattr(self.ex, 'id', '') == 'binance':
                    params['newClientOrderId'] = client_order_id
                else:
                    params['clientOrderId'] = client_order_id
        except Exception:
            pass
        try:
            order = self._retry(self.ex.create_order, 'create_order', symbol=symbol, type=order_type, side=side, amount=amount, price=px_use, params=params)
            result = LiveOrderResult(
                id=str(order.get('id')),
                status=str(order.get('status', 'open')),
                symbol=symbol,
                side=side,
                type=order_type,
                price=float(order.get('price') or px_use or 0.0) if (order.get('price') or px_use) is not None else None,
                amount=float(order.get('amount')) if order.get('amount') is not None else None,
                cost=float(order.get('cost')) if order.get('cost') is not None else None,
            )
            try:
                if client_order_id:
                    self._client_results[client_order_id] = result
            except Exception:
                pass
            return result
        except Exception as ex:
            raise RuntimeError(f"Exchange order error: {ex}")

    def place_oco_sell(self, symbol: str, quantity: float, tp_price: float, sl_stop_price: float, sl_limit_price: Optional[float] = None) -> bool:
        """Attempt to place an OCO sell (TP + SL) on supported exchanges (Binance).
{{ ... }}
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
            order = self._retry(self.ex.create_order, 'create_order', symbol=symbol, type='limit', side='sell', amount=qty, price=tp_p, params=params)
            _ = order  # not used beyond this
            return True
        except Exception:
            return False

    def place_oco_or_fallback(self, symbol: str, quantity: float, tp_price: float, sl_stop_price: float, sl_limit_price: Optional[float] = None) -> Dict[str, Any]:
        """Place OCO; if not supported or fails, fallback to separate stop-limit + limit TP.
        Returns a dict with keys: {'mode': 'oco'|'separate'|'failed', 'tp_ok': bool, 'sl_ok': bool}
        """
        result = {'mode': 'failed', 'tp_ok': False, 'sl_ok': False}
        # Try OCO first
        try:
            ok = self.place_oco_sell(symbol, quantity, tp_price, sl_stop_price, sl_limit_price)
            if ok:
                # Try a light verification: check there are open orders for this symbol on sell side
                try:
                    open_orders = self.ex.fetch_open_orders(symbol=symbol)
                    sells = [o for o in open_orders if str(o.get('side','')).lower()=='sell']
                    if len(sells) >= 2:
                        result.update({'mode': 'oco', 'tp_ok': True, 'sl_ok': True})
                        return result
                except Exception:
                    # If verification not possible, assume success
                    result.update({'mode': 'oco', 'tp_ok': True, 'sl_ok': True})
                    return result
        except Exception:
            pass
        # Fallback to separate legs
        try:
            market = self.markets.get(symbol)
            if market is None:
                return result
            qty = self._conform_amount(market, float(quantity))
            tp_p = self._conform_price(market, float(tp_price))
            sl_stop = self._conform_price(market, float(sl_stop_price))
            sl_lim = self._conform_price(market, float(sl_limit_price if sl_limit_price is not None else sl_stop))
            # Stop-limit leg
            sl_ok = self.place_stop_limit_sell(symbol, qty, sl_stop, sl_lim)
            # TP limit leg
            tp_ok = False
            tp_id = None
            try:
                order_tp = self._retry(self.ex.create_order, 'create_order', symbol=symbol, type='limit', side='sell', amount=qty, price=tp_p)
                tp_id = str(order_tp.get('id')) if order_tp and order_tp.get('id') else None
                tp_ok = True
            except Exception:
                tp_ok = False
            result.update({'mode': 'separate', 'tp_ok': bool(tp_ok), 'sl_ok': bool(sl_ok), 'tp_id': tp_id})
            return result
        except Exception:
            return result
    def place_stop_limit_sell(self, symbol: str, quantity: float, stop_price: float, limit_price: Optional[float] = None) -> bool:
        """Place a standalone stop-limit sell order for protection.
        Returns True if submitted, False otherwise.

        Notes:
        - On Binance via ccxt, use type='limit' with params {'stopPrice', 'timeInForce', 'type': 'STOP_LOSS_LIMIT'}
        - Some exchanges require specific type names; this method targets common ccxt params
        """
        try:
            market = self.markets.get(symbol)
            if market is None:
                return False
            qty = self._conform_amount(market, float(quantity))
            stp = self._conform_price(market, float(stop_price))
            lim = self._conform_price(market, float(limit_price if limit_price is not None else stop_price))
            params: Dict[str, Any] = {}
            ex_id = getattr(self.ex, 'id', '')
            if ex_id == 'binance':
                params = {
                    'type': 'STOP_LOSS_LIMIT',
                    'stopPrice': stp,
                    'timeInForce': 'GTC',
                }
                order = self._retry(self.ex.create_order, 'create_order', symbol=symbol, type='limit', side='sell', amount=qty, price=lim, params=params)
                _ = order
                return True
            else:
                # Generic attempt: some exchanges accept stop params similarly
                params = {
                    'stopPrice': stp,
                    'timeInForce': 'GTC',
                }
                order = self._retry(self.ex.create_order, 'create_order', symbol=symbol, type='limit', side='sell', amount=qty, price=lim, params=params)
                _ = order
                return True
        except Exception:
            return False

    # Retry helpers for tracker
    def fetch_open_orders_retry(self, symbol: str):
        return self._retry(self.ex.fetch_open_orders, 'fetch_open_orders', symbol=symbol)

    def create_limit_sell_retry(self, symbol: str, amount: float, price: float):
        return self._retry(self.ex.create_order, 'create_order', symbol=symbol, type='limit', side='sell', amount=amount, price=price)

    def cancel_open_sell_orders(self, symbol: str) -> int:
        """Cancel all open sell orders for a symbol. Returns number canceled."""
        try:
            orders = self._retry(self.ex.fetch_open_orders, 'fetch_open_orders', symbol=symbol)
        except Exception:
            orders = []
        canceled = 0
        for o in (orders or []):
            try:
                if str(o.get('side','')).lower() != 'sell':
                    continue
                oid = o.get('id')
                if oid is None:
                    continue
                try:
                    self._retry(self.ex.cancel_order, 'cancel_order', oid, symbol)
                    canceled += 1
                except Exception:
                    continue
            except Exception:
                continue
        return canceled

    def cancel_order_retry(self, order_id: str, symbol: str) -> None:
        self._retry(self.ex.cancel_order, 'cancel_order', order_id, symbol)

    def get_failure_counts(self, window_sec: int = 60) -> Dict[str, int]:
        import time
        now = time.time()
        out: Dict[str, int] = {}
        for ep, times in self._fail_ts.items():
            out[ep] = len([t for t in times if now - t <= window_sec])
        return out
