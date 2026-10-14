import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from atr_portfolio_simulator import calculate_position


def test_position_risk_equals_risk_per_trade():
    result = calculate_position(
        equity=100_000.0,
        entry_price=100.0,
        atr_value=5.0,
    )

    assert abs(result["risk_amount"] - 1_000.0) < 0.0001
    assert abs(result["position_risk"] - 1_000.0) < 0.0001


def test_stop_distance_is_two_atr():
    result = calculate_position(
        equity=100_000.0,
        entry_price=100.0,
        atr_value=5.0,
    )

    assert result["stop_distance"] == 10.0


def test_position_value_is_consistent():
    result = calculate_position(
        equity=100_000.0,
        entry_price=100.0,
        atr_value=5.0,
    )

    expected_position_value = 1_000.0 / (10.0 / 100.0)

    assert abs(result["position_value"] - expected_position_value) < 0.0001
    assert abs(result["position_exposure"] - 0.10) < 0.0001
