from src.analytics.cagr import (
    calculate_cagr,
    revenue_cagr,
    pat_cagr,
    eps_cagr,
    calculate_growth_metrics,
)


def test_normal_cagr():
    value, flag = calculate_cagr(100, 150, 3)

    assert value is not None
    assert round(value, 2) == 14.47
    assert flag is None


def test_revenue_cagr():
    value, flag = revenue_cagr(100, 200, 5)

    assert round(value, 2) == 14.87
    assert flag is None


def test_pat_cagr():
    value, flag = pat_cagr(50, 100, 5)

    assert round(value, 2) == 14.87
    assert flag is None


def test_eps_cagr():
    value, flag = eps_cagr(10, 20, 5)

    assert round(value, 2) == 14.87
    assert flag is None


def test_turnaround_flag():
    value, flag = calculate_cagr(-100, 100, 5)

    assert value is None
    assert flag == "TURNAROUND"


def test_decline_to_loss_flag():
    value, flag = calculate_cagr(100, -50, 5)

    assert value is None
    assert flag == "DECLINE_TO_LOSS"


def test_both_negative_flag():
    value, flag = calculate_cagr(-100, -50, 5)

    assert value is None
    assert flag == "BOTH_NEGATIVE"


def test_zero_base_flag():
    value, flag = calculate_cagr(0, 100, 5)

    assert value is None
    assert flag == "ZERO_BASE"


def test_insufficient_data_flag():
    value, flag = calculate_cagr(
        100,
        150,
        5,
        available_years=3,
    )

    assert value is None
    assert flag == "INSUFFICIENT"


def test_growth_metrics_have_separate_flags():
    result = calculate_growth_metrics(
        100,
        150,
        available_years=10,
    )

    assert "cagr_3yr" in result
    assert "cagr_3yr_flag" in result

    assert "cagr_5yr" in result
    assert "cagr_5yr_flag" in result

    assert "cagr_10yr" in result
    assert "cagr_10yr_flag" in result

    assert result["cagr_3yr"] is not None
    assert result["cagr_3yr_flag"] is None