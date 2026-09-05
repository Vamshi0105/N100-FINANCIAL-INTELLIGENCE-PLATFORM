"""
Shared SQLite data access functions for the Streamlit dashboard.
"""

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


DATABASE_PATH = Path("data/nifty100.db")


def _get_connection():
    """Create a SQLite database connection."""
    return sqlite3.connect(DATABASE_PATH)


@st.cache_data(ttl=600)
def get_companies():
    """Return all companies."""
    connection = _get_connection()

    dataframe = pd.read_sql_query(
        """
        SELECT *
        FROM companies
        ORDER BY company_name
        """,
        connection,
    )

    connection.close()
    return dataframe


@st.cache_data(ttl=600)
def get_ratios(ticker, year=None):
    """Return financial ratios for a company."""

    connection = _get_connection()

    if year is None:
        query = """
        SELECT *
        FROM financial_ratios
        WHERE company_id = ?
        ORDER BY year
        """

        dataframe = pd.read_sql_query(
            query,
            connection,
            params=(ticker,),
        )
    else:
        query = """
        SELECT *
        FROM financial_ratios
        WHERE company_id = ?
          AND year = ?
        """

        dataframe = pd.read_sql_query(
            query,
            connection,
            params=(ticker, year),
        )

    connection.close()
    return dataframe


@st.cache_data(ttl=600)
def get_pl(ticker):
    """Return Profit and Loss history."""

    connection = _get_connection()

    dataframe = pd.read_sql_query(
        """
        SELECT *
        FROM profitandloss
        WHERE company_id = ?
        ORDER BY year
        """,
        connection,
        params=(ticker,),
    )

    connection.close()
    return dataframe


@st.cache_data(ttl=600)
def get_bs(ticker):
    """Return Balance Sheet history."""

    connection = _get_connection()

    dataframe = pd.read_sql_query(
        """
        SELECT *
        FROM balancesheet
        WHERE company_id = ?
        ORDER BY year
        """,
        connection,
        params=(ticker,),
    )

    connection.close()
    return dataframe


@st.cache_data(ttl=600)
def get_cf(ticker):
    """Return Cash Flow history."""

    connection = _get_connection()

    dataframe = pd.read_sql_query(
        """
        SELECT *
        FROM cashflow
        WHERE company_id = ?
        ORDER BY year
        """,
        connection,
        params=(ticker,),
    )

    connection.close()
    return dataframe


@st.cache_data(ttl=600)
def get_sectors():
    """Return sector information."""

    connection = _get_connection()

    dataframe = pd.read_sql_query(
        """
        SELECT *
        FROM sectors
        ORDER BY broad_sector, sub_sector, company_id
        """,
        connection,
    )

    connection.close()
    return dataframe


@st.cache_data(ttl=600)
def get_peers(group_name):
    """Return companies in a peer group."""

    connection = _get_connection()

    dataframe = pd.read_sql_query(
        """
        SELECT
            p.peer_group_name,
            p.company_id,
            p.is_benchmark,
            c.company_name
        FROM peer_groups p
        LEFT JOIN companies c
            ON p.company_id = c.id
        WHERE p.peer_group_name = ?
        ORDER BY
            p.is_benchmark DESC,
            c.company_name
        """,
        connection,
        params=(group_name,),
    )

    connection.close()
    return dataframe


@st.cache_data(ttl=600)
def get_valuation(ticker):
    """
    Return valuation data if the valuation table exists.
    Otherwise return an empty DataFrame.
    """

    connection = _get_connection()

    exists = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'valuation'
        """
    ).fetchone()

    if not exists:
        connection.close()
        return pd.DataFrame()

    dataframe = pd.read_sql_query(
        """
        SELECT *
        FROM valuation
        WHERE company_id = ?
        """,
        connection,
        params=(ticker,),
    )

    connection.close()
    return dataframe