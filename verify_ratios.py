import sqlite3

DB_PATH = "data/nifty100.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("\n===== FINANCIAL RATIOS CHECK =====")

cursor.execute(
    "SELECT COUNT(*) FROM financial_ratios"
)

count = cursor.fetchone()[0]

print("Total rows:", count)

if count >= 1100:
    print("PASS: 1,100+ rows")
else:
    print("FAIL: Less than 1,100 rows")


print("\n===== DISTINCT COMPANIES =====")

cursor.execute(
    "SELECT COUNT(DISTINCT company_id) "
    "FROM financial_ratios"
)

companies = cursor.fetchone()[0]

print(
    "Companies:",
    companies
)


print("\n===== YEAR RANGE =====")

cursor.execute("""
    SELECT MIN(year), MAX(year)
    FROM financial_ratios
""")

print(
    cursor.fetchone()
)


print("\n===== KPI NULL CHECK =====")

columns = [
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
    "cash_from_operations_cr",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
    "eps_cagr_5yr",
    "composite_quality_score"
]

for column in columns:

    cursor.execute(
        f"""
        SELECT
            COUNT(*),
            COUNT({column})
        FROM financial_ratios
        """
    )

    total, populated = cursor.fetchone()

    print(
        f"{column:35} "
        f"{populated}/{total}"
    )


conn.close()