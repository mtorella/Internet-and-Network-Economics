from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd


def style_ax(ax: plt.Axes) -> None:
    PANEL = "#1a1d27"
    GRID = "#333344"
    AXIS = "#888899"
    ax.set_facecolor(PANEL)
    ax.tick_params(colors=AXIS, labelsize=9)
    ax.xaxis.label.set_color(AXIS)
    ax.yaxis.label.set_color(AXIS)
    for spine in ax.spines.values():
        spine.set_color(GRID)
    ax.grid(True, color=GRID, alpha=0.5, linewidth=0.5)


def minmax(s: pd.Series) -> pd.Series:
    s = s.astype(float)
    smin = s.min()
    smax = s.max()
    if pd.isna(smin) or pd.isna(smax) or np.isclose(smax, smin):
        return pd.Series(np.zeros(len(s), dtype=float), index=s.index)
    return (s - smin) / (smax - smin)


def sector_type_color(icio_sector: str) -> str:
    if icio_sector in {"J58T60", "J61", "J62_63", "C26"}:
        return "#4FC3F7"  # digital/ICT
    if icio_sector.startswith("C"):
        return "#FFB74D"  # manufacturing
    if icio_sector in {"K", "M", "N", "L"}:
        return "#81C784"  # business services
    if icio_sector in {"G", "H49", "H50", "H51", "H52", "H53", "I"}:
        return "#F48FB1"  # trade transport
    if icio_sector in {"D", "E", "F"}:
        return "#CE93D8"  # utilities construction
    return "#90A4AE"


def classify_bottleneck(
    df: pd.DataFrame,
    digital_col: str,
    pr_quantile: float = 0.60,
    dig_quantile: float = 0.40,
) -> pd.Series:
    """Classify sectors as double bottlenecks based on centrality and digitalisation.

    A sector is a double bottleneck if it is simultaneously structurally central
    in the global supply network and digitally lagging relative to other Italian
    sectors. Both thresholds are computed only over sectors that have a valid
    (non-null) value for the chosen digitalisation measure, so the classification
    set is self-consistent.

    Default thresholds:
        - PageRank >= 60th percentile  →  structurally central
        - Digitalisation <= 40th percentile  →  digitally lagging

    The dig_quantile can be tightened (e.g. 0.30) for measures that tend to
    produce more borderline flags, such as ICT share, which can classify
    sectors with moderate digital intensity as lagging purely due to low
    capital stock.

    Parameters
    ----------
    df           : DataFrame containing at least "pagerank" and `digital_col`
    digital_col  : column name of the normalised digitalisation measure
                   (e.g. "dig_intensity_norm" or "ict_share_norm")
    pr_quantile  : PageRank percentile threshold for centrality (default 0.60)
    dig_quantile : Digitalisation percentile threshold for lagging (default 0.40)

    Returns
    -------
    Boolean Series — True where the sector is flagged as a double bottleneck.
    """
    valid = df[digital_col].notna()
    pr_cut = df.loc[valid, "pagerank"].quantile(pr_quantile)
    dig_cut = df.loc[valid, digital_col].quantile(dig_quantile)
    return (df["pagerank"] >= pr_cut) & (df[digital_col] <= dig_cut)


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


def draw_arc(
    ax: plt.Axes,
    p0: tuple[float, float],
    p1: tuple[float, float],
    color: str,
    alpha: float,
    lw: float,
) -> None:
    x0, y0 = p0
    x1, y1 = p1
    bulge = 0.55 * abs(x1 - x0)
    cx = (x0 + x1) / 2 + (bulge if x1 > x0 else -bulge)
    cy = (y0 + y1) / 2
    t = np.linspace(0, 1, 80)
    bx = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t ** 2 * x1
    by = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t ** 2 * y1
    ax.plot(bx, by, color=color, alpha=alpha, lw=lw, solid_capstyle="round", zorder=1)


