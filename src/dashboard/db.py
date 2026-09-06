import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


DATABASE_PATH = Path("data/nifty100.db")


def _query_database(query, params=None):
    """
    Execute a SQL query and return the result as a DataFrame.
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


# ============================================================
# DAY 22 — SHARED DATABASE FUNCTIONS
# ============================================================

@st.cache_data(ttl=600)
def get_companies():
    """
    Return all companies with sector information.
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
    Return Profit & Loss history.
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
    Return Balance Sheet history.
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
    Return Cash Flow history.
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
    Return sector mapping.
    """

    query = """
    SELECT
        company_id,
        broad_sector,
        sub_sector,
        index_weight_pct,
        market_cap_category
    FROM sectors
    ORDER BY broad_sector, company_id
    """

    return _query_database(query)


@st.cache_data(ttl=600)
def get_peers(group_name):
    """
    Return companies belonging to a peer group.
    """

    query = """
    SELECT *
    FROM peer_groups
    WHERE peer_group_name = ?
    ORDER BY company_id
    """

    return _query_database(
        query,
        params=(group_name,),
    )


@st.cache_data(ttl=600)
def get_valuation(ticker):
    """
    Return valuation-related information for a company.
    """

    query = """
    SELECT
        r.company_id,
        r.year,
        r.free_cash_flow_cr,
        m.market_cap_crore,
        m.pe_ratio,
        m.pb_ratio,
        m.dividend_yield_pct
    FROM financial_ratios r
    LEFT JOIN market_cap m
        ON r.company_id = m.company_id
        AND CAST(SUBSTR(r.year, 1, 4) AS INTEGER) = m.year
    WHERE r.company_id = ?
    ORDER BY r.year DESC
    """

    return _query_database(
        query,
        params=(ticker,),
    )


# ============================================================
# DAY 23 — HOME SCREEN FUNCTIONS
# ============================================================

@st.cache_data(ttl=600)
def get_available_years():
    """
    Return available annual financial years between 2019 and 2024.
    """

    query = """
    SELECT DISTINCT year
    FROM financial_ratios
    WHERE year IS NOT NULL
      AND year LIKE '%-03'
      AND CAST(SUBSTR(year, 1, 4) AS INTEGER)
          BETWEEN 2019 AND 2024
    ORDER BY year
    """

    dataframe = _query_database(query)

    return dataframe["year"].dropna().astype(str).tolist()


@st.cache_data(ttl=600)
def get_home_metrics(year=None):
    """
    Return the six Home Screen KPI metrics.
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
        "average_roe": float(
            dataframe["return_on_equity_pct"].mean()
        ),
        "median_pe": float(
            dataframe["pe_ratio"].median()
        ),
        "median_debt_to_equity": float(
            dataframe["debt_to_equity"].median()
        ),
        "total_companies": int(
            dataframe["company_id"].nunique()
        ),
        "median_revenue_cagr_5yr": float(
            dataframe["revenue_cagr_5yr"].median()
        ),
        "debt_free_companies": int(
            dataframe.loc[
                dataframe["debt_to_equity"].fillna(float("inf"))
                <= 0.000001,
                "company_id"
            ].nunique()
        ),
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
    Return the top five companies by composite quality score.
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


# ============================================================
# DAY 23 — COMPANY PROFILE FUNCTIONS
# ============================================================

@st.cache_data(ttl=600)
def get_company_profile(ticker):
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

    return _query_database(
        query,
        params=(ticker,),
    )


@st.cache_data(ttl=600)
def get_latest_company_kpis(ticker):
    """
    Return latest KPI metrics for a company.
    """

    query = """
    SELECT
        company_id,
        year,
        return_on_equity_pct,
        return_on_capital_employed_pct,
        net_profit_margin_pct,
        debt_to_equity,
        revenue_cagr_5yr,
        free_cash_flow_cr
    FROM financial_ratios
    WHERE company_id = ?
    ORDER BY year DESC
    LIMIT 1
    """

    return _query_database(
        query,
        params=(ticker,),
    )


@st.cache_data(ttl=600)
def get_company_financial_history(ticker):
    """
    Return annual Revenue and Net Profit history.
    """

    query = """
    SELECT
        company_id,
        year,
        sales,
        net_profit
    FROM profitandloss
    WHERE company_id = ?
      AND year LIKE '%-03'
    ORDER BY year
    """

    return _query_database(
        query,
        params=(ticker,),
    )


