from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from ..data.ccxt_ohlcv import get_candles_ccxt
from ..data.ohlcv import get_candles
from ..notifier import Notifier
from .engine import ATRRiskParams, simulate_on_series


@dataclass
class EvalResult:
    params: Dict[str, float]
    trades: int
    win_rate: float
    profit_factor: float
    max_drawdown: float
    cagr: float
    mar: float
    avg_return_pct: float


def _read_config() -> Dict:
    project_root = Path(__file__).resolve().parents[2]
    with open(project_root / "config" / "config.yaml", "r") as f:
        return yaml.safe_load(f) or {}


def _fetch_series(
    cfg_all: Dict, coin_id: str, timeframe: str, days: int
) -> Optional[Tuple[List[float], List[float], List[float], List[int]]]:
    try:
        data_cfg = cfg_all.get("data") or {}
        provider = str(data_cfg.get("provider", "coingecko")).lower()
        api_key = os.environ.get("COINGECKO_API_KEY")
        tracked = cfg_all.get("tracked_coins") or {}
        per = tracked.get(coin_id, {})
        cg_id = per.get("coingecko_id", coin_id)
        if provider == "ccxt":
            providers_cfg = cfg_all.get("providers") or {}
            exchange_name = str(providers_cfg.get("exchange", "binance")).lower()
            market = per.get("market") or f"{per.get('symbol', coin_id).upper()}/USDT"
            # Avoid invalid self-quoted markets (e.g., USDT/USDT) by falling back to CoinGecko
            try:
                base, quote = market.split("/")
            except ValueError:
                base, quote = market, "USDT"
            if base.upper() == quote.upper():
                provider = "coingecko"
        if timeframe == "1d":
            limit = min(int(days), 2000)
        elif timeframe == "4h":
            limit = min(int(days) * 6, 2000)
        elif timeframe == "1h":
            limit = min(int(days) * 24, 2000)
        else:
            limit = 1000
        if provider == "ccxt":
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
        closes = [c.c for c in candles]
        highs = [c.h for c in candles]
        lows = [c.l for c in candles]
        times = [getattr(c, "ts", i) for i, c in enumerate(candles)]
        return closes, highs, lows, times
    except Exception as ex:
        print(f"  Data fetch failed for {coin_id}: {ex} (skipping).")
        return None


