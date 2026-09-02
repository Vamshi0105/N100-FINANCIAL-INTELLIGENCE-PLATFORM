"""
Financial Ratio Engine
Day 12 - Populate financial_ratios

Run from project root:

    python -m src.analytics.ratios
"""

import logging
import math
import sqlite3
from pathlib import Path
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

DB_PATH = Path("data") / "nifty100.db"

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================
# HELPERS
# ============================================================

def to_float(value):
    """Safely convert a database value to float."""
    if value is None:
        return None

    try:
        value = float(value)

        if not math.isfinite(value):
            return None

        return value

    except (TypeError, ValueError):
        return None


def safe_sum(*values):
    """Sum available numeric values."""
    numbers = [
        to_float(v)
        for v in values
        if to_float(v) is not None
    ]

    if not numbers:
        return None

    return sum(numbers)


def cagr(start_value, end_value, years):
    """
    CAGR = ((end / start) ^ (1 / years) - 1) * 100

    CAGR is returned only when both values are positive.
    """
    start_value = to_float(start_value)
    end_value = to_float(end_value)

    if start_value is None or end_value is None:
        return None

    if start_value <= 0 or end_value <= 0:
        return None

    if years <= 0:
        return None

    try:
        return (
            (end_value / start_value) ** (1 / years) - 1
        ) * 100
    except (ValueError, ZeroDivisionError, OverflowError):
        return None


# ============================================================
# PROFITABILITY RATIOS
# ============================================================

def net_profit_margin(net_profit, sales):
    """
    Net Profit Margin =
        Net Profit / Sales * 100
    """
    net_profit = to_float(net_profit)
    sales = to_float(sales)

    if net_profit is None or sales is None:
        return None

    if sales == 0:
        return None

    return (net_profit / sales) * 100


def operating_profit_margin(
    operating_profit,
    sales,
    opm_percentage=None,
):
    """
    Operating Profit Margin =
        Operating Profit / Sales * 100

    Reported OPM is only used for cross-checking.
    """
    operating_profit = to_float(operating_profit)
    sales = to_float(sales)

    if operating_profit is None or sales is None:
        return None

    if sales == 0:
        return None

    calculated = (operating_profit / sales) * 100

    reported = to_float(opm_percentage)

    if reported is not None:
        difference = abs(calculated - reported)

        if difference > 1:
            logger.warning(
                "OPM mismatch: calculated=%.2f reported=%.2f",
                calculated,
                reported,
            )

    return calculated


def cross_check_opm(calculated_opm, reported_opm):
    calculated_opm = to_float(calculated_opm)
    reported_opm = to_float(reported_opm)

    if calculated_opm is None or reported_opm is None:
        return False

    # Ignore obviously invalid source percentage values.
    # A percentage outside this range is treated as bad source data.
    if reported_opm < -100 or reported_opm > 100:
        logger.warning(
            "Invalid source OPM ignored: calculated=%.2f reported=%.2f",
            calculated_opm,
            reported_opm,
        )
        return False

    difference = abs(calculated_opm - reported_opm)

    if difference > 1:
        logger.warning(
            "OPM mismatch: calculated=%.2f reported=%.2f",
            calculated_opm,
            reported_opm,
        )
        return False

    return True


def return_on_equity(
    net_profit,
    equity_capital,
    reserves,
):
    """
    ROE =
        Net Profit /
        (Equity Capital + Reserves) * 100
    """
    net_profit = to_float(net_profit)

    if net_profit is None:
        return None

    equity_capital = to_float(equity_capital) or 0
    reserves = to_float(reserves) or 0

    equity = equity_capital + reserves

    if equity <= 0:
        return None

    return (net_profit / equity) * 100


def return_on_capital_employed(
    ebit,
    equity_capital,
    reserves,
    borrowings,
):
    """
    ROCE =
        EBIT / Capital Employed * 100
    """
    ebit = to_float(ebit)

    if ebit is None:
        return None

    equity_capital = to_float(equity_capital) or 0
    reserves = to_float(reserves) or 0
    borrowings = to_float(borrowings) or 0

    capital_employed = (
        equity_capital
        + reserves
        + borrowings
    )

    if capital_employed == 0:
        return None

    return (ebit / capital_employed) * 100


def return_on_assets(
    net_profit,
    total_assets,
):
    """
    ROA =
        Net Profit / Total Assets * 100
    """
    net_profit = to_float(net_profit)
    total_assets = to_float(total_assets)

    if net_profit is None or total_assets is None:
        return None

    if total_assets == 0:
        return None

    return (net_profit / total_assets) * 100


# ============================================================
# LEVERAGE RATIOS
# ============================================================

def debt_to_equity(
    borrowings,
    equity_capital,
    reserves,
):
    borrowings = to_float(borrowings)

    if borrowings is None:
        return None

    equity_capital = to_float(equity_capital) or 0
    reserves = to_float(reserves) or 0

    equity = equity_capital + reserves

    if borrowings == 0:
        return 0

    if equity == 0:
        return None

    return borrowings / equity


