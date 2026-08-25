from src.analytics.leverage import (
    debt_to_equity,
    high_leverage_flag,
    interest_coverage_ratio,
    icr_label,
    icr_warning_flag,
    net_debt,
    asset_turnover,
)


def test_debt_to_equity():
    assert debt_to_equity(500, 500, 500) == 0.5


def test_debt_to_equity_debt_free_returns_zero():
    assert debt_to_equity(0, 500, 500) == 0


def test_high_leverage_flag():
    assert high_leverage_flag(6, "Manufacturing") is True


def test_high_leverage_financials_not_flagged():
    assert high_leverage_flag(6, "Financials") is False


def test_interest_coverage_interest_zero_returns_none():
    assert interest_coverage_ratio(100, 20, 0) is None


def test_icr_label_debt_free():
    icr = interest_coverage_ratio(100, 20, 0)
    assert icr_label(icr) == "Debt Free"


def test_icr_warning_flag():
    assert icr_warning_flag(1.2) is True


def test_net_debt_and_asset_turnover():
    assert net_debt(1000, 300) == 700
    assert asset_turnover(2000, 1000) == 2.0