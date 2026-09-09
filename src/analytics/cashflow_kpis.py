"""
Day 31 — Cash Flow Intelligence Module

Generates company-level cash flow intelligence using
historical financial data from the N100 database.

Outputs:

output/cashflow_intelligence.xlsx
output/distress_alerts.csv

Columns:

company_id
sector
cfo_quality_score
cfo_quality_label
capex_intensity_pct
capex_label
fcf_cagr_5yr
fcf_conversion_pct
distress_flag
deleveraging_flag
capital_allocation_label
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

LOG_PATH = (
    OUTPUT_DIR
    / "cashflow_kpis.log"
)


# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------

def configure_logging() -> None:
    """
    Configure Day 31 logging.
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
    Safely convert a value to float.
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
    Load Day 31 data.
    """

    logging.info(
        "Loading Day 31 data from %s",
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
    Return latest row by year.
    """

    if df.empty:
        return None

    working_df = df.sort_values(
        by="year_numeric",
        ascending=False,
        na_position="last",
    )

    return working_df.iloc[0]


def latest_n_rows(
    df: pd.DataFrame,
    count: int,
) -> pd.DataFrame:
    """
    Return latest rows in chronological order.
    """

    if df.empty:
        return df.copy()

    working_df = df.sort_values(
        by="year_numeric",
        ascending=True,
        na_position="last",
    )

    return working_df.tail(
        count
    ).copy()


def latest_value(
    df: pd.DataFrame,
    column: str,
) -> float | None:
    """
    Return latest available numeric value.
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
        na_position="last",
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
    the latest 5 matching years.

    Years with PAT equal to zero are ignored.
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

    cfo_values = merged[
        "operating_activity"
    ].tolist()

    pat_values = merged[
        "net_profit"
    ].tolist()

    return cfo_quality_score(
        cfo_values,
        pat_values,
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

    cashflow[
        "investing_activity"
    ] = pd.to_numeric(
        cashflow[
            "investing_activity"
        ],
        errors="coerce",
    )

    pnl[
        "sales"
    ] = pd.to_numeric(
        pnl[
            "sales"
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
            "investing_activity",
            "sales",
        ]
    )

    if merged.empty:
        return None, None

    merged = merged.sort_values(
        by="year_numeric",
        ascending=False,
    )

    latest = merged.iloc[0]

    investing_activity = to_numeric(
        latest[
            "investing_activity"
        ]
    )

    sales = to_numeric(
        latest[
            "sales"
        ]
    )

    if (
        investing_activity is None
        or sales is None
    ):
        return None, None

    return capex_intensity(
        investing_activity,
        sales,
    )


# ---------------------------------------------------------
# FCF helpers
# ---------------------------------------------------------

def calculate_fcf_history(
    cashflow_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate FCF history.

    FCF = CFO + Investing Activity
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

    if working_df.empty:
        return pd.DataFrame(
            columns=[
                "year_numeric",
                "fcf",
            ]
        )

    working_df[
        "fcf"
    ] = working_df.apply(
        lambda row: free_cash_flow(
            row[
                "operating_activity"
            ],
            row[
                "investing_activity"
            ],
        ),
        axis=1,
    )

    return working_df[
        [
            "year_numeric",
            "fcf",
        ]
    ].sort_values(
        by="year_numeric",
        ascending=True,
    )


def calculate_fcf_cagr_5yr(
    cashflow_df: pd.DataFrame,
) -> float | None:
    """
    Calculate FCF CAGR across 5 years.

    Returns None when CAGR is mathematically invalid.
    """

    fcf_history = calculate_fcf_history(
        cashflow_df
    )

    if len(fcf_history) < 5:
        return None

    values = fcf_history.tail(
        5
    ).reset_index(
        drop=True
    )

    beginning_fcf = to_numeric(
        values.loc[
            0,
            "fcf",
        ]
    )

    ending_fcf = to_numeric(
        values.loc[
            len(values) - 1,
            "fcf",
        ]
    )

    if (
        beginning_fcf is None
        or ending_fcf is None
        or beginning_fcf <= 0
        or ending_fcf <= 0
    ):
        return None

    periods = (
        len(values) - 1
    )

    if periods <= 0:
        return None

    cagr = (
        (
            ending_fcf
            / beginning_fcf
        )
        ** (
            1 / periods
        )
        - 1
    ) * 100

    return round(
        cagr,
        2,
    )


def calculate_fcf_conversion(
    cashflow_df: pd.DataFrame,
    pnl_df: pd.DataFrame,
) -> float | None:
    """
    Calculate latest FCF conversion rate.

    FCF / Operating Profit * 100
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

    if merged.empty:
        return None

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
) -> tuple[bool, float | None, float | None]:
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
    Deleveraging:

    Latest CFF < 0
    AND
    Latest borrowings < previous year borrowings.
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

    previous_borrowings = borrowings[-2]
    latest_borrowings = borrowings[-1]

    return (
        latest_cff < 0
        and latest_borrowings
        < previous_borrowings
    )


