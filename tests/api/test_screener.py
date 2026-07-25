"""Day 42 -- Screener endpoint tests."""

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_screener_min_roe_filters_correctly():
    resp = client.get("/api/v1/screener", params={"min_roe": 15})
    assert resp.status_code == 200
    data = resp.json()["results"]
    assert len(data) > 0
    for company in data:
        assert company["return_on_equity_pct"] >= 15


def test_screener_invalid_param_returns_400():
    resp = client.get("/api/v1/screener", params={"min_roe": "abc"})
    assert resp.status_code == 400
