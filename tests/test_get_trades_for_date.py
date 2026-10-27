import sys
from datetime import date
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from atr_portfolio_simulator import get_trades_for_date


def make_trade(symbol, entry_date):
    return {
        "symbol": symbol,
        "entry_date": entry_date,
        "exit_date": date(2026, 1, 10),
        "entry_price": 100.0,
        "exit_price": 105.0,
        "volume_ratio": 3.0,
    }


def test_returns_only_trades_for_requested_date():
    trades = [
        make_trade("TLV", date(2026, 1, 2)),
        make_trade("SNP", date(2026, 1, 2)),
        make_trade("BRD", date(2026, 1, 3)),
    ]

    result = get_trades_for_date(trades, date(2026, 1, 2))

    assert len(result) == 2
    assert result[0]["symbol"] == "TLV"
    assert result[1]["symbol"] == "SNP"


def test_returns_empty_list_when_no_trade_matches():
    trades = [
        make_trade("TLV", date(2026, 1, 2)),
    ]

    result = get_trades_for_date(trades, date(2026, 1, 3))

    assert result == []
