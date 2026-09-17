"""
Screener API endpoint.

Day 40 - N100 Financial Intelligence Platform
"""

from typing import Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from src.screener.engine import run_screener


router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_filter(
    value: Optional[str],
    parameter_name: str,
) -> Optional[float]:
    """Validate and convert numeric screener parameters."""

    if value is None:
        return None

    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail=f"{parameter_name} must be a valid number",
        )

    if numeric_value < 0:
        raise HTTPException(
            status_code=400,
            detail=f"{parameter_name} cannot be negative",
        )

    return numeric_value


# ---------------------------------------------------------------------------
# Screener
# ---------------------------------------------------------------------------

@router.get("/screener")
def get_screener(
    min_roe: Optional[str] = Query(
        default=None,
        description="Minimum ROE percentage",
    ),
    max_de: Optional[str] = Query(
        default=None,
        description="Maximum debt-to-equity ratio",
    ),
    min_fcf: Optional[str] = Query(
        default=None,
        description="Minimum free cash flow in crore",
    ),
    sector: Optional[str] = Query(
        default=None,
        description="Broad sector",
    ),
    min_rev_cagr_5yr: Optional[str] = Query(
        default=None,
        description="Minimum 5-year revenue CAGR percentage",
    ),
    min_pat_cagr_5yr: Optional[str] = Query(
        default=None,
        description="Minimum 5-year PAT CAGR percentage",
    ),
    max_pe: Optional[str] = Query(
        default=None,
        description="Maximum P/E ratio",
    ),
):
    """
    Return ranked companies matching screener filters.

    The API delegates filtering to the same screener engine used
    by the Streamlit dashboard, ensuring both interfaces use the
    same data-selection and filtering logic.
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

    # Convert API parameter names to the screener engine's filter names.
    filters = {}

    if min_roe is not None:
        filters["return_on_equity_pct_min"] = min_roe

    if max_de is not None:
        filters["debt_to_equity_max"] = max_de

    if min_fcf is not None:
        filters["free_cash_flow_cr_min"] = min_fcf

    if min_rev_cagr_5yr is not None:
        filters["revenue_cagr_5yr_min"] = min_rev_cagr_5yr

    if min_pat_cagr_5yr is not None:
        filters["pat_cagr_5yr_min"] = min_pat_cagr_5yr

    if max_pe is not None:
        filters["pe_ratio_max"] = max_pe

    if sector is not None:
        # Sector is applied after the common screener engine.
        filters["_api_sector"] = sector.strip()

    # Remove the API-only sector key before passing filters to engine.
    engine_filters = {
        key: value
        for key, value in filters.items()
        if key != "_api_sector"
    }

    results = run_screener(filters=engine_filters)

    # Apply sector filter using the same dashboard result DataFrame.
    if sector is not None:
        results = results[
            results["broad_sector"]
            .astype(str)
            .str.lower()
            == sector.strip().lower()
        ]

    companies = []

    for _, row in results.iterrows():
        companies.append({
            "ticker": row.get("company_id"),
            "company_name": (
                None if pd.isna(row.get("name"))
                else row.get("name")
            ),
            "sector": (
                None if pd.isna(row.get("broad_sector"))
                else row.get("broad_sector")
            ),
            "year": (
                None if pd.isna(row.get("year"))
                else row.get("year")
            ),
            "roe": (
                None if pd.isna(row.get("return_on_equity_pct"))
                else row.get("return_on_equity_pct")
            ),
            "debt_to_equity": (
                None if pd.isna(row.get("debt_to_equity"))
                else row.get("debt_to_equity")
            ),
            "free_cash_flow_cr": (
                None if pd.isna(row.get("free_cash_flow_cr"))
                else row.get("free_cash_flow_cr")
            ),
            "revenue_cagr_5yr": (
                None if pd.isna(row.get("revenue_cagr_5yr"))
                else row.get("revenue_cagr_5yr")
            ),
            "pat_cagr_5yr": (
                None if pd.isna(row.get("pat_cagr_5yr"))
                else row.get("pat_cagr_5yr")
            ),
            "pe": (
                None if pd.isna(row.get("pe_ratio"))
                else row.get("pe_ratio")
            ),
            "composite_quality_score": (
                None if pd.isna(row.get("composite_quality_score"))
                else row.get("composite_quality_score")
            ),
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