import sqlite3


DB_PATH = "data/nifty100.db"


conn = sqlite3.connect(
    DB_PATH
)

cursor = conn.cursor()


query = """
SELECT
    company_id,
    year,
    return_on_equity_pct,
    debt_to_equity
FROM financial_ratios
WHERE return_on_equity_pct > 15
  AND debt_to_equity < 1
ORDER BY return_on_equity_pct DESC
"""


cursor.execute(query)

rows = cursor.fetchall()


print("\n===== SCREENER =====")

print(
    "Matching company-year rows:",
    len(rows)
)


for row in rows:

    print(
        f"Company={row[0]} | "
        f"Year={row[1]} | "
        f"ROE={row[2]:.2f}% | "
        f"D/E={row[3]:.2f}"
    )


if 15 <= len(rows) <= 50:

    print(
        "\nPASS: Result count is between 15 and 50."
    )

else:

    print(
        "\nREVIEW: Result count is outside expected range."
    )


conn.close()