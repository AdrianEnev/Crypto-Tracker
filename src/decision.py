from __future__ import annotations
from typing import Any, Dict, Optional

import pandas as pd
import yaml

from .strategies.factory import get_strategy
from .models import Decision


def _load_full_config(config_path: str) -> Dict[str, Any]:
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _build_df_from_history(tracker, coin_id: str) -> Optional[pd.DataFrame]:
    h = (tracker.history.get(coin_id) or {})
    candles = h.get("candles") or []
    if not candles:
        return None
    df = pd.DataFrame({
        "open": [c.o for c in candles],
        "high": [c.h for c in candles],
        "low": [c.l for c in candles],
        "close": [c.c for c in candles],
        "volume": [c.v for c in candles],
        "ts": [c.ts for c in candles],
    })
    df.index = pd.to_datetime(df["ts"], unit="ms")
    return df


def make_decision(tracker, coin_id: str) -> Decision:
    """
    Orchestrate strategy evaluation for a coin and return a Decision.
    Applies regime and volatility gates from config.
    """
    cfg_all = _load_full_config(tracker.config_path)
    per_coin_cfg = (cfg_all.get("tracked_coins") or {}).get(coin_id) or {}
    strat_cfg = (per_coin_cfg.get("strategy") or {})
    strat_name = str(strat_cfg.get("name") or (cfg_all.get("strategy") or {}).get("default_strategy") or "mean_reversion")
    strat_params: Dict[str, Any] = strat_cfg.get("params") or {}

    df = _build_df_from_history(tracker, coin_id)
    if df is None or df.empty:
        return Decision(signal="no_data", confidence=0.0, action_recommended="Hold", reason="No candles in history")

    # Instantiate and run strategy
    try:
        strategy = get_strategy(strat_name, strat_params)
    except Exception as ex:
        return Decision(signal="strategy_error", confidence=0.0, action_recommended="Hold", reason=f"{ex}")

    try:
        signals = strategy.generate_signals(df)
        last_sig = int(signals["signal"].iloc[-1]) if "signal" in signals.columns and not signals.empty else 0
    except Exception as ex:
        return Decision(signal="strategy_eval_error", confidence=0.0, action_recommended="Hold", reason=str(ex))

    # Regime filter (EMA fast vs slow) if enabled & available in tracker.history
    regime_ok = True
    use_regime = bool((cfg_all.get("strategy") or {}).get("use_regime_filter", False))
    if use_regime:
        last = ((tracker.history.get(coin_id) or {}).get("last") or {})
        ef = last.get("ema_fast")
        es = last.get("ema_slow")
        if ef is None or es is None:
            # If no EMA context, fail safe to neutral
            regime_ok = False
        else:
            if last_sig > 0:
                regime_ok = float(ef) > float(es)
            elif last_sig < 0:
                regime_ok = float(ef) < float(es)

    # Volatility gate using ATR%
    vol_ok = True
    vg = (cfg_all.get("strategy") or {}).get("vol_gate") or {}
    if vg:
        min_atr_pct = vg.get("min_atr_pct")
        max_atr_pct = vg.get("max_atr_pct")
        last = ((tracker.history.get(coin_id) or {}).get("last") or {})
        atr_val = last.get("atr")
        close = last.get("close")
        if atr_val is None or close is None or float(close) <= 0:
            vol_ok = False
        else:
            atr_pct = (float(atr_val) / float(close)) * 100.0
            if min_atr_pct is not None and atr_pct < float(min_atr_pct):
                vol_ok = False
            if max_atr_pct is not None and atr_pct > float(max_atr_pct):
                vol_ok = False

    # Decide action
    action = "Hold"
    reason_parts = [f"strat={strat_name}"]
    if last_sig > 0:
        action = "Buy"
        reason_parts.append("signal=buy")
    elif last_sig < 0:
        action = "Sell"
        reason_parts.append("signal=sell")
    else:
        reason_parts.append("signal=flat")

    if not regime_ok:
        action = "Hold"
        reason_parts.append("regime_blocked")
    if not vol_ok:
        action = "Hold"
        reason_parts.append("vol_gate_blocked")

    # Confidence heuristic: base 0.8 if both gates pass and we have a non-zero signal; else low
    confidence = 0.8 if (last_sig != 0 and regime_ok and vol_ok) else (0.3 if last_sig != 0 else 0.0)

    return Decision(
        signal=f"{strat_name}_signal",
        confidence=confidence,
        action_recommended=action,
        reason=",".join(reason_parts),
    )

