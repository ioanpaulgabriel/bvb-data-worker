from atr_portfolio_simulator import process_daily_prices


def test_updates_current_price_and_equity():
    position = {
        "symbol": "TLV",
        "quantity": 100,
        "entry_price": 100.0,
        "current_price": 100.0,
    }

    result = process_daily_prices(
        cash=50_000.0,
        positions=[position],
        daily_rows={
            "TLV": {
                "open": 101.0,
                "high": 104.0,
                "low": 100.0,
                "close": 103.0,
            }
        },
    )

    assert result["positions"][0]["current_price"] == 103.0
    assert result["equity"] == 50_000.0 + 100 * 103.0
