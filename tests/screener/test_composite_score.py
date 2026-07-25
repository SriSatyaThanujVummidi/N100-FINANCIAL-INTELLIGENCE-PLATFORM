"""Sandbox tests for the Day 17 sector-relative composite score."""

import sqlite3

import numpy as np
import pandas as pd
import pytest

from src.screener.composite_score import (
    compute_sector_relative_composite_score,
    de_score,
    icr_score,
    winsorize_and_scale_within_group,
)


def test_de_score_known_points():
    assert de_score(0.0) == pytest.approx(100.0)
    assert de_score(0.5) == pytest.approx(85.0)
    assert de_score(1.0) == pytest.approx(70.0)
    assert de_score(2.0) == pytest.approx(50.0)
    assert de_score(5.0) == pytest.approx(0.0)
    assert de_score(8.0) == pytest.approx(0.0)  # clamped beyond 5


def test_de_score_none_for_missing():
    assert de_score(None) is None
    assert de_score(np.nan) is None


def test_icr_score_known_points():
    assert icr_score(1.5, is_debt_free=False) == pytest.approx(0.0)
    assert icr_score(3.0, is_debt_free=False) == pytest.approx(50.0)
    assert icr_score(5.0, is_debt_free=False) == pytest.approx(75.0)
    assert icr_score(10.0, is_debt_free=False) == pytest.approx(100.0)
    assert icr_score(1.0, is_debt_free=False) == pytest.approx(
        0.0
    )  # below 1.5, clamped


def test_icr_score_debt_free_scores_100_regardless_of_null_icr():
    assert icr_score(None, is_debt_free=True) == pytest.approx(100.0)


def test_winsorize_scales_within_group_not_across():
    """Two 'sectors' with wildly different scales must each be scored
    0-100 relative to their OWN group, not the combined pool — this is
    the core SIEMENS fix (sector-relative, not global)."""
    df = pd.DataFrame(
        {
            "sector": ["A", "A", "A", "A", "B", "B", "B", "B"],
            "metric": [10, 20, 30, 40, 1000, 2000, 3000, 4000],
        }
    )
    result = df.groupby("sector")["metric"].transform(winsorize_and_scale_within_group)
    # Both groups' lowest value should score low, highest should score high,
    # REGARDLESS of the absolute scale difference between A and B.
    assert result.iloc[0] < result.iloc[3]  # A: 10 scores lower than 40
    assert result.iloc[4] < result.iloc[7]  # B: 1000 scores lower than 4000


def test_winsorize_single_company_sector_returns_50_not_crash():
    """A sector with only 1 company (degenerate P10==P90) must not crash
    or produce a nonsensical score — defaults to 50."""
    df = pd.DataFrame({"sector": ["SOLO"], "metric": [42.0]})
    result = df.groupby("sector")["metric"].transform(winsorize_and_scale_within_group)
    assert result.iloc[0] == pytest.approx(50.0)


def test_composite_score_valid_when_one_minor_subscore_missing():
    """Day 17 design fix: missing ONE sub-score (e.g. null ROCE, 10%
    weight -- well under the 50% MIN_AVAILABLE_WEIGHT cutoff) must still
    produce a valid weighted-average score, not None.

    This replaces the old all-or-nothing rule (borrowed from Sprint 2's
    simpler 4-input formula), which nulled 44/92 REAL companies in
    production purely because fcf_cagr_5yr legitimately can't be computed
    for volatile cash-flow histories (confirmed via
    day17_diagnose_fcf_cagr.py -- RELIANCE/LT/HDFCBANK/TATAMOTORS all
    showed real, business-normal FCF sign-crossings, e.g. RELIANCE
    swinging from -Rs52,161cr in 2019 to +Rs45,207cr in 2024).

    FCF history is seeded for BOTH companies here (6 years, 2019-2024)
    so fcf_cagr_5yr_score is computable for each -- otherwise that column
    alone would be NaN for both A and B, and the test couldn't isolate
    the ROCE-missing case in isolation.
    """
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE financial_ratios (company_id TEXT, year TEXT, free_cash_flow_cr REAL)"
    )
    fcf_history = [
        ("A", "2019-03", 26.0),
        ("A", "2020-03", 30.0),
        ("A", "2021-03", 35.0),
        ("A", "2022-03", 40.0),
        ("A", "2023-03", 45.0),
        ("A", "2024-03", 50.0),
        ("B", "2019-03", 22.0),
        ("B", "2020-03", 25.0),
        ("B", "2021-03", 28.0),
        ("B", "2022-03", 32.0),
        ("B", "2023-03", 36.0),
        ("B", "2024-03", 40.0),
    ]
    conn.executemany(
        "INSERT INTO financial_ratios (company_id, year, free_cash_flow_cr) VALUES (?, ?, ?)",
        fcf_history,
    )
    conn.commit()

    universe = pd.DataFrame(
        {
            "company_id": ["A", "B"],
            "year": ["2024-03", "2024-03"],
            "broad_sector": ["Tech", "Tech"],
            "return_on_equity_pct": [20.0, 18.0],
            "return_on_capital_employed_pct": [
                25.0,
                None,
            ],  # B missing ROCE only (10% weight)
            "net_profit_margin_pct": [15.0, 14.0],
            "revenue_cagr_5yr": [12.0, 11.0],
            "pat_cagr_5yr": [10.0, 9.0],
            "debt_to_equity": [0.3, 0.4],
            "interest_coverage": [8.0, 7.0],
            "is_debt_free": [False, False],
            "cash_from_operations_cr": [100.0, 90.0],
            "net_profit": [80.0, 70.0],
            "free_cash_flow_cr": [50.0, 40.0],
        }
    )
    result = compute_sector_relative_composite_score(universe, conn)
    assert pd.notna(
        result.loc[result["company_id"] == "A", "composite_score_sector_relative"].iloc[
            0
        ]
    )
    # B is missing only ROCE (10% weight) -- well under the 50% cutoff --
    # should STILL get a valid score now, unlike the old all-or-nothing design.
    assert pd.notna(
        result.loc[result["company_id"] == "B", "composite_score_sector_relative"].iloc[
            0
        ]
    )


