"""Day 42 -- API health endpoint tests."""

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_health_returns_200_and_ok_status():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_health_db_row_counts_present():
    resp = client.get("/api/v1/health")
    data = resp.json()
    assert "db_row_counts" in data
    # Real schema has 12 tables (Day 4/38 finding), not spec's literal "10" -- asserting
    # against the confirmed real count, not the spec's inconsistent number.
    assert len(data["db_row_counts"]) == 12
    assert data["db_row_counts"]["companies"] == 92


def test_health_has_uptime_and_version():
    resp = client.get("/api/v1/health")
    data = resp.json()
    assert "uptime_seconds" in data
    assert "version" in data
