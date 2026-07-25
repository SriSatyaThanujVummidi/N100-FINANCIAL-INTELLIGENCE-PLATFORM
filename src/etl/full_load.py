"""Day 5 — Full Data Load: all 12 files into nifty100.db.

Run order: companies -> sectors -> profitandloss -> balancesheet -> cashflow
-> analysis -> documents -> prosandcons -> stock_prices -> market_cap
-> financial_ratios -> peer_groups (parents before children, per FK design).

Writes output/load_audit.csv with: table, rows_in, rows_out, rejected,
timestamp, runtime_s.
"""

from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

# Allow running this file directly (python src/etl/full_load.py) — same
# sys.path trick validator.py already uses.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from etl.loader import load_all_core, load_all_supporting
from etl.normaliser import normalize_ticker, normalize_year
from etl.db import (
    DB_PATH,
    create_database,
    foreign_key_check,
    get_connection,
    insert_dataframe,
)

AUDIT_ROWS: list[dict] = []


def _normalize_ticker_column(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, int]:
    """Apply normalize_ticker to a column. Drops rows that fail to parse."""
    cleaned, keep = [], []
    for val in df[col]:
        try:
            cleaned.append(normalize_ticker(val))
            keep.append(True)
        except ValueError:
            cleaned.append(None)
            keep.append(False)
    df = df.copy()
    df[col] = cleaned
    keep_mask = pd.Series(keep, index=df.index)
    n_dropped = int((~keep_mask).sum())
    return df[keep_mask], n_dropped


def _normalize_year_column(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, int]:
    """Apply normalize_year. Drops unparseable rows AND TTM rows (not a fiscal year-end)."""
    cleaned, keep = [], []
    for val in df[col]:
        try:
            normalized = normalize_year(val)
        except ValueError:
            cleaned.append(None)
            keep.append(False)
            continue
        if normalized == "TTM":
            cleaned.append(None)
            keep.append(False)
            continue
        cleaned.append(normalized)
        keep.append(True)
    df = df.copy()
    df[col] = cleaned
    keep_mask = pd.Series(keep, index=df.index)
    n_dropped = int((~keep_mask).sum())
    return df[keep_mask], n_dropped


def _filter_fk_orphans(
    df: pd.DataFrame, col: str, valid_ids: set[str]
) -> tuple[pd.DataFrame, int]:
    """Drop rows whose company_id has no matching row in companies (expected — 8 known orphans)."""
    mask = df[col].isin(valid_ids)
    return df[mask], int((~mask).sum())


def _dedup_keep_last(df: pd.DataFrame, key_cols: list[str]) -> tuple[pd.DataFrame, int]:
    """Drop duplicate (composite key) row-blocks, keeping the last occurrence."""
    before = len(df)
    df = df.drop_duplicates(subset=key_cols, keep="last")
    return df, before - len(df)


def _filter_to_schema_columns(df: pd.DataFrame, conn, table_name: str) -> pd.DataFrame:
    """Drop any DataFrame columns that aren't in the actual SQLite table schema.

    Real source files sometimes carry extra columns the spec/schema doesn't
    define (e.g. a stray row-index 'id' in sectors.xlsx). to_sql() fails hard
    if it tries to insert into a column that doesn't exist, so we filter
    defensively here and log what got dropped, rather than crash table by
    table as we discover each one.
    """
    schema_cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table_name})")}
    extra = [c for c in df.columns if c not in schema_cols]
    if extra:
        print(f"  -> {table_name}: dropping columns not in schema: {extra}")
    return df[[c for c in df.columns if c in schema_cols]]


