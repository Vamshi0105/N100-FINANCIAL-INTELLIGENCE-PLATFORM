"""
Company documents API endpoints.

Day 40 - N100 Financial Intelligence Platform
"""

from fastapi import APIRouter, HTTPException

from src.api.config import get_db_connection


router = APIRouter()


def _is_valid_url(url):
    """
    Return True when the supplied value looks like a valid HTTP(S) URL.
    """

    if not url:
        return False

    url = str(url).strip().lower()

    return url.startswith("http://") or url.startswith("https://")


@router.get("/companies/{ticker}/documents")
def get_company_documents(ticker: str):
    """
    Return annual-report links for a company.

    Each document contains:
    - year
    - annual_report
    - is_url_valid
    """

    ticker = ticker.strip()

    if not ticker:
        raise HTTPException(
            status_code=404,
            detail="Company not found",
        )

    connection = get_db_connection()

    try:
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
                annual_report
            FROM documents
            WHERE LOWER(company_id) = LOWER(?)
            ORDER BY year DESC
            """,
            (actual_ticker,),
        ).fetchall()

        documents = []

        for row in rows:
            annual_report = row["annual_report"]

            documents.append({
                "year": row["year"],
                "annual_report": annual_report,
                "is_url_valid": _is_valid_url(
                    annual_report
                ),
            })

        return {
            "ticker": actual_ticker,
            "company_name": company_row["company_name"],
            "count": len(documents),
            "documents": documents,
        }

    finally:
        connection.close()


@router.get("/documents")
def get_documents():
    """
    Basic documents API status endpoint.
    """

    return {
        "status": "ok",
        "message": "Documents API available",
    }