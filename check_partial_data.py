import sqlite3


conn = sqlite3.connect("data/nifty100.db")
cur = conn.cursor()


query = """
SELECT
    company_id,
    COUNT(*) AS years
FROM financial_ratios
WHERE substr(year, -3) = '-03'
GROUP BY company_id
HAVING COUNT(*) < 10
ORDER BY years, company_id
"""


rows = cur.execute(query).fetchall()

print("\nCompanies with fewer than 10 annual records:\n")

if not rows:
    print("None found.")
else:
    for company_id, years in rows:
        print(f"{company_id}: {years} years")


conn.close()