from __future__ import annotations

import argparse
import csv
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from src.data.ccxt_ohlcv import get_candles_ccxt

# Reuse existing modules
from src.data.ohlcv import get_candles
from src.decision import compute_confidence, recommend_action
from src.indicators.core import atr as atr_series
from src.indicators.core import ema as ema_series
from src.indicators.core import rsi as rsi_series
from src.risk import ATRRiskParams, compute_stop_levels, compute_stop_levels_atr


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


def _log_fallback(
    coin_id: str, timeframe: str, ex: Exception, provider: str, stage: str = "fetch"
) -> None:
    msg = (
        f"[backtest] {coin_id}: {stage} '{timeframe}' via {provider} failed ({ex}). "
        f"Falling back to 1d."
    )
    print(msg)


def simulate_on_series(
    coin_id: str,
    threshold: float,
    closes: List[float],
    highs: List[float],
    lows: List[float],
    rsi_period: int,
    ema_fast: int,
    ema_slow: int,
    atr_params: Optional[ATRRiskParams],
    slippage_base_bps: int,
    slippage_k_atr_pct: float,
    fee_bps: int,
    times: Optional[List[int]] = None,
    export_dir: Optional[Path] = None,
    use_regime_filter: bool = False,
    vol_gate_min_atr_pct: Optional[float] = None,
    vol_gate_max_atr_pct: Optional[float] = None,
    risk_budget_pct: Optional[float] = None,
    auto_threshold: float = 0.8,
    auto_threshold_bear: Optional[float] = None,
) -> BacktestResult:
    # Indicators
    if times is None:
        times = list(range(len(closes)))
    if len(closes) < max(rsi_period + 1, ema_slow + 1, 50):
        return BacktestResult([], [], 0.0, 0.0, 0.0)
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

    def apply_costs(price: float, side: str, atr_pct: float) -> float:
        # Dynamic slippage: base_bps + k * ATR%
        slip_dynamic = float(slippage_base_bps)
        try:
            slip_dynamic += float(slippage_k_atr_pct) * float(atr_pct)
        except Exception:
            pass
        # Cap slippage to a reasonable range [0, 100] bps
        slip_dynamic = max(0.0, min(100.0, slip_dynamic))
        total_bps = slip_dynamic + float(fee_bps)
        mult = (1.0 + total_bps / 10000.0) if side == "buy" else (1.0 - total_bps / 10000.0)
        return price * mult

    for i in range(len(closes)):
        price = float(closes[i])
        equity_val = cash + (pos_qty * price)
        equity.append(equity_val)

        rsi = rsi_vals[i] if i < len(rsi_vals) else None
        ef = ema_fast_vals[i] if i < len(ema_fast_vals) else None
        es = ema_slow_vals[i] if i < len(ema_slow_vals) else None
        atr = atr_vals[i] if i < len(atr_vals) else None

        ma_short = ef if ef is not None else es
        ma_long = es
        conf = compute_confidence(price, threshold, rsi, ma_short, ma_long)
        signal, action_rec, _ = recommend_action(
            price, threshold, rsi, conf, suggestion_threshold=0.5
        )

        if action_rec == "Buy" and pos_qty == 0.0:
            # Regime filter gating
            if use_regime_filter and ef is not None and es is not None and ef <= es:
                # still compute regime-aware threshold check below — but if regime filter is ON and strictly forbids, skip
                pass  # skip entry
            else:
                # Volatility gating
                atr_ok = True
                if (
                    (vol_gate_min_atr_pct is not None or vol_gate_max_atr_pct is not None)
                    and atr is not None
                    and price > 0
                ):
                    atr_pct = (atr / price) * 100.0
                    if (
                        vol_gate_min_atr_pct is not None and atr_pct < float(vol_gate_min_atr_pct)
                    ) or (
                        vol_gate_max_atr_pct is not None and atr_pct > float(vol_gate_max_atr_pct)
                    ):
                        atr_ok = False
                if not atr_ok:
                    pass
                else:
                    # Confidence auto-threshold: bear uses stricter if provided
                    is_bear = bool(
                        use_regime_filter and ef is not None and es is not None and ef <= es
                    )
                    thr = float(
                        auto_threshold_bear
                        if (is_bear and auto_threshold_bear is not None)
                        else auto_threshold
                    )
                    if conf < thr:
                        # Not enough confidence to auto-enter
                        continue
                    # ATR-based sizing if configured; else fallback to 10% of cash
                    size_usd = cash * 0.1
                    if risk_budget_pct is not None and risk_budget_pct > 0:
                        equity_val_now = cash + (pos_qty * price)
                        budget_usd = max(0.0, equity_val_now * float(risk_budget_pct))
                        if atr_params is not None and atr is not None and atr > 0:
                            sl_price, _tp_price = compute_stop_levels_atr(price, atr, atr_params)
                            if sl_price is not None and price > sl_price:
                                risk_per_unit = price - sl_price
                                if risk_per_unit > 0:
                                    units = budget_usd / risk_per_unit
                                    size_usd = min(budget_usd, price * units)
                        size_usd = min(size_usd, cash)
                    if size_usd > 0:
                        atr_pct_now = (
                            (atr / price * 100.0) if (atr is not None and price > 0) else 0.0
                        )
                        fill_price = apply_costs(price, "buy", atr_pct_now)
                        qty = size_usd / fill_price
                        if qty > 0:
                            pos_qty = qty
                            pos_entry_price = fill_price
                            pos_entry_idx = i
                            peak_price_since_entry = price
                            trades.append(Trade(entry_idx=i, entry_price=fill_price))
                            cash -= size_usd
                            continue

        if pos_qty > 0.0 and pos_entry_price is not None and pos_entry_idx is not None:
            peak_price_since_entry = max(peak_price_since_entry or price, price)
            if atr_params and atr:
                sl, tp = compute_stop_levels_atr(pos_entry_price, atr, atr_params)
                if sl is None or tp is None:
                    sl, tp = pos_entry_price * 0.97, pos_entry_price * 1.06
            else:
                sl, tp = pos_entry_price * 0.97, pos_entry_price * 1.06
            trail_hit = False
            if atr_params and atr and peak_price_since_entry is not None:
                trail_level = peak_price_since_entry - atr_params.trail_mult * atr
                trail_hit = price <= trail_level
            stop_hit = price <= sl
            tp_hit = price >= tp
            if stop_hit or tp_hit:
                atr_pct_now2 = (atr / price * 100.0) if (atr is not None and price > 0) else 0.0
                fill_price = apply_costs(price, "sell", atr_pct_now2)
                cash += pos_qty * fill_price
                trades[-1].exit_idx = i
                trades[-1].exit_price = fill_price
                trades[-1].reason = "stop" if stop_hit else "tp"
                pos_qty = 0.0
                pos_entry_price = None
                pos_entry_idx = None
                peak_price_since_entry = None
                continue
            if trail_hit:
                atr_pct_now3 = (atr / price * 100.0) if (atr is not None and price > 0) else 0.0
                fill_price = apply_costs(price, "sell", atr_pct_now3)
                cash += pos_qty * fill_price
                trades[-1].exit_idx = i
                trades[-1].exit_price = fill_price
                trades[-1].reason = "trail"
                pos_qty = 0.0
                pos_entry_price = None
                pos_entry_idx = None
                peak_price_since_entry = None
                continue

    wins = [t for t in trades if (t.pnl_pct() or 0) > 0]
    losses = [t for t in trades if (t.pnl_pct() or 0) <= 0]
    win_rate = (len(wins) / len(trades) * 100.0) if trades else 0.0
    gross_profit = sum(((t.pnl_pct() or 0) for t in wins))
    gross_loss = -sum(((t.pnl_pct() or 0) for t in losses))
    profit_factor = (
        (gross_profit / gross_loss)
        if gross_loss > 0
        else (gross_profit if gross_profit > 0 else 0.0)
    )
    max_dd = 0.0
    peak = equity[0] if equity else 0.0
    for v in equity:
        if v > peak:
            peak = v
        dd = (peak - v) / peak * 100.0 if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd

    # Optional export
    if export_dir is not None:
        export_dir.mkdir(parents=True, exist_ok=True)
        trades_path = export_dir / f"{coin_id}_trades.csv"
        with trades_path.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(
                [
                    "entry_idx",
                    "entry_time",
                    "entry_price",
                    "exit_idx",
                    "exit_time",
                    "exit_price",
                    "reason",
                    "pnl_pct",
                ]
            )
            for t in trades:
                e_t = (
                    times[t.entry_idx]
                    if t.entry_idx is not None and t.entry_idx < len(times)
                    else t.entry_idx
                )
                x_t = (
                    times[t.exit_idx]
                    if t.exit_idx is not None and t.exit_idx < len(times)
                    else t.exit_idx
                )
                w.writerow(
                    [
                        t.entry_idx,
                        e_t,
                        f"{t.entry_price:.6f}",
                        t.exit_idx,
                        x_t,
                        (f"{t.exit_price:.6f}" if t.exit_price is not None else ""),
                        t.reason,
                        (f"{t.pnl_pct():.4f}" if t.pnl_pct() is not None else ""),
                    ]
                )
    return BacktestResult(
        trades=trades,
        equity=equity,
        win_rate=win_rate,
        profit_factor=profit_factor,
        max_drawdown=max_dd,
    )


