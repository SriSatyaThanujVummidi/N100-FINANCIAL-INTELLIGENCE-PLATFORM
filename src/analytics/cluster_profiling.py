"""
Day 37 -- Cluster Profiling & Naming (Sprint 6, Module 10)

Reuses Day 36's build_feature_table() (same imputation/masking, same random_state=42 KMeans
fit) so the 5 feature values line up exactly with output/cluster_labels.csv's cluster
assignments. Profiles each cluster (mean/median of the 5 input features + sector composition +
most-representative companies), proposes descriptive names based on the real comparative
profile, and overwrites cluster_labels.csv's placeholder Cluster_0..4 names with the proposed
ones -- FLAGGED FOR TEAM LEAD REVIEW per spec's explicit instruction, not treated as final.
"""

import logging
import sqlite3
from pathlib import Path

import pandas as pd

from src.analytics.clustering import (
    get_connection,
    build_feature_table,
    run_kmeans,
    FEATURE_COLS,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("output")


def load_clustered_data(conn: sqlite3.Connection) -> pd.DataFrame:
    """Rebuilds the exact Day 36 feature table + KMeans fit (deterministic: random_state=42),
    rather than re-reading cluster_labels.csv alone, since we need the raw feature VALUES
    (not just the assignment) to compute per-cluster mean/median."""
    df = build_feature_table(conn)
    df = run_kmeans(df)
    return df


def profile_clusters(df: pd.DataFrame) -> pd.DataFrame:
    """Profile clusters."""
    return df.groupby("cluster_id")[FEATURE_COLS].agg(["mean", "median"]).round(2)


def sector_composition(df: pd.DataFrame, top_n: int = 3) -> dict:
    """Top sectors by count within each cluster -- naming evidence, not a hard rule."""
    comp = {}
    for cluster_id, grp in df.groupby("cluster_id"):
        comp[cluster_id] = grp["broad_sector"].value_counts().head(top_n).to_dict()
    return comp


def representative_companies(df: pd.DataFrame, n: int = 5) -> dict:
    """Companies closest to their cluster centroid -- most 'typical' members, useful for
    eyeballing whether a proposed name actually fits real companies."""
    reps = {}
    for cluster_id, grp in df.groupby("cluster_id"):
        reps[cluster_id] = (
            grp.sort_values("distance_from_centroid").head(n)["company_id"].tolist()
        )
    return reps


def propose_cluster_names(profile: pd.DataFrame) -> dict:
    """
    Rule-based naming from the REAL comparative profile across the 5 clusters (ranked relative
    to each other -- 'high ROE' only means something relative to this dataset's own
    distribution). Priority order, each cluster claimed once:

      1. Highest mean ROE                          -> High-Quality Compounders
      2. Highest mean D/E among remaining           -> Value Cyclicals (leverage-driven)
      3. Highest mean Revenue CAGR among remaining  -> Emerging Growth (fast-growing,
         typically still cash-burning -- pairs naturally with weak/negative FCF CAGR)
      4. Lowest mean Revenue CAGR among remaining   -> Defensive / Steady Compounders
      5. Whatever's left -- named from ITS OWN profile, not forced into spec's "Distressed
         or Turnaround" label unless it actually looks distressed (low/negative ROE,
         sharply negative FCF CAGR). If it doesn't, it's flagged explicitly rather than
         mislabeled.

    FLAGGED FOR TEAM LEAD: proposal based on aggregate stats only -- cross-check against
    representative_companies() / sector_composition() output before finalising.
    """
    means = profile.xs("mean", axis=1, level=1)
    remaining = set(means.index)
    names = {}

    hqc = (
        means.loc[list(remaining)]
        .sort_values(by="return_on_equity_pct", ascending=False)
        .index[0]
    )
    names[hqc] = "High-Quality Compounders"
    remaining.discard(hqc)

    vc = (
        means.loc[list(remaining)]
        .sort_values(by="debt_to_equity", ascending=False)
        .index[0]
    )
    names[vc] = "Value Cyclicals"
    remaining.discard(vc)

    eg = (
        means.loc[list(remaining)]
        .sort_values(by="revenue_cagr_5yr", ascending=False)
        .index[0]
    )
    names[eg] = "Emerging Growth"
    remaining.discard(eg)

    dd = (
        means.loc[list(remaining)]
        .sort_values(by="revenue_cagr_5yr", ascending=True)
        .index[0]
    )
    names[dd] = "Defensive / Steady Compounders"
    remaining.discard(dd)

    for last in remaining:
        row = means.loc[last]
        if row["return_on_equity_pct"] < 5 or row["fcf_cagr_5yr"] < -20:
            names[last] = "Distressed or Turnaround"
        else:
            names[last] = (
                "Asset-Light Quality (does not fit spec's 5 example archetypes -- flag for team lead)"
            )

    return names


def main() -> None:
    """Main."""
    conn = get_connection()
    try:
        df = load_clustered_data(conn)
    finally:
        conn.close()

    profile = profile_clusters(df)
    print("\nCluster feature profile (mean / median):")
    print(profile)

    comp = sector_composition(df)
    print("\nTop sectors per cluster (naming evidence):")
    for cid, sectors in comp.items():
        print(f"  Cluster {cid}: {sectors}")

    reps = representative_companies(df)
    print("\nMost representative companies per cluster (closest to centroid):")
    for cid, companies in reps.items():
        print(f"  Cluster {cid}: {companies}")

    proposed_names = propose_cluster_names(profile)
    print(
        "\nProposed cluster names (PROVISIONAL -- review against composition above before sign-off):"
    )
    for cid, name in sorted(proposed_names.items()):
        print(f"  Cluster {cid}: {name}")

    df["cluster_name"] = df["cluster_id"].map(proposed_names)
    out_cols = ["company_id", "cluster_id", "cluster_name", "distance_from_centroid"]
    df[out_cols].sort_values("company_id").to_csv(
        OUTPUT_DIR / "cluster_labels.csv", index=False
    )
    logger.info(
        "output/cluster_labels.csv updated with proposed names -- %d rows", len(df)
    )

    profile_out = profile.copy()
    profile_out.columns = ["_".join(col) for col in profile_out.columns]
    profile_out["cluster_name"] = profile_out.index.map(proposed_names)
    profile_out["n_companies"] = df.groupby("cluster_id").size()
    profile_out.to_csv(OUTPUT_DIR / "cluster_profile_summary.csv")
    logger.info(
        "output/cluster_profile_summary.csv written (extra -- supporting evidence for the naming above)"
    )


if __name__ == "__main__":
    main()
