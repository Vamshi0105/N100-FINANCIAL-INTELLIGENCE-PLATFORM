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