def simulate_coin(
    coin_id: str,
    cg_id: str,
    threshold: float,
    days: int,
    timeframe: str,
    rsi_period: int,
    ema_fast: int,
    ema_slow: int,
    atr_params: Optional[ATRRiskParams],
    slippage_bps: int,
    fee_bps: int,
    export_dir: Optional[Path] = None,
) -> BacktestResult:
    # Fetch candles via provider
    project_root = Path(__file__).resolve().parents[2]
    config_path = project_root / "config" / "config.yaml"
    with open(config_path, "r") as f:
        cfg_all = yaml.safe_load(f) or {}
    data_cfg = cfg_all.get("data") or {}
    provider = str(data_cfg.get("provider", "coingecko")).lower()
    # Backtest parity options from config
    ind_cfg = cfg_all.get("indicators") or {}
    rsi_period = int(ind_cfg.get("rsi_period", rsi_period))
    ema_fast = int(ind_cfg.get("ema_fast", ema_fast))
    ema_slow = int(ind_cfg.get("ema_slow", ema_slow))
    # Strategy toggles
    strat = cfg_all.get("strategy") or {}
    use_regime_filter = bool(strat.get("use_regime_filter", False))
    vg = strat.get("vol_gate") or {}
    vol_gate_min_atr_pct = vg.get("min_atr_pct")
    vol_gate_max_atr_pct = vg.get("max_atr_pct")
    try:
        vol_gate_min_atr_pct = (
            float(vol_gate_min_atr_pct) if vol_gate_min_atr_pct is not None else None
        )
    except Exception:
        vol_gate_min_atr_pct = None
    try:
        vol_gate_max_atr_pct = (
            float(vol_gate_max_atr_pct) if vol_gate_max_atr_pct is not None else None
        )
    except Exception:
        vol_gate_max_atr_pct = None
    # Decision thresholds
    decision = cfg_all.get("decision") or {}
    thresholds = decision.get("confidence_thresholds") or {}
    try:
        auto_thr = float(thresholds.get("auto", 0.8))
    except Exception:
        auto_thr = 0.8
    try:
        auto_thr_bear = thresholds.get("auto_bear")
        auto_thr_bear = float(auto_thr_bear) if auto_thr_bear is not None else None
    except Exception:
        auto_thr_bear = None
    # Execution sizing and fee/slippage parity
    exe_cfg = cfg_all.get("execution") or {}
    try:
        risk_budget_pct = float(exe_cfg.get("risk_budget_pct", 0.0))
    except Exception:
        risk_budget_pct = 0.0
    # Fee tiers -> choose fee_bps if tiers defined
    try:
        tiers = exe_cfg.get("fee_tiers") or []
        fee_tier_volume_usd = float(exe_cfg.get("fee_tier_volume_usd", 0.0))
        best = None
        if isinstance(tiers, list):
            for t in tiers:
                try:
                    v = float(t.get("volume_usd", 0.0))
                    if v <= fee_tier_volume_usd:
                        if best is None or v > float(best.get("volume_usd", -1e9)):
                            best = t
                except Exception:
                    continue
        if best is not None:
            tb = best.get("taker_bps", best.get("maker_bps", None))
            if tb is not None:
                fee_bps = int(float(tb))
    except Exception:
        pass
    # Slippage model
    slip_cfg = exe_cfg.get("slippage") or {}
    slippage_base_bps = int(slip_cfg.get("base_bps", slippage_bps))
    slippage_k_atr_pct = float(slip_cfg.get("k_atr_pct", 0.0))
    api_key = os.environ.get("COINGECKO_API_KEY")
    try:
        if provider == "ccxt":
            providers_cfg = cfg_all.get("providers") or {}
            exchange_name = str(providers_cfg.get("exchange", "binance")).lower()
            tracked = cfg_all.get("tracked_coins") or {}
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
            candles = get_candles_ccxt(
                exchange_name,
                market,
                timeframe=timeframe,
                cache_dir="./data_cache",
                limit=limit,
                use_cache=True,
            )
        else:
            candles = get_candles(
                cg_id,
                timeframe=timeframe,
                days=days,
                cache_dir="./data_cache",
                use_cache=True,
                api_key=api_key,
            )
    except Exception as ex:
        if timeframe != "1d":
            _log_fallback(coin_id, timeframe, ex, provider, stage="fetch")
            if provider == "ccxt":
                # fallback to ccxt daily if supported, else coingecko daily
                exchange_name = str(providers_cfg.get("exchange", "binance")).lower()
                tracked = cfg_all.get("tracked_coins") or {}
                per_coin = tracked.get(coin_id) or {}
                market = per_coin.get("market") or f"{per_coin.get('symbol', coin_id).upper()}/USDT"
                try:
                    candles = get_candles_ccxt(
                        exchange_name,
                        market,
                        timeframe="1d",
                        cache_dir="./data_cache",
                        limit=min(int(days), 2000),
                        use_cache=True,
                    )
                except Exception as ex2:
                    _log_fallback(coin_id, "1d", ex2, "ccxt", stage="fetch-ccxt-daily")
                    candles = get_candles(
                        cg_id,
                        timeframe="1d",
                        days=min(days, 365),
                        cache_dir="./data_cache",
                        use_cache=True,
                        api_key=api_key,
                    )
            else:
                # If provider is not ccxt and timeframe is not 1d, fallback to coingecko daily
                candles = get_candles(
                    cg_id,
                    timeframe="1d",
                    days=min(days, 365),
                    cache_dir="./data_cache",
                    use_cache=True,
                    api_key=api_key,
                )
        else:
            raise
    # Build series arrays from fetched candles
    closes = [c.c for c in candles]
    highs = [c.h for c in candles]
    lows = [c.l for c in candles]
    # Optional timestamps if available on candle object
    times = [getattr(c, "ts", i) for i, c in enumerate(candles)]

    # Delegate to series-based simulation to avoid duplicated logic
    return simulate_on_series(
        coin_id=coin_id,
        threshold=threshold,
        closes=closes,
        highs=highs,
        lows=lows,
        rsi_period=rsi_period,
        ema_fast=ema_fast,
        ema_slow=ema_slow,
        atr_params=atr_params,
        slippage_base_bps=slippage_base_bps,
        slippage_k_atr_pct=slippage_k_atr_pct,
        fee_bps=fee_bps,
        times=times,
        export_dir=export_dir,
        use_regime_filter=use_regime_filter,
        vol_gate_min_atr_pct=vol_gate_min_atr_pct,
        vol_gate_max_atr_pct=vol_gate_max_atr_pct,
        risk_budget_pct=risk_budget_pct,
        auto_threshold=auto_thr,
        auto_threshold_bear=auto_thr_bear,
    )


