"""
Valuation and market-cap API endpoints.

Day 40 - N100 Financial Intelligence Platform
"""

from fastapi import APIRouter, HTTPException

from src.api.config import get_db_connection

router = APIRouter()


@router.get("/market-cap/{ticker}")
def get_market_cap_history(ticker: str):
    """
    Return historical valuation multiples for a company.

    Metrics:
    - Market Cap
    - Enterprise Value
    - P/E
    - P/B
    - EV/EBITDA
    - Dividend Yield

    Historical records are returned for 2019-2024.
    """

    ticker = ticker.strip()

    if not ticker:
        raise HTTPException(
            status_code=404,
            detail="Company not found",
        )

    connection = get_db_connection()

    try:
        # Verify company exists.
        company_row = connection.execute(
            """
            SELECT
                id,
                company_name
            FROM companies
            WHERE LOWER(id) = LOWER(?)
            LIMIT 1
            """,
            (ticker,),
        ).fetchone()

        if company_row is None:
            raise HTTPException(
                status_code=404,
                detail=f"Company '{ticker}' not found",
            )

        actual_ticker = company_row["id"]

        rows = connection.execute(
            """
            SELECT
                year,
                market_cap_crore,
                enterprise_value_crore,
                pe_ratio,
                pb_ratio,
                ev_ebitda,
                dividend_yield_pct
            FROM market_cap
            WHERE LOWER(company_id) = LOWER(?)
              AND year BETWEEN 2019 AND 2024
            ORDER BY year ASC
            """,
            (actual_ticker,),
        ).fetchall()

        history = []

        for row in rows:
            history.append(
                {
                    "year": row["year"],
                    "market_cap_crore": row["market_cap_crore"],
                    "enterprise_value_crore": row["enterprise_value_crore"],
                    "pe": row["pe_ratio"],
                    "pb": row["pb_ratio"],
                    "ev_ebitda": row["ev_ebitda"],
                    "dividend_yield_pct": row["dividend_yield_pct"],
                }
            )

        return {
            "ticker": actual_ticker,
            "company_name": company_row["company_name"],
            "count": len(history),
            "history": history,
        }

    finally:
        connection.close()


@router.get("/valuation")
def get_valuation():
    """
    Basic valuation API status endpoint.
    """

    return {
        "status": "ok",
        "message": "Valuation API available",
    }
