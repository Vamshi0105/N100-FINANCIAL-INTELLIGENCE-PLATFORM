from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


def test_get_companies_returns_92_records():
    response = client.get("/api/v1/companies")

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, dict)
    assert data["count"] == 92
    assert "companies" in data
    assert isinstance(data["companies"], list)
    assert len(data["companies"]) == 92


def test_get_tcs_returns_correct_data():
    response = client.get("/api/v1/companies/TCS")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == "TCS"

    assert "company" in data
    assert data["company"]["id"] == "TCS"
    assert data["company"]["company_name"] == "Tata Consultancy Services Ltd"

    assert "latest_year_kpis" in data
    assert data["latest_year_kpis"]["company_id"] == "TCS"

    assert "sector" in data
    assert data["sector"]["company_id"] == "TCS"


def test_invalid_company_returns_404():
    response = client.get("/api/v1/companies/INVALID")

    assert response.status_code == 404