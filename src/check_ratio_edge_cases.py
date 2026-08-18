import sqlite3
import logging
import os


DB_PATH = "data/nifty100.db"

OUTPUT = "output/ratio_edge_cases.log"

os.makedirs(
    "output",
    exist_ok=True
)


logging.basicConfig(
    filename=OUTPUT,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


conn = sqlite3.connect(
    DB_PATH
)

cursor = conn.cursor()

print("Checking ratio edge cases...")

# First, check the schema
cursor.execute("PRAGMA table_info(companies)")
print("Companies table columns:")
companies_columns = cursor.fetchall()
for row in companies_columns:
    print(row)

cursor.execute("PRAGMA table_info(financial_ratios)")
print("Financial_ratios table columns:")
fr_columns = cursor.fetchall()
for row in fr_columns:
    print(row)

# ============================================================
# ROCE SOURCE COMPARISON
# ============================================================

cursor.execute("""
    SELECT
        fr.company_id,
        fr.year,
        fr.return_on_capital_employed_pct,
        c.roce_percentage
    FROM financial_ratios fr
    JOIN companies c
        ON fr.company_id = c.id
    WHERE c.roce_percentage IS NOT NULL
""")


for (
    company_id,
    year,
    computed,
    source
) in cursor.fetchall():

    if computed is None or source is None:
        continue

    difference = abs(
        computed - source
    )

    if difference > 5:

        logging.warning(
            "ROCE anomaly | "
            "company=%s | year=%s | "
            "computed=%.4f | source=%.4f | "
            "difference=%.4f | "
            "category=REVIEW_REQUIRED",
            company_id,
            year,
            computed,
            source,
            difference
        )


# ============================================================
# ROE SOURCE COMPARISON
# ============================================================

cursor.execute("""
    SELECT
        fr.company_id,
        fr.year,
        fr.return_on_equity_pct,
        c.roe_percentage
    FROM financial_ratios fr
    JOIN companies c
        ON fr.company_id = c.id
    WHERE c.roe_percentage IS NOT NULL
""")


for (
    company_id,
    year,
    computed,
    source
) in cursor.fetchall():

    if computed is None or source is None:
        continue

    difference = abs(
        computed - source
    )

    if difference > 5:

        logging.warning(
            "ROE anomaly | "
            "company=%s | year=%s | "
            "computed=%.4f | source=%.4f | "
            "difference=%.4f | "
            "category=REVIEW_REQUIRED",
            company_id,
            year,
            computed,
            source,
            difference
        )


# ============================================================
# FINANCIALS SECTOR
# ============================================================

cursor.execute("""
    SELECT
        c.id,
        s.broad_sector
    FROM companies c
    JOIN sectors s
        ON c.id = s.company_id
    WHERE s.broad_sector = 'Financials'
""")


financials = cursor.fetchall()

print(
    "Financials companies:",
    len(financials)
)


for company_id, sector in financials:

    logging.info(
        "Financials carve-out | "
        "company=%s | "
        "high leverage warning suppressed",
        company_id
    )


conn.close()

print(
    f"Edge case log created: {OUTPUT}"
)