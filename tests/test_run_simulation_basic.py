import sys
from datetime import date
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from atr_portfolio_simulator import run_simulation


def test_runs_with_no_trades_and_no_positions():
    result = run_simulation(
        trades=[],
        ohlcv_by_symbol={
            "TLV": [
                {
                    "date": date(2026, 1, 2),
                    "open": 100.0,
                    "high": 101.0,
                    "low": 99.0,
                    "close": 100.0,
                    "volume": 1000.0,
                }
            ]
        },
    )

    assert result["initial_cash"] == 100_000.0
    assert result["final_cash"] == 100_000.0
    assert result["final_equity"] == 100_000.0
    assert len(result["equity_curve"]) == 1
    assert result["equity_curve"][0]["active_positions"] == 0


def test_creates_equity_curve_for_multiple_dates():
    rows = [
        {
            "date": date(2026, 1, 2),
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "volume": 1000.0,
        },
        {
            "date": date(2026, 1, 3),
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 101.0,
            "volume": 1000.0,
        },
    ]

    result = run_simulation(
        trades=[],
        ohlcv_by_symbol={"TLV": rows},
    )

    assert len(result["equity_curve"]) == 2
    assert result["equity_curve"][0]["date"] == date(2026, 1, 2)
    assert result["equity_curve"][1]["date"] == date(2026, 1, 3)
