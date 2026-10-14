import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from atr_portfolio_simulator import process_daily_prices


def test_updates_position_prices_and_equity():
    positions = [
        {
            "symbol": "TLV",
            "quantity": 100,
            "entry_price": 50.0,
            "current_price": 50.0,
        }
    ]

    daily_rows = {
        "TLV": {
            "open": 51.0,
            "high": 53.0,
            "low": 50.0,
            "close": 52.0,
        }
    }

    result = process_daily_prices(
        cash=95_000.0,
        positions=positions,
        daily_rows=daily_rows,
    )

    assert result["positions"][0]["current_price"] == 52.0
    assert result["equity"] == 100_200.0


def test_keeps_position_when_daily_row_is_missing():
    positions = [
        {
            "symbol": "TLV",
            "quantity": 100,
            "entry_price": 50.0,
            "current_price": 50.0,
        }
    ]

    result = process_daily_prices(
        cash=95_000.0,
        positions=positions,
        daily_rows={},
    )

    assert result["positions"][0]["current_price"] == 50.0
    assert result["equity"] == 100_000.0
