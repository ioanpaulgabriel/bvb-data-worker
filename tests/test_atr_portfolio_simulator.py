import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from atr_portfolio_simulator import can_open_position


def test_allows_valid_position():
    assert can_open_position(
        active_positions=2,
        current_total_exposure=0.40,
        current_symbol_exposure=0.10,
        new_position_exposure=0.10,
        current_risk_used=0.01,
        new_position_risk=0.005,
    ) is True


def test_rejects_when_position_limit_reached():
    assert can_open_position(
        active_positions=5,
        current_total_exposure=0.40,
        current_symbol_exposure=0.10,
        new_position_exposure=0.10,
        current_risk_used=0.01,
        new_position_risk=0.005,
    ) is False


def test_rejects_when_total_exposure_exceeded():
    assert can_open_position(
        active_positions=2,
        current_total_exposure=0.95,
        current_symbol_exposure=0.10,
        new_position_exposure=0.10,
        current_risk_used=0.01,
        new_position_risk=0.005,
    ) is False


def test_rejects_when_symbol_exposure_exceeded():
    assert can_open_position(
        active_positions=2,
        current_total_exposure=0.40,
        current_symbol_exposure=0.20,
        new_position_exposure=0.10,
        current_risk_used=0.01,
        new_position_risk=0.005,
    ) is False


def test_rejects_when_daily_risk_exceeded():
    assert can_open_position(
        active_positions=2,
        current_total_exposure=0.40,
        current_symbol_exposure=0.10,
        new_position_exposure=0.10,
        current_risk_used=0.015,
        new_position_risk=0.01,
    ) is False
