"""Excel loaders for the 7 core and 5 supplementary Nifty 100 datasets."""

from __future__ import annotations
from pathlib import Path
import pandas as pd

CORE_FILES = [
    "companies.xlsx",
    "profitandloss.xlsx",
    "balancesheet.xlsx",
    "cashflow.xlsx",
    "analysis.xlsx",
    "documents.xlsx",
    "prosandcons.xlsx",
]

SUPPORTING_FILES = [
    "sectors.xlsx",
    "stock_prices.xlsx",
    "market_cap.xlsx",
    "financial_ratios.xlsx",
    "peer_groups.xlsx",
]


def load_core_file(path: str) -> pd.DataFrame:
    """Load one core dataset. Row 0 is metadata, row 1 is the real header."""
    df = pd.read_excel(path, header=1)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def load_supporting_file(path: str) -> pd.DataFrame:
    """Load one supplementary dataset. Header is the normal first row."""
    df = pd.read_excel(path, header=0)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def load_all_core(data_dir: str = "data/raw") -> dict[str, pd.DataFrame]:
    """Load all core."""
    base = Path(data_dir)
    return {Path(f).stem: load_core_file(str(base / f)) for f in CORE_FILES}


def load_all_supporting(data_dir: str = "data/supporting") -> dict[str, pd.DataFrame]:
    """Note: peer_groups.xlsx here is the normalised relational shape
    (id, peer_group_name, company_id, is_benchmark) — not comma-separated
    members as in the spec. Downstream code should target the real shape."""
    base = Path(data_dir)
    return {Path(f).stem: load_supporting_file(str(base / f)) for f in SUPPORTING_FILES}


if __name__ == "__main__":
    core = load_all_core()
    supporting = load_all_supporting()
    print("=== Core files ===")
    for name, df in core.items():
        print(f"{name}: {len(df)} rows, {len(df.columns)} cols -> {list(df.columns)}")
    print("\n=== Supporting files ===")
    for name, df in supporting.items():
        print(f"{name}: {len(df)} rows, {len(df.columns)} cols -> {list(df.columns)}")
