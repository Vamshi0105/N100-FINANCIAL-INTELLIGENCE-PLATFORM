"""
NIFTY 100 Financial Intelligence Platform
Sprint 1 - ETL Execution Script
"""

from pathlib import Path
import sys

import pandas as pd

# Project root
ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

sys.path.insert(
    0,
    str(ROOT)
)

from src.etl.loader import (
    CORE,
    SUPPLEMENTARY,
    read_excel,
    load_database
)

from src.etl.validator import (
    validate_all
)


# ---------------------------------------------------------
# Create output directory
# ---------------------------------------------------------

OUTPUT = (
    ROOT
    / "output"
)

OUTPUT.mkdir(
    parents=True,
    exist_ok=True
)


# ---------------------------------------------------------
# Read all Excel files
# ---------------------------------------------------------

print()
print("=" * 70)
print("NIFTY 100 FINANCIAL INTELLIGENCE PLATFORM")
print("SPRINT 1 - DATA FOUNDATION")
print("=" * 70)
print()

frames = {}

for table_name in (
    CORE + SUPPLEMENTARY
):

    print(
        f"Loading source: "
        f"{table_name}.xlsx"
    )

    frames[table_name] = (
        read_excel(
            ROOT,
            table_name
        )
    )

    print(
        f"Rows: "
        f"{len(frames[table_name])}"
    )


# ---------------------------------------------------------
# Data Quality Validation
# ---------------------------------------------------------

print()
print("-" * 70)
print("RUNNING DATA QUALITY RULES DQ-01 TO DQ-16")
print("-" * 70)
print()

validation = validate_all(
    frames
)

validation_file = (
    OUTPUT
    / "validation_failures.csv"
)

validation.to_csv(
    validation_file,
    index=False
)


print(
    f"Total validation findings: "
    f"{len(validation)}"
)

if not validation.empty:

    severity_counts = (
        validation["severity"]
        .value_counts()
    )

    print()
    print("Severity summary:")

    print(
        severity_counts
    )


# ---------------------------------------------------------
# Build SQLite Database
# ---------------------------------------------------------

print()
print("-" * 70)
print("BUILDING SQLITE DATABASE")
print("-" * 70)
print()

database_path = (
    ROOT
    / "data"
    / "nifty100.db"
)

(
    loaded_frames,
    audit,
    foreign_key_errors
) = load_database(
    ROOT,
    database_path
)


# ---------------------------------------------------------
# Audit Summary
# ---------------------------------------------------------

print()
print("-" * 70)
print("LOAD AUDIT")
print("-" * 70)
print()

print(
    audit.to_string(
        index=False
    )
)


# ---------------------------------------------------------
# Foreign Key Check
# ---------------------------------------------------------

print()
print("-" * 70)
print("FOREIGN KEY VALIDATION")
print("-" * 70)
print()

if len(foreign_key_errors) == 0:

    print(
        "PASS - No foreign key violations"
    )

else:

    print(
        "FAIL - Foreign key violations:"
    )

    for error in foreign_key_errors:

        print(error)


# ---------------------------------------------------------
# Final report
# ---------------------------------------------------------

report_file = (
    OUTPUT
    / "final_validation_report.txt"
)

critical_count = 0

if not validation.empty:

    critical_count = int(
        (
            validation["severity"]
            == "CRITICAL"
        ).sum()
    )


with open(
    report_file,
    "w",
    encoding="utf-8"
) as file:

    file.write(
        "NIFTY 100 FINANCIAL INTELLIGENCE PLATFORM\n"
    )

    file.write(
        "SPRINT 1 - FINAL VALIDATION REPORT\n"
    )

    file.write(
        "=" * 60 + "\n\n"
    )

    file.write(
        f"Validation findings: "
        f"{len(validation)}\n"
    )

    file.write(
        f"Critical findings: "
        f"{critical_count}\n"
    )

    file.write(
        f"Foreign key violations: "
        f"{len(foreign_key_errors)}\n\n"
    )

    file.write(
        "DATABASE:\n"
    )

    file.write(
        str(database_path)
        + "\n\n"
    )

    file.write(
        "AUDIT:\n"
    )

    file.write(
        audit.to_string(
            index=False
        )
    )

    file.write(
        "\n"
    )


print()
print("=" * 70)
print("SPRINT 1 ETL COMPLETED")
print("=" * 70)
print()

print(
    f"Database: {database_path}"
)

print(
    f"Validation log: {validation_file}"
)

print(
    f"Load audit: "
    f"{OUTPUT / 'load_audit.csv'}"
)

print(
    f"Final report: {report_file}"
)

print()