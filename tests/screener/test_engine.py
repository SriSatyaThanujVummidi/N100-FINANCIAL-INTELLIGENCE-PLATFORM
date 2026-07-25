"""Sandbox tests for src/screener/engine.py — Day 15.

Synthetic data mirrors real edge cases found in Sprints 1-2:
- Financials company with high D/E (should pass D/E filter via carve-out)
- Truly debt-free company (total_debt_cr=0, null ICR) — should pass ICR-min
- Missing-data company (total_debt_cr>0, null ICR — e.g. PNB/ADANIENSOL
  pattern) — should FAIL ICR-min, not be silently passed
- Ordinary company that legitimately fails D/E
"""

import pandas as pd
import pytest

from src.screener.engine import (
    apply_filters,
    apply_single_filter,
    fiscal_year_to_calendar_year,
    rank_and_sort,
)

CONFIG = {
    "metrics": {
        "de": "debt_to_equity",
        "icr": "interest_coverage",
        "roe": "return_on_equity_pct",
    },
    "sector_carveouts": {"de_skip_sectors": ["Financials"]},
}


@pytest.fixture
def sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "company_id": ["BANKX", "DEBTFREEX", "MISSINGDATAX", "LEVEREDX"],
            "broad_sector": ["Financials", "Industrials", "Industrials", "Industrials"],
            "debt_to_equity": [6.0, 0.0, 1.8, 3.0],
            "total_debt_cr": [50000.0, 0.0, 1200.0, 900.0],
            "interest_coverage": [4.0, None, None, 2.0],
            "return_on_equity_pct": [18.0, 14.0, 9.0, 20.0],
            "is_debt_free": [False, True, False, False],
        }
    )


def test_de_financials_carveout_passes(sample_df):
    filters = [{"metric": "de", "op": "<", "value": 1.0}]
    result = apply_filters(sample_df, filters, CONFIG)
    assert "BANKX" in result["company_id"].values  # D/E=6.0 but Financials -> exempt


def test_de_non_financials_fails_normally(sample_df):
    filters = [{"metric": "de", "op": "<", "value": 1.0}]
    result = apply_filters(sample_df, filters, CONFIG)
    assert "LEVEREDX" not in result["company_id"].values  # D/E=3.0, not Financials


def test_icr_true_debt_free_passes_min_filter(sample_df):
    filters = [{"metric": "icr", "op": ">", "value": 3.0}]
    result = apply_filters(sample_df, filters, CONFIG)
    assert "DEBTFREEX" in result["company_id"].values  # null ICR but total_debt_cr=0


def test_icr_missing_data_fails_min_filter(sample_df):
    """Critical case: null ICR with real debt outstanding must NOT auto-pass."""
    filters = [{"metric": "icr", "op": ">", "value": 3.0}]
    result = apply_filters(sample_df, filters, CONFIG)
    assert "MISSINGDATAX" not in result["company_id"].values  # null ICR, debt=1200cr


def test_combined_filters_roe_and_de(sample_df):
    filters = [
        {"metric": "roe", "op": ">", "value": 15},
        {"metric": "de", "op": "<", "value": 1.0},
    ]
    result = apply_filters(sample_df, filters, CONFIG)
    # BANKX: ROE 18>15 pass, D/E exempt (Financials) -> passes
    # LEVEREDX: ROE 20>15 pass, D/E 3.0 fails -> excluded
    assert set(result["company_id"]) == {"BANKX"}


def test_rank_and_sort_descending(sample_df):
    ranked = rank_and_sort(sample_df, "return_on_equity_pct")
    assert list(ranked["company_id"]) == [
        "LEVEREDX",
        "BANKX",
        "DEBTFREEX",
        "MISSINGDATAX",
    ]


def test_fiscal_year_to_calendar_year_parses():
    assert fiscal_year_to_calendar_year("2024-03") == 2024
    assert fiscal_year_to_calendar_year("2019-12") == 2019


def test_fiscal_year_to_calendar_year_handles_garbage():
    assert fiscal_year_to_calendar_year("garbage") is None
    assert fiscal_year_to_calendar_year(None) is None


def test_apply_single_filter_nan_fails_not_passes():
    """NaN on a plain (non-ICR) metric must fail the filter, not raise or auto-pass."""
    df = pd.DataFrame({"x": [10.0, None, 5.0]})
    mask = apply_single_filter(df, "x", ">", 8.0)
    assert list(mask) == [True, False, False]
