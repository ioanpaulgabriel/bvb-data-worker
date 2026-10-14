from datetime import date

MAX_ACTIVE_POSITIONS = 5


def can_open_position(active_positions):
    return len(active_positions) < MAX_ACTIVE_POSITIONS


def test_allows_position_when_below_limit():
    assert can_open_position([]) is True
    assert can_open_position(["A", "B", "C", "D"]) is True


def test_rejects_position_when_limit_reached():
    active = ["A", "B", "C", "D", "E"]
    assert can_open_position(active) is False
