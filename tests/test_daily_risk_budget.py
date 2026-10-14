DAILY_RISK_BUDGET = 0.02


def can_open_position(current_risk_used, new_position_risk):
    return current_risk_used + new_position_risk <= DAILY_RISK_BUDGET


def test_allows_position_within_budget():
    assert can_open_position(0.00, 0.01) is True
    assert can_open_position(0.01, 0.01) is True


def test_rejects_position_above_budget():
    assert can_open_position(0.015, 0.01) is False
    assert can_open_position(0.02, 0.005) is False
