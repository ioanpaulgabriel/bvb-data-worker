COST_RATE = 0.005


def calculate_net_return(entry_price, exit_price):
    gross_return = exit_price / entry_price
    return gross_return * (1 - COST_RATE) * (1 - COST_RATE) - 1


def test_no_profit_when_prices_are_equal():
    result = calculate_net_return(100.0, 100.0)
    expected = (1 - COST_RATE) * (1 - COST_RATE) - 1

    assert abs(result - expected) < 0.0000001


def test_positive_trade_has_costs_applied():
    result = calculate_net_return(100.0, 110.0)
    gross_return = 110.0 / 100.0 - 1

    assert result < gross_return
