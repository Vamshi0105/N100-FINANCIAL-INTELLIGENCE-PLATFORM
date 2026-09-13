"""
Health API endpoints.
"""

import time

from fastapi import APIRouter

from src.api.config import (
    API_VERSION,
    START_TIME,
    get_db_connection,
)

router = APIRouter()


@router.get("/health")
def health_check():
    """
    Return API health, database row counts, uptime, and version.
    """

    connection = get_db_connection()

    try:
        tables = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()

        db_row_counts = {}

        for table in tables:
            table_name = table["name"]

            row = connection.execute(
                f'SELECT COUNT(*) AS count FROM "{table_name}"'
            ).fetchone()

            db_row_counts[table_name] = row["count"]

    finally:
        connection.close()

    uptime_seconds = time.monotonic() - START_TIME

    return {
        "status": "ok",
        "db_row_counts": db_row_counts,
        "uptime_seconds": round(uptime_seconds, 2),
        "version": API_VERSION,
    }