from __future__ import annotations
import argparse
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import csv

from pathlib import Path
import os
import yaml

# Reuse existing modules
from ..data.ohlcv import get_candles
from ..data.ccxt_ohlcv import get_candles_ccxt
from ..indicators.core import rsi as rsi_series, ema as ema_series, atr as atr_series
from ..decision import compute_confidence, recommend_action
from ..risk import ATRRiskParams, compute_stop_levels_atr, compute_stop_levels


@dataclass
class Trade:
    entry_idx: int
    entry_price: float
    exit_idx: Optional[int] = None
    exit_price: Optional[float] = None
    reason: str = ""

    def pnl_pct(self) -> Optional[float]:
        if self.exit_price is None or self.entry_price == 0:
            return None
        return (self.exit_price / self.entry_price - 1.0) * 100.0


@dataclass
class BacktestResult:
    trades: List[Trade]
    equity: List[float]
    win_rate: float
    profit_factor: float
    max_drawdown: float


def simulate_coin(coin_id: str, cg_id: str, threshold: float, days: int, timeframe: str,
                  rsi_period: int, ema_fast: int, ema_slow: int,
                  atr_params: Optional[ATRRiskParams], slippage_bps: int, fee_bps: int,
                  export_dir: Optional[Path] = None) -> BacktestResult:
    # Fetch candles via provider
    project_root = Path(__file__).resolve().parents[2]
    config_path = project_root / "config" / "config.yaml"
    with open(config_path, "r") as f:
        cfg_all = yaml.safe_load(f) or {}
    data_cfg = (cfg_all.get("data") or {})
    provider = str(data_cfg.get("provider", "coingecko")).lower()
    api_key = os.environ.get("COINGECKO_API_KEY")
    try:
        if provider == "ccxt":
            providers_cfg = (cfg_all.get("providers") or {})
            exchange_name = str(providers_cfg.get("exchange", "binance")).lower()
            tracked = (cfg_all.get("tracked_coins") or {})
            per_coin = tracked.get(coin_id) or {}
            market = per_coin.get("market") or f"{per_coin.get('symbol', coin_id).upper()}/USDT"
            # map limit from days + timeframe
            if timeframe == "1d":
                limit = min(int(days), 2000)
            elif timeframe == "4h":
                limit = min(int(days) * 6, 2000)
            elif timeframe == "1h":
                limit = min(int(days) * 24, 2000)
            else:
                limit = 1000
            candles = get_candles_ccxt(exchange_name, market, timeframe=timeframe, cache_dir="./data_cache", limit=limit, use_cache=True)
        else:
            candles = get_candles(cg_id, timeframe=timeframe, days=days, cache_dir="./data_cache", use_cache=True, api_key=api_key)
    except Exception as ex:
        if timeframe != "1d":
            print(f"[backtest] {coin_id}: '{timeframe}' fetch failed ({ex}). Falling back to 1d.")
            if provider == "ccxt":
                # fallback to ccxt daily if supported, else coingecko daily
                try:
                    providers_cfg = (cfg_all.get("providers") or {})
                    exchange_name = str(providers_cfg.get("exchange", "binance")).lower()
                    tracked = (cfg_all.get("tracked_coins") or {})
                    per_coin = tracked.get(coin_id) or {}
                    market = per_coin.get("market") or f"{per_coin.get('symbol', coin_id).upper()}/USDT"
                    candles = get_candles_ccxt(exchange_name, market, timeframe="1d", cache_dir="./data_cache", limit=min(int(days), 2000), use_cache=True)
                except Exception:
                    candles = get_candles(cg_id, timeframe="1d", days=min(days, 365), cache_dir="./data_cache", use_cache=True, api_key=api_key)
            else:
                candles = get_candles(cg_id, timeframe="1d", days=min(days, 365), cache_dir="./data_cache", use_cache=True, api_key=api_key)
        else:
            raise
    closes = [c.c for c in candles]
    highs = [c.h for c in candles]
    lows = [c.l for c in candles]
    # Optional timestamps if available on candle object
    times = [getattr(c, 'ts', i) for i, c in enumerate(candles)]
    if len(closes) < max(rsi_period + 1, ema_slow + 1, 50):
        return BacktestResult([], [], 0.0, 0.0, 0.0)

    # Indicators
    rsi_vals = rsi_series(closes, rsi_period)
    ema_fast_vals = ema_series(closes, ema_fast)
    ema_slow_vals = ema_series(closes, ema_slow)
    atr_vals = atr_series(highs, lows, closes, atr_params.atr_period if atr_params else 14)

    trades: List[Trade] = []
    equity: List[float] = []
    cash = 10000.0
    pos_qty = 0.0
    pos_entry_idx: Optional[int] = None
    pos_entry_price: Optional[float] = None
    peak_price_since_entry: Optional[float] = None

    def apply_costs(price: float, side: str) -> float:
        # slippage + fee approximated as bps
        mult = 1.0
        mult *= (1.0 + (slippage_bps + fee_bps) / 10000.0) if side == "buy" else (1.0 - (slippage_bps + fee_bps) / 10000.0)
        return price * mult

    for i in range(len(closes)):
        price = float(closes[i])
        # Equity calculation
        equity_val = cash + (pos_qty * price)
        equity.append(equity_val)

        # indicators
        rsi = rsi_vals[i] if i < len(rsi_vals) else None
        ef = ema_fast_vals[i] if i < len(ema_fast_vals) else None
        es = ema_slow_vals[i] if i < len(ema_slow_vals) else None
        atr = atr_vals[i] if i < len(atr_vals) else None

        # Decision (use same recommend_action and confidence mapping)
        ma_short = ef if ef is not None else es
        ma_long = es
        conf = compute_confidence(price, threshold, rsi, ma_short, ma_long)
        signal, action_rec, _ = recommend_action(price, threshold, rsi, conf, suggestion_threshold=0.5)

        # Entry logic: Buy when recommended and not in position
        if action_rec == "Buy" and pos_qty == 0.0:
            # allocate fixed 10% of cash
            size_usd = cash * 0.1
            if size_usd > 0:
                fill_price = apply_costs(price, "buy")
                qty = size_usd / fill_price
                pos_qty = qty
                pos_entry_price = fill_price
                pos_entry_idx = i
                peak_price_since_entry = price
                trades.append(Trade(entry_idx=i, entry_price=fill_price))
                cash -= size_usd
                continue

        # If in position, update peak and check exits
        if pos_qty > 0.0 and pos_entry_price is not None and pos_entry_idx is not None:
            peak_price_since_entry = max(peak_price_since_entry or price, price)
            # Prefer ATR exits if available
            if atr_params and atr:
                sl, tp = compute_stop_levels_atr(pos_entry_price, atr, atr_params)
                # If ATR missing/unusable, fall back to percent-based stops
                if sl is None or tp is None:
                    sl, tp = pos_entry_price * 0.97, pos_entry_price * 1.06
            else:
                # percent fallback from globals (reuse decision thresholds as proxy)
                sl, tp = pos_entry_price * 0.97, pos_entry_price * 1.06
            # ATR trailing if configured
            trail_hit = False
            if atr_params and atr and peak_price_since_entry is not None:
                trail_level = peak_price_since_entry - atr_params.trail_mult * atr
                trail_hit = price <= trail_level

            stop_hit = price <= sl
            tp_hit = price >= tp
            if stop_hit or tp_hit:
                fill_price = apply_costs(price, "sell")
                cash += pos_qty * fill_price
                trades[-1].exit_idx = i
                trades[-1].exit_price = fill_price
                trades[-1].reason = "stop" if stop_hit else "tp"
                pos_qty = 0.0
                pos_entry_price = None
                pos_entry_idx = None
                peak_price_since_entry = None
                continue
            # Trailing exit after SL/TP check to let TP take precedence
            if trail_hit:
                fill_price = apply_costs(price, "sell")
                cash += pos_qty * fill_price
                trades[-1].exit_idx = i
                trades[-1].exit_price = fill_price
                trades[-1].reason = "trail"
                pos_qty = 0.0
                pos_entry_price = None
                pos_entry_idx = None
                peak_price_since_entry = None
                continue

    # Metrics
    wins = [t for t in trades if (t.pnl_pct() or 0) > 0]
    losses = [t for t in trades if (t.pnl_pct() or 0) <= 0]
    win_rate = (len(wins) / len(trades) * 100.0) if trades else 0.0
    gross_profit = sum(((t.pnl_pct() or 0) for t in wins))
    gross_loss = -sum(((t.pnl_pct() or 0) for t in losses))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0.0)
    # max drawdown
    max_dd = 0.0
    peak = equity[0] if equity else 0.0
    for v in equity:
        if v > peak:
            peak = v
        dd = (peak - v) / peak * 100.0 if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd

    # CSV export if requested
    if export_dir is not None:
        export_dir.mkdir(parents=True, exist_ok=True)
        # Trades CSV
        trades_path = export_dir / f"{coin_id}_trades.csv"
        with trades_path.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["entry_idx", "entry_time", "entry_price", "exit_idx", "exit_time", "exit_price", "reason", "pnl_pct"])
            for t in trades:
                e_t = times[t.entry_idx] if t.entry_idx is not None and t.entry_idx < len(times) else t.entry_idx
                x_t = times[t.exit_idx] if t.exit_idx is not None and t.exit_idx < len(times) else t.exit_idx
                w.writerow([t.entry_idx, e_t, f"{t.entry_price:.6f}", t.exit_idx, x_t,
                           (f"{t.exit_price:.6f}" if t.exit_price is not None else ""), t.reason,
                           (f"{t.pnl_pct():.4f}" if t.pnl_pct() is not None else "")])
        # Equity CSV
        equity_path = export_dir / f"{coin_id}_equity.csv"
        with equity_path.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["idx", "time", "equity"])
            for idx, ev in enumerate(equity):
                t = times[idx] if idx < len(times) else idx
                w.writerow([idx, t, f"{ev:.6f}"])

    return BacktestResult(trades=trades, equity=equity, win_rate=win_rate, profit_factor=profit_factor, max_drawdown=max_dd)


