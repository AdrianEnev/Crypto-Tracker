from pathlib import Path

import optuna
import yaml

from src.backtest.optimizer import _eval_params, _fetch_series


def objective(
    trial,
    cfg_all,
    coin_id,
    timeframe,
    days,
    use_price_as_threshold,
    disable_regime_filter,
    disable_vol_gate,
):
    params = {
        "rsi": trial.suggest_int("rsi", 5, 25),
        "ema_fast": trial.suggest_int("ema_fast", 5, 50),
        "ema_slow": trial.suggest_int("ema_slow", 20, 100),
        "sl_mult": trial.suggest_float("sl_mult", 0.5, 3.0),
        "tp_mult": trial.suggest_float("tp_mult", 1.0, 5.0),
        "risk_budget_pct": trial.suggest_float("risk_budget_pct", 0.001, 0.02),
    }

    series = _fetch_series(cfg_all, coin_id, timeframe, days)
    if series is None:
        return 0.0

    closes, highs, lows, times = series
    result = _eval_params(
        closes,
        highs,
        lows,
        times,
        cfg_all,
        coin_id,
        params,
        timeframe,
        use_price_as_threshold,
        disable_regime_filter,
        disable_vol_gate,
    )

    return result.profit_factor


def tune():
    cfg_all = yaml.safe_load(Path("config/config.yaml").read_text())

    # For simplicity, we'll tune the first enabled coin
    coin_id = next(cid for cid, c in cfg_all["tracked_coins"].items() if not c.get("disabled"))

    study = optuna.create_study(direction="maximize")
    study.optimize(
        lambda trial: objective(trial, cfg_all, coin_id, "1d", 365, False, False, False),
        n_trials=100,
    )

    print("Best trial:")
    trial = study.best_trial
    print(f"  Value: {trial.value}")
    print("  Params: ")
    for key, value in trial.params.items():
        print(f"    {key}: {value}")


if __name__ == "__main__":
    tune()
