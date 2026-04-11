from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from utils.helpers import (
    country_label_y,
    draw_arc,
    foreign_positions,
    load_zblock_csv,
    minmax,
    sector_type_color,
    style_ax,
)
from utils.constants import NACE_TO_ICIO, SECTOR_LABELS

# Input / Output paths
ROOT = Path(__file__).resolve().parent.parent
DATA_PREP = ROOT / "data" / "prepared"
DATA_PROC = ROOT / "data" / "processed"
OUT_FIG = ROOT / "outputs" / "figures"
OUT_TBL = ROOT / "outputs" / "tables"

OUT_FIG.mkdir(parents=True, exist_ok=True)
OUT_TBL.mkdir(parents=True, exist_ok=True)

# Load and inspect all required 2021 files first
icio_path = DATA_PREP / "icio_zblock_2021.csv"
growth_path = DATA_PROC / "growth_accounts_2021_wide.csv"
intang_path = DATA_PROC / "intangibles_analytical_2021.csv"

print("=" * 80)
print("INPUT SCHEMA CHECK (2021)")
print("=" * 80)

z_block = load_zblock_csv(icio_path)
growth_df = pd.read_csv(growth_path, low_memory=False)
intang_df = pd.read_csv(intang_path, low_memory=False)

print(f"Loaded {icio_path.name}: shape={z_block.shape}")
print(f"Z-block columns sample: {list(z_block.columns[:10])}")
print("-" * 80)
print(f"Loaded {growth_path.name}: shape={growth_df.shape}")
print(f"Growth columns: {list(growth_df.columns)}")
print("-" * 80)
print(f"Loaded {intang_path.name}: shape={intang_df.shape}")
print(f"Intangibles columns sample: {list(intang_df.columns[:40])}")
print("=" * 80)

# -----------------------------------------------------------------------------
# Part 1 — Intermediate-use graph and centrality
# -----------------------------------------------------------------------------
print("\nPART 1 — Graph + centrality")

# Extract labels and adjacency matrix from Z-block
labels = z_block.index.astype(str).tolist()
Adjacency_Matrix = z_block.to_numpy(dtype=np.float64)

# Zero out diagonal to remove intra-sector flows (see README for rationale)
np.fill_diagonal(Adjacency_Matrix, 0.0)

# Apply threshold to filter out minor flows
src_idx, tgt_idx = np.where(Adjacency_Matrix > 50)
weights = Adjacency_Matrix[src_idx, tgt_idx]

# Build directed graph from thresholded flows
G = nx.DiGraph()
G.add_nodes_from(labels)
G.add_weighted_edges_from((labels[s], labels[t], float(w)) for s, t, w in zip(src_idx, tgt_idx, weights))

print(f"Graph built with threshold $50M:")
print(f"Nodes={G.number_of_nodes():,}, Edges={G.number_of_edges():,}")

# Compute centrality measures
pagerank = nx.pagerank(G, weight="weight")
betweenness = nx.betweenness_centrality(G, k=300, normalized=True, weight="weight", seed=42)
in_strength = dict(G.in_degree(weight="weight"))
out_strength = dict(G.out_degree(weight="weight"))

# Create centrality DataFrame for all nodes
centrality_df = pd.DataFrame(
    {
        "node": list(G.nodes),
        "country": [n.split("_", 1)[0] for n in G.nodes],
        "sector": [n.split("_", 1)[1] for n in G.nodes],
        "pagerank": [pagerank[n] for n in G.nodes],
        "betweenness": [betweenness[n] for n in G.nodes],
        "in_strength": [in_strength[n] for n in G.nodes],
        "out_strength": [out_strength[n] for n in G.nodes],
    }
)

# Compute total strength as sum of in + out for later use in visualisations
centrality_df["total_strength"] = centrality_df["in_strength"] + centrality_df["out_strength"]

# Filter to Italian sectors only for analysis
ita_centrality = (centrality_df[centrality_df["country"] == "ITA"].copy().reset_index(drop=True))
print(f"Italian sectors in centrality table: {len(ita_centrality)}")

# Store intermediate centrality table for Italy
ita_centrality.to_csv(OUT_TBL / "italy_centrality_2021.csv", index=False)
print(f"Saved {OUT_TBL / 'italy_centrality_2021.csv'}")

