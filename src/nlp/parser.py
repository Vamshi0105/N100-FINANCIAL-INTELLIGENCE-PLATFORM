"""
Day 29 â€” NLP Analysis Text Parser

Parses text-based analysis metrics from:

data/raw/analysis.xlsx

Target fields:

compounded_sales_growth
compounded_profit_growth
stock_price_cagr
roe

Expected examples:

10 Years: 21%
5 Years: 10%
3 Years: -1%

Required base regex pattern:

(\\d+)\\s*Years?:?\\s*([\\d.]+)%

The parser also accepts optional whitespace and negative percentages.

Outputs:

output/analysis_parsed.csv
output/parse_failures.csv
output/cagr_manual_review.csv

Cross-validation:

compounded_sales_growth
    -> financial_ratios.revenue_cagr_3yr
    -> financial_ratios.revenue_cagr_5yr
    -> financial_ratios.revenue_cagr_10yr

compounded_profit_growth
    -> financial_ratios.pat_cagr_3yr
    -> financial_ratios.pat_cagr_5yr
    -> financial_ratios.pat_cagr_10yr

A difference greater than 5 percentage points is flagged
for manual review.
"""

from __future__ import annotations

import logging
import re
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

# ---------------------------------------------------------

# Project paths

# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ANALYSIS_PATH = (
PROJECT_ROOT
/ "data"
/ "raw"
/ "analysis.xlsx"
)

DB_PATH = (
PROJECT_ROOT
/ "data"
/ "nifty100.db"
)

OUTPUT_DIR = (
PROJECT_ROOT
/ "output"
)

PARSED_OUTPUT_PATH = (
OUTPUT_DIR
/ "analysis_parsed.csv"
)

FAILURES_OUTPUT_PATH = (
OUTPUT_DIR
/ "parse_failures.csv"
)

MANUAL_REVIEW_OUTPUT_PATH = (
OUTPUT_DIR
/ "cagr_manual_review.csv"
)

LOG_PATH = (
OUTPUT_DIR
/ "nlp_parser.log"
)

# ---------------------------------------------------------

# Configuration

# ---------------------------------------------------------

TARGET_FIELDS = [
"compounded_sales_growth",
"compounded_profit_growth",
"stock_price_cagr",
"roe",
]

# Base pattern requested in Day 29.

#

# Original:

#

# (\d+)\s*Years?:?\s*([\d.]+)%

#

# Extended slightly to support negative values such as:

#

# 3 Years: -1%

#

PERIOD_PATTERN = re.compile(
r"(\d+)\s*Years?\s*:?\s*(-?[\d.]+)\s*%",
re.IGNORECASE,
)

CAGR_COLUMN_MAP = {
"compounded_sales_growth": {
3: "revenue_cagr_3yr",
5: "revenue_cagr_5yr",
10: "revenue_cagr_10yr",
},
"compounded_profit_growth": {
3: "pat_cagr_3yr",
5: "pat_cagr_5yr",
10: "pat_cagr_10yr",
},
}

DIVERGENCE_THRESHOLD = 5.0

# ---------------------------------------------------------

# Logging

# ---------------------------------------------------------

