from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
YEAR = 2021
THRESHOLD_MUSD = 50.0
BETWEENNESS_K = 300

ROOT = Path(__file__).resolve().parent.parent
DATA_PREP = ROOT / "data" / "prepared"
DATA_PROC = ROOT / "data" / "processed"
OUT_FIG = ROOT / "outputs" / "figures"
OUT_TBL = ROOT / "outputs" / "tables"

OUT_FIG.mkdir(parents=True, exist_ok=True)
OUT_TBL.mkdir(parents=True, exist_ok=True)

# Dark style palette
BG = "#0f1117"
PANEL = "#1a1d27"
GRID = "#333344"
TEXT = "#cccccc"
AXIS = "#888899"


# NACE -> ICIO crosswalk (as used in project prototype)
NACE_TO_ICIO = {
    "A": "A01",
    "B": "B07",
    "C10-C12": "C10T12",
    "C13-C15": "C13T15",
    "C16-C18": "C17_18",
    "C16": "C16",
    "C19": "C19",
    "C20": "C20",
    "C20-C21": "C20",
    "C21": "C21",
    "C22-C23": "C22",
    "C24-C25": "C25",
    "C26": "C26",
    "C26-C27": "C26",
    "C27": "C27",
    "C28": "C28",
    "C29-C30": "C29",
    "C31-C33": "C31T33",
    "D": "D",
    "D-E": "D",
    "E": "E",
    "F": "F",
    "G": "G",
    "G45": "G",
    "G46": "G",
    "G47": "G",
    "H": "H49",
    "H49": "H49",
    "H50": "H50",
    "H51": "H51",
    "H52": "H52",
    "H53": "H53",
    "I": "I",
    "J": "J62_63",
    "J58-J60": "J58T60",
    "J61": "J61",
    "J62-J63": "J62_63",
    "K": "K",
    "L": "L",
    "L68A": "L",
    "M": "M",
    "M-N": "M",
    "N": "N",
    "O": "O",
    "O-Q": "O",
    "P": "P",
    "Q": "Q",
    "Q86": "Q",
    "R": "R",
    "R-S": "R",
    "S": "S",
}

SECTOR_LABELS = {
    "A01": "Agriculture",
    "A02": "Forestry",
    "A03": "Fishing",
    "B05": "Coal mining",
    "B06": "Oil & gas",
    "B07": "Metal ores mining",
    "B08": "Other mining",
    "B09": "Mining support",
    "C10T12": "Food & beverages",
    "C13T15": "Textiles & apparel",
    "C16": "Wood products",
    "C17_18": "Paper & printing",
    "C19": "Coke & petroleum",
    "C20": "Chemicals",
    "C21": "Pharmaceuticals",
    "C22": "Rubber & plastics",
    "C23": "Non-metallic minerals",
    "C24A": "Basic metals (ferrous)",
    "C24B": "Basic metals (non-ferrous)",
    "C25": "Fabricated metals",
    "C26": "Electronics & ICT",
    "C27": "Electrical equipment",
    "C28": "Machinery",
    "C29": "Motor vehicles",
    "C301": "Shipbuilding",
    "C302T309": "Other transport equip.",
    "C31T33": "Furniture & repair",
    "D": "Electricity & gas",
    "E": "Water & waste",
    "F": "Construction",
    "G": "Wholesale & retail",
    "H49": "Land transport",
    "H50": "Water transport",
    "H51": "Air transport",
    "H52": "Warehousing",
    "H53": "Postal services",
    "I": "Accommodation & food",
    "J58T60": "Publishing & media",
    "J61": "Telecommunications",
    "J62_63": "IT services",
    "K": "Financial services",
    "L": "Real estate",
    "M": "Professional services",
    "N": "Administrative services",
    "O": "Public admin",
    "P": "Education",
    "Q": "Health & social work",
    "R": "Arts & entertainment",
    "S": "Other services",
    "T": "Household services",
}


def style_ax(ax: plt.Axes) -> None:
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


# -----------------------------------------------------------------------------
# Load and inspect all required 2021 files first
# -----------------------------------------------------------------------------
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
labels = z_block.index.astype(str).tolist()
Z = z_block.to_numpy(dtype=np.float64)
np.fill_diagonal(Z, 0.0)

src_idx, tgt_idx = np.where(Z > THRESHOLD_MUSD)
weights = Z[src_idx, tgt_idx]

