from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import csv

import os
import yaml

from .engine import simulate_on_series, ATRRiskParams
from ..data.ohlcv import get_candles
from ..data.ccxt_ohlcv import get_candles_ccxt


@dataclass
class EvalResult:
    params: Dict[str, float]
    trades: int
    win_rate: float
    profit_factor: float
    max_drawdown: float

def _read_config() -> Dict:
    project_root = Path(__file__).resolve().parents[2]
    with open(project_root / "config" / "config.yaml", "r") as f:
        return yaml.safe_load(f) or {}


def _fetch_series(cfg_all: Dict, coin_id: str, timeframe: str, days: int) -> Optional[Tuple[List[float], List[float], List[float], List[int]]]:
    try:
        data_cfg = (cfg_all.get("data") or {})
        provider = str(data_cfg.get("provider", "coingecko")).lower()
        api_key = os.environ.get("COINGECKO_API_KEY")
        tracked = (cfg_all.get("tracked_coins") or {})
        per = tracked.get(coin_id, {})
        cg_id = per.get("coingecko_id", coin_id)
        if provider == "ccxt":
            providers_cfg = (cfg_all.get("providers") or {})
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
            candles = get_candles_ccxt(exchange_name, market, timeframe=timeframe, cache_dir="./data_cache", limit=limit, use_cache=True)
        else:
            candles = get_candles(cg_id, timeframe=timeframe, days=days, cache_dir="./data_cache", use_cache=True, api_key=api_key)
        closes = [c.c for c in candles]
        highs = [c.h for c in candles]
        lows = [c.l for c in candles]
        times = [getattr(c, 'ts', i) for i, c in enumerate(candles)]
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