def configure_logging() -> None:
    """
    Configure Day 29 parser logging.
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

# Utility functions

# ---------------------------------------------------------

def normalize_column_name(
    value: Any,
    ) -> str:
    """
    Normalize a column name for comparison.
    """

    if value is None:
        return ""

    return (
        str(value)
        .strip()
        .lower()
        .replace("\n", " ")
        .replace("\r", " ")
    )

def normalize_company_id(
    value: Any,
    ) -> str | None:
    """
    Normalize stock-symbol company identifiers.
    """

    if value is None:
        return None

    if pd.isna(value):
        return None

    company_id = (
        str(value)
        .strip()
        .upper()
    )

    if not company_id:
        return None

    return company_id

def normalize_text(
    value: Any,
    ) -> str | None:
    """
    Safely normalize an analysis text value.
    """

    if value is None:
        return None

    if pd.isna(value):
        return None

    text = (
        str(value)
        .replace("\n", " ")
        .replace("\r", " ")
        .strip()
    )

    if not text:
        return None

    return text

def normalize_year(
    value: Any,
    ) -> int | None:
    """
    Convert year values such as:

        2024
        2024-03
        2024-12
        2024-03-31

    into:

        2024
    """

    if value is None:
        return None

    if pd.isna(value):
        return None

    text = str(value).strip()

    if not text:
        return None

    match = re.match(
        r"^(\d{4})",
        text,
    )

    if match:
        return int(
            match.group(1)
        )

    try:
        return int(
            float(text)
        )
    except (
        TypeError,
        ValueError,
    ):
        return None

# ---------------------------------------------------------

# Excel loading

# ---------------------------------------------------------

def find_header_row(
    raw_df: pd.DataFrame,
    ) -> int:
    """
    Find the row containing the actual analysis headers.

    The analysis.xlsx file has metadata above the
    real header row.

    Expected header row contains:

        company_id
        compounded_sales_growth
        compounded_profit_growth
        stock_price_cagr
        roe
    """

    required = {
        "company_id",
        "compounded_sales_growth",
        "compounded_profit_growth",
        "stock_price_cagr",
        "roe",
    }

    for index in raw_df.index:

        row_values = {
            normalize_column_name(value)
            for value in raw_df.loc[index].tolist()
        }

        if required.issubset(
            row_values
        ):
            return int(index)

    raise ValueError(
        "Could not find analysis header row "
        "containing all required fields."
    )

def load_analysis_data() -> pd.DataFrame:
    """
    Load and normalize analysis.xlsx.
    """

    logging.info(
        "Loading analysis data from %s",
        ANALYSIS_PATH,
    )

    if not ANALYSIS_PATH.exists():
        raise FileNotFoundError(
            f"analysis.xlsx not found: {ANALYSIS_PATH}"
        )

    raw_df = pd.read_excel(
        ANALYSIS_PATH,
        header=None,
    )

    header_row = find_header_row(
        raw_df
    )

    logging.info(
        "Detected analysis header row: %s",
        header_row,
    )

    headers = [
        normalize_column_name(value)
        for value in raw_df.loc[
            header_row
        ].tolist()
    ]

    data_df = raw_df.iloc[
        header_row + 1:
    ].copy()

    data_df.columns = headers

    data_df = data_df.dropna(
        how="all"
    )

    if "company_id" not in data_df.columns:
        raise ValueError(
            "analysis.xlsx does not contain company_id"
        )

    missing_fields = [
        field
        for field in TARGET_FIELDS
        if field not in data_df.columns
    ]

    if missing_fields:
        raise ValueError(
            "analysis.xlsx is missing required fields: "
            + ", ".join(
                missing_fields
            )
        )

    data_df[
        "company_id"
    ] = data_df[
        "company_id"
    ].apply(
        normalize_company_id
    )

    data_df = data_df[
        data_df["company_id"].notna()
    ].copy()

    logging.info(
        "Analysis rows loaded: %s",
        len(data_df),
    )

    logging.info(
        "Unique analysis companies: %s",
        data_df[
            "company_id"
        ].nunique(),
    )

    return data_df

# ---------------------------------------------------------

# Regex parsing

# ---------------------------------------------------------

def parse_metric_text(
    company_id: str,
    metric_type: str,
    raw_value: Any,
    ) -> tuple[
    dict[str, Any] | None,
    dict[str, Any] | None,
    ]:
    """
    Parse one analysis metric text field.

    Returns:

        (parsed_record, failure_record)

    Example:

        10 Years: 21%

    becomes:

        {
            company_id: TCS,
            metric_type: compounded_sales_growth,
            period_years: 10,
            value_pct: 21.0
        }
    """

    raw_text = normalize_text(
        raw_value
    )

    if raw_text is None:
        return (
            None,
            {
                "company_id": company_id,
                "metric_type": metric_type,
                "raw_text": "",
                "failure_reason": "empty_value",
            },
        )

    match = PERIOD_PATTERN.search(
        raw_text
    )

    if not match:
        return (
            None,
            {
                "company_id": company_id,
                "metric_type": metric_type,
                "raw_text": raw_text,
                "failure_reason": "regex_no_match",
            },
        )

    try:
        period_years = int(
            match.group(1)
        )

        value_pct = float(
            match.group(2)
        )

    except (
        TypeError,
        ValueError,
    ):
        return (
            None,
            {
                "company_id": company_id,
                "metric_type": metric_type,
                "raw_text": raw_text,
                "failure_reason": "numeric_conversion_error",
            },
        )

    return (
        {
            "company_id": company_id,
            "metric_type": metric_type,
            "period_years": period_years,
            "value_pct": value_pct,
        },
        None,
    )

def parse_analysis_metrics(
    analysis_df: pd.DataFrame,
    ) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    ]:
    """
    Parse all target fields from analysis.xlsx.
    """

    parsed_records = []

    failure_records = []

    for _, row in analysis_df.iterrows():

        company_id = normalize_company_id(
            row.get(
                "company_id"
            )
        )

        if company_id is None:
            continue

        for metric_type in TARGET_FIELDS:

            parsed_record, failure_record = (
                parse_metric_text(
                    company_id=company_id,
                    metric_type=metric_type,
                    raw_value=row.get(
                        metric_type
                    ),
                )
            )

            if parsed_record is not None:
                parsed_records.append(
                    parsed_record
                )

            if failure_record is not None:
                failure_records.append(
                    failure_record
                )

    parsed_columns = [
        "company_id",
        "metric_type",
        "period_years",
        "value_pct",
    ]

    failure_columns = [
        "company_id",
        "metric_type",
        "raw_text",
        "failure_reason",
    ]

    parsed_df = pd.DataFrame(
        parsed_records,
        columns=parsed_columns,
    )

    failures_df = pd.DataFrame(
        failure_records,
        columns=failure_columns,
    )

    return (
        parsed_df,
        failures_df,
    )

# ---------------------------------------------------------

# Ratio Engine loading

# ---------------------------------------------------------

def load_ratio_engine_data() -> pd.DataFrame:
    """
    Load CAGR data from financial_ratios.

    Important:

    financial_ratios.company_id is declared INTEGER,
    but the actual stored SQLite values are TEXT stock
    symbols such as:

        ABB
        TCS
        INFY
        HDFCBANK

    Therefore company_id is explicitly cast and normalized
    as TEXT here.
    """

    logging.info(
        "Loading Ratio Engine data from %s",
        DB_PATH,
    )

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    query = """
        SELECT
            CAST(company_id AS TEXT) AS company_id,
            year,

            revenue_cagr_3yr,
            revenue_cagr_5yr,
            revenue_cagr_10yr,

            pat_cagr_3yr,
            pat_cagr_5yr,
            pat_cagr_10yr

        FROM financial_ratios
    """

    with sqlite3.connect(
        DB_PATH
    ) as connection:

        ratio_df = pd.read_sql_query(
            query,
            connection,
        )

    if ratio_df.empty:

        logging.warning(
            "financial_ratios returned no rows"
        )

        return ratio_df

    ratio_df[
        "company_id"
    ] = ratio_df[
        "company_id"
    ].apply(
        normalize_company_id
    )

    ratio_df[
        "year_numeric"
    ] = ratio_df[
        "year"
    ].apply(
        normalize_year
    )

    ratio_df = ratio_df[
        ratio_df[
            "company_id"
        ].notna()
    ].copy()

    logging.info(
        "Ratio Engine rows loaded: %s",
        len(ratio_df),
    )

    logging.info(
        "Ratio Engine companies: %s",
        ratio_df[
            "company_id"
        ].nunique(),
    )

    return ratio_df

# ---------------------------------------------------------

# CAGR cross-validation

# ---------------------------------------------------------

def get_ratio_engine_column(
    metric_type: str,
    period_years: int,
    ) -> str | None:
    """
    Return the matching Ratio Engine CAGR column.
    """

    metric_mapping = CAGR_COLUMN_MAP.get(
        metric_type
    )

    if metric_mapping is None:
        return None

    return metric_mapping.get(
        period_years
    )

def get_latest_ratio_value(
    ratio_company_df: pd.DataFrame,
    ratio_column: str,
    ) -> tuple[
    float | None,
    Any,
    ]:
    """
    Get the latest available non-null Ratio Engine value
    for a company and CAGR metric.
    """

    if ratio_company_df.empty:
        return (
            None,
            None,
        )

    if ratio_column not in ratio_company_df.columns:
        return (
            None,
            None,
        )

    working_df = (
        ratio_company_df.copy()
    )

    working_df[
        ratio_column
    ] = pd.to_numeric(
        working_df[
            ratio_column
        ],
        errors="coerce",
    )

    working_df = working_df[
        working_df[
            ratio_column
        ].notna()
    ].copy()

    if working_df.empty:
        return (
            None,
            None,
        )

    working_df = working_df.sort_values(
        by="year_numeric",
        ascending=False,
        na_position="last",
    )

    latest_row = working_df.iloc[0]

    return (
        float(
            latest_row[
                ratio_column
            ]
        ),
        latest_row[
            "year"
        ],
    )

def cross_validate_cagr(
    parsed_df: pd.DataFrame,
    ratio_df: pd.DataFrame,
    ) -> pd.DataFrame:
    """
    Cross-validate parsed CAGR values against
    Ratio Engine values.

    Only sales growth and profit growth are validated.

    stock_price_cagr and roe do not currently have a
    direct equivalent CAGR field in financial_ratios.
    """

    review_records = []

    if parsed_df.empty:
        return pd.DataFrame(
            columns=[
                "company_id",
                "metric_type",
                "period_years",
                "parsed_value_pct",
                "ratio_engine_column",
                "ratio_engine_value_pct",
                "ratio_engine_year",
                "divergence_pct_points",
                "status",
            ]
        )

    if ratio_df.empty:

        for _, parsed_row in parsed_df.iterrows():

            metric_type = parsed_row[
                "metric_type"
            ]

            if (
                metric_type
                not in CAGR_COLUMN_MAP
            ):
                continue

            review_records.append(
                {
                    "company_id": parsed_row[
                        "company_id"
                    ],
                    "metric_type": metric_type,
                    "period_years": parsed_row[
                        "period_years"
                    ],
                    "parsed_value_pct": parsed_row[
                        "value_pct"
                    ],
                    "ratio_engine_column": None,
                    "ratio_engine_value_pct": None,
                    "ratio_engine_year": None,
                    "divergence_pct_points": None,
                    "status": "RATIO_ENGINE_DATA_MISSING",
                }
            )

        return pd.DataFrame(
            review_records
        )

    ratio_company_groups = {
        company_id: group.copy()
        for company_id, group
        in ratio_df.groupby(
            "company_id"
        )
    }

    for _, parsed_row in parsed_df.iterrows():

        company_id = parsed_row[
            "company_id"
        ]

        metric_type = parsed_row[
            "metric_type"
        ]

        period_years = int(
            parsed_row[
                "period_years"
            ]
        )

        parsed_value = float(
            parsed_row[
                "value_pct"
            ]
        )

        # Only validate CAGR metrics that exist
        # in the Ratio Engine.
        if (
            metric_type
            not in CAGR_COLUMN_MAP
        ):
            continue

        ratio_column = (
            get_ratio_engine_column(
                metric_type,
                period_years,
            )
        )

        if ratio_column is None:

            review_records.append(
                {
                    "company_id": company_id,
                    "metric_type": metric_type,
                    "period_years": period_years,
                    "parsed_value_pct": parsed_value,
                    "ratio_engine_column": None,
                    "ratio_engine_value_pct": None,
                    "ratio_engine_year": None,
                    "divergence_pct_points": None,
                    "status": "UNSUPPORTED_PERIOD",
                }
            )

            continue

        company_ratio_df = (
            ratio_company_groups.get(
                company_id
            )
        )

        if company_ratio_df is None:

            review_records.append(
                {
                    "company_id": company_id,
                    "metric_type": metric_type,
                    "period_years": period_years,
                    "parsed_value_pct": parsed_value,
                    "ratio_engine_column": ratio_column,
                    "ratio_engine_value_pct": None,
                    "ratio_engine_year": None,
                    "divergence_pct_points": None,
                    "status": "COMPANY_NOT_FOUND",
                }
            )

            continue

        ratio_value, ratio_year = (
            get_latest_ratio_value(
                company_ratio_df,
                ratio_column,
            )
        )

        if ratio_value is None:

            review_records.append(
                {
                    "company_id": company_id,
                    "metric_type": metric_type,
                    "period_years": period_years,
                    "parsed_value_pct": parsed_value,
                    "ratio_engine_column": ratio_column,
                    "ratio_engine_value_pct": None,
                    "ratio_engine_year": None,
                    "divergence_pct_points": None,
                    "status": "RATIO_VALUE_MISSING",
                }
            )

            continue

        divergence = abs(
            parsed_value
            - ratio_value
        )

        if divergence > DIVERGENCE_THRESHOLD:

            status = "MANUAL_REVIEW"

        else:

            status = "MATCH"

        review_records.append(
            {
                "company_id": company_id,
                "metric_type": metric_type,
                "period_years": period_years,
                "parsed_value_pct": parsed_value,
                "ratio_engine_column": ratio_column,
                "ratio_engine_value_pct": ratio_value,
                "ratio_engine_year": ratio_year,
                "divergence_pct_points": divergence,
                "status": status,
            }
        )

    review_columns = [
        "company_id",
        "metric_type",
        "period_years",
        "parsed_value_pct",
        "ratio_engine_column",
        "ratio_engine_value_pct",
        "ratio_engine_year",
        "divergence_pct_points",
        "status",
    ]

    return pd.DataFrame(
        review_records,
        columns=review_columns,
    )

# ---------------------------------------------------------

# Output writing

# ---------------------------------------------------------

def save_outputs(
    parsed_df: pd.DataFrame,
    failures_df: pd.DataFrame,
    review_df: pd.DataFrame,
    ) -> None:
    """
    Save all Day 29 output files.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    parsed_df.to_csv(
        PARSED_OUTPUT_PATH,
        index=False,
    )

    failures_df.to_csv(
        FAILURES_OUTPUT_PATH,
        index=False,
    )

    review_df.to_csv(
        MANUAL_REVIEW_OUTPUT_PATH,
        index=False,
    )

    logging.info(
        "Parsed output saved: %s",
        PARSED_OUTPUT_PATH,
    )

    logging.info(
        "Parse failures saved: %s",
        FAILURES_OUTPUT_PATH,
    )

    logging.info(
        "CAGR manual review saved: %s",
        MANUAL_REVIEW_OUTPUT_PATH,
    )

