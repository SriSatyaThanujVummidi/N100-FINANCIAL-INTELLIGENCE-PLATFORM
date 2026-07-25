import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.reports.sector_report import compute_medians, is_implausible_pct, fmt


def test_compute_medians_basic():
    companies = [
        {
            "roe": 10,
            "roce": None,
            "de": None,
            "opm": None,
            "revenue_cagr_5yr": None,
            "npm": None,
            "fcf": None,
            "eps_cagr_5yr": None,
        },
        {
            "roe": 20,
            "roce": None,
            "de": None,
            "opm": None,
            "revenue_cagr_5yr": None,
            "npm": None,
            "fcf": None,
            "eps_cagr_5yr": None,
        },
        {
            "roe": 30,
            "roce": None,
            "de": None,
            "opm": None,
            "revenue_cagr_5yr": None,
            "npm": None,
            "fcf": None,
            "eps_cagr_5yr": None,
        },
    ]
    medians = compute_medians(companies)
    assert medians["roe"] == 20


def test_compute_medians_all_none_returns_none():
    companies = [
        {
            "roe": None,
            "roce": None,
            "de": None,
            "opm": None,
            "revenue_cagr_5yr": None,
            "npm": None,
            "fcf": None,
            "eps_cagr_5yr": None,
        }
    ]
    medians = compute_medians(companies)
    assert medians["roe"] is None


def test_is_implausible_pct():
    assert is_implausible_pct(600.0) is True
    assert is_implausible_pct(20.0) is False


def test_fmt_none():
    assert fmt(None) == "N/A"


def test_fmt_percent():
    assert fmt(15.567) == "15.6%"


def test_fmt_ratio():
    assert fmt(0.5, suffix="x") == "0.50x"


def test_fmt_crore():
    assert fmt(1234.5, suffix="Cr", precision=0) == "Rs 1,234 Cr"