@st.cache_data(ttl=600)
def get_company_ratio_history(ticker):
    """
    Return annual ROE and ROCE history.
    """

    query = """
    SELECT
        company_id,
        year,
        return_on_equity_pct,
        return_on_capital_employed_pct
    FROM financial_ratios
    WHERE company_id = ?
      AND year LIKE '%-03'
    ORDER BY year
    """

    return _query_database(
        query,
        params=(ticker,),
    )


@st.cache_data(ttl=600)
def get_company_pros_cons(ticker):
    """
    Return pros and cons for a company.

    The database schema is inspected dynamically so this
    function can work with the existing prosandcons table.
    """

    query = """
    SELECT *
    FROM prosandcons
    WHERE company_id = ?
    """

    dataframe = _query_database(
        query,
        params=(ticker,),
    )

    if dataframe.empty:
        return {
            "pros": [],
            "cons": [],
        }

    pros = []
    cons = []

    for column in dataframe.columns:

        column_name = column.lower()

        if "pro" in column_name:

            values = dataframe[column].dropna().astype(str)

            for value in values:
                value = value.strip()

                if value:
                    pros.append(value)

        elif "con" in column_name:

            values = dataframe[column].dropna().astype(str)

            for value in values:
                value = value.strip()

                if value:
                    cons.append(value)

    return {
        "pros": pros,
        "cons": cons,
    }


@st.cache_data(ttl=600)
def get_pros_cons(ticker):
    """
    Return the raw pros and cons rows for the Profile screen.
    """

    query = """
    SELECT *
    FROM prosandcons
    WHERE company_id = ?
    """

    return _query_database(
        query,
        params=(ticker,),
    )
# ============================================================
# DAY 23 — COMPANY PROFILE FUNCTIONS
# ============================================================

@st.cache_data(ttl=600)
def get_company_profile(ticker):
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

    return _query_database(
        query,
        params=(ticker,),
    )


@st.cache_data(ttl=600)
def get_latest_company_kpis(ticker):
    """
    Return latest KPI metrics for a company.
    """

    query = """
    SELECT
        company_id,
        year,
        return_on_equity_pct,
        return_on_capital_employed_pct,
        net_profit_margin_pct,
        debt_to_equity,
        revenue_cagr_5yr,
        free_cash_flow_cr
    FROM financial_ratios
    WHERE company_id = ?
      AND year LIKE '%-03'
    ORDER BY year DESC
    LIMIT 1
    """

    return _query_database(
        query,
        params=(ticker,),
    )


@st.cache_data(ttl=600)
def get_company_financial_history(ticker):
    """
    Return annual Revenue and Net Profit history.
    """

    query = """
    SELECT
        company_id,
        year,
        sales,
        net_profit
    FROM profitandloss
    WHERE company_id = ?
      AND year LIKE '%-03'
    ORDER BY year
    """

    return _query_database(
        query,
        params=(ticker,),
    )


@st.cache_data(ttl=600)
def get_company_ratio_history(ticker):
    """
    Return annual ROE and ROCE history.
    """

    query = """
    SELECT
        company_id,
        year,
        return_on_equity_pct,
        return_on_capital_employed_pct
    FROM financial_ratios
    WHERE company_id = ?
      AND year LIKE '%-03'
    ORDER BY year
    """

    return _query_database(
        query,
        params=(ticker,),
    )


@st.cache_data(ttl=600)
def get_company_pros_cons(ticker):
    """
    Return pros and cons for a company.
    """

    query = """
    SELECT *
    FROM prosandcons
    WHERE company_id = ?
    """

    dataframe = _query_database(
        query,
        params=(ticker,),
    )

    if dataframe.empty:
        return {
            "pros": [],
            "cons": [],
        }

    pros = []
    cons = []

    for column in dataframe.columns:
        column_name = column.lower()

        if column_name.startswith("pro") or "pros" in column_name:

            values = dataframe[column].dropna().astype(str).tolist()

            for value in values:
                value = value.strip()

                if value:
                    pros.append(value)

        elif column_name.startswith("con") or "cons" in column_name:

            values = dataframe[column].dropna().astype(str).tolist()

            for value in values:
                value = value.strip()

                if value:
                    cons.append(value)

    return {
        "pros": pros,
        "cons": cons,
    }
@st.cache_data(ttl=600)
def get_company_profile(ticker):
    """
    Return company profile information for a ticker.
    """

    query = """
    SELECT
        c.id AS company_id,
        c.company_name,
        c.about_company,
        c.website,
        c.company_logo,
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
