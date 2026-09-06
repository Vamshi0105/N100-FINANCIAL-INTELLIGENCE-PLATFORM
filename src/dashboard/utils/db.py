"""
Shared SQLite database access functions for the Streamlit dashboard.
"""

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


DATABASE_PATH = Path("data/nifty100.db")


def _query_database(query, params=None):
    """
    Execute a SQL query and return the result as a pandas DataFrame.
    """

    connection = sqlite3.connect(DATABASE_PATH)

    try:
        dataframe = pd.read_sql_query(
            query,
            connection,
            params=params,
        )
    finally:
        connection.close()

    return dataframe


@st.cache_data(ttl=600)
def get_companies():
    """
    Return all companies available in the database.
    """

    query = """
    SELECT
        c.id AS company_id,
        c.company_name,
        s.broad_sector,
        s.sub_sector
    FROM companies c
    LEFT JOIN sectors s
        ON c.id = s.company_id
    ORDER BY c.id
    """

    return _query_database(query)


@st.cache_data(ttl=600)
def get_company_profile(ticker: str) -> pd.DataFrame:
    """
    Return company profile and sector information.
    """

    query = """
    SELECT
        c.id AS company_id,
        c.company_name,
        c.company_logo,
        c.chart_link,
        c.about_company,
        c.website,
        c.nse_profile,
        c.bse_profile,
        c.face_value,
        c.book_value,
        s.broad_sector,
        s.sub_sector
    FROM companies c
    LEFT JOIN sectors s
        ON c.id = s.company_id
    WHERE UPPER(c.id) = UPPER(?)
    """

    return _query_database(query, params=(ticker,))


@st.cache_data(ttl=600)
def get_pros_cons(ticker: str) -> pd.DataFrame:
    """
    Get pros and cons for a company.
    """

    query = """
    SELECT
        company_id,
        pros,
        cons
    FROM prosandcons
    WHERE UPPER(company_id) = UPPER(?)
    """

    return _query_database(query, (ticker,))


@st.cache_data(ttl=600)
def get_available_years():
    """
    Return all available annual financial years.

    Only March-ending years are included because they represent
    the main annual reporting period for the dashboard.
    """

    query = """
    SELECT DISTINCT year
    FROM financial_ratios
    WHERE year IS NOT NULL
      AND CAST(SUBSTR(year, 1, 4) AS INTEGER) BETWEEN 2019 AND 2024
      AND year LIKE '%-03'
    ORDER BY year
    """

    dataframe = _query_database(query)
    return dataframe["year"].dropna().astype(str).tolist()


@st.cache_data(ttl=600)
def get_home_metrics(year=None):
    """
    Return summary KPI metrics for the Home dashboard.

    Metrics:
    - Average ROE
    - Median P/E
    - Median Debt-to-Equity
    - Total Companies
    - Median Revenue CAGR 5Y
    - Debt-Free Companies
    """

    if year is None:
        year = "2024-03"

    query = """
    SELECT
        r.company_id,
        r.return_on_equity_pct,
        r.debt_to_equity,
        r.revenue_cagr_5yr,
        m.pe_ratio
    FROM financial_ratios r
    LEFT JOIN market_cap m
        ON r.company_id = m.company_id
        AND CAST(SUBSTR(r.year, 1, 4) AS INTEGER) = m.year
    WHERE r.year = ?
    """

    dataframe = _query_database(
        query,
        params=(year,),
    )

    if dataframe.empty:
        return {
            "average_roe": None,
            "median_pe": None,
            "median_debt_to_equity": None,
            "total_companies": 0,
            "median_revenue_cagr_5yr": None,
            "debt_free_companies": 0,
        }

    return {
        "average_roe": dataframe["return_on_equity_pct"].mean(),
        "median_pe": dataframe["pe_ratio"].median(),
        "median_debt_to_equity": dataframe[
            "debt_to_equity"
        ].median(),
        "total_companies": dataframe["company_id"].nunique(),
        "median_revenue_cagr_5yr": dataframe[
            "revenue_cagr_5yr"
        ].median(),
        "debt_free_companies": dataframe[
            dataframe["debt_to_equity"].fillna(float("inf"))
            <= 0.000001
        ]["company_id"].nunique(),
    }


@st.cache_data(ttl=600)
def get_sector_breakdown(year):
    """
    Return company count by broad sector.
    """

    query = """
    SELECT
        s.broad_sector,
        COUNT(DISTINCT r.company_id) AS company_count
    FROM financial_ratios r
    LEFT JOIN sectors s
        ON r.company_id = s.company_id
    WHERE r.year = ?
    GROUP BY s.broad_sector
    ORDER BY company_count DESC
    """

    return _query_database(query, params=(year,))


