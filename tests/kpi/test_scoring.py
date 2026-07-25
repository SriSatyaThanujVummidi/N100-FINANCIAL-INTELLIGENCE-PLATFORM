"""Day 12 unit tests — composite quality score."""

import pytest
from analytics.scoring import (
    de_score,
    winsorized_percentiles,
    normalize_winsorized,
    composite_quality_score,
    composite_quality_label,
    compute_quality_scores_for_year,
)

# ---------- de_score() ----------


def test_de_score_exact_anchor_zero():
    assert de_score(0.0) == 100.0


def test_de_score_exact_anchor_half():
    assert de_score(0.5) == 85.0


def test_de_score_exact_anchor_one():
    assert de_score(1.0) == 70.0


def test_de_score_exact_anchor_two():
    assert de_score(2.0) == 50.0


def test_de_score_exact_anchor_five():
    assert de_score(5.0) == 0.0


def test_de_score_above_five_clamps_to_zero():
    assert de_score(8.0) == 0.0


def test_de_score_interpolated_midpoint():
    # Halfway between (1.0, 70) and (2.0, 50) -> 60
    assert de_score(1.5) == pytest.approx(60.0)


def test_de_score_none():
    assert de_score(None) is None


def test_de_score_negative_defensive_guard():
    assert de_score(-1.0) is None


# ---------- winsorized_percentiles() / normalize_winsorized() ----------


def test_winsorized_percentiles_basic():
    p10, p90 = winsorized_percentiles([10, 20, 30, 40, 50, 60, 70, 80, 90, 100])
    assert p10 < p90


def test_normalize_winsorized_midpoint():
    assert normalize_winsorized(50, 0, 100) == pytest.approx(50.0)


def test_normalize_winsorized_clips_above_p90():
    assert normalize_winsorized(150, 0, 100) == pytest.approx(100.0)


def test_normalize_winsorized_clips_below_p10():
    assert normalize_winsorized(-50, 0, 100) == pytest.approx(0.0)


def test_normalize_winsorized_equal_p10_p90():
    # No spread to rank against -> 50 regardless of value
    assert normalize_winsorized(999, 42, 42) == 50.0


def test_normalize_winsorized_none_value():
    assert normalize_winsorized(None, 0, 100) is None


# ---------- composite_quality_score() ----------


def test_composite_quality_score_normal():
    score = composite_quality_score(
        roe_score=80, fcf_score=60, roce_score=70, de_score_value=100
    )
    expected = 0.3 * 80 + 0.25 * 60 + 0.25 * 70 + 0.20 * 100
    assert score == pytest.approx(expected)


def test_composite_quality_score_missing_one_subscore_returns_none():
    assert composite_quality_score(80, None, 70, 100) is None


def test_composite_quality_score_all_missing():
    assert composite_quality_score(None, None, None, None) is None


# ---------- composite_quality_label() ----------


def test_composite_quality_label_excellent():
    assert composite_quality_label(85) == "Excellent"


def test_composite_quality_label_excellent_boundary():
    assert composite_quality_label(70) == "Excellent"


def test_composite_quality_label_moderate():
    assert composite_quality_label(55) == "Moderate"


def test_composite_quality_label_moderate_boundary():
    assert composite_quality_label(40) == "Moderate"


def test_composite_quality_label_weak():
    assert composite_quality_label(25) == "Weak"


def test_composite_quality_label_none():
    assert composite_quality_label(None) is None


# ---------- compute_quality_scores_for_year() ----------


def test_compute_quality_scores_for_year_basic_spread():
    rows = [
        {
            "company_id": "A",
            "return_on_equity_pct": 25,
            "return_on_capital_employed_pct": 22,
            "free_cash_flow_cr": 5000,
            "debt_to_equity": 0.0,
        },
        {
            "company_id": "B",
            "return_on_equity_pct": 15,
            "return_on_capital_employed_pct": 14,
            "free_cash_flow_cr": 1000,
            "debt_to_equity": 1.0,
        },
        {
            "company_id": "C",
            "return_on_equity_pct": 5,
            "return_on_capital_employed_pct": 6,
            "free_cash_flow_cr": -500,
            "debt_to_equity": 3.0,
        },
    ]
    results = compute_quality_scores_for_year(rows)
    by_company = {r["company_id"]: r for r in results}

    # A should score highest (best ROE/ROCE/FCF, zero debt), C lowest
    assert (
        by_company["A"]["composite_quality_score"]
        > by_company["B"]["composite_quality_score"]
    )
    assert (
        by_company["B"]["composite_quality_score"]
        > by_company["C"]["composite_quality_score"]
    )
    assert by_company["A"]["composite_quality_label"] is not None


