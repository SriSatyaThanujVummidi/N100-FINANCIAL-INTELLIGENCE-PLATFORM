"""Day 42 -- Sector endpoint tests."""

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_sectors_returns_ten_not_eleven():
    """Real sectors table has 10 distinct broad_sector values, not spec's stated 11
    (Day 22/25/38/40 already-documented finding). Asserting against real data."""
    resp = client.get("/api/v1/sectors")
    assert resp.status_code == 200
    assert len(resp.json()) == 10


def test_sector_companies_returns_only_that_sector():
    resp = client.get("/api/v1/sectors/Information Technology/companies")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 5  # TCS, INFY, HCLTECH, TECHM, LTIM -- confirmed Day 18/39
    for company in data:
        assert company["company_id"] in {"TCS", "INFY", "HCLTECH", "TECHM", "LTIM"}


def test_unknown_sector_returns_404():
    resp = client.get("/api/v1/sectors/UNKNOWN/companies")
    assert resp.status_code == 404
