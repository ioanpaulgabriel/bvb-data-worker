import csv
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDS_PATH = Path(
    os.environ.get(
        "FOLDS_PATH",
        "config/walk_forward_folds.json",
    )
)
RESULTS_PATH = Path(
    os.environ.get(
        "RESULTS_PATH",
        "data/walk_forward_results.csv",
    )
)

HOLDING_DAYS = os.environ.get("HOLDING_DAYS", "16")
MIN_VOLUME_RATIO = os.environ.get("MIN_VOLUME_RATIO", "2.0")


def run_command(command, env):
    print("\n" + "=" * 70)
    print(" ".join(command))
    print("=" * 70)
    subprocess.run(command, env=env, check=True)


def main():
    if not FOLDS_PATH.exists():
        raise FileNotFoundError(f"Nu există {FOLDS_PATH}")

    with FOLDS_PATH.open() as file:
        config = json.load(file)

    folds = config["folds"]
    results = []

    for index, fold in enumerate(folds, start=1):
        train_start = fold["train_start"]
        train_end = fold["train_end_exclusive"]
        test_start = fold["test_start"]
        test_end = fold["test_end_exclusive"]

        print(
            f"\n### FOLD {index}/{len(folds)}: "
            f"train {train_start} -> {train_end}, "
            f"test {test_start} -> {test_end}"
        )

        env = os.environ.copy()
        env.update(
            {
                "SIGNAL_START": test_start,
                "SIGNAL_END": test_end,
                "HOLDING_DAYS": HOLDING_DAYS,
                "MIN_VOLUME_RATIO": MIN_VOLUME_RATIO,
                "SIMULATION_SPLIT": "fold",
                "TRAIN_START": train_start,
                "TRAIN_END": train_end,
                "TEST_START": test_start,
                "TEST_END": test_end,
            }
        )

        run_command(
            [
                str(ROOT / ".venv" / "bin" / "python"),
                str(ROOT / "scripts" / "generate_atr_portfolio_signals.py"),
            ],
            env,
        )

        run_command(
            [
                str(ROOT / ".venv" / "bin" / "python"),
                str(ROOT / "scripts" / "run_atr_portfolio_simulation.py"),
            ],
            env,
        )

        trades_path = ROOT / "data" / "atr_portfolio_simulation_trades_fold.csv"
        equity_path = ROOT / "data" / "atr_portfolio_simulation_equity_fold.csv"

        import pandas as pd

        trades = pd.read_csv(trades_path)
        equity = pd.read_csv(equity_path)

        final_equity = float(equity.iloc[-1]["equity"])
        initial_equity = float(equity.iloc[0]["equity"])
        total_return = final_equity / initial_equity - 1

        returns = (
            pd.to_numeric(trades["net_return"], errors="coerce")
            .dropna()
            if "net_return" in trades.columns
            else pd.Series(dtype=float)
        )

        win_rate = float((returns > 0).mean()) if len(returns) else None
        average_trade_return = float(returns.mean()) if len(returns) else None

        gross_profit = float(returns[returns > 0].sum()) if len(returns) else 0.0
        gross_loss = float(-returns[returns < 0].sum()) if len(returns) else 0.0
        profit_factor = (
            gross_profit / gross_loss
            if gross_loss > 0
            else float("inf") if gross_profit > 0 else None
        )

        equity_values = pd.to_numeric(
            equity["equity"], errors="coerce"
        ).dropna()
        running_max = equity_values.cummax()
        drawdown = equity_values / running_max - 1
        max_drawdown = float(drawdown.min()) if len(drawdown) else None

        results.append(
            {
                "fold": fold.get("fold_id", index),
                "train_start": train_start,
                "train_end": train_end,
                "test_start": test_start,
                "test_end": test_end,
                "trades": len(trades),
                "initial_equity": initial_equity,
                "final_equity": final_equity,
                "total_return": total_return,
                "win_rate": win_rate,
                "average_trade_return": average_trade_return,
                "profit_factor": profit_factor,
                "max_drawdown": max_drawdown,
            }
        )

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RESULTS_PATH.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    print("\n### REZULTATE WALK-FORWARD")
    for result in results:
        print(
            f"Fold {result['fold']}: "
            f"tranzacții={result['trades']}, "
            f"equity final={result['final_equity']:.2f} RON, "
            f"return={result['total_return']:.2%}, "
            f"win rate={result['win_rate']:.2%}, "
            f"profit factor={result['profit_factor']}, "
            f"max drawdown={result['max_drawdown']:.2%}"
        )

    print(f"\nRezultate salvate în: {RESULTS_PATH}")


if __name__ == "__main__":
    main()
