import sqlite3
import csv
import os

from analytics.cashflow_kpis import (
    sign,
    capital_allocation_pattern,
    cfo_pat_ratio
)


DB_PATH = "data/nifty100.db"

OUTPUT = "output/capital_allocation.csv"


os.makedirs(
    "output",
    exist_ok=True
)


conn = sqlite3.connect(
    DB_PATH
)

cursor = conn.cursor()


cursor.execute("""
    SELECT
        fr.company_id,
        fr.year,
        cf.operating_activity as cfo,
        cf.investing_activity as cfi,
        cf.financing_activity as cff
    FROM financial_ratios fr
    JOIN cashflow cf
        ON fr.company_id = cf.company_id
        AND fr.year = cf.year
    ORDER BY fr.company_id, fr.year
""")


rows = cursor.fetchall()


with open(
    OUTPUT,
    "w",
    newline="",
    encoding="utf-8"
) as file:

    writer = csv.writer(file)

    writer.writerow([
        "company_id",
        "year",
        "cfo_sign",
        "cfi_sign",
        "cff_sign",
        "pattern_label"
    ])

    for (
        company_id,
        year,
        cfo,
        cfi,
        cff
    ) in rows:

        cfo_s = sign(cfo)

        cfi_s = sign(cfi)

        cff_s = sign(cff)

        # CFO/PAT is needed for the
        # special (+,-,-) classification.
        cursor.execute("""
            SELECT
                cash_from_operations_cr,
                pat_cagr_5yr
            FROM financial_ratios
            WHERE company_id = ?
              AND year = ?
        """, (
            company_id,
            year
        ))

        result = cursor.fetchone()

        cfo_pat = None

        # We don't use CAGR as PAT.
        # The special classification will be
        # based on CFO/PAT when source PAT
        # is available later.
        #
        # For now, normal sign pattern is used.

        label = capital_allocation_pattern(
            cfo,
            cfi,
            cff,
            cfo_pat
        )

        writer.writerow([
            company_id,
            year,
            cfo_s,
            cfi_s,
            cff_s,
            label
        ])


conn.close()


print(
    f"Created: {OUTPUT}"
)

print(
    f"Rows written: {len(rows)}"
)