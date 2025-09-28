from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from ..risk import ATRRiskParams
from .engine import simulate_coin


def grid(values):
    return values


def main():
    parser = argparse.ArgumentParser(description="Parameter tuning over 1y history")
    parser.add_argument(
        "--coins", type=str, default="", help="Comma-separated coin ids (default: all tracked)"
    )
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--timeframe", type=str, default="1d")
    parser.add_argument("--slippage_bps", type=int, default=10)
    parser.add_argument("--fee_bps", type=int, default=5)
    parser.add_argument("--min_trades", type=int, default=5)
    parser.add_argument(
        "--write", action="store_true", help="Write best params back to config/config.yaml per-coin"
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[2]
    config_path = project_root / "config" / "config.yaml"
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f) or {}

    tracked = cfg.get("tracked_coins") or {}
    target_ids = (
        [c.strip() for c in args.coins.split(",") if c.strip()]
        if args.coins
        else list(tracked.keys())
    )

    # Global defaults
    ind_cfg = cfg.get("indicators") or {}
    g_rsi = int(ind_cfg.get("rsi_period", 14))
    g_ef = int(ind_cfg.get("ema_fast", 20))
    g_es = int(ind_cfg.get("ema_slow", 50))
    risk_cfg = cfg.get("risk") or {}
    atr_cfg = risk_cfg.get("atr") or {}

    # Grids (conservative sizes to keep runtime down)
    rsi_grid = grid([10, 14, 21, 28])
    ef_grid = grid([12, 20, 26])
    es_grid = grid([40, 50, 60])
    atr_sl_grid = grid([1.0, 1.5, 2.0])
    atr_tp_grid = grid([2.0, 3.0, 4.0])

    results_summary: Dict[str, Dict[str, float]] = {}

    for coin_id in target_ids:
        cdata = tracked.get(coin_id) or {}
        threshold = float(cdata.get("threshold", 0.0))
        cg_id = str(cdata.get("coingecko_id", coin_id))

        best = {
            "score": -1e9,
            "pf": 0.0,
            "win": 0.0,
            "dd": 0.0,
            "rsi": g_rsi,
            "ef": g_ef,
            "es": g_es,
            "sl": float(atr_cfg.get("sl_mult", 1.5)) if atr_cfg else 1.5,
            "tp": float(atr_cfg.get("tp_mult", 3.0)) if atr_cfg else 3.0,
        }

        for rsi_p in rsi_grid:
            for ef in ef_grid:
                for es in es_grid:
                    for slm in atr_sl_grid:
                        for tpm in atr_tp_grid:
                            atrp = int(atr_cfg.get("period", 14)) if atr_cfg else 14
                            atr_params = ATRRiskParams(
                                atr_period=atrp,
                                sl_mult=slm,
                                tp_mult=tpm,
                                trail_mult=(
                                    float(atr_cfg.get("trail_mult", 2.0)) if atr_cfg else 2.0
                                ),
                            )
                            res = simulate_coin(
                                coin_id=coin_id,
                                cg_id=cg_id,
                                threshold=threshold,
                                days=args.days,
                                timeframe=args.timeframe,
                                rsi_period=int(rsi_p),
                                ema_fast=int(ef),
                                ema_slow=int(es),
                                atr_params=atr_params,
                                slippage_bps=args.slippage_bps,
                                fee_bps=args.fee_bps,
                            )
                            # Require a minimum number of trades to avoid overfitting
                            if len(res.trades) < args.min_trades:
                                continue
                            # Score: prioritize PF, penalize drawdown
                            score = res.profit_factor - (res.max_drawdown / 100.0)
                            if score > best["score"]:
                                best.update(
                                    {
                                        "score": score,
                                        "pf": res.profit_factor,
                                        "win": res.win_rate,
                                        "dd": res.max_drawdown,
                                        "rsi": int(rsi_p),
                                        "ef": int(ef),
                                        "es": int(es),
                                        "sl": float(slm),
                                        "tp": float(tpm),
                                    }
                                )
        if best["score"] <= -1e8:
            print(f"No viable params for {coin_id} (not enough trades). Skipping.")
            continue

        results_summary[coin_id] = best
        print(
            f"\n>>> {coin_id} best: PF={best['pf']:.2f} Win%={best['win']:.1f}% MaxDD={best['dd']:.1f}% RSI={best['rsi']} EF={best['ef']} ES={best['es']} SLx={best['sl']} TPx={best['tp']}"
        )

    if args.write and results_summary:
        # Write per-coin overrides back to config
        with open(config_path, "r") as f:
            cfg_all = yaml.safe_load(f) or {}
        tc = cfg_all.setdefault("tracked_coins", {})
        for coin_id, best in results_summary.items():
            cd = tc.setdefault(coin_id, {})
            ind = cd.setdefault("indicators", {})
            ind["rsi_period"] = int(best["rsi"])
            ind["ema_fast"] = int(best["ef"])
            ind["ema_slow"] = int(best["es"])
            rc = cd.setdefault("risk", {})
            ac = rc.setdefault("atr", {})
            # Keep existing period if present, else default 14
            ac.setdefault("period", int((cfg.get("risk") or {}).get("atr", {}).get("period", 14)))
            ac["sl_mult"] = float(best["sl"])
            ac["tp_mult"] = float(best["tp"])
        with open(config_path, "w") as f:
            yaml.safe_dump(cfg_all, f, sort_keys=False)
        print("\nWrote best per-coin parameters to config/config.yaml")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