def main():
    parser = argparse.ArgumentParser(description="Backtest engine")
    parser.add_argument("--coins", type=str, required=False, default="",
                        help="Comma-separated coin ids from config.tracked_coins (e.g., solana,polkadot)")
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--timeframe", type=str, default="1d")
    parser.add_argument("--slippage_bps", type=int, default=10)
    parser.add_argument("--fee_bps", type=int, default=5)
    args = parser.parse_args()

    # Load config for coin ids, thresholds and CG ids
    project_root = Path(__file__).resolve().parents[2]
    config_path = project_root / "config" / "config.yaml"
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f) or {}
    all_tracked = cfg.get("tracked_coins") or {}

    target_ids = [c.strip() for c in args.coins.split(",") if c.strip()] if args.coins else list(all_tracked.keys())

    # Indicator/risk defaults
    ind_cfg = (cfg.get("indicators") or {})
    rsi_p = int(ind_cfg.get("rsi_period", 14))
    ema_fast = int(ind_cfg.get("ema_fast", 20))
    ema_slow = int(ind_cfg.get("ema_slow", 50))
    risk_cfg = (cfg.get("risk") or {})
    atr_cfg = (risk_cfg.get("atr") or {})
    atr_params = None
    if atr_cfg:
        try:
            atr_params = ATRRiskParams(
                atr_period=int(atr_cfg.get("period", 14)),
                sl_mult=float(atr_cfg.get("sl_mult", 1.5)),
                tp_mult=float(atr_cfg.get("tp_mult", 3.0)),
                trail_mult=float(atr_cfg.get("trail_mult", 2.0)),
            )
        except Exception:
            atr_params = None

    summary: Dict[str, BacktestResult] = {}
    export_dir = Path(__file__).resolve().parents[2] / "logs" / "backtest"

    for coin_id in target_ids:
        data = all_tracked.get(coin_id) or {}
        threshold = float(data.get("threshold", 0.0))
        cg_id = str(data.get("coingecko_id", coin_id))
        res = simulate_coin(
            coin_id=coin_id,
            cg_id=cg_id,
            threshold=threshold,
            days=args.days,
            timeframe=args.timeframe,
            rsi_period=rsi_p,
            ema_fast=ema_fast,
            ema_slow=ema_slow,
            atr_params=atr_params,
            slippage_bps=args.slippage_bps,
            fee_bps=args.fee_bps,
            export_dir=export_dir,
        )
        summary[coin_id] = res

    # Print summary
    for coin_id, res in summary.items():
        print(f"\n=== {coin_id} ===")
        print(f"Trades: {len(res.trades)} | Win%: {res.win_rate:.1f}% | PF: {res.profit_factor:.2f} | MaxDD: {res.max_drawdown:.1f}%")

    # Simple exit code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
