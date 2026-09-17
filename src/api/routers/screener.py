"""
Screener API endpoint.

Day 40 - N100 Financial Intelligence Platform
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from src.api.config import get_db_connection


router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_filter(
    value: Optional[float],
    parameter_name: str,
) -> Optional[float]:
    """Validate numeric screener parameters."""

    if value is None:
        return None

    if value < 0:
        raise HTTPException(
            status_code=400,
            detail=f"{parameter_name} cannot be negative",
        )

    return value


def _latest_metric_cte(
    metric_column: str,
    alias: str,
) -> str:
    """
    Build a CTE that returns the latest non-null value for a metric
    independently for each company.
    """

    return f"""
        {alias} AS (
            SELECT fr.company_id, fr.{metric_column} AS value
            FROM financial_ratios fr
            WHERE fr.{metric_column} IS NOT NULL
              AND fr.year = (
                  SELECT MAX(fr2.year)
                  FROM financial_ratios fr2
                  WHERE fr2.company_id = fr.company_id
                    AND fr2.{metric_column} IS NOT NULL
              )
        )
    """


# ---------------------------------------------------------------------------
# Screener
# ---------------------------------------------------------------------------

@router.get("/screener")
def get_screener(
    min_roe: Optional[float] = Query(
        default=None,
        description="Minimum ROE percentage",
    ),
    max_de: Optional[float] = Query(
        default=None,
        description="Maximum debt-to-equity ratio",
    ),
    min_fcf: Optional[float] = Query(
        default=None,
        description="Minimum free cash flow in crore",
    ),
    sector: Optional[str] = Query(
        default=None,
        description="Broad sector",
    ),
    min_rev_cagr_5yr: Optional[float] = Query(
        default=None,
        description="Minimum 5-year revenue CAGR percentage",
    ),
    min_pat_cagr_5yr: Optional[float] = Query(
        default=None,
        description="Minimum 5-year PAT CAGR percentage",
    ),
    max_pe: Optional[float] = Query(
        default=None,
        description="Maximum P/E ratio",
    ),
):
    """
    Return ranked companies matching screener filters.

    The company's latest financial year is reported separately from
    the latest available value of each screener metric. This handles
    cases where the newest financial-ratio row does not contain
    calculated historical metrics.
    """

    min_roe = _validate_filter(min_roe, "min_roe")
    max_de = _validate_filter(max_de, "max_de")
    min_fcf = _validate_filter(min_fcf, "min_fcf")
    min_rev_cagr_5yr = _validate_filter(
        min_rev_cagr_5yr,
        "min_rev_cagr_5yr",
    )
    min_pat_cagr_5yr = _validate_filter(
        min_pat_cagr_5yr,
        "min_pat_cagr_5yr",
    )
    max_pe = _validate_filter(max_pe, "max_pe")

    if sector is not None and not sector.strip():
        raise HTTPException(
            status_code=400,
            detail="sector cannot be empty",
        )

    connection = get_db_connection()

    try:
        sql = f"""
            WITH
            latest_ratio AS (
                SELECT fr.company_id, fr.year
                FROM financial_ratios fr
                WHERE fr.year = (
                    SELECT MAX(fr2.year)
                    FROM financial_ratios fr2
                    WHERE fr2.company_id = fr.company_id
                )
            ),

            {_latest_metric_cte(
                "return_on_equity_pct",
                "latest_roe",
            )}

            ,

            {_latest_metric_cte(
                "free_cash_flow_cr",
                "latest_fcf",
            )}

            ,

            {_latest_metric_cte(
                "revenue_cagr_5yr",
                "latest_rev_cagr",
            )}

            ,

            {_latest_metric_cte(
                "pat_cagr_5yr",
                "latest_pat_cagr",
            )}

            ,

            latest_market_cap AS (
                SELECT mc.company_id, mc.pe_ratio
                FROM market_cap mc
                WHERE mc.year = (
                    SELECT MAX(mc2.year)
                    FROM market_cap mc2
                    WHERE mc2.company_id = mc.company_id
                )
            )

            SELECT
                c.id AS ticker,
                c.company_name,
                s.broad_sector AS sector,
                lr.year,

                roe.value AS roe,
                fr.debt_to_equity AS debt_to_equity,
                fcf.value AS free_cash_flow_cr,
                rev.value AS revenue_cagr_5yr,
                pat.value AS pat_cagr_5yr,

                fr.composite_quality_score AS composite_quality_score,
                mc.pe_ratio AS pe

            FROM companies c

            INNER JOIN latest_ratio lr
                ON lr.company_id = c.id

            INNER JOIN financial_ratios fr
                ON fr.company_id = lr.company_id
                AND fr.year = lr.year

            LEFT JOIN latest_roe roe
                ON roe.company_id = c.id

            LEFT JOIN latest_fcf fcf
                ON fcf.company_id = c.id

            LEFT JOIN latest_rev_cagr rev
                ON rev.company_id = c.id

            LEFT JOIN latest_pat_cagr pat
                ON pat.company_id = c.id

            LEFT JOIN sectors s
                ON s.company_id = c.id

            LEFT JOIN latest_market_cap mc
                ON mc.company_id = c.id

            WHERE 1 = 1
        """

        params = []

        if min_roe is not None:
            sql += " AND roe.value >= ?"
            params.append(min_roe)

        if max_de is not None:
            sql += " AND fr.debt_to_equity <= ?"
            params.append(max_de)

        if min_fcf is not None:
            sql += " AND fcf.value >= ?"
            params.append(min_fcf)

        if sector:
            sql += " AND LOWER(s.broad_sector) = LOWER(?)"
            params.append(sector.strip())

        if min_rev_cagr_5yr is not None:
            sql += " AND rev.value >= ?"
            params.append(min_rev_cagr_5yr)

        if min_pat_cagr_5yr is not None:
            sql += " AND pat.value >= ?"
            params.append(min_pat_cagr_5yr)

        if max_pe is not None:
            sql += """
                AND mc.pe_ratio IS NOT NULL
                AND mc.pe_ratio <= ?
            """
            params.append(max_pe)

        sql += """
            ORDER BY
                fr.composite_quality_score DESC,
                c.id ASC
        """

        rows = connection.execute(sql, params).fetchall()

        companies = []

        for row in rows:
            companies.append({
                "ticker": row["ticker"],
                "company_name": row["company_name"],
                "sector": row["sector"],
                "year": row["year"],
                "roe": row["roe"],
                "debt_to_equity": row["debt_to_equity"],
                "free_cash_flow_cr": row["free_cash_flow_cr"],
                "revenue_cagr_5yr": row["revenue_cagr_5yr"],
                "pat_cagr_5yr": row["pat_cagr_5yr"],
                "pe": row["pe"],
                "composite_quality_score": row[
                    "composite_quality_score"
                ],
            })

        return {
            "count": len(companies),
            "filters": {
                "min_roe": min_roe,
                "max_de": max_de,
                "min_fcf": min_fcf,
                "sector": sector.strip() if sector else None,
                "min_rev_cagr_5yr": min_rev_cagr_5yr,
                "min_pat_cagr_5yr": min_pat_cagr_5yr,
                "max_pe": max_pe,
            },
            "companies": companies,
        }

    finally:
        connection.close()