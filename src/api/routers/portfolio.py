"""
Portfolio statistics API endpoints.

Day 40 - N100 Financial Intelligence Platform
"""

from statistics import quantiles

from fastapi import APIRouter

from src.api.config import get_db_connection


router = APIRouter()


CORE_METRICS = {
    "roe": "return_on_equity_pct",
    "roce": "return_on_capital_employed_pct",
    "revenue_cagr_5yr": "revenue_cagr_5yr",
    "pat_cagr_5yr": "pat_cagr_5yr",
    "eps_cagr_5yr": "eps_cagr_5yr",
    "free_cash_flow_cr": "free_cash_flow_cr",
    "asset_turnover": "asset_turnover",
    "interest_coverage": "interest_coverage",
    "debt_to_equity": "debt_to_equity",
    "net_profit_margin": "net_profit_margin_pct",
}


def _percentile(values, percentile):
    """
    Calculate an interpolated percentile.

    Uses the same linear interpolation convention as
    numpy.percentile.
    """

    if not values:
        return None

    values = sorted(
        float(value)
        for value in values
        if value is not None
    )

    if not values:
        return None

    if len(values) == 1:
        return round(values[0], 4)

    position = (len(values) - 1) * percentile

    lower_index = int(position)
    upper_index = min(
        lower_index + 1,
        len(values) - 1,
    )

    fraction = position - lower_index

    result = (
        values[lower_index]
        + fraction
        * (
            values[upper_index]
            - values[lower_index]
        )
    )

    return round(result, 4)


def _latest_metric_values(
    connection,
    metric_column,
):
    """
    Return the latest available non-null value for each company.
    """

    rows = connection.execute(
        f"""
        SELECT
            fr.company_id,
            fr.{metric_column} AS value
        FROM financial_ratios fr
        WHERE fr.{metric_column} IS NOT NULL
          AND fr.year = (
              SELECT MAX(fr2.year)
              FROM financial_ratios fr2
              WHERE fr2.company_id = fr.company_id
                AND fr2.{metric_column} IS NOT NULL
          )
        """
    ).fetchall()

    return [
        row["value"]
        for row in rows
        if row["value"] is not None
    ]


@router.get("/portfolio/stats")
def get_portfolio_stats():
    """
    Return P10-P90 percentile statistics for the
    10 core financial KPIs across the N100 universe.
    """

    connection = get_db_connection()

    try:
        percentiles = [
            ("P10", 0.10),
            ("P20", 0.20),
            ("P30", 0.30),
            ("P40", 0.40),
            ("P50", 0.50),
            ("P60", 0.60),
            ("P70", 0.70),
            ("P80", 0.80),
            ("P90", 0.90),
        ]

        statistics = {}

        for metric_name, database_column in CORE_METRICS.items():

            values = _latest_metric_values(
                connection,
                database_column,
            )

            statistics[metric_name] = {
                label: _percentile(
                    values,
                    percentile,
                )
                for label, percentile in percentiles
            }

        return {
            "company_universe": 92,
            "metric_count": len(CORE_METRICS),
            "percentiles": [
                "P10",
                "P20",
                "P30",
                "P40",
                "P50",
                "P60",
                "P70",
                "P80",
                "P90",
            ],
            "statistics": statistics,
        }

    finally:
        connection.close()


@router.get("/portfolio")
def get_portfolio():
    """
    Basic portfolio API status endpoint.
    """

    return {
        "status": "ok",
        "message": "Portfolio API available",
    }