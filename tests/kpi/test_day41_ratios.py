"""Day 41 -- KPI formula tests, corrected against real function signatures."""

import pytest
from src.analytics.ratios import (
    return_on_equity,
    debt_to_equity,
    interest_coverage_ratio,
    high_leverage_flag,
)
from src.analytics.cagr import cagr
from src.analytics.cashflow_kpis import cfo_pat_ratio


def test_roe_positive_equity():
    assert round(return_on_equity(100, 200, 300), 2) == 20.0


def test_roe_negative_equity():
    assert return_on_equity(100, 200, -250) is None


def test_de_debt_free():
    assert debt_to_equity(0, 200, 300) == 0


def test_icr_zero_interest():
    value, label = interest_coverage_ratio(1000, 200, 0)
    assert value is None
    assert label == "Debt Free"


def test_de_high_leverage_flag_nonfinancial_true():
    assert high_leverage_flag(6.0, "Materials") is True


def test_de_high_leverage_flag_financials_exempt():
    assert high_leverage_flag(6.0, "Financials") is False


def test_cagr_turnaround():
    result, flag = cagr(-100, 200, 5)
    assert result is None
    assert flag == "TURNAROUND"


def test_cagr_decline_to_loss():
    result, flag = cagr(100, -50, 5)
    assert result is None
    assert flag == "DECLINE_TO_LOSS"


def test_cagr_normal():
    result, flag = cagr(100, 161.05, 5)
    assert round(result, 1) == pytest.approx(10.0, abs=0.5)


def test_cagr_zero_base():
    result, flag = cagr(0, 100, 5)
    assert result is None
    assert flag == "ZERO_BASE"


def test_cagr_both_negative():
    result, flag = cagr(-100, -50, 5)
    assert result is None
    assert flag == "BOTH_NEGATIVE"


def test_cfo_pat_ratio_high_quality():
    assert cfo_pat_ratio(1200, 1000) == pytest.approx(1.2)


def test_cfo_pat_ratio_zero_pat():
    assert cfo_pat_ratio(500, 0) is None
