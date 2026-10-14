MAX_TOTAL_EXPOSURE = 1.0
MAX_SYMBOL_EXPOSURE = 0.25


def can_open_position(
    current_total_exposure,
    current_symbol_exposure,
    new_position_exposure,
):
    new_total = current_total_exposure + new_position_exposure
    new_symbol = current_symbol_exposure + new_position_exposure

    return (
        new_total <= MAX_TOTAL_EXPOSURE
        and new_symbol <= MAX_SYMBOL_EXPOSURE
    )


def test_allows_position_within_limits():
    assert can_open_position(0.00, 0.00, 0.10) is True
    assert can_open_position(0.80, 0.10, 0.10) is True


def test_rejects_position_above_total_exposure():
    assert can_open_position(0.95, 0.00, 0.10) is False


def test_rejects_position_above_symbol_exposure():
    assert can_open_position(0.50, 0.20, 0.10) is False
