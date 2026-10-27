from __future__ import annotations

MAX_TOTAL_EXPOSURE = 1.0
MAX_SYMBOL_EXPOSURE = 0.25
MAX_ACTIVE_POSITIONS = 5
DAILY_RISK_BUDGET = 0.02


def can_open_position(
    active_positions: int,
    current_total_exposure: float,
    current_symbol_exposure: float,
    new_position_exposure: float,
    current_risk_used: float,
    new_position_risk: float,
) -> bool:
    if active_positions >= MAX_ACTIVE_POSITIONS:
        return False

    if current_total_exposure + new_position_exposure > MAX_TOTAL_EXPOSURE:
        return False

    if current_symbol_exposure + new_position_exposure > MAX_SYMBOL_EXPOSURE:
        return False

    if current_risk_used + new_position_risk > DAILY_RISK_BUDGET:
        return False

    return True

import os

import os

ATR_MULTIPLIER = 1.5
STOP_ATR_MULTIPLIER = float(
    os.getenv("STOP_ATR_MULTIPLIER", "2.0")
)
SIZING_ATR_MULTIPLIER = float(
    os.getenv("SIZING_ATR_MULTIPLIER", "2.0")
)
RISK_PER_TRADE = 0.01
DRAWDOWN_THROTTLE_THRESHOLD = float(
    os.getenv("DRAWDOWN_THROTTLE_THRESHOLD", "0")
)
DRAWDOWN_THROTTLE_FACTOR = float(
    os.getenv("DRAWDOWN_THROTTLE_FACTOR", "0.5")
)


def calculate_position(
    equity: float,
    entry_price: float,
    atr_value: float,
    risk_per_trade: float = RISK_PER_TRADE,
) -> dict:
    stop_distance = atr_value * SIZING_ATR_MULTIPLIER
    risk_amount = equity * risk_per_trade
    position_value = risk_amount / (stop_distance / entry_price)

    max_position_value = equity * MAX_SYMBOL_EXPOSURE
    position_value = min(position_value, max_position_value)

    position_exposure = position_value / equity
    position_risk = (
        position_value * stop_distance / entry_price
    )

    return {
        "stop_distance": stop_distance,
        "risk_amount": risk_amount,
        "position_value": position_value,
        "position_exposure": position_exposure,
        "position_risk": position_risk,
    }

COST_RATE = 0.005
MIN_VOLUME_RATIO = float(
    os.getenv("MIN_VOLUME_RATIO", "2.5")
)
TREND_FILTER = False
import os
USE_STOP_LOSS = (
    os.getenv("USE_STOP_LOSS", "false").strip().lower()
    in {"1", "true", "yes", "on"}
)
HOLDING_DAYS = int(os.getenv("HOLDING_DAYS", "8"))
TREND_SMA_PERIOD = 200


def simulate_position(
    entry_price: float,
    atr_value: float,
    rows: list[dict],
    planned_exit_date,
) -> dict:
    stop_price = entry_price - atr_value * STOP_ATR_MULTIPLIER
    stop_date = None

    for row in rows:
        if row["date"] > planned_exit_date:
            break

        if row["low"] <= stop_price:
            stop_date = row["date"]
            break

    if stop_date is not None:
        exit_price = stop_price
        actual_exit_date = stop_date
    else:
        exit_row = next(
            row for row in rows if row["date"] == planned_exit_date
        )
        exit_price = exit_row["open"]
        actual_exit_date = planned_exit_date

    net_return = (
        exit_price / entry_price
        * (1 - COST_RATE)
        * (1 - COST_RATE)
        - 1
    )

    return {
        "stop_price": stop_price,
        "stopped_out": stop_date is not None,
        "actual_exit_date": actual_exit_date,
        "exit_price": exit_price,
        "net_return": net_return,
    }

def calculate_equity(cash: float, positions: list[dict]) -> float:
    return cash + sum(
        position["quantity"] * position["current_price"]
        for position in positions
    )

import math


def open_position(
    cash: float,
    symbol: str,
    entry_price: float,
    position_value: float,
) -> dict:
    quantity = math.floor(position_value / entry_price)

    if quantity <= 0:
        return {
            "opened": False,
            "cash": cash,
            "position": None,
        }

    gross_cost = quantity * entry_price
    commission = gross_cost * COST_RATE
    total_cost = gross_cost + commission

    if total_cost > cash:
        return {
            "opened": False,
            "cash": cash,
            "position": None,
        }

    position = {
        "symbol": symbol,
        "quantity": quantity,
        "entry_price": entry_price,
        "current_price": entry_price,
    }

    return {
        "opened": True,
        "cash": cash - total_cost,
        "position": position,
    }

