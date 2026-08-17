"""
NIFTY 100 Financial Intelligence Platform
Sprint 1 - Excel Loader + SQLite Loader
"""

import sqlite3
import time
from pathlib import Path

import pandas as pd

from .normaliser import (
    normalize_ticker,
    normalize_year
)


CORE = [
    "companies",
    "profitandloss",
    "balancesheet",
    "cashflow",
    "analysis",
    "documents",
    "prosandcons"
]


SUPPLEMENTARY = [
    "sectors",
    "stock_prices",
    "market_cap",
    "financial_ratios",
    "peer_groups"
]


NUMERIC_COLUMNS = {

    "companies": [
        "face_value",
        "book_value",
        "roce_percentage",
        "roe_percentage"
    ],

    "profitandloss": [
        "sales",
        "expenses",
        "operating_profit",
        "opm_percentage",
        "other_income",
        "interest",
        "depreciation",
        "profit_before_tax",
        "tax_percentage",
        "net_profit",
        "eps",
        "dividend_payout"
    ],

    "balancesheet": [
        "equity_capital",
        "reserves",
        "borrowings",
        "other_liabilities",
        "total_liabilities",
        "fixed_assets",
        "cwip",
        "investments",
        "other_asset",
        "total_assets"
    ],

    "cashflow": [
        "operating_activity",
        "investing_activity",
        "financing_activity",
        "net_cash_flow"
    ],

    "sectors": [
        "index_weight_pct"
    ],

    "stock_prices": [
        "open_price",
        "high_price",
        "low_price",
        "close_price",
        "volume",
        "adjusted_close"
    ],

    "market_cap": [
        "market_cap_crore",
        "enterprise_value_crore",
        "pe_ratio",
        "pb_ratio",
        "ev_ebitda",
        "dividend_yield_pct"
    ],

    "financial_ratios": [
        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "return_on_equity_pct",
        "debt_to_equity",
        "interest_coverage",
        "asset_turnover",
        "free_cash_flow_cr",
        "capex_cr",
        "earnings_per_share",
        "book_value_per_share",
        "dividend_payout_ratio_pct",
        "total_debt_cr",
        "cash_from_operations_cr"
    ]
}


def get_source_path(root, table_name):

    root = Path(root)

    raw_path = (
        root
        / "data"
        / "raw"
        / f"{table_name}.xlsx"
    )

    supporting_path = (
        root
        / "data"
        / "supporting"
        / f"{table_name}.xlsx"
    )

    if raw_path.exists():
        return raw_path

    if supporting_path.exists():
        return supporting_path

    raise FileNotFoundError(
        f"Excel file not found for: {table_name}"
    )


def read_excel(root, table_name):

    path = get_source_path(
        root,
        table_name
    )

    # Core files use header row 2 in the supplied dataset.
    header = (
        1
        if table_name in CORE
        else 0
    )

    df = pd.read_excel(
        path,
        header=header
    )

    # Clean column names
    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    # Normalize company ID
    if "company_id" in df.columns:

        df["company_id"] = (
            df["company_id"]
            .map(normalize_ticker)
        )

    # Rename common columns
    rename_map = {}

    if "Year" in df.columns:
        rename_map["Year"] = "year"

    if "Company ID" in df.columns:
        rename_map["Company ID"] = "company_id"

    if "Company_ID" in df.columns:
        rename_map["Company_ID"] = "company_id"

    if "Ticker" in df.columns:
        rename_map["Ticker"] = "company_id"

    if "Annual Report" in df.columns:
        rename_map["Annual Report"] = "Annual_Report"

    if rename_map:
        df = df.rename(
            columns=rename_map
        )

    # Normalize company ID again after renaming
    if "company_id" in df.columns:

        df["company_id"] = (
            df["company_id"]
            .map(normalize_ticker)
        )

    # Normalize financial years
    annual_tables = {
        "profitandloss",
        "balancesheet",
        "cashflow",
        "financial_ratios"
    }

    if (
        table_name in annual_tables
        and "year" in df.columns
    ):

        def safe_year(value):

            try:
                return normalize_year(value)

            except Exception:
                return None

        df["year"] = (
            df["year"]
            .map(safe_year)
        )

    # Documents generally use calendar year
    if table_name == "documents":

        if "year" in df.columns:

            df["year"] = pd.to_numeric(
                df["year"],
                errors="coerce"
            )

    # Stock price dates
    if (
        table_name == "stock_prices"
        and "date" in df.columns
    ):

        df["date"] = pd.to_datetime(
            df["date"],
            errors="coerce"
        ).dt.strftime("%Y-%m-%d")

    # Numeric conversion
    for column in NUMERIC_COLUMNS.get(
        table_name,
        []
    ):

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

    return df


def get_table_columns(connection, table_name):

    rows = connection.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return {
        row[1]
        for row in rows
    }


