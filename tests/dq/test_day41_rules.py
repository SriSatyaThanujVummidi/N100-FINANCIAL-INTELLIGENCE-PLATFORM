"""Day 41 -- 14 DQ rule tests, one crafted violation per rule (spec Section 23).
Signatures confirmed live against src/etl/validator.py, not guessed."""

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
    dq14_eps_sign_consistency,
    dq16_coverage_check,
)


def _has(violations, rule_id, severity):
    return any(
        v["rule_id"] == rule_id and v["severity"] == severity for v in violations
    )


def test_dq01_company_pk_uniqueness():
    df = pd.DataFrame({"id": ["TCS", "TCS"], "company_name": ["A", "B"]})
    assert _has(dq01_company_pk_uniqueness(df), "DQ-01", "CRITICAL")


def test_dq02_annual_pk_uniqueness():
    df = pd.DataFrame(
        {
            "company_id": ["TCS", "TCS"],
            "year": ["2023-03", "2023-03"],
            "sales": [100, 100],
        }
    )
    assert _has(dq02_annual_pk_uniqueness(df, "profitandloss"), "DQ-02", "CRITICAL")


def test_dq03_fk_integrity():
    df = pd.DataFrame({"company_id": ["NOTREAL"], "year": ["2023-03"], "sales": [100]})
    assert _has(
        dq03_fk_integrity(df, "profitandloss", valid_ids={"TCS", "INFY"}),
        "DQ-03",
        "CRITICAL",
    )


def test_dq04_bs_balance():
    df = pd.DataFrame(
        {
            "company_id": ["TCS"],
            "year": ["2023-03"],
            "total_assets": [1000],
            "total_liabilities": [1200],
        }
    )
    assert _has(dq04_balance_sheet_balance(df), "DQ-04", "WARNING")


def test_dq05_opm_cross_check():
    df = pd.DataFrame(
        {
            "company_id": ["TCS"],
            "year": ["2023-03"],
            "sales": [1000],
            "operating_profit": [250],
            "opm_percentage": [50.0],
        }
    )
    assert _has(dq05_opm_cross_check(df), "DQ-05", "WARNING")


def test_dq06_positive_sales():
    df = pd.DataFrame({"company_id": ["TCS"], "year": ["2023-03"], "sales": [0]})
    assert _has(dq06_positive_sales(df, financial_ids=set()), "DQ-06", "WARNING")


def test_dq07_year_format():
    df = pd.DataFrame({"company_id": ["TCS"], "year": ["invalid-year"], "sales": [100]})
    assert _has(dq07_year_format(df, "profitandloss"), "DQ-07", "CRITICAL")


def test_dq08_ticker_format():
    df = pd.DataFrame({"company_id": ["X"], "company_name": ["Too Short Ticker"]})
    assert _has(dq08_ticker_format(df, "companies"), "DQ-08", "CRITICAL")


def test_dq09_net_cash_check():
    df = pd.DataFrame(
        {
            "company_id": ["TCS"],
            "year": ["2023-03"],
            "operating_activity": [100],
            "investing_activity": [-50],
            "financing_activity": [-20],
            "net_cash_flow": [500],
        }
    )
    assert _has(dq09_net_cash_check(df), "DQ-09", "WARNING")


def test_dq10_nonneg_fixed_assets():
    df = pd.DataFrame(
        {"company_id": ["TCS"], "year": ["2023-03"], "fixed_assets": [-100]}
    )
    assert _has(dq10_non_negative_fixed_assets(df), "DQ-10", "WARNING")


def test_dq11_tax_rate_range():
    df = pd.DataFrame(
        {
            "company_id": ["TCS"],
            "year": ["2023-03"],
            "sales": [100],
            "tax_percentage": [95.0],
        }
    )
    assert _has(dq11_tax_rate_range(df), "DQ-11", "WARNING")


def test_dq12_dividend_payout_cap():
    df = pd.DataFrame(
        {
            "company_id": ["TCS"],
            "year": ["2023-03"],
            "sales": [100],
            "dividend_payout": [250.0],
        }
    )
    assert _has(dq12_dividend_payout_cap(df), "DQ-12", "WARNING")


def test_dq14_eps_sign_consistency():
    df = pd.DataFrame(
        {
            "company_id": ["TCS"],
            "year": ["2023-03"],
            "sales": [100],
            "net_profit": [500],
            "eps": [-10.0],
        }
    )
    assert _has(dq14_eps_sign_consistency(df), "DQ-14", "WARNING")


def test_dq16_coverage_check():
    pl = pd.DataFrame(
        {
            "company_id": ["TESTCO"] * 2,
            "year": ["2023-03", "2024-03"],
            "sales": [100, 110],
        }
    )
    bs = pd.DataFrame(
        {
            "company_id": ["TESTCO"] * 2,
            "year": ["2023-03", "2024-03"],
            "total_assets": [500, 550],
        }
    )
    cf = pd.DataFrame(
        {
            "company_id": ["TESTCO"] * 2,
            "year": ["2023-03", "2024-03"],
            "operating_activity": [50, 60],
        }
    )
    assert _has(dq16_coverage_check(pl, bs, cf, min_years=5), "DQ-16", "WARNING")