def high_leverage_flag(
    debt_to_equity_ratio,
    sector=None,
):
    debt_to_equity_ratio = to_float(
        debt_to_equity_ratio
    )

    if debt_to_equity_ratio is None:
        return False

    return (
        debt_to_equity_ratio > 5
        and sector != "Financials"
    )


# ============================================================
# INTEREST COVERAGE
# ============================================================

def interest_coverage_ratio(
    operating_profit,
    other_income,
    interest,
):
    operating_profit = to_float(operating_profit)
    other_income = to_float(other_income) or 0
    interest = to_float(interest)

    if operating_profit is None or interest is None:
        return None

    if interest == 0:
        return None

    return (
        operating_profit + other_income
    ) / interest


def interest_coverage_label(icr):
    icr = to_float(icr)

    if icr is None:
        return "Debt Free"

    if icr >= 3:
        return "Strong"

    if icr >= 1.5:
        return "Adequate"

    if icr >= 1:
        return "Watchlist"

    return "At Risk"


def interest_coverage_warning(icr):
    icr = to_float(icr)

    if icr is None:
        return False

    return icr < 1.5


# ============================================================
# BALANCE SHEET RATIOS
# ============================================================

def net_debt(
    borrowings,
    investments,
):
    borrowings = to_float(borrowings)
    investments = to_float(investments)

    if borrowings is None and investments is None:
        return None

    return (
        (borrowings or 0)
        - (investments or 0)
    )


def asset_turnover(
    sales,
    total_assets,
):
    sales = to_float(sales)
    total_assets = to_float(total_assets)

    if sales is None or total_assets is None:
        return None

    if total_assets == 0:
        return None

    return sales / total_assets


# ============================================================
# CASH FLOW RATIOS
# ============================================================

def free_cash_flow(
    operating_activity,
    investing_activity,
):
    """
    FCF = CFO + CFI

    Investing activity is normally negative for capex.
    Therefore this produces CFO - Capex when CFI represents
    cash spent on investments/capex.
    """
    cfo = to_float(operating_activity)
    cfi = to_float(investing_activity)

    if cfo is None and cfi is None:
        return None

    return (
        (cfo or 0)
        + (cfi or 0)
    )


def capex_cr(investing_activity):
    """
    Capex is represented as positive spending amount.
    """
    investing_activity = to_float(
        investing_activity
    )

    if investing_activity is None:
        return None

    return abs(investing_activity)


def capex_intensity(
    investing_activity,
    sales,
):
    investing_activity = to_float(
        investing_activity
    )
    sales = to_float(sales)

    if investing_activity is None or sales is None:
        return None

    if sales == 0:
        return None

    return (
        abs(investing_activity) / sales
    ) * 100


def cfo_quality_ratio(
    cfo,
    pat,
):
    cfo = to_float(cfo)
    pat = to_float(pat)

    if cfo is None or pat is None:
        return None

    if pat == 0:
        return None

    return cfo / pat


def cfo_quality_label(ratio):
    ratio = to_float(ratio)

    if ratio is None:
        return "Unavailable"

    if ratio >= 1:
        return "Strong"

    if ratio >= 0.75:
        return "Adequate"

    if ratio >= 0.5:
        return "Weak"

    return "Poor"


def fcf_conversion_rate(
    fcf,
    net_profit,
):
    fcf = to_float(fcf)
    net_profit = to_float(net_profit)

    if fcf is None or net_profit is None:
        return None

    if net_profit == 0:
        return None

    return (
        fcf / net_profit
    ) * 100


# ============================================================
# PER SHARE / DIVIDEND RATIOS
# ============================================================

def earnings_per_share(eps):
    return to_float(eps)


def book_value_per_share(
    equity_capital,
    reserves,
    eps=None,
):
    """
    The source data does not contain share count.

    If equity capital is available, use it as the denominator
    only when a usable share-count field is unavailable.

    This function intentionally returns None unless an actual
    share count can be supplied.
    """
    return None


def dividend_payout_ratio(
    dividend_payout,
):
    return to_float(dividend_payout)


# ============================================================
# CAGR
# ============================================================

def calculate_cagr(
    start_value,
    end_value,
    years,
):
    return cagr(
        start_value,
        end_value,
        years,
    )


# ============================================================
# COMPOSITE QUALITY SCORE
# ============================================================