def test_composite_score_none_when_majority_weight_missing():
    """A company missing MORE THAN HALF the total weight must get None --
    too little signal left in the remaining weighted average to trust it.

    Missing here: ROCE(10%) + revenue_cagr(10%) + pat_cagr(10%) +
    de_score(10%) + icr_score(5%) + cfo_pat_ratio-derived(10%) = 55%
    missing, which exceeds the 50% MIN_AVAILABLE_WEIGHT cutoff.
    free_cash_flow_cr is set to None too, but fcf_positive_flag still
    computes to 0.0 via np.where (not NaN) -- that column is NOT counted
    as missing, since the flag has a defined value either way.
    """
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE financial_ratios (company_id TEXT, year TEXT, free_cash_flow_cr REAL)"
    )
    conn.commit()

    universe = pd.DataFrame(
        {
            "company_id": ["C"],
            "year": ["2024-03"],
            "broad_sector": ["Tech"],
            "return_on_equity_pct": [20.0],
            "return_on_capital_employed_pct": [None],  # missing: 10%
            "net_profit_margin_pct": [15.0],
            "revenue_cagr_5yr": [None],  # missing: 10%
            "pat_cagr_5yr": [None],  # missing: 10%
            "debt_to_equity": [None],  # missing: de_score 10%
            "interest_coverage": [None],  # missing: icr_score 5%
            "is_debt_free": [False],
            "cash_from_operations_cr": [None],  # -> cfo_pat_ratio None: missing 10%
            "net_profit": [80.0],
            "free_cash_flow_cr": [None],  # fcf_positive_flag still computes (0.0)
        }
    )
    result = compute_sector_relative_composite_score(universe, conn)
    assert pd.isna(
        result.loc[result["company_id"] == "C", "composite_score_sector_relative"].iloc[
            0
        ]
    )


def test_sanity_flagged_company_gets_none_score_and_no_pollution():
    """A company with an implausible ROE (e.g. HAL/BEL-style, ROE in the
    thousands of %) must (a) get composite_score_sector_relative = None
    regardless of available weight, and (b) NOT distort the sector
    percentile window for a genuine peer in the same sector."""
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE financial_ratios (company_id TEXT, year TEXT, free_cash_flow_cr REAL)"
    )
    conn.commit()

    universe = pd.DataFrame(
        {
            "company_id": ["GOODCO", "BADCO"],
            "year": ["2024-03", "2024-03"],
            "broad_sector": ["Industrials", "Industrials"],
            "return_on_equity_pct": [18.0, 3816.0],  # BADCO: HAL-style implausible ROE
            "return_on_capital_employed_pct": [20.0, 2590.0],
            "net_profit_margin_pct": [12.0, 10.0],
            "revenue_cagr_5yr": [11.0, 9.0],
            "pat_cagr_5yr": [10.0, 8.0],
            "debt_to_equity": [0.4, 0.3],
            "interest_coverage": [6.0, 5.0],
            "is_debt_free": [False, False],
            "cash_from_operations_cr": [100.0, 90.0],
            "net_profit": [80.0, 70.0],
            "free_cash_flow_cr": [50.0, 40.0],
        }
    )
    result = compute_sector_relative_composite_score(universe, conn)

    badco_score = result.loc[
        result["company_id"] == "BADCO", "composite_score_sector_relative"
    ].iloc[0]
    assert pd.isna(badco_score)

    # GOODCO's ROE sub-score should reflect its own real value (18.0),
    # not be corrupted by BADCO's implausible 3816.0 stretching the
    # sector's P10/P90 window. With BADCO masked out of the pool before
    # winsorization, GOODCO is effectively the only valid data point in
    # its sector for this metric, so it should default to 50 (the
    # single-company-in-group fallback), NOT some distorted value near 0
    # (which is what would happen if 3816.0 were still in the pool
    # stretching the range).
    goodco_roe_score = result.loc[
        result["company_id"] == "GOODCO", "return_on_equity_pct_score"
    ].iloc[0]
    assert goodco_roe_score == pytest.approx(50.0)
