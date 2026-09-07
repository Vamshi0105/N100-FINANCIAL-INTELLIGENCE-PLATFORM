from __future__ import annotations

import sqlite3
from pathlib import Path

from analytics.cash_flow import (
    generate_capital_allocation_csv,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DB_PATH = (
    PROJECT_ROOT
    / "data"
    / "nifty100.db"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "output"
    / "capital_allocation.csv"
)


def main():
    """
    Generate the latest capital allocation pattern
    for each company.

    The dashboard needs one latest annual record
    per company.
    """

    print(f"Database: {DB_PATH}")
    print(f"Output: {OUTPUT_PATH}")

    with sqlite3.connect(DB_PATH) as connection:

        cursor = connection.cursor()

        # ---------------------------------------------
        # Latest annual cash flow record per company.
        #
        # We use March year-end records (YYYY-03).
        # ---------------------------------------------

        cursor.execute(
            """
            SELECT
                cf.company_id,
                cf.year,
                cf.operating_activity AS cfo,
                cf.investing_activity AS cfi,
                cf.financing_activity AS cff

            FROM cashflow cf

            INNER JOIN (
                SELECT
                    company_id,
                    MAX(year) AS latest_year

                FROM cashflow

                WHERE year LIKE '%-03'

                GROUP BY company_id
            ) latest

                ON cf.company_id = latest.company_id
                AND cf.year = latest.latest_year

            ORDER BY cf.company_id
            """
        )

        rows = cursor.fetchall()

    print(
        f"\nLatest annual records found: {len(rows)}"
    )

    if not rows:

        print(
            "WARNING: No annual cash flow records found."
        )
        return

    records = []

    for (
        company_id,
        year,
        cfo,
        cfi,
        cff,
    ) in rows:

        records.append(
            {
                "company_id": company_id,
                "year": year,
                "cfo": cfo,
                "cfi": cfi,
                "cff": cff,
            }
        )

    # ---------------------------------------------
    # Use the existing analytics function.
    # ---------------------------------------------

    generate_capital_allocation_csv(
        records,
        output_path=OUTPUT_PATH,
    )

    print(
        f"\nCreated: {OUTPUT_PATH}"
    )

    print(
        f"Rows written: {len(records)}"
    )

    # ---------------------------------------------
    # Print pattern summary.
    # ---------------------------------------------

    pattern_counts = {}

    for record in records:

        from analytics.cash_flow import (
            capital_allocation_pattern,
        )

        pattern = capital_allocation_pattern(
            record["cfo"],
            record["cfi"],
            record["cff"],
        )

        pattern_counts[pattern] = (
            pattern_counts.get(
                pattern,
                0,
            )
            + 1
        )

    print("\nPattern counts:")

    for pattern, count in sorted(
        pattern_counts.items()
    ):
        print(
            f"{pattern}: {count}"
        )


if __name__ == "__main__":
    main()