def calculate_composite_quality_score(
    npm,
    opm,
    roe,
    roce,
    roa,
    debt_equity,
    interest_coverage,
    asset_turnover_value,
    cfo_quality,
    revenue_cagr_5yr,
    pat_cagr_5yr,
    eps_cagr_5yr,
):
    """
    Simple normalized quality score.

    Score range: 0-100.

    Missing metrics are ignored.
    """

    scores = []

    # Profitability
    if npm is not None:
        if npm > 20:
            scores.append(100)
        elif npm > 10:
            scores.append(75)
        elif npm > 5:
            scores.append(50)
        elif npm > 0:
            scores.append(25)
        else:
            scores.append(0)

    if opm is not None:
        if opm > 25:
            scores.append(100)
        elif opm > 15:
            scores.append(75)
        elif opm > 8:
            scores.append(50)
        elif opm > 0:
            scores.append(25)
        else:
            scores.append(0)

    if roe is not None:
        if roe > 20:
            scores.append(100)
        elif roe > 15:
            scores.append(80)
        elif roe > 10:
            scores.append(60)
        elif roe > 5:
            scores.append(40)
        elif roe > 0:
            scores.append(20)
        else:
            scores.append(0)

    if roce is not None:
        if roce > 20:
            scores.append(100)
        elif roce > 15:
            scores.append(80)
        elif roce > 10:
            scores.append(60)
        elif roce > 5:
            scores.append(40)
        elif roce > 0:
            scores.append(20)
        else:
            scores.append(0)

    # Leverage
    if debt_equity is not None:
        if debt_equity < 0.5:
            scores.append(100)
        elif debt_equity < 1:
            scores.append(80)
        elif debt_equity < 2:
            scores.append(60)
        elif debt_equity < 3:
            scores.append(40)
        elif debt_equity < 5:
            scores.append(20)
        else:
            scores.append(0)

    # Interest coverage
    if interest_coverage is not None:
        if interest_coverage >= 5:
            scores.append(100)
        elif interest_coverage >= 3:
            scores.append(80)
        elif interest_coverage >= 1.5:
            scores.append(60)
        elif interest_coverage >= 1:
            scores.append(30)
        else:
            scores.append(0)

    # CFO quality
    if cfo_quality is not None:
        if cfo_quality >= 1:
            scores.append(100)
        elif cfo_quality >= 0.75:
            scores.append(75)
        elif cfo_quality >= 0.5:
            scores.append(50)
        elif cfo_quality >= 0:
            scores.append(25)
        else:
            scores.append(0)

    # Growth
    for growth in (
        revenue_cagr_5yr,
        pat_cagr_5yr,
        eps_cagr_5yr,
    ):
        if growth is not None:
            if growth >= 20:
                scores.append(100)
            elif growth >= 10:
                scores.append(80)
            elif growth >= 5:
                scores.append(60)
            elif growth >= 0:
                scores.append(40)
            else:
                scores.append(0)

    if not scores:
        return None

    return sum(scores) / len(scores)


# ============================================================
# DATABASE HELPERS
# ============================================================

def get_connection():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH.resolve()}"
        )

    return sqlite3.connect(
        str(DB_PATH)
    )


def get_table_columns(conn, table_name):
    rows = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return [
        row[1]
        for row in rows
    ]


def verify_schema(conn):
    columns = get_table_columns(
        conn,
        "financial_ratios",
    )

    logger.info(
        "Verified financial_ratios schema: %d columns",
        len(columns),
    )

    required = [
        "company_id",
        "year",
        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "return_on_equity_pct",
        "return_on_capital_employed_pct",
        "return_on_assets_pct",
        "debt_to_equity",
        "high_leverage_flag",
        "interest_coverage",
        "icr_label",
        "icr_warning_flag",
        "net_debt_cr",
        "asset_turnover",
        "free_cash_flow_cr",
        "capex_cr",
        "capex_intensity_pct",
        "cfo_quality_ratio",
        "cfo_quality_label",
        "fcf_conversion_rate_pct",
        "earnings_per_share",
        "book_value_per_share",
        "dividend_payout_ratio_pct",
        "total_debt_cr",
        "cash_from_operations_cr",
        "revenue_cagr_3yr",
        "revenue_cagr_3yr_flag",
        "revenue_cagr_5yr",
        "revenue_cagr_5yr_flag",
        "revenue_cagr_10yr",
        "revenue_cagr_10yr_flag",
        "pat_cagr_3yr",
        "pat_cagr_3yr_flag",
        "pat_cagr_5yr",
        "pat_cagr_5yr_flag",
        "pat_cagr_10yr",
        "pat_cagr_10yr_flag",
        "eps_cagr_3yr",
        "eps_cagr_3yr_flag",
        "eps_cagr_5yr",
        "eps_cagr_5yr_flag",
        "eps_cagr_10yr",
        "eps_cagr_10yr_flag",
        "composite_quality_score",
    ]

    missing = [
        col
        for col in required
        if col not in columns
    ]

    if missing:
        raise RuntimeError(
            "financial_ratios is missing columns: "
            + ", ".join(missing)
        )

    return columns


# ============================================================
# LOAD SOURCE DATA
# ============================================================

