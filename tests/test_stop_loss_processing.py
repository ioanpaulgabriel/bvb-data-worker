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