def process_stop_losses(
    cash: float,
    positions: list[dict],
    daily_rows: dict[str, dict],
) -> dict:
    remaining_positions = []
    closed_symbols = []
    closed_trades = []

    for position in positions:
        symbol = position["symbol"]
        row = daily_rows.get(symbol)

        if row is None:
            remaining_positions.append(position)
            continue

        stop_price = (
            position["entry_price"]
            - position["atr_value"] * STOP_ATR_MULTIPLIER
        )

        if row["low"] <= stop_price:
            execution_price = min(row["open"], stop_price)
            result = close_position(
                cash=cash,
                positions=[position],
                symbol=symbol,
                exit_price=execution_price,
            )

            cash = result["cash"]
            closed_symbols.append(symbol)
            closed_trades.append(
                {
                    "symbol": symbol,
                    "entry_date": position.get("entry_date"),
                    "exit_date": None,
                    "entry_price": position["entry_price"],
                    "exit_price": execution_price,
                    "position_value": position["quantity"]
                    * position["entry_price"],
                    "net_return": result["net_return"],
                    "stopped_out": True,
                }
            )
            continue

        position["current_price"] = row["close"]
        remaining_positions.append(position)

    return {
        "cash": cash,
        "positions": remaining_positions,
        "closed_symbols": closed_symbols,
        "closed_trades": closed_trades,
    }

def close_position(
    cash: float,
    positions: list[dict],
    symbol: str,
    exit_price: float,
) -> dict:
    position = next(
        (p for p in positions if p["symbol"] == symbol),
        None,
    )

    if position is None:
        return {
            "closed": False,
            "cash": cash,
            "positions": positions,
            "net_return": None,
        }

    gross_proceeds = position["quantity"] * exit_price
    commission = gross_proceeds * COST_RATE
    net_proceeds = gross_proceeds - commission

    entry_cost = position["quantity"] * position["entry_price"]
    entry_commission = entry_cost * COST_RATE

    net_return = (
        net_proceeds / (entry_cost + entry_commission)
        - 1
    )

    remaining_positions = [
        p for p in positions if p["symbol"] != symbol
    ]

    return {
        "closed": True,
        "cash": cash + net_proceeds,
        "positions": remaining_positions,
        "net_return": net_return,
    }

def process_daily_prices(
    cash: float,
    positions: list[dict],
    daily_rows: dict[str, dict],
) -> dict:
    updated_positions = []
    closed_symbols = []

    for position in positions:
        symbol = position["symbol"]
        row = daily_rows.get(symbol)

        if row is None:
            updated_positions.append(position)
            continue

        position["current_price"] = row["close"]
        updated_positions.append(position)

    equity = calculate_equity(cash, updated_positions)

    return {
        "cash": cash,
        "positions": updated_positions,
        "closed_symbols": closed_symbols,
        "equity": equity,
    }
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from atr_portfolio_simulator import process_stop_losses


def make_position():
    return {
        "symbol": "TLV",
        "quantity": 100,
        "entry_price": 100.0,
        "atr_value": 5.0,
        "current_price": 100.0,
    }


def test_closes_position_when_low_hits_stop():
    position = make_position()
    daily_rows = {
        "TLV": {
            "open": 99.0,
            "high": 100.0,
            "low": 89.0,
            "close": 90.0,
        }
    }

    result = process_stop_losses(
        cash=90_000.0,
        positions=[position],
        daily_rows=daily_rows,
    )

    assert result["closed_symbols"] == ["TLV"]
    assert result["positions"] == []
    assert result["cash"] > 90_000.0


def test_keeps_position_when_stop_not_hit():
    position = make_position()
    daily_rows = {
        "TLV": {
            "open": 99.0,
            "high": 100.0,
            "low": 95.0,
            "close": 98.0,
        }
    }

    result = process_stop_losses(
        cash=90_000.0,
        positions=[position],
        daily_rows=daily_rows,
    )

    assert result["closed_symbols"] == []
    assert len(result["positions"]) == 1
    assert result["positions"][0]["current_price"] == 98.0

import csv
from datetime import datetime
from pathlib import Path