def load_source_data(conn):

    pnl_rows = conn.execute(
        """
        SELECT
            company_id,
            year,
            sales,
            expenses,
            operating_profit,
            opm_percentage,
            other_income,
            interest,
            depreciation,
            profit_before_tax,
            tax_percentage,
            net_profit,
            eps,
            dividend_payout
        FROM profitandloss
        """
    ).fetchall()

    bs_rows = conn.execute(
        """
        SELECT
            company_id,
            year,
            equity_capital,
            reserves,
            borrowings,
            other_liabilities,
            total_liabilities,
            fixed_assets,
            cwip,
            investments,
            other_asset,
            total_assets
        FROM balancesheet
        """
    ).fetchall()

    cf_rows = conn.execute(
        """
        SELECT
            company_id,
            year,
            operating_activity,
            investing_activity,
            financing_activity,
            net_cash_flow
        FROM cashflow
        """
    ).fetchall()

    logger.info(
        "Loaded P&L rows: %d",
        len(pnl_rows),
    )

    logger.info(
        "Loaded balance sheet rows: %d",
        len(bs_rows),
    )

    logger.info(
        "Loaded cash flow rows: %d",
        len(cf_rows),
    )

    pnl = {}
    bs = {}
    cf = {}

    for row in pnl_rows:
        key = (
            row[0],
            row[1],
        )

        pnl[key] = {
            "company_id": row[0],
            "year": row[1],
            "sales": row[2],
            "expenses": row[3],
            "operating_profit": row[4],
            "opm_percentage": row[5],
            "other_income": row[6],
            "interest": row[7],
            "depreciation": row[8],
            "profit_before_tax": row[9],
            "tax_percentage": row[10],
            "net_profit": row[11],
            "eps": row[12],
            "dividend_payout": row[13],
        }

    for row in bs_rows:
        key = (
            row[0],
            row[1],
        )

        bs[key] = {
            "company_id": row[0],
            "year": row[1],
            "equity_capital": row[2],
            "reserves": row[3],
            "borrowings": row[4],
            "other_liabilities": row[5],
            "total_liabilities": row[6],
            "fixed_assets": row[7],
            "cwip": row[8],
            "investments": row[9],
            "other_asset": row[10],
            "total_assets": row[11],
        }

    for row in cf_rows:
        key = (
            row[0],
            row[1],
        )

        cf[key] = {
            "company_id": row[0],
            "year": row[1],
            "operating_activity": row[2],
            "investing_activity": row[3],
            "financing_activity": row[4],
            "net_cash_flow": row[5],
        }

    return pnl, bs, cf

# ============================================================
# DAY 13 — SECTOR + SOURCE RATIO CROSS-CHECKS
# ============================================================

def normalize_company_id(value):
    """Normalize company identifiers for reliable cross-file joins."""
    if value is None:
        return None
    return str(value).strip().upper()


def find_project_file(filename):
    """
    Locate a project Excel file without assuming one
    particular folder structure.
    """

    candidates = [
        Path(filename),
        Path("data") / filename,
        Path("data") / "raw" / filename,
        Path("data") / "supporting" / filename,
        Path("input") / filename,
        Path("inputs") / filename,
        Path("data") / "input" / filename,
    ]

    for path in candidates:
        if path.exists():
            return path

    raise FileNotFoundError(
        f"Could not locate {filename}. "
        f"Checked: {', '.join(str(p) for p in candidates)}"
    )


def load_sector_mapping():
    """
    Load company_id -> broad_sector from sectors.xlsx.

    Day 13 sector data is optional. If sectors.xlsx is not available,
    return an empty mapping so the core ratio engine can still run.
    """

    try:
        path = find_project_file("sectors.xlsx")
    except FileNotFoundError:
        logger.warning(
            "sectors.xlsx not found. Continuing without sector mapping."
        )
        return {}

    df = pd.read_excel(path)

    required_columns = {
        "company_id",
        "broad_sector",
    }

    missing = required_columns - set(df.columns)

    if missing:
        raise RuntimeError(
            "sectors.xlsx is missing columns: "
            + ", ".join(sorted(missing))
        )

    df["company_id"] = df["company_id"].map(
        normalize_company_id
    )

    sectors = dict(
        zip(
            df["company_id"],
            df["broad_sector"],
        )
    )

    logger.info(
        "Loaded sector mappings: %d",
        len(sectors),
    )

    return sectors


def load_source_ratio_values():
    """
    Load pre-computed ROCE and ROE values from companies.xlsx.

    These values are optional Day 13 validation/reference data.
    If companies.xlsx is unavailable, return empty mappings so the
    core ratio engine can still populate financial_ratios.
    """

    try:
        path = find_project_file("companies.xlsx")
    except FileNotFoundError:
        logger.warning(
            "companies.xlsx not found. Continuing without source ROCE/ROE."
        )
        return {}, {}

    # companies.xlsx has a title row above the real headers.
    df = pd.read_excel(
        path,
        header=1,
    )

    required_columns = {
        "id",
        "roce_percentage",
        "roe_percentage",
    }

    missing = required_columns - set(df.columns)

    if missing:
        raise RuntimeError(
            "companies.xlsx is missing columns: "
            + ", ".join(sorted(missing))
        )

    df["id"] = df["id"].map(
        normalize_company_id
    )

    roce_values = {}
    roe_values = {}

    for _, row in df.iterrows():

        company_id = row["id"]

        roce = to_float(
            row["roce_percentage"]
        )

        roe = to_float(
            row["roe_percentage"]
        )

        roce_values[company_id] = roce
        roe_values[company_id] = roe

    logger.info(
        "Loaded source ROCE values: %d",
        len(roce_values),
    )

    logger.info(
        "Loaded source ROE values: %d",
        len(roe_values),
    )

    return roce_values, roe_values