def fix_is_benchmark(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce is_benchmark to a clean 0/1 int regardless of source representation."""
    df = df.copy()
    df["is_benchmark"] = df["is_benchmark"].apply(
        lambda v: 1 if str(v).strip().lower() in ("1", "true", "yes", "y") else 0
    )
    return df


def _load_table(
    table_name: str,
    df: pd.DataFrame,
    conn,
    valid_ids: set[str] | None = None,
    ticker_col: str = "company_id",
    year_col: str | None = None,
    key_cols: list[str] | None = None,
    rename_map: dict[str, str] | None = None,
    extra_fix=None,
) -> pd.DataFrame:
    start = time.perf_counter()
    rows_in = len(df)
    rejected = 0

    if rename_map:
        df = df.rename(columns=rename_map)

    df, n = _normalize_ticker_column(df, ticker_col)
    rejected += n

    if valid_ids is not None:
        df, n = _filter_fk_orphans(df, ticker_col, valid_ids)
        rejected += n

    if year_col:
        df, n = _normalize_year_column(df, year_col)
        rejected += n

    if extra_fix:
        df = extra_fix(df)

    if key_cols:
        df, n = _dedup_keep_last(df, key_cols)
        rejected += n

    df = _filter_to_schema_columns(df, conn, table_name)

    rows_out = insert_dataframe(conn, table_name, df)
    runtime_s = round(time.perf_counter() - start, 3)

    AUDIT_ROWS.append(
        {
            "table": table_name,
            "rows_in": rows_in,
            "rows_out": rows_out,
            "rejected": rejected,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "runtime_s": runtime_s,
        }
    )
    print(
        f"[{table_name:16s}] in={rows_in:5d}  out={rows_out:5d}  rejected={rejected:4d}  ({runtime_s}s)"
    )
    return df


def main() -> None:
    """Main."""
    print("Loading raw Excel files...")
    core = load_all_core()
    supporting = load_all_supporting()

    # Always start from a clean database. Each table commits immediately on
    # success, so a run that fails partway through (e.g. on table 5) leaves
    # tables 1-4 permanently saved to disk. Re-running on top of that causes
    # spurious UNIQUE constraint errors that look like new bugs but aren't -
    # so we remove any existing db file ourselves rather than relying on a
    # manual delete step before every run.
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Removed existing {DB_PATH} for a clean run.\n")

    conn = get_connection()
    create_database(conn)

    # 1. companies — must load first; everything else FKs to it.
    companies_clean = _load_table(
        "companies",
        core["companies"],
        conn,
        ticker_col="id",
        key_cols=["id"],
    )
    valid_ids = set(companies_clean["id"])
    print(f"-> {len(valid_ids)} valid company ids after load.\n")

    # 2. sectors
    _load_table(
        "sectors",
        supporting["sectors"],
        conn,
        valid_ids=valid_ids,
        key_cols=["company_id"],
    )

    # 3. profitandloss
    _load_table(
        "profitandloss",
        core["profitandloss"],
        conn,
        valid_ids=valid_ids,
        year_col="year",
        key_cols=["company_id", "year"],
        rename_map={"id": "source_id"},
    )

    # 4. balancesheet
    _load_table(
        "balancesheet",
        core["balancesheet"],
        conn,
        valid_ids=valid_ids,
        year_col="year",
        key_cols=["company_id", "year"],
        rename_map={"id": "source_id"},
    )

    # 5. cashflow
    _load_table(
        "cashflow",
        core["cashflow"],
        conn,
        valid_ids=valid_ids,
        year_col="year",
        key_cols=["company_id", "year"],
        rename_map={"id": "source_id"},
    )

    # 6. analysis (partial coverage; multiple rows per company — one per
    # reporting period: 10yr, 5yr, 3yr, TTM — NOT 1:1, dedup by row id)
    _load_table(
        "analysis", core["analysis"], conn, valid_ids=valid_ids, key_cols=["id"]
    )

    # 7. documents
    _load_table(
        "documents",
        core["documents"],
        conn,
        valid_ids=valid_ids,
        key_cols=["company_id", "report_year"],
        rename_map={
            "id": "source_id",
            "Year": "report_year",
            "Annual_Report": "annual_report_url",
        },
    )

    # 8. prosandcons
    _load_table(
        "prosandcons", core["prosandcons"], conn, valid_ids=valid_ids, key_cols=["id"]
    )

    # 9. stock_prices
    _load_table(
        "stock_prices",
        supporting["stock_prices"],
        conn,
        valid_ids=valid_ids,
        key_cols=["company_id", "date"],
    )

    # 10. market_cap (year is a plain calendar int 2019-2024 — no normalize_year needed)
    _load_table(
        "market_cap",
        supporting["market_cap"],
        conn,
        valid_ids=valid_ids,
        key_cols=["company_id", "year"],
    )

    # 11. financial_ratios (pre-computed supplementary file)
    _load_table(
        "financial_ratios",
        supporting["financial_ratios"],
        conn,
        valid_ids=valid_ids,
        year_col="year",
        key_cols=["company_id", "year"],
    )

    # 12. peer_groups
    _load_table(
        "peer_groups",
        supporting["peer_groups"],
        conn,
        valid_ids=valid_ids,
        key_cols=["peer_group_name", "company_id"],
        extra_fix=fix_is_benchmark,
    )

    # ---- audit log ----
    out_dir = Path("output")
    out_dir.mkdir(exist_ok=True)
    audit_df = pd.DataFrame(AUDIT_ROWS)
    audit_df.to_csv(out_dir / "load_audit.csv", index=False)
    print(f"\nWrote {len(audit_df)} rows to output/load_audit.csv")

    # ---- FK integrity check ----
    fk_violations = foreign_key_check(conn)
    print(f"PRAGMA foreign_key_check violations: {len(fk_violations)}")
    if fk_violations:
        print(fk_violations)

    conn.close()


if __name__ == "__main__":
    main()
