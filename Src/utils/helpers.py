from __future__ import annotations
from pathlib import Path
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

from utils.constants import ICIO_SECTOR_CODES

def minmax(s: pd.Series) -> pd.Series:
    lo, hi = s.min(), s.max()
    return (s - lo) / (hi - lo) if hi > lo else pd.Series(0.0, index=s.index)

def extract_zblock(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Isolate the Z-block from a raw ICIO DataFrame — square intermediate-transactions matrix."""
    intermediate_cols = [c for c in raw_df.columns if "_" in c and c.split("_", 1)[1] in ICIO_SECTOR_CODES]
    intermediate_rows = [r for r in raw_df.index if "_" in str(r) and str(r).split("_", 1)[1] in ICIO_SECTOR_CODES]
    return raw_df.loc[intermediate_rows, intermediate_cols]

def build_coefficient_graph(z_block: pd.DataFrame, coeff_threshold: float = 0.01) -> nx.DiGraph:
    """Build a directed graph from the Leontief technical coefficient matrix"""
    # Retrieve sector labels and convert Z-block to numeric matrix
    labels = z_block.index.astype(str).tolist()
    # Convert Z-block to numeric matrix, ensuring any non-numeric entries are treated as zeros
    Z = z_block.to_numpy(dtype=np.float64)
    np.fill_diagonal(Z, 0.0)

    # Normalize columns to get technical coefficients, handling zero-sum columns
    col_sums = Z.sum(axis=0)
    col_sums[col_sums == 0] = 1.0
    A = Z / col_sums[np.newaxis, :]

    # Create edges for coefficients above the threshold
    src_idx, tgt_idx = np.where(A >= coeff_threshold)
    weights = A[src_idx, tgt_idx]

    # Build directed graph with weighted edges
    G = nx.DiGraph()
    G.add_nodes_from(labels)
    G.add_weighted_edges_from((labels[s], labels[t], float(w)) for s, t, w in zip(src_idx, tgt_idx, weights))
    return G

def load_zblock_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)

    # Handle cases where the CSV may include a separate first index column.
    first_col = str(df.columns[0])
    if first_col.startswith("Unnamed:") and df.shape[1] == df.shape[0] + 1:
        idx = df.iloc[:, 0].astype(str)
        df = df.iloc[:, 1:]
        df.index = idx
    elif df.shape[0] == df.shape[1]:
        # In this dataset, row labels were not saved separately; columns and rows share order.
        df.index = df.columns
    else:
        raise ValueError(
            f"Unexpected Z-block shape/format: {df.shape}. Cannot infer row labels safely."
        )

    return df.apply(pd.to_numeric, errors="coerce").fillna(0.0)

def preprocess_digitalisation(year: int, data_proc: Path, nace_to_icio: dict) -> pd.DataFrame:
    """Load and crosswalk both digitalisation measures for Italy for a given year.

    Applies the NACE→ICIO crosswalk to EUKLEMS growth accounts (ICT share)
    and Intan-Invest intangibles (digital intensity = software+R&D / VA).
    Tracks whether each ICIO code's ICT value comes from a direct NACE match
    or an aggregate mapping (ict_share_source column); aggregate-source
    sectors are less reliable for Variant B classification.
    Returns an empty DataFrame if input files are missing.
    """
    growth_path = data_proc / f"growth_accounts_{year}_wide.csv"
    intang_path = data_proc / f"intangibles_analytical_{year}.csv"

    # --- ICT share (EUKLEMS) ---
    growth_df = pd.read_csv(growth_path, low_memory=False)
    growth_it = growth_df[growth_df["geo_code"] == "IT"].copy()
    growth_it["icio_code"] = growth_it["nace_r2_code"].map(nace_to_icio)
    growth_it = growth_it.explode("icio_code").dropna(subset=["icio_code", "ict_share"])
    growth_it["is_direct"] = growth_it["nace_r2_code"] == growth_it["icio_code"]
    ict_by_sector = growth_it.groupby("icio_code", as_index=False).agg(
        ict_share=("ict_share", "mean"),
        ict_share_source=("is_direct", lambda x: "direct" if x.any() else "aggregate"),
    )

    # --- Digital intensity (Intan-Invest) ---
    intang_df = pd.read_csv(intang_path, low_memory=False)
    intang_it = intang_df[intang_df["geo_code"] == "IT"].copy()
    intang_it["dig_intensity"] = (
        intang_it["I_Soft_DB"].fillna(0.0) + intang_it["I_RD"].fillna(0.0)
    ) / intang_it["VA_CP"].replace(0, np.nan)
    intang_it["icio_code"] = intang_it["nace_r2_code"].map(nace_to_icio)
    intang_it = intang_it.explode("icio_code").dropna(subset=["icio_code", "dig_intensity"])
    dig_by_sector = intang_it.groupby("icio_code", as_index=False)["dig_intensity"].mean()

    df_composite = ict_by_sector.merge(dig_by_sector, on="icio_code", how="outer")
    df_composite["dig_intensity_norm"] = minmax(df_composite["dig_intensity"])
    df_composite["ict_share_norm"] = minmax(df_composite["ict_share"])
    return df_composite