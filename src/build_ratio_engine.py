import sqlite3
import logging
import os
import traceback

from analytics.ratios import (
    net_profit_margin,
    operating_profit_margin,
    cross_check_opm,
    return_on_equity,
    return_on_capital_employed,
    return_on_assets,
    debt_to_equity,
    high_leverage_flag,
    interest_coverage_ratio,
    interest_coverage_label,
    interest_coverage_warning,
    net_debt,
    asset_turnover,
)

from analytics.cagr import calculate_cagr

from analytics.cashflow_kpis import (
    free_cash_flow,
    cfo_pat_ratio,
    cfo_quality_score,
    capex_intensity,
    capex_intensity_label,
    fcf_conversion_rate,
    capital_allocation_pattern,
)


DB_PATH = "data/nifty100.db"

OUTPUT_DIR = "output"

os.makedirs(OUTPUT_DIR, exist_ok=True)

LOG_FILE = os.path.join(
    OUTPUT_DIR,
    "ratio_edge_cases.log"
)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


def normalize_year(value):
    """
    Convert financial period values into a numeric year.

    Supported examples:
        2012
        "2012"
        "2012-12"
        "2012-03"
        "2012-09"
        "2012-12-31"
    """

    if value is None:
        return None

    value = str(value).strip()

    # YYYY-MM or YYYY-MM-DD
    if "-" in value:
        first_part = value.split("-")[0]

        try:
            return int(first_part)
        except ValueError:
            return None

    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def clean_number(value):
    """
    Convert SQLite values safely to float.
    """

    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        logging.debug(
            f"Failed to convert value to float: {value} (type: {type(value).__name__})"
        )
        return None


def get_columns(cursor, table):
    """
    Return column names for a table.
    """

    try:
        cursor.execute(
            f"PRAGMA table_info({table})"
        )

        return [
            row[1]
            for row in cursor.fetchall()
        ]
    except sqlite3.Error as e:
        logging.error(
            f"Error getting columns for table '{table}': {e}"
        )
        return []


def find_column(columns, candidates):
    """
    Find the first matching column from candidates.
    """

    normalized = {
        column.lower(): column
        for column in columns
    }

    for candidate in candidates:

        if candidate.lower() in normalized:
            return normalized[candidate.lower()]

    return None


def load_table(cursor, table):
    """
    Load an entire SQLite table.
    """

    try:
        columns = get_columns(
            cursor,
            table
        )

        if not columns:
            logging.warning(
                f"No columns found for table '{table}'"
            )
            return []

        cursor.execute(
            f"SELECT * FROM {table}"
        )

        rows = cursor.fetchall()

        result = []

        for row in rows:

            result.append(
                dict(zip(columns, row))
            )

        return result
    except sqlite3.Error as e:
        logging.error(
            f"Error loading table '{table}': {e}"
        )
        return []


def get_value(row, aliases):
    """
    Get value from a row using multiple possible
    column names.
    """

    if row is None:
        return None

    try:
        for alias in aliases:

            for key in row:

                if key.lower() == alias.lower():

                    return clean_number(
                        row[key]
                    )
    except Exception as e:
        logging.debug(
            f"Error retrieving value with aliases {aliases}: {e}"
        )

    return None


def get_text(row, aliases):
    """
    Get text value from a row.
    """

    if row is None:
        return None

    try:
        for alias in aliases:

            for key in row:

                if key.lower() == alias.lower():
                    return row[key]
    except Exception as e:
        logging.debug(
            f"Error retrieving text with aliases {aliases}: {e}"
        )

    return None


def get_company_id(row):
    try:
        return (
            row.get("company_id")
            or row.get("companyId")
            or row.get("id")
        )
    except Exception as e:
        logging.debug(f"Error getting company_id: {e}")
        return None


def get_year(row):
    try:
        return (
            row.get("year")
            or row.get("Year")
            or row.get("financial_year")
            or row.get("fiscal_year")
        )
    except Exception as e:
        logging.debug(f"Error getting year: {e}")
        return None


