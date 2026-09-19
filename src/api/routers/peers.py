"""
Peer Groups API endpoints.

Day 40 - N100 Financial Intelligence Platform
"""

from fastapi import APIRouter, HTTPException

from src.api.config import get_db_connection

router = APIRouter()


@router.get("/peers")
def get_peer_groups():
    """
    Return all available peer groups.
    """

    connection = get_db_connection()

    try:
        rows = connection.execute("""
            SELECT
                peer_group_name,
                COUNT(DISTINCT company_id) AS company_count
            FROM peer_groups
            WHERE peer_group_name IS NOT NULL
              AND TRIM(peer_group_name) <> ''
            GROUP BY peer_group_name
            ORDER BY peer_group_name
            """).fetchall()

        return {
            "count": len(rows),
            "peer_groups": [
                {
                    "peer_group": row["peer_group_name"],
                    "company_count": row["company_count"],
                }
                for row in rows
            ],
        }

    finally:
        connection.close()


@router.get("/peers/{group_name}")
def get_peer_group(group_name: str):
    """
    Return all companies in a peer group with percentile
    rankings for the available peer metrics.

    Peer groups are matched case-insensitively.

    Returns HTTP 404 when the peer group does not exist.
    """

    group_name = group_name.strip()

    if not group_name:
        raise HTTPException(
            status_code=404,
            detail="Peer group not found",
        )

    connection = get_db_connection()

    try:
        group_row = connection.execute(
            """
            SELECT DISTINCT peer_group_name
            FROM peer_groups
            WHERE LOWER(TRIM(peer_group_name)) = LOWER(?)
            LIMIT 1
            """,
            (group_name,),
        ).fetchone()

        if group_row is None:
            raise HTTPException(
                status_code=404,
                detail=f"Peer group '{group_name}' not found",
            )

        actual_group_name = group_row["peer_group_name"]

        company_rows = connection.execute(
            """
            SELECT
                pg.company_id,
                c.company_name,
                pg.is_benchmark
            FROM peer_groups pg
            LEFT JOIN companies c
                ON c.id = pg.company_id
            WHERE LOWER(TRIM(pg.peer_group_name)) = LOWER(?)
            ORDER BY
                pg.is_benchmark DESC,
                pg.company_id ASC
            """,
            (actual_group_name,),
        ).fetchall()

        percentile_rows = connection.execute(
            """
            SELECT
                pp.company_id,
                pp.metric,
                pp.value,
                pp.percentile_rank,
                pp.year
            FROM peer_percentiles pp
            WHERE LOWER(TRIM(pp.peer_group_name)) = LOWER(?)
            ORDER BY
                pp.company_id,
                pp.metric
            """,
            (actual_group_name,),
        ).fetchall()

        percentile_data = {}

        for row in percentile_rows:
            company_id = row["company_id"]

            if company_id not in percentile_data:
                percentile_data[company_id] = {}

            percentile_data[company_id][row["metric"]] = {
                "value": row["value"],
                "percentile_rank": row["percentile_rank"],
                "year": row["year"],
            }

        companies = []

        for row in company_rows:
            company_id = row["company_id"]

            companies.append(
                {
                    "ticker": company_id,
                    "company_name": row["company_name"],
                    "is_benchmark": bool(row["is_benchmark"]),
                    "metrics": percentile_data.get(
                        company_id,
                        {},
                    ),
                }
            )

        return {
            "peer_group": actual_group_name,
            "count": len(companies),
            "companies": companies,
        }

    finally:
        connection.close()


@router.get("/companies/{ticker}/peers/compare")
def compare_company_with_peers(ticker: str):
    """
    Compare a company against its peer-group average and
    designated benchmark company.

    Returns 8 radar-chart metrics:
    - ROE
    - ROCE
    - Revenue CAGR 5yr
    - PAT CAGR 5yr
    - EPS CAGR 5yr
    - FCF
    - Asset Turnover
    - Interest Coverage
    """

    ticker = ticker.strip()

    if not ticker:
        raise HTTPException(
            status_code=404,
            detail="Company not found",
        )

    connection = get_db_connection()

    try:
        # Find the company and its peer group.
        company_row = connection.execute(
            """
            SELECT
                pg.company_id,
                pg.peer_group_name
            FROM peer_groups pg
            INNER JOIN companies c
                ON c.id = pg.company_id
            WHERE LOWER(c.id) = LOWER(?)
            LIMIT 1
            """,
            (ticker,),
        ).fetchone()

        if company_row is None:
            raise HTTPException(
                status_code=404,
                detail=f"Company '{ticker}' not found",
            )

        actual_ticker = company_row["company_id"]
        peer_group = company_row["peer_group_name"]

        # Required radar metrics.
        metric_map = {
            "ROE": "ROE",
            "ROCE": "ROCE",
            "Revenue CAGR 5yr": "Revenue CAGR 5yr",
            "PAT CAGR 5yr": "PAT CAGR 5yr",
            "EPS CAGR 5yr": "EPS CAGR 5yr",
            "FCF": "FCF",
            "Asset Turnover": "Asset Turnover",
            "Interest Coverage": "Interest Coverage",
        }

        rows = connection.execute(
            """
            SELECT
                pp.company_id,
                pp.metric,
                pp.value,
                pp.year,
                pg.is_benchmark
            FROM peer_percentiles pp
            INNER JOIN peer_groups pg
                ON pg.company_id = pp.company_id
                AND pg.peer_group_name = pp.peer_group_name
            WHERE LOWER(TRIM(pp.peer_group_name)) = LOWER(?)
            """,
            (peer_group,),
        ).fetchall()

        metric_values = {}

        for row in rows:
            metric = row["metric"]

            if metric not in metric_map.values():
                continue

            if metric not in metric_values:
                metric_values[metric] = []

            metric_values[metric].append(
                {
                    "company_id": row["company_id"],
                    "value": row["value"],
                    "year": row["year"],
                    "is_benchmark": bool(row["is_benchmark"]),
                }
            )

        radar = []

        benchmark_ticker = None

        for display_metric, database_metric in metric_map.items():

            values = metric_values.get(
                database_metric,
                [],
            )

            numeric_values = [
                float(item["value"]) for item in values if item["value"] is not None
            ]

            peer_average = (
                sum(numeric_values) / len(numeric_values) if numeric_values else None
            )

            company_value = None
            company_year = None

            benchmark_value = None
            benchmark_year = None

            for item in values:

                if item["company_id"].lower() == actual_ticker.lower():
                    company_value = item["value"]
                    company_year = item["year"]

                if item["is_benchmark"]:
                    benchmark_value = item["value"]
                    benchmark_ticker = item["company_id"]
                    benchmark_year = item["year"]

            radar.append(
                {
                    "metric": display_metric,
                    "company": company_value,
                    "peer_average": (
                        round(peer_average, 4) if peer_average is not None else None
                    ),
                    "benchmark": benchmark_value,
                    "company_year": company_year,
                    "benchmark_ticker": benchmark_ticker,
                    "benchmark_year": benchmark_year,
                }
            )

        return {
            "ticker": actual_ticker,
            "peer_group": peer_group,
            "benchmark_ticker": benchmark_ticker,
            "metrics": radar,
        }

    finally:
        connection.close()
