from src.analytics.ratios import (
    debt_to_equity,
    high_leverage_flag,
    interest_coverage_ratio,
    interest_coverage_label,
    interest_coverage_warning,
    net_debt,
    asset_turnover,
)


def test_debt_free_returns_zero():
    assert debt_to_equity(
        0,
        100,
        50
    ) == 0


def test_debt_to_equity_normal():
    assert debt_to_equity(
        100,
        100,
        100
    ) == 0.5


def test_interest_zero_returns_none():
    assert interest_coverage_ratio(
        100,
        20,
        0
    ) is None


def test_icr_debt_free_label():
    icr = interest_coverage_ratio(
        100,
        20,
        0
    )

    assert interest_coverage_label(icr) == "Debt Free"


def test_high_debt_flag():
    assert high_leverage_flag(
        6,
        "Technology"
    ) is True




def test_icr_warning():
    assert interest_coverage_warning(1.2) is True


