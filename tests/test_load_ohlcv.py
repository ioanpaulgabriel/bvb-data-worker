import sys
from datetime import date
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from atr_portfolio_simulator import load_ohlcv


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.query = None
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, query, params):
        self.query = query
        self.params = params

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, rows):
        self.rows = rows
        self.last_cursor = None

    def cursor(self):
        self.last_cursor = FakeCursor(self.rows)
        return self.last_cursor


def test_loads_ohlcv_rows_in_order():
    rows = [
        (
            date(2026, 1, 2),
            10.0,
            11.0,
            9.5,
            10.5,
            1000.0,
        ),
        (
            date(2026, 1, 3),
            10.5,
            12.0,
            10.0,
            11.0,
            1200.0,
        ),
    ]

    connection = FakeConnection(rows)

    result = load_ohlcv(
        connection,
        "TLV",
        date(2026, 1, 1),
        date(2026, 1, 31),
    )

    assert len(result) == 2
    assert result[0]["date"] == date(2026, 1, 2)
    assert result[0]["open"] == 10.0
    assert result[0]["low"] == 9.5
    assert result[1]["close"] == 11.0
    assert result[1]["volume"] == 1200.0


def test_passes_symbol_and_dates_to_query():
    connection = FakeConnection([])
    start = date(2026, 1, 1)
    end = date(2026, 1, 31)

    load_ohlcv(connection, "TLV", start, end)

    assert connection.last_cursor.params == ("TLV", start, end)
