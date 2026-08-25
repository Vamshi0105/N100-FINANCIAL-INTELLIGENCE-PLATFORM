from src.analytics.ratios import (
    net_profit_margin,
    operating_profit_margin,
    return_on_equity,
    return_on_capital_employed,
    return_on_assets,
)


def test_net_profit_margin():
    assert net_profit_margin(200, 1000) == 20.0


def test_net_profit_margin_zero_sales():
    assert net_profit_margin(200, 0) is None


def test_operating_profit_margin():
    assert operating_profit_margin(150, 1000) == 15.0


def test_operating_profit_margin_matches_reported():
    assert operating_profit_margin(150, 1000, 15.0) == 15.0


def test_operating_profit_margin_zero_sales():
    assert operating_profit_margin(150, 0) is None


def test_return_on_equity():
    assert return_on_equity(200, 500, 500) == 20.0


def test_return_on_equity_zero_equity():
    assert return_on_equity(200, 0, 0) is None


def test_return_on_equity_negative_equity():
    assert return_on_equity(200, -600, 500) is None


def test_return_on_capital_employed():
    assert return_on_capital_employed(150, 500, 500, 500) == 10.0


def test_return_on_capital_employed_zero():
    assert return_on_capital_employed(150, 0, 0, 0) is None


def test_return_on_assets():
    assert return_on_assets(200, 2000) == 10.0


def test_return_on_assets_zero_assets():
    assert return_on_assets(200, 0) is None