# -----------------------------------------------------------------------------
# Part 2 — Digitalisation metrics
# -----------------------------------------------------------------------------
print("\nPART 2 — Digitalisation metrics")

# Select only Italian sectors
growth_it = growth_df[growth_df["geo_code"] == "IT"].copy()

# Start preprocessing growth accounts: compute ICT share and map to ICIO sectors
print(f"\nStarting growth accounts preprocessing: initial rows={len(growth_it)}")

# Map NACE codes to ICIO sectors and drop rows with missing mappings or ICT share
growth_it["icio_code"] = growth_it["nace_r2_code"].map(NACE_TO_ICIO)

# Computing number of rows before data cleaning
n_before = len(growth_it)
# Count missing values for icio_code and ict_share before dropping
n_missing_icio = growth_it["icio_code"].isna().sum()
print(f"Sectors with missing ICIO code: {n_missing_icio} ({n_missing_icio / n_before:.1%}, {growth_it[growth_it['icio_code'].isna()]['nace_r2_code'].unique()})")
n_missing_ict = growth_it["ict_share"].isna().sum()
print(f"Sectors with missing ICT share: {n_missing_ict} ({n_missing_ict / n_before:.1%}, {growth_it[growth_it['ict_share'].isna()]['nace_r2_code'].unique()})")

# Drop rows with missing ICIO code or ICT share and report how many were dropped
growth_it = growth_it.dropna(subset=["icio_code", "ict_share"])
n_after = len(growth_it)
print(f"Rows dropped due to missing ICIO code or ICT share: {n_before - n_after}, columns left: {n_after}")

# Compute average ICT share by ICIO sector
ict_by_sector = growth_it.groupby("icio_code", as_index=False)["ict_share"].mean()


# Intangibles data for Italy
intang_it = intang_df[intang_df["geo_code"] == "IT"].copy()

# Start preprocessing intangibles: compute digital intensity and map to ICIO sectors
print(f"\nStarting intangibles preprocessing: initial rows={len(intang_it)}...")

# Compute digital intensity as (Soft_DB + R&D) / VA_CP, handling missing values and zero denominators
intang_it["dig_intensity"] = (intang_it["I_Soft_DB"].fillna(0.0) + intang_it["I_RD"].fillna(0.0)) / intang_it["VA_CP"].replace(0, np.nan)

# Map NACE codes to ICIO sectors and drop rows with missing mappings or digital intensity
intang_it["icio_code"] = intang_it["nace_r2_code"].map(NACE_TO_ICIO)
# Compute number of rows before data cleaning
rows_before = len(intang_it)
# Count missing values for icio_code and dig_intensity before dropping
n_missing_icio_intang = intang_it["icio_code"].isna().sum()
print(f"Sectors with missing ICIO code in intangibles: {n_missing_icio_intang} ({n_missing_icio_intang / rows_before:.1%}, {intang_it[intang_it['icio_code'].isna()]['nace_r2_code'].unique()})")
n_missing_dig_intensity = intang_it["dig_intensity"].isna().sum()
print(f"Sectors with missing digital intensity: {n_missing_dig_intensity} ({n_missing_dig_intensity / rows_before:.1%}, {intang_it[intang_it['dig_intensity'].isna()]['nace_r2_code'].unique()})")
intang_it = intang_it.dropna(subset=["icio_code", "dig_intensity"])
rows_after = len(intang_it)
print(f"Rows dropped due to missing ICIO code or digital intensity: {rows_before - rows_after}, columns left: {rows_after}")

# Compute average digital intensity by ICIO sector
dig_by_sector = (intang_it.groupby("icio_code", as_index=False)["dig_intensity"].mean())

# Merge ICT share and digital intensity on ICIO code to create composite table
print(f"\nMerging ICT share and digital intensity: ICT rows={len(ict_by_sector)}, Intangibles rows={len(dig_by_sector)}")
df_composite = ict_by_sector.merge(dig_by_sector, on="icio_code", how="outer")

# Report any sectors that are in one dataset but not the other
unmatched_sectors = dig_by_sector[~dig_by_sector["icio_code"].isin(ict_by_sector["icio_code"])]["icio_code"].tolist()
print(f"Sectors in intangibles but not in ICT: {unmatched_sectors}")


