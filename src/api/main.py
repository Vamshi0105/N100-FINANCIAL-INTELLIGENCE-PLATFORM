"""
N100 Financial Intelligence Platform
FastAPI Application Entry Point

Day 38 - FastAPI Server Scaffold
"""

import logging
import sqlite3
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import (
    companies,
    documents,
    health,
    peers,
    portfolio,
    screener,
    sectors,
    valuation,
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = PROJECT_ROOT / "data" / "nifty100.db"

API_VERSION = "1.0.0"

# Application start time for uptime calculation
START_TIME = time.monotonic()


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("n100.api")


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def get_db_connection() -> sqlite3.Connection:
    """
    Create a SQLite connection to the N100 database.

    Row factory allows rows to be accessed by column name.
    """
    connection = sqlite3.connect(str(DATABASE_PATH))
    connection.row_factory = sqlite3.Row
    return connection


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="N100 Financial Intelligence API",
    description="REST API for the N100 Financial Intelligence Platform",
    version=API_VERSION,
)


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request logging middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def request_logging_middleware(
    request: Request,
    call_next,
):
    """Log HTTP method, path, and response time for every request."""

    start = time.perf_counter()

    try:
        response = await call_next(request)
        return response
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000

        logger.info(
            "%s %s | %.2f ms",
            request.method,
            request.url.path,
            elapsed_ms,
        )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

API_PREFIX = "/api/v1"

app.include_router(
    companies.router,
    prefix=API_PREFIX,
    tags=["Companies"],
)

app.include_router(
    screener.router,
    prefix=API_PREFIX,
    tags=["Screener"],
)

app.include_router(
    sectors.router,
    prefix=API_PREFIX,
    tags=["Sectors"],
)

app.include_router(
    peers.router,
    prefix=API_PREFIX,
    tags=["Peers"],
)

app.include_router(
    valuation.router,
    prefix=API_PREFIX,
    tags=["Valuation"],
)

app.include_router(
    portfolio.router,
    prefix=API_PREFIX,
    tags=["Portfolio"],
)

app.include_router(
    documents.router,
    prefix=API_PREFIX,
    tags=["Documents"],
)

app.include_router(
    health.router,
    prefix=API_PREFIX,
    tags=["Health"],
)


# ---------------------------------------------------------------------------
# Root endpoint
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    """Basic API information."""

    return {
        "name": "N100 Financial Intelligence API",
        "version": API_VERSION,
        "docs": "/docs",
        "health": "/api/v1/health",
    }