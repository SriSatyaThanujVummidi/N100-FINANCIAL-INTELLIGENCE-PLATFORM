"""Day 42 -- Company endpoint tests."""

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_list_companies_returns_92():
    resp = client.get("/api/v1/companies")
    assert resp.status_code == 200
    assert len(resp.json()) == 92


def test_get_tcs_returns_correct_data():
    resp = client.get("/api/v1/companies/TCS")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "TCS"
    assert data["company_name"] == "Tata Consultancy Services Ltd"
    assert data["latest_ratios"] is not None
    assert (
        data["latest_ratios"]["return_on_equity_pct"]
        == data["latest_ratios"]["return_on_equity_pct"]
    )  # not NaN


def test_get_invalid_ticker_returns_404():
    resp = client.get("/api/v1/companies/INVALID")
    assert resp.status_code == 404


def test_sbin_bs_returns_empty_not_error():
    """SBIN has a genuine zero-row balance sheet gap (Day 6) -- must be [] with 200, not an error."""
    resp = client.get("/api/v1/companies/SBIN/bs")
    assert resp.status_code == 200
    assert resp.json() == []
