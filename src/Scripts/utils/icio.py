"""ICIO-specific constants and helpers — Z-block extraction and graph construction."""

import numpy as np
import pandas as pd
import networkx as nx

# 50 sector codes used in the OECD ICIO tables
ICIO_50_CODES: list[str] = [
    "A01", "A02", "A03", "B05", "B06", "B07", "B08", "B09",
    "C10-C12", "C13-C15", "C16", "C17", "C18", "C19",
    "C20", "C21", "C22", "C23", "C24", "C25", "C26", "C27", "C28", "C29",
    "C30", "C31-C32", "C33", "D35", "E36", "E37-E39", "F", "G45", "G46",
    "G47", "H49", "H50", "H51", "H52", "H53", "I", "J58-J60", "J61",
    "J62-J63", "K64", "K65", "K66", "L68", "M69-M70", "M71", "M72",
    "M73-M74", "M75", "N", "O", "P", "Q", "R-S", "T",
]

# Z-block extraction
def extract_zblock(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Isolate the Z-block from a raw ICIO DataFrame – square intermediate-transactions matrix. """
    sector_codes_set = set(ICIO_50_CODES)

    intermediate_cols = [c for c in raw_df.columns if "_" in c and c.split("_", 1)[1] in sector_codes_set]
    intermediate_rows = [r for r in raw_df.index if "_" in str(r) and str(r).split("_", 1)[1] in sector_codes_set]
    z_block = raw_df.loc[intermediate_rows, intermediate_cols]

    return z_block


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_thresholded_graph(
    z_block: pd.DataFrame, percentile: int = 99
) -> tuple[nx.DiGraph, float]:
    """Build a thresholded directed graph from a Z-block DataFrame.

    Self-loops are removed before thresholding. Only edges above the given
    percentile of non-zero weights are retained.

    Parameters
    ----------
    z_block    : pd.DataFrame  – square intermediate-transactions matrix
    percentile : int           – threshold percentile (default 99)

    Returns
    -------
    G         : nx.DiGraph  – thresholded directed graph with 'weight' edge attribute
    threshold : float       – the computed weight threshold value
    """
    labels = z_block.index.tolist()
    Z = z_block.values.astype(np.float64)
    np.fill_diagonal(Z, 0.0)

    nonzero = Z[Z > 0]
    threshold = float(np.percentile(nonzero, percentile)) if len(nonzero) else 0.0

    Z_thresh = Z.copy()
    Z_thresh[Z_thresh < threshold] = 0.0
    src_idx, tgt_idx = np.where(Z_thresh > 0)

    G = nx.DiGraph()
    G.add_nodes_from(labels)
    G.add_weighted_edges_from(
        [(labels[s], labels[t], Z_thresh[s, t]) for s, t in zip(src_idx, tgt_idx)]
    )
    return G, threshold