# Normalise both digitalisation measures to [0,1] for comparability
# NaN values (H50/H51/H52/H53 missing ICT share) are preserved — handled in classification
df_composite["dig_intensity_norm"] = minmax(df_composite["dig_intensity"])
df_composite["ict_share_norm"] = minmax(df_composite["ict_share"])

df_composite.to_csv(OUT_TBL / "df_composite_2021.csv", index=False)
print(f"Saved {OUT_TBL / 'df_composite_2021.csv'}")


# -----------------------------------------------------------------------------
# Part 3 — Merge and classify double bottlenecks
# -----------------------------------------------------------------------------
print("\nPART 3 — Double bottleneck classification")
print("-" * 50)

# Merge Italian centrality with digitalisation measures
analysis_df = ita_centrality.merge(
    df_composite,
    left_on="sector",
    right_on="icio_code",
    how="inner",
)
analysis_df["sector_label"] = analysis_df["sector"].map(SECTOR_LABELS).fillna(analysis_df["sector"])
print(f"Sectors entering bottleneck analysis: {len(analysis_df)}")

# A sector is a double bottleneck if:
#   - PageRank >= 60th percentile (structurally central in the global supply network)
#   - Digitalisation <= 40th percentile (digitally lagging relative to other Italian sectors)
#
# Two independent variants to check robustness of the classification:
#   Variant A — digital intensity (software + R&D / VA): covers all matched sectors
#   Variant B — ICT share (EUKLEMS): covers 33 sectors; H50/H51/H52/H53 excluded (no EUKLEMS data)
# Sectors flagged in both variants are robust double bottlenecks.

def classify_variant(df: pd.DataFrame, digital_col: str) -> pd.Series:
    valid = df[digital_col].notna()
    pr_cut = df.loc[valid, "pagerank"].quantile(0.60)
    dig_cut = df.loc[valid, digital_col].quantile(0.40)
    return (df["pagerank"] >= pr_cut) & (df[digital_col] <= dig_cut)


analysis_df["variant_a_dig_intensity"] = classify_variant(analysis_df, "dig_intensity_norm")
analysis_df["variant_b_ict_share"] = classify_variant(analysis_df, "ict_share_norm")
analysis_df["robust"] = analysis_df["variant_a_dig_intensity"] & analysis_df["variant_b_ict_share"]

n_a = analysis_df["variant_a_dig_intensity"].sum()
n_b = analysis_df["variant_b_ict_share"].sum()
n_robust = analysis_df["robust"].sum()
print(f"Bottlenecks — Variant A (digital intensity): {n_a}")
print(f"Bottlenecks — Variant B (ICT share):         {n_b}")
print(f"Robust double bottlenecks (flagged in both): {n_robust}")
print("-" * 50)

robustness_cols = [
    "sector",
    "sector_label",
    "pagerank",
    "dig_intensity_norm",
    "ict_share_norm",
    "variant_a_dig_intensity",
    "variant_b_ict_share",
    "robust",
]
robustness = analysis_df[robustness_cols].sort_values(
    ["robust", "variant_a_dig_intensity", "sector"],
    ascending=[False, False, True],
)

print("\nRobustness check table:")
print(robustness.to_string(index=False))

robustness.to_csv(OUT_TBL / "robustness_check_2021.csv", index=False)
print(f"\nSaved {OUT_TBL / 'robustness_check_2021.csv'}")


# -----------------------------------------------------------------------------
# Part 4 — Visualisations
# -----------------------------------------------------------------------------
print("\nPART 4 — Visualisations")

# Figure 0: network spine — Italy's position in the global supply network
# Italian sectors sorted by PageRank in the centre; top 10 trading partners on left/right;
# bezier arcs = top 5% of bilateral flows by weight.
ita_nodes = [n for n in G.nodes if n.startswith("ITA_")]

country_flow = {}
for u, v, d in G.edges(data=True):
    u_country = u.split("_", 1)[0]
    v_country = v.split("_", 1)[0]
    if (u_country == "ITA") == (v_country == "ITA"):
        continue
    foreign = v_country if u_country == "ITA" else u_country
    country_flow[foreign] = country_flow.get(foreign, 0.0) + float(d["weight"])

top10_countries = sorted(country_flow, key=country_flow.get, reverse=True)[:10]