# ---------------------------------------------------------

# Main execution

# ---------------------------------------------------------

def run_parser() -> None:
    """
    Execute the Day 29 NLP Analysis Parser.
    """

    configure_logging()

    logging.info(
        "Starting Day 29 NLP Analysis Parser"
    )

    analysis_df = (
        load_analysis_data()
    )

    parsed_df, failures_df = (
        parse_analysis_metrics(
            analysis_df
        )
    )

    ratio_df = (
        load_ratio_engine_data()
    )

    review_df = (
        cross_validate_cagr(
            parsed_df,
            ratio_df,
        )
    )

    save_outputs(
        parsed_df,
        failures_df,
        review_df,
    )

    logging.info(
        "Parsed records: %s",
        len(parsed_df),
    )

    logging.info(
        "Parse failures: %s",
        len(failures_df),
    )

    if not review_df.empty:

        manual_review_count = len(
            review_df[
                review_df["status"]
                == "MANUAL_REVIEW"
            ]
        )

        match_count = len(
            review_df[
                review_df["status"]
                == "MATCH"
            ]
        )

    else:

        manual_review_count = 0
        match_count = 0

    logging.info(
        "CAGR matches: %s",
        match_count,
    )

    logging.info(
        "Manual review flags: %s",
        manual_review_count,
    )

    print(
        "\nDay 29 NLP Analysis Parser completed successfully."
    )

    print(
        f"Parsed records: {len(parsed_df)}"
    )

    print(
        f"Parse failures: {len(failures_df)}"
    )

    print(
        f"CAGR matches: {match_count}"
    )

    print(
        f"Manual review flags: {manual_review_count}"
    )

    print(
        "\nGenerated files:"
    )

    print(
        f"  {PARSED_OUTPUT_PATH}"
    )

    print(
        f"  {FAILURES_OUTPUT_PATH}"
    )

    print(
        f"  {MANUAL_REVIEW_OUTPUT_PATH}"
    )

if __name__ == "__main__":
    run_parser()
