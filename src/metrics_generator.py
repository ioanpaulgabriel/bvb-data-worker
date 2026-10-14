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

ATR_PERIOD = 14
ATR_MULTIPLIER = 2.0


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


def compute_atr(atr_rows: list[dict], period: int) -> float | None:
    """Calculeaza ATR simplu din ultimele `period` True Range-uri."""

    if len(atr_rows) < period + 1:
        return None

    true_ranges = []

    for previous, current in zip(atr_rows[:-1], atr_rows[1:]):
        high = current["high"]
        low = current["low"]
        previous_close = previous["close"]

        true_range = max(
            high - low,
            abs(high - previous_close),
            abs(low - previous_close),
        )
        true_ranges.append(true_range)

    relevant = true_ranges[-period:]
    atr = sum(relevant) / len(relevant)

    return atr if atr > 0 else None


def compute_trade_daily_returns(
    rows: list[dict],
    trade: dict,
    result: dict,
) -> dict:
    entry_price = float(trade["entry_price"])
    entry_date = trade["entry_date"]
    actual_exit_date = result["actual_exit_date"]
    exit_price = result["exit_price"]

    series = [
        r for r in rows
        if entry_date <= r["date"] <= actual_exit_date
    ]

    daily_returns = {}
    previous_close = entry_price

    for row in series:
        current_date = row["date"]
        close_price = row["close"]

        if current_date == actual_exit_date:
            end_price = exit_price
        else:
            end_price = close_price

        daily_returns[current_date] = end_price / previous_close - 1
        previous_close = close_price

    return daily_returns


def compute_daily_portfolio(
    results: list[dict],
    daily_returns_by_trade: list[dict],
) -> tuple[list[dict], float]:
    all_dates = sorted(
        {
            current_date
            for trade_returns in daily_returns_by_trade
            for current_date in trade_returns
        }
    )

    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    curve = []

    for current_date in all_dates:
        active_returns = [
            trade_returns[current_date]
            for trade_returns in daily_returns_by_trade
            if current_date in trade_returns
        ]

        if active_returns:
            portfolio_return = sum(active_returns) / len(active_returns)
        else:
            portfolio_return = 0.0

        equity *= 1 + portfolio_return
        peak = max(peak, equity)
        drawdown = equity / peak - 1
        max_drawdown = min(max_drawdown, drawdown)

        curve.append(
            {
                "date": current_date,
                "active_trades": len(active_returns),
                "portfolio_return": portfolio_return,
                "equity": equity,
                "drawdown": drawdown,
            }
        )

    return curve, max_drawdown