G = nx.DiGraph()
G.add_nodes_from(labels)
G.add_weighted_edges_from(
    (labels[s], labels[t], float(w)) for s, t, w in zip(src_idx, tgt_idx, weights)
)

print(
    f"Graph built with threshold ${THRESHOLD_MUSD:.0f}M: "
    f"nodes={G.number_of_nodes():,}, edges={G.number_of_edges():,}"
)

pagerank = nx.pagerank(G, weight="weight")
betweenness = nx.betweenness_centrality(
    G,
    k=BETWEENNESS_K,
    normalized=True,
    weight="weight",
    seed=42,
)
in_strength = dict(G.in_degree(weight="weight"))
out_strength = dict(G.out_degree(weight="weight"))

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
centrality_df["total_strength"] = centrality_df["in_strength"] + centrality_df["out_strength"]

ita_centrality = (
    centrality_df[centrality_df["country"] == "ITA"]
    .copy()
    .reset_index(drop=True)
)
print(f"Italian sectors in centrality table: {len(ita_centrality)}")

# Save centrality table for later use
centrality_df.to_csv(OUT_TBL / "centrality_2021.csv", index=False)

# -----------------------------------------------------------------------------
# Part 2 — Composite digitalisation measure
# -----------------------------------------------------------------------------
print("\nPART 2 — Composite digitalisation")

growth_it = growth_df[growth_df["geo_code"] == "IT"].copy()
growth_it["icio_code"] = growth_it["nace_r2_code"].map(NACE_TO_ICIO)
growth_it = growth_it.dropna(subset=["icio_code", "ict_share"])

ict_by_sector = (
    growth_it.groupby("icio_code", as_index=False)["ict_share"]
    .mean()
    .rename(columns={"ict_share": "ict_share_raw"})
)

intang_it = intang_df[intang_df["geo_code"] == "IT"].copy()
if "year" in intang_it.columns:
    intang_it = intang_it[intang_it["year"] == YEAR].copy()

intang_it["dig_intensity"] = (
    intang_it["I_Soft_DB"].fillna(0.0) + intang_it["I_RD"].fillna(0.0)
) / intang_it["VA_CP"].replace(0, np.nan)

intang_it["icio_code"] = intang_it["nace_r2_code"].map(NACE_TO_ICIO)
intang_it = intang_it.dropna(subset=["icio_code", "dig_intensity"])

dig_by_sector = (
    intang_it.groupby("icio_code", as_index=False)["dig_intensity"]
    .mean()
    .rename(columns={"dig_intensity": "dig_intensity_raw"})
)

df_composite = ict_by_sector.merge(dig_by_sector, on="icio_code", how="inner")

matched = len(df_composite)
lost_ict = len(ict_by_sector) - matched
lost_dig = len(dig_by_sector) - matched
print(f"Matched sectors: {matched}")
print(f"Lost from ICT side: {lost_ict}")
print(f"Lost from Intangibles side: {lost_dig}")

df_composite["ict_share_norm"] = minmax(df_composite["ict_share_raw"])
df_composite["dig_intensity_norm"] = minmax(df_composite["dig_intensity_raw"])
df_composite["composite_equal"] = (
    df_composite["ict_share_norm"] + df_composite["dig_intensity_norm"]
) / 2.0
df_composite["composite_weighted"] = (
    0.4 * df_composite["dig_intensity_norm"]
    + 0.6 * df_composite["ict_share_norm"]
)

df_composite.to_csv(OUT_TBL / "df_composite_2021.csv", index=False)
print(f"Saved {OUT_TBL / 'df_composite_2021.csv'}")


# -----------------------------------------------------------------------------
# Part 3 — Merge and classify double bottlenecks
# -----------------------------------------------------------------------------
print("\nPART 3 — Double bottleneck classification")

analysis_df = ita_centrality.merge(
    df_composite,
    left_on="sector",
    right_on="icio_code",
    how="inner",
)
analysis_df["sector_label"] = analysis_df["sector"].map(SECTOR_LABELS).fillna(analysis_df["sector"])


def classify_variant(df: pd.DataFrame, digital_col: str) -> pd.Series:
    pr_cut = df["pagerank"].quantile(0.60)
    dig_cut = df[digital_col].quantile(0.40)
    return (df["pagerank"] >= pr_cut) & (df[digital_col] <= dig_cut)


