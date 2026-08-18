import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DB = ROOT / "data" / "nifty100.db"
SQL_FILE = ROOT / "notebooks" / "exploratory_queries.sql"

connection = sqlite3.connect(DB)

# Enable foreign keys
connection.execute("PRAGMA foreign_keys = ON")

sql = SQL_FILE.read_text(encoding="utf-8")

# Split the file into individual statements
queries = [
    query.strip()
    for query in sql.split(";")
    if query.strip()
]

for number, query in enumerate(queries, 1):

    print()
    print("=" * 70)
    print(f"QUERY {number}")
    print("=" * 70)

    try:

        cursor = connection.execute(query)

        columns = [
            description[0]
            for description in cursor.description
        ]

        print(" | ".join(columns))
        print("-" * 70)

        rows = cursor.fetchall()

        for row in rows[:20]:
            print(" | ".join(
                str(value)
                for value in row
            ))

        if len(rows) > 20:
            print(
                f"\nShowing 20 of {len(rows)} rows"
            )

    except Exception as error:

        print("ERROR:")
        print(error)


connection.close()

print()
print("=" * 70)
print("EXPLORATORY QUERIES COMPLETED")
print("=" * 70)