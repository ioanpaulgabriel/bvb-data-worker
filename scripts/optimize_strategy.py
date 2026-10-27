import csv
from datetime import datetime, timezone
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import optuna
from optuna.samplers import TPESampler

HOLDINGS = [16, 17, 18, 19, 20, 21, 22, 23, 24, 25]
N_TRIALS = int(os.getenv("OPTUNA_TRIALS", "40"))
OUT = Path("config/optimized_hyperparameters.json")


def run(h, v):
    env = os.environ.copy()
    env.update({
        "HOLDING_DAYS": str(h),
        "MIN_VOLUME_RATIO": str(v),
        "SIMULATION_SPLIT": "train",
    })
    subprocess.run(
        [sys.executable, "scripts/generate_atr_portfolio_signals.py"],
        env=env, check=True, capture_output=True,
    )
    subprocess.run(
        [sys.executable, "scripts/run_atr_portfolio_simulation.py"],
        env=env, check=True, capture_output=True,
    )

    with Path("data/atr_portfolio_simulation_trades_train.csv").open() as f:
        trades = list(csv.DictReader(f))
    with Path("data/atr_portfolio_simulation_equity_train.csv").open() as f:
        equity = [float(r["equity"]) for r in csv.DictReader(f)]

    pnl = [float(t["net_return"]) * float(t["position_value"]) for t in trades]
    wins = [x for x in pnl if x > 0]
    losses = [x for x in pnl if x < 0]
    gw, gl = sum(wins), abs(sum(losses))
    pf = gw / gl if gl else 10.0

    peak, mdd = equity[0], 0.0
    for e in equity:
        peak = max(peak, e)
        mdd = min(mdd, e / peak - 1)

    rets = [p / 100000 for p in pnl]
    mean = sum(rets) / len(rets)
    sd = (sum((r - mean) ** 2 for r in rets) / len(rets)) ** 0.5
    sharpe = mean / sd * math.sqrt(252) if sd else 0

    return {
        "trades": len(trades),
        "profit_factor": pf,
        "sharpe": sharpe,
        "max_drawdown": mdd,
        "total_pnl": sum(pnl),
    }


def objective(trial):
    h = trial.suggest_categorical("holding_days", HOLDINGS)
    v = trial.suggest_categorical("min_volume_ratio", [1.5, 2.0, 2.5])

    m = run(h, v)

    score = m["sharpe"]
    score -= 2 * max(0, 1.10 - m["profit_factor"])
    score -= 0.01 * max(0, 150 - m["trades"])
    score -= 2 * max(0, abs(m["max_drawdown"]) - 0.25)

    trial.set_user_attr("metrics", m)
    return score


def main():
    seed = int(os.getenv("OPTUNA_SEED", "42"))
    storage = os.getenv("OPTUNA_STORAGE", "sqlite:///config/optuna_study.db")

    study = optuna.create_study(
        direction="maximize",
        sampler=TPESampler(seed=seed),
        storage=storage,
        study_name="atr_portfolio_train",
        load_if_exists=True,
    )
    study.optimize(objective, n_trials=N_TRIALS)

    best = study.best_trial
    params = best.params
    metrics = best.user_attrs["metrics"]

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "parameters": params,
        "train_metrics": metrics,
        "score": best.value,
        "run_configuration": {
            "n_trials": N_TRIALS,
            "optuna_seed": seed,
            "optuna_storage": storage,
            "study_name": "atr_portfolio_train",
            "trials": [
                {
                    "number": t.number,
                    "params": t.params,
                    "value": t.value,
                    "metrics": t.user_attrs.get("metrics"),
                }
                for t in study.trials
            ],
            "holding_days_options": HOLDINGS,
            "min_volume_ratio_options": [1.5, 2.0, 2.5],
            "simulation_split": "train",
            "train_end_date": "2025-01-01",
            "initial_cash": 100000.0,
            "cost_rate": 0.005,
            "min_volume_ratio_default": 2.5,
        },
        "notes": [
            "Rezultat train-only; nu este validare out-of-sample.",
            "Drawdown-ul este calculat din equity_curve.",
            "Sharpe-ul este calculat din randamentele pe tranzactie, nu din randamente zilnice."
        ]
    }, indent=2))

    print("BEST:", params)
    print("METRICS:", metrics)
    print("SCORE:", best.value)
    print(f"Salvat: {OUT}")


if __name__ == "__main__":
    main()
