"""
Company Data API endpoints.

Day 39 - N100 Financial Intelligence Platform
"""

import re
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from src.api.config import get_db_connection


router = APIRouter()


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]
TEARSHEET_DIR = PROJECT_ROOT / "reports" / "tearsheets"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

YEAR_PATTERN = re.compile(r"^\d{4}-\d{2}$")


def validate_year(value: Optional[str], parameter_name: str) -> Optional[str]:
    """Validate YYYY-MM year format."""

    if value is None:
        return None

    if not YEAR_PATTERN.fullmatch(value):
        raise HTTPException(
            status_code=400,
            detail=f"{parameter_name} must be in YYYY-MM format",
        )

    month = int(value[5:7])

    if month < 1 or month > 12:
        raise HTTPException(
            status_code=400,
            detail=f"{parameter_name} must contain a valid month",
        )

    return value


def company_exists(connection, ticker: str) -> bool:
    """Check whether a ticker exists."""

    row = connection.execute(
        """
        SELECT 1
        FROM companies
        WHERE UPPER(id) = UPPER(?)
        LIMIT 1
        """,
        (ticker,),
    ).fetchone()

    return row is not None


def get_company_or_404(connection, ticker: str):
    """Return company row or raise HTTP 404."""

    row = connection.execute(
        """
        SELECT *
        FROM companies
        WHERE UPPER(id) = UPPER(?)
        LIMIT 1
        """,
        (ticker,),
    ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Company '{ticker}' not found",
        )

    return row


def rows_to_dicts(rows):
    """Convert sqlite3.Row objects to dictionaries."""

    return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# GET /companies
# ---------------------------------------------------------------------------

@router.get("/companies")
def get_companies(
    sector: Optional[str] = Query(
        default=None,
        description="Filter by broad sector",
    ),
    market_cap_category: Optional[str] = Query(
        default=None,
        description="Filter by market-cap category",
    ),
    search: Optional[str] = Query(
        default=None,
        description="Partial company name or ticker search",
    ),
):
    """
    Return all companies with summary data.

    Supports optional sector, market-cap category, and
    partial ticker/company-name filters.
    """

    connection = get_db_connection()

    try:
        sql = """
            SELECT
                c.id,
                c.company_name,
                s.broad_sector,
                s.sub_sector,
                c.roe_percentage AS roe_pct,
                c.roce_percentage AS roce_pct
            FROM companies c
            LEFT JOIN sectors s
                ON s.company_id = c.id
            WHERE 1 = 1
        """

        params = []

        if sector:
            sql += """
                AND LOWER(s.broad_sector) = LOWER(?)
            """
            params.append(sector.strip())

        if market_cap_category:
            sql += """
                AND LOWER(s.market_cap_category) = LOWER(?)
            """
            params.append(market_cap_category.strip())

        if search:
            sql += """
                AND (
                    LOWER(c.id) LIKE LOWER(?)
                    OR LOWER(c.company_name) LIKE LOWER(?)
                )
            """
            search_pattern = f"%{search.strip()}%"
            params.extend([search_pattern, search_pattern])

        sql += """
            ORDER BY c.id
        """

        rows = connection.execute(sql, params).fetchall()

        return {
            "count": len(rows),
            "companies": rows_to_dicts(rows),
        }

    finally:
        connection.close()


# ---------------------------------------------------------------------------
# GET /companies/{ticker}
# ---------------------------------------------------------------------------

@router.get("/companies/{ticker}")
def get_company_profile(ticker: str):
    """
    Return the complete company profile, latest KPIs,
    and sector data.
    """

    connection = get_db_connection()

    try:
        company = get_company_or_404(connection, ticker)

        company_id = company["id"]

        # Sector data
        sector = connection.execute(
            """
            SELECT *
            FROM sectors
            WHERE company_id = ?
            LIMIT 1
            """,
            (company_id,),
        ).fetchone()

        # Latest financial-ratio year
        latest_ratio = connection.execute(
            """
            SELECT *
            FROM financial_ratios
            WHERE company_id = ?
            ORDER BY year DESC
            LIMIT 1
            """,
            (company_id,),
        ).fetchone()

        # Latest P&L year
        latest_pl = connection.execute(
            """
            SELECT *
            FROM profitandloss
            WHERE company_id = ?
            ORDER BY year DESC
            LIMIT 1
            """,
            (company_id,),
        ).fetchone()

        # Latest market-cap information
        latest_market_cap = connection.execute(
            """
            SELECT *
            FROM market_cap
            WHERE company_id = ?
            ORDER BY year DESC
            LIMIT 1
            """,
            (company_id,),
        ).fetchone()

        return {
            "id": company_id,
            "company": dict(company),
            "latest_year_kpis": (
                dict(latest_ratio) if latest_ratio else None
            ),
            "latest_profitandloss": (
                dict(latest_pl) if latest_pl else None
            ),
            "latest_market_cap": (
                dict(latest_market_cap)
                if latest_market_cap
                else None
            ),
            "sector": (
                dict(sector)
                if sector
                else None
            ),
        }

    finally:
        connection.close()


