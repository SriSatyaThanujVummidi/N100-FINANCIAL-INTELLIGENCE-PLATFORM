"""Schema & data quality validator — implements DQ-01 through DQ-16.

Run directly to validate the 7 core files and write output/validation_failures.csv.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

# Allow running this file directly (python src/etl/validator.py) by putting
# the src/ directory on the import path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from etl.loader import load_all_core, load_all_supporting
from etl.normaliser import TICKER_CORRECTIONS, normalize_ticker, normalize_year

YEAR_FORMAT_RE = re.compile(r"^\d{4}-\d{2}$")


def _violation(rule_id, severity, table, company_id="", year="", field="", issue=""):
    return {
        "rule_id": rule_id,
        "severity": severity,
        "table": table,
        "company_id": company_id,
        "year": year,
        "field": field,
        "issue": issue,
    }


def normalize_table(
    df: pd.DataFrame,
    table_name: str,
    ticker_col: str = "company_id",
    year_col: str | None = "year",
):
    """Apply normalize_ticker / normalize_year to a table. Returns (clean_df, violations)."""
    df = df.copy()
    violations = []

    clean_tickers = []
    for val in df[ticker_col]:
        try:
            clean = normalize_ticker(val)
        except ValueError:
            clean_tickers.append(None)
            violations.append(
                _violation(
                    "DQ-08",
                    "CRITICAL",
                    table_name,
                    company_id=val,
                    issue=f"Unparseable / missing ticker: {val!r}",
                )
            )
            continue
        raw_upper = str(val).strip().upper()
        if raw_upper in TICKER_CORRECTIONS:
            violations.append(
                _violation(
                    "DQ-08",
                    "INFO",
                    table_name,
                    company_id=clean,
                    issue=f"Ticker corrected: {raw_upper!r} -> {clean!r} (known data entry typo)",
                )
            )
        clean_tickers.append(clean)
    df[ticker_col] = clean_tickers

    if year_col and year_col in df.columns:
        clean_years = []
        for i, val in enumerate(df[year_col]):
            cid = df[ticker_col].iloc[i]
            try:
                normalized = normalize_year(val)
            except ValueError:
                clean_years.append(None)
                violations.append(
                    _violation(
                        "DQ-07",
                        "CRITICAL",
                        table_name,
                        company_id=cid,
                        year=val,
                        issue=f"Unparseable year: {val!r}",
                    )
                )
                continue
            if normalized == "TTM":
                # TTM = trailing twelve months, not a discrete fiscal year-end.
                # Expected format, not a data error — drop from the annual
                # time series and log as INFO so it doesn't get mistaken for
                # a critical bug.
                clean_years.append(None)
                violations.append(
                    _violation(
                        "DQ-07",
                        "INFO",
                        table_name,
                        company_id=cid,
                        year=val,
                        issue="TTM row excluded from annual time series (not a fiscal year-end)",
                    )
                )
                continue
            clean_years.append(normalized)
        df[year_col] = clean_years

    df = df.dropna(subset=[ticker_col])
    if year_col and year_col in df.columns:
        df = df.dropna(subset=[year_col])
    return df, violations


# ---------------------------------------------------------------- DQ rules


def dq01_company_pk_uniqueness(companies_df):
    """Dq01 company pk uniqueness."""
    violations = []
    if len(companies_df) != companies_df["id"].nunique():
        dupes = companies_df[companies_df["id"].duplicated(keep=False)]["id"].unique()
        for d in dupes:
            violations.append(
                _violation(
                    "DQ-01",
                    "CRITICAL",
                    "companies",
                    company_id=d,
                    issue="Duplicate company id",
                )
            )
    return violations


def dq02_annual_pk_uniqueness(df, table_name):
    """Dq02 annual pk uniqueness."""
    violations = []
    dupes = df[df.duplicated(subset=["company_id", "year"], keep=False)]
    for _, row in dupes.iterrows():
        violations.append(
            _violation(
                "DQ-02",
                "CRITICAL",
                table_name,
                company_id=row["company_id"],
                year=row["year"],
                issue="Duplicate (company_id, year) pair",
            )
        )
    return violations


def dq03_fk_integrity(df, table_name, valid_ids):
    """Dq03 fk integrity."""
    violations = []
    orphans = df[~df["company_id"].isin(valid_ids)]
    for _, row in orphans.iterrows():
        violations.append(
            _violation(
                "DQ-03",
                "CRITICAL",
                table_name,
                company_id=row["company_id"],
                issue="company_id not found in companies table",
            )
        )
    return violations


def dq04_balance_sheet_balance(bs_df):
    """Dq04 balance sheet balance."""
    violations = []
    for _, row in bs_df.iterrows():
        ta, tl = row.get("total_assets"), row.get("total_liabilities")
        if pd.isna(ta) or ta == 0:
            continue
        if abs(ta - tl) / abs(ta) >= 0.01:
            violations.append(
                _violation(
                    "DQ-04",
                    "WARNING",
                    "balancesheet",
                    company_id=row["company_id"],
                    year=row["year"],
                    field="total_assets/total_liabilities",
                    issue=f"assets={ta}, liabilities={tl}",
                )
            )
    return violations


def dq05_opm_cross_check(pl_df):
    """Dq05 opm cross check."""
    violations = []
    for _, row in pl_df.iterrows():
        sales, opm, op_profit = (
            row.get("sales"),
            row.get("opm_percentage"),
            row.get("operating_profit"),
        )
        if pd.isna(sales) or sales == 0 or pd.isna(opm):
            continue
        computed = (op_profit / sales) * 100
        if abs(opm - computed) >= 1.0:
            violations.append(
                _violation(
                    "DQ-05",
                    "WARNING",
                    "profitandloss",
                    company_id=row["company_id"],
                    year=row["year"],
                    field="opm_percentage",
                    issue=f"source={opm}, computed={computed:.2f}",
                )
            )
    return violations


def dq06_positive_sales(pl_df, financial_ids):
    """Dq06 positive sales."""
    violations = []
    for _, row in pl_df.iterrows():
        if row["company_id"] in financial_ids:
            continue
        if pd.isna(row.get("sales")) or row["sales"] <= 0:
            violations.append(
                _violation(
                    "DQ-06",
                    "WARNING",
                    "profitandloss",
                    company_id=row["company_id"],
                    year=row["year"],
                    field="sales",
                    issue=f"sales={row.get('sales')}",
                )
            )
    return violations


def dq07_year_format(df, table_name):
    """Dq07 year format."""
    violations = []
    for _, row in df.iterrows():
        if not YEAR_FORMAT_RE.match(str(row["year"])):
            violations.append(
                _violation(
                    "DQ-07",
                    "CRITICAL",
                    table_name,
                    company_id=row["company_id"],
                    year=row["year"],
                    issue="Year not in YYYY-MM format",
                )
            )
    return violations


def dq08_ticker_format(df, table_name):
    """Dq08 ticker format."""
    violations = []
    for _, row in df.iterrows():
        cid = str(row["company_id"])
        if not (2 <= len(cid) <= 12):
            violations.append(
                _violation(
                    "DQ-08",
                    "CRITICAL",
                    table_name,
                    company_id=cid,
                    issue=f"Ticker length {len(cid)} out of range 2-12",
                )
            )
    return violations


def dq09_net_cash_check(cf_df):
    """Dq09 net cash check."""
    violations = []
    for _, row in cf_df.iterrows():
        cfo = row.get("operating_activity") or 0
        cfi = row.get("investing_activity") or 0
        cff = row.get("financing_activity") or 0
        ncf = row.get("net_cash_flow")
        if pd.isna(ncf):
            continue
        computed = cfo + cfi + cff
        if abs(ncf - computed) > 10:
            violations.append(
                _violation(
                    "DQ-09",
                    "WARNING",
                    "cashflow",
                    company_id=row["company_id"],
                    year=row["year"],
                    field="net_cash_flow",
                    issue=f"reported={ncf}, computed={computed}",
                )
            )
    return violations


def dq10_non_negative_fixed_assets(bs_df):
    """Dq10 non negative fixed assets."""
    violations = []
    for _, row in bs_df.iterrows():
        fa = row.get("fixed_assets")
        if pd.notna(fa) and fa < 0:
            violations.append(
                _violation(
                    "DQ-10",
                    "WARNING",
                    "balancesheet",
                    company_id=row["company_id"],
                    year=row["year"],
                    field="fixed_assets",
                    issue=f"fixed_assets={fa}",
                )
            )
    return violations


def dq11_tax_rate_range(pl_df):
    """Dq11 tax rate range."""
    violations = []
    for _, row in pl_df.iterrows():
        tax = row.get("tax_percentage")
        if pd.notna(tax) and not (0 <= tax <= 60):
            violations.append(
                _violation(
                    "DQ-11",
                    "WARNING",
                    "profitandloss",
                    company_id=row["company_id"],
                    year=row["year"],
                    field="tax_percentage",
                    issue=f"tax_percentage={tax}",
                )
            )
    return violations


def dq12_dividend_payout_cap(pl_df):
    """Dq12 dividend payout cap."""
    violations = []
    for _, row in pl_df.iterrows():
        dp = row.get("dividend_payout")
        if pd.notna(dp) and dp > 200:
            violations.append(
                _violation(
                    "DQ-12",
                    "WARNING",
                    "profitandloss",
                    company_id=row["company_id"],
                    year=row["year"],
                    field="dividend_payout",
                    issue=f"dividend_payout={dp}",
                )
            )
    return violations


def dq13_url_validity(documents_df, sample_size=None, timeout=5):
    """Checks Annual_Report URLs return HTTP 200. Slow for 1,585 rows — use sample_size while testing."""
    import requests

    violations = []
    rows = documents_df.head(sample_size) if sample_size else documents_df
    for _, row in rows.iterrows():
        url = row.get("Annual_Report")
        if pd.isna(url) or not str(url).startswith("http"):
            continue
        try:
            resp = requests.head(url, timeout=timeout, allow_redirects=True)
            if resp.status_code != 200:
                violations.append(
                    _violation(
                        "DQ-13",
                        "WARNING",
                        "documents",
                        company_id=row["company_id"],
                        year=row.get("Year"),
                        field="Annual_Report",
                        issue=f"HTTP {resp.status_code}",
                    )
                )
        except requests.RequestException as exc:
            violations.append(
                _violation(
                    "DQ-13",
                    "WARNING",
                    "documents",
                    company_id=row["company_id"],
                    year=row.get("Year"),
                    field="Annual_Report",
                    issue=str(exc),
                )
            )
    return violations


def dq14_eps_sign_consistency(pl_df):
    """Dq14 eps sign consistency."""
    violations = []
    for _, row in pl_df.iterrows():
        eps, net_profit = row.get("eps"), row.get("net_profit")
        if pd.notna(eps) and pd.notna(net_profit) and net_profit > 0 and eps <= 0:
            violations.append(
                _violation(
                    "DQ-14",
                    "WARNING",
                    "profitandloss",
                    company_id=row["company_id"],
                    year=row["year"],
                    field="eps",
                    issue=f"net_profit={net_profit}, eps={eps}",
                )
            )
    return violations


def dq15_strict_balance_info(bs_df):
    """Dq15 strict balance info."""
    violations = []
    for _, row in bs_df.iterrows():
        if row.get("total_assets") != row.get("total_liabilities"):
            violations.append(
                _violation(
                    "DQ-15",
                    "INFO",
                    "balancesheet",
                    company_id=row["company_id"],
                    year=row["year"],
                    issue="assets != liabilities (informational only)",
                )
            )
    return violations


def dq16_coverage_check(pl_df, bs_df, cf_df, min_years=5):
    """Dq16 coverage check."""
    violations = []
    pl_counts = pl_df.groupby("company_id")["year"].nunique()
    bs_counts = bs_df.groupby("company_id")["year"].nunique()
    cf_counts = cf_df.groupby("company_id")["year"].nunique()
    all_ids = set(pl_counts.index) | set(bs_counts.index) | set(cf_counts.index)
    for cid in all_ids:
        years = min(pl_counts.get(cid, 0), bs_counts.get(cid, 0), cf_counts.get(cid, 0))
        if years < min_years:
            violations.append(
                _violation(
                    "DQ-16",
                    "WARNING",
                    "coverage",
                    company_id=cid,
                    issue=f"Only {years} years of combined P&L/BS/CF history",
                )
            )
    return violations


# ---------------------------------------------------------------- runner


def run_all_checks(skip_url_check: bool = True) -> pd.DataFrame:
    """Run all checks."""
    core = load_all_core()
    supporting = load_all_supporting()

    companies_df = core["companies"].copy()
    companies_df["id"] = companies_df["id"].apply(
        lambda v: normalize_ticker(v) if pd.notna(v) else v
    )

    pl_df, v_pl = normalize_table(core["profitandloss"], "profitandloss")
    bs_df, v_bs = normalize_table(core["balancesheet"], "balancesheet")
    cf_df, v_cf = normalize_table(core["cashflow"], "cashflow")
    documents_df, v_docs = normalize_table(
        core["documents"], "documents", year_col=None
    )

    sectors_df = supporting["sectors"]
    financial_ids = set(
        sectors_df.loc[sectors_df["broad_sector"] == "Financials", "company_id"]
    )
    valid_ids = set(companies_df["id"])

    violations = []
    violations += v_pl + v_bs + v_cf + v_docs
    violations += dq01_company_pk_uniqueness(companies_df)
    violations += dq02_annual_pk_uniqueness(pl_df, "profitandloss")
    violations += dq02_annual_pk_uniqueness(bs_df, "balancesheet")
    violations += dq02_annual_pk_uniqueness(cf_df, "cashflow")
    violations += dq03_fk_integrity(pl_df, "profitandloss", valid_ids)
    violations += dq03_fk_integrity(bs_df, "balancesheet", valid_ids)
    violations += dq03_fk_integrity(cf_df, "cashflow", valid_ids)
    violations += dq04_balance_sheet_balance(bs_df)
    violations += dq05_opm_cross_check(pl_df)
    violations += dq06_positive_sales(pl_df, financial_ids)
    violations += dq07_year_format(pl_df, "profitandloss")
    violations += dq07_year_format(bs_df, "balancesheet")
    violations += dq07_year_format(cf_df, "cashflow")
    violations += dq08_ticker_format(pl_df, "profitandloss")
    violations += dq09_net_cash_check(cf_df)
    violations += dq10_non_negative_fixed_assets(bs_df)
    violations += dq11_tax_rate_range(pl_df)
    violations += dq12_dividend_payout_cap(pl_df)
    if not skip_url_check:
        violations += dq13_url_validity(documents_df, sample_size=50)
    violations += dq14_eps_sign_consistency(pl_df)
    violations += dq15_strict_balance_info(bs_df)
    violations += dq16_coverage_check(pl_df, bs_df, cf_df)

    return pd.DataFrame(violations)


if __name__ == "__main__":
    out_dir = Path("output")
    out_dir.mkdir(exist_ok=True)

    result = run_all_checks(skip_url_check=True)
    result.to_csv(out_dir / "validation_failures.csv", index=False)

    print(f"Wrote {len(result)} violations to output/validation_failures.csv")
    if len(result):
        print(result["severity"].value_counts())

    critical = result[result["severity"] == "CRITICAL"] if len(result) else result
    if len(critical):
        print(
            f"\nWARNING: {len(critical)} CRITICAL violations found - must resolve before Day 05:"
        )
        print(critical.to_string(index=False))
    else:
        print("\nZero CRITICAL violations.")