def prepare_data(frames):

    # ---------------------------------------------------------
    # Companies
    # ---------------------------------------------------------

    companies = frames["companies"].copy()

    companies["id"] = (
        companies["id"]
        .map(normalize_ticker)
    )

    companies = companies[
        companies["id"].str.len().between(
            2,
            12
        )
    ]

    companies = companies.drop_duplicates(
        subset=["id"],
        keep="last"
    )

    company_ids = set(
        companies["id"]
    )

    frames["companies"] = companies

    # ---------------------------------------------------------
    # Annual financial tables
    # ---------------------------------------------------------

    for table_name in [
        "profitandloss",
        "balancesheet",
        "cashflow"
    ]:

        df = frames[table_name].copy()

        if "company_id" in df.columns:

            df["company_id"] = (
                df["company_id"]
                .map(normalize_ticker)
            )

        # Remove invalid years
        if "year" in df.columns:

            df = df[
                df["year"].notna()
            ]

        # Remove orphan companies
        if "company_id" in df.columns:

            df = df[
                df["company_id"]
                .isin(company_ids)
            ]

        # Remove duplicate annual records
        if {
            "company_id",
            "year"
        }.issubset(df.columns):

            df = df.drop_duplicates(
                subset=[
                    "company_id",
                    "year"
                ],
                keep="last"
            )

        frames[table_name] = df

    # ---------------------------------------------------------
    # Other tables
    # ---------------------------------------------------------

    for table_name, df in frames.items():

        if "company_id" in df.columns:

            df["company_id"] = (
                df["company_id"]
                .map(normalize_ticker)
            )

            df = df[
                df["company_id"]
                .isin(company_ids)
            ]

            frames[table_name] = df

    # ---------------------------------------------------------
    # DQ-09 correction
    # ---------------------------------------------------------

    cashflow = frames["cashflow"].copy()

    required = {
        "operating_activity",
        "investing_activity",
        "financing_activity",
        "net_cash_flow"
    }

    if required.issubset(
        cashflow.columns
    ):

        calculated = (
            cashflow[
                [
                    "operating_activity",
                    "investing_activity",
                    "financing_activity"
                ]
            ]
            .fillna(0)
            .sum(axis=1)
        )

        mismatch = (
            cashflow["net_cash_flow"]
            - calculated
        ).abs() > 10

        cashflow.loc[
            mismatch,
            "net_cash_flow"
        ] = calculated[mismatch]

    frames["cashflow"] = cashflow

    # ---------------------------------------------------------
    # DQ-10 correction
    # ---------------------------------------------------------

    balancesheet = (
        frames["balancesheet"]
        .copy()
    )

    if "fixed_assets" in balancesheet.columns:

        mask = (
            balancesheet["fixed_assets"]
            < 0
        )

        balancesheet.loc[
            mask,
            "fixed_assets"
        ] = 0

    frames["balancesheet"] = balancesheet

    return frames


def load_database(
    root,
    database_path
):

    root = Path(root)
    database_path = Path(database_path)

    frames = {}

    for table_name in (
        CORE + SUPPLEMENTARY
    ):

        print(
            f"Reading {table_name}.xlsx ..."
        )

        frames[table_name] = (
            read_excel(
                root,
                table_name
            )
        )

    # Prepare data
    frames = prepare_data(
        frames
    )

    # Create database folder
    database_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    if database_path.exists():
        database_path.unlink()

    connection = sqlite3.connect(
        database_path
    )

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    # Create tables
    schema_path = (
        root
        / "db"
        / "schema.sql"
    )

    schema = schema_path.read_text(
        encoding="utf-8"
    )

    connection.executescript(
        schema
    )

    load_order = [
        "companies",
        "sectors",
        "peer_groups",
        "profitandloss",
        "balancesheet",
        "cashflow",
        "analysis",
        "documents",
        "prosandcons",
        "stock_prices",
        "market_cap",
        "financial_ratios"
    ]

    audit = []

    for table_name in load_order:

        start_time = time.time()

        df = frames[table_name].copy()

        # Documents column naming
        if (
            table_name == "documents"
            and "Annual_Report" in df.columns
        ):

            df = df.rename(
                columns={
                    "Annual_Report":
                    "annual_report"
                }
            )

        table_columns = (
            get_table_columns(
                connection,
                table_name
            )
        )

        valid_columns = [
            column
            for column in df.columns
            if column in table_columns
        ]

        df = df[
            valid_columns
        ]

        # Insert
        if not df.empty:

            df.to_sql(
                table_name,
                connection,
                if_exists="append",
                index=False
            )

        elapsed = (
            time.time()
            - start_time
        )

        source_count = len(
            read_excel(
                root,
                table_name
            )
        )

        audit.append({

            "table": table_name,

            "rows_in":
                source_count,

            "rows_out":
                len(df),

            "rejected":
                source_count - len(df),

            "runtime_s":
                round(
                    elapsed,
                    4
                )
        })

        print(
            f"{table_name}: "
            f"{len(df)} rows loaded"
        )

    connection.commit()

    # Foreign key validation
    foreign_key_errors = connection.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    connection.close()

    output_folder = (
        root
        / "output"
    )

    output_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    audit_df = pd.DataFrame(
        audit
    )

    audit_df.to_csv(
        output_folder
        / "load_audit.csv",
        index=False
    )

    return (
        frames,
        audit_df,
        foreign_key_errors
    )