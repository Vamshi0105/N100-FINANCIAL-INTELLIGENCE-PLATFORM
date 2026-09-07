from __future__ import annotations

import sqlite3
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd
import streamlit as st


# --------------------------------------------------
# Project paths
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_DB_PATH = (
    PROJECT_ROOT
    / "data"
    / "nifty100.db"
)


# --------------------------------------------------
# Load companies
# --------------------------------------------------

@st.cache_data
def load_companies(
    db_path: str,
) -> pd.DataFrame:

    query = """
        SELECT
            id AS company_id,
            company_name
        FROM companies
        ORDER BY company_name
    """

    with sqlite3.connect(
        db_path
    ) as connection:

        df = pd.read_sql_query(
            query,
            connection,
        )

    if df.empty:
        return df

    df["company_id"] = (
        df["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    return df


# --------------------------------------------------
# Load annual reports
# --------------------------------------------------

@st.cache_data
def load_annual_reports(
    db_path: str,
    company_id: str,
) -> pd.DataFrame:

    query = """
        SELECT
            year,
            annual_report
        FROM documents
        WHERE UPPER(
            TRIM(company_id)
        ) = ?
        AND annual_report IS NOT NULL
        AND TRIM(annual_report) != ''
        ORDER BY year DESC
    """

    with sqlite3.connect(
        db_path
    ) as connection:

        df = pd.read_sql_query(
            query,
            connection,
            params=(
                company_id.upper(),
            ),
        )

    return df


# --------------------------------------------------
# Check report availability
# --------------------------------------------------

@st.cache_data(
    ttl=3600,
    show_spinner=False,
)
def check_report_status(
    url: str,
) -> tuple[bool, int | None]:
    """
    Check whether the report URL is available.

    A URL returning HTTP 404 is marked
    as unavailable.

    Other HTTP responses are treated as
    available because some BSE URLs may
    reject HEAD requests while still
    allowing browser access.
    """

    if not url:
        return False, None

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/120 Safari/537.36"
        )
    }

    try:

        request = Request(
            url,
            headers=headers,
            method="HEAD",
        )

        with urlopen(
            request,
            timeout=10,
        ) as response:

            status_code = response.getcode()

            if status_code == 404:
                return False, status_code

            return True, status_code

    except HTTPError as error:

        if error.code == 404:
            return False, error.code

        # Some BSE servers reject HEAD
        # requests with 403/405 even though
        # the PDF is accessible in browser.
        return True, error.code

    except URLError:
        return True, None

    except Exception:
        return True, None


# --------------------------------------------------
# Format company options
# --------------------------------------------------

def format_company(
    company_row: dict,
) -> str:

    return (
        f"{company_row['company_id']} "
        f"— "
        f"{company_row['company_name']}"
    )


# --------------------------------------------------
# Render page
# --------------------------------------------------

def render():

    st.title(
        "📄 Annual Reports"
    )

    st.caption(
        "Browse available company annual reports "
        "and access BSE PDF documents."
    )

    db_path = str(
        DEFAULT_DB_PATH
    )

    # ----------------------------------------------
    # Database check
    # ----------------------------------------------

    if not DEFAULT_DB_PATH.exists():

        st.error(
            "Database file not found."
        )

        st.code(
            str(DEFAULT_DB_PATH)
        )

        return

    # ----------------------------------------------
    # Load companies
    # ----------------------------------------------

    try:

        companies_df = (
            load_companies(
                db_path
            )
        )

    except Exception as error:

        st.error(
            "Unable to load companies."
        )

        st.exception(
            error
        )

        return

    if companies_df.empty:

        st.warning(
            "No companies were found "
            "in the database."
        )

        return

    # ----------------------------------------------
    # Company selection
    # ----------------------------------------------

    st.markdown(
        "## Company Selection"
    )

    company_records = (
        companies_df.to_dict(
            orient="records"
        )
    )

    selected_company = (
        st.selectbox(
            "Search and select a company",
            options=company_records,
            format_func=format_company,
            key="reports_company_selector",
        )
    )

    company_id = (
        str(
            selected_company[
                "company_id"
            ]
        )
        .strip()
        .upper()
    )

    company_name = (
        selected_company[
            "company_name"
        ]
    )

    # ----------------------------------------------
    # Load reports
    # ----------------------------------------------

    try:

        reports_df = (
            load_annual_reports(
                db_path,
                company_id,
            )
        )

    except Exception as error:

        st.error(
            "Unable to load annual reports."
        )

        st.exception(
            error
        )

        return

    # ----------------------------------------------
    # KPI summary
    # ----------------------------------------------

    st.divider()

    col1, col2, col3 = st.columns(
        3
    )

    with col1:

        st.caption(
            "Company"
        )

        st.subheader(
            company_id
        )

    with col2:

        st.caption(
            "Available Reports"
        )

        st.subheader(
            len(
                reports_df
            )
        )

    with col3:

        st.caption(
            "Latest Report"
        )

        if reports_df.empty:

            st.subheader(
                "N/A"
            )

        else:

            latest_year = (
                reports_df[
                    "year"
                ].max()
            )

            st.subheader(
                int(
                    latest_year
                )
            )

    st.divider()

    # ----------------------------------------------
    # Annual report list
    # ----------------------------------------------

    st.markdown(
        f"## {company_name}"
    )

    st.markdown(
        "### Annual Reports"
    )

    if reports_df.empty:

        st.warning(
            "No annual report records were "
            "found for this company."
        )

        st.info(
            "This company may not yet have "
            "annual report records in the "
            "`documents` table."
        )

        return

    # ----------------------------------------------
    # Report table
    # ----------------------------------------------

    st.caption(
        "Click **Open BSE PDF** to access "
        "the company's annual report."
    )

    for row in reports_df.itertuples(
        index=False
    ):

        year = row.year
        report_url = row.annual_report

        report_available, status_code = (
            check_report_status(
                report_url
            )
        )

        col1, col2, col3 = st.columns(
            [
                1.2,
                2,
                1.5,
            ]
        )

        with col1:

            st.markdown(
                f"**FY {year}**"
            )

        with col2:

            if not report_available:

                st.markdown(
                    """
                    <span style="
                        background-color:#7f1d1d;
                        color:#fecaca;
                        padding:6px 12px;
                        border-radius:6px;
                        font-weight:600;
                    ">
                    Report unavailable
                    </span>
                    """,
                    unsafe_allow_html=True,
                )

            else:

                if status_code is None:

                    st.caption(
                        "Availability could not "
                        "be verified. "
                        "Try opening the report."
                    )

                else:

                    st.success(
                        "Report available"
                    )

        with col3:

            if report_available:

                st.link_button(
                    "📄 Open BSE PDF",
                    report_url,
                    use_container_width=True,
                )

            else:

                st.button(
                    "Report unavailable",
                    disabled=True,
                    key=(
                        f"unavailable_"
                        f"{company_id}_"
                        f"{year}"
                    ),
                    use_container_width=True,
                )

        st.divider()

    # ----------------------------------------------
    # Data source information
    # ----------------------------------------------

    st.caption(
        "Source: BSE annual report documents "
        "stored in the project database."
    )


if __name__ == "__main__":

    render()