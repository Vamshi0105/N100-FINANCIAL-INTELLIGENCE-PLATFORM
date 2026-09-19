from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_screener_min_roe_returns_only_high_roe_companies():
    response = client.get(
        "/api/v1/screener",
        params={"min_roe": 15},
    )

    assert response.status_code == 200

    data = response.json()

    # Support either a direct list or an API response containing results.
    if isinstance(data, list):
        results = data
    else:
        results = data.get("results", data.get("companies", []))

    for company in results:
        roe = company.get("roe")

        if roe is not None:
            assert float(roe) >= 15


def test_screener_invalid_parameter_returns_400():
    response = client.get(
        "/api/v1/screener",
        params={"min_roe": "INVALID"},
    )

    assert response.status_code == 400
