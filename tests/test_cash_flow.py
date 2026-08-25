from src.analytics.cash_flow import (
    free_cash_flow,
    cfo_quality_score,
    capex_intensity,
    fcf_conversion_rate,
    capital_allocation_pattern,
)


def test_free_cash_flow():
    assert free_cash_flow(1000, -300) == 700


def test_free_cash_flow_can_be_negative():
    assert free_cash_flow(100, -500) == -400


def test_cfo_quality_high():
    score, label = cfo_quality_score(
        [120, 110, 130, 125, 115],
        [100, 100, 100, 100, 100],
    )

    assert score == 1.2
    assert label == "High Quality"


def test_cfo_quality_moderate():
    score, label = cfo_quality_score(
        [70, 60, 80, 75, 65],
        [100, 100, 100, 100, 100],
    )

    assert score == 0.7
    assert label == "Moderate"


def test_cfo_quality_accrual_risk():
    score, label = cfo_quality_score(
        [30, 40, 20, 35, 25],
        [100, 100, 100, 100, 100],
    )

    assert score == 0.3
    assert label == "Accrual Risk"


def test_cfo_quality_pat_zero():
    score, label = cfo_quality_score(
        [100, 100, 100, 100, 100],
        [100, 0, 100, 100, 100],
    )

    assert score is None
    assert label is None


def test_capex_intensity_asset_light():
    intensity, label = capex_intensity(-20, 1000)

    assert intensity == 2.0
    assert label == "Asset Light"


def test_capex_intensity_moderate():
    intensity, label = capex_intensity(-50, 1000)

    assert intensity == 5.0
    assert label == "Moderate"


def test_capex_intensity_capital_intensive():
    intensity, label = capex_intensity(-100, 1000)

    assert intensity == 10.0
    assert label == "Capital Intensive"


def test_fcf_conversion_rate():
    assert fcf_conversion_rate(200, 400) == 50.0


def test_fcf_conversion_zero_operating_profit():
    assert fcf_conversion_rate(200, 0) is None


def test_reinvestor_pattern():
    assert (
        capital_allocation_pattern(100, -50, -25)
        == "Reinvestor"
    )


def test_shareholder_returns_pattern():
    assert (
        capital_allocation_pattern(
            100,
            -50,
            -25,
            cfo_pat_ratio=1.5,
        )
        == "Shareholder Returns"
    )


def test_liquidating_assets_pattern():
    assert (
        capital_allocation_pattern(100, 50, -25)
        == "Liquidating Assets"
    )


def test_distress_signal_pattern():
    assert (
        capital_allocation_pattern(-100, 50, 25)
        == "Distress Signal"
    )


def test_growth_funded_by_debt_pattern():
    assert (
        capital_allocation_pattern(-100, -50, 25)
        == "Growth Funded by Debt"
    )


def test_cash_accumulator_pattern():
    assert (
        capital_allocation_pattern(100, 50, 25)
        == "Cash Accumulator"
    )


def test_pre_revenue_pattern():
    assert (
        capital_allocation_pattern(-100, -50, -25)
        == "Pre-Revenue"
    )


def test_mixed_pattern():
    assert (
        capital_allocation_pattern(100, -50, 25)
        == "Mixed"
    )