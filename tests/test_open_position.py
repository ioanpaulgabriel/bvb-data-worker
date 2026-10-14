import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from atr_portfolio_simulator import open_position


def test_opens_whole_share_position_and_deducts_cost():
    result = open_position(
        cash=10_000.0,
        symbol="TLV",
        entry_price=50.0,
        position_value=1_000.0,
    )

    assert result["opened"] is True
    assert result["position"]["quantity"] == 20
    assert abs(result["cash"] - (10_000.0 - 1_000.0 - 5.0)) < 0.0001


def test_rejects_position_when_cash_is_insufficient():
    result = open_position(
        cash=500.0,
        symbol="TLV",
        entry_price=50.0,
        position_value=1_000.0,
    )

    assert result["opened"] is False
    assert result["position"] is None
    assert result["cash"] == 500.0


def test_rejects_position_when_value_is_too_small():
    result = open_position(
        cash=10_000.0,
        symbol="TLV",
        entry_price=50.0,
        position_value=10.0,
    )

    assert result["opened"] is False
    assert result["position"] is None