def main():
    # Always read settings from config/config.yaml
    project_root = Path(__file__).resolve().parents[2]
    config_path = project_root / "config" / "config.yaml"
    with open(config_path, "r") as f:
        cfg_all = yaml.safe_load(f) or {}
    data_cfg = cfg_all.get("data") or {}
    timeframe = str(data_cfg.get("timeframe", "1d"))
    days = int(data_cfg.get("days", 365))
    ind_cfg = cfg_all.get("indicators") or {}
    rsi_period = int(ind_cfg.get("rsi_period", 14))
    ema_fast = int(ind_cfg.get("ema_fast", 20))
    ema_slow = int(ind_cfg.get("ema_slow", 50))
    risk_cfg2 = cfg_all.get("risk") or {}
    atr_cfg = risk_cfg2.get("atr") or {}
    try:
        atr_params = ATRRiskParams(
            atr_period=int(atr_cfg.get("period", 14)),
            sl_mult=float(atr_cfg.get("sl_mult", 1.5)),
            tp_mult=float(atr_cfg.get("tp_mult", 3.0)),
            trail_mult=float(atr_cfg.get("trail_mult", 2.0)),
        )
    except Exception:
        atr_params = None
    slippage_bps = 10
    fee_bps = 5
    tracked = cfg_all.get("tracked_coins") or {}
    coin_ids = [cid for cid, c in tracked.items() if not (c or {}).get("disabled", False)]
    # Optional CoinGecko id mapping
    results: Dict[str, BacktestResult] = {}
    for cid in coin_ids:
        cg_id = (tracked.get(cid) or {}).get("coingecko_id", cid)
        threshold = float((tracked.get(cid) or {}).get("threshold", 0.0))
        res = simulate_coin(
            coin_id=cid,
            cg_id=cg_id,
            threshold=threshold,
            days=days,
            timeframe=timeframe,
            rsi_period=rsi_period,
            ema_fast=ema_fast,
            ema_slow=ema_slow,
            atr_params=atr_params,
            slippage_bps=slippage_bps,
            fee_bps=fee_bps,
            export_dir=None,
        )
        results[cid] = res
    # Print a simple summary
    print("Backtest summary (config-driven):")
    for cid, r in results.items():
        print(
            f" - {cid}: trades={len(r.trades)}, win_rate={r.win_rate:.2f}%, PF={r.profit_factor:.3f}, maxDD={r.max_drawdown:.2f}%"
        )

    # Load config for coin ids, thresholds and CG ids
    project_root = Path(__file__).resolve().parents[2]
    config_path = project_root / "config" / "config.yaml"
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f) or {}
    all_tracked = cfg.get("tracked_coins") or {}

    target_ids = list(all_tracked.keys())

    # Indicator/risk defaults
    ind_cfg = cfg.get("indicators") or {}
    rsi_p = int(ind_cfg.get("rsi_period", 14))
    ema_fast = int(ind_cfg.get("ema_fast", 20))
    ema_slow = int(ind_cfg.get("ema_slow", 50))
    risk_cfg = cfg.get("risk") or {}
    atr_cfg = risk_cfg.get("atr") or {}
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
            days=days,
            timeframe=timeframe,
            rsi_period=rsi_p,
            ema_fast=ema_fast,
            ema_slow=ema_slow,
            atr_params=atr_params,
            slippage_bps=slippage_bps,
            fee_bps=fee_bps,
            export_dir=export_dir,
        )
        summary[coin_id] = res

    # Print summary
    for coin_id, res in summary.items():
        print(f"\n=== {coin_id} ===")
        print(
            f"Trades: {len(res.trades)} | Win%: {res.win_rate:.1f}% | PF: {res.profit_factor:.2f} | MaxDD: {res.max_drawdown:.1f}%"
        )

    # Simple exit code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
