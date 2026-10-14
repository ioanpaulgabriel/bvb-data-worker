from datetime import date

ATR_MULTIPLIER = 2.0


def calculate_stop_price(entry_price, atr_value):
    return entry_price - atr_value * ATR_MULTIPLIER


def find_stop_date(rows, stop_price):
    for row in rows:
        if row["low"] <= stop_price:
            return row["date"]
    return None


def test_stop_price_uses_two_atr():
    assert calculate_stop_price(100.0, 5.0) == 90.0


def test_finds_first_day_stop_is_hit():
    rows = [
        {"date": date(2026, 1, 2), "low": 95.0},
        {"date": date(2026, 1, 3), "low": 89.0},
        {"date": date(2026, 1, 4), "low": 85.0},
    ]

    assert find_stop_date(rows, 90.0) == date(2026, 1, 3)


def test_returns_none_when_stop_not_hit():
    rows = [
        {"date": date(2026, 1, 2), "low": 95.0},
        {"date": date(2026, 1, 3), "low": 91.0},
    ]

    assert find_stop_date(rows, 90.0) is None