analysis_df["variant_a_dig_only"] = classify_variant(analysis_df, "dig_intensity_norm")
analysis_df["variant_b_composite_equal"] = classify_variant(analysis_df, "composite_equal")
analysis_df["variant_c_composite_weighted"] = classify_variant(analysis_df, "composite_weighted")
analysis_df["robust"] = (
    analysis_df["variant_a_dig_only"]
    & analysis_df["variant_b_composite_equal"]
    & analysis_df["variant_c_composite_weighted"]
)

robustness_cols = [
    "sector",
    "sector_label",
    "variant_a_dig_only",
    "variant_b_composite_equal",
    "variant_c_composite_weighted",
    "robust",
]
robustness = analysis_df[robustness_cols].sort_values(["robust", "sector"], ascending=[False, True])

print("\nRobustness check table:")
print(robustness.to_string(index=False))

robustness.to_csv(OUT_TBL / "robustness_check_2021.csv", index=False)
print(f"Saved {OUT_TBL / 'robustness_check_2021.csv'}")


# -----------------------------------------------------------------------------
# Part 4 — Visualisations
# -----------------------------------------------------------------------------
print("\nPART 4 — Visualisations")

# Figure 0: network spine
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


def foreign_positions(country_list: list[str], x_base: float) -> dict[str, tuple[float, float]]:
    pos: dict[str, tuple[float, float]] = {}
    if len(country_list) == 0:
        return pos
    band = (Y_MAX - Y_MIN) / len(country_list)
    for ci, country in enumerate(country_list):
        nodes = sorted(
            [
                n
                for n in G.nodes
                if n.startswith(f"{country}_")
                and any(n in (u, v) for u, v, _ in top_edges)
            ]
        )
        if not nodes:
            continue
        y_top = Y_MAX - ci * band
        y_bot = y_top - band * 0.85
        ys = np.linspace(y_top, y_bot, len(nodes))
        for node, y in zip(nodes, ys):
            pos[node] = (x_base, float(y))
    return pos


left_pos = foreign_positions(left_countries, X_LEFT)
right_pos = foreign_positions(right_countries, X_RIGHT)
all_pos = {**ita_pos, **left_pos, **right_pos}

fig0, ax0 = plt.subplots(figsize=(20, 24), facecolor=BG)
ax0.set_facecolor(BG)
ax0.axis("off")


def draw_arc(ax: plt.Axes, p0: tuple[float, float], p1: tuple[float, float], color: str, alpha: float, lw: float) -> None:
    x0, y0 = p0
    x1, y1 = p1
    bulge = 0.55 * abs(x1 - x0)
    cx = (x0 + x1) / 2 + (bulge if x1 > x0 else -bulge)
    cy = (y0 + y1) / 2
    t = np.linspace(0, 1, 80)
    bx = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t ** 2 * x1
    by = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t ** 2 * y1
    ax.plot(bx, by, color=color, alpha=alpha, lw=lw, solid_capstyle="round", zorder=1)


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
        edgecolors=AXIS,
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


def country_label_y(pos_dict: dict[str, tuple[float, float]], country: str) -> float:
    ys = [pos_dict[n][1] for n in pos_dict if n.startswith(f"{country}_")]
    return float(np.mean(ys)) if ys else 0.0


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
    facecolor=PANEL,
    edgecolor=GRID,
    labelcolor="white",
    framealpha=0.95,
    bbox_to_anchor=(0.01, 0.01),
)

ax0.set_title(
    f"Italy in the Global Supply Network ({YEAR})\n"
    "Centre: Italian sectors by PageRank  ·  Sides: top 10 partner countries  ·  Arcs: top 5% flows",
    fontsize=13,
    color="white",
    fontweight="bold",
    pad=16,
)
ax0.set_xlim(-2.0, 2.0)
ax0.set_ylim(-1.12, 1.12)
plt.tight_layout()
fig0.savefig(OUT_FIG / "fig0_network_spine_2021.png", dpi=150, bbox_inches="tight", facecolor=BG)
plt.close(fig0)
print(f"Saved {OUT_FIG / 'fig0_network_spine_2021.png'}")


