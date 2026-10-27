import sys
from datetime import date
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

import atr_portfolio_simulator
from atr_portfolio_simulator import run_simulation


def make_rows():
    rows = []

    for day in range(1, 18):
        rows.append(
            {
                "date": date(2026, 1, day),
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.0,
                "volume": 1000.0,
            }
        )

    return rows


def test_opens_valid_position_on_entry_date():
    trades = [
        {
            "symbol": "TLV",
            "entry_date": date(2026, 1, 17),
            "exit_date": date(2026, 1, 24),
            "entry_price": 100.0,
            "exit_price": 105.0,
            "volume_ratio": 3.0,
        }
    ]

    atr_portfolio_simulator.TREND_FILTER = False

    result = run_simulation(
        trades=trades,
        ohlcv_by_symbol={"TLV": make_rows()},
    )

    assert result["final_cash"] < 100_000.0
    assert result["final_equity"] < 100_000.0
    assert result["final_equity"] > 0
