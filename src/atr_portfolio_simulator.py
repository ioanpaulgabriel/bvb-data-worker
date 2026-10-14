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

ATR_MULTIPLIER = 2.0
RISK_PER_TRADE = 0.01


def calculate_position(
    equity: float,
    entry_price: float,
    atr_value: float,
) -> dict:
    stop_distance = atr_value * ATR_MULTIPLIER
    risk_amount = equity * RISK_PER_TRADE
    position_value = risk_amount / (stop_distance / entry_price)
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


def simulate_position(
    entry_price: float,
    atr_value: float,
    rows: list[dict],
    planned_exit_date,
) -> dict:
    stop_price = entry_price - atr_value * ATR_MULTIPLIER
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

    net_return = (
        exit_price / position["entry_price"]
        * (1 - COST_RATE)
        * (1 - COST_RATE)
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
def process_stop_losses(
    cash: float,
    positions: list[dict],
    daily_rows: dict[str, dict],
) -> dict:
    remaining_positions = []
    closed_symbols = []

    for position in positions:
        symbol = position["symbol"]
        row = daily_rows.get(symbol)

        if row is None:
            remaining_positions.append(position)
            continue

        stop_price = (
            position["entry_price"]
            - position["atr_value"] * ATR_MULTIPLIER
        )

        if row["low"] <= stop_price:
            result = close_position(
                cash=cash,
                positions=[position],
                symbol=symbol,
                exit_price=stop_price,
            )

            cash = result["cash"]
            closed_symbols.append(symbol)
            continue

        position["current_price"] = row["close"]
        remaining_positions.append(position)

    return {
        "cash": cash,
        "positions": remaining_positions,
        "closed_symbols": closed_symbols,
    }

def process_stop_losses(
    cash: float,
    positions: list[dict],
    daily_rows: dict[str, dict],
) -> dict:
    remaining_positions = []
    closed_symbols = []

    for position in positions:
        symbol = position["symbol"]
        row = daily_rows.get(symbol)

        if row is None:
            remaining_positions.append(position)
            continue

        stop_price = (
            position["entry_price"]
            - position["atr_value"] * ATR_MULTIPLIER
        )

        if row["low"] <= stop_price:
            result = close_position(
                cash=cash,
                positions=[position],
                symbol=symbol,
                exit_price=stop_price,
            )

            cash = result["cash"]
            closed_symbols.append(symbol)
            continue

        position["current_price"] = row["close"]
        remaining_positions.append(position)

    return {
        "cash": cash,
        "positions": remaining_positions,
        "closed_symbols": closed_symbols,
    }

def process_stop_losses(
    cash: float,
    positions: list[dict],
    daily_rows: dict[str, dict],
) -> dict:
    remaining_positions = []
    closed_symbols = []

    for position in positions:
        symbol = position["symbol"]
        row = daily_rows.get(symbol)

        if row is None:
            remaining_positions.append(position)
            continue

        stop_price = (
            position["entry_price"]
            - position["atr_value"] * ATR_MULTIPLIER
        )

        if row["low"] <= stop_price:
            result = close_position(
                cash=cash,
                positions=[position],
                symbol=symbol,
                exit_price=stop_price,
            )

            cash = result["cash"]
            closed_symbols.append(symbol)
            continue

        position["current_price"] = row["close"]
        remaining_positions.append(position)

    return {
        "cash": cash,
        "positions": remaining_positions,
        "closed_symbols": closed_symbols,
    }

def process_stop_losses(
    cash: float,
    positions: list[dict],
    daily_rows: dict[str, dict],
) -> dict:
    remaining_positions = []
    closed_symbols = []

    for position in positions:
        symbol = position["symbol"]
        row = daily_rows.get(symbol)

        if row is None:
            remaining_positions.append(position)
            continue

        stop_price = (
            position["entry_price"]
            - position["atr_value"] * ATR_MULTIPLIER
        )

        if row["low"] <= stop_price:
            result = close_position(
                cash=cash,
                positions=[position],
                symbol=symbol,
                exit_price=stop_price,
            )

            cash = result["cash"]
            closed_symbols.append(symbol)
            continue

        position["current_price"] = row["close"]
        remaining_positions.append(position)

    return {
        "cash": cash,
        "positions": remaining_positions,
        "closed_symbols": closed_symbols,
    }
def process_stop_losses(
    cash: float,
    positions: list[dict],
    daily_rows: dict[str, dict],
) -> dict:
    remaining_positions = []
    closed_symbols = []

    for position in positions:
        symbol = position["symbol"]
        row = daily_rows.get(symbol)

        if row is None:
            remaining_positions.append(position)
            continue

        stop_price = (
            position["entry_price"]
            - position["atr_value"] * ATR_MULTIPLIER
        )

        if row["low"] <= stop_price:
            result = close_position(
                cash=cash,
                positions=[position],
                symbol=symbol,
                exit_price=stop_price,
            )

            cash = result["cash"]
            closed_symbols.append(symbol)
            continue

        position["current_price"] = row["close"]
        remaining_positions.append(position)

    return {
        "cash": cash,
        "positions": remaining_positions,
        "closed_symbols": closed_symbols,
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


