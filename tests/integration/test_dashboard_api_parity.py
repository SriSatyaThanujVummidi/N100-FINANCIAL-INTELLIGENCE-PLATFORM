"""
Day 42 -- Integration test: confirms the API's /screener endpoint returns the same company
set as a direct DB query using the same logic the dashboard's screener screen relies on
(financial_ratios.return_on_equity_pct, latest year per company, sanity-bound masked).

This requires the FastAPI app importable in-process (via TestClient), and reads directly
from the real nifty100.db -- no live server needs to be running for this test to pass.
"""

import sqlite3

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)
DB_PATH = "data/nifty100.db"


def _dashboard_path_roe_gte(threshold: float) -> set:
    """Mirrors the dashboard/screener's underlying query logic: latest year per company,
    ROE >= threshold, sanity-bound masked (same +/-500% bound as Day 13/17/18/36/37/39/40).
    """
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT fr.company_id, fr.return_on_equity_pct FROM financial_ratios fr
        INNER JOIN (SELECT company_id, MAX(year) AS y FROM financial_ratios GROUP BY company_id) latest
          ON fr.company_id = latest.company_id AND fr.year = latest.y
    """
    rows = conn.execute(query).fetchall()
    conn.close()
    return {
        company_id
        for company_id, roe in rows
        if roe is not None and abs(roe) <= 500 and roe >= threshold
    }


def test_screener_matches_dashboard_query_for_min_roe_15():
    dashboard_side = _dashboard_path_roe_gte(15)
    resp = client.get("/api/v1/screener", params={"min_roe": 15})
    assert resp.status_code == 200
    api_side = {c["company_id"] for c in resp.json()["results"]}
    assert api_side == dashboard_side


def test_screener_matches_dashboard_query_for_min_roe_20():
    """Second threshold, to confirm parity isn't a coincidence at one specific cutoff."""
    dashboard_side = _dashboard_path_roe_gte(20)
    resp = client.get("/api/v1/screener", params={"min_roe": 20})
    assert resp.status_code == 200
    api_side = {c["company_id"] for c in resp.json()["results"]}
    assert api_side == dashboard_side