# ---------------------------------------------------------------------------
# Financial history helper
# ---------------------------------------------------------------------------

def get_financial_history(
    ticker: str,
    table_name: str,
    from_year: Optional[str],
    to_year: Optional[str],
):
    """Return year-filtered financial history."""

    from_year = validate_year(from_year, "from_year")
    to_year = validate_year(to_year, "to_year")

    if from_year and to_year and from_year > to_year:
        raise HTTPException(
            status_code=400,
            detail="from_year cannot be later than to_year",
        )

    connection = get_db_connection()

    try:
        if not company_exists(connection, ticker):
            raise HTTPException(
                status_code=404,
                detail=f"Company '{ticker}' not found",
            )

        sql = f"""
            SELECT *
            FROM {table_name}
            WHERE company_id = ?
        """

        params = [ticker.upper()]

        if from_year:
            sql += " AND year >= ?"
            params.append(from_year)

        if to_year:
            sql += " AND year <= ?"
            params.append(to_year)

        sql += " ORDER BY year ASC"

        rows = connection.execute(sql, params).fetchall()

        return {
            "ticker": ticker.upper(),
            "history": rows_to_dicts(rows),
        }

    finally:
        connection.close()


# ---------------------------------------------------------------------------
# GET /companies/{ticker}/pl
# ---------------------------------------------------------------------------

@router.get("/companies/{ticker}/pl")
def get_company_profit_and_loss(
    ticker: str,
    from_year: Optional[str] = Query(
        default=None,
        description="Starting financial year in YYYY-MM format",
    ),
    to_year: Optional[str] = Query(
        default=None,
        description="Ending financial year in YYYY-MM format",
    ),
):
    """Return P&L history."""

    return get_financial_history(
        ticker=ticker,
        table_name="profitandloss",
        from_year=from_year,
        to_year=to_year,
    )


# ---------------------------------------------------------------------------
# GET /companies/{ticker}/bs
# ---------------------------------------------------------------------------

@router.get("/companies/{ticker}/bs")
def get_company_balance_sheet(
    ticker: str,
    from_year: Optional[str] = Query(
        default=None,
        description="Starting financial year in YYYY-MM format",
    ),
    to_year: Optional[str] = Query(
        default=None,
        description="Ending financial year in YYYY-MM format",
    ),
):
    """Return balance-sheet history."""

    return get_financial_history(
        ticker=ticker,
        table_name="balancesheet",
        from_year=from_year,
        to_year=to_year,
    )


# ---------------------------------------------------------------------------
# GET /companies/{ticker}/cashflow
# ---------------------------------------------------------------------------

@router.get("/companies/{ticker}/cashflow")
def get_company_cashflow(
    ticker: str,
    from_year: Optional[str] = Query(
        default=None,
        description="Starting financial year in YYYY-MM format",
    ),
    to_year: Optional[str] = Query(
        default=None,
        description="Ending financial year in YYYY-MM format",
    ),
):
    """Return cash-flow history."""

    return get_financial_history(
        ticker=ticker,
        table_name="cashflow",
        from_year=from_year,
        to_year=to_year,
    )


# ---------------------------------------------------------------------------
# GET /companies/{ticker}/ratios
# ---------------------------------------------------------------------------

@router.get("/companies/{ticker}/ratios")
def get_company_ratios(
    ticker: str,
    year: Optional[str] = Query(
        default=None,
        description="Financial year in YYYY-MM format",
    ),
):
    """
    Return computed financial KPIs for every year,
    or a single year when year is supplied.
    """

    year = validate_year(year, "year")

    connection = get_db_connection()

    try:
        if not company_exists(connection, ticker):
            raise HTTPException(
                status_code=404,
                detail=f"Company '{ticker}' not found",
            )

        sql = """
            SELECT *
            FROM financial_ratios
            WHERE company_id = ?
        """

        params = [ticker.upper()]

        if year:
            sql += " AND year = ?"
            params.append(year)

        sql += " ORDER BY year ASC"

        rows = connection.execute(sql, params).fetchall()

        return {
            "ticker": ticker.upper(),
            "year": year,
            "ratios": rows_to_dicts(rows),
        }

    finally:
        connection.close()


# ---------------------------------------------------------------------------
# GET /companies/{ticker}/tearsheet
# ---------------------------------------------------------------------------

@router.get(
    "/companies/{ticker}/tearsheet",
    response_class=FileResponse,
)
def get_company_tearsheet(ticker: str):
    """
    Return the pre-generated company tearsheet PDF.
    """

    ticker = ticker.upper()

    connection = get_db_connection()

    try:
        if not company_exists(connection, ticker):
            raise HTTPException(
                status_code=404,
                detail=f"Company '{ticker}' not found",
            )
    finally:
        connection.close()

    pdf_path = TEARSHEET_DIR / f"{ticker}_tearsheet.pdf"

    if not pdf_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Tearsheet PDF for '{ticker}' not found",
        )

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=f"{ticker}_tearsheet.pdf",
    )