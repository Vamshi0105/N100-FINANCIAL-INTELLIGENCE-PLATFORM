import sqlite3

DB_PATH = "data/nifty100.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("\n===== TABLES =====")

cursor.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type='table'
    ORDER BY name
""")

tables = cursor.fetchall()

for table in tables:
    print("-", table[0])

print("\n===== TABLE STRUCTURES =====")

for (table_name,) in tables:
    print(f"\n--- {table_name} ---")

    cursor.execute(f"PRAGMA table_info({table_name})")

    columns = cursor.fetchall()

    for column in columns:
        print(
            f"{column[1]:35} "
            f"type={column[2]:15} "
            f"not_null={column[3]}"
        )

conn.close()