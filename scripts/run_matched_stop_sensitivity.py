import csv
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from atr_portfolio_simulator import COST_RATE
SIMULATOR = ROOT / "src" / "atr_portfolio_simulator.py"
RUNNER = ROOT / "scripts" / "run_atr_portfolio_simulation.py"

MULTIPLIERS = [2.0, 2.5, 3.0]
RESULTS_PATH = ROOT / "data" / "atr_matched_stop_sensitivity.csv"
INITIAL_CASH = 100_000.0

original = SIMULATOR.read_text()

stop_pattern = re.compile(
    r"^STOP_ATR_MULTIPLIER\s*=\s*[0-9.]+$", re.MULTILINE
)
sizing_pattern = re.compile(
    r"^SIZING_ATR_MULTIPLIER\s*=\s*[0-9.]+$", re.MULTILINE
)

if not stop_pattern.search(original) or not sizing_pattern.search(original):
    raise SystemExit("Nu am gasit parametrii STOP/SIZING.")


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="") as file:
        return list(csv.DictReader(file))


def trade_pnl(row: dict, cost_rate: float) -> float:
    entry_price = float(row["entry_price"])
    exit_price = float(row["exit_price"])
    position_value = float(row["position_value"])
    quantity = position_value / entry_price

    entry_cost = position_value * (1 + cost_rate)
    exit_proceeds = quantity * exit_price * (1 - cost_rate)

    return exit_proceeds - entry_cost


def max_drawdown(rows: list[dict]) -> float:
    peak = float("-inf")
    result = 0.0

    for row in rows:
        equity = float(row["equity"])
        peak = max(peak, equity)
        result = min(result, (equity - peak) / peak)

    return result


def analyze_split(split: str, cost_rate: float) -> dict:
    trades = read_csv(
        ROOT / "data" / f"atr_portfolio_simulation_trades_{split}.csv"
    )
    equity = read_csv(
        ROOT / "data" / f"atr_portfolio_simulation_equity_{split}.csv"
    )

    pnls = [trade_pnl(row, cost_rate) for row in trades]
    wins = [pnl for pnl in pnls if pnl > 0]
    losses = [pnl for pnl in pnls if pnl <= 0]

    stopped = [
        trade_pnl(row, cost_rate)
        for row in trades
        if row["stopped_out"].lower() == "true"
    ]
    normal = [
        trade_pnl(row, cost_rate)
        for row in trades
        if row["stopped_out"].lower() != "true"
    ]

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    final_equity = float(equity[-1]["equity"])

    return {
        "trades": len(trades),
        "final_equity": final_equity,
        "total_pnl": final_equity - INITIAL_CASH,
        "win_rate": len(wins) / len(trades) if trades else 0,
        "profit_factor": gross_profit / gross_loss if gross_loss else float("inf"),
        "stopped_trades": len(stopped),
        "stopped_pnl": sum(stopped),
        "normal_trades": len(normal),
        "normal_pnl": sum(normal),
        "max_drawdown": max_drawdown(equity),
    }


def run_split(split: str) -> dict:
    env = {**os.environ, "SIMULATION_SPLIT": split}
    subprocess.run(
        ["python3", str(RUNNER)],
        check=True,
        cwd=ROOT,
        env=env,
    )
    return analyze_split(split, COST_RATE)


def main() -> None:
    rows = []

    for multiplier in MULTIPLIERS:
        text = stop_pattern.sub(
            f"STOP_ATR_MULTIPLIER = {multiplier}", original, count=1
        )
        text = sizing_pattern.sub(
            f"SIZING_ATR_MULTIPLIER = {multiplier}", text, count=1
        )
        SIMULATOR.write_text(text)

        print(f"\n=== STOP/SIZING ATR = {multiplier} ===")

        train = run_split("train")
        test = run_split("test")

        row = {
            "stop_atr": multiplier,
            "sizing_atr": multiplier,
            "train_trades": train["trades"],
            "train_pnl": train["total_pnl"],
            "train_pf": train["profit_factor"],
            "train_dd": train["max_drawdown"],
            "test_trades": test["trades"],
            "test_pnl": test["total_pnl"],
            "test_pf": test["profit_factor"],
            "test_dd": test["max_drawdown"],
        }
        rows.append(row)

        print(
            f"TRAIN: trades={train['trades']} "
            f"pnl={train['total_pnl']:.2f} "
            f"pf={train['profit_factor']:.2f} "
            f"dd={train['max_drawdown']:.2%}"
        )
        print(
            f"TEST:  trades={test['trades']} "
            f"pnl={test['total_pnl']:.2f} "
            f"pf={test['profit_factor']:.2f} "
            f"dd={test['max_drawdown']:.2%}"
        )

    SIMULATOR.write_text(original)

    fields = list(rows[0].keys())
    with RESULTS_PATH.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nRezultate salvate in: {RESULTS_PATH}")
    print("Baseline-ul a fost restaurat.")


if __name__ == "__main__":
    main()
