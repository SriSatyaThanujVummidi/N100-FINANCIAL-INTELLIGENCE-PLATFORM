"""DQ rule unit tests — Sprint 3, Day 21.

Spec Module 12, feature 12.3: "Each of 14 DQ rules triggered on crafted
violation records; severity correct." The real codebase (src/etl/
validator.py, built Sprint 1 Day 3) implements 16 rules (DQ-01 through
DQ-16), matching spec Section 23's own rule table exactly — the
tracker's "14" is the same category of internal spec inconsistency
already documented for the 10-vs-12-tables and 14-vs-19-columns cases
(see PROGRESS.md Days 4/12). All 16 real rules are tested here.

Each test builds a minimal crafted DataFrame with ONE violating row (and
often one clean row alongside it) to confirm: (a) the violation is
detected, (b) it is NOT detected for the clean row (no false positive),
and (c) the severity matches spec Section 23's table exactly.

DQ-13 (URL validity) is network-dependent (requests.head against live
URLs) — tested only for its offline skip-logic (non-http/NaN values are
skipped without a network call), not its actual HTTP behaviour, which
would make this suite flaky and slow. Consistent with validator.py's own
skip_url_check=True default.
"""

import pandas as pd

from src.etl.validator import (
    dq01_company_pk_uniqueness,
    dq02_annual_pk_uniqueness,
    dq03_fk_integrity,
    dq04_balance_sheet_balance,
    dq05_opm_cross_check,
    dq06_positive_sales,
    dq07_year_format,
    dq08_ticker_format,
    dq09_net_cash_check,
    dq10_non_negative_fixed_assets,
    dq11_tax_rate_range,
    dq12_dividend_payout_cap,
    dq13_url_validity,
    dq14_eps_sign_consistency,
    dq15_strict_balance_info,
    dq16_coverage_check,
)


def test_dq01_duplicate_company_id_critical():
    df = pd.DataFrame({"id": ["TCS", "INFY", "TCS"]})
    violations = dq01_company_pk_uniqueness(df)
    assert len(violations) == 1
    assert violations[0]["rule_id"] == "DQ-01"
    assert violations[0]["severity"] == "CRITICAL"
    assert violations[0]["company_id"] == "TCS"


def test_dq01_no_duplicates_no_violation():
    df = pd.DataFrame({"id": ["TCS", "INFY", "RELIANCE"]})
    assert dq01_company_pk_uniqueness(df) == []


def test_dq02_duplicate_company_year_critical():
    df = pd.DataFrame(
        {
            "company_id": ["TCS", "TCS", "INFY"],
            "year": ["2024-03", "2024-03", "2024-03"],
        }
    )
    violations = dq02_annual_pk_uniqueness(df, "profitandloss")
    assert len(violations) == 2  # both duplicate rows flagged
    assert all(
        v["rule_id"] == "DQ-02" and v["severity"] == "CRITICAL" for v in violations
    )


def test_dq03_orphan_company_id_critical():
    df = pd.DataFrame({"company_id": ["TCS", "GHOST"], "year": ["2024-03", "2024-03"]})
    violations = dq03_fk_integrity(df, "profitandloss", valid_ids={"TCS", "INFY"})
    assert len(violations) == 1
    assert violations[0]["rule_id"] == "DQ-03"
    assert violations[0]["severity"] == "CRITICAL"
    assert violations[0]["company_id"] == "GHOST"


def test_dq04_balance_sheet_mismatch_warning():
    df = pd.DataFrame(
        {
            "company_id": ["A", "B"],
            "year": ["2024-03", "2024-03"],
            "total_assets": [1000.0, 1000.0],
            "total_liabilities": [
                1200.0,
                1005.0,
            ],  # A: 20% off (violation); B: 0.5% off (fine)
        }
    )
    violations = dq04_balance_sheet_balance(df)
    assert len(violations) == 1
    assert violations[0]["rule_id"] == "DQ-04"
    assert violations[0]["severity"] == "WARNING"
    assert violations[0]["company_id"] == "A"


def test_dq05_opm_cross_check_warning():
    df = pd.DataFrame(
        {
            "company_id": ["A"],
            "year": ["2024-03"],
            "sales": [1000.0],
            "opm_percentage": [50.0],  # source claims 50%
            "operating_profit": [200.0],  # actual computed = 20%
        }
    )
    violations = dq05_opm_cross_check(df)
    assert len(violations) == 1
    assert violations[0]["rule_id"] == "DQ-05"
    assert violations[0]["severity"] == "WARNING"


def test_dq06_zero_sales_non_financial_warning():
    df = pd.DataFrame(
        {
            "company_id": ["INDUSTRIALCO", "BANKCO"],
            "year": ["2024-03", "2024-03"],
            "sales": [0.0, 0.0],
        }
    )
    violations = dq06_positive_sales(df, financial_ids={"BANKCO"})
    assert len(violations) == 1
    assert violations[0]["rule_id"] == "DQ-06"
    assert violations[0]["severity"] == "WARNING"
    assert violations[0]["company_id"] == "INDUSTRIALCO"  # BANKCO exempt as Financials