# Figure 1: Top-15 by total strength
fig1, ax1 = plt.subplots(figsize=(12, 7), facecolor=BG)
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
ax1.set_yticklabels(top15["label"], fontsize=10, color=TEXT)
ax1.set_xlabel("Total IO flow strength (billion USD)", fontsize=10)
ax1.set_title(
    f"Italian Sector Hubs — Total IO Flow Strength ({YEAR})",
    fontsize=13,
    color="white",
    fontweight="bold",
    pad=12,
)
ax1.invert_yaxis()

for bar, val in zip(bars, top15["total_strength"] / 1000.0):
    ax1.text(float(val) + 0.2, bar.get_y() + bar.get_height() / 2, f"${val:.1f}B", va="center", color=TEXT, fontsize=8)

plt.tight_layout()
fig1.savefig(OUT_FIG / "fig1_hub_ranking_2021.png", dpi=150, bbox_inches="tight", facecolor=BG)
plt.close(fig1)
print(f"Saved {OUT_FIG / 'fig1_hub_ranking_2021.png'}")


# Figure 2: PageRank vs Betweenness
fig2, ax2 = plt.subplots(figsize=(10, 7), facecolor=BG)
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
    ax2.annotate(lab, (row["betweenness"] * 100, row["pagerank"] * 100), xytext=(5, 3), textcoords="offset points", fontsize=7.5, color=TEXT)

cb = plt.colorbar(sc, ax=ax2, pad=0.01)
cb.set_label("Total flow strength (M USD)", color=AXIS, fontsize=9)
cb.ax.yaxis.set_tick_params(color=AXIS)
plt.setp(cb.ax.yaxis.get_ticklabels(), color=AXIS)

ax2.set_xlabel("Betweenness centrality (%)", fontsize=10)
ax2.set_ylabel("PageRank (%)", fontsize=10)
ax2.set_title(
    f"Centrality Map — Italian Sectors ({YEAR})",
    fontsize=13,
    color="white",
    fontweight="bold",
    pad=10,
)

plt.tight_layout()
fig2.savefig(OUT_FIG / "fig2_centrality_map_2021.png", dpi=150, bbox_inches="tight", facecolor=BG)
plt.close(fig2)
print(f"Saved {OUT_FIG / 'fig2_centrality_map_2021.png'}")


# Figure 3: 1x3 panel (PageRank vs digitalisation variants)
panel_variants = [
    ("dig_intensity_norm", "Variant A: Dig Intensity"),
    ("composite_equal", "Variant B: Composite Equal"),
    ("composite_weighted", "Variant C: Composite Weighted"),
]

fig3, axes = plt.subplots(1, 3, figsize=(24, 7), facecolor=BG)
for ax, (xcol, title) in zip(axes, panel_variants):
    style_ax(ax)
    x = analysis_df[xcol]
    y = analysis_df["pagerank"]
    s = analysis_df["total_strength"] / analysis_df["total_strength"].max() * 700 + 40

    ax.scatter(
        x,
        y,
        s=s,
        c=[sector_type_color(sec) for sec in analysis_df["sector"]],
        alpha=0.85,
        edgecolors="white",
        linewidths=0.5,
        zorder=3,
    )

    med_x = x.median()
    med_y = y.median()
    ax.axvline(med_x, color="white", alpha=0.20, linewidth=1, linestyle="--")
    ax.axhline(med_y, color="white", alpha=0.20, linewidth=1, linestyle="--")

    for _, row in analysis_df.iterrows():
        ax.annotate(
            row["sector_label"],
            xy=(row[xcol], row["pagerank"]),
            xytext=(4, 3),
            textcoords="offset points",
            fontsize=7,
            color=TEXT,
            alpha=0.9,
        )

    ax.set_xlabel("Digitalisation score (0-1)", fontsize=10)
    ax.set_ylabel("PageRank", fontsize=10)
    ax.set_title(title, fontsize=12, color="white", fontweight="bold")

fig3.suptitle(
    f"Centrality vs Digitalisation — Italy ({YEAR})\nBubble size = total strength",
    fontsize=14,
    color="white",
    fontweight="bold",
)
plt.tight_layout(rect=[0, 0.02, 1, 0.95])
fig3.savefig(OUT_FIG / "fig3_centrality_vs_digitalisation_panel_2021.png", dpi=150, bbox_inches="tight", facecolor=BG)
plt.close(fig3)
print(f"Saved {OUT_FIG / 'fig3_centrality_vs_digitalisation_panel_2021.png'}")

print("\nPipeline complete.")