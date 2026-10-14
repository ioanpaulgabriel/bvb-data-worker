import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from atr_portfolio_simulator import calculate_equity


def test_equity_is_cash_when_no_positions():
    assert calculate_equity(100_000.0, []) == 100_000.0


def test_equity_includes_position_value():
    positions = [
        {
            "symbol": "TLV",
            "quantity": 100,
            "current_price": 50.0,
        },
        {
            "symbol": "SNP",
            "quantity": 200,
            "current_price": 25.0,
        },
    ]

    assert calculate_equity(90_000.0, positions) == 100_000.0


def test_equity_reflects_price_change():
    positions = [
        {
            "symbol": "TLV",
            "quantity": 100,
            "current_price": 55.0,
        }
    ]

    assert calculate_equity(90_000.0, positions) == 95_500.0