candidate_edges = [
    (u, v, float(d["weight"]))
    for u, v, d in G.edges(data=True)
    if (
        (u.startswith("ITA_") and v.split("_", 1)[0] in top10_countries)
        or (v.startswith("ITA_") and u.split("_", 1)[0] in top10_countries)
    )
]

if len(candidate_edges) > 0:
    edge_cut = np.percentile([w for _, _, w in candidate_edges], 95)
    top_edges = [(u, v, w) for (u, v, w) in candidate_edges if w >= edge_cut]
else:
    top_edges = []

ita_sorted = sorted(ita_nodes, key=lambda n: pagerank.get(n, 0.0), reverse=True)
Y_MAX, Y_MIN = 1.0, -1.0
X_ITA = 0.0
ita_y = np.linspace(Y_MAX, Y_MIN, len(ita_sorted))
ita_pos = {node: (X_ITA, ita_y[i]) for i, node in enumerate(ita_sorted)}

left_countries = top10_countries[:5]
right_countries = top10_countries[5:]
X_LEFT, X_RIGHT = -1.6, 1.6


left_pos = foreign_positions(left_countries, X_LEFT, top_edges, G.nodes, Y_MAX, Y_MIN)
right_pos = foreign_positions(right_countries, X_RIGHT, top_edges, G.nodes, Y_MAX, Y_MIN)
all_pos = {**ita_pos, **left_pos, **right_pos}

fig0, ax0 = plt.subplots(figsize=(20, 24), facecolor= "#1e1f29")
ax0.set_facecolor("#1e1f29")
ax0.axis("off")


if len(top_edges) > 0:
    max_w = max(w for _, _, w in top_edges)
    for u, v, w in top_edges:
        if u not in all_pos or v not in all_pos:
            continue
        ita_node = u if u.startswith("ITA_") else v
        color = sector_type_color(ita_node.split("_", 1)[1])
        alpha = 0.12 + 0.45 * (w / max_w)
        lw = 0.4 + 2.0 * (w / max_w)
        draw_arc(ax0, all_pos[u], all_pos[v], color=color, alpha=float(alpha), lw=float(lw))

country_palette = [
    "#546E7A",
    "#5C6BC0",
    "#26A69A",
    "#66BB6A",
    "#FFA726",
    "#8D6E63",
    "#78909C",
    "#AB47BC",
    "#EF5350",
    "#42A5F5",
]
country_colors = {c: country_palette[i] for i, c in enumerate(top10_countries)}

max_pr = max(pagerank.values()) if len(pagerank) else 1.0

for node, (x, y) in {**left_pos, **right_pos}.items():
    country = node.split("_", 1)[0]
    size = 15 + (pagerank.get(node, 0.0) / max_pr) * 200
    ax0.scatter(
        x,
        y,
        s=size,
        c=country_colors.get(country, "#555566"),
        edgecolors="white",
        linewidths=0.3,
        zorder=3,
        alpha=0.75,
    )

for node in ita_sorted:
    x, y = ita_pos[node]
    size = 60 + (pagerank.get(node, 0.0) / max_pr) * 1400
    color = sector_type_color(node.split("_", 1)[1])
    ax0.scatter(x, y, s=size, c=color, edgecolors="white", linewidths=0.7, zorder=5, alpha=0.95)

for i, node in enumerate(ita_sorted):
    x, y = ita_pos[node]
    sec = node.split("_", 1)[1]
    label = SECTOR_LABELS.get(sec, sec)
    if i % 2 == 0:
        ax0.text(x + 0.07, y, label, fontsize=7.2, color="white", va="center", ha="left", alpha=0.88)
    else:
        ax0.text(x - 0.07, y, label, fontsize=7.2, color="white", va="center", ha="right", alpha=0.88)

for country in left_countries:
    y = country_label_y(left_pos, country)
    ax0.text(X_LEFT - 0.1, y, country, fontsize=12, color=country_colors[country], fontweight="bold", va="center", ha="right", alpha=0.95)

for country in right_countries:
    y = country_label_y(right_pos, country)
    ax0.text(X_RIGHT + 0.1, y, country, fontsize=12, color=country_colors[country], fontweight="bold", va="center", ha="left", alpha=0.95)

for x in [X_ITA - 0.22, X_ITA + 0.22]:
    ax0.axvline(x, color="#2a2d3a", linewidth=0.8, linestyle="--", alpha=0.7)