def setup_edge_case_log():
    """
    Create/reset the Day 13 anomaly log.
    """

    output_dir = Path("output")

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    log_path = (
        output_dir
        / "ratio_edge_cases.log"
    )

    with open(
        log_path,
        "w",
        encoding="utf-8",
    ) as log_file:

        log_file.write(
            "N100 Ratio Engine - Day 13 Edge Cases\n"
        )

        log_file.write(
            "=" * 70
            + "\n"
        )

        log_file.write(
            "ROCE / ROE source cross-checks\n"
        )

        log_file.write(
            "Difference threshold: > 5 percentage points\n"
        )

        log_file.write(
            "Computed Ratio Engine values are analytical source of truth.\n"
        )

        log_file.write(
            "companies.xlsx values are source/display reference only.\n"
        )

        log_file.write(
            "=" * 70
            + "\n\n"
        )

    return log_path


def classify_ratio_anomaly(
    ratio_name,
    calculated,
    source,
    difference,
):
    """
    Categorize a Day 13 source/computed mismatch.

    ROE values that are implausibly tiny versus the computed engine value
    are treated as data-source issues. Other large mismatches are treated
    as version differences unless a formula discrepancy is explicitly
    established during review.
    """
    if ratio_name == "ROE" and abs(source) < 1 and abs(calculated) > 5:
        return "data source issue"

    return "version difference"


def log_ratio_edge_case(
    log_path,
    ratio_name,
    company_id,
    year,
    calculated,
    source,
    difference,
    category=None,
):
    """
    Append one ratio anomaly to the Day 13 log.
    """

    if category is None:
        category = classify_ratio_anomaly(
            ratio_name,
            calculated,
            source,
            difference,
        )

    with open(
        log_path,
        "a",
        encoding="utf-8",
    ) as log_file:

        log_file.write(
            f"{ratio_name} ANOMALY | "
            f"company={company_id} | "
            f"year={year} | "
            f"calculated={calculated:.4f} | "
            f"source={source:.4f} | "
            f"difference={difference:.4f} | "
            f"category={category}\n"
        )


def cross_check_source_ratios(
    output_rows,
    roce_source,
    roe_source,
    log_path,
):
    """
    Compare the latest computed Ratio Engine ROCE/ROE
    against companies.xlsx.

    The companies.xlsx ratios are company-level values,
    so the latest available calculated year is used.

    An anomaly is logged when the absolute difference
    exceeds 5 percentage points.
    """

    latest_rows = {}

    # --------------------------------------------------------
    # Keep latest year for each company
    # --------------------------------------------------------

    for row in output_rows:

        company_id = row.get(
            "company_id"
        )

        year = row.get(
            "year"
        )

        if company_id is None:
            continue

        parsed_year = parse_year(year)

        if parsed_year is None:
            continue

        existing = latest_rows.get(
            company_id
        )

        if (
            existing is None
            or parsed_year
            > parse_year(existing["year"])
        ):
            latest_rows[company_id] = row

    roce_anomalies = 0
    roe_anomalies = 0

    # --------------------------------------------------------
    # ROCE cross-check
    # --------------------------------------------------------

    for company_id, row in latest_rows.items():

        calculated = to_float(
            row.get(
                "return_on_capital_employed_pct"
            )
        )

        source = roce_source.get(
            company_id
        )

        if calculated is None or source is None:
            continue

        difference = abs(
            calculated - source
        )

        if difference > 5:

            log_ratio_edge_case(
                log_path=log_path,
                ratio_name="ROCE",
                company_id=company_id,
                year=row["year"],
                calculated=calculated,
                source=source,
                difference=difference,
            )

            roce_anomalies += 1

    # --------------------------------------------------------
    # ROE cross-check
    # --------------------------------------------------------

    for company_id, row in latest_rows.items():

        calculated = to_float(
            row.get(
                "return_on_equity_pct"
            )
        )

        source = roe_source.get(
            company_id
        )

        if calculated is None or source is None:
            continue

        difference = abs(
            calculated - source
        )

        if difference > 5:

            log_ratio_edge_case(
                log_path=log_path,
                ratio_name="ROE",
                company_id=company_id,
                year=row["year"],
                calculated=calculated,
                source=source,
                difference=difference,
            )

            roe_anomalies += 1

    return (
        roce_anomalies,
        roe_anomalies,
    )
# ============================================================
# HISTORICAL VALUE HELPERS
# ============================================================

def historical_value(
    data,
    company_id,
    target_year,
    field,
):
    key = (
        company_id,
        target_year,
    )

    row = data.get(key)

    if row is None:
        return None

    return row.get(field)


def parse_year(year):
    """
    Handles values such as:

        2020
        '2020'
        '2020-03'
        '2020-12'
    """
    if year is None:
        return None

    try:
        return int(str(year)[:4])
    except (ValueError, TypeError):
        return None


def find_prior_year_value(
    data,
    company_id,
    current_year,
    field,
    years_back,
):
    current = parse_year(current_year)

    if current is None:
        return None

    target = current - years_back

    # First try exact year formats found in source.
    candidates = []

    for key, row in data.items():
        if key[0] != company_id:
            continue

        row_year = parse_year(key[1])

        if row_year == target:
            value = row.get(field)

            if value is not None:
                candidates.append(
                    (
                        key[1],
                        value,
                    )
                )

    if not candidates:
        return None

    # Deterministic selection.
    candidates.sort(
        key=lambda x: str(x[0])
    )

    return candidates[-1][1]


