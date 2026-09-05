import pandas as pd

from src.analytics.peer import (
    calculate_peer_percentiles,
    get_peer_group_for_company,
)


def test_higher_value_gets_higher_percentile():

    ratios = pd.DataFrame(
        {
            "company_id": [
                "AAA",
                "BBB",
                "CCC",
            ],
            "year": [
                2025,
                2025,
                2025,
            ],
            "return_on_equity_pct": [
                10.0,
                20.0,
                30.0,
            ],
            "return_on_capital_employed_pct": [
                10.0,
                20.0,
                30.0,
            ],
            "net_profit_margin_pct": [
                10.0,
                20.0,
                30.0,
            ],
            "debt_to_equity": [
                3.0,
                2.0,
                1.0,
            ],
            "free_cash_flow_cr": [
                100.0,
                200.0,
                300.0,
            ],
            "pat_cagr_5yr": [
                5.0,
                10.0,
                15.0,
            ],
            "revenue_cagr_5yr": [
                5.0,
                10.0,
                15.0,
            ],
            "eps_cagr_5yr": [
                5.0,
                10.0,
                15.0,
            ],
            "interest_coverage": [
                2.0,
                4.0,
                8.0,
            ],
            "asset_turnover": [
                1.0,
                2.0,
                3.0,
            ],
        }
    )

    peers = pd.DataFrame(
        {
            "company_id": [
                "AAA",
                "BBB",
                "CCC",
            ],
            "peer_group_name": [
                "Test Group",
                "Test Group",
                "Test Group",
            ],
        }
    )

    result = calculate_peer_percentiles(
        ratios,
        peers,
    )

    roe = result[
        result["metric"] == "ROE"
    ].sort_values("value")

    assert list(
        roe["percentile_rank"]
    ) == [0.0, 0.5, 1.0]


def test_debt_to_equity_is_inverted():

    ratios = pd.DataFrame(
        {
            "company_id": [
                "AAA",
                "BBB",
                "CCC",
            ],
            "year": [
                2025,
                2025,
                2025,
            ],
            "return_on_equity_pct": [
                1.0,
                1.0,
                1.0,
            ],
            "return_on_capital_employed_pct": [
                1.0,
                1.0,
                1.0,
            ],
            "net_profit_margin_pct": [
                1.0,
                1.0,
                1.0,
            ],
            "debt_to_equity": [
                3.0,
                2.0,
                1.0,
            ],
            "free_cash_flow_cr": [
                1.0,
                1.0,
                1.0,
            ],
            "pat_cagr_5yr": [
                1.0,
                1.0,
                1.0,
            ],
            "revenue_cagr_5yr": [
                1.0,
                1.0,
                1.0,
            ],
            "eps_cagr_5yr": [
                1.0,
                1.0,
                1.0,
            ],
            "interest_coverage": [
                1.0,
                1.0,
                1.0,
            ],
            "asset_turnover": [
                1.0,
                1.0,
                1.0,
            ],
        }
    )

    peers = pd.DataFrame(
        {
            "company_id": [
                "AAA",
                "BBB",
                "CCC",
            ],
            "peer_group_name": [
                "Test Group",
                "Test Group",
                "Test Group",
            ],
        }
    )

    result = calculate_peer_percentiles(
        ratios,
        peers,
    )

    debt = result[
        result["metric"] == "D/E"
    ].sort_values(
        "value",
        ascending=False,
    )

    assert list(
        debt["percentile_rank"]
    ) == [0.0, 0.5, 1.0]


def test_company_without_peer_group():

    peers = pd.DataFrame(
        {
            "company_id": [
                "AAA",
            ],
            "peer_group_name": [
                "Test Group",
            ],
        }
    )

    result = get_peer_group_for_company(
        "ZZZ",
        peers,
    )

    assert result == "No peer group assigned"