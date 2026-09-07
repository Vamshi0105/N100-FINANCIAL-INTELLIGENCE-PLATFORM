from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[3]

CAPITAL_ALLOCATION_PATH = (
    PROJECT_ROOT
    / "output"
    / "capital_allocation.csv"
)

DATABASE_PATH = (
    PROJECT_ROOT
    / "data"
    / "nifty100.db"
)


@st.cache_data
def load_capital_allocation_data():
    """
    Load the latest capital allocation pattern data.
    """

    if not CAPITAL_ALLOCATION_PATH.exists():
        return pd.DataFrame()

    dataframe = pd.read_csv(
        CAPITAL_ALLOCATION_PATH
    )

    required_columns = {
        "company_id",
        "year",
        "cfo_sign",
        "cfi_sign",
        "cff_sign",
        "pattern_label",
    }

    missing_columns = (
        required_columns
        - set(dataframe.columns)
    )

    if missing_columns:
        raise ValueError(
            "capital_allocation.csv is missing columns: "
            + ", ".join(
                sorted(missing_columns)
            )
        )

    dataframe["company_id"] = (
        dataframe["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    dataframe["pattern_label"] = (
        dataframe["pattern_label"]
        .fillna("Unknown")
        .astype(str)
    )

    dataframe["year"] = (
        dataframe["year"]
        .astype(str)
    )

    return dataframe


@st.cache_data
def load_company_names():
    """
    Load company names from SQLite.
    """

    import sqlite3

    if not DATABASE_PATH.exists():
        return pd.DataFrame(
            columns=[
                "company_id",
                "company_name",
            ]
        )

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    query = """
    SELECT
        id AS company_id,
        company_name
    FROM companies
    """

    dataframe = pd.read_sql_query(
        query,
        connection,
    )

    connection.close()

    dataframe["company_id"] = (
        dataframe["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    return dataframe


def render():

    st.title("💰 Capital & Cash Flow")

    st.write(
        "Explore how companies generate, invest, "
        "and finance cash based on their latest "
        "annual cash-flow pattern."
    )

    # ---------------------------------------------
    # Load Data
    # ---------------------------------------------

    allocation_df = (
        load_capital_allocation_data()
    )

    if allocation_df.empty:

        st.warning(
            "Capital allocation data is not available."
        )

        st.info(
            "Run the following command first:\n\n"
            "`python src/generate_capital_allocation.py`"
        )

        return

    company_df = (
        load_company_names()
    )

    dataframe = allocation_df.merge(
        company_df,
        on="company_id",
        how="left",
    )

    dataframe["company_name"] = (
        dataframe["company_name"]
        .fillna(dataframe["company_id"])
    )

    # ---------------------------------------------
    # Summary KPIs
    # ---------------------------------------------

    total_companies = (
        dataframe["company_id"]
        .nunique()
    )

    total_patterns = (
        dataframe["pattern_label"]
        .nunique()
    )

    most_common_pattern = (
        dataframe["pattern_label"]
        .value_counts()
        .idxmax()
    )

    latest_year = (
        dataframe["year"]
        .max()
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Companies",
        total_companies,
    )

    col2.metric(
        "Allocation Patterns",
        total_patterns,
    )

    col3.metric(
        "Largest Pattern",
        most_common_pattern,
    )

    col4.metric(
        "Latest Period",
        latest_year,
    )

    st.divider()

    # ---------------------------------------------
    # Pattern Summary
    # ---------------------------------------------

    st.subheader(
        "Capital Allocation Map"
    )

    st.caption(
        "Each rectangle represents a company. "
        "Companies are grouped by their capital "
        "allocation pattern."
    )

    # ---------------------------------------------
    # Treemap Data
    # ---------------------------------------------

    treemap_df = dataframe.copy()

    # Each company gets equal weight.
    # This makes the treemap represent
    # company distribution across patterns.
    treemap_df["company_weight"] = 1

    figure = px.treemap(
        treemap_df,
        path=[
            "pattern_label",
            "company_name",
        ],
        values="company_weight",
        color="pattern_label",
        hover_data={
            "company_id": True,
            "year": True,
            "cfo_sign": True,
            "cfi_sign": True,
            "cff_sign": True,
            "company_weight": False,
        },
    )

    figure.update_traces(
        textinfo=(
            "label+value+percent parent"
        )
    )

    figure.update_layout(
        height=700,
        margin=dict(
            t=30,
            l=10,
            r=10,
            b=10,
        ),
    )

    st.plotly_chart(
        figure,
        use_container_width=True,
    )

    st.divider()

    # ---------------------------------------------
    # Pattern Selection
    # ---------------------------------------------

    st.subheader(
        "Explore Capital Allocation Pattern"
    )

    patterns = sorted(
        dataframe["pattern_label"]
        .unique()
        .tolist()
    )

    selected_pattern = st.selectbox(
        "Select Capital Allocation Pattern",
        patterns,
    )

    selected_df = dataframe[
        dataframe["pattern_label"]
        == selected_pattern
    ].copy()

    selected_company_count = (
        selected_df["company_id"]
        .nunique()
    )

    percentage = (
        selected_company_count
        / total_companies
        * 100
    )

    col1, col2 = st.columns(2)

    col1.metric(
        "Companies in Pattern",
        selected_company_count,
    )

    col2.metric(
        "Share of Coverage",
        f"{percentage:.1f}%",
    )

    # ---------------------------------------------
    # Pattern Explanation
    # ---------------------------------------------

    pattern_descriptions = {

        "Reinvestor": (
            "Positive operating cash flow with "
            "cash being deployed into investing "
            "activities and financing outflows. "
            "This commonly indicates internally "
            "funded reinvestment and debt or "
            "capital repayment."
        ),

        "Shareholder Returns": (
            "Strong operating cash generation with "
            "cash deployment towards investment and "
            "returns to shareholders."
        ),

        "Liquidating Assets": (
            "Positive operating and investing cash "
            "flows with financing outflows. "
            "This may indicate asset sales or "
            "reduced investment activity."
        ),

        "Distress Signal": (
            "Negative operating cash flow combined "
            "with positive investing and financing "
            "cash flows."
        ),

        "Growth Funded by Debt": (
            "Negative operating and investing cash "
            "flows supported by positive financing "
            "cash flow."
        ),

        "Cash Accumulator": (
            "Positive cash flow from operations, "
            "investing and financing."
        ),

        "Pre-Revenue": (
            "Negative cash flow across operating, "
            "investing and financing activities."
        ),

        "Mixed": (
            "Positive operating cash flow, negative "
            "investing cash flow and positive "
            "financing cash flow."
        ),

    }

    description = (
        pattern_descriptions.get(
            selected_pattern,
            (
                "This is a cash-flow sign pattern "
                "that does not currently have a "
                "special descriptive classification."
            ),
        )
    )

    st.info(
        description
    )

    # ---------------------------------------------
    # Selected Company List
    # ---------------------------------------------

    st.subheader(
        f"Companies — {selected_pattern}"
    )

    display_columns = [
        "company_id",
        "company_name",
        "year",
        "cfo_sign",
        "cfi_sign",
        "cff_sign",
    ]

    company_display = (
        selected_df[
            display_columns
        ]
        .sort_values(
            by="company_name"
        )
        .reset_index(
            drop=True
        )
    )

    company_display = (
        company_display.rename(
            columns={
                "company_id": "Company ID",
                "company_name": "Company",
                "year": "Financial Year",
                "cfo_sign": "CFO",
                "cfi_sign": "CFI",
                "cff_sign": "CFF",
            }
        )
    )

    st.dataframe(
        company_display,
        use_container_width=True,
        hide_index=True,
    )

    # ---------------------------------------------
    # Pattern Distribution Chart
    # ---------------------------------------------

    st.divider()

    st.subheader(
        "Pattern Distribution"
    )

    pattern_counts = (
        dataframe[
            "pattern_label"
        ]
        .value_counts()
        .reset_index()
    )

    pattern_counts.columns = [
        "Pattern",
        "Companies",
    ]

    pattern_counts = (
        pattern_counts.sort_values(
            by="Companies",
            ascending=False,
        )
    )

    bar_figure = px.bar(
        pattern_counts,
        x="Pattern",
        y="Companies",
        text="Companies",
        labels={
            "Pattern": "Capital Allocation Pattern",
            "Companies": "Number of Companies",
        },
    )

    bar_figure.update_traces(
        textposition="outside"
    )

    bar_figure.update_layout(
        height=500,
        showlegend=False,
        xaxis_tickangle=-30,
    )

    st.plotly_chart(
        bar_figure,
        use_container_width=True,
    )

    st.caption(
        "Capital allocation classification is based "
        "on the signs of Cash Flow from Operations "
        "(CFO), Investing Activities (CFI), and "
        "Financing Activities (CFF)."
    )