def calculate_growth_metrics(
    company_id,
    year,
    pnl,
):
    revenue_3 = calculate_cagr(
        find_prior_year_value(
            pnl,
            company_id,
            year,
            "sales",
            3,
        ),
        historical_value(
            pnl,
            company_id,
            year,
            "sales",
        ),
        3,
    )

    revenue_5 = calculate_cagr(
        find_prior_year_value(
            pnl,
            company_id,
            year,
            "sales",
            5,
        ),
        historical_value(
            pnl,
            company_id,
            year,
            "sales",
        ),
        5,
    )

    revenue_10 = calculate_cagr(
        find_prior_year_value(
            pnl,
            company_id,
            year,
            "sales",
            10,
        ),
        historical_value(
            pnl,
            company_id,
            year,
            "sales",
        ),
        10,
    )

    pat_3 = calculate_cagr(
        find_prior_year_value(
            pnl,
            company_id,
            year,
            "net_profit",
            3,
        ),
        historical_value(
            pnl,
            company_id,
            year,
            "net_profit",
        ),
        3,
    )

    pat_5 = calculate_cagr(
        find_prior_year_value(
            pnl,
            company_id,
            year,
            "net_profit",
            5,
        ),
        historical_value(
            pnl,
            company_id,
            year,
            "net_profit",
        ),
        5,
    )

    pat_10 = calculate_cagr(
        find_prior_year_value(
            pnl,
            company_id,
            year,
            "net_profit",
            10,
        ),
        historical_value(
            pnl,
            company_id,
            year,
            "net_profit",
        ),
        10,
    )

    eps_3 = calculate_cagr(
        find_prior_year_value(
            pnl,
            company_id,
            year,
            "eps",
            3,
        ),
        historical_value(
            pnl,
            company_id,
            year,
            "eps",
        ),
        3,
    )

    eps_5 = calculate_cagr(
        find_prior_year_value(
            pnl,
            company_id,
            year,
            "eps",
            5,
        ),
        historical_value(
            pnl,
            company_id,
            year,
            "eps",
        ),
        5,
    )

    eps_10 = calculate_cagr(
        find_prior_year_value(
            pnl,
            company_id,
            year,
            "eps",
            10,
        ),
        historical_value(
            pnl,
            company_id,
            year,
            "eps",
        ),
        10,
    )

    return {
        "revenue_cagr_3yr": revenue_3,
        "revenue_cagr_5yr": revenue_5,
        "revenue_cagr_10yr": revenue_10,
        "pat_cagr_3yr": pat_3,
        "pat_cagr_5yr": pat_5,
        "pat_cagr_10yr": pat_10,
        "eps_cagr_3yr": eps_3,
        "eps_cagr_5yr": eps_5,
        "eps_cagr_10yr": eps_10,
    }


# ============================================================
# FLAG HELPERS
# ============================================================

def growth_flag(value):
    value = to_float(value)

    if value is None:
        return False

    return value < 0


# ============================================================
# BUILD RATIO ROW
# ============================================================

