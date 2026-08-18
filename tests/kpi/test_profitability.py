from src.analytics.ratios import (
    net_profit_margin,
    operating_profit_margin,
    cross_check_opm,
    return_on_equity,
    return_on_capital_employed,
    return_on_assets,
)


def test_net_profit_margin_normal():
    assert net_profit_margin(20, 100) == 20


def test_net_profit_margin_zero_sales():
    assert net_profit_margin(20, 0) is None


def test_operating_profit_margin():
    assert operating_profit_margin(30, 100) == 30


def test_opm_cross_check_mismatch():
    computed = operating_profit_margin(30, 100)

    assert cross_check_opm(
        computed,
        25,
        tolerance=1
    ) is True


def test_roe_normal():
    assert return_on_equity(
        20,
        50,
        50
    ) == 20


def test_roe_negative_equity():
    assert return_on_equity(
        20,
        50,
        -60
    ) is None


def test_roce_normal():
    assert return_on_capital_employed(
        30,
        50,
        50,
        100
    ) == 15


def test_roa_zero_assets():
    assert return_on_assets(
        20,
        0
    ) is None