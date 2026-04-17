"""
analysis.py — Digital Transition and Supply-Chain Structure in the Italian Economy
===================================================================================
Internet and Network Economics — Group Project

Research question
-----------------
Are the sectors that Italy's production network depends on most heavily also
the ones that are most digitally lagging?

A sector that is structurally central AND under-digitalised is called a
"double bottleneck": it drags down every downstream sector.

Pipeline
--------
    Part 1 — Build the supply-chain network for each year (2016–2021).
              Use Leontief technical coefficients so that centrality reflects
              structural dependency rather than raw sector size.
              Extract PageRank and betweenness for all Italian sectors.

    Part 2 — Load two independent digitalisation proxies for Italy:
              Variant A — Digital intensity (software + R&D investment / VA)
              Variant B — ICT capital share (ICT capital / total capital services)

    Part 3 — Merge centrality with digitalisation. Classify each sector into
              a 2×2 typology (Digital leader / In transition / Past adopter /
              Structurally lagging). Flag double bottlenecks: sectors that are
              both structurally central and digitally lagging, confirmed by
              both Variant A and Variant B.

    Part 4 — Four publication-ready figures:
              Fig A — Multi-year bottleneck persistence heatmap (2016–2021)
              Fig B — 2×2 digitalisation typology scatter (2021)
              Fig C — Centrality vs digitalisation two-panel with OLS trend (2021)
              Fig D — Top-15 Italian sectors by supply-chain participation (2021)

Prerequisites (produced by preprocessing.py)
--------------------------------------------
    data/prepared/icio_zblock_{year}.csv
    data/processed/growth_accounts_{year}_wide.csv
    data/processed/intangibles_analytical_{year}.csv
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # must be set before pyplot import
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap

from utils.helpers import (
    assign_typology,
    build_coefficient_graph,
    classify_bottleneck,
    load_zblock_csv,
    minmax,
    preprocess_digitalisation,
    sector_type_color,
    style_ax,
)
from utils.constants import NACE_TO_ICIO, SECTOR_LABELS

# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------
ROOT      = Path(__file__).resolve().parent.parent
DATA_PREP = ROOT / "data" / "prepared"
DATA_PROC = ROOT / "data" / "processed"
OUT_FIG   = ROOT / "outputs" / "figures"
OUT_TBL   = ROOT / "outputs" / "tables"

OUT_FIG.mkdir(parents=True, exist_ok=True)
OUT_TBL.mkdir(parents=True, exist_ok=True)

YEARS = list(range(2016, 2022))

# Colour palette used across all scatter plots for the four typology categories
TYPOLOGY_COLORS = {
    "Digital leader":       "#66BB6A",  # green
    "In transition":        "#FFA726",  # amber
    "Past adopter":         "#42A5F5",  # blue
    "Structurally lagging": "#EF5350",  # red
}


# ===========================================================================
# Part 1–3: Multi-year panel loop (2016–2021)
# ===========================================================================
print("=" * 80)
print("ANALYSIS — Digital Transition and Supply-Chain Structure (2016–2021)")
print("=" * 80)

panel_records = []   # results collected here, one DataFrame per year

for year in YEARS:
    icio_path = DATA_PREP / f"icio_zblock_{year}.csv"
    if not icio_path.exists():
        print(f"\n  {year}: z-block not found — skipped")
        continue

    print(f"\n{'—' * 40} {year} {'—' * 40}")

    # ------------------------------------------------------------------
    # Part 1 — Build network and compute centrality
    # ------------------------------------------------------------------

    # Load the intermediate transaction matrix (Z-block) and build the
    # Leontief coefficient graph (see build_coefficient_graph in helpers.py)
    z_block = load_zblock_csv(icio_path)
    G = build_coefficient_graph(z_block)
    print(f"  Network: {G.number_of_nodes():,} nodes, {G.number_of_edges():,} edges")

    # PageRank: how much other important sectors depend on a given sector.
    # Computed on the full global graph (~4,250 nodes); Italian sectors extracted below.
    pagerank = nx.pagerank(G, weight="weight")

    # Betweenness: fraction of shortest supply paths passing through a node.
    # k=300 uses the Brandes approximation (exact computation is infeasible at this scale).
    betweenness = nx.betweenness_centrality(G, k=300, normalized=True, weight="weight", seed=42)

    # Strength: sum of edge weights for in- and out-edges respectively
    in_strength  = dict(G.in_degree(weight="weight"))
    out_strength = dict(G.out_degree(weight="weight"))

    centrality_df = pd.DataFrame({
        "node":         list(G.nodes),
        "country":      [n.split("_", 1)[0] for n in G.nodes],
        "sector":       [n.split("_", 1)[1] for n in G.nodes],
        "pagerank":     [pagerank[n]    for n in G.nodes],
        "betweenness":  [betweenness[n] for n in G.nodes],
        "in_strength":  [in_strength[n] for n in G.nodes],
        "out_strength": [out_strength[n] for n in G.nodes],
    })
    centrality_df["total_strength"] = centrality_df["in_strength"] + centrality_df["out_strength"]

    # Keep only Italian sectors (ITA_*) for the rest of the analysis
    ita_centrality = (
        centrality_df[centrality_df["country"] == "ITA"]
        .copy()
        .reset_index(drop=True)
    )
    print(f"  Italian sectors in network: {len(ita_centrality)}")

    # ------------------------------------------------------------------
    # Part 2 — Load digitalisation measures
    # ------------------------------------------------------------------
    df_composite = preprocess_digitalisation(year, DATA_PROC, NACE_TO_ICIO)
    if df_composite.empty:
        print(f"  Digitalisation data unavailable — skipped")
        continue

    # ------------------------------------------------------------------
    # Part 3 — Merge, classify typology, flag double bottlenecks
    # ------------------------------------------------------------------

    # Inner merge: keeps only sectors present in both the network and
    # the digitalisation data (sectors with no data are reported below)
    analysis_df = ita_centrality.merge(
        df_composite, left_on="sector", right_on="icio_code", how="inner"
    )
    analysis_df["sector_label"] = analysis_df["sector"].map(SECTOR_LABELS).fillna(analysis_df["sector"])

    dropped = ita_centrality[~ita_centrality["sector"].isin(df_composite["icio_code"])]["sector"].tolist()
    print(f"  Sectors analysed: {len(analysis_df)} | Dropped (no digital data): {len(dropped)} — {dropped}")

    # 2×2 typology: each sector is placed relative to the median on both digital measures
    analysis_df["typology"] = assign_typology(analysis_df)

    # Variant A: digital intensity proxy, 60th/40th percentile thresholds
    analysis_df["variant_a"] = classify_bottleneck(analysis_df, "dig_intensity_norm")

    # Variant B: ICT capital share proxy, tighter 30th percentile for digitalisation.
    # Only direct-source sectors are used (sectors that inherit their ICT value from
    # a broad NACE aggregate are excluded — their score blends dissimilar sub-sectors)
    analysis_df["variant_b"] = False
    direct_idx = analysis_df[analysis_df["ict_share_source"] == "direct"].index
    if len(direct_idx) > 0:
        vb = classify_bottleneck(
            analysis_df.loc[direct_idx].copy(), "ict_share_norm", dig_quantile=0.30
        )
        analysis_df.loc[direct_idx, "variant_b"] = vb.values

    # A sector is a ROBUST double bottleneck only if flagged by BOTH variants.
    # Requiring agreement across two independent proxies reduces false positives.
    analysis_df["bottleneck"] = analysis_df["variant_a"] & analysis_df["variant_b"]
    analysis_df["year"] = year

    print(f"  Variant A: {analysis_df['variant_a'].sum()} | "
          f"Variant B: {analysis_df['variant_b'].sum()} | "
          f"Robust bottlenecks: {analysis_df['bottleneck'].sum()}")
    print(f"  Typology: {analysis_df['typology'].value_counts().to_dict()}")

    panel_records.append(analysis_df)

print("\n" + "=" * 80)
panel_df = pd.concat(panel_records, ignore_index=True)
panel_df.to_csv(OUT_TBL / "panel_bottleneck_2016_2021.csv", index=False)
print(f"Saved panel table → {OUT_TBL / 'panel_bottleneck_2016_2021.csv'}")


# ===========================================================================
# Part 4 — Visualisations
# ===========================================================================
print("\nPART 4 — Visualisations")
print("-" * 50)

# Convenience slice: 2021 data is used for the three cross-sectional figures
df_2021 = panel_df[panel_df["year"] == 2021].copy()


# ---------------------------------------------------------------------------
# Figure A — Multi-year bottleneck persistence heatmap (2016–2021)
#
# Shows which Italian sectors are classified as double bottlenecks consistently
# across years.  Persistence strengthens the finding: a sector that is flagged
# every year is a structural problem, not a 2021 anomaly.
#
# Rows    = Italian sectors, sorted by persistence (most persistent at top)
# Columns = years
# Colour  = 4-level status (see legend)
# ---------------------------------------------------------------------------

def _encode_status(row: pd.Series) -> int:
    """Map variant flags to a 0–3 integer for the heatmap colour scale."""
    if row["variant_a"] and row["variant_b"]:
        return 3   # both variants → robust bottleneck
    if row["variant_a"]:
        return 2   # Variant A only (digital intensity)
    if row["variant_b"]:
        return 1   # Variant B only (ICT share)
    return 0       # neither variant

panel_df["status"] = panel_df.apply(_encode_status, axis=1)

# Pivot to sector × year matrix
pivot = panel_df.pivot_table(index="sector_label", columns="year", values="status", aggfunc="first")
pivot = pivot.fillna(0).astype(int)

# Sort rows: more "robust" years first, then any-variant years
sort_key = (pivot == 3).sum(axis=1) * 10 + (pivot >= 1).sum(axis=1)
pivot = pivot.loc[sort_key.sort_values(ascending=False).index]

cmap_a = ListedColormap(["#1e1f29", "#5C6BC0", "#FFA726", "#C62828"])

fig_a, ax_a = plt.subplots(figsize=(10, 13), facecolor="#1e1f29")
ax_a.set_facecolor("#1e1f29")
ax_a.imshow(pivot.values, aspect="auto", cmap=cmap_a, vmin=0, vmax=3, interpolation="nearest")

ax_a.set_xticks(range(len(pivot.columns)))
ax_a.set_xticklabels(pivot.columns, fontsize=11, color="white", fontweight="bold")
ax_a.set_yticks(range(len(pivot.index)))
ax_a.set_yticklabels(pivot.index, fontsize=9, color="white")
ax_a.tick_params(colors="white", length=0)
for spine in ax_a.spines.values():
    spine.set_visible(False)

legend_a = [
    mpatches.Patch(color="#C62828", label="Robust bottleneck — high centrality AND low digitalisation (both variants)"),
    mpatches.Patch(color="#FFA726", label="Variant A only — digital intensity (software + R&D / VA)"),
    mpatches.Patch(color="#5C6BC0", label="Variant B only — ICT capital share (EUKLEMS)"),
    mpatches.Patch(color="#1e1f29", label="Not a bottleneck", edgecolor="#444455"),
]
ax_a.legend(handles=legend_a, loc="lower right", fontsize=8,
            facecolor="#2a2d3a", edgecolor="#444455", labelcolor="white",
            framealpha=0.95, handlelength=1.5)

ax_a.set_title(
    "Which Italian sectors are persistent double bottlenecks?\n"
    "A double bottleneck = structurally central in global supply chains AND digitally lagging\n"
    "Sectors are sorted by persistence: the most consistently flagged appear at the top.",
    fontsize=11, color="white", fontweight="bold", pad=14, loc="left",
)

plt.tight_layout()
fig_a.savefig(OUT_FIG / "figA_bottleneck_panel_2016_2021.png",
              dpi=150, bbox_inches="tight", facecolor="#1e1f29")
plt.close(fig_a)
print(f"Saved {OUT_FIG / 'figA_bottleneck_panel_2016_2021.png'}")


# ---------------------------------------------------------------------------
# Figure B — 2×2 Digitalisation typology scatter (2021)
#
# Maps every Italian sector on two digital dimensions simultaneously:
#   X axis = ICT capital share (EUKLEMS) — how much digital stock is installed
#   Y axis = Digital intensity (Intan-Invest) — how actively digitalising
#   Bubble size = PageRank (structural importance)
#
# Sectors in the bottom-left quadrant ("Structurally lagging") with LARGE
# bubbles are both the least digital and the most central — i.e., the
# double bottlenecks identified in Fig A.
# ---------------------------------------------------------------------------
valid_b    = df_2021["dig_intensity_norm"].notna() & df_2021["ict_share_norm"].notna()
plot_b     = df_2021[valid_b].copy()
dig_med_b  = plot_b["dig_intensity_norm"].median()
ict_med_b  = plot_b["ict_share_norm"].median()

QUAD_BG = {
    "Digital leader":       "#1a3320",
    "In transition":        "#332610",
    "Past adopter":         "#0d1e33",
    "Structurally lagging": "#331010",
}

fig_b, ax_b = plt.subplots(figsize=(11, 9), facecolor="#1e1f29")
style_ax(ax_b)

# Quadrant background shading
ax_b.axvspan(ict_med_b, 1.05,  ymin=0.5, ymax=1.0, color=QUAD_BG["Digital leader"],       zorder=0)
ax_b.axvspan(-0.05, ict_med_b, ymin=0.5, ymax=1.0, color=QUAD_BG["In transition"],         zorder=0)
ax_b.axvspan(ict_med_b, 1.05,  ymin=0.0, ymax=0.5, color=QUAD_BG["Past adopter"],          zorder=0)
ax_b.axvspan(-0.05, ict_med_b, ymin=0.0, ymax=0.5, color=QUAD_BG["Structurally lagging"],  zorder=0)

# Median lines as quadrant boundaries
ax_b.axvline(ict_med_b, color="#777788", linewidth=1, linestyle="--", alpha=0.8)
ax_b.axhline(dig_med_b, color="#777788", linewidth=1, linestyle="--", alpha=0.8)

sizes_b  = plot_b["pagerank"] / plot_b["pagerank"].max() * 700 + 40
pr_cut_b = plot_b["pagerank"].quantile(0.60)

for typ, color in TYPOLOGY_COLORS.items():
    mask = plot_b["typology"] == typ
    ax_b.scatter(
        plot_b.loc[mask, "ict_share_norm"],
        plot_b.loc[mask, "dig_intensity_norm"],
        s=sizes_b[mask], c=color, alpha=0.85,
        edgecolors="white", linewidths=0.5, zorder=3, label=typ,
    )

# Label only the most central sectors (top 40% PageRank) to reduce clutter
for _, row in plot_b[plot_b["pagerank"] >= pr_cut_b].iterrows():
    ax_b.annotate(
        row["sector_label"],
        xy=(row["ict_share_norm"], row["dig_intensity_norm"]),
        xytext=(6, 4), textcoords="offset points",
        fontsize=8, color="white", alpha=0.95,
    )

# Quadrant labels in the four corners
for txt, x_pos, y_pos, ha in [
    ("Digital leader",        0.76, 0.89, "center"),
    ("In transition",         0.02, 0.89, "left"),
    ("Past adopter",          0.76, 0.04, "center"),
    ("Structurally\nlagging", 0.02, 0.04, "left"),
]:
    ax_b.text(x_pos, y_pos, txt, transform=ax_b.transAxes,
              fontsize=9, color="#bbbbcc", alpha=0.75, ha=ha, va="bottom")

ax_b.set_xlim(-0.03, 1.05)
ax_b.set_ylim(-0.03, 1.05)
ax_b.set_xlabel(
    "ICT capital share (0 = lowest, 1 = highest)  ·  EUKLEMS growth accounts\n"
    "← less embedded digital capital stock · more embedded digital capital stock →",
    fontsize=9,
)
ax_b.set_ylabel(
    "Digital investment intensity (0 = lowest, 1 = highest)  ·  Intan-Invest\n"
    "← less software & R&D investment · more software & R&D investment →",
    fontsize=9,
)
ax_b.set_title(
    "Where does each Italian sector stand on digitalisation? (2021)\n"
    "Bubble size = PageRank (structural centrality in global supply chains)\n"
    "Labels shown only for the top 40% most central sectors",
    fontsize=12, color="white", fontweight="bold", pad=12,
)
ax_b.legend(title="Typology", title_fontsize=9, fontsize=9,
            facecolor="#1e1f29", edgecolor="#2a2d3a", labelcolor="white", loc="upper left")

plt.tight_layout()
fig_b.savefig(OUT_FIG / "figB_typology_scatter_2021.png",
              dpi=150, bbox_inches="tight", facecolor="#1e1f29")
plt.close(fig_b)
print(f"Saved {OUT_FIG / 'figB_typology_scatter_2021.png'}")


# ---------------------------------------------------------------------------
# Figure C — Centrality vs Digitalisation, two panels (2021)
#
# Directly tests the research question: are more central sectors less digitalised?
# A negative OLS slope and concentration of sectors in the red (top-left) zone
# would confirm the double bottleneck pattern.
#
# Left panel  = Variant A: digital intensity (all matched sectors)
# Right panel = Variant B: ICT share (direct-source sectors only)
#
# Reading guide:
#   Top-left quadrant (red shading) = double bottleneck zone
#   Dashed lines = classification thresholds
#   White line   = OLS trend (slope shown in legend)
#   Hollow markers (Variant B only) = aggregate-source ICT value, less reliable
# ---------------------------------------------------------------------------
PANEL_VARIANTS = [
    # (column, panel title, x-axis description, dig_quantile, src_filter)
    ("dig_intensity_norm",
     "Variant A — Digital Investment Intensity",
     "Software + R&D investment / Value Added  (Intan-Invest, normalised 0–1)",
     0.40, None),
    ("ict_share_norm",
     "Variant B — ICT Capital Share",
     "ICT capital / total capital services  (EUKLEMS, direct-source only, normalised 0–1)",
     0.30, "direct"),
]

fig_c, axes_c = plt.subplots(1, 2, figsize=(18, 8), facecolor="#1e1f29")

for ax, (xcol, panel_title, x_desc, dig_q, src_filter) in zip(axes_c, PANEL_VARIANTS):
    style_ax(ax)

    valid_c = df_2021[xcol].notna()
    plot_c  = df_2021[valid_c].copy()
    x       = plot_c[xcol]
    y       = plot_c["pagerank"] * 100   # express PageRank as a percentage

    # Bubble size proportional to total supply-chain strength
    s = plot_c["total_strength"] / df_2021["total_strength"].max() * 700 + 40

    # Classification thresholds used to draw the bottleneck zone
    pr_cut_c  = y.quantile(0.60)
    if src_filter:
        dig_cut_c = x[plot_c["ict_share_source"] == "direct"].quantile(dig_q)
    else:
        dig_cut_c = x.quantile(dig_q)

    # Red shading marks the double bottleneck zone (high centrality, low digitalisation)
    ax.axvspan(x.min() - 0.05, dig_cut_c, color="#EF5350", alpha=0.07, zorder=1)
    ax.axhspan(pr_cut_c, y.max() * 1.12,  color="#EF5350", alpha=0.07, zorder=1)

    # Threshold lines
    ax.axvline(dig_cut_c, color="#EF5350", linewidth=1.2, linestyle="--", alpha=0.7,
               label=f"Digitalisation threshold ({int(dig_q*100)}th percentile)")
    ax.axhline(pr_cut_c,  color="#FFA726", linewidth=1.2, linestyle="--", alpha=0.7,
               label="Centrality threshold (60th percentile)")

    # OLS trend line: a negative slope supports the double bottleneck hypothesis
    x_fit = x.dropna().values
    y_fit = y[x.notna()].values
    if len(x_fit) > 2:
        coeffs = np.polyfit(x_fit, y_fit, 1)
        x_line = np.linspace(x_fit.min(), x_fit.max(), 100)
        ax.plot(x_line, np.polyval(coeffs, x_line),
                color="white", linewidth=1.5, linestyle="-", alpha=0.45, zorder=4,
                label=f"OLS trend  (slope = {coeffs[0]:+.2f})")

    # Scatter points coloured by typology; hollow markers for aggregate-source in Variant B
    for typ, color in TYPOLOGY_COLORS.items():
        mask_typ = plot_c["typology"] == typ
        if src_filter:
            direct = mask_typ & (plot_c["ict_share_source"] == "direct")
            aggr   = mask_typ & (plot_c["ict_share_source"] != "direct")
            ax.scatter(x[direct], y[direct], s=s[direct],  c=color,
                       alpha=0.85, edgecolors="white", linewidths=0.5, zorder=3)
            ax.scatter(x[aggr],   y[aggr],   s=s[aggr],   facecolors="none",
                       edgecolors=color, linewidths=1.2, alpha=0.55, zorder=3)
        else:
            ax.scatter(x[mask_typ], y[mask_typ], s=s[mask_typ], c=color,
                       alpha=0.85, edgecolors="white", linewidths=0.5, zorder=3)

    # Sector labels for the most central sectors only
    for _, row in plot_c[y >= pr_cut_c].iterrows():
        ax.annotate(
            row["sector_label"],
            xy=(row[xcol], row["pagerank"] * 100),
            xytext=(5, 4), textcoords="offset points",
            fontsize=7.5, color="white", alpha=0.95,
        )

    # Label the bottleneck zone in the top-left corner
    ax.text(0.02, 0.97, "Double bottleneck\nzone",
            transform=ax.transAxes, fontsize=8, color="#EF5350",
            alpha=0.85, va="top")

    ax.set_xlabel(f"{x_desc}", fontsize=9)
    ax.set_ylabel("PageRank (%)  ·  structural centrality in global supply chain", fontsize=9)
    ax.set_title(panel_title, fontsize=11, color="white", fontweight="bold")
    ax.legend(fontsize=8, facecolor="#1e1f29", edgecolor="#444455",
              labelcolor="white", loc="upper right", framealpha=0.85)

# Shared bottom legend: typology colours + hollow-marker note
shared_patches = [mpatches.Patch(color=c, label=t) for t, c in TYPOLOGY_COLORS.items()]
shared_patches.append(
    mpatches.Patch(facecolor="none", edgecolor="white",
                   label="Hollow = aggregate-source ICT value (Variant B only, less reliable)")
)
fig_c.legend(handles=shared_patches, loc="lower center", ncol=5, fontsize=9,
             facecolor="#1e1f29", edgecolor="#2a2d3a", labelcolor="white",
             framealpha=0.95, bbox_to_anchor=(0.5, -0.03))

fig_c.suptitle(
    "Are Italy's most central supply-chain sectors also the least digitalised? (2021)\n"
    "Top-left red zone = double bottleneck · White line = OLS trend · Bubble size = total supply-chain strength\n"
    "A negative slope and sectors in the red zone confirm the double bottleneck pattern.",
    fontsize=12, color="white", fontweight="bold",
)
plt.tight_layout(rect=[0, 0.05, 1, 0.92])
fig_c.savefig(OUT_FIG / "figC_centrality_vs_digitalisation_2021.png",
              dpi=150, bbox_inches="tight", facecolor="#1e1f29")
plt.close(fig_c)
print(f"Saved {OUT_FIG / 'figC_centrality_vs_digitalisation_2021.png'}")


# ---------------------------------------------------------------------------
# Figure D — Top-15 Italian sectors by total supply-chain participation (2021)
#
# A simple entry-point ranking: which Italian sectors are most embedded in
# global intermediate trade?  These sectors are where a digitalisation gap
# would have the highest potential negative spill-over on other sectors.
#
# Bar colour encodes broad sector type (see helpers.py for the colour mapping).
# ---------------------------------------------------------------------------
top15 = df_2021.nlargest(15, "total_strength").copy()
top15["label"] = top15["sector"].map(SECTOR_LABELS).fillna(top15["sector"])

fig_d, ax_d = plt.subplots(figsize=(12, 7), facecolor="#1e1f29")
style_ax(ax_d)

bar_colors_d = [sector_type_color(s) for s in top15["sector"]]
bars_d = ax_d.barh(
    range(len(top15)), top15["total_strength"],
    color=bar_colors_d, edgecolor="none", height=0.65,
)
ax_d.set_yticks(range(len(top15)))
ax_d.set_yticklabels(top15["label"], fontsize=10, color="white")
ax_d.invert_yaxis()   # highest-ranked sector at top

# Annotate bars with their exact value
for bar, val in zip(bars_d, top15["total_strength"]):
    ax_d.text(float(val) + top15["total_strength"].max() * 0.01,
              bar.get_y() + bar.get_height() / 2,
              f"{val:.2f}", va="center", color="white", fontsize=8.5)

# Legend for sector-type colours
legend_d = [
    mpatches.Patch(color="#4FC3F7", label="Digital / ICT"),
    mpatches.Patch(color="#FFB74D", label="Manufacturing"),
    mpatches.Patch(color="#81C784", label="Business services"),
    mpatches.Patch(color="#F48FB1", label="Trade & transport"),
    mpatches.Patch(color="#CE93D8", label="Utilities & construction"),
    mpatches.Patch(color="#90A4AE", label="Other"),
]
ax_d.legend(handles=legend_d, fontsize=8, facecolor="#1e1f29",
            edgecolor="#444455", labelcolor="white", loc="lower right")

ax_d.set_xlabel(
    "Total supply-chain strength (sum of in + out Leontief coefficients)\n"
    "Higher value = more deeply integrated in global intermediate trade",
    fontsize=9,
)
ax_d.set_title(
    "Top 15 Italian Sectors by Supply-Chain Participation (2021)\n"
    "These are the sectors where a digitalisation gap has the highest potential spill-over impact.\n"
    "Cross-reference with Fig A to identify which of these are also double bottlenecks.",
    fontsize=11, color="white", fontweight="bold", pad=12, loc="left",
)

plt.tight_layout()
fig_d.savefig(OUT_FIG / "figD_hub_ranking_2021.png",
              dpi=150, bbox_inches="tight", facecolor="#1e1f29")
plt.close(fig_d)
print(f"Saved {OUT_FIG / 'figD_hub_ranking_2021.png'}")

print("\nPipeline complete.")