def compute_atr_daily_portfolio(
    daily_returns_by_trade: list[dict],
    allocation_weights: list[float | None],
) -> tuple[list[dict], float]:
    """Equity curve ponderat ATR, cu greutati normalizate zilnic."""

    valid_trades = [
        (returns, weight)
        for returns, weight in zip(daily_returns_by_trade, allocation_weights)
        if weight is not None and weight > 0
    ]

    all_dates = sorted(
        {
            current_date
            for trade_returns, _ in valid_trades
            for current_date in trade_returns
        }
    )

    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    curve = []

    for current_date in all_dates:
        weighted_returns = []
        total_weight = 0.0

        for trade_returns, weight in valid_trades:
            if current_date not in trade_returns:
                continue

            weighted_returns.append(weight * trade_returns[current_date])
            total_weight += weight

        if total_weight > 0:
            portfolio_return = sum(weighted_returns) / total_weight
            active_trades = len(weighted_returns)
        else:
            portfolio_return = 0.0
            active_trades = 0

        equity *= 1 + portfolio_return
        peak = max(peak, equity)
        drawdown = equity / peak - 1
        max_drawdown = min(max_drawdown, drawdown)

        curve.append(
            {
                "date": current_date,
                "active_trades": active_trades,
                "portfolio_return": portfolio_return,
                "equity": equity,
                "drawdown": drawdown,
            }
        )

    return curve, max_drawdown


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
    daily_returns_by_trade = []
    atr_trade_metrics = []
    allocation_weights = []

    sequential_equity = 1.0

    with psycopg.connect(database_url) as conn, conn.cursor() as cur:
        for trade in trades:
            cur.execute(
                """
                SELECT trade_date, low, close
                  FROM historical_ohlcv
                 WHERE symbol = %s
                   AND trade_date >= %s
                   AND trade_date <= %s
                   AND low IS NOT NULL
                   AND close IS NOT NULL
                 ORDER BY trade_date ASC
                """,
                (
                    trade["symbol"],
                    trade["entry_date"],
                    trade["exit_date"],
                ),
            )

            rows = [
                {
                    "date": row[0],
                    "low": float(row[1]),
                    "close": float(row[2]),
                }
                for row in cur.fetchall()
            ]

            result = simulate_trade(rows, trade)
            results.append(result)

            daily_returns_by_trade.append(
                compute_trade_daily_returns(rows, trade, result)
            )

            cur.execute(
                """
                SELECT trade_date, high, low, close
                  FROM historical_ohlcv
                 WHERE symbol = %s
                   AND trade_date < %s
                   AND high IS NOT NULL
                   AND low IS NOT NULL
                   AND close IS NOT NULL
                 ORDER BY trade_date DESC
                 LIMIT %s
                """,
                (
                    trade["symbol"],
                    trade["entry_date"],
                    ATR_PERIOD + 1,
                ),
            )

            atr_rows = [
                {
                    "date": row[0],
                    "high": float(row[1]),
                    "low": float(row[2]),
                    "close": float(row[3]),
                }
                for row in reversed(cur.fetchall())
            ]

            atr_value = compute_atr(atr_rows, ATR_PERIOD)
            entry_price = float(trade["entry_price"])

            if atr_value is None:
                allocation_weight = None
                stop_distance = None
                risk_amount = None
                position_size = None
                position_value = None
            else:
                stop_distance = atr_value * ATR_MULTIPLIER
                risk_amount = sequential_equity * RISK_PER_TRADE
                position_size = risk_amount / stop_distance
                position_value = position_size * entry_price
                position_value = min(position_value, sequential_equity)
                allocation_weight = position_value / sequential_equity

            atr_trade_metrics.append(
                {
                    "symbol": trade["symbol"],
                    "entry_date": trade["entry_date"],
                    "atr_value": atr_value,
                    "stop_distance": stop_distance,
                    "risk_amount": risk_amount,
                    "position_size": position_size,
                    "position_value": position_value,
                    "allocation_weight": allocation_weight,
                }
            )

            allocation_weights.append(allocation_weight)
            sequential_equity *= 1 + result["net_return"]

    metrics = compute_metrics(results)

    daily_equity_curve, portfolio_max_drawdown_daily = compute_daily_portfolio(
        results,
        daily_returns_by_trade,
    )

    atr_equity_curve, atr_portfolio_max_drawdown_daily = (
        compute_atr_daily_portfolio(
            daily_returns_by_trade,
            allocation_weights,
        )
    )

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
            "daily_portfolio_model": "equal_weight_active_positions",
            "atr_period": ATR_PERIOD,
            "atr_multiplier": ATR_MULTIPLIER,
            "atr_sizing_model": "risk_targeted_dynamic_weight",
        },
        **metrics,
        "portfolio_max_drawdown_daily": portfolio_max_drawdown_daily,
        "atr_portfolio_max_drawdown_daily": atr_portfolio_max_drawdown_daily,
        "net_returns": [r["net_return"] for r in results],
        "trade_results": results,
        "daily_equity_curve": daily_equity_curve,
        "atr_trade_metrics": atr_trade_metrics,
        "atr_dynamic_equity_curve": atr_equity_curve,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    print(f"Metrics written to {OUTPUT_FILE}")
    print(json.dumps(metrics, indent=2))
    print(
        json.dumps(
            {
                "portfolio_max_drawdown_daily": portfolio_max_drawdown_daily,
                "atr_portfolio_max_drawdown_daily": atr_portfolio_max_drawdown_daily,
                "daily_equity_points": len(daily_equity_curve),
                "atr_dynamic_equity_points": len(atr_equity_curve),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
