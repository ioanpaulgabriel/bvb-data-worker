import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from atr_portfolio_simulator import COST_RATE

INITIAL_CASH = 100_000.0
SPLITS = ["train", "test"]
OUTPUT_PATH = ROOT / "data" / "atr_walk_forward_comparison.csv"


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="") as file:
        return list(csv.DictReader(file))


def trade_pnl(row: dict) -> float:
    entry_price = float(row["entry_price"])
    exit_price = float(row["exit_price"])
    position_value = float(row["position_value"])
    quantity = position_value / entry_price

    entry_cost = position_value * (1 + COST_RATE)
    exit_proceeds = quantity * exit_price * (1 - COST_RATE)

    return exit_proceeds - entry_cost


def max_drawdown(equity_rows: list[dict]) -> float:
    peak = float("-inf")
    result = 0.0

    for row in equity_rows:
        equity = float(row["equity"])
        peak = max(peak, equity)
        result = min(result, (equity - peak) / peak)

    return result


def analyze(split: str) -> dict:
    trades = read_csv(
        ROOT / "data" / f"atr_portfolio_simulation_trades_{split}.csv"
    )
    equity = read_csv(
        ROOT / "data" / f"atr_portfolio_simulation_equity_{split}.csv"
    )

    pnls = [trade_pnl(row) for row in trades]
    wins = [pnl for pnl in pnls if pnl > 0]
    losses = [pnl for pnl in pnls if pnl <= 0]

    stopped = [
        trade_pnl(row)
        for row in trades
        if row["stopped_out"].lower() == "true"
    ]
    normal = [
        trade_pnl(row)
        for row in trades
        if row["stopped_out"].lower() != "true"
    ]

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    return {
        "split": split,
        "trades": len(trades),
        "final_equity": float(equity[-1]["equity"]),
        "total_pnl": float(equity[-1]["equity"]) - INITIAL_CASH,
        "total_return": (float(equity[-1]["equity"]) - INITIAL_CASH)
        / INITIAL_CASH,
        "win_rate": len(wins) / len(trades) if trades else 0,
        "profit_factor": gross_profit / gross_loss if gross_loss else float("inf"),
        "stopped_trades": len(stopped),
        "stopped_pnl": sum(stopped),
        "normal_trades": len(normal),
        "normal_pnl": sum(normal),
        "max_drawdown": max_drawdown(equity),
    }


def main() -> None:
    results = [analyze(split) for split in SPLITS]

    fields = list(results[0].keys())

    with OUTPUT_PATH.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)

    print("\nWALK-FORWARD COMPARISON")
    print(f"{'Metric':20} {'Train 2021-2024':>20} {'Test 2025-2026':>20}")

    labels = {
        "trades": "Trades",
        "final_equity": "Final equity",
        "total_pnl": "Total P&L",
        "total_return": "Total return",
        "win_rate": "Win rate",
        "profit_factor": "Profit factor",
        "stopped_trades": "Stopped trades",
        "stopped_pnl": "Stopped P&L",
        "normal_trades": "Normal exits",
        "normal_pnl": "Normal-exit P&L",
        "max_drawdown": "Max drawdown",
    }

    for field in fields[1:]:
        train_value = results[0][field]
        test_value = results[1][field]

        if field in {"total_return", "win_rate", "max_drawdown"}:
            train_value = f"{train_value:.2%}"
            test_value = f"{test_value:.2%}"
        elif field in {"final_equity", "total_pnl", "stopped_pnl", "normal_pnl"}:
            train_value = f"{train_value:,.2f}"
            test_value = f"{test_value:,.2f}"
        elif field == "profit_factor":
            train_value = f"{train_value:.2f}"
            test_value = f"{test_value:.2f}"

        print(f"{labels[field]:20} {train_value:>20} {test_value:>20}")

    print(f"\nRaport salvat: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
