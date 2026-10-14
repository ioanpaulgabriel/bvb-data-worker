"""Dynamic portfolio metrics generator for BET Overextended Mean Reversion.

Reads trades_history.csv, simulates an intraday stop-loss using daily Low
prices, computes portfolio statistics and writes a JSON snapshot.

No database tables are modified.
"""

from __future__ import annotations

import csv
import json
import os
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv
import psycopg

TRADES_FILE = Path("output/trades_history.csv")
OUTPUT_FILE = Path("/home/bvb/bvb-info/output/portfolio_metrics_history_stop8.json")

STRATEGY_NAME = "bvb_overextended_mean_reversion"
STRATEGY_VERSION = "v1.0_stop8"
STOP_LOSS = 0.08
COST_RATE = 0.005
RISK_PER_TRADE = 0.01


def load_trades() -> list[dict]:
    with TRADES_FILE.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        for row in rows:
            row["entry_date"] = datetime.strptime(row["entry_date"], "%Y-%m-%d").date()
            row["exit_date"] = datetime.strptime(row["exit_date"], "%Y-%m-%d").date()
        return rows


def simulate_trade(rows: list[dict], trade: dict) -> dict:
    entry_price = float(trade["entry_price"])
    stop_price = entry_price * (1 - STOP_LOSS)

    entry_date = trade["entry_date"]
    exit_date = trade["exit_date"]

    holding_rows = [
        r for r in rows
        if entry_date <= r["date"] < exit_date
    ]

    stopped = False
    stop_date = None

    for row in holding_rows:
        if row["low"] <= stop_price:
            stopped = True
            stop_date = row["date"]
            break

    if stopped:
        net_return = -STOP_LOSS
        exit_price = stop_price
        final_exit_date = stop_date
    else:
        exit_price = float(trade["exit_price"])
        gross_return = exit_price / entry_price - 1
        net_return = (1 + gross_return) * (1 - COST_RATE) - 1
        final_exit_date = exit_date

    return {
        "symbol": trade["symbol"],
        "entry_date": entry_date,
        "planned_exit_date": exit_date,
        "actual_exit_date": final_exit_date,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "stopped_out": stopped,
        "net_return": net_return,
    }


def compute_metrics(results: list[dict]) -> dict:
    net_returns = [r["net_return"] for r in results]
    total_trades = len(net_returns)

    if total_trades == 0:
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "average_net_return": 0.0,
            "net_profit_factor": 0.0,
            "max_drawdown": 0.0,
            "final_equity": 1.0,
            "stopped_out_trades": 0,
            "stopped_out_pct": 0.0,
        }

    wins = [r for r in net_returns if r > 0]
    losses = [r for r in net_returns if r <= 0]

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0

    for net_return in net_returns:
        equity *= 1 + net_return
        peak = max(peak, equity)
        max_drawdown = min(max_drawdown, equity / peak - 1)

    return {
        "total_trades": total_trades,
        "win_rate": len(wins) / total_trades,
        "average_net_return": sum(net_returns) / total_trades,
        "net_profit_factor": (
            gross_profit / gross_loss if gross_loss > 0 else 0.0
        ),
        "max_drawdown": max_drawdown,
        "final_equity": equity,
        "stopped_out_trades": sum(1 for r in results if r["stopped_out"]),
        "stopped_out_pct": sum(
            1 for r in results if r["stopped_out"]
        ) / total_trades,
    }


def main() -> None:
    load_dotenv(".env")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is not set")

    trades = load_trades()
    results = []

    with psycopg.connect(database_url) as conn, conn.cursor() as cur:
        for trade in trades:
            cur.execute(
                """
                SELECT trade_date, low
                  FROM historical_ohlcv
                 WHERE symbol = %s
                   AND trade_date >= %s
                   AND trade_date < %s
                   AND low IS NOT NULL
                 ORDER BY trade_date ASC
                """,
                (
                    trade["symbol"],
                    trade["entry_date"],
                    trade["exit_date"],
                ),
            )

            rows = [
                {"date": row[0], "low": float(row[1])}
                for row in cur.fetchall()
            ]

            results.append(simulate_trade(rows, trade))

    metrics = compute_metrics(results)

    payload = {
        "strategy": STRATEGY_NAME,
        "version": STRATEGY_VERSION,
        "generated_at": str(date.today()),
        "configuration": {
            "input_file": str(TRADES_FILE),
            "stop_loss": STOP_LOSS,
            "cost_rate": COST_RATE,
            "risk_per_trade": RISK_PER_TRADE,
            "stop_mode": "intraday_low",
        },
        **metrics,
        "net_returns": [r["net_return"] for r in results],
        "trade_results": results,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    print(f"Metrics written to {OUTPUT_FILE}")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
