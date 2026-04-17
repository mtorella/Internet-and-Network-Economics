from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import ListedColormap
from utils.helpers import classify_bottleneck, load_zblock_csv, minmax, sector_type_color, style_ax
from utils.constants import NACE_TO_ICIO, SECTOR_LABELS

# Input / Output paths
ROOT = Path(__file__).resolve().parent.parent
DATA_PREP = ROOT / "data" / "prepared"
DATA_PROC = ROOT / "data" / "processed"
OUT_FIG = ROOT / "outputs" / "figures"
OUT_TBL = ROOT / "outputs" / "tables"

OUT_FIG.mkdir(parents=True, exist_ok=True)
OUT_TBL.mkdir(parents=True, exist_ok=True)

YEARS = list(range(2016, 2022))

# Minimum Leontief technical coefficient to include an edge.
# a_ij >= 0.01 means sector i provides at least 1% of j's total intermediate inputs.
# This is more meaningful than a raw USD threshold because it captures structural
# dependency regardless of sector size.
COEFF_THRESHOLD = 0.01


# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------

def build_coefficient_graph(z_block: pd.DataFrame, coeff_threshold: float = COEFF_THRESHOLD) -> nx.DiGraph:
    """Build a directed graph from the Leontief technical coefficient matrix.

    A = Z / x  where x_j = sum_i(z_ij)  (total intermediate inputs received by j).
    Edge i→j is retained if a_ij >= coeff_threshold, meaning sector i supplies at
    least `coeff_threshold` share of j's intermediate input bundle.

    Using coefficients instead of raw USD flows removes the size bias: a sector
    that provides a large share of inputs to many others scores high regardless
    of the absolute dollar value of its transactions.

    Self-loops are zeroed before normalisation.
    Columns with zero sum (inactive sectors) are left as zero rather than divided.
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


def preprocess_digitalisation(year: int) -> pd.DataFrame:
    """Load and merge ICT share + digital intensity for Italy for a given year.

    Changes vs analysis.py:
    - Tracks whether each ICIO code's ICT share comes from a direct NACE match
      or an aggregate mapping (ict_share_source column).
    - Aggregate-source sectors are kept in the table but flagged so that
      Variant B classification can exclude them.

    Returns a DataFrame with columns:
        icio_code, dig_intensity, dig_intensity_norm,
        ict_share, ict_share_norm, ict_share_source
    Returns an empty DataFrame if data is unavailable for the year.
    """
    growth_path = DATA_PROC / f"growth_accounts_{year}_wide.csv"
    intang_path = DATA_PROC / f"intangibles_analytical_{year}.csv"
    if not growth_path.exists() or not intang_path.exists():
        return pd.DataFrame()

    # ICT share (EUKLEMS growth accounts)
    growth_df = pd.read_csv(growth_path, low_memory=False)
    growth_it = growth_df[growth_df["geo_code"] == "IT"].copy()
    growth_it["icio_code"] = growth_it["nace_r2_code"].map(NACE_TO_ICIO)
    growth_it = growth_it.explode("icio_code")
    growth_it = growth_it.dropna(subset=["icio_code", "ict_share"])
    growth_it["is_direct"] = growth_it["nace_r2_code"] == growth_it["icio_code"]
    ict_by_sector = growth_it.groupby("icio_code", as_index=False).agg(
        ict_share=("ict_share", "mean"),
        ict_share_source=("is_direct", lambda x: "direct" if x.any() else "aggregate"),
    )

    # Digital intensity (Intan-Invest)
    intang_df = pd.read_csv(intang_path, low_memory=False)
    intang_it = intang_df[intang_df["geo_code"] == "IT"].copy()
    intang_it["dig_intensity"] = (
        intang_it["I_Soft_DB"].fillna(0.0) + intang_it["I_RD"].fillna(0.0)
    ) / intang_it["VA_CP"].replace(0, np.nan)
    intang_it["icio_code"] = intang_it["nace_r2_code"].map(NACE_TO_ICIO)
    intang_it = intang_it.explode("icio_code")
    intang_it = intang_it.dropna(subset=["icio_code", "dig_intensity"])
    dig_by_sector = intang_it.groupby("icio_code", as_index=False)["dig_intensity"].mean()

    df_composite = ict_by_sector.merge(dig_by_sector, on="icio_code", how="outer")
    df_composite["dig_intensity_norm"] = minmax(df_composite["dig_intensity"])
    df_composite["ict_share_norm"] = minmax(df_composite["ict_share"])
    return df_composite


def assign_typology(df: pd.DataFrame) -> pd.Series:
    """Assign a 2×2 digitalisation typology using median splits.

    The two dimensions are:
        - dig_intensity_norm: investment flow (software + R&D / VA, Intan-Invest)
        - ict_share_norm:     embedded capital stock (ICT / total capital, EUKLEMS)

    Using the median rather than an arbitrary percentile gives a symmetric
    partition: each category contains roughly a quarter of the sectors.

    Categories:
        Digital leader       — high investment AND high stock
        In transition        — high investment, low stock  (catching up)
        Past adopter         — low investment, high stock  (coasting on legacy capital)
        Structurally lagging — low investment AND low stock (worst case)
    """
    # Only valid (non-null) observations inform the medians
    valid = df["dig_intensity_norm"].notna() & df["ict_share_norm"].notna()
    dig_med = df.loc[valid, "dig_intensity_norm"].median()
    ict_med = df.loc[valid, "ict_share_norm"].median()

    high_dig = df["dig_intensity_norm"] >= dig_med
    high_ict = df["ict_share_norm"] >= ict_med

    typology = pd.Series("Unknown", index=df.index)
    # Restrict quadrant assignment to sectors with both digital metrics available.
    # Otherwise missing values would be coerced into the "Structurally lagging" cell.
    typology[valid & high_dig & high_ict] = "Digital leader"
    typology[valid & high_dig & ~high_ict] = "In transition"
    typology[valid & ~high_dig & high_ict] = "Past adopter"
    typology[valid & ~high_dig & ~high_ict] = "Structurally lagging"
    return typology


# -----------------------------------------------------------------------------
# Multi-year panel loop
# -----------------------------------------------------------------------------
print("=" * 80)
print("ANALYSIS 2 — MULTI-YEAR PANEL (2016–2021)")
print("Technical coefficients · 2×2 typology · Aggregate-source filtering")
print("=" * 80)

panel_records = []

for year in YEARS:
    icio_path = DATA_PREP / f"icio_zblock_{year}.csv"
    if not icio_path.exists():
        print(f"\n  {year}: z-block not found — skipped")
        continue

    print(f"\n--- {year} ---")

    # Part 1 — Technical coefficient graph and centrality
    z_block = load_zblock_csv(icio_path)
    G = build_coefficient_graph(z_block)
    print(f"  Coefficient graph: nodes={G.number_of_nodes():,}, edges={G.number_of_edges():,}")

    pagerank = nx.pagerank(G, weight="weight")
    betweenness = nx.betweenness_centrality(G, k=300, normalized=True, weight="weight", seed=42)
    in_strength = dict(G.in_degree(weight="weight"))
    out_strength = dict(G.out_degree(weight="weight"))

    centrality_df = pd.DataFrame({
        "node": list(G.nodes),
        "country": [n.split("_", 1)[0] for n in G.nodes],
        "sector": [n.split("_", 1)[1] for n in G.nodes],
        "pagerank": [pagerank[n] for n in G.nodes],
        "betweenness": [betweenness[n] for n in G.nodes],
        "in_strength": [in_strength[n] for n in G.nodes],
        "out_strength": [out_strength[n] for n in G.nodes],
    })
    centrality_df["total_strength"] = centrality_df["in_strength"] + centrality_df["out_strength"]
    ita_centrality = centrality_df[centrality_df["country"] == "ITA"].copy().reset_index(drop=True)

    # Part 2 — Digitalisation metrics
    df_composite = preprocess_digitalisation(year)
    if df_composite.empty:
        print(f"  Digitalisation data unavailable — skipped")
        continue

    # Part 3 — Merge, typology, classify
    analysis_df = ita_centrality.merge(df_composite, left_on="sector", right_on="icio_code", how="inner")
    analysis_df["sector_label"] = analysis_df["sector"].map(SECTOR_LABELS).fillna(analysis_df["sector"])
    analysis_df["typology"] = assign_typology(analysis_df)

    # Variant A: digital intensity, all matched sectors, 40th percentile
    analysis_df["variant_a"] = classify_bottleneck(analysis_df, "dig_intensity_norm")

    # Variant B: ICT share, direct-source sectors only, 30th percentile.
    # Sectors whose ICT value comes only from an aggregate NACE mapping are excluded
    # because their score is shared with dissimilar sub-sectors and cannot reliably
    # represent the specific ICIO sector's digital capital intensity.
    analysis_df["variant_b"] = False
    direct_idx = analysis_df[analysis_df["ict_share_source"] == "direct"].index
    if len(direct_idx) > 0:
        vb = classify_bottleneck(
            analysis_df.loc[direct_idx].copy(), "ict_share_norm", dig_quantile=0.30
        )
        analysis_df.loc[direct_idx, "variant_b"] = vb.values

    analysis_df["bottleneck"] = analysis_df["variant_a"] & analysis_df["variant_b"]
    analysis_df["year"] = year

    n_a = analysis_df["variant_a"].sum()
    n_b = analysis_df["variant_b"].sum()
    n_bn = analysis_df["bottleneck"].sum()
    print(f"  IT sectors analysed: {len(analysis_df)} | Variant A: {n_a} | Variant B: {n_b} | Bottlenecks: {n_bn}")
    print(f"  Typology: { analysis_df['typology'].value_counts().to_dict()}")
    panel_records.append(analysis_df)

print("\n" + "=" * 80)
if not panel_records:
    raise RuntimeError(
        "No yearly records were produced. Check that required files exist in data/prepared and data/processed."
    )
panel_df = pd.concat(panel_records, ignore_index=True)
panel_df.to_csv(OUT_TBL / "panel_bottleneck_2016_2021.csv", index=False)
print(f"Saved {OUT_TBL / 'panel_bottleneck_2016_2021.csv'}")


# -----------------------------------------------------------------------------
# Figure A — Multi-year bottleneck heatmap
# Rows = Italian sectors sorted by total bottleneck count across years.
# Columns = years. Cell encoding:
#   3 (dark red)  = both variants flagged (robust bottleneck)
#   2 (orange)    = Variant A only
#   1 (steel)     = Variant B only
#   0 (dark)      = neither
# This shows which sectors are persistently vulnerable and whether the pattern
# is stable or shifting over time.
# -----------------------------------------------------------------------------
print("\nPART 4 — Visualisations")
print("-" * 50)

def _encode(row):
    a, b = row["variant_a"], row["variant_b"]
    if a and b:
        return 3
    if a:
        return 2
    if b:
        return 1
    return 0

panel_df["status"] = panel_df.apply(_encode, axis=1)

pivot = panel_df.pivot_table(index="sector_label", columns="year", values="status", aggfunc="first")
pivot = pivot.fillna(0).astype(int)
sort_key = (pivot == 3).sum(axis=1) * 10 + (pivot >= 1).sum(axis=1)
pivot = pivot.loc[sort_key.sort_values(ascending=False).index]

cmap = ListedColormap(["#1e1f29", "#5C6BC0", "#FFA726", "#C62828"])
fig_a, ax_a = plt.subplots(figsize=(10, 13), facecolor="#1e1f29")
ax_a.set_facecolor("#1e1f29")

im = ax_a.imshow(pivot.values, aspect="auto", cmap=cmap, vmin=0, vmax=3, interpolation="nearest")

ax_a.set_xticks(range(len(pivot.columns)))
ax_a.set_xticklabels(pivot.columns, fontsize=11, color="white", fontweight="bold")
ax_a.set_yticks(range(len(pivot.index)))
ax_a.set_yticklabels(pivot.index, fontsize=9, color="white")
ax_a.tick_params(colors="white", length=0)

for spine in ax_a.spines.values():
    spine.set_visible(False)

legend_items = [
    mpatches.Patch(color="#C62828", label="Robust bottleneck (both variants)"),
    mpatches.Patch(color="#FFA726", label="Variant A only (digital intensity)"),
    mpatches.Patch(color="#5C6BC0", label="Variant B only (ICT share)"),
    mpatches.Patch(facecolor="#1e1f29", edgecolor="#444455", label="Neither"),
]
ax_a.legend(
    handles=legend_items, loc="lower right", fontsize=9,
    facecolor="#1e1f29", edgecolor="#2a2d3a", labelcolor="white", framealpha=0.95,
)
ax_a.set_title(
    "Bottleneck Classification — Italian Sectors (2016–2021)\n"
    "Sorted by persistence of robust bottleneck status",
    fontsize=13, color="white", fontweight="bold", pad=14,
)
plt.tight_layout()
fig_a.savefig(OUT_FIG / "figA_bottleneck_panel_2016_2021.png", dpi=150, bbox_inches="tight", facecolor="#1e1f29")
plt.close(fig_a)
print(f"Saved {OUT_FIG / 'figA_bottleneck_panel_2016_2021.png'}")


# -----------------------------------------------------------------------------
# Figure B — 2×2 digitalisation typology scatter (2021)
# X = ICT share norm (embedded capital stock).
# Y = digital intensity norm (investment flow).
# Four quadrants with coloured backgrounds, bubble size = PageRank.
# Only central sectors (above 60th percentile PageRank) are labelled to
# focus attention on the sectors that matter for the bottleneck question.
# -----------------------------------------------------------------------------
df_2021 = panel_df[panel_df["year"] == 2021].copy()

typology_colors = {
    "Digital leader":       "#66BB6A",
    "In transition":        "#FFA726",
    "Past adopter":         "#42A5F5",
    "Structurally lagging": "#EF5350",
}
typology_bg = {
    "Digital leader":       "#1a3320",
    "In transition":        "#332610",
    "Past adopter":         "#0d1e33",
    "Structurally lagging": "#331010",
}

valid_b = df_2021["dig_intensity_norm"].notna() & df_2021["ict_share_norm"].notna()
plot_b = df_2021[valid_b].copy()
dig_med = plot_b["dig_intensity_norm"].median()
ict_med = plot_b["ict_share_norm"].median()

fig_b, ax_b = plt.subplots(figsize=(11, 9), facecolor="#1e1f29")
style_ax(ax_b)

# Quadrant background shading
ax_b.axvspan(ict_med, 1.05, ymin=0.5, ymax=1.0, color=typology_bg["Digital leader"], zorder=0)
ax_b.axvspan(-0.05, ict_med, ymin=0.5, ymax=1.0, color=typology_bg["In transition"], zorder=0)
ax_b.axvspan(ict_med, 1.05, ymin=0.0, ymax=0.5, color=typology_bg["Past adopter"], zorder=0)
ax_b.axvspan(-0.05, ict_med, ymin=0.0, ymax=0.5, color=typology_bg["Structurally lagging"], zorder=0)

ax_b.axvline(ict_med, color="#555566", linewidth=1, linestyle="--", alpha=0.8)
ax_b.axhline(dig_med, color="#555566", linewidth=1, linestyle="--", alpha=0.8)

pr_cut = plot_b["pagerank"].quantile(0.60)
pr_max = plot_b["pagerank"].max()
pr_den = pr_max if pd.notna(pr_max) and pr_max > 0 else 1.0
sizes = plot_b["pagerank"] / pr_den * 700 + 40

for typ, color in typology_colors.items():
    mask = plot_b["typology"] == typ
    ax_b.scatter(
        plot_b.loc[mask, "ict_share_norm"],
        plot_b.loc[mask, "dig_intensity_norm"],
        s=sizes[mask],
        c=color,
        alpha=0.85,
        edgecolors="white",
        linewidths=0.5,
        zorder=3,
        label=typ,
    )

# Label central sectors (above PageRank 60th percentile)
for _, row in plot_b[plot_b["pagerank"] >= pr_cut].iterrows():
    ax_b.annotate(
        row["sector_label"],
        xy=(row["ict_share_norm"], row["dig_intensity_norm"]),
        xytext=(5, 4),
        textcoords="offset points",
        fontsize=7.5,
        color="white",
        alpha=0.95,
    )

# Quadrant labels
for txt, x, y, ha in [
    ("Digital leader",       0.75, 0.88, "center"),
    ("In transition",        0.05, 0.88, "left"),
    ("Past adopter",         0.75, 0.06, "center"),
    ("Structurally\nlagging", 0.05, 0.06, "left"),
]:
    ax_b.text(x, y, txt, transform=ax_b.transAxes, fontsize=9,
              color="#aaaaaa", alpha=0.7, ha=ha, va="bottom")

ax_b.set_xlim(-0.03, 1.05)
ax_b.set_ylim(-0.03, 1.05)
ax_b.set_xlabel("ICT share norm — embedded capital stock (EUKLEMS)", fontsize=10)
ax_b.set_ylabel("Digital intensity norm — software + R&D investment (Intan-Invest)", fontsize=10)
ax_b.set_title(
    "Digitalisation Typology — Italian Sectors (2021)\n"
    "Bubble size = PageRank (technical coefficients)  ·  Labels = sectors above 60th percentile",
    fontsize=12, color="white", fontweight="bold", pad=12,
)
ax_b.legend(fontsize=9, facecolor="#1e1f29", edgecolor="#2a2d3a", labelcolor="white", loc="upper left")
plt.tight_layout()
fig_b.savefig(OUT_FIG / "figB_typology_scatter_2021.png", dpi=150, bbox_inches="tight", facecolor="#1e1f29")
plt.close(fig_b)
print(f"Saved {OUT_FIG / 'figB_typology_scatter_2021.png'}")


# -----------------------------------------------------------------------------
# Figure C — Technical coefficient PageRank vs digitalisation (2021, two panels)
# Same structure as Fig 3 in analysis.py but:
#   - PageRank is based on Leontief coefficients, not raw USD flows
#   - Colour encodes typology, not sector type
#   - Aggregate-source sectors shown as hollow markers in Variant B panel
# -----------------------------------------------------------------------------
panel_variants_c = [
    ("dig_intensity_norm", "Variant A — Digital Intensity\n(software + R&D / VA, Intan-Invest)"),
    ("ict_share_norm",     "Variant B — ICT Share\n(EUKLEMS, direct-source sectors only)"),
]

fig_c, axes_c = plt.subplots(1, 2, figsize=(18, 8), facecolor="#1e1f29")
for ax, (xcol, title) in zip(axes_c, panel_variants_c):
    style_ax(ax)
    valid = df_2021[xcol].notna()
    plot_df = df_2021[valid].copy()

    x = plot_df[xcol]
    y = plot_df["pagerank"] * 100
    strength_max = df_2021["total_strength"].max()
    strength_den = strength_max if pd.notna(strength_max) and strength_max > 0 else 1.0
    s = plot_df["total_strength"] / strength_den * 700 + 40

    pr_cut = y.quantile(0.60)
    dig_cut_a = x.quantile(0.40) if xcol == "dig_intensity_norm" else None
    dig_cut_b = x[plot_df["ict_share_source"] == "direct"].quantile(0.30) if xcol == "ict_share_norm" else None
    dig_cut = dig_cut_a if xcol == "dig_intensity_norm" else dig_cut_b

    # Shade bottleneck quadrant
    if dig_cut is not None and pd.notna(dig_cut):
        ax.axvspan(x.min() - 0.05, dig_cut, color="#EF5350", alpha=0.06, zorder=1)
        ax.axhspan(pr_cut, y.max() * 1.1, color="#EF5350", alpha=0.06, zorder=1)
        ax.axvline(dig_cut, color="#EF5350", alpha=0.7, linewidth=1, linestyle="--")
    ax.axhline(pr_cut, color="#EF5350", alpha=0.7, linewidth=1, linestyle="--")

    for typ, color in typology_colors.items():
        mask = plot_df["typology"] == typ
        # In Variant B panel, aggregate-source sectors as hollow markers
        if xcol == "ict_share_norm":
            direct = mask & (plot_df["ict_share_source"] == "direct")
            aggr = mask & (plot_df["ict_share_source"] == "aggregate")
            ax.scatter(x[direct], y[direct], s=s[direct], c=color, alpha=0.85,
                       edgecolors="white", linewidths=0.5, zorder=3)
            ax.scatter(x[aggr], y[aggr], s=s[aggr], facecolors="none", edgecolors=color,
                       linewidths=1.2, alpha=0.5, zorder=3)
        else:
            ax.scatter(x[mask], y[mask], s=s[mask], c=color, alpha=0.85,
                       edgecolors="white", linewidths=0.5, zorder=3)

    # Label sectors above PageRank threshold
    for _, row in plot_df[plot_df["pagerank"] * 100 >= pr_cut].iterrows():
        ax.annotate(
            row["sector_label"],
            xy=(row[xcol], row["pagerank"] * 100),
            xytext=(5, 4),
            textcoords="offset points",
            fontsize=7.5,
            color="white",
            alpha=0.95,
        )

    ax.set_xlabel("Digitalisation score (0–1)", fontsize=10)
    ax.set_ylabel("PageRank, % (technical coefficients)", fontsize=10)
    ax.set_title(title, fontsize=11, color="white", fontweight="bold")

# Shared typology legend
legend_items_c = [mpatches.Patch(color=c, label=t) for t, c in typology_colors.items()]
legend_items_c.append(
    mpatches.Patch(facecolor="none", edgecolor="white", label="Aggregate-source (Variant B only)")
)
fig_c.legend(
    handles=legend_items_c, loc="lower center", ncol=5, fontsize=9,
    facecolor="#1e1f29", edgecolor="#2a2d3a", labelcolor="white", framealpha=0.95,
    bbox_to_anchor=(0.5, -0.01),
)
fig_c.suptitle(
    "Centrality vs Digitalisation — Italy (2021)  ·  Technical coefficient PageRank\n"
    "Top-left quadrant = bottleneck zone  ·  Colour = digitalisation typology  ·  Hollow = aggregate-source ICT value",
    fontsize=12, color="white", fontweight="bold",
)
plt.tight_layout(rect=[0, 0.04, 1, 0.94])
fig_c.savefig(OUT_FIG / "figC_coeff_pagerank_vs_digital_2021.png", dpi=150, bbox_inches="tight", facecolor="#1e1f29")
plt.close(fig_c)
print(f"Saved {OUT_FIG / 'figC_coeff_pagerank_vs_digital_2021.png'}")

print("\nPipeline complete.")
