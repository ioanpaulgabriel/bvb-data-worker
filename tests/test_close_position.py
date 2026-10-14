import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from atr_portfolio_simulator import close_position


def make_positions():
    return [
        {
            "symbol": "TLV",
            "quantity": 20,
            "entry_price": 50.0,
            "current_price": 50.0,
        },
        {
            "symbol": "SNP",
            "quantity": 10,
            "entry_price": 100.0,
            "current_price": 100.0,
        },
    ]


def test_closes_position_and_adds_net_proceeds():
    result = close_position(
        cash=9_000.0,
        positions=make_positions(),
        symbol="TLV",
        exit_price=55.0,
    )

    expected_proceeds = 20 * 55.0 * (1 - 0.005)

    assert result["closed"] is True
    assert abs(result["cash"] - (9_000.0 + expected_proceeds)) < 0.0001
    assert len(result["positions"]) == 1
    assert result["positions"][0]["symbol"] == "SNP"


def test_returns_unchanged_when_symbol_not_found():
    result = close_position(
        cash=9_000.0,
        positions=make_positions(),
        symbol="BRD",
        exit_price=55.0,
    )

    assert result["closed"] is False
    assert result["cash"] == 9_000.0
    assert len(result["positions"]) == 2
    assert result["net_return"] is None