def test_compute_quality_scores_for_year_missing_de_gives_none_score():
    # SBIN-style: no balance sheet data -> D/E missing -> composite score None
    rows = [
        {
            "company_id": "SBIN",
            "return_on_equity_pct": 15,
            "return_on_capital_employed_pct": None,
            "free_cash_flow_cr": 2000,
            "debt_to_equity": None,
        },
        {
            "company_id": "TCS",
            "return_on_equity_pct": 45,
            "return_on_capital_employed_pct": 60,
            "free_cash_flow_cr": 35000,
            "debt_to_equity": 0.09,
        },
    ]
    results = compute_quality_scores_for_year(rows)
    by_company = {r["company_id"]: r for r in results}
    assert by_company["SBIN"]["composite_quality_score"] is None
    assert by_company["TCS"]["composite_quality_score"] is not None


def test_compute_quality_scores_for_year_single_company_no_crash():
    rows = [
        {
            "company_id": "ONLY",
            "return_on_equity_pct": 20,
            "return_on_capital_employed_pct": 18,
            "free_cash_flow_cr": 1000,
            "debt_to_equity": 0.5,
        },
    ]
    results = compute_quality_scores_for_year(rows)
    assert results[0]["composite_quality_score"] is not None


def test_hal_style_implausible_roe_gets_none_score_not_inflated():
    rows = [
        {
            "company_id": "HAL",
            "return_on_equity_pct": 3816.58,
            "return_on_capital_employed_pct": 2590.99,
            "free_cash_flow_cr": 1814,
            "debt_to_equity": 0.62,
        },
        {
            "company_id": "TCS",
            "return_on_equity_pct": 50.94,
            "return_on_capital_employed_pct": 60.21,
            "free_cash_flow_cr": 50429,
            "debt_to_equity": 0.09,
        },
    ]
    results = compute_quality_scores_for_year(rows)
    by_company = {r["company_id"]: r for r in results}
    assert by_company["HAL"]["composite_quality_score"] is None
    assert by_company["HAL"]["composite_quality_label"] is None
    assert by_company["TCS"]["composite_quality_score"] is not None


def test_implausible_value_excluded_from_percentile_pool_protects_other_companies():
    # Without the fix, HAL's extreme ROE would inflate the P90 used to
    # score B and C, compressing both of their scores artificially low.
    rows_with_hal = [
        {
            "company_id": "HAL",
            "return_on_equity_pct": 3816.58,
            "return_on_capital_employed_pct": 2590.99,
            "free_cash_flow_cr": 1814,
            "debt_to_equity": 0.62,
        },
        {
            "company_id": "B",
            "return_on_equity_pct": 20.0,
            "return_on_capital_employed_pct": 18.0,
            "free_cash_flow_cr": 2000,
            "debt_to_equity": 0.5,
        },
        {
            "company_id": "C",
            "return_on_equity_pct": 15.0,
            "return_on_capital_employed_pct": 14.0,
            "free_cash_flow_cr": 1000,
            "debt_to_equity": 1.0,
        },
    ]
    rows_without_hal = [r for r in rows_with_hal if r["company_id"] != "HAL"]

    results_with = {
        r["company_id"]: r for r in compute_quality_scores_for_year(rows_with_hal)
    }
    results_without = {
        r["company_id"]: r for r in compute_quality_scores_for_year(rows_without_hal)
    }

    # B's score should be identical whether or not HAL's row was present --
    # proof that HAL no longer pollutes the percentile pool.
    assert results_with["B"]["composite_quality_score"] == pytest.approx(
        results_without["B"]["composite_quality_score"]
    )


def test_implausible_roce_alone_also_excludes_company():
    rows = [
        {
            "company_id": "WEIRD",
            "return_on_equity_pct": 25.0,
            "return_on_capital_employed_pct": 9999.0,
            "free_cash_flow_cr": 500,
            "debt_to_equity": 1.0,
        },
        {
            "company_id": "NORMAL",
            "return_on_equity_pct": 18.0,
            "return_on_capital_employed_pct": 16.0,
            "free_cash_flow_cr": 800,
            "debt_to_equity": 0.8,
        },
    ]
    results = {r["company_id"]: r for r in compute_quality_scores_for_year(rows)}
    assert results["WEIRD"]["composite_quality_score"] is None
    assert results["NORMAL"]["composite_quality_score"] is not None


def test_all_plausible_unaffected_by_fix():
    rows = [
        {
            "company_id": "A",
            "return_on_equity_pct": 25,
            "return_on_capital_employed_pct": 22,
            "free_cash_flow_cr": 5000,
            "debt_to_equity": 0.0,
        },
        {
            "company_id": "B",
            "return_on_equity_pct": 15,
            "return_on_capital_employed_pct": 14,
            "free_cash_flow_cr": 1000,
            "debt_to_equity": 1.0,
        },
    ]
    results = compute_quality_scores_for_year(rows)
    assert all(r["composite_quality_score"] is not None for r in results)