def build_ratio_row(
    company_id,
    year,
    pnl_row,
    bs_row,
    cf_row,
    pnl,
    sector=None,
):
    pnl_row = pnl_row or {}
    bs_row = bs_row or {}
    cf_row = cf_row or {}

    sales = pnl_row.get("sales")
    operating_profit = pnl_row.get(
        "operating_profit"
    )
    reported_opm = pnl_row.get(
        "opm_percentage"
    )
    other_income = pnl_row.get(
        "other_income"
    )
    interest = pnl_row.get(
        "interest"
    )
    net_profit = pnl_row.get(
        "net_profit"
    )
    eps = pnl_row.get("eps")
    dividend_payout = pnl_row.get(
        "dividend_payout"
    )

    equity_capital = bs_row.get(
        "equity_capital"
    )
    reserves = bs_row.get(
        "reserves"
    )
    borrowings = bs_row.get(
        "borrowings"
    )
    investments = bs_row.get(
        "investments"
    )
    total_assets = bs_row.get(
        "total_assets"
    )

    cfo = cf_row.get(
        "operating_activity"
    )
    cfi = cf_row.get(
        "investing_activity"
    )

    # --------------------------------------------------------
    # Core ratios
    # --------------------------------------------------------

    npm = net_profit_margin(
        net_profit,
        sales,
    )

    opm = operating_profit_margin(
        operating_profit,
        sales,
        reported_opm,
    )

    roe = return_on_equity(
        net_profit,
        equity_capital,
        reserves,
    )

    roce = return_on_capital_employed(
        operating_profit,
        equity_capital,
        reserves,
        borrowings,
    )

    roa = return_on_assets(
        net_profit,
        total_assets,
    )

    de = debt_to_equity(
        borrowings,
        equity_capital,
        reserves,
    )

    icr = interest_coverage_ratio(
        operating_profit,
        other_income,
        interest,
    )

    net_debt_value = net_debt(
        borrowings,
        investments,
    )

    turnover = asset_turnover(
        sales,
        total_assets,
    )

    fcf = free_cash_flow(
        cfo,
        cfi,
    )

    capex = capex_cr(
        cfi,
    )

    capex_intensity_value = capex_intensity(
        cfi,
        sales,
    )

    cfo_quality = cfo_quality_ratio(
        cfo,
        net_profit,
    )

    fcf_conversion = fcf_conversion_rate(
        fcf,
        net_profit,
    )

    # --------------------------------------------------------
    # Growth metrics
    # --------------------------------------------------------

    growth = calculate_growth_metrics(
        company_id,
        year,
        pnl,
    )

    # --------------------------------------------------------
    # Composite score
    # --------------------------------------------------------

    score = calculate_composite_quality_score(
        npm=npm,
        opm=opm,
        roe=roe,
        roce=roce,
        roa=roa,
        debt_equity=de,
        interest_coverage=icr,
        asset_turnover_value=turnover,
        cfo_quality=cfo_quality,
        revenue_cagr_5yr=(
            growth["revenue_cagr_5yr"]
        ),
        pat_cagr_5yr=(
            growth["pat_cagr_5yr"]
        ),
        eps_cagr_5yr=(
            growth["eps_cagr_5yr"]
        ),
    )

    # --------------------------------------------------------
    # Return dictionary
    # --------------------------------------------------------

    return {
        "company_id": company_id,
        "year": year,

        "net_profit_margin_pct": npm,

        "operating_profit_margin_pct": opm,

        "return_on_equity_pct": roe,

        "return_on_capital_employed_pct": roce,

        "return_on_assets_pct": roa,

        "debt_to_equity": de,

        "high_leverage_flag": (
            high_leverage_flag(
                de,
                sector=sector,
            )
        ),

        "interest_coverage": icr,

        "icr_label": (
            interest_coverage_label(icr)
        ),

        "icr_warning_flag": (
            interest_coverage_warning(icr)
        ),

        "net_debt_cr": net_debt_value,

        "asset_turnover": turnover,

        "free_cash_flow_cr": fcf,

        "capex_cr": capex,

        "capex_intensity_pct": (
            capex_intensity_value
        ),

        "cfo_quality_ratio": cfo_quality,

        "cfo_quality_label": (
            cfo_quality_label(cfo_quality)
        ),

        "fcf_conversion_rate_pct": (
            fcf_conversion
        ),

        "earnings_per_share": (
            earnings_per_share(eps)
        ),

        "book_value_per_share": (
            book_value_per_share(
                equity_capital,
                reserves,
                eps,
            )
        ),

        "dividend_payout_ratio_pct": (
            dividend_payout_ratio(
                dividend_payout
            )
        ),

        "total_debt_cr": to_float(
            borrowings
        ),

        "cash_from_operations_cr": to_float(
            cfo
        ),

        "revenue_cagr_3yr": (
            growth["revenue_cagr_3yr"]
        ),

        "revenue_cagr_3yr_flag": (
            growth_flag(
                growth["revenue_cagr_3yr"]
            )
        ),

        "revenue_cagr_5yr": (
            growth["revenue_cagr_5yr"]
        ),

        "revenue_cagr_5yr_flag": (
            growth_flag(
                growth["revenue_cagr_5yr"]
            )
        ),

        "revenue_cagr_10yr": (
            growth["revenue_cagr_10yr"]
        ),

        "revenue_cagr_10yr_flag": (
            growth_flag(
                growth["revenue_cagr_10yr"]
            )
        ),

        "pat_cagr_3yr": (
            growth["pat_cagr_3yr"]
        ),

        "pat_cagr_3yr_flag": (
            growth_flag(
                growth["pat_cagr_3yr"]
            )
        ),

        "pat_cagr_5yr": (
            growth["pat_cagr_5yr"]
        ),

        "pat_cagr_5yr_flag": (
            growth_flag(
                growth["pat_cagr_5yr"]
            )
        ),

        "pat_cagr_10yr": (
            growth["pat_cagr_10yr"]
        ),

        "pat_cagr_10yr_flag": (
            growth_flag(
                growth["pat_cagr_10yr"]
            )
        ),

        "eps_cagr_3yr": (
            growth["eps_cagr_3yr"]
        ),

        "eps_cagr_3yr_flag": (
            growth_flag(
                growth["eps_cagr_3yr"]
            )
        ),

        "eps_cagr_5yr": (
            growth["eps_cagr_5yr"]
        ),

        "eps_cagr_5yr_flag": (
            growth_flag(
                growth["eps_cagr_5yr"]
            )
        ),

        "eps_cagr_10yr": (
            growth["eps_cagr_10yr"]
        ),

        "eps_cagr_10yr_flag": (
            growth_flag(
                growth["eps_cagr_10yr"]
            )
        ),

        "composite_quality_score": score,
    }


# ============================================================
# POPULATE DATABASE
# ============================================================

