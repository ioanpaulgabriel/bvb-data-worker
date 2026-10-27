import sys
from datetime import date
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from atr_portfolio_simulator import load_trades


def test_loads_and_sorts_trades(tmp_path):
    csv_file = tmp_path / "trades.csv"

    csv_file.write_text(
        "symbol,entry_date,exit_date,entry_price,exit_price,volume_ratio\n"
        "AQ,2024-12-09,2024-12-16,1.1045,1.1591,3.227678\n"
        "ATB,2022-03-08,2022-03-15,0.532,0.538,1.899412\n",
        encoding="utf-8",
    )

    trades = load_trades(csv_file)

    assert len(trades) == 2
    assert trades[0]["symbol"] == "ATB"
    assert trades[0]["entry_date"] == date(2022, 3, 8)
    assert trades[1]["symbol"] == "AQ"
    assert trades[1]["entry_date"] == date(2024, 12, 9)
    assert trades[0]["entry_price"] == 0.532


def test_parses_numeric_fields(tmp_path):
    csv_file = tmp_path / "trades.csv"

    csv_file.write_text(
        "symbol,entry_date,exit_date,entry_price,exit_price,volume_ratio\n"
        "AQ,2024-12-09,2024-12-16,1.1045,1.1591,3.227678\n",
        encoding="utf-8",
    )

    trade = load_trades(csv_file)[0]

    assert trade["exit_price"] == 1.1591
    assert trade["volume_ratio"] == 3.227678