def create_financial_ratios_table(cursor):
    try:
        cursor.execute("""
            DROP TABLE IF EXISTS financial_ratios
        """)

        cursor.execute("""
            CREATE TABLE financial_ratios (

                company_id INTEGER NOT NULL,
                year INTEGER NOT NULL,

                net_profit_margin_pct REAL,
                operating_profit_margin_pct REAL,
                return_on_equity_pct REAL,
                return_on_capital_employed_pct REAL,
                return_on_assets_pct REAL,

                debt_to_equity REAL,
                high_leverage_flag INTEGER,

                interest_coverage REAL,
                icr_label TEXT,
                icr_warning_flag INTEGER,

                net_debt_cr REAL,
                asset_turnover REAL,

                free_cash_flow_cr REAL,
                capex_cr REAL,
                capex_intensity_pct REAL,

                cfo_quality_ratio REAL,
                cfo_quality_label TEXT,

                fcf_conversion_rate_pct REAL,

                earnings_per_share REAL,
                book_value_per_share REAL,
                dividend_payout_ratio_pct REAL,

                total_debt_cr REAL,
                cash_from_operations_cr REAL,

                revenue_cagr_3yr REAL,
                revenue_cagr_3yr_flag TEXT,

                revenue_cagr_5yr REAL,
                revenue_cagr_5yr_flag TEXT,

                revenue_cagr_10yr REAL,
                revenue_cagr_10yr_flag TEXT,

                pat_cagr_3yr REAL,
                pat_cagr_3yr_flag TEXT,

                pat_cagr_5yr REAL,
                pat_cagr_5yr_flag TEXT,

                pat_cagr_10yr REAL,
                pat_cagr_10yr_flag TEXT,

                eps_cagr_3yr REAL,
                eps_cagr_3yr_flag TEXT,

                eps_cagr_5yr REAL,
                eps_cagr_5yr_flag TEXT,

                eps_cagr_10yr REAL,
                eps_cagr_10yr_flag TEXT,

                composite_quality_score REAL,

                PRIMARY KEY (company_id, year)
            )
        """)
    except sqlite3.Error as e:
        logging.error(
            f"Error creating financial_ratios table: {e}"
        )
        raise


def calculate_composite_quality(
    roe,
    npm,
    debt_to_equity_value,
    icr,
    asset_turnover_value
):
    """
    Simple 100-point quality score.

    This can be adjusted later if your project
    has a prescribed scoring methodology.
    """

    try:
        score = 0

        if roe is not None:

            if roe >= 20:
                score += 25

            elif roe >= 15:
                score += 20

            elif roe >= 10:
                score += 10

        if npm is not None:

            if npm >= 15:
                score += 20

            elif npm >= 10:
                score += 15

            elif npm >= 5:
                score += 10

        if debt_to_equity_value is not None:

            if debt_to_equity_value < 0.5:
                score += 20

            elif debt_to_equity_value < 1:
                score += 15

            elif debt_to_equity_value < 2:
                score += 10

        if icr is not None:

            if icr >= 3:
                score += 20

            elif icr >= 1.5:
                score += 10

        if asset_turnover_value is not None:

            if asset_turnover_value >= 1:
                score += 15

            elif asset_turnover_value >= 0.5:
                score += 10

        return score
    except Exception as e:
        logging.error(
            f"Error calculating composite quality: {e}"
        )
        return 0


