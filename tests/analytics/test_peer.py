"""Sandbox tests for Day 18 peer percentile rankings."""

import pandas as pd
import pytest

from src.analytics.peer import compute_peer_percentiles, get_peer_percentile


@pytest.fixture
def sample_universe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "company_id": ["A", "B", "C", "D"],
            "year": ["2024-03"] * 4,
            "peer_group_name": ["GroupX", "GroupX", "GroupX", None],  # D: no group
            "is_benchmark": [1, 0, 0, 0],
            "return_on_equity_pct": [30.0, 20.0, 10.0, 15.0],
            "return_on_capital_employed_pct": [25.0, 18.0, 9.0, 12.0],
            "net_profit_margin_pct": [15.0, 12.0, 8.0, 10.0],
            "debt_to_equity": [0.1, 0.5, 1.0, 0.3],
            "free_cash_flow_cr": [100.0, 50.0, 20.0, 40.0],
            "pat_cagr_5yr": [20.0, 15.0, 5.0, 10.0],
            "revenue_cagr_5yr": [18.0, 14.0, 6.0, 9.0],
            "eps_cagr_5yr": [16.0, 13.0, 4.0, 8.0],
            "interest_coverage": [10.0, 6.0, 2.0, 5.0],
            "asset_turnover": [1.5, 1.2, 0.8, 1.0],
            "sanity_flagged": [False, False, False, False],
        }
    )


def test_higher_roe_gets_higher_percentile(sample_universe):
    """Spec's own Day 21 exit criterion: within a peer group, the company
    with the highest ROE should have the highest ROE percentile rank."""
    result = compute_peer_percentiles(sample_universe)
    roe_rows = result[result["metric"] == "return_on_equity_pct"].set_index(
        "company_id"
    )
    assert roe_rows.loc["A", "percentile_rank"] > roe_rows.loc["B", "percentile_rank"]
    assert roe_rows.loc["B", "percentile_rank"] > roe_rows.loc["C", "percentile_rank"]


def test_de_inverted_lower_debt_gets_higher_percentile(sample_universe):
    """D/E must be INVERTED: company A has the LOWEST D/E (0.1) and
    should get the HIGHEST percentile rank for this metric, per spec
    Module 9 feature 4.1: 'invert the percentile so lower D/E = higher
    percentile rank'."""
    result = compute_peer_percentiles(sample_universe)
    de_rows = result[result["metric"] == "debt_to_equity"].set_index("company_id")
    assert de_rows.loc["A", "percentile_rank"] > de_rows.loc["C", "percentile_rank"]


def test_company_with_no_peer_group_excluded_from_percentiles(sample_universe):
    """Company D has peer_group_name=None -- must not appear in the
    percentiles table at all (handled separately via
    get_peer_percentile's 'No peer group assigned' message)."""
    result = compute_peer_percentiles(sample_universe)
    assert "D" not in result["company_id"].values


def test_get_peer_percentile_message_for_unassigned_company(sample_universe):
    result = compute_peer_percentiles(sample_universe)
    message = get_peer_percentile("D", result)
    assert message == "No peer group assigned"


def test_get_peer_percentile_returns_rows_for_assigned_company(sample_universe):
    result = compute_peer_percentiles(sample_universe)
    rows = get_peer_percentile("A", result)
    assert isinstance(rows, pd.DataFrame)
    assert len(rows) == len(sample_universe.columns) - len(
        ["company_id", "year", "peer_group_name", "is_benchmark", "sanity_flagged"]
    )


def test_sanity_flagged_company_has_null_roe_roce_percentile():
    """A company masked by Day 13's sanity-bound check (ROE/ROCE set to
    None before this function runs) must produce a NaN percentile for
    those two metrics specifically -- not a corrupted rank, not a crash.
    Mirrors the real Life Insurance group finding: HDFCLIFE/ICICIPRULI
    both flagged, LICI/SBILIFE clean."""
    df = pd.DataFrame(
        {
            "company_id": ["LICI", "HDFCLIFE", "SBILIFE", "ICICIPRULI"],
            "year": ["2024-03"] * 4,
            "peer_group_name": ["Life Insurance"] * 4,
            "is_benchmark": [1, 0, 0, 0],
            "return_on_equity_pct": [40.0, None, 20.0, None],  # masked
            "return_on_capital_employed_pct": [35.0, None, 18.0, None],  # masked
            "net_profit_margin_pct": [10.0, 8.0, 9.0, 7.0],
            "debt_to_equity": [0.0, 0.1, 0.0, 0.2],
            "free_cash_flow_cr": [500.0, 300.0, 200.0, 100.0],
            "pat_cagr_5yr": [12.0, 10.0, 8.0, 6.0],
            "revenue_cagr_5yr": [11.0, 9.0, 7.0, 5.0],
            "eps_cagr_5yr": [10.0, 8.0, 6.0, 4.0],
            "interest_coverage": [50.0, 40.0, 30.0, 20.0],
            "asset_turnover": [0.5, 0.4, 0.3, 0.2],
            "sanity_flagged": [False, True, False, True],
        }
    )
    result = compute_peer_percentiles(df)
    roe_rows = result[result["metric"] == "return_on_equity_pct"].set_index(
        "company_id"
    )

    assert pd.isna(roe_rows.loc["HDFCLIFE", "percentile_rank"])
    assert pd.isna(roe_rows.loc["ICICIPRULI", "percentile_rank"])
    assert pd.notna(roe_rows.loc["LICI", "percentile_rank"])
    assert pd.notna(roe_rows.loc["SBILIFE", "percentile_rank"])
