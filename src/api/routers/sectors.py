"""
Sector API endpoints.

Day 40 - N100 Financial Intelligence Platform
"""

from statistics import median

from fastapi import APIRouter, HTTPException

from src.api.config import get_db_connection

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _latest_non_null_metric(
    connection,
    metric_column: str,
) -> dict:
    """
    Return the latest non-null value for a financial-ratio metric
    for each company.
    """

    sql = f"""
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

    rows = connection.execute(sql).fetchall()

    return {row["company_id"]: row["value"] for row in rows}


def _latest_ratio_metric(
    connection,
    metric_column: str,
) -> dict:
    """
    Return the metric from each company's latest financial-ratio row.
    """

    sql = f"""
        SELECT
            fr.company_id,
            fr.{metric_column} AS value
        FROM financial_ratios fr
        WHERE fr.year = (
            SELECT MAX(fr2.year)
            FROM financial_ratios fr2
            WHERE fr2.company_id = fr.company_id
        )
    """

    rows = connection.execute(sql).fetchall()

    return {row["company_id"]: row["value"] for row in rows}


def _latest_pe(connection) -> dict:
    """Return the latest available P/E ratio for each company."""

    rows = connection.execute("""
        SELECT
            mc.company_id,
            mc.pe_ratio
        FROM market_cap mc
        WHERE mc.year = (
            SELECT MAX(mc2.year)
            FROM market_cap mc2
            WHERE mc2.company_id = mc.company_id
        )
        """).fetchall()

    return {row["company_id"]: row["pe_ratio"] for row in rows}


def _median(values):
    """Return median rounded to four decimal places."""

    cleaned = [float(value) for value in values if value is not None]

    if not cleaned:
        return None

    return round(median(cleaned), 4)


# ---------------------------------------------------------------------------
# GET /sectors
# ---------------------------------------------------------------------------


@router.get("/sectors")
def get_sectors():
    """
    Return statistics for all sectors.

    Statistics:
    - company_count
    - median_roe
    - median_pe
    - median_de
    """

    connection = get_db_connection()

    try:
        sector_rows = connection.execute("""
            SELECT
                company_id,
                broad_sector
            FROM sectors
            WHERE broad_sector IS NOT NULL
              AND TRIM(broad_sector) <> ''
            ORDER BY broad_sector, company_id
            """).fetchall()

        # ROE uses latest available non-null value.
        latest_roe = _latest_non_null_metric(
            connection,
            "return_on_equity_pct",
        )

        # D/E uses the latest financial-ratio row.
        latest_de = _latest_ratio_metric(
            connection,
            "debt_to_equity",
        )

        # P/E uses latest market-cap year.
        latest_pe = _latest_pe(connection)

        sector_data = {}

        for row in sector_rows:
            company_id = row["company_id"]
            sector = row["broad_sector"].strip()

            if sector not in sector_data:
                sector_data[sector] = {
                    "company_ids": [],
                    "roe": [],
                    "pe": [],
                    "de": [],
                }

            sector_data[sector]["company_ids"].append(company_id)

            if company_id in latest_roe:
                sector_data[sector]["roe"].append(latest_roe[company_id])

            if company_id in latest_pe:
                sector_data[sector]["pe"].append(latest_pe[company_id])

            if company_id in latest_de:
                sector_data[sector]["de"].append(latest_de[company_id])

        sectors = []

        for sector, data in sorted(sector_data.items()):
            sectors.append(
                {
                    "sector": sector,
                    "company_count": len(data["company_ids"]),
                    "median_roe": _median(data["roe"]),
                    "median_pe": _median(data["pe"]),
                    "median_de": _median(data["de"]),
                }
            )

        return {
            "count": len(sectors),
            "sectors": sectors,
        }

    finally:
        connection.close()


# ---------------------------------------------------------------------------
# GET /sectors/{sector}/companies
# ---------------------------------------------------------------------------


@router.get("/sectors/{sector}/companies")
def get_sector_companies(
    sector: str,
):
    """
    Return all companies belonging to a sector
    with their latest-year KPIs.

    Sector matching is case-insensitive.

    Returns HTTP 404 when the sector does not exist.
    """

    sector = sector.strip()

    if not sector:
        raise HTTPException(
            status_code=404,
            detail="Sector not found",
        )

    connection = get_db_connection()

    try:
        # ---------------------------------------------------------------
        # Verify that the requested sector exists.
        # ---------------------------------------------------------------

        sector_row = connection.execute(
            """
            SELECT DISTINCT
                broad_sector
            FROM sectors
            WHERE LOWER(TRIM(broad_sector)) = LOWER(?)
            LIMIT 1
            """,
            (sector,),
        ).fetchone()

        if sector_row is None:
            raise HTTPException(
                status_code=404,
                detail=f"Sector '{sector}' not found",
            )

        actual_sector = sector_row["broad_sector"]

        # ---------------------------------------------------------------
        # Get latest financial-ratio row for each company.
        # ---------------------------------------------------------------

        rows = connection.execute(
            """
            SELECT
                c.id AS ticker,
                c.company_name,

                s.broad_sector AS sector,
                s.sub_sector,

                fr.year,

                fr.return_on_equity_pct
                    AS roe,

                fr.return_on_capital_employed_pct
                    AS roce,

                fr.return_on_assets_pct
                    AS roa,

                fr.net_profit_margin_pct
                    AS net_profit_margin,

                fr.operating_profit_margin_pct
                    AS operating_profit_margin,

                fr.debt_to_equity,

                fr.interest_coverage,

                fr.free_cash_flow_cr,

                fr.revenue_cagr_5yr,

                fr.pat_cagr_5yr,

                fr.composite_quality_score

            FROM companies c

            INNER JOIN sectors s
                ON s.company_id = c.id

            LEFT JOIN financial_ratios fr
                ON fr.company_id = c.id
                AND fr.year = (
                    SELECT MAX(fr2.year)
                    FROM financial_ratios fr2
                    WHERE fr2.company_id = c.id
                )

            WHERE LOWER(TRIM(s.broad_sector)) = LOWER(?)

            ORDER BY
                fr.composite_quality_score DESC,
                c.id ASC
            """,
            (actual_sector,),
        ).fetchall()

        companies = []

        for row in rows:
            companies.append(
                {
                    "ticker": row["ticker"],
                    "company_name": row["company_name"],
                    "sector": row["sector"],
                    "sub_sector": row["sub_sector"],
                    "year": row["year"],
                    "roe": row["roe"],
                    "roce": row["roce"],
                    "roa": row["roa"],
                    "net_profit_margin": row["net_profit_margin"],
                    "operating_profit_margin": row["operating_profit_margin"],
                    "debt_to_equity": row["debt_to_equity"],
                    "interest_coverage": row["interest_coverage"],
                    "free_cash_flow_cr": row["free_cash_flow_cr"],
                    "revenue_cagr_5yr": row["revenue_cagr_5yr"],
                    "pat_cagr_5yr": row["pat_cagr_5yr"],
                    "composite_quality_score": row["composite_quality_score"],
                }
            )

        return {
            "sector": actual_sector,
            "count": len(companies),
            "companies": companies,
        }

    finally:
        connection.close()
