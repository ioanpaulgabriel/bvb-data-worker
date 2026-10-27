import sys
from datetime import date
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from atr_portfolio_simulator import simulate_position, STOP_ATR_MULTIPLIER


def make_rows():
    return [
        {
            "date": date(2026, 1, 2),
            "open": 101.0,
            "high": 103.0,
            "low": 99.0,
            "close": 102.0,
        },
        {
            "date": date(2026, 1, 3),
            "open": 102.0,
            "high": 104.0,
            "low": 88.0,
            "close": 90.0,
        },
        {
            "date": date(2026, 1, 6),
            "open": 105.0,
            "high": 106.0,
            "low": 104.0,
            "close": 105.0,
        },
    ]


def test_exit_at_stop_when_low_hits_stop():
    result = simulate_position(
        entry_price=100.0,
        atr_value=5.0,
        rows=make_rows(),
        planned_exit_date=date(2026, 1, 6),
    )

    assert result["stopped_out"] is True
    assert result["actual_exit_date"] == date(2026, 1, 3)
    assert result["exit_price"] == 100.0 - 5.0 * STOP_ATR_MULTIPLIER


def test_exit_at_planned_open_when_stop_not_hit():
    rows = [
        {
            "date": date(2026, 1, 2),
            "open": 101.0,
            "high": 103.0,
            "low": 99.0,
            "close": 102.0,
        },
        {
            "date": date(2026, 1, 6),
            "open": 105.0,
            "high": 106.0,
            "low": 104.0,
            "close": 105.0,
        },
    ]

    result = simulate_position(
        entry_price=100.0,
        atr_value=5.0,
        rows=rows,
        planned_exit_date=date(2026, 1, 6),
    )

    assert result["stopped_out"] is False
    assert result["actual_exit_date"] == date(2026, 1, 6)
    assert result["exit_price"] == 105.0