@st.cache_data(ttl=600)
def get_top_companies(year):
    """
    Calculate and return top 5 companies by composite quality score.
    """

    from src.screener.scoring import calculate_composite_quality_score

    query = """
    SELECT
        r.*,
        c.company_name,
        s.broad_sector
    FROM financial_ratios r
    LEFT JOIN companies c
        ON r.company_id = c.id
    LEFT JOIN sectors s
        ON r.company_id = s.company_id
    WHERE r.year = ?
    """

    dataframe = _query_database(query, params=(year,))

    if dataframe.empty:
        return dataframe

    dataframe = calculate_composite_quality_score(dataframe)

    columns = [
        "company_id",
        "company_name",
        "broad_sector",
        "composite_quality_score",
        "return_on_equity_pct",
        "debt_to_equity",
    ]

    columns = [column for column in columns if column in dataframe.columns]

    return dataframe.sort_values(
        "composite_quality_score",
        ascending=False,
    ).head(5)[columns]


@st.cache_data(ttl=600)
def get_ratios(ticker, year=None):
    """
    Return financial ratios for a company.

    If year is None, returns all available years.
    """

    if year is None:

        query = """
        SELECT *
        FROM financial_ratios
        WHERE company_id = ?
        ORDER BY year
        """

        return _query_database(
            query,
            params=(ticker,),
        )

    query = """
    SELECT *
    FROM financial_ratios
    WHERE company_id = ?
      AND year = ?
    """

    return _query_database(
        query,
        params=(ticker, year),
    )


@st.cache_data(ttl=600)
def get_pl(ticker):
    """
    Return Profit & Loss history for a company.
    """

    query = """
    SELECT *
    FROM profitandloss
    WHERE company_id = ?
    ORDER BY year
    """

    return _query_database(
        query,
        params=(ticker,),
    )


@st.cache_data(ttl=600)
def get_bs(ticker):
    """
    Return Balance Sheet history for a company.
    """

    query = """
    SELECT *
    FROM balancesheet
    WHERE company_id = ?
    ORDER BY year
    """

    return _query_database(
        query,
        params=(ticker,),
    )


@st.cache_data(ttl=600)
def get_cf(ticker):
    """
    Return Cash Flow history for a company.
    """

    query = """
    SELECT *
    FROM cashflow
    WHERE company_id = ?
    ORDER BY year
    """

    return _query_database(
        query,
        params=(ticker,),
    )


@st.cache_data(ttl=600)
def get_sectors():
    """
    Return sector information for all companies.
    """

    query = """
    SELECT
        company_id,
        broad_sector,
        sub_sector
    FROM sectors
    ORDER BY broad_sector, company_id
    """

    return _query_database(query)


@st.cache_data(ttl=600)
def get_peers(group_name):
    """
    Return companies belonging to a peer group.

    Also includes the latest available financial ratios.
    """

    query = """
    SELECT
        pg.company_id,
        pg.peer_group_name,
        c.company_name,
        r.year,
        r.return_on_equity_pct,
        r.return_on_capital_employed_pct,
        r.net_profit_margin_pct,
        r.debt_to_equity,
        r.free_cash_flow_cr,
        r.revenue_cagr_5yr,
        r.pat_cagr_5yr,
        r.eps_cagr_5yr,
        r.interest_coverage,
        r.asset_turnover,
        r.composite_quality_score
    FROM peer_groups pg

    LEFT JOIN companies c
        ON pg.company_id = c.company_id

    LEFT JOIN financial_ratios r
        ON pg.company_id = r.company_id
        AND r.year = (
            SELECT MAX(r2.year)
            FROM financial_ratios r2
            WHERE r2.company_id = pg.company_id
        )

    WHERE pg.peer_group_name = ?

    ORDER BY pg.company_id
    """

    return _query_database(
        query,
        params=(group_name,),
    )


@st.cache_data(ttl=600)
def get_valuation(ticker):
    """
    Return valuation information for a company.

    This function is prepared for the valuation module.
    """

    query = """
    SELECT *
    FROM valuation
    WHERE company_id = ?
    ORDER BY year DESC
    """

    try:
        return _query_database(
            query,
            params=(ticker,),
        )

    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=600)
def get_company_profile_ratios(ticker: str) -> pd.DataFrame:
    """
    Get historical financial ratios for a company.
    """

    query = """
    SELECT
        year,
        return_on_equity_pct,
        operating_profit_margin_pct,
        debt_to_equity,
        revenue_cagr_5yr,
        free_cash_flow_cr
    FROM financial_ratios
    WHERE UPPER(company_id) = UPPER(?)
    ORDER BY year
    """

    return _query_database(query, (ticker,))


@st.cache_data(ttl=600)
def get_company_financial_history(ticker: str) -> pd.DataFrame:
    """
    Get historical Revenue and Net Profit.
    """

    query = """
    SELECT
        year,
        sales,
        net_profit
    FROM profitandloss
    WHERE UPPER(company_id) = UPPER(?)
    ORDER BY year
    """

    return _query_database(query, (ticker,))


@st.cache_data(ttl=600)
def get_company_return_history(ticker: str) -> pd.DataFrame:
    """
    Get historical ROE and ROCE values.
    """

    query = """
    SELECT
        company_id,
        year,
        return_on_equity_pct,
        return_on_capital_employed_pct
    FROM financial_ratios
    WHERE UPPER(company_id) = UPPER(?)
    ORDER BY year
    """

    return _query_database(query, (ticker,))