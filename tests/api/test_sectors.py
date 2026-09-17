from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


def test_get_sectors_returns_expected_sector_count():
    response = client.get("/api/v1/sectors")

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, dict)
    assert data["count"] == 10
    assert len(data["sectors"]) == 10


def test_information_technology_sector_returns_it_companies_only():
    response = client.get(
        "/api/v1/sectors/Information%20Technology/companies"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["sector"] == "Information Technology"
    assert data["count"] == 5
    assert isinstance(data["companies"], list)

    for company in data["companies"]:
        assert company["sector"] == "Information Technology"