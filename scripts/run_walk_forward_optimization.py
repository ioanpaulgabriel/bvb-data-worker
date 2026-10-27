import csv
import itertools
import json
import os
import shutil
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FOLDS_PATH = Path(
    os.environ.get(
        "FOLDS_PATH",
        "config/walk_forward_folds.json",
    )
)
OUTPUT_DIR = Path(
    os.environ.get(
        "OUTPUT_DIR",
        "data/walk_forward",
    )
)
PYTHON = ROOT / ".venv" / "bin" / "python"

HOLDING_DAYS_OPTIONS = [16, 17, 18, 19, 20, 21, 22, 23, 24, 25]
MIN_VOLUME_RATIO_OPTIONS = [1.5, 2.0, 2.5]


def run_command(command, env):
    print("\n" + "-" * 70)
    print(" ".join(command))
    print("-" * 70)
    subprocess.run(command, env=env, check=True)


def evaluate(window_start, window_end, holding_days, min_volume_ratio):
    env = os.environ.copy()
    env["HISTORY_DIR"] = os.environ.get(
        "HISTORY_DIR", "data/history"
    )
    env.update(
        {
            "SIGNAL_START": window_start,
            "SIGNAL_END": window_end,
            "HOLDING_DAYS": str(holding_days),
            "MIN_VOLUME_RATIO": str(min_volume_ratio),
            "SIMULATION_SPLIT": "fold",
            "TRAIN_START": window_start,
            "TRAIN_END": window_end,
            "TEST_START": window_start,
            "TEST_END": window_end,
        }
    )

    run_command(
        [str(PYTHON), str(ROOT / "scripts" / "generate_atr_portfolio_signals.py")],
        env,
    )
    run_command(
        [str(PYTHON), str(ROOT / "scripts" / "run_atr_portfolio_simulation.py")],
        env,
    )

    equity = pd.read_csv(ROOT / "data" / "atr_portfolio_simulation_equity_fold.csv")
    trades = pd.read_csv(ROOT / "data" / "atr_portfolio_simulation_trades_fold.csv")

    initial_equity = float(equity.iloc[0]["equity"])
    final_equity = float(equity.iloc[-1]["equity"])
    total_return = final_equity / initial_equity - 1

    equity_values = pd.to_numeric(equity["equity"], errors="coerce").dropna()
    running_max = equity_values.cummax()
    drawdown = equity_values / running_max - 1
    max_drawdown = float(drawdown.min()) if len(drawdown) else 0.0

    returns = (
        pd.to_numeric(trades["net_return"], errors="coerce").dropna()
        if "net_return" in trades.columns
        else pd.Series(dtype=float)
    )
    gross_profit = float(returns[returns > 0].sum()) if len(returns) else 0.0
    gross_loss = float(-returns[returns < 0].sum()) if len(returns) else 0.0
    profit_factor = (
        gross_profit / gross_loss
        if gross_loss > 0
        else float("inf") if gross_profit > 0 else 0.0
    )

    robust_score = (
        total_return / abs(max_drawdown)
        if max_drawdown < 0
        else 0.0
    )

    return {
        "holding_days": holding_days,
        "min_volume_ratio": min_volume_ratio,
        "trades": len(trades),
        "initial_equity": initial_equity,
        "final_equity": final_equity,
        "total_return": total_return,
        "max_drawdown": max_drawdown,
        "profit_factor": profit_factor,
        "robust_score": robust_score,
    }


