from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


# --------------------------------------------------
# Project paths
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_DB_PATH = (
    PROJECT_ROOT
    / "data"
    / "nifty100.db"
)

DEFAULT_MARKET_CAP_PATH = (
    PROJECT_ROOT
    / "data"
    / "supporting"
    / "market_cap.xlsx"
)

DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT
    / "output"
)

DEFAULT_SUMMARY_PATH = (
    DEFAULT_OUTPUT_DIR
    / "valuation_summary.xlsx"
)

DEFAULT_FLAGS_PATH = (
    DEFAULT_OUTPUT_DIR
    / "valuation_flags.csv"
)


# --------------------------------------------------
# Load market-cap data
# --------------------------------------------------

def load_market_cap_data(
    market_cap_path: str | Path = (
        DEFAULT_MARKET_CAP_PATH
    ),
) -> pd.DataFrame:
    """
    Load valuation data from market_cap.xlsx.
    """

    market_cap_path = Path(
        market_cap_path
    )

    if not market_cap_path.exists():

        raise FileNotFoundError(
            f"Market cap file not found: "
            f"{market_cap_path}"
        )

    df = pd.read_excel(
        market_cap_path
    )

    required_columns = [
        "company_id",
        "year",
        "market_cap_crore",
        "pe_ratio",
        "pb_ratio",
        "ev_ebitda",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:

        raise ValueError(
            "market_cap.xlsx is missing "
            f"required columns: "
            f"{missing_columns}"
        )

    df["company_id"] = (
        df["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["year"] = pd.to_numeric(
        df["year"],
        errors="coerce",
    )

    numeric_columns = [
        "market_cap_crore",
        "pe_ratio",
        "pb_ratio",
        "ev_ebitda",
    ]

    for column in numeric_columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    df = df.dropna(
        subset=[
            "company_id",
            "year",
        ]
    )

    df["year"] = (
        df["year"]
        .astype(int)
    )

    return df


# --------------------------------------------------
# Load company names and sectors
# --------------------------------------------------

def load_company_sector_data(
    db_path: str | Path = (
        DEFAULT_DB_PATH
    ),
) -> pd.DataFrame:
    """
    Load company names and broad sectors
    from SQLite.
    """

    db_path = Path(
        db_path
    )

    query = """
        SELECT
            c.id AS company_id,
            c.company_name,
            s.broad_sector
        FROM companies c
        LEFT JOIN sectors s
            ON c.id = s.company_id
    """

    with sqlite3.connect(
        db_path
    ) as connection:

        df = pd.read_sql_query(
            query,
            connection,
        )

    df["company_id"] = (
        df["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    return df


# --------------------------------------------------
# Load free cash flow
# --------------------------------------------------

def load_free_cash_flow_data(
    db_path: str | Path = (
        DEFAULT_DB_PATH
    ),
) -> pd.DataFrame:
    """
    Load annual Free Cash Flow from
    financial_ratios.

    financial_ratios uses years such as:
        2024-03

    This function extracts:
        2024

    so the records can be joined with
    market_cap.xlsx.
    """

    db_path = Path(
        db_path
    )

    query = """
        SELECT
            company_id,
            year,
            free_cash_flow_cr
        FROM financial_ratios
        WHERE year LIKE '%-03'
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

    df["market_year"] = pd.to_numeric(
        df["year"]
        .astype(str)
        .str[:4],
        errors="coerce",
    )

    df["free_cash_flow_cr"] = (
        pd.to_numeric(
            df["free_cash_flow_cr"],
            errors="coerce",
        )
    )

    df = df.dropna(
        subset=[
            "market_year",
        ]
    )

    df["market_year"] = (
        df["market_year"]
        .astype(int)
    )

    return df[
        [
            "company_id",
            "market_year",
            "free_cash_flow_cr",
        ]
    ]


# --------------------------------------------------
# Latest valuation records
# --------------------------------------------------

def get_latest_market_cap_records(
    market_cap_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Return the latest available valuation
    record for every company.
    """

    df = market_cap_df.copy()

    df = df.sort_values(
        [
            "company_id",
            "year",
        ]
    )

    latest_df = (
        df.groupby(
            "company_id",
            as_index=False,
        )
        .tail(1)
        .copy()
    )

    return latest_df


# --------------------------------------------------
# Five-year median P/E
# --------------------------------------------------

def calculate_five_year_median_pe(
    market_cap_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate the median P/E from the latest
    five available years for every company.
    """

    df = market_cap_df.copy()

    df = df.sort_values(
        [
            "company_id",
            "year",
        ]
    )

    latest_five = (
        df.groupby(
            "company_id",
            group_keys=False,
        )
        .tail(5)
        .copy()
    )

    result = (
        latest_five.groupby(
            "company_id",
            as_index=False,
        )["pe_ratio"]
        .median()
        .rename(
            columns={
                "pe_ratio":
                    "5yr_median_PE"
            }
        )
    )

    return result


# --------------------------------------------------
# Sector median P/E
# --------------------------------------------------

def calculate_sector_median_pe(
    latest_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate median P/E for each broad sector
    using the latest valuation year.
    """

    result = (
        latest_df.groupby(
            "sector",
            dropna=False,
            as_index=False,
        )["P/E"]
        .median()
        .rename(
            columns={
                "P/E":
                    "sector_median_PE"
            }
        )
    )

    return result


# --------------------------------------------------
# FCF Yield
# --------------------------------------------------

def calculate_fcf_yield(
    free_cash_flow_cr: float,
    market_cap_crore: float,
) -> float:
    """
    FCF Yield:

        FCF / Market Cap x 100
    """

    if pd.isna(
        free_cash_flow_cr
    ):

        return np.nan

    if pd.isna(
        market_cap_crore
    ):

        return np.nan

    if market_cap_crore <= 0:

        return np.nan

    return (
        free_cash_flow_cr
        /
        market_cap_crore
        *
        100
    )


# --------------------------------------------------
# Valuation flag
# --------------------------------------------------

def calculate_valuation_flag(
    pe_ratio: float,
    sector_median_pe: float,
) -> str:
    """
    Apply valuation rules.

    P/E > sector median x 1.5
        -> Caution

    P/E < sector median x 0.7
        -> Discount

    Otherwise
        -> Fair
    """

    if pd.isna(
        pe_ratio
    ):

        return "Fair"

    if pd.isna(
        sector_median_pe
    ):

        return "Fair"

    if sector_median_pe <= 0:

        return "Fair"

    if pe_ratio > (
        sector_median_pe
        * 1.5
    ):

        return "Caution"

    if pe_ratio < (
        sector_median_pe
        * 0.7
    ):

        return "Discount"

    return "Fair"


# --------------------------------------------------
# Build valuation summary
# --------------------------------------------------

def build_valuation_summary(
    market_cap_df: pd.DataFrame,
    company_sector_df: pd.DataFrame,
    free_cash_flow_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build the complete valuation dataset
    for the latest company valuation year.
    """

    # ----------------------------------------------
    # Latest valuation data
    # ----------------------------------------------

    latest_df = (
        get_latest_market_cap_records(
            market_cap_df
        )
    )

    # ----------------------------------------------
    # Company names and sectors
    # ----------------------------------------------

    latest_df = latest_df.merge(
        company_sector_df,
        on="company_id",
        how="left",
    )

    # ----------------------------------------------
    # Free Cash Flow
    # ----------------------------------------------

    latest_df = latest_df.merge(
        free_cash_flow_df,
        left_on=[
            "company_id",
            "year",
        ],
        right_on=[
            "company_id",
            "market_year",
        ],
        how="left",
    )

    # ----------------------------------------------
    # Five-year median P/E
    # ----------------------------------------------

    median_pe_df = (
        calculate_five_year_median_pe(
            market_cap_df
        )
    )

    latest_df = latest_df.merge(
        median_pe_df,
        on="company_id",
        how="left",
    )

    # ----------------------------------------------
    # Rename output fields
    # ----------------------------------------------

    latest_df = latest_df.rename(
        columns={
            "company_name":
                "company_name",
            "broad_sector":
                "sector",
            "pe_ratio":
                "P/E",
            "pb_ratio":
                "P/B",
            "ev_ebitda":
                "EV/EBITDA",
        }
    )

    # ----------------------------------------------
    # FCF Yield
    # ----------------------------------------------

    latest_df[
        "FCF_yield_pct"
    ] = latest_df.apply(
        lambda row:
            calculate_fcf_yield(
                row[
                    "free_cash_flow_cr"
                ],
                row[
                    "market_cap_crore"
                ],
            ),
        axis=1,
    )

    # ----------------------------------------------
    # Sector median P/E
    # ----------------------------------------------

    sector_median_df = (
        calculate_sector_median_pe(
            latest_df
        )
    )

    latest_df = latest_df.merge(
        sector_median_df,
        on="sector",
        how="left",
    )

    # ----------------------------------------------
    # P/E vs sector median
    # ----------------------------------------------

    latest_df[
        "PE_vs_sector_median_pct"
    ] = np.where(
        latest_df[
            "sector_median_PE"
        ]
        > 0,
        (
            (
                latest_df["P/E"]
                /
                latest_df[
                    "sector_median_PE"
                ]
            )
            - 1
        )
        * 100,
        np.nan,
    )

    # ----------------------------------------------
    # Valuation flags
    # ----------------------------------------------

    latest_df["flag"] = (
        latest_df.apply(
            lambda row:
                calculate_valuation_flag(
                    row["P/E"],
                    row[
                        "sector_median_PE"
                    ],
                ),
            axis=1,
        )
    )

    # ----------------------------------------------
    # Final output columns
    # ----------------------------------------------

    output_columns = [
        "company_id",
        "company_name",
        "sector",
        "P/E",
        "P/B",
        "EV/EBITDA",
        "FCF_yield_pct",
        "5yr_median_PE",
        "PE_vs_sector_median_pct",
        "flag",
    ]

    summary_df = latest_df[
        output_columns
    ].copy()

    summary_df = summary_df.sort_values(
        [
            "flag",
            "company_id",
        ]
    )

    return summary_df


# --------------------------------------------------
# Generate valuation files
# --------------------------------------------------

def generate_valuation_outputs(
    market_cap_path: str | Path = (
        DEFAULT_MARKET_CAP_PATH
    ),
    db_path: str | Path = (
        DEFAULT_DB_PATH
    ),
    summary_path: str | Path = (
        DEFAULT_SUMMARY_PATH
    ),
    flags_path: str | Path = (
        DEFAULT_FLAGS_PATH
    ),
) -> pd.DataFrame:
    """
    Main Day 26 workflow.

    1. Load market_cap.xlsx
    2. Load companies and sectors
    3. Load Free Cash Flow
    4. Build valuation summary
    5. Write valuation_summary.xlsx
    6. Write valuation_flags.csv
    """

    summary_path = Path(
        summary_path
    )

    flags_path = Path(
        flags_path
    )

    summary_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    flags_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ----------------------------------------------
    # Load data
    # ----------------------------------------------

    market_cap_df = (
        load_market_cap_data(
            market_cap_path
        )
    )

    company_sector_df = (
        load_company_sector_data(
            db_path
        )
    )

    free_cash_flow_df = (
        load_free_cash_flow_data(
            db_path
        )
    )

    # ----------------------------------------------
    # Build summary
    # ----------------------------------------------

    summary_df = (
        build_valuation_summary(
            market_cap_df,
            company_sector_df,
            free_cash_flow_df,
        )
    )

    # ----------------------------------------------
    # Round numeric output
    # ----------------------------------------------

    numeric_columns = [
        "P/E",
        "P/B",
        "EV/EBITDA",
        "FCF_yield_pct",
        "5yr_median_PE",
        "PE_vs_sector_median_pct",
    ]

    for column in numeric_columns:

        summary_df[column] = (
            summary_df[column]
            .round(2)
        )

    # ----------------------------------------------
    # Write Excel summary
    # ----------------------------------------------

    summary_df.to_excel(
        summary_path,
        index=False,
    )

    # ----------------------------------------------
    # Filter flagged companies
    # ----------------------------------------------

    flags_df = summary_df[
        summary_df["flag"].isin(
            [
                "Caution",
                "Discount",
            ]
        )
    ].copy()

    flags_df.to_csv(
        flags_path,
        index=False,
    )

    return summary_df


# --------------------------------------------------
# Command-line execution
# --------------------------------------------------

if __name__ == "__main__":

    summary = (
        generate_valuation_outputs()
    )

    caution_count = (
        summary[
            summary["flag"]
            == "Caution"
        ].shape[0]
    )

    discount_count = (
        summary[
            summary["flag"]
            == "Discount"
        ].shape[0]
    )

    fair_count = (
        summary[
            summary["flag"]
            == "Fair"
        ].shape[0]
    )

    print(
        "Valuation analysis complete."
    )

    print(
        f"Companies analysed: "
        f"{len(summary)}"
    )

    print(
        f"Caution: "
        f"{caution_count}"
    )

    print(
        f"Discount: "
        f"{discount_count}"
    )

    print(
        f"Fair: "
        f"{fair_count}"
    )

    print(
        f"\nSummary: "
        f"{DEFAULT_SUMMARY_PATH}"
    )

    print(
        f"Flags: "
        f"{DEFAULT_FLAGS_PATH}"
    )