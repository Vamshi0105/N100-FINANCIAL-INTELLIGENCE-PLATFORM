from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_health_returns_200():
    response = client.get("/api/v1/health")

    assert response.status_code == 200


def test_health_status_is_ok():
    response = client.get("/api/v1/health")

    assert response.json()["status"] == "ok"


def test_health_contains_db_row_counts():
    response = client.get("/api/v1/health")

    data = response.json()

    assert "db_row_counts" in data

    required_tables = {
        "analysis",
        "balancesheet",
        "cashflow",
        "companies",
        "documents",
        "financial_ratios",
        "market_cap",
        "peer_groups",
        "profitandloss",
        "sectors",
    }

    row_counts = data["db_row_counts"]

    assert required_tables.issubset(row_counts.keys())

    for table in required_tables:
        assert isinstance(row_counts[table], int)
        assert row_counts[table] >= 0
