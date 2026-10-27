import sys
from datetime import date
from pathlib import Path

import os

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from atr_portfolio_simulator import run_simulation

SIGNALS_PATH = ROOT / "data" / "atr_portfolio_signals.csv"
SPLIT = os.environ.get("SIMULATION_SPLIT", "all").lower()
MIN_VOLUME_RATIO = float(os.environ.get("MIN_VOLUME_RATIO", "2.5"))

if SPLIT not in {"all", "train", "test", "fold"}:
    raise ValueError(
        "SIMULATION_SPLIT trebuie sa fie: all, train, test sau fold."
    )

if SPLIT == "fold":
    required = [
        "TRAIN_START",
        "TRAIN_END",
        "TEST_START",
        "TEST_END",
    ]
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise ValueError(
            "Pentru SIMULATION_SPLIT=fold sunt necesare: "
            + ", ".join(missing)
        )

SPLIT_SUFFIX = "" if SPLIT == "all" else f"_{SPLIT}"

TRADES_PATH = ROOT / "data" / f"atr_portfolio_simulation_trades{SPLIT_SUFFIX}.csv"
EQUITY_PATH = ROOT / "data" / f"atr_portfolio_simulation_equity{SPLIT_SUFFIX}.csv"
HISTORY_DIR = Path(
    os.environ.get("HISTORY_DIR", "data/history")
)


def main():
    if not SIGNALS_PATH.exists():
        raise FileNotFoundError(
            "Rulează mai întâi generate_atr_portfolio_signals.py"
        )

    signals = pd.read_csv(SIGNALS_PATH)
    signals.columns = [column.strip().lower() for column in signals.columns]

    if signals.empty:
        print("Nu există semnale de tranzacționat.")
        print(f"Fișier semnale: {SIGNALS_PATH}")
        return

    signals["entry_date"] = pd.to_datetime(signals["entry_date"]).dt.date
    signals["exit_date"] = pd.to_datetime(signals["exit_date"]).dt.date

    split_start = None
    split_end = None

    if SPLIT == "train":
        split_start = date(2021, 1, 1)
        split_end = date(2025, 1, 1)
        signals = signals[
            (signals["entry_date"] < split_end)
            & (signals["exit_date"] < split_end)
        ]
    elif SPLIT == "test":
        split_start = date(2025, 1, 1)
        split_end = date(2027, 1, 1)
        signals = signals[
            (signals["entry_date"] >= split_start)
            & (signals["exit_date"] >= split_start)
        ]
    elif SPLIT == "fold":
        split_start = date.fromisoformat(os.environ["TEST_START"])
        split_end = date.fromisoformat(os.environ["TEST_END"])
        signals = signals[
            (signals["entry_date"] >= split_start)
            & (signals["exit_date"] < split_end)
        ]

    if "volumeratio" in signals.columns:
        signals = signals.rename(
            columns={"volumeratio": "volume_ratio"}
        )

    ohlcv_by_symbol = {}

    for history_path in sorted(HISTORY_DIR.glob("*_history.csv")):
        history = pd.read_csv(history_path)
        history.columns = [
            column.strip().lower() for column in history.columns
        ]

        history["date"] = pd.to_datetime(history["date"]).dt.date

        if split_start is not None:
            history = history[history["date"] >= split_start]

        if split_end is not None:
            history = history[history["date"] < split_end]

        if history.empty:
            continue

        symbol = history["symbol"].iloc[0]
        rows = []

        for _, row in history.iterrows():
            rows.append(
                {
                    "date": row["date"],
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row["volume"]),
                }
            )

        ohlcv_by_symbol[symbol] = rows

    result = run_simulation(
        trades=signals.to_dict("records"),
        ohlcv_by_symbol=ohlcv_by_symbol,
        min_volume_ratio=MIN_VOLUME_RATIO,
    )

    trades = pd.DataFrame(result["trade_results"])
    equity = pd.DataFrame(result["equity_curve"])

    trades.to_csv(TRADES_PATH, index=False)
    equity.to_csv(EQUITY_PATH, index=False)

    print(f"Split: {SPLIT}")
    print(f"Tranzacții simulate: {len(trades)}")
    print(f"Zile simulate: {len(equity)}")
    final_positions = result.get("final_positions", [])
    unrealized = sum(
        position["quantity"]
        * (position["current_price"] - position["entry_price"])
        for position in final_positions
    )

    print(f"Poziții deschise la final: {len(final_positions)}")
    print(f"P&L nerealizat: {unrealized:.2f} RON")
    print(f"Numerar final: {result['final_cash']:.2f} RON")
    print(f"Equity final: {result['final_equity']:.2f} RON")
    print(f"Raport tranzacții: {TRADES_PATH}")
    print(f"Raport equity: {EQUITY_PATH}")


if __name__ == "__main__":
    main()
