from __future__ import annotations
from typing import Any, Dict, List


REQUIRED_TOP_LEVEL = [
    "tracked_coins",
    "api",
]


def validate_config(cfg: Dict[str, Any]) -> List[str]:
    """Lightweight config validator (no external deps).

    Returns list of human-readable error strings. Empty list means OK.
    """
    errors: List[str] = []
    if not isinstance(cfg, dict):
        return ["config root must be a mapping"]

    # top-level
    for key in REQUIRED_TOP_LEVEL:
        if key not in cfg:
            errors.append(f"missing top-level key: {key}")

    # api
    api = cfg.get("api") or {}
    if not isinstance(api, dict):
        errors.append("api must be a mapping")
    else:
        if not api.get("base_url"):
            errors.append("api.base_url is required")
        if "timeout" in api:
            try:
                to = float(api["timeout"])
                if to <= 0:
                    errors.append("api.timeout must be positive")
            except Exception:
                errors.append("api.timeout must be a number")

    # tracked_coins
    tcoins = cfg.get("tracked_coins") or {}
    if not isinstance(tcoins, dict) or not tcoins:
        errors.append("tracked_coins must be a non-empty mapping")
    else:
        for cid, data in tcoins.items():
            if not isinstance(data, dict):
                errors.append(f"tracked_coins.{cid} must be a mapping")
                continue
            for req in ("symbol", "name", "threshold"):
                if req not in data:
                    errors.append(f"tracked_coins.{cid}.{req} is required")
            if "threshold" in data:
                try:
                    float(data["threshold"])
                except Exception:
                    errors.append(f"tracked_coins.{cid}.threshold must be numeric")
            if "check_interval" in data:
                try:
                    iv = int(data["check_interval"])
                    if iv <= 0:
                        errors.append(f"tracked_coins.{cid}.check_interval must be positive")
                except Exception:
                    errors.append(f"tracked_coins.{cid}.check_interval must be an integer")

    # execution.liquidity_check
    exec_cfg = cfg.get("execution") or {}
    if isinstance(exec_cfg, dict):
        # Fees & slippage
        slip = exec_cfg.get("slippage") or {}
        if slip:
            if "base_bps" in slip:
                try:
                    bb = float(slip["base_bps"])
                    if bb < 0:
                        errors.append("execution.slippage.base_bps must be >= 0")
                except Exception:
                    errors.append("execution.slippage.base_bps must be a number")
            if "k_atr_pct" in slip:
                try:
                    float(slip["k_atr_pct"])
                except Exception:
                    errors.append("execution.slippage.k_atr_pct must be numeric")
        if "fee_bps" in exec_cfg:
            try:
                fb = float(exec_cfg["fee_bps"])
                if fb < 0:
                    errors.append("execution.fee_bps must be >= 0")
            except Exception:
                errors.append("execution.fee_bps must be numeric")
        # Exposure caps
        for k in (
            "max_exposure_pct",
            "max_coin_exposure_pct",
            "max_sector_exposure_pct",
            "cash_floor_pct",
            "max_portfolio_var_pct",
        ):
            if k in exec_cfg and exec_cfg[k] is not None:
                try:
                    float(exec_cfg[k])
                except Exception:
                    errors.append(f"execution.{k} must be numeric")
        if "max_exposure_usd" in exec_cfg and exec_cfg["max_exposure_usd"] is not None:
            try:
                float(exec_cfg["max_exposure_usd"])
            except Exception:
                errors.append("execution.max_exposure_usd must be numeric")
        # Liquidity
        liq = exec_cfg.get("liquidity_check") or {}
        if liq:
            try:
                if "min_daily_notional_usd" in liq:
                    mdn = float(liq["min_daily_notional_usd"])
                    if mdn < 0:
                        errors.append(
                            "execution.liquidity_check.min_daily_notional_usd must be >= 0"
                        )
            except Exception:
                errors.append("execution.liquidity_check.min_daily_notional_usd must be a number")
        ks = exec_cfg.get("kill_switch") or {}
        if ks:
            if "dd_intraday_pct" in ks:
                try:
                    dd = float(ks["dd_intraday_pct"])
                    if dd < 0:
                        errors.append("execution.kill_switch.dd_intraday_pct must be >= 0")
                except Exception:
                    errors.append("execution.kill_switch.dd_intraday_pct must be a number")
            if "max_errors_per_hour" in ks:
                try:
                    me = int(ks["max_errors_per_hour"])
                    if me < 0:
                        errors.append("execution.kill_switch.max_errors_per_hour must be >= 0")
                except Exception:
                    errors.append("execution.kill_switch.max_errors_per_hour must be an integer")
        # Stagger
        stag = exec_cfg.get("stagger") or {}
        if stag:
            if "max_per_cycle" in stag:
                try:
                    v = int(stag["max_per_cycle"])
                    if v < 0:
                        errors.append("execution.stagger.max_per_cycle must be >= 0")
                except Exception:
                    errors.append("execution.stagger.max_per_cycle must be an integer")
            if "spacing_seconds" in stag:
                try:
                    s = int(stag["spacing_seconds"])
                    if s < 0:
                        errors.append("execution.stagger.spacing_seconds must be >= 0")
                except Exception:
                    errors.append("execution.stagger.spacing_seconds must be an integer")

    # optimize
    opt = cfg.get("optimize") or {}
    if opt:
        if "min_trades" in opt:
            try:
                mt = int(opt["min_trades"])
                if mt < 0:
                    errors.append("optimize.min_trades must be >= 0")
            except Exception:
                errors.append("optimize.min_trades must be an integer")
        if "min_mar" in opt:
            try:
                float(opt["min_mar"])
            except Exception:
                errors.append("optimize.min_mar must be numeric")
        if "mc_trials" in opt:
            try:
                trials = int(opt["mc_trials"])
                if trials <= 0:
                    errors.append("optimize.mc_trials must be > 0")
            except Exception:
                errors.append("optimize.mc_trials must be an integer")

    return errors
