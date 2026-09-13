"""
Shared API configuration and database utilities.
"""

import sqlite3
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATABASE_PATH = PROJECT_ROOT / "data" / "nifty100.db"

API_VERSION = "1.0.0"

START_TIME = time.monotonic()


def get_db_connection() -> sqlite3.Connection:
    """Create a SQLite database connection."""

    connection = sqlite3.connect(str(DATABASE_PATH))
    connection.row_factory = sqlite3.Row
    return connection