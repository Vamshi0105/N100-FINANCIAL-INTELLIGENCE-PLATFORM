"""
Day 31 + Day 32 â€” Cash Flow Intelligence and Capital Allocation

Generates:

output/cashflow_intelligence.xlsx
output/distress_alerts.csv
output/capital_allocation.csv
output/capital_allocation_distribution.csv
output/pattern_changes.csv
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from src.analytics.cash_flow import (
capital_allocation_pattern,
capex_intensity,
cfo_quality_score,
fcf_conversion_rate,
free_cash_flow,
)

# ---------------------------------------------------------

# Project paths

# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = (
PROJECT_ROOT
/ "data"
/ "nifty100.db"
)

OUTPUT_DIR = (
PROJECT_ROOT
/ "output"
)

INTELLIGENCE_OUTPUT_PATH = (
OUTPUT_DIR
/ "cashflow_intelligence.xlsx"
)

DISTRESS_OUTPUT_PATH = (
OUTPUT_DIR
/ "distress_alerts.csv"
)

CAPITAL_ALLOCATION_OUTPUT_PATH = (
OUTPUT_DIR
/ "capital_allocation.csv"
)

DISTRIBUTION_OUTPUT_PATH = (
OUTPUT_DIR
/ "capital_allocation_distribution.csv"
)

PATTERN_CHANGES_OUTPUT_PATH = (
OUTPUT_DIR
/ "pattern_changes.csv"
)

LOG_PATH = (
OUTPUT_DIR
/ "cashflow_kpis.log"
)

# ---------------------------------------------------------

# Logging

# ---------------------------------------------------------

def configure_logging() -> None:
    """
    Configure logging.
    """
    
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    
    logger = logging.getLogger()
    
    if logger.handlers:
        return
    
    logger.setLevel(
        logging.INFO
    )
    
    formatter = logging.Formatter(
        "%(levelname)s | %(message)s"
    )
    
    file_handler = logging.FileHandler(
        LOG_PATH,
        encoding="utf-8",
    )
    
    file_handler.setFormatter(
        formatter
    )
    
    stream_handler = logging.StreamHandler()
    
    stream_handler.setFormatter(
        formatter
    )
    
    logger.addHandler(
        file_handler
    )
    
    logger.addHandler(
        stream_handler
    )
    
# ---------------------------------------------------------

# Normalization helpers

# ---------------------------------------------------------

def normalize_company_id(
    value: Any,
    ) -> str | None:
    """
    Normalize company identifier.
    """
    
    if value is None:
        return None
    
    if pd.isna(value):
        return None
    
    company_id = str(
        value
    ).strip().upper()
    
    if not company_id:
        return None
    
    return company_id
    
def normalize_year(
    value: Any,
    ) -> int | None:
    """
    Convert year values into integers.
    """
    
    if value is None:
        return None
    
    if pd.isna(value):
        return None
    
    text = str(
        value
    ).strip()
    
    if not text:
        return None
    
    try:
    
        return int(
            text[:4]
        )
    
    except (
        TypeError,
        ValueError,
    ):
    
        return None
    
def to_numeric(
    value: Any,
    ) -> float | None:
    """
    Safely convert value to float.
    """
    
    if value is None:
        return None
    
    if pd.isna(value):
        return None
    
    try:
    
        result = float(
            value
        )
    
        if pd.isna(result):
            return None
    
        return result
    
    except (
        TypeError,
        ValueError,
    ):
    
        return None
    
# ---------------------------------------------------------

# Data loading

# ---------------------------------------------------------

def load_data() -> dict[str, pd.DataFrame]:
    """
    Load required data from database.
    """
    
    logging.info(
        "Loading cash flow intelligence data from %s",
        DB_PATH,
    )
    
    if not DB_PATH.exists():
    
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )
    
    queries = {
    
        "companies": """
            SELECT
                CAST(id AS TEXT) AS company_id,
                company_name
            FROM companies
        """,
    
        "cashflow": """
            SELECT
                CAST(company_id AS TEXT) AS company_id,
                year,
                operating_activity,
                investing_activity,
                financing_activity,
                net_cash_flow
            FROM cashflow
        """,
    
        "profitandloss": """
            SELECT
                CAST(company_id AS TEXT) AS company_id,
                year,
                sales,
                operating_profit,
                net_profit
            FROM profitandloss
        """,
    
        "balancesheet": """
            SELECT
                CAST(company_id AS TEXT) AS company_id,
                year,
                borrowings
            FROM balancesheet
        """,
    
        "sectors": """
            SELECT
                CAST(company_id AS TEXT) AS company_id,
                broad_sector,
                sub_sector
            FROM sectors
        """,
    }
    
    data: dict[
        str,
        pd.DataFrame,
    ] = {}
    
    with sqlite3.connect(
        DB_PATH
    ) as connection:
    
        for name, query in queries.items():
    
            df = pd.read_sql_query(
                query,
                connection,
            )
    
            if (
                "company_id"
                in df.columns
            ):
    
                df[
                    "company_id"
                ] = df[
                    "company_id"
                ].apply(
                    normalize_company_id
                )
    
                df = df[
                    df[
                        "company_id"
                    ].notna()
                ].copy()
    
            if (
                "year"
                in df.columns
            ):
    
                df[
                    "year_numeric"
                ] = df[
                    "year"
                ].apply(
                    normalize_year
                )
    
            data[name] = df
    
            logging.info(
                "%s rows loaded: %s",
                name,
                len(df),
            )
    
    return data
    
# ---------------------------------------------------------

# Historical helpers

# ---------------------------------------------------------

def latest_row(
    df: pd.DataFrame,
    ) -> pd.Series | None:
    """
    Return latest row.
    """
    
    if df.empty:
        return None
    
    working_df = df.sort_values(
        by="year_numeric",
        ascending=False,
        na_position="last",
    )
    
    return working_df.iloc[0]
    
def latest_value(
    df: pd.DataFrame,
    column: str,
    ) -> float | None:
    """
    Return latest numeric value.
    """
    
    if (
        df.empty
        or column
        not in df.columns
    ):
        return None
    
    working_df = df.copy()
    
    working_df[
        column
    ] = pd.to_numeric(
        working_df[column],
        errors="coerce",
    )
    
    working_df = working_df[
        working_df[
            column
        ].notna()
    ].copy()
    
    if working_df.empty:
        return None
    
    row = latest_row(
        working_df
    )
    
    if row is None:
        return None
    
    return to_numeric(
        row[column]
    )
    
def latest_two_values(
    df: pd.DataFrame,
    column: str,
    ) -> list[float]:
    """
    Return latest two numeric values.
    """
    
    if (
        df.empty
        or column
        not in df.columns
    ):
        return []
    
    working_df = df.copy()
    
    working_df[
        column
    ] = pd.to_numeric(
        working_df[column],
        errors="coerce",
    )
    
    working_df = working_df[
        working_df[
            column
        ].notna()
    ].copy()
    
    working_df = working_df.sort_values(
        by="year_numeric",
        ascending=True,
    )
    
    return [
        float(value)
        for value
        in working_df[
            column
        ]
        .tail(2)
        .tolist()
    ]
    
# ---------------------------------------------------------

# CFO quality

# ---------------------------------------------------------

def calculate_cfo_quality(
    cashflow_df: pd.DataFrame,
    pnl_df: pd.DataFrame,
    ) -> tuple[float | None, str | None]:
    """
    Calculate average CFO/PAT ratio over
    latest 5 matching years.
    """
    
    if (
        cashflow_df.empty
        or pnl_df.empty
    ):
        return None, None
    
    cashflow = cashflow_df[
        [
            "year_numeric",
            "operating_activity",
        ]
    ].copy()
    
    pnl = pnl_df[
        [
            "year_numeric",
            "net_profit",
        ]
    ].copy()
    
    cashflow[
        "operating_activity"
    ] = pd.to_numeric(
        cashflow[
            "operating_activity"
        ],
        errors="coerce",
    )
    
    pnl[
        "net_profit"
    ] = pd.to_numeric(
        pnl[
            "net_profit"
        ],
        errors="coerce",
    )
    
    merged = cashflow.merge(
        pnl,
        on="year_numeric",
        how="inner",
    )
    
    merged = merged.dropna(
        subset=[
            "operating_activity",
            "net_profit",
        ]
    )
    
    merged = merged[
        merged[
            "net_profit"
        ]
        != 0
    ].copy()
    
    if merged.empty:
        return None, None
    
    merged = merged.sort_values(
        by="year_numeric",
        ascending=True,
    ).tail(
        5
    )
    
    return cfo_quality_score(
        merged[
            "operating_activity"
        ].tolist(),
        merged[
            "net_profit"
        ].tolist(),
    )
    
# ---------------------------------------------------------

# CapEx intensity

# ---------------------------------------------------------

def calculate_capex_intensity(
    cashflow_df: pd.DataFrame,
    pnl_df: pd.DataFrame,
    ) -> tuple[float | None, str | None]:
    """
    Calculate latest CapEx intensity.
    """
    
    if (
        cashflow_df.empty
        or pnl_df.empty
    ):
        return None, None
    
    cashflow = cashflow_df[
        [
            "year_numeric",
            "investing_activity",
        ]
    ].copy()
    
    pnl = pnl_df[
        [
            "year_numeric",
            "sales",
        ]
    ].copy()
    
    merged = cashflow.merge(
        pnl,
        on="year_numeric",
        how="inner",
    )
    
    merged[
        "investing_activity"
    ] = pd.to_numeric(
        merged[
            "investing_activity"
        ],
        errors="coerce",
    )
    
    merged[
        "sales"
    ] = pd.to_numeric(
        merged[
            "sales"
        ],
        errors="coerce",
    )
    
    merged = merged.dropna(
        subset=[
            "investing_activity",
            "sales",
        ]
    )
    
    if merged.empty:
        return None, None
    
    latest = merged.sort_values(
        by="year_numeric",
        ascending=False,
    ).iloc[0]
    
    return capex_intensity(
        float(
            latest[
                "investing_activity"
            ]
        ),
        float(
            latest[
                "sales"
            ]
        ),
    )
    
# ---------------------------------------------------------

# FCF helpers

# ---------------------------------------------------------

def calculate_fcf_history(
    cashflow_df: pd.DataFrame,
    ) -> pd.DataFrame:
    """
    FCF = CFO + Investing Activity.
    """
    
    if cashflow_df.empty:
        return pd.DataFrame(
            columns=[
                "year_numeric",
                "fcf",
            ]
        )
    
    working_df = cashflow_df[
        [
            "year_numeric",
            "operating_activity",
            "investing_activity",
        ]
    ].copy()
    
    working_df[
        "operating_activity"
    ] = pd.to_numeric(
        working_df[
            "operating_activity"
        ],
        errors="coerce",
    )
    
    working_df[
        "investing_activity"
    ] = pd.to_numeric(
        working_df[
            "investing_activity"
        ],
        errors="coerce",
    )
    
    working_df = working_df.dropna(
        subset=[
            "operating_activity",
            "investing_activity",
        ]
    )
    
    working_df[
        "fcf"
    ] = (
        working_df[
            "operating_activity"
        ]
        + working_df[
            "investing_activity"
        ]
    )
    
    return working_df[
        [
            "year_numeric",
            "fcf",
        ]
    ].sort_values(
        by="year_numeric"
    )
    
def calculate_fcf_cagr_5yr(
    cashflow_df: pd.DataFrame,
    ) -> float | None:
    """
    Calculate 5-year FCF CAGR.
    """
    
    history = calculate_fcf_history(
        cashflow_df
    )
    
    if len(history) < 5:
        return None
    
    values = history.tail(
        5
    ).reset_index(
        drop=True
    )
    
    beginning = to_numeric(
        values.loc[
            0,
            "fcf",
        ]
    )
    
    ending = to_numeric(
        values.loc[
            len(values) - 1,
            "fcf",
        ]
    )
    
    if (
        beginning is None
        or ending is None
        or beginning <= 0
        or ending <= 0
    ):
        return None
    
    periods = len(values) - 1
    
    result = (
        (
            ending
            / beginning
        )
        ** (
            1 / periods
        )
        - 1
    ) * 100
    
    return round(
        result,
        2,
    )
    
def calculate_fcf_conversion(
    cashflow_df: pd.DataFrame,
    pnl_df: pd.DataFrame,
    ) -> float | None:
    """
    Calculate latest FCF conversion.
    """
    
    if (
        cashflow_df.empty
        or pnl_df.empty
    ):
        return None
    
    cashflow = cashflow_df[
        [
            "year_numeric",
            "operating_activity",
            "investing_activity",
        ]
    ].copy()
    
    pnl = pnl_df[
        [
            "year_numeric",
            "operating_profit",
        ]
    ].copy()
    
    merged = cashflow.merge(
        pnl,
        on="year_numeric",
        how="inner",
    )
    
    merged = merged.sort_values(
        by="year_numeric",
        ascending=False,
    )
    
    for _, row in merged.iterrows():
    
        cfo = to_numeric(
            row[
                "operating_activity"
            ]
        )
    
        cfi = to_numeric(
            row[
                "investing_activity"
            ]
        )
    
        operating_profit = to_numeric(
            row[
                "operating_profit"
            ]
        )
    
        if (
            cfo is None
            or cfi is None
            or operating_profit is None
        ):
            continue
    
        fcf = free_cash_flow(
            cfo,
            cfi,
        )
    
        result = fcf_conversion_rate(
            fcf,
            operating_profit,
        )
    
        if result is not None:
            return round(
                result,
                2,
            )
    
    return None
    
# ---------------------------------------------------------

# Distress detection

# ---------------------------------------------------------

def detect_distress(
    cashflow_df: pd.DataFrame,
    ) -> tuple[
    bool,
    float | None,
    float | None,
    ]:
    """
    Distress:
    
    CFO < 0
    AND
    CFF > 0
    """
    
    latest = latest_row(
        cashflow_df
    )
    
    if latest is None:
        return False, None, None
    
    cfo = to_numeric(
        latest.get(
            "operating_activity"
        )
    )
    
    cff = to_numeric(
        latest.get(
            "financing_activity"
        )
    )
    
    if (
        cfo is None
        or cff is None
    ):
        return False, cfo, cff
    
    return (
        cfo < 0
        and cff > 0
    ), cfo, cff
    
# ---------------------------------------------------------

# Deleveraging detection

# ---------------------------------------------------------

def detect_deleveraging(
    cashflow_df: pd.DataFrame,
    balance_df: pd.DataFrame,
    ) -> bool:
    """
    Latest CFF < 0
    AND
    borrowings declining.
    """
    
    latest_cff = latest_value(
        cashflow_df,
        "financing_activity",
    )
    
    borrowings = latest_two_values(
        balance_df,
        "borrowings",
    )
    
    if (
        latest_cff is None
        or len(borrowings) < 2
    ):
        return False
    
    return (
        latest_cff < 0
        and borrowings[-1]
        < borrowings[-2]
    )
    
# ---------------------------------------------------------

# Capital allocation history

# ---------------------------------------------------------

def sign_label(
    value: float | None,
    ) -> str:
    """
    Convert value to +, -, or 0.
    """
    
    if value is None:
        return "0"
    
    if value > 0:
        return "+"
    
    if value < 0:
        return "-"
    
    return "0"
    
def build_capital_allocation_history(
    cashflow_df: pd.DataFrame,
    pnl_df: pd.DataFrame,
    ) -> pd.DataFrame:
    """
    Build capital allocation history for
    every available cashflow year.
    
    This is the key Day 32 fix.
    
    One output row is generated for every
    company-year present in the cashflow table.
    """
    
    if cashflow_df.empty:
    
        return pd.DataFrame(
            columns=[
                "company_id",
                "year",
                "year_numeric",
                "cfo_sign",
                "cfi_sign",
                "cff_sign",
                "pattern_label",
            ]
        )
    
    working_df = cashflow_df.copy()
    
    working_df[
        "operating_activity"
    ] = pd.to_numeric(
        working_df[
            "operating_activity"
        ],
        errors="coerce",
    )
    
    working_df[
        "investing_activity"
    ] = pd.to_numeric(
        working_df[
            "investing_activity"
        ],
        errors="coerce",
    )
    
    working_df[
        "financing_activity"
    ] = pd.to_numeric(
        working_df[
            "financing_activity"
        ],
        errors="coerce",
    )
    
    pnl_lookup = {}
    
    if not pnl_df.empty:
    
        pnl_working = pnl_df[
            [
                "year_numeric",
                "net_profit",
            ]
        ].copy()
    
        pnl_working[
            "net_profit"
        ] = pd.to_numeric(
            pnl_working[
                "net_profit"
            ],
            errors="coerce",
        )
    
        for _, row in pnl_working.iterrows():
    
            year = row[
                "year_numeric"
            ]
    
            net_profit = row[
                "net_profit"
            ]
    
            if (
                pd.notna(year)
                and pd.notna(net_profit)
                and net_profit != 0
            ):
    
                pnl_lookup[
                    int(year)
                ] = float(
                    net_profit
                )
    
    records = []
    
    for _, row in working_df.iterrows():
    
        cfo = to_numeric(
            row[
                "operating_activity"
            ]
        )
    
        cfi = to_numeric(
            row[
                "investing_activity"
            ]
        )
    
        cff = to_numeric(
            row[
                "financing_activity"
            ]
        )
    
        cfo = 0.0 if cfo is None else cfo
        cfi = 0.0 if cfi is None else cfi
        cff = 0.0 if cff is None else cff
    
        year_numeric = row[
            "year_numeric"
        ]
    
        cfo_pat_ratio = None
    
        if (
            pd.notna(
                year_numeric
            )
            and int(
                year_numeric
            )
            in pnl_lookup
        ):
    
            net_profit = pnl_lookup[
                int(
                    year_numeric
                )
            ]
    
            if net_profit != 0:
    
                cfo_pat_ratio = (
                    cfo
                    / net_profit
                )
    
        pattern_label = (
            capital_allocation_pattern(
                cfo,
                cfi,
                cff,
                cfo_pat_ratio,
            )
        )
    
        records.append(
            {
                "company_id": row[
                    "company_id"
                ],
                "year": row[
                    "year"
                ],
                "year_numeric": year_numeric,
                "cfo_sign": sign_label(
                    cfo
                ),
                "cfi_sign": sign_label(
                    cfi
                ),
                "cff_sign": sign_label(
                    cff
                ),
                "pattern_label": (
                    pattern_label
                ),
            }
        )
    
    return pd.DataFrame(
        records
    )
    
# ---------------------------------------------------------

# Day 32 verification

# ---------------------------------------------------------

def verify_capital_allocation_coverage(
    capital_allocation_df: pd.DataFrame,
    cashflow_df: pd.DataFrame,
    ) -> None:
    """
    Verify capital allocation covers every
    company-year available in cashflow data.
    """
    
    expected = cashflow_df[
        [
            "company_id",
            "year_numeric",
        ]
    ].dropna().drop_duplicates()
    
    generated = capital_allocation_df[
        [
            "company_id",
            "year_numeric",
        ]
    ].dropna().drop_duplicates()
    
    merged = expected.merge(
        generated,
        on=[
            "company_id",
            "year_numeric",
        ],
        how="left",
        indicator=True,
    )
    
    missing = merged[
        merged[
            "_merge"
        ]
        != "both"
    ]
    
    if not missing.empty:
    
        missing_records = [
            (
                f"{row.company_id} "
                f"({int(row.year_numeric)})"
            )
            for row in missing.itertuples()
        ]
    
        raise ValueError(
            "Missing capital allocation records: "
            + ", ".join(
                missing_records
            )
        )
    
    logging.info(
        "Capital allocation coverage passed "
        "for %s company-year records",
        len(expected),
    )
    
# ---------------------------------------------------------

# Distribution summary

# ---------------------------------------------------------

def generate_distribution_summary(
    capital_allocation_df: pd.DataFrame,
    ) -> pd.DataFrame:
    """
    Count companies in each pattern
    for the latest available year.
    """
    
    if capital_allocation_df.empty:
    
        return pd.DataFrame(
            columns=[
                "pattern_label",
                "company_count",
            ]
        )
    
    latest_rows = (
        capital_allocation_df
        .sort_values(
            by=[
                "company_id",
                "year_numeric",
            ],
            ascending=[
                True,
                False,
            ],
        )
        .groupby(
            "company_id",
            as_index=False,
        )
        .first()
    )
    
    distribution = (
        latest_rows[
            "pattern_label"
        ]
        .value_counts()
        .rename_axis(
            "pattern_label"
        )
        .reset_index(
            name="company_count"
        )
    )
    
    return distribution.sort_values(
        by="company_count",
        ascending=False,
    ).reset_index(
        drop=True
    )
    
# ---------------------------------------------------------

# Pattern changes

# ---------------------------------------------------------

def generate_pattern_changes(
    capital_allocation_df: pd.DataFrame,
    ) -> pd.DataFrame:
    """
    Detect year-over-year pattern changes.
    
    Example:
    
    Reinvestor -> Distress Signal
    """
    
    columns = [
        "company_id",
        "previous_year",
        "previous_pattern",
        "year",
        "pattern_label",
        "change_description",
    ]
    
    if capital_allocation_df.empty:
    
        return pd.DataFrame(
            columns=columns
        )
    
    working_df = (
        capital_allocation_df
        .sort_values(
            by=[
                "company_id",
                "year_numeric",
            ],
            ascending=[
                True,
                True,
            ],
        )
        .copy()
    )
    
    records = []
    
    for company_id, group in (
        working_df.groupby(
            "company_id"
        )
    ):
    
        group = group.reset_index(
            drop=True
        )
    
        for index in range(
            1,
            len(group),
        ):
    
            previous_row = group.iloc[
                index - 1
            ]
    
            current_row = group.iloc[
                index
            ]
    
            previous_pattern = (
                previous_row[
                    "pattern_label"
                ]
            )
    
            current_pattern = (
                current_row[
                    "pattern_label"
                ]
            )
    
            if (
                previous_pattern
                != current_pattern
            ):
    
                records.append(
                    {
                        "company_id": (
                            company_id
                        ),
                        "previous_year": (
                            previous_row[
                                "year"
                            ]
                        ),
                        "previous_pattern": (
                            previous_pattern
                        ),
                        "year": (
                            current_row[
                                "year"
                            ]
                        ),
                        "pattern_label": (
                            current_pattern
                        ),
                        "change_description": (
                            f"{previous_pattern} "
                            f"-> "
                            f"{current_pattern}"
                        ),
                    }
                )
    
    return pd.DataFrame(
        records,
        columns=columns,
    )
    
    
# ---------------------------------------------------------

# Sector helper

# ---------------------------------------------------------

def get_sector(
    sector_df: pd.DataFrame,
    ) -> str | None:
    """
    Return broad sector.
    """
    
    
    if sector_df.empty:
        return None
    
    row = sector_df.iloc[0]
    
    broad_sector = row.get(
        "broad_sector"
    )
    
    sub_sector = row.get(
        "sub_sector"
    )
    
    if (
        pd.notna(
            broad_sector
        )
        and str(
            broad_sector
        ).strip()
    ):
        return str(
            broad_sector
        ).strip()
    
    if (
        pd.notna(
            sub_sector
        )
        and str(
            sub_sector
        ).strip()
    ):
        return str(
            sub_sector
        ).strip()
    
    return None
    
    
# ---------------------------------------------------------

# Main intelligence engine

# ---------------------------------------------------------

def generate_cashflow_intelligence(
    data: dict[str, pd.DataFrame],
    ) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    ]:
    
    
    companies_df = data[
        "companies"
    ]
    
    cashflow_df = data[
        "cashflow"
    ]
    
    pnl_df = data[
        "profitandloss"
    ]
    
    balance_df = data[
        "balancesheet"
    ]
    
    sectors_df = data[
        "sectors"
    ]
    
    company_ids = sorted(
        companies_df[
            "company_id"
        ]
        .dropna()
        .unique()
        .tolist()
    )
    
    logging.info(
        "Companies to process: %s",
        len(company_ids),
    )
    
    intelligence_records = []
    
    distress_records = []
    
    capital_history_frames = []
    
    for company_id in company_ids:
    
        company_cashflow = cashflow_df[
            cashflow_df[
                "company_id"
            ]
            == company_id
        ].copy()
    
        company_pnl = pnl_df[
            pnl_df[
                "company_id"
            ]
            == company_id
        ].copy()
    
        company_balance = balance_df[
            balance_df[
                "company_id"
            ]
            == company_id
        ].copy()
    
        company_sector = sectors_df[
            sectors_df[
                "company_id"
            ]
            == company_id
        ].copy()
    
        sector = get_sector(
            company_sector
        )
    
        cfo_score, cfo_label = (
            calculate_cfo_quality(
                company_cashflow,
                company_pnl,
            )
        )
    
        capex_pct, capex_label = (
            calculate_capex_intensity(
                company_cashflow,
                company_pnl,
            )
        )
    
        fcf_cagr = (
            calculate_fcf_cagr_5yr(
                company_cashflow
            )
        )
    
        fcf_conversion = (
            calculate_fcf_conversion(
                company_cashflow,
                company_pnl,
            )
        )
    
        distress_flag, latest_cfo, latest_cff = (
            detect_distress(
                company_cashflow
            )
        )
    
        deleveraging_flag = (
            detect_deleveraging(
                company_cashflow,
                company_balance,
            )
        )
    
        company_capital_history = (
            build_capital_allocation_history(
                company_cashflow,
                company_pnl,
            )
        )
    
        if (
            not company_capital_history.empty
        ):
    
            capital_history_frames.append(
                company_capital_history
            )
    
            latest_capital_row = (
                company_capital_history
                .sort_values(
                    by="year_numeric",
                    ascending=False,
                )
                .iloc[0]
            )
    
            capital_allocation_label = (
                latest_capital_row[
                    "pattern_label"
                ]
            )
    
        else:
    
            capital_allocation_label = None
    
        intelligence_records.append(
            {
                "company_id": company_id,
                "sector": sector,
                "cfo_quality_score": (
                    round(
                        cfo_score,
                        2,
                    )
                    if cfo_score is not None
                    else None
                ),
                "cfo_quality_label": (
                    cfo_label
                ),
                "capex_intensity_pct": (
                    round(
                        capex_pct,
                        2,
                    )
                    if capex_pct is not None
                    else None
                ),
                "capex_label": (
                    capex_label
                ),
                "fcf_cagr_5yr": (
                    fcf_cagr
                ),
                "fcf_conversion_pct": (
                    fcf_conversion
                ),
                "distress_flag": (
                    bool(
                        distress_flag
                    )
                ),
                "deleveraging_flag": (
                    bool(
                        deleveraging_flag
                    )
                ),
                "capital_allocation_label": (
                    capital_allocation_label
                ),
            }
        )
    
        if distress_flag:
    
            latest_net_profit = (
                latest_value(
                    company_pnl,
                    "net_profit",
                )
            )
    
            distress_records.append(
                {
                    "company_id": company_id,
                    "cfo_value": latest_cfo,
                    "cff_value": latest_cff,
                    "latest_net_profit": (
                        latest_net_profit
                    ),
                }
            )
    
    output_columns = [
        "company_id",
        "sector",
        "cfo_quality_score",
        "cfo_quality_label",
        "capex_intensity_pct",
        "capex_label",
        "fcf_cagr_5yr",
        "fcf_conversion_pct",
        "distress_flag",
        "deleveraging_flag",
        "capital_allocation_label",
    ]
    
    distress_columns = [
        "company_id",
        "cfo_value",
        "cff_value",
        "latest_net_profit",
    ]
    
    intelligence_df = pd.DataFrame(
        intelligence_records,
        columns=output_columns,
    )
    
    distress_df = pd.DataFrame(
        distress_records,
        columns=distress_columns,
    )
    
    if capital_history_frames:
    
        capital_allocation_df = pd.concat(
            capital_history_frames,
            ignore_index=True,
        )
    
    else:
    
        capital_allocation_df = (
            pd.DataFrame()
        )
    
    intelligence_df = (
        intelligence_df
        .sort_values(
            by="company_id"
        )
        .reset_index(
            drop=True
        )
    )
    
    distress_df = (
        distress_df
        .sort_values(
            by="company_id"
        )
        .reset_index(
            drop=True
        )
    )
    
    capital_allocation_df = (
        capital_allocation_df
        .sort_values(
            by=[
                "company_id",
                "year_numeric",
            ]
        )
        .reset_index(
            drop=True
        )
    )
    
    return (
        intelligence_df,
        distress_df,
        capital_allocation_df,
    )
    
    
# ---------------------------------------------------------

# Company coverage

# ---------------------------------------------------------

def verify_company_coverage(
    intelligence_df: pd.DataFrame,
    companies_df: pd.DataFrame,
    ) -> None:
    
    
    expected_companies = set(
        companies_df[
            "company_id"
        ]
        .dropna()
        .tolist()
    )
    
    generated_companies = set(
        intelligence_df[
            "company_id"
        ]
        .dropna()
        .tolist()
    )
    
    missing = (
        expected_companies
        - generated_companies
    )
    
    if missing:
    
        raise ValueError(
            "Companies missing cash flow intelligence: "
            + ", ".join(
                sorted(
                    missing
                )
            )
        )
    
    logging.info(
        "Company coverage passed for %s companies",
        len(
            expected_companies
        ),
    )
    
# ---------------------------------------------------------

# Output writing

# ---------------------------------------------------------

def save_outputs(
    intelligence_df: pd.DataFrame,
    distress_df: pd.DataFrame,
    capital_allocation_df: pd.DataFrame,
    distribution_df: pd.DataFrame,
    pattern_changes_df: pd.DataFrame,
    ) -> None:
    """
    Save all Day 31 and Day 32 outputs.
    """
    
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    
    intelligence_df.to_excel(
        INTELLIGENCE_OUTPUT_PATH,
        index=False,
    )
    
    distress_df.to_csv(
        DISTRESS_OUTPUT_PATH,
        index=False,
    )
    
    capital_allocation_df[
        [
            "company_id",
            "year",
            "cfo_sign",
            "cfi_sign",
            "cff_sign",
            "pattern_label",
        ]
    ].to_csv(
        CAPITAL_ALLOCATION_OUTPUT_PATH,
        index=False,
    )
    
    distribution_df.to_csv(
        DISTRIBUTION_OUTPUT_PATH,
        index=False,
    )
    
    pattern_changes_df.to_csv(
        PATTERN_CHANGES_OUTPUT_PATH,
        index=False,
    )
    
    logging.info(
        "Cash flow intelligence saved: %s",
        INTELLIGENCE_OUTPUT_PATH,
    )
    
    logging.info(
        "Distress alerts saved: %s",
        DISTRESS_OUTPUT_PATH,
    )
    
    logging.info(
        "Capital allocation saved: %s",
        CAPITAL_ALLOCATION_OUTPUT_PATH,
    )
    
    logging.info(
        "Capital allocation distribution saved: %s",
        DISTRIBUTION_OUTPUT_PATH,
    )
    
    logging.info(
        "Pattern changes saved: %s",
        PATTERN_CHANGES_OUTPUT_PATH,
    )
    
# ---------------------------------------------------------

# Main execution

# ---------------------------------------------------------

def run_cashflow_intelligence() -> None:
    """
    Execute Day 31 + Day 32 modules.
    """
    
    configure_logging()
    
    logging.info(
        "Starting Cash Flow Intelligence "
        "and Capital Allocation Module"
    )
    
    data = load_data()
    
    (
        intelligence_df,
        distress_df,
        capital_allocation_df,
    ) = generate_cashflow_intelligence(
        data
    )
    
    verify_company_coverage(
        intelligence_df,
        data[
            "companies"
        ],
    )
    
    verify_capital_allocation_coverage(
        capital_allocation_df,
        data[
            "cashflow"
        ],
    )
    
    distribution_df = (
        generate_distribution_summary(
            capital_allocation_df
        )
    )
    
    pattern_changes_df = (
        generate_pattern_changes(
            capital_allocation_df
        )
    )
    
    save_outputs(
        intelligence_df,
        distress_df,
        capital_allocation_df,
        distribution_df,
        pattern_changes_df,
    )
    
    print(
        "\nDay 31 + Day 32 completed successfully."
    )
    
    print(
        f"Companies processed: "
        f"{len(intelligence_df)}"
    )
    
    print(
        f"Capital allocation records: "
        f"{len(capital_allocation_df)}"
    )
    
    print(
        f"Distress alerts: "
        f"{len(distress_df)}"
    )
    
    print(
        f"Pattern changes: "
        f"{len(pattern_changes_df)}"
    )
    
    print(
        "\nOutputs:"
    )
    
    print(
        f"  {INTELLIGENCE_OUTPUT_PATH}"
    )
    
    print(
        f"  {DISTRESS_OUTPUT_PATH}"
    )
    
    print(
        f"  {CAPITAL_ALLOCATION_OUTPUT_PATH}"
    )
    
    print(
        f"  {DISTRIBUTION_OUTPUT_PATH}"
    )
    
    print(
        f"  {PATTERN_CHANGES_OUTPUT_PATH}"
    )
    
    
if __name__ == "__main__":
    run_cashflow_intelligence()