def _walk_forward_splits(n: int, folds: int = 3) -> List[Tuple[int, int, int, int]]:
    # Return list of (train_start, train_end, test_start, test_end) indices, sequentially
    if folds < 2:
        folds = 2
    seg = n // folds
    out = []
    for i in range(folds - 1):
        tr_start = i * seg
        tr_end = (i + 1) * seg
        te_start = tr_end
        te_end = min(n, te_start + seg)
        if te_end - te_start >= max(60, seg // 4):  # ensure enough bars
            out.append((tr_start, tr_end, te_start, te_end))
    return out


def _eval_params(
    closes,
    highs,
    lows,
    times,
    cfg_all: Dict,
    coin_id: str,
    params: Dict[str, float],
    timeframe: str,
    use_price_as_threshold: bool = False,
    disable_regime_filter: bool = False,
    disable_vol_gate: bool = False,
) -> EvalResult:
    ind_cfg = cfg_all.get("indicators") or {}
    ema_fast = int(params.get("ema_fast", ind_cfg.get("ema_fast", 20)))
    ema_slow = int(params.get("ema_slow", ind_cfg.get("ema_slow", 50)))
    rsi_p = int(params.get("rsi", ind_cfg.get("rsi_period", 14)))
    # Strategy
    strat = cfg_all.get("strategy") or {}
    use_regime_filter = bool(strat.get("use_regime_filter", False))
    if disable_regime_filter:
        use_regime_filter = False
    vg = strat.get("vol_gate") or {}
    vol_min = float(vg.get("min_atr_pct", 0.0)) if vg.get("min_atr_pct") is not None else None
    vol_max = float(vg.get("max_atr_pct", 0.0)) if vg.get("max_atr_pct") is not None else None
    if disable_vol_gate:
        vol_min = None
        vol_max = None
    # Decision
    decision = cfg_all.get("decision") or {}
    thr = decision.get("confidence_thresholds") or {}
    auto_thr = float(thr.get("auto", 0.8))
    auto_thr_bear = thr.get("auto_bear")
    auto_thr_bear = float(auto_thr_bear) if auto_thr_bear is not None else None
    # ATR params
    risk_cfg2 = cfg_all.get("risk") or {}
    atr_cfg = risk_cfg2.get("atr") or {}
    atr_params = ATRRiskParams(
        atr_period=int(atr_cfg.get("period", 14)),
        sl_mult=float(params.get("sl_mult", atr_cfg.get("sl_mult", 1.5))),
        tp_mult=float(params.get("tp_mult", atr_cfg.get("tp_mult", 3.0))),
        trail_mult=float(atr_cfg.get("trail_mult", 2.0)),
    )
    # Risk budget
    risk_budget_pct = float(params.get("risk_budget_pct", 0.0))
    # Evaluate on full segment (caller should slice series)
    # Threshold selection
    if use_price_as_threshold:
        # Surrogate threshold: median of closes in this slice
        try:
            threshold_val = float(sorted(closes)[len(closes) // 2]) if closes else 0.0
        except Exception:
            threshold_val = 0.0
    else:
        tracked = cfg_all.get("tracked_coins") or {}
        threshold_val = float((tracked.get(coin_id) or {}).get("threshold", 0.0))
    # Fee/slippage parity
    exe_cfg = cfg_all.get("execution") or {}
    # Fee tiers
    fee_bps = 5
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
    slip_cfg = exe_cfg.get("slippage") or {}
    slippage_base_bps = int(slip_cfg.get("base_bps", 10))
    slippage_k_atr_pct = float(slip_cfg.get("k_atr_pct", 0.0))

    res = simulate_on_series(
        coin_id=coin_id,
        threshold=threshold_val,
        closes=closes,
        highs=highs,
        lows=lows,
        rsi_period=rsi_p,
        ema_fast=ema_fast,
        ema_slow=ema_slow,
        atr_params=atr_params,
        slippage_base_bps=slippage_base_bps,
        slippage_k_atr_pct=slippage_k_atr_pct,
        fee_bps=fee_bps,
        times=times,
        export_dir=None,
        use_regime_filter=use_regime_filter,
        vol_gate_min_atr_pct=vol_min,
        vol_gate_max_atr_pct=vol_max,
        risk_budget_pct=risk_budget_pct,
        auto_threshold=auto_thr,
        auto_threshold_bear=auto_thr_bear,
    )
    # Robust metrics
    try:
        eq0 = res.equity[0] if res.equity else 0.0
        eq1 = res.equity[-1] if res.equity else 0.0
        bars = len(res.equity)
        # approximate years by timeframe
        if timeframe == "1d":
            years = bars / 365.0
        elif timeframe == "4h":
            years = (bars * 4.0) / (24.0 * 365.0)
        elif timeframe == "1h":
            years = (bars * 1.0) / (24.0 * 365.0)
        else:
            years = bars / 365.0
        cagr = ((eq1 / eq0) ** (1.0 / years) - 1.0) * 100.0 if eq0 > 0 and years > 0 else 0.0
    except Exception:
        cagr = 0.0
    try:
        mar = (cagr / res.max_drawdown) if res.max_drawdown > 0 else 0.0
    except Exception:
        mar = 0.0
    # avg return per trade (pct)
    avg_ret = 0.0
    try:
        rets = [t.pnl_pct() for t in res.trades if t.pnl_pct() is not None]
        avg_ret = (sum(rets) / len(rets)) if rets else 0.0
    except Exception:
        avg_ret = 0.0

    return EvalResult(
        params=params,
        trades=len(res.trades),
        win_rate=res.win_rate,
        profit_factor=res.profit_factor,
        max_drawdown=res.max_drawdown,
        cagr=cagr,
        mar=mar,
        avg_return_pct=avg_ret,
    )


def _grid_from_config(cfg_all: Dict) -> Dict:
    """Extracts the optimization grid from the config."""
    og = cfg_all.get("optimizer_grid") or {}
    return {
        "rsi": og.get("rsi", [14]),
        "ema_fast": og.get("ema_fast", [20]),
        "ema_slow": og.get("ema_slow", [50]),
        "sl_mult": og.get("sl_mult", [1.5]),
        "tp_mult": og.get("tp_mult", [3.0]),
        "risk_budget_pct": og.get("risk_budget_pct", [0.0]),
    }


def optimize() -> None:
    cfg_all = _read_config()
    notifier = Notifier()
    data_cfg = cfg_all.get("data") or {}
    timeframe = str(data_cfg.get("timeframe", "1d"))
    days = int(data_cfg.get("days", 365))
    grid_global = _grid_from_config(cfg_all)
    grid_overrides = cfg_all.get("optimizer_grid_overrides") or {}
    opt_cfg = cfg_all.get("optimize") or {}
    folds = int(opt_cfg.get("folds", 3))
    use_price_as_threshold = bool(opt_cfg.get("use_price_as_threshold", False))
    disable_regime_filter = bool(opt_cfg.get("disable_regime_filter", False))
    disable_vol_gate = bool(opt_cfg.get("disable_vol_gate", False))
    skip_symbols = [s.upper() for s in (opt_cfg.get("skip_symbols", ["USDT", "USDC"]))]
    tracked = cfg_all.get("tracked_coins") or {}
    coin_ids = [cid for cid, c in tracked.items() if not (c or {}).get("disabled", False)]

    for cid in coin_ids:
        print(f"\n=== Optimize {cid} ({timeframe}, {days}d) ===")
        series = _fetch_series(cfg_all, cid, timeframe, days)
        if series is None:
            print("  Skipping due to data fetch error.")
            continue
        closes, highs, lows, times = series
        # Skip stablecoins or unwanted symbols
        try:
            sym = str((tracked.get(cid) or {}).get("symbol", cid)).upper()
        except Exception:
            sym = cid.upper()
        if sym in skip_symbols:
            print("  Skipping due to configured skip_symbols.")
            continue
        n = len(closes)
        if n < 200:
            print("  Not enough data; skipping.")
            continue
        splits = _walk_forward_splits(n, folds=folds)
        # Choose grid (override per coin if provided)
        og = grid_overrides.get(cid) or {}
        grid = {
            "rsi": og.get("rsi", grid_global["rsi"]),
            "ema_fast": og.get("ema_fast", grid_global["ema_fast"]),
            "ema_slow": og.get("ema_slow", grid_global["ema_slow"]),
            "sl_mult": og.get("sl_mult", grid_global["sl_mult"]),
            "tp_mult": og.get("tp_mult", grid_global["tp_mult"]),
            "risk_budget_pct": og.get("risk_budget_pct", grid_global["risk_budget_pct"]),
        }
        combos = list(
            product(
                grid["rsi"],
                grid["ema_fast"],
                grid["ema_slow"],
                grid["sl_mult"],
                grid["tp_mult"],
                grid["risk_budget_pct"],
            )
        )
        results_summary: List[Tuple[Dict[str, float], List[EvalResult]]] = []
        for rsi_p, ef, es, slm, tpm, rb in combos:
            params = {
                "rsi": rsi_p,
                "ema_fast": ef,
                "ema_slow": es,
                "sl_mult": slm,
                "tp_mult": tpm,
                "risk_budget_pct": rb,
            }
            wf_results: List[EvalResult] = []
            for tr_s, tr_e, te_s, te_e in splits:
                # Train selection (we don't fit; for completeness, evaluate on train too)
                _ = _eval_params(
                    closes[tr_s:tr_e],
                    highs[tr_s:tr_e],
                    lows[tr_s:tr_e],
                    times[tr_s:tr_e],
                    cfg_all,
                    cid,
                    params,
                    timeframe,
                    use_price_as_threshold=use_price_as_threshold,
                    disable_regime_filter=disable_regime_filter,
                    disable_vol_gate=disable_vol_gate,
                )
                # Test evaluation
                ev = _eval_params(
                    closes[te_s:te_e],
                    highs[te_s:te_e],
                    lows[te_s:te_e],
                    times[te_s:te_e],
                    cfg_all,
                    cid,
                    params,
                    timeframe,
                    use_price_as_threshold=use_price_as_threshold,
                    disable_regime_filter=disable_regime_filter,
                    disable_vol_gate=disable_vol_gate,
                )
                wf_results.append(ev)
            results_summary.append((params, wf_results))

        # Rank by average profit factor over tests, then drawdown
        def score(item):
            params, lst = item
            if not lst:
                return (0.0, 1e9, 0.0)
            avg_pf = sum(x.profit_factor for x in lst) / len(lst)
            avg_dd = sum(x.max_drawdown for x in lst) / len(lst)
            avg_mar = sum(x.mar for x in lst) / len(lst)
            # Quality gate: MAR > 0.5, p5 worst week > -10%, p95 DD < 20%
            quality_score = 0
            if avg_mar > 0.5:
                quality_score += 1
            # These would require MC sims, for now we use avg as proxy
            if avg_dd < 20.0:
                quality_score += 1
            return (quality_score, avg_pf, -avg_dd)

        ranked = sorted(results_summary, key=score, reverse=True)
        print("Top 5 parameter sets (avg across walk-forward tests):")
        for i, (p, lst) in enumerate(ranked[:5], start=1):
            if lst:
                avg_pf = sum(x.profit_factor for x in lst) / len(lst)
                avg_dd = sum(x.max_drawdown for x in lst) / len(lst)
                avg_trades = int(sum(x.trades for x in lst) / len(lst))
                avg_wr = sum(x.win_rate for x in lst) / len(lst)
                avg_cagr = sum(x.cagr for x in lst) / len(lst)
                avg_mar = sum(x.mar for x in lst) / len(lst)
                avg_ret = sum(x.avg_return_pct for x in lst) / len(lst)
                print(
                    f" {i:>2}. params={p} | PF={avg_pf:.2f} | maxDD={avg_dd:.1f}% | "
                    f"WR={avg_wr:.1f}% | CAGR={avg_cagr:.2f}% | MAR={avg_mar:.2f} | "
                    f"avgRet={avg_ret:.2f}% | trades~{avg_trades}"
                )
            else:
                print(f" {i:>2}. params={p} | no results")
        # Print suggested YAML snippet for the best set
        if ranked:
            best_params, best_list = ranked[0]
            snippet = {
                "indicators": {
                    "rsi_period": best_params["rsi"],
                    "ema_fast": best_params["ema_fast"],
                    "ema_slow": best_params["ema_slow"],
                },
                "risk": {
                    "atr": {
                        "sl_mult": best_params["sl_mult"],
                        "tp_mult": best_params["tp_mult"],
                    }
                },
                "execution": {
                    "risk_budget_pct": best_params["risk_budget_pct"],
                },
            }
            out_dir = Path(__file__).resolve().parents[2] / "logs" / "backtest"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / "suggested_config.yaml"
            with out_path.open("a") as f:
                f.write(f"# Suggested config for {cid}\n")
                yaml.dump({cid: snippet}, f, default_flow_style=False)
                f.write("\n")
            print(f"Suggested config snippet for {cid} saved to {out_path}")
        # Send a short notifier summary for this coin
        try:
            if ranked:
                p, lst = ranked[0]
                if lst:
                    avg_pf = sum(x.profit_factor for x in lst) / len(lst)
                    avg_wr = sum(x.win_rate for x in lst) / len(lst)
                    avg_dd = sum(x.max_drawdown for x in lst) / len(lst)
                    avg_cagr = sum(x.cagr for x in lst) / len(lst)
                    avg_mar = sum(x.mar for x in lst) / len(lst)
                    msg = (
                        f"Top params: rsi={p['rsi']}, ef={p['ema_fast']}, es={p['ema_slow']}, "
                        f"sl={p['sl_mult']}, tp={p['tp_mult']}, rb={p['risk_budget_pct']}\n"
                        f"PF={avg_pf:.2f}, WR={avg_wr:.1f}%, maxDD={avg_dd:.1f}%, "
                        f"CAGR={avg_cagr:.2f}%, MAR={avg_mar:.2f}"
                    )
                    notifier.alert(f"Optimizer Summary {cid}", msg, style="cyan")
        except Exception:
            pass
        # Write CSV summary per coin
        try:
            out_dir = Path(__file__).resolve().parents[2] / "logs" / "backtest"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"optimizer_{cid}_{timeframe}.csv"
            with out_path.open("w", newline="") as f:
                w = csv.writer(f)
                w.writerow(
                    [
                        "rsi",
                        "ema_fast",
                        "ema_slow",
                        "sl_mult",
                        "tp_mult",
                        "risk_budget_pct",
                        "avg_pf",
                        "avg_dd",
                        "avg_trades",
                        "avg_win_rate",
                        "avg_cagr",
                        "avg_mar",
                        "avg_return_pct",
                        "mc_p5_return_pct",
                        "mc_p5_maxdd_pct",
                        "mc_p5_worst_week_pct",
                    ]
                )
                for p, lst in ranked:
                    if lst:
                        avg_pf = sum(x.profit_factor for x in lst) / len(lst)
                        avg_dd = sum(x.max_drawdown for x in lst) / len(lst)
                        avg_trades = sum(x.trades for x in lst) / len(lst)
                        avg_wr = sum(x.win_rate for x in lst) / len(lst)
                        avg_cagr = sum(x.cagr for x in lst) / len(lst)
                        avg_mar = sum(x.mar for x in lst) / len(lst)
                        avg_ret = sum(x.avg_return_pct for x in lst) / len(lst)
                    else:
                        avg_pf = 0.0
                        avg_dd = 0.0
                        avg_trades = 0.0
                        avg_wr = 0.0
                        avg_cagr = 0.0
                        avg_mar = 0.0
                        avg_ret = 0.0
                    # Simple Monte Carlo sequencing for this parameter set on full data
                    # Re-evaluate on full series for MC
                    _eval_params(
                        closes,
                        highs,
                        lows,
                        times,
                        cfg_all,
                        cid,
                        p,
                        timeframe,
                        use_price_as_threshold=use_price_as_threshold,
                        disable_regime_filter=disable_regime_filter,
                        disable_vol_gate=disable_vol_gate,
                    )
                    # Build trade return list from a fresh full-run simulation
                    # We do not store per-trade results here; approximate using avg_return_pct and trade count
                    # For a better MC, consider extending engine to return per-trade returns list
                    mc_p5 = 0.0
                    mc_p5_maxdd = 0.0
                    mc_p5_worstweek = 0.0
                    try:
                        import random

                        rets = [
                            t.pnl_pct()
                            for t in simulate_on_series(
                                coin_id=cid,
                                threshold=float(
                                    (cfg_all.get("tracked_coins") or {})
                                    .get(cid, {})
                                    .get("threshold", 0.0)
                                ),
                                closes=closes,
                                highs=highs,
                                lows=lows,
                                rsi_period=int(p["rsi"]),
                                ema_fast=int(p["ema_fast"]),
                                ema_slow=int(p["ema_slow"]),
                                atr_params=ATRRiskParams(
                                    atr_period=int(
                                        (cfg_all.get("risk") or {}).get("atr", {}).get("period", 14)
                                    ),
                                    sl_mult=float(p["sl_mult"]),
                                    tp_mult=float(p["tp_mult"]),
                                    trail_mult=float(
                                        (cfg_all.get("risk") or {})
                                        .get("atr", {})
                                        .get("trail_mult", 2.0)
                                    ),
                                ),
                                slippage_base_bps=int(
                                    (cfg_all.get("execution") or {})
                                    .get("slippage", {})
                                    .get("base_bps", 10)
                                ),
                                slippage_k_atr_pct=float(
                                    (cfg_all.get("execution") or {})
                                    .get("slippage", {})
                                    .get("k_atr_pct", 0.0)
                                ),
                                fee_bps=int(
                                    float(
                                        (
                                            (cfg_all.get("execution") or {})
                                            .get("fee_tiers", [{}])[0]
                                            .get(
                                                "taker_bps",
                                                (cfg_all.get("execution") or {}).get("fee_bps", 5),
                                            )
                                        )
                                    )
                                ),
                                times=times,
                                export_dir=None,
                                use_regime_filter=bool(
                                    (cfg_all.get("strategy") or {}).get("use_regime_filter", False)
                                ),
                                vol_gate_min_atr_pct=(cfg_all.get("strategy") or {})
                                .get("vol_gate", {})
                                .get("min_atr_pct"),
                                vol_gate_max_atr_pct=(cfg_all.get("strategy") or {})
                                .get("vol_gate", {})
                                .get("max_atr_pct"),
                                risk_budget_pct=float(p.get("risk_budget_pct", 0.0)),
                                auto_threshold=float(
                                    (cfg_all.get("decision") or {})
                                    .get("confidence_thresholds", {})
                                    .get("auto", 0.8)
                                ),
                                auto_threshold_bear=(
                                    float(
                                        (
                                            (cfg_all.get("decision") or {})
                                            .get("confidence_thresholds", {})
                                            .get("auto_bear", 0.8)
                                        )
                                    )
                                    if (
                                        (cfg_all.get("decision") or {})
                                        .get("confidence_thresholds", {})
                                        .get("auto_bear", None)
                                        is not None
                                    )
                                    else None
                                ),
                            ).trades
                            if t.pnl_pct() is not None
                        ]
                        if rets:
                            trials = int((cfg_all.get("optimize") or {}).get("mc_trials", 200))
                            finals: List[float] = []
                            dds: List[float] = []
                            wweeks: List[float] = []
                            for _ in range(trials):
                                random.shuffle(rets)
                                g = 1.0
                                eq_curve: List[float] = []
                                for rp in rets:
                                    g *= 1.0 + rp / 100.0
                                    eq_curve.append(g)
                                finals.append((g - 1.0) * 100.0)
                                # max drawdown (%) on equity curve
                                peak = eq_curve[0] if eq_curve else 1.0
                                maxdd = 0.0
                                for v in eq_curve:
                                    if v > peak:
                                        peak = v
                                    dd = (peak - v) / peak * 100.0 if peak > 0 else 0.0
                                    if dd > maxdd:
                                        maxdd = dd
                                dds.append(maxdd)
                                # worst-week proxy: worst rolling 7-trade cumulative return (%)
                                if len(rets) >= 7:
                                    worst = 0.0
                                    for i in range(0, len(rets) - 6):
                                        g7 = 1.0
                                        for j in range(7):
                                            g7 *= 1.0 + rets[i + j] / 100.0
                                        r7 = (g7 - 1.0) * 100.0
                                        if r7 < worst:
                                            worst = r7
                                    wweeks.append(worst)
                                else:
                                    wweeks.append(0.0)
                            finals.sort()
                            dds.sort()
                            wweeks.sort()
                            mc_p5 = finals[int(0.05 * (len(finals) - 1))] if finals else 0.0
                            mc_p5_maxdd = (
                                dds[int(0.95 * (len(dds) - 1))] if dds else 0.0
                            )  # 95th percentile DD
                            mc_p5_worstweek = (
                                wweeks[int(0.05 * (len(wweeks) - 1))] if wweeks else 0.0
                            )
                    except Exception:
                        mc_p5 = 0.0
                        mc_p5_maxdd = 0.0
                        mc_p5_worstweek = 0.0
                    w.writerow(
                        [
                            p["rsi"],
                            p["ema_fast"],
                            p["ema_slow"],
                            p["sl_mult"],
                            p["tp_mult"],
                            p["risk_budget_pct"],
                            f"{avg_pf:.4f}",
                            f"{avg_dd:.2f}",
                            f"{avg_trades:.2f}",
                            f"{avg_wr:.2f}",
                            f"{avg_cagr:.2f}",
                            f"{avg_mar:.2f}",
                            f"{avg_ret:.2f}",
                            f"{mc_p5:.2f}",
                            f"{mc_p5_maxdd:.2f}",
                            f"{mc_p5_worstweek:.2f}",
                        ]
                    )
            print(f"  Wrote CSV: {out_path}")
        except Exception as ex:
            print(f"  Could not write CSV for {cid}: {ex}")


if __name__ == "__main__":
    optimize()