def _eval_params(closes, highs, lows, times, cfg_all: Dict, coin_id: str, params: Dict[str, float], 
                 use_price_as_threshold: bool = False,
                 disable_regime_filter: bool = False,
                 disable_vol_gate: bool = False) -> EvalResult:
    ind_cfg = (cfg_all.get("indicators") or {})
    ema_fast = int(params.get("ema_fast", ind_cfg.get("ema_fast", 20)))
    ema_slow = int(params.get("ema_slow", ind_cfg.get("ema_slow", 50)))
    rsi_p = int(params.get("rsi", ind_cfg.get("rsi_period", 14)))
    # Strategy
    strat = (cfg_all.get("strategy") or {})
    use_regime_filter = bool(strat.get("use_regime_filter", False))
    if disable_regime_filter:
        use_regime_filter = False
    vg = (strat.get("vol_gate") or {})
    vol_min = float(vg.get("min_atr_pct", 0.0)) if vg.get("min_atr_pct") is not None else None
    vol_max = float(vg.get("max_atr_pct", 0.0)) if vg.get("max_atr_pct") is not None else None
    if disable_vol_gate:
        vol_min = None
        vol_max = None
    # Decision
    decision = (cfg_all.get("decision") or {})
    thr = (decision.get("confidence_thresholds") or {})
    auto_thr = float(thr.get("auto", 0.8))
    auto_thr_bear = thr.get("auto_bear")
    auto_thr_bear = float(auto_thr_bear) if auto_thr_bear is not None else None
    # ATR params
    risk_cfg2 = (cfg_all.get("risk") or {})
    atr_cfg = (risk_cfg2.get("atr") or {})
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
            threshold_val = float(sorted(closes)[len(closes)//2]) if closes else 0.0
        except Exception:
            threshold_val = 0.0
    else:
        tracked = (cfg_all.get("tracked_coins") or {})
        threshold_val = float((tracked.get(coin_id) or {}).get("threshold", 0.0))
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
        slippage_bps=10,
        fee_bps=5,
        times=times,
        export_dir=None,
        use_regime_filter=use_regime_filter,
        vol_gate_min_atr_pct=vol_min,
        vol_gate_max_atr_pct=vol_max,
        risk_budget_pct=risk_budget_pct,
        auto_threshold=auto_thr,
        auto_threshold_bear=auto_thr_bear,
    )
    return EvalResult(
        params=params,
        trades=len(res.trades),
        win_rate=res.win_rate,
        profit_factor=res.profit_factor,
        max_drawdown=res.max_drawdown,
    )


def _grid_from_config(cfg_all: Dict) -> Dict:
    """Extracts the optimization grid from the config."""
    og = (cfg_all.get("optimizer_grid") or {})
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
    data_cfg = (cfg_all.get("data") or {})
    timeframe = str(data_cfg.get("timeframe", "1d"))
    days = int(data_cfg.get("days", 365))
    grid = _grid_from_config(cfg_all)
    opt_cfg = (cfg_all.get("optimize") or {})
    folds = int(opt_cfg.get("folds", 3))
    use_price_as_threshold = bool(opt_cfg.get("use_price_as_threshold", False))
    disable_regime_filter = bool(opt_cfg.get("disable_regime_filter", False))
    disable_vol_gate = bool(opt_cfg.get("disable_vol_gate", False))
    skip_symbols = [s.upper() for s in (opt_cfg.get("skip_symbols", ["USDT", "USDC"]))]
    tracked = (cfg_all.get("tracked_coins") or {})
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
            sym = str((tracked.get(cid) or {}).get('symbol', cid)).upper()
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
        combos = list(product(grid["rsi"], grid["ema_fast"], grid["ema_slow"], grid["sl_mult"], grid["tp_mult"], grid["risk_budget_pct"]))
        results_summary: List[Tuple[Dict[str, float], List[EvalResult]]] = []
        for rsi_p, ef, es, slm, tpm, rb in combos:
            params = {"rsi": rsi_p, "ema_fast": ef, "ema_slow": es, "sl_mult": slm, "tp_mult": tpm, "risk_budget_pct": rb}
            wf_results: List[EvalResult] = []
            for (tr_s, tr_e, te_s, te_e) in splits:
                # Train selection (we don't fit; for completeness, evaluate on train too)
                _ = _eval_params(
                    closes[tr_s:tr_e], highs[tr_s:tr_e], lows[tr_s:tr_e], times[tr_s:tr_e], cfg_all, cid, params,
                    use_price_as_threshold=use_price_as_threshold,
                    disable_regime_filter=disable_regime_filter,
                    disable_vol_gate=disable_vol_gate,
                )
                # Test evaluation
                ev = _eval_params(
                    closes[te_s:te_e], highs[te_s:te_e], lows[te_s:te_e], times[te_s:te_e], cfg_all, cid, params,
                    use_price_as_threshold=use_price_as_threshold,
                    disable_regime_filter=disable_regime_filter,
                    disable_vol_gate=disable_vol_gate,
                )
                wf_results.append(ev)
            results_summary.append((params, wf_results))
        # Rank by average profit factor over tests, then drawdown
        def score(item):
            _, lst = item
            if not lst:
                return (0.0, 1e9)
            avg_pf = sum(x.profit_factor for x in lst) / len(lst)
            avg_dd = sum(x.max_drawdown for x in lst) / len(lst)
            return (avg_pf, -avg_dd)
        ranked = sorted(results_summary, key=score, reverse=True)
        print("Top 5 parameter sets (avg across walk-forward tests):")
        for i, (p, lst) in enumerate(ranked[:5], start=1):
            if lst:
                avg_pf = sum(x.profit_factor for x in lst) / len(lst)
                avg_dd = sum(x.max_drawdown for x in lst) / len(lst)
                avg_trades = int(sum(x.trades for x in lst) / len(lst))
                avg_wr = sum(x.win_rate for x in lst) / len(lst)
                print(f" {i:>2}. params={p} | PF={avg_pf:.2f} | maxDD={avg_dd:.1f}% | WR={avg_wr:.1f}% | trades~{avg_trades}")
            else:
                print(f" {i:>2}. params={p} | no results")
        # Print suggested YAML snippet for the best set
        if ranked:
            best_params, best_list = ranked[0]
            print("Suggested config snippet (paste under indicators/risk/execution):")
            print("indicators:")
            print(f"  rsi_period: {best_params['rsi']}")
            print(f"  ema_fast: {best_params['ema_fast']}")
            print(f"  ema_slow: {best_params['ema_slow']}")
            print("risk:")
            print("  atr:")
            print(f"    sl_mult: {best_params['sl_mult']}")
            print(f"    tp_mult: {best_params['tp_mult']}")
            print("execution:")
            print(f"  risk_budget_pct: {best_params['risk_budget_pct']}")
        # Write CSV summary per coin
        try:
            out_dir = Path(__file__).resolve().parents[2] / 'logs' / 'backtest'
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"optimizer_{cid}_{timeframe}.csv"
            with out_path.open('w', newline='') as f:
                w = csv.writer(f)
                w.writerow(['rsi','ema_fast','ema_slow','sl_mult','tp_mult','risk_budget_pct','avg_pf','avg_dd','avg_trades','avg_win_rate'])
                for p, lst in ranked:
                    if lst:
                        avg_pf = sum(x.profit_factor for x in lst) / len(lst)
                        avg_dd = sum(x.max_drawdown for x in lst) / len(lst)
                        avg_trades = sum(x.trades for x in lst) / len(lst)
                        avg_wr = sum(x.win_rate for x in lst) / len(lst)
                    else:
                        avg_pf = 0.0; avg_dd = 0.0; avg_trades = 0.0; avg_wr = 0.0
                    w.writerow([
                        p['rsi'], p['ema_fast'], p['ema_slow'], p['sl_mult'], p['tp_mult'], p['risk_budget_pct'],
                        f"{avg_pf:.4f}", f"{avg_dd:.2f}", f"{avg_trades:.2f}", f"{avg_wr:.2f}"
                    ])
            print(f"  Wrote CSV: {out_path}")
        except Exception as ex:
            print(f"  Could not write CSV for {cid}: {ex}")


if __name__ == "__main__":
    optimize()
