import pandas as pd
from fastapi.testclient import TestClient

from src.api.main import app
from src.screener.engine import run_screener

client = TestClient(app)


def test_dashboard_screener_matches_api_screener():
    """
    Verify that the dashboard screener engine and FastAPI
    screener endpoint return the same company universe
    for a shared ROE filter.
    """

    # FastAPI screener result
    response = client.get("/api/v1/screener?min_roe=15")

    assert response.status_code == 200

    api_data = response.json()

    assert api_data["count"] == 53
    assert "companies" in api_data
    assert isinstance(api_data["companies"], list)

    # API uses "ticker" as the company identifier.
    api_ids = {
        company["ticker"] for company in api_data["companies"] if company.get("ticker")
    }

    # Streamlit dashboard uses the same screener engine.
    dashboard_results = run_screener(
        filters={
            "return_on_equity_pct_min": 15,
        }
    )

    assert isinstance(dashboard_results, pd.DataFrame)
    assert "company_id" in dashboard_results.columns

    dashboard_ids = set(dashboard_results["company_id"].dropna().astype(str))

    # Both paths must return the same companies.
    assert dashboard_ids == api_ids


def test_dashboard_screener_results_respect_roe_filter():
    """
    Verify that the dashboard screener applies ROE >= 15 correctly.
    """

    results = run_screener(
        filters={
            "return_on_equity_pct_min": 15,
        }
    )

    assert not results.empty
    assert "return_on_equity_pct" in results.columns

    valid_roe = results["return_on_equity_pct"].dropna()

    assert (valid_roe >= 15).all()
