from src.analytics.cashflow_kpis import (
    free_cash_flow,
    capex_intensity,
    fcf_conversion_rate,
    capital_allocation_pattern,
)


def test_cashflow_kpis():
    assert free_cash_flow(
        100,
        -40
    ) == 60

    assert round(
        capex_intensity(-10, 100),
        2
    ) == 10

    assert round(
        fcf_conversion_rate(60, 100),
        2
    ) == 60


def test_capital_allocation():
    result = capital_allocation_pattern(
        100,
        -50,
        -20,
        1.2
    )

    assert result == "Shareholder Returns"