def main():

    print("Starting Financial Ratio Engine...")

    conn = None
    try:
        if not os.path.exists(DB_PATH):
            logging.error(
                f"Database file not found: {DB_PATH}"
            )
            print(f"ERROR: Database file not found: {DB_PATH}")
            return

        conn = sqlite3.connect(
            DB_PATH
        )

        cursor = conn.cursor()

        print("Loading source tables...")

        pnl = load_table(
            cursor,
            "profitandloss"
        )

        balance = load_table(
            cursor,
            "balancesheet"
        )

        cashflow = load_table(
            cursor,
            "cashflow"
        )

        companies = load_table(
            cursor,
            "companies"
        )

        print(
            f"Profit/Loss rows: {len(pnl)}"
        )

        print(
            f"Balance Sheet rows: {len(balance)}"
        )

        print(
            f"Cash Flow rows: {len(cashflow)}"
        )

        print(
            f"Companies: {len(companies)}"
        )

        # ---------------------------------------------------------
        # Create lookup dictionaries
        # ---------------------------------------------------------

        balance_lookup = {}

        for row in balance:

            company_id = get_company_id(row)
            year = get_year(row)

            if company_id is not None and year is not None:

                balance_lookup[
                    (company_id, year)
                ] = row

        cashflow_lookup = {}

        for row in cashflow:

            company_id = get_company_id(row)
            year = get_year(row)

            if company_id is not None and year is not None:

                cashflow_lookup[
                    (company_id, year)
                ] = row

        company_lookup = {}

        for row in companies:

            company_id = get_company_id(row)

            if company_id is not None:

                company_lookup[
                    company_id
                ] = row

        # ---------------------------------------------------------
        # Recreate financial_ratios
        
   
           # ---------------------------------------------------------
        # Recreate financial_ratios
        # ---------------------------------------------------------

        create_financial_ratios_table(
            cursor
        )

        conn.commit()

        insert_sql = """
            INSERT OR REPLACE INTO financial_ratios (

                company_id,
                year,

                net_profit_margin_pct,
                operating_profit_margin_pct,
                return_on_equity_pct,
                return_on_capital_employed_pct,
                return_on_assets_pct,

                debt_to_equity,
                high_leverage_flag,

                interest_coverage,
                icr_label,
                icr_warning_flag,

                net_debt_cr,
                asset_turnover,

                free_cash_flow_cr,
                capex_cr,
                capex_intensity_pct,

                cfo_quality_ratio,
                cfo_quality_label,

                fcf_conversion_rate_pct,

                earnings_per_share,
                book_value_per_share,
                dividend_payout_ratio_pct,

                total_debt_cr,
                cash_from_operations_cr,

                revenue_cagr_3yr,
                revenue_cagr_3yr_flag,

                revenue_cagr_5yr,
                revenue_cagr_5yr_flag,

                revenue_cagr_10yr,
                revenue_cagr_10yr_flag,

                pat_cagr_3yr,
                pat_cagr_3yr_flag,

                pat_cagr_5yr,
                pat_cagr_5yr_flag,

                pat_cagr_10yr,
                pat_cagr_10yr_flag,

                eps_cagr_3yr,
                eps_cagr_3yr_flag,

                eps_cagr_5yr,
                eps_cagr_5yr_flag,

                eps_cagr_10yr,
                eps_cagr_10yr_flag,

                composite_quality_score

            )

            VALUES (
                ?, ?, ?, ?, ?, ?, ?,
                ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?, ?,
                ?, ?,
                ?,
                ?, ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?
            )
        """

        # ---------------------------------------------------------
        # Revenue/PAT/EPS history
        # ---------------------------------------------------------

        history = {}

        for row in pnl:

            company_id = get_company_id(row)
            year = get_year(row)

            if company_id is None or year is None:
                continue

            if company_id not in history:
                history[company_id] = {}

            if year not in history[company_id]:
                history[company_id][year] = {}

            history[company_id][year]["revenue"] = get_value(
                row,
                [
                    "sales",
                    "revenue",
                    "net_sales",
                    "total_revenue"
                ]
            )

            history[company_id][year]["pat"] = get_value(
                row,
                [
                    "net_profit",
                    "net_profit_after_tax",
                    "profit_after_tax",
                    "pat"
                ]
            )

            history[company_id][year]["eps"] = get_value(
                row,
                [
                    "eps",
                    "earnings_per_share"
                ]
            )

        # ---------------------------------------------------------
        # Process every P&L company-year
        # ---------------------------------------------------------

        processed = 0
        skipped = 0

        for pnl_row in pnl:

            try:
                company_id = get_company_id(
                    pnl_row
                )

                year = get_year(
                    pnl_row
                )

                current_year = normalize_year(year)

                if current_year is None:
                    logging.warning(
                        "Invalid year | company=%s | year=%s",
                        company_id,
                        year
                    )

                    skipped += 1
                    continue

                bs_row = balance_lookup.get(
                    (company_id, year),
                    {}
                )

                cf_row = cashflow_lookup.get(
                    (company_id, year),
                    {}
                )

                company_row = company_lookup.get(
                    company_id,
                    {}
                )

                sales = get_value(
                    pnl_row,
                    [
                        "sales",
                        "revenue",
                        "net_sales",
                        "total_revenue"
                    ]
                )

                net_profit = get_value(
                    pnl_row,
                    [
                        "net_profit",
                        "net_profit_after_tax",
                        "profit_after_tax",
                        "pat"
                    ]
                )

                operating_profit = get_value(
                    pnl_row,
                    [
                        "operating_profit",
                        "op_profit"
                    ]
                )

                other_income = get_value(
                    pnl_row,
                    [
                        "other_income"
                    ]
                )

                interest = get_value(
                    pnl_row,
                    [
                        "interest",
                        "interest_expense",
                        "finance_cost"
                    ]
                )

                ebit = get_value(
                    pnl_row,
                    [
                        "ebit",
                        "earnings_before_interest_and_tax"
                    ]
                )

                if ebit is None:

                    ebit = (
                        operating_profit or 0
                    ) + (
                        other_income or 0
                    )

                equity_capital = get_value(
                    bs_row,
                    [
                        "equity_capital",
                        "share_capital",
                        "equity"
                    ]
                )

                reserves = get_value(
                    bs_row,
                    [
                        "reserves",
                        "reserves_and_surplus"
                    ]
                )

                borrowings = get_value(
                    bs_row,
                    [
                        "borrowings",
                        "total_borrowings",
                        "debt",
                        "total_debt"
                    ]
                )

                investments = get_value(
                    bs_row,
                    [
                        "investments",
                        "total_investments"
                    ]
                )

                total_assets = get_value(
                    bs_row,
                    [
                        "total_assets",
                        "assets"
                    ]
                )

                cfo = get_value(
                    cf_row,
                    [
                        "operating_activity",
                        "cash_from_operations",
                        "cash_flow_from_operating_activities",
                        "cfo"
                    ]
                )

                cfi = get_value(
                    cf_row,
                    [
                        "investing_activity",
                        "cash_from_investing",
                        "cash_flow_from_investing_activities",
                        "cfi"
                    ]
                )

                cff = get_value(
                    cf_row,
                    [
                        "financing_activity",
                        "cash_from_financing",
                        "cash_flow_from_financing_activities",
                        "cff"
                    ]
                )

                broad_sector = get_text(
                    company_row,
                    [
                        "broad_sector",
                        "sector"
                    ]
                )

                npm = net_profit_margin(
                    net_profit,
                    sales
                )

                opm = operating_profit_margin(
                    operating_profit,
                    sales
                )

                roe = return_on_equity(
                    net_profit,
                    equity_capital,
                    reserves
                )

                roce = return_on_capital_employed(
                    ebit,
                    equity_capital,
                    reserves,
                    borrowings
                )

                roa = return_on_assets(
                    net_profit,
                    total_assets
                )

                de = debt_to_equity(
                    borrowings,
                    equity_capital,
                    reserves
                )

                leverage_flag = high_leverage_flag(
                    de,
                    broad_sector
                )

                icr = interest_coverage_ratio(
                    operating_profit,
                    other_income,
                    interest
                )

                icr_label = interest_coverage_label(
                    icr
                )

                icr_warning = interest_coverage_warning(
                    icr
                )

                net_debt_value = net_debt(
                    borrowings,
                    investments
                )

                turnover = asset_turnover(
                    sales,
                    total_assets
                )

                fcf = free_cash_flow(
                    cfo,
                    cfi
                )

                capex_pct = capex_intensity(
                    cfi,
                    sales
                )

                capex_label = capex_intensity_label(
                    capex_pct
                )

                cfo_pat = cfo_pat_ratio(
                    cfo,
                    net_profit
                )

                cfo_quality_ratio, cfo_quality_label = (
                    cfo_quality_score(
                        cfo,
                        net_profit
                    )
                )

                fcf_conversion = fcf_conversion_rate(
                    fcf,
                    operating_profit
                )

                eps = get_value(
                    pnl_row,
                    [
                        "eps",
                        "earnings_per_share"
                    ]
                )

                shares = get_value(
                    bs_row,
                    [
                        "number_of_shares",
                        "shares_outstanding",
                        "equity_shares",
                        "no_of_shares"
                    ]
                )

                equity_total = (
                    (equity_capital or 0) +
                    (reserves or 0)
                )

                book_value_per_share = None

                if shares and shares != 0:

                    book_value_per_share = (
                        equity_total / shares
                    )

                dividends = get_value(
                    pnl_row,
                    [
                        "dividend",
                        "dividends",
                        "dividend_paid"
                    ]
                )

                dividend_payout = None

                if (
                    dividends is not None
                    and net_profit is not None
                    and net_profit != 0
                ):

                    dividend_payout = (
                        dividends / net_profit
                    ) * 100

                company_history = history.get(
                    company_id,
                    {}
                )

                revenue_history = {
                    normalize_year(y): values["revenue"]
                    for y, values in company_history.items()
                    if normalize_year(y) is not None
                    and values.get("revenue") is not None
                }

                pat_history = {
                    normalize_year(y): values["pat"]
                    for y, values in company_history.items()
                    if normalize_year(y) is not None
                    and values.get("pat") is not None
                }

                eps_history = {
                    normalize_year(y): values["eps"]
                    for y, values in company_history.items()
                    if normalize_year(y) is not None
                    and values.get("eps") is not None
                }

                def cagr_window(history_data, window):

                    years_available = [
                        y for y in history_data
                        if y <= current_year
                    ]

                    years_available.sort()

                    if len(years_available) < window + 1:
                        return None, "INSUFFICIENT"

                    start_year = years_available[-(window + 1)]

                    end_year = years_available[-1]

                    return calculate_cagr(
                        history_data[start_year],
                        history_data[end_year],
                        end_year - start_year
                    )

                rev3, rev3_flag = cagr_window(
                    revenue_history,
                    3
                )

                rev5, rev5_flag = cagr_window(
                    revenue_history,
                    5
                )

                rev10, rev10_flag = cagr_window(
                    revenue_history,
                    10
                )

                pat3, pat3_flag = cagr_window(
                    pat_history,
                    3
                )

                pat5, pat5_flag = cagr_window(
                    pat_history,
                    5
                )

                pat10, pat10_flag = cagr_window(
                    pat_history,
                    10
                )

                eps3, eps3_flag = cagr_window(
                    eps_history,
                    3
                )

                eps5, eps5_flag = cagr_window(
                    eps_history,
                    5
                )

                eps10, eps10_flag = cagr_window(
                    eps_history,
                    10
                )

                quality_score = calculate_composite_quality(
                    roe,
                    npm,
                    de,
                    icr,
                    turnover
                )

                source_opm = get_value(
                    pnl_row,
                    [
                        "opm_percentage",
                        "opm_percent",
                        "operating_profit_margin"
                    ]
                )

                if cross_check_opm(
                    opm,
                    source_opm
                ):

                    logging.warning(
                        "OPM mismatch | company=%s | year=%s | "
                        "computed=%s | source=%s",
                        company_id,
                        year,
                        opm,
                        source_opm
                    )

                values = (

                    company_id,
                    current_year,

                    npm,
                    opm,
                    roe,
                    roce,
                    roa,

                    de,
                    int(leverage_flag),

                    icr,
                    icr_label,
                    int(icr_warning),

                    net_debt_value,
                    turnover,

                    fcf,
                    cfi,
                    capex_pct,

                    cfo_quality_ratio,
                    cfo_quality_label,

                    fcf_conversion,

                    eps,
                    book_value_per_share,
                    dividend_payout,

                    borrowings,
                    cfo,

                    rev3,
                    rev3_flag,

                    rev5,
                    rev5_flag,

                    rev10,
                    rev10_flag,

                    pat3,
                    pat3_flag,

                    pat5,
                    pat5_flag,

                    pat10,
                    pat10_flag,

                    eps3,
                    eps3_flag,

                    eps5,
                    eps5_flag,

                    eps10,
                    eps10_flag,

                    quality_score
                )

                cursor.execute(
                    insert_sql,
                    values
                )

                processed += 1

            except Exception as e:
                logging.error(
                    f"Error processing company {company_id} year {year}: {str(e)}\n{traceback.format_exc()}"
                )
                skipped += 1
                continue

        conn.commit()

        print(
            f"\nProcessed rows: {processed}"
        )

        print(
            f"Skipped rows: {skipped}"
        )

        cursor.execute(
            "SELECT COUNT(*) FROM financial_ratios"
        )

        count = cursor.fetchone()[0]

        print(
            f"financial_ratios rows: {count}"
        )

        print("\nRatio Engine completed successfully.")

    except sqlite3.Error as e:
        logging.error(
            f"Database error: {e}\n{traceback.format_exc()}"
        )
        print(f"ERROR: Database error - {e}")

    except Exception as e:
        logging.error(
            f"Unexpected error: {e}\n{traceback.format_exc()}"
        )
        print(f"ERROR: {e}")

    finally:
        if conn:
            try:
                conn.close()
            except sqlite3.Error as e:
                logging.error(
                    f"Error closing database connection: {e}"
                )


if __name__ == "__main__":
    main()