def load_trades(trades_file: str | Path) -> list[dict]:
    trades = []

    with Path(trades_file).open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            trades.append(
                {
                    "symbol": row["symbol"],
                    "entry_date": datetime.strptime(
                        row["entry_date"], "%Y-%m-%d"
                    ).date(),
                    "exit_date": datetime.strptime(
                        row["exit_date"], "%Y-%m-%d"
                    ).date(),
                    "entry_price": float(row["entry_price"]),
                    "exit_price": float(row["exit_price"]),
                    "volume_ratio": float(row["volume_ratio"]),
                }
            )

    trades.sort(
        key=lambda trade: (
            trade["entry_date"],
            trade["symbol"],
        )
    )

    return trades

import os

import psycopg
from dotenv import load_dotenv


def load_ohlcv(
    connection,
    symbol: str,
    start_date,
    end_date,
) -> list[dict]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT trade_date, open, high, low, close, volume
              FROM historical_ohlcv
             WHERE symbol = %s
               AND trade_date >= %s
               AND trade_date <= %s
               AND open IS NOT NULL
               AND high IS NOT NULL
               AND low IS NOT NULL
               AND close IS NOT NULL
               AND volume IS NOT NULL
             ORDER BY trade_date ASC
            """,
            (symbol, start_date, end_date),
        )

        return [
            {
                "date": row[0],
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
            }
            for row in cursor.fetchall()
        ]

ATR_PERIOD = 14


def calculate_atr(rows: list[dict], period: int = ATR_PERIOD) -> float | None:
    if len(rows) < period + 1:
        return None

    true_ranges = []

    for previous, current in zip(rows[:-1], rows[1:]):
        true_range = max(
            current["high"] - current["low"],
            abs(current["high"] - previous["close"]),
            abs(current["low"] - previous["close"]),
        )
        true_ranges.append(true_range)

    relevant = true_ranges[-period:]
    atr = sum(relevant) / len(relevant)

    return atr if atr > 0 else None

def get_trades_for_date(trades: list[dict], current_date) -> list[dict]:
    return [
        trade
        for trade in trades
        if trade["entry_date"] == current_date
    ]

def get_all_trading_dates(
    ohlcv_by_symbol: dict[str, list[dict]],
) -> list:
    dates = {
        row["date"]
        for rows in ohlcv_by_symbol.values()
        for row in rows
    }

    return sorted(dates)


def run_simulation(
    trades: list[dict],
    ohlcv_by_symbol: dict[str, list[dict]],
    initial_cash: float = 100_000.0,
    min_volume_ratio: float = MIN_VOLUME_RATIO,
) -> dict:
    cash = initial_cash
    positions = []
    equity_curve = []
    trade_results = []
    total_entry_cost = 0.0
    total_exit_proceeds = 0.0

    trades = [
        trade
        for trade in trades
        if trade.get("volume_ratio", 0) >= min_volume_ratio
    ]

    for current_date in get_all_trading_dates(ohlcv_by_symbol):
        daily_rows = {}

        for symbol, rows in ohlcv_by_symbol.items():
            row = next(
                (r for r in rows if r["date"] == current_date),
                None,
            )

            if row is not None:
                daily_rows[symbol] = row

        cash_before_stop = cash

        if USE_STOP_LOSS:
            stop_result = process_stop_losses(
                cash=cash,
                positions=positions,
                daily_rows=daily_rows,
            )
        else:
            stop_result = {
                "cash": cash,
                "positions": positions,
                "closed_symbols": [],
                "closed_trades": [],
            }

        cash = stop_result["cash"]
        stop_exit_proceeds = cash - cash_before_stop

        if stop_exit_proceeds > 0:
            total_exit_proceeds += stop_exit_proceeds

        for stopped_trade in stop_result["closed_trades"]:
            stopped_trade["exit_date"] = current_date
            trade_results.append(stopped_trade)
        positions = stop_result["positions"]
        remaining_positions = []

        for position in positions:
            if current_date < position["planned_exit_date"]:
                remaining_positions.append(position)
                continue

            row = daily_rows.get(position["symbol"])

            if row is None:
                remaining_positions.append(position)
                continue

            close_result = close_position(
                cash=cash,
                positions=[position],
                symbol=position["symbol"],
                exit_price=row["open"],
            )

            total_exit_proceeds += (
                position["quantity"] * row["open"]
                * (1 - COST_RATE)
            )



            cash = close_result["cash"]
            trade_results.append(
                {
                    "symbol": position["symbol"],
                    "entry_date": position.get("entry_date"),
                    "exit_date": current_date,
                    "entry_price": position["entry_price"],
                    "exit_price": row["open"],
                    "position_value": position["quantity"] * position["entry_price"],
                    "net_return": close_result["net_return"],
                    "stopped_out": False,
                }
            )

        positions = remaining_positions

        price_result = process_daily_prices(
            cash=cash,
            positions=positions,
            daily_rows=daily_rows,
        )
        positions = price_result["positions"]

        for trade in get_trades_for_date(trades, current_date):
            symbol = trade["symbol"]
            rows = ohlcv_by_symbol.get(symbol, [])

            prior_rows = [
                row for row in rows if row["date"] < current_date
            ]

            atr_value = calculate_atr(prior_rows)

            if atr_value is None:
                continue

            if TREND_FILTER:
                closes = [row["close"] for row in prior_rows]

                if len(closes) < TREND_SMA_PERIOD:
                    continue

                sma = sum(closes[-TREND_SMA_PERIOD:]) / TREND_SMA_PERIOD

                if closes[-1] <= sma:
                    continue

            equity_before_entry = calculate_equity(cash, positions)

            if equity_curve:
                peak_equity = max(
                    item["equity"] for item in equity_curve
                )
                current_equity = equity_curve[-1]["equity"]
                current_drawdown = (
                    current_equity / peak_equity - 1
                    if peak_equity > 0
                    else 0.0
                )
            else:
                current_drawdown = 0.0

            effective_risk_per_trade = RISK_PER_TRADE
            if (
                DRAWDOWN_THROTTLE_THRESHOLD > 0
                and current_drawdown <= -DRAWDOWN_THROTTLE_THRESHOLD
            ):
                effective_risk_per_trade = (
                    RISK_PER_TRADE * DRAWDOWN_THROTTLE_FACTOR
                )

            sizing = calculate_position(
                equity=equity_before_entry,
                entry_price=trade["entry_price"],
                atr_value=atr_value,
                risk_per_trade=effective_risk_per_trade,
            )

            current_total_exposure = sum(
                position["quantity"] * position["current_price"]
                for position in positions
            ) / equity_before_entry

            current_symbol_exposure = sum(
                position["quantity"] * position["current_price"]
                for position in positions
                if position["symbol"] == symbol
            ) / equity_before_entry

            if not can_open_position(
                active_positions=len(positions),
                current_total_exposure=current_total_exposure,
                current_symbol_exposure=current_symbol_exposure,
                new_position_exposure=sizing["position_exposure"],
                current_risk_used=(
                    sum(
                        position.get("risk_amount", 0.0)
                        for position in positions
                    )
                    / equity_before_entry
                ),
                new_position_risk=sizing["position_risk"]
                / equity_before_entry,
            ):
                continue

            entry_result = open_position(
                cash=cash,
                symbol=symbol,
                entry_price=trade["entry_price"],
                position_value=sizing["position_value"],
            )

            if not entry_result["opened"]:
                continue

            cash = entry_result["cash"]
            position = entry_result["position"]
            total_entry_cost += (
                position["quantity"]
                * position["entry_price"]
                * (1 + COST_RATE)
            )
            position["atr_value"] = atr_value
            position["risk_amount"] = sizing["position_risk"]
            position["entry_date"] = trade["entry_date"]
            position["planned_exit_date"] = trade["exit_date"]
            positions.append(position)

        equity = calculate_equity(cash, positions)

        equity_curve.append(
            {
                "date": current_date,
                "cash": cash,
                "equity": equity,
                "active_positions": len(positions),
            }
        )

    expected_final_cash = (
        initial_cash
        - total_entry_cost
        + total_exit_proceeds
    )

    reconciliation_difference = abs(cash - expected_final_cash)

    if reconciliation_difference > 0.01:
        raise AssertionError(
            "Cash reconciliation failed: "
            f"expected={expected_final_cash:.2f}, "
            f"actual={cash:.2f}, "
            f"difference={reconciliation_difference:.2f}"
        )

    print(
        f"RECONCILIATION entry_cost={total_entry_cost:.2f} "
        f"exit_proceeds={total_exit_proceeds:.2f} "
        f"expected_final={expected_final_cash:.2f} "
        f"actual_final={cash:.2f} "
        f"difference={reconciliation_difference:.6f}"
    )

    return {
        "initial_cash": initial_cash,
        "final_cash": cash,
        "final_positions": positions,
        "final_equity": calculate_equity(cash, positions),
        "equity_curve": equity_curve,
        "trade_results": trade_results,
    }