legend_items = [
    mpatches.Patch(color="#4FC3F7", label="Digital / ICT"),
    mpatches.Patch(color="#FFB74D", label="Manufacturing"),
    mpatches.Patch(color="#81C784", label="Business services"),
    mpatches.Patch(color="#F48FB1", label="Trade & transport"),
    mpatches.Patch(color="#CE93D8", label="Utilities & construction"),
    mpatches.Patch(color="#90A4AE", label="Other"),
]
ax0.legend(
    handles=legend_items,
    loc="lower left",
    fontsize=10,
    facecolor="#1e1f29",
    edgecolor="#2a2d3a",
    labelcolor="white",
    framealpha=0.95,
    bbox_to_anchor=(0.01, 0.01),
)

ax0.set_title(
    f"Italy in the Global Supply Network 2021)\n"
    "Centre: Italian sectors by PageRank  ·  Sides: top 10 partner countries  ·  Arcs: top 5% flows",
    fontsize=13,
    color="white",
    fontweight="bold",
    pad=16,
)
ax0.set_xlim(-2.0, 2.0)
ax0.set_ylim(-1.12, 1.12)
plt.tight_layout()
fig0.savefig(OUT_FIG / "fig0_network_spine_2021.png", dpi=150, bbox_inches="tight", facecolor="#1e1f29")
plt.close(fig0)
print(f"Saved {OUT_FIG / 'fig0_network_spine_2021.png'}")


# Figure 1: Top-15 Italian sectors by total IO flow strength
# Establishes which sectors are the largest hubs in the global supply chain —
# the starting point for identifying where bottlenecks could have the most impact.
fig1, ax1 = plt.subplots(figsize=(12, 7), facecolor="#1e1f29")
style_ax(ax1)

top15 = ita_centrality.nlargest(15, "total_strength").copy()
top15["label"] = top15["sector"].map(SECTOR_LABELS).fillna(top15["sector"])
bar_colors = [sector_type_color(s) for s in top15["sector"]]

bars = ax1.barh(
    range(len(top15)),
    top15["total_strength"] / 1000.0,
    color=bar_colors,
    edgecolor="none",
    height=0.65,
)
ax1.set_yticks(range(len(top15)))
ax1.set_yticklabels(top15["label"], fontsize=10, color="white")
ax1.set_xlabel("Total IO flow strength (billion USD)", fontsize=10)
ax1.set_title(
    f"Italian Sector Hubs — Total IO Flow Strength (2021)",
    fontsize=13,
    color="white",
    fontweight="bold",
    pad=12,
)
ax1.invert_yaxis()

for bar, val in zip(bars, top15["total_strength"] / 1000.0):
    ax1.text(float(val) + 0.2, bar.get_y() + bar.get_height() / 2, f"${val:.1f}B", va="center", color="white", fontsize=8)

plt.tight_layout()
fig1.savefig(OUT_FIG / "fig1_hub_ranking_2021.png", dpi=150, bbox_inches="tight", facecolor="#1e1f29")
plt.close(fig1)
print(f"Saved {OUT_FIG / 'fig1_hub_ranking_2021.png'}")


# Figure 2: PageRank vs Betweenness centrality
# Separates two distinct structural roles: sectors that are large recipients of supply-chain
# inputs (high PageRank) vs sectors that act as bridges whose removal would disconnect many
# supply paths (high betweenness). The two roles do not always coincide.
fig2, ax2 = plt.subplots(figsize=(10, 7), facecolor="#1e1f29")
style_ax(ax2)

sizes = ita_centrality["total_strength"] / ita_centrality["total_strength"].max() * 600 + 30
sc = ax2.scatter(
    ita_centrality["betweenness"] * 100,
    ita_centrality["pagerank"] * 100,
    s=sizes,
    alpha=0.80,
    c=ita_centrality["total_strength"],
    cmap="plasma",
    edgecolors="white",
    linewidths=0.4,
)

for _, row in ita_centrality[ita_centrality["pagerank"] >= ita_centrality["pagerank"].quantile(0.75)].iterrows():
    sec = row["sector"]
    lab = SECTOR_LABELS.get(sec, sec)
    ax2.annotate(lab, (row["betweenness"] * 100, row["pagerank"] * 100), xytext=(5, 3), textcoords="offset points", fontsize=7.5, color="white")