def main():
    if not FOLDS_PATH.exists():
        raise FileNotFoundError(f"Nu există {FOLDS_PATH}")

    with FOLDS_PATH.open() as file:
        config = json.load(file)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = []

    for fold in config["folds"]:
        fold_id = fold["fold_id"]
        train_start = fold["train_start"]
        train_end = fold["train_end_exclusive"]
        test_start = fold["test_start"]
        test_end = fold["test_end_exclusive"]

        print(
            f"\n### OPTIMIZARE FOLD {fold_id}: "
            f"train {train_start} -> {train_end}"
        )

        trials = []
        combinations = list(
            itertools.product(
                HOLDING_DAYS_OPTIONS,
                MIN_VOLUME_RATIO_OPTIONS,
            )
        )

        for number, (holding_days, min_volume_ratio) in enumerate(
            combinations, start=1
        ):
            print(
                f"\nFold {fold_id} | trial {number}/{len(combinations)} | "
                f"HOLDING_DAYS={holding_days} | "
                f"MIN_VOLUME_RATIO={min_volume_ratio}"
            )

            result = evaluate(
                train_start,
                train_end,
                holding_days,
                min_volume_ratio,
            )
            result["trial"] = number
            trials.append(result)

        trials_path = OUTPUT_DIR / f"fold_{fold_id}_optimization_trials.csv"
        with trials_path.open("w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(trials[0].keys()))
            writer.writeheader()
            writer.writerows(trials)

        eligible = [trial for trial in trials if trial["trades"] >= 30]
        if not eligible:
            raise ValueError(
                f"Fold {fold_id}: niciun trial nu are minimum 30 de tranzacții."
            )

        best = max(eligible, key=lambda item: item["robust_score"])

        print(
            f"\n### CEL MAI BUN SET PENTRU FOLD {fold_id}: "
            f"HOLDING_DAYS={best['holding_days']}, "
            f"MIN_VOLUME_RATIO={best['min_volume_ratio']}, "
            f"train return={best['total_return']:.2%}, "
            f"train drawdown={best['max_drawdown']:.2%}, "
            f"robust score={best['robust_score']:.2f}"
        )

        print(
            f"\n### EVALUARE TEST FOLD {fold_id}: "
            f"test {test_start} -> {test_end}"
        )
        test_result = evaluate(
            test_start,
            test_end,
            best["holding_days"],
            best["min_volume_ratio"],
        )

        shutil.copy(
            ROOT / "data" / "atr_portfolio_simulation_trades_fold.csv",
            OUTPUT_DIR / f"fold_{fold_id}_trades.csv",
        )
        shutil.copy(
            ROOT / "data" / "atr_portfolio_simulation_equity_fold.csv",
            OUTPUT_DIR / f"fold_{fold_id}_equity.csv",
        )

        best_parameters = {
            "fold_id": fold_id,
            "train_start": train_start,
            "train_end": train_end,
            "test_start": test_start,
            "test_end": test_end,
            "holding_days": best["holding_days"],
            "min_volume_ratio": best["min_volume_ratio"],
            "train_total_return": best["total_return"],
            "train_max_drawdown": best["max_drawdown"],
            "train_profit_factor": best["profit_factor"],
            "train_robust_score": best["robust_score"],
            "test_total_return": test_result["total_return"],
            "test_trades": test_result["trades"],
            "test_final_equity": test_result["final_equity"],
        }

        with (OUTPUT_DIR / f"fold_{fold_id}_best_parameters.json").open(
            "w"
        ) as file:
            json.dump(best_parameters, file, indent=2)

        summary.append(best_parameters)

    summary_path = OUTPUT_DIR / "walk_forward_summary.csv"
    with summary_path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(summary[0].keys()))
        writer.writeheader()
        writer.writerows(summary)

    print("\n### REZULTATE OPTIMIZATE WALK-FORWARD")
    for result in summary:
        print(
            f"Fold {result['fold_id']}: "
            f"HOLDING_DAYS={result['holding_days']}, "
            f"MIN_VOLUME_RATIO={result['min_volume_ratio']}, "
            f"train={result['train_total_return']:.2%}, "
            f"test={result['test_total_return']:.2%}, "
            f"tranzacții test={result['test_trades']}"
        )

    print(f"\nRezultate salvate în: {summary_path}")


if __name__ == "__main__":
    main()