# ---------------------------------------------------------
# Capital allocation
# ---------------------------------------------------------

def calculate_capital_allocation(
    cashflow_df: pd.DataFrame,
    cfo_quality: float | None,
) -> str | None:
    """
    Calculate latest capital allocation label.
    """

    latest = latest_row(
        cashflow_df
    )

    if latest is None:
        return None

    cfo = to_numeric(
        latest.get(
            "operating_activity"
        )
    )

    cfi = to_numeric(
        latest.get(
            "investing_activity"
        )
    )

    cff = to_numeric(
        latest.get(
            "financing_activity"
        )
    )

    if (
        cfo is None
        or cfi is None
        or cff is None
    ):
        return None

    return capital_allocation_pattern(
        cfo,
        cfi,
        cff,
        cfo_quality,
    )


# ---------------------------------------------------------
# Sector helper
# ---------------------------------------------------------

def get_sector(
    sector_df: pd.DataFrame,
) -> str | None:
    """
    Return best available sector name.
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
]:
    """
    Generate cash flow intelligence
    and distress alerts.
    """

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

        capital_allocation = (
            calculate_capital_allocation(
                company_cashflow,
                cfo_score,
            )
        )

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
                "cfo_quality_label": cfo_label,
                "capex_intensity_pct": (
                    round(
                        capex_pct,
                        2,
                    )
                    if capex_pct is not None
                    else None
                ),
                "capex_label": capex_label,
                "fcf_cagr_5yr": fcf_cagr,
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
                    capital_allocation
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

    intelligence_df = intelligence_df.sort_values(
        by="company_id"
    ).reset_index(
        drop=True
    )

    distress_df = distress_df.sort_values(
        by="company_id"
    ).reset_index(
        drop=True
    )

    return (
        intelligence_df,
        distress_df,
    )


# ---------------------------------------------------------
# Verification
# ---------------------------------------------------------

def verify_company_coverage(
    intelligence_df: pd.DataFrame,
    companies_df: pd.DataFrame,
) -> None:
    """
    Verify every company is present.
    """

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
        "Coverage verification passed for %s companies",
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
) -> None:
    """
    Save Day 31 outputs.
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

    logging.info(
        "Cash flow intelligence saved: %s",
        INTELLIGENCE_OUTPUT_PATH,
    )

    logging.info(
        "Distress alerts saved: %s",
        DISTRESS_OUTPUT_PATH,
    )


# ---------------------------------------------------------
# Main execution
# ---------------------------------------------------------

def run_cashflow_intelligence() -> None:
    """
    Execute Day 31 Cash Flow Intelligence Module.
    """

    configure_logging()

    logging.info(
        "Starting Day 31 Cash Flow Intelligence Module"
    )

    data = load_data()

    intelligence_df, distress_df = (
        generate_cashflow_intelligence(
            data
        )
    )

    verify_company_coverage(
        intelligence_df,
        data[
            "companies"
        ],
    )

    save_outputs(
        intelligence_df,
        distress_df,
    )

    print(
        "\nDay 31 Cash Flow Intelligence "
        "Module completed successfully."
    )

    print(
        f"Companies processed: {len(intelligence_df)}"
    )

    print(
        f"Distress alerts: {len(distress_df)}"
    )

    print(
        f"\nIntelligence output:"
    )

    print(
        f"  {INTELLIGENCE_OUTPUT_PATH}"
    )

    print(
        f"\nDistress alerts:"
    )

    print(
        f"  {DISTRESS_OUTPUT_PATH}"
    )


if __name__ == "__main__":
    run_cashflow_intelligence()