from atr_portfolio_simulator import run_simulation


def make_trade(volume_ratio):
    return {
        "symbol": "TLV",
        "entry_date": "2024-01-20",
        "exit_date": "2024-01-31",
        "entry_price": 100.0,
        "volume_ratio": volume_ratio,
    }


def make_history():
    rows = []

    for day in range(1, 32):
        rows.append(
            {
                "date": f"2024-01-{day:02d}",
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.5,
                "volume": 20_000,
            }
        )

    return {"TLV": rows}


def test_volume_ratio_below_default_is_filtered():
    result = run_simulation(
        trades=[make_trade(1.8)],
        ohlcv_by_symbol=make_history(),
        initial_cash=100_000.0,
    )

    assert result["trade_results"] == []


def test_volume_ratio_parameter_allows_lower_threshold():
    result = run_simulation(
        trades=[make_trade(1.8)],
        ohlcv_by_symbol=make_history(),
        initial_cash=100_000.0,
        min_volume_ratio=1.5,
    )

    assert len(result["trade_results"]) == 1
    assert result["trade_results"][0]["symbol"] == "TLV"
