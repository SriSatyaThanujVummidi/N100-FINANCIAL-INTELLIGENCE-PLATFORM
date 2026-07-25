"""Sandbox tests for Turnaround Watch (Sprint 3, Day 16):
- D/E-declining-YoY detection
- Revenue CAGR 3yr, computed on the fly via src/analytics/cagr.py
  (not persisted in financial_ratios, per Day 15 finding)
"""

import sqlite3

import pandas as pd
import pytest

from src.screener.turnaround import compute_revenue_cagr_3yr, de_declining_yoy


@pytest.fixture
def de_history() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "company_id": ["A", "A", "A", "B", "B", "B", "C", "C"],
            "year": [
                "2022-03",
                "2023-03",
                "2024-03",
                "2022-03",
                "2023-03",
                "2024-03",
                "2023-03",
                "2024-03",
            ],
            "debt_to_equity": [1.5, 1.2, 0.9, 1.0, 1.1, 1.3, 0.5, 0.5],
        }
    )


def test_declining_de_flagged_true(de_history):
    result = de_declining_yoy(de_history)
    assert result["A"] is True  # 1.5 -> 1.2 -> 0.9, strictly declining over last 3yr


def test_rising_de_flagged_false(de_history):
    result = de_declining_yoy(de_history)
    assert result["B"] is False  # 1.0 -> 1.1 -> 1.3, rising


def test_flat_de_flagged_false(de_history):
    result = de_declining_yoy(de_history)
    assert result["C"] is False  # only 2 years, below window_years=3 default


def test_declining_de_uses_recent_window_only():
    """Day 16 fix: a company with an UP year outside the recent window
    should still pass, since only the most recent window_years matter —
    not the entire history. D at 2.0 -> 3.0 -> 1.2 -> 1.0 -> 0.8: rose in
    year 1, but the most recent 3 years (1.2 -> 1.0 -> 0.8) strictly
    decline, so this should flag True despite the earlier up-year."""
    history = pd.DataFrame(
        {
            "company_id": ["D"] * 5,
            "year": ["2020-03", "2021-03", "2022-03", "2023-03", "2024-03"],
            "debt_to_equity": [2.0, 3.0, 1.2, 1.0, 0.8],
        }
    )
    result = de_declining_yoy(history)
    assert result["D"] is True


def test_compute_revenue_cagr_3yr_normal_growth():
    """Revenue growing from 100 -> 133.1 over 3yr should give ~10% CAGR
    (matches cagr.py's own test_cagr_normal reference case, scaled)."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE profitandloss (company_id TEXT, year TEXT, sales REAL)")
    conn.executemany(
        "INSERT INTO profitandloss VALUES (?, ?, ?)",
        [
            ("GROWCO", "2021-03", 100.0),
            ("GROWCO", "2022-03", 110.0),
            ("GROWCO", "2023-03", 121.0),
            ("GROWCO", "2024-03", 133.1),
        ],
    )
    conn.commit()

    universe = pd.DataFrame({"company_id": ["GROWCO"], "year": ["2024-03"]})
    result = compute_revenue_cagr_3yr(universe, conn)

    assert result["GROWCO"] == pytest.approx(10.0, abs=0.1)


def test_compute_revenue_cagr_3yr_insufficient_history():
    """A company with < 3 years of history should get None, not crash."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE profitandloss (company_id TEXT, year TEXT, sales REAL)")
    conn.executemany(
        "INSERT INTO profitandloss VALUES (?, ?, ?)",
        [("NEWCO", "2023-03", 50.0), ("NEWCO", "2024-03", 60.0)],
    )
    conn.commit()

    universe = pd.DataFrame({"company_id": ["NEWCO"], "year": ["2024-03"]})
    result = compute_revenue_cagr_3yr(universe, conn)

    assert result["NEWCO"] is None