cb = plt.colorbar(sc, ax=ax2, pad=0.01)
cb.set_label("Total flow strength (M USD)", color="white", fontsize=9)
cb.ax.yaxis.set_tick_params(color="white")
plt.setp(cb.ax.yaxis.get_ticklabels(), color="white")

ax2.set_xlabel("Betweenness centrality (%)", fontsize=10)
ax2.set_ylabel("PageRank (%)", fontsize=10)
ax2.set_title(
    f"Centrality Map — Italian Sectors (2021)",
    fontsize=13,
    color="white",
    fontweight="bold",
    pad=10,
)

plt.tight_layout()
fig2.savefig(OUT_FIG / "fig2_centrality_map_2021.png", dpi=150, bbox_inches="tight", facecolor="#1e1f29")
plt.close(fig2)
print(f"Saved {OUT_FIG / 'fig2_centrality_map_2021.png'}")


# Figure 3: PageRank vs digitalisation — two panels, one per variant
# The top-left quadrant (high centrality, low digitalisation) is the double bottleneck zone.
# Variant A uses digital intensity (Intan-Invest, all matched sectors).
# Variant B uses ICT share (EUKLEMS, 33 sectors — H50/H51/H52/H53 excluded).
# Robust bottlenecks are highlighted with a white ring to distinguish them from the rest.
panel_variants = [
    ("dig_intensity_norm", "Variant A — Digital Intensity\n(software + R&D / VA, Intan-Invest)"),
    ("ict_share_norm", "Variant B — ICT Share\n(EUKLEMS growth accounts)"),
]

fig3, axes = plt.subplots(1, 2, figsize=(18, 7), facecolor= "#1e1f29")
for ax, (xcol, title) in zip(axes, panel_variants):
    style_ax(ax)
    valid = analysis_df[xcol].notna()
    plot_df = analysis_df[valid].copy()

    x = plot_df[xcol]
    y = plot_df["pagerank"]
    s = plot_df["total_strength"] / analysis_df["total_strength"].max() * 700 + 40

    # Non-robust sectors
    non_robust = ~plot_df["robust"]
    ax.scatter(
        x[non_robust], y[non_robust],
        s=s[non_robust],
        c=[sector_type_color(sec) for sec in plot_df.loc[non_robust, "sector"]],
        alpha=0.75,
        edgecolors="none",
        zorder=3,
    )

    # Robust bottlenecks — highlighted with white ring
    robust = plot_df["robust"]
    ax.scatter(
        x[robust], y[robust],
        s=s[robust],
        c=[sector_type_color(sec) for sec in plot_df.loc[robust, "sector"]],
        alpha=0.95,
        edgecolors="white",
        linewidths=1.5,
        zorder=5,
    )

    # Threshold lines marking the bottleneck quadrant
    pr_cut = y.quantile(0.60)
    dig_cut = x.quantile(0.40)
    ax.axvline(dig_cut, color="#EF5350", alpha=0.45, linewidth=1, linestyle="--")
    ax.axhline(pr_cut, color="#EF5350", alpha=0.45, linewidth=1, linestyle="--")

    for _, row in plot_df.iterrows():
        ax.annotate(
            row["sector_label"],
            xy=(row[xcol], row["pagerank"]),
            xytext=(4, 3),
            textcoords="offset points",
            fontsize=7,
            color="white",
            alpha=0.9,
        )

    ax.set_xlabel("Digitalisation score (0–1)", fontsize=10)
    ax.set_ylabel("PageRank", fontsize=10)
    ax.set_title(title, fontsize=11, color="white", fontweight="bold")

fig3.suptitle(
    f"Centrality vs Digitalisation — Italy (2021)\n"
    "Top-left quadrant = double bottleneck zone  ·  White ring = robust across both variants  ·  Bubble size = total strength",
    fontsize=13,
    color="white",
    fontweight="bold",
)
plt.tight_layout(rect=[0, 0.02, 1, 0.94])
fig3.savefig(OUT_FIG / "fig3_centrality_vs_digitalisation_panel_2021.png", dpi=150, bbox_inches="tight", facecolor="#1e1f29")
plt.close(fig3)
print(f"Saved {OUT_FIG / 'fig3_centrality_vs_digitalisation_panel_2021.png'}")

print("\nPipeline complete.")