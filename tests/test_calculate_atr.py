import sys
from datetime import date
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from atr_portfolio_simulator import calculate_atr


def make_rows():
    rows = []

    for day in range(1, 17):
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


def test_returns_none_when_not_enough_rows():
    assert calculate_atr([], 14) is None
    assert calculate_atr(make_rows()[:10], 14) is None


def test_calculates_average_true_range():
    rows = make_rows()

    atr = calculate_atr(rows, 14)

    assert atr is not None
    assert abs(atr - 2.0) < 0.0001