def foreign_positions(
    country_list: list[str],
    x_base: float,
    top_edges: list[tuple[str, str, float]],
    nodes,
    y_max: float = 1.0,
    y_min: float = -1.0,
) -> dict[str, tuple[float, float]]:
    pos: dict[str, tuple[float, float]] = {}
    if not country_list:
        return pos
    band = (y_max - y_min) / len(country_list)
    for ci, country in enumerate(country_list):
        country_nodes = sorted(
            [
                n
                for n in nodes
                if n.startswith(f"{country}_")
                and any(n in (u, v) for u, v, _ in top_edges)
            ]
        )
        if not country_nodes:
            continue
        y_top = y_max - ci * band
        y_bot = y_top - band * 0.85
        ys = np.linspace(y_top, y_bot, len(country_nodes))
        for node, y in zip(country_nodes, ys):
            pos[node] = (x_base, float(y))
    return pos


def country_label_y(pos_dict: dict[str, tuple[float, float]], country: str) -> float:
    ys = [pos_dict[n][1] for n in pos_dict if n.startswith(f"{country}_")]
    return float(np.mean(ys)) if ys else 0.0


# ---------------------------------------------------------------------------
# Network construction
# ---------------------------------------------------------------------------

def build_coefficient_graph(z_block: pd.DataFrame, coeff_threshold: float = 0.01) -> nx.DiGraph:
    """Build a directed graph from the Leontief technical coefficient matrix.

    Normalises each column of Z by its sum (a_ij = z_ij / sum_i z_ij),
    zeros the diagonal, and retains edges where a_ij >= coeff_threshold.
    Using coefficients instead of raw flows removes size bias: a sector
    scores high only if it supplies a meaningful *share* of others' inputs.
    """
    labels = z_block.index.astype(str).tolist()
    Z = z_block.to_numpy(dtype=np.float64)
    np.fill_diagonal(Z, 0.0)

    col_sums = Z.sum(axis=0)
    col_sums[col_sums == 0] = 1.0
    A = Z / col_sums[np.newaxis, :]

    src_idx, tgt_idx = np.where(A >= coeff_threshold)
    weights = A[src_idx, tgt_idx]

    G = nx.DiGraph()
    G.add_nodes_from(labels)
    G.add_weighted_edges_from(
        (labels[s], labels[t], float(w)) for s, t, w in zip(src_idx, tgt_idx, weights)
    )
    return G


# ---------------------------------------------------------------------------
# Digitalisation data loading
# ---------------------------------------------------------------------------

def preprocess_digitalisation(
    year: int,
    data_proc: Path,
    nace_to_icio: dict,
) -> pd.DataFrame:
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
    if not growth_path.exists() or not intang_path.exists():
        return pd.DataFrame()

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
    df_composite["ict_share_norm"]     = minmax(df_composite["ict_share"])
    return df_composite


# ---------------------------------------------------------------------------
# Typology classification
# ---------------------------------------------------------------------------

def assign_typology(df: pd.DataFrame) -> pd.Series:
    """Assign a 2×2 digitalisation typology using median splits.

    Combines both digital measures into four categories:
        Digital leader       — above median on both investment and stock
        In transition        — high investment, low stock (catching up)
        Past adopter         — low investment, high stock (coasting)
        Structurally lagging — below median on both (worst case)
    """
    valid = df["dig_intensity_norm"].notna() & df["ict_share_norm"].notna()
    dig_med = df.loc[valid, "dig_intensity_norm"].median()
    ict_med = df.loc[valid, "ict_share_norm"].median()

    high_dig = df["dig_intensity_norm"] >= dig_med
    high_ict = df["ict_share_norm"] >= ict_med

    typology = pd.Series("Unknown", index=df.index)
    typology[high_dig  & high_ict ] = "Digital leader"
    typology[high_dig  & ~high_ict] = "In transition"
    typology[~high_dig & high_ict ] = "Past adopter"
    typology[~high_dig & ~high_ict] = "Structurally lagging"
    return typology