def populate_financial_ratios():
    logger.info(
        "Starting financial ratio engine"
    )

    conn = get_connection()

    try:
        # ----------------------------------------------------
        # Verify schema
        # ----------------------------------------------------

        table_columns = verify_schema(conn)

        # ----------------------------------------------------
        # Load source data
        # ----------------------------------------------------

        pnl, bs, cf = load_source_data(
            conn
        )

        # ----------------------------------------------------
        # Day 13 — Load sector and source-ratio reference data
        # ----------------------------------------------------

        sectors = load_sector_mapping()
        roce_source, roe_source = load_source_ratio_values()
        edge_case_log = setup_edge_case_log()

        financials_count = sum(
            1
            for company_id in sectors
            if sectors.get(company_id) == "Financials"
        )

        logger.info(
            "Financials companies in sector mapping: %d",
            financials_count,
        )

        # ----------------------------------------------------
        # UNION of all company/year combinations
        # ----------------------------------------------------

        all_keys = (
            set(pnl.keys())
            | set(bs.keys())
            | set(cf.keys())
        )

        all_keys = sorted(
            all_keys,
            key=lambda x: (
                str(x[0]),
                str(x[1]),
            ),
        )

        logger.info(
            "Union company/year combinations: %d",
            len(all_keys),
        )

        # ----------------------------------------------------
        # Build rows
        # ----------------------------------------------------

        output_rows = []

        for company_id, year in all_keys:

            pnl_row = pnl.get(
                (company_id, year)
            )

            bs_row = bs.get(
                (company_id, year)
            )

            cf_row = cf.get(
                (company_id, year)
            )

            row = build_ratio_row(
              company_id=company_id,
                year=year,
                pnl_row=pnl_row,
                bs_row=bs_row,
                cf_row=cf_row,
                pnl=pnl,
                sector=sectors.get(
                    normalize_company_id(company_id)
                ),
)
            output_rows.append(row)

        logger.info(
            "Prepared ratio rows: %d",
            len(output_rows),
        )
        # ----------------------------------------------------
        # Day 13 — ROCE / ROE source cross-check
        # ----------------------------------------------------

        roce_anomalies, roe_anomalies = (
            cross_check_source_ratios(
                output_rows=output_rows,
                roce_source=roce_source,
                roe_source=roe_source,
                log_path=edge_case_log,
            )
        )

        logger.info(
            "Day 13 ROCE anomalies: %d",
            roce_anomalies,
        )

        logger.info(
            "Day 13 ROE anomalies: %d",
            roe_anomalies,
        )

        print()
        print(
            f"ROCE anomalies: {roce_anomalies}"
        )

        print(
            f"ROE anomalies: {roe_anomalies}"
        )

        print(
            f"Edge-case log: {edge_case_log}"
        )

        print(
            f"Financials companies: {financials_count}"
        )

        logger.info(
            "Financials companies in sector mapping: %d",
            financials_count,
        )
        # ----------------------------------------------------
        # Make sure output rows contain exactly the columns
        # required by the existing table.
        #
        # This prevents:
        #
        # 46 values for 44 columns
        # 47 values for 44 columns
        # ----------------------------------------------------
        
        if not output_rows:
            raise RuntimeError(
                "No ratio rows were generated."
            )

        insert_columns = [
            column
            for column in table_columns
            if column in output_rows[0]
        ]

        if not insert_columns:
            raise RuntimeError(
                "No matching financial ratio columns found."
            )

        placeholders = ", ".join(
            ["?"] * len(insert_columns)
        )

        column_sql = ", ".join(
            insert_columns
        )

        insert_sql = f"""
            INSERT OR REPLACE INTO financial_ratios
            ({column_sql})
            VALUES ({placeholders})
        """

        values = []

        for row in output_rows:
            values.append(
                tuple(
                    row.get(column)
                    for column in insert_columns
                )
            )

        # ----------------------------------------------------
        # Replace old calculated data
        # ----------------------------------------------------

        conn.execute(
            "DELETE FROM financial_ratios"
        )

        conn.executemany(
            insert_sql,
            values,
        )

        conn.commit()

        # ----------------------------------------------------
        # Verify row count
        # ----------------------------------------------------

        count = conn.execute(
            """
            SELECT COUNT(*)
            FROM financial_ratios
            """
        ).fetchone()[0]

        logger.info(
            "financial_ratios rows: %d",
            count,
        )

        print()
        print(
            f"financial_ratios rows: {count}"
        )

        if count >= 1100:
            print(
                "PASS: row count >= 1,100"
            )
        else:
            print(
                "FAIL: row count < 1,100"
            )

        # ----------------------------------------------------
        # Company count
        # ----------------------------------------------------

        company_count = conn.execute(
            """
            SELECT COUNT(DISTINCT company_id)
            FROM financial_ratios
            """
        ).fetchone()[0]

        print(
            f"Companies populated: {company_count}"
        )

        # ----------------------------------------------------
        # Sample rows
        # ----------------------------------------------------

        print()
        print("Sample rows:")

        sample_rows = conn.execute(
            """
            SELECT
                company_id,
                year,
                net_profit_margin_pct,
                operating_profit_margin_pct,
                return_on_equity_pct,
                return_on_capital_employed_pct,
                return_on_assets_pct,
                composite_quality_score
            FROM financial_ratios
            ORDER BY company_id, year
            LIMIT 5
            """
        ).fetchall()

        for row in sample_rows:
            print(row)

        print()
        print(
            "Ratio engine completed successfully."
        )

    finally:
        conn.close()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    populate_financial_ratios()