def test_dq07_bad_year_format_critical():
    df = pd.DataFrame({"company_id": ["A", "B"], "year": ["2024-03", "garbage"]})
    violations = dq07_year_format(df, "profitandloss")
    assert len(violations) == 1
    assert violations[0]["rule_id"] == "DQ-07"
    assert violations[0]["severity"] == "CRITICAL"
    assert violations[0]["company_id"] == "B"


def test_dq08_ticker_length_out_of_range_critical():
    df = pd.DataFrame({"company_id": ["TC", "X", "A" * 15]})
    violations = dq08_ticker_format(df, "profitandloss")
    # "X" (len 1) and "AAAAAAAAAAAAAAA" (len 15) both out of the 2-12 range
    assert len(violations) == 2
    assert all(
        v["rule_id"] == "DQ-08" and v["severity"] == "CRITICAL" for v in violations
    )


def test_dq09_net_cash_mismatch_warning():
    df = pd.DataFrame(
        {
            "company_id": ["A"],
            "year": ["2024-03"],
            "operating_activity": [100.0],
            "investing_activity": [-50.0],
            "financing_activity": [-20.0],
            "net_cash_flow": [100.0],  # should be ~30, off by 70
        }
    )
    violations = dq09_net_cash_check(df)
    assert len(violations) == 1
    assert violations[0]["rule_id"] == "DQ-09"
    assert violations[0]["severity"] == "WARNING"


def test_dq10_negative_fixed_assets_warning():
    df = pd.DataFrame(
        {"company_id": ["A"], "year": ["2024-03"], "fixed_assets": [-50.0]}
    )
    violations = dq10_non_negative_fixed_assets(df)
    assert len(violations) == 1
    assert violations[0]["rule_id"] == "DQ-10"
    assert violations[0]["severity"] == "WARNING"


def test_dq11_tax_rate_out_of_range_warning():
    df = pd.DataFrame(
        {"company_id": ["A"], "year": ["2024-03"], "tax_percentage": [85.0]}
    )
    violations = dq11_tax_rate_range(df)
    assert len(violations) == 1
    assert violations[0]["rule_id"] == "DQ-11"
    assert violations[0]["severity"] == "WARNING"


def test_dq12_dividend_payout_over_200_warning():
    df = pd.DataFrame(
        {"company_id": ["A"], "year": ["2024-03"], "dividend_payout": [250.0]}
    )
    violations = dq12_dividend_payout_cap(df)
    assert len(violations) == 1
    assert violations[0]["rule_id"] == "DQ-12"
    assert violations[0]["severity"] == "WARNING"


def test_dq13_skips_non_http_and_null_without_network_call():
    """Offline-only check: non-http/NaN values are skipped via `continue`
    before any requests.head() call — no network access needed to verify
    this branch."""
    df = pd.DataFrame(
        {
            "company_id": ["A", "B"],
            "Year": [2024, 2024],
            "Annual_Report": [None, "not-a-url"],
        }
    )
    violations = dq13_url_validity(df)
    assert violations == []


def test_dq14_eps_sign_mismatch_warning():
    df = pd.DataFrame(
        {"company_id": ["A"], "year": ["2024-03"], "net_profit": [500.0], "eps": [-2.0]}
    )
    violations = dq14_eps_sign_consistency(df)
    assert len(violations) == 1
    assert violations[0]["rule_id"] == "DQ-14"
    assert violations[0]["severity"] == "WARNING"


def test_dq15_strict_mismatch_info():
    df = pd.DataFrame(
        {
            "company_id": ["A", "B"],
            "year": ["2024-03", "2024-03"],
            "total_assets": [1000.0, 500.0],
            "total_liabilities": [1000.001, 500.0],  # A: any diff; B: exact match
        }
    )
    violations = dq15_strict_balance_info(df)
    assert len(violations) == 1
    assert violations[0]["rule_id"] == "DQ-15"
    assert violations[0]["severity"] == "INFO"
    assert violations[0]["company_id"] == "A"


def test_dq16_short_history_warning():
    short_co = pd.DataFrame(
        {"company_id": ["JIOFIN"] * 2, "year": ["2023-03", "2024-03"]}
    )
    long_co = pd.DataFrame(
        {"company_id": ["TCS"] * 6, "year": [f"20{18+i}-03" for i in range(6)]}
    )
    pl_df = pd.concat([short_co, long_co], ignore_index=True)
    bs_df = pl_df.copy()
    cf_df = pl_df.copy()

    violations = dq16_coverage_check(pl_df, bs_df, cf_df, min_years=5)
    assert len(violations) == 1
    assert violations[0]["rule_id"] == "DQ-16"
    assert violations[0]["severity"] == "WARNING"
    assert violations[0]["company_id"] == "JIOFIN"
