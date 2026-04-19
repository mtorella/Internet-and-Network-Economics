from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from utils.constants import ICIO_TO_NACE

# --- Paths ---
ROOT = Path(__file__).resolve().parent.parent
DATA_PROC = ROOT / "data" / "processed"
OUT_FIG = ROOT / "outputs" / "figures"
OUT_TBL = ROOT / "outputs" / "tables"
OUT_FIG.mkdir(parents=True, exist_ok=True)
OUT_TBL.mkdir(parents=True, exist_ok=True)

# --- Style ---
sns.set_style("whitegrid")
plt.rcParams["figure.figsize"] = (12, 6)
plt.rcParams["font.size"] = 11

YEARS = list(range(2016, 2022))

# Loop over years, load centrality and digitalisation data, and merge into a panel
data_frames = {}
for year in YEARS:
    # Load centrality data
    centrality_path = DATA_PROC / f"centrality_{year}.csv"
    centrality_df = pd.read_csv(centrality_path)
    # Load digitalisation data
    digital_path = DATA_PROC / f"digitalisation_{year}.csv"
    digital_df = pd.read_csv(digital_path)

    # Create a new column in centrality for NACE codes by mapping ICIO codes
    centrality_df["nace_r2_code"] = centrality_df["icio_code"].map(ICIO_TO_NACE)
    # Merge on NACE code, make sure column with the same name are not duplicated
    merged_df = pd.merge(centrality_df, digital_df, left_on="nace_r2_code", right_on="nace_r2_code", how="inner", suffixes=("", "_dig"))
    # Drop any duplicate columns that may have been created during the merge
    for col in merged_df.columns:
        if col.endswith("_dig"):
            merged_df = merged_df.drop(columns=[col])
    # Compute how many sectors are in this year’s merged dataset
    print(f"{year}: merged dataset has {len(merged_df)} sectors")
    data_frames[year] = merged_df

panel = pd.concat(data_frames.values(), ignore_index=True)

PAIRS = [
    ("ict_share_norm", "ICT capital share (norm.)"),
    ("dig_intensity_norm", "Digital intensity (norm.)"),
]

BAR_PAIRS = [
    ("ict_share", "ICT capital share"),
    ("dig_intensity", "Digital intensity"),
]

# ── Figure 1: Bar charts ───────────────────────────────────────────────────
for year in YEARS:
    df = panel[panel["year"] == year].copy()
    if df.empty:
        continue

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle(f"Top 10 Sectors by Digitalisation — {year}", fontsize=13, fontweight="bold")

    for ax, (col, col_label) in zip(axes, BAR_PAIRS):
        sub = df.dropna(subset=[col]).nlargest(10, col).sort_values(col)
        ax.barh(sub["icio_code"], sub[col], color="steelblue", edgecolor="white")
        ax.set_xlabel(col_label)
        ax.set_title(f"Top 10 — {col_label}")

    fig.tight_layout()
    fig.savefig(OUT_FIG / f"fig_bars_{year}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"fig_bars_{year}.png saved")


# ── Figure 3: Spearman correlation over time ──────────────────────────────
def spearman_ci(x: pd.Series, y: pd.Series, alpha: float = 0.05):
    mask = x.notna() & y.notna()
    x, y = x[mask], y[mask]
    n = len(x)
    if n < 4:
        return np.nan, np.nan, np.nan
    r, _ = stats.spearmanr(x, y)
    z = np.arctanh(r)
    se = 1.0 / np.sqrt(n - 3)
    z_crit = stats.norm.ppf(1 - alpha / 2)
    return r, np.tanh(z - z_crit * se), np.tanh(z + z_crit * se)


corr_records = []
for year in YEARS:
    df = panel[panel["year"] == year]
    for col, _ in PAIRS:
        r, lo, hi = spearman_ci(df["pagerank_norm"], df[col])
        corr_records.append({"year": year, "metric": col, "r": r, "ci_lo": lo, "ci_hi": hi})

corr_df = pd.DataFrame(corr_records)

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle("Spearman Rank Correlation over Time (2016–2021)", fontsize=13, fontweight="bold")

for ax, (col, title) in zip(axes, PAIRS):
    sub = corr_df[corr_df["metric"] == col].sort_values("year")
    ax.plot(sub["year"], sub["r"], marker="o", color="steelblue", linewidth=1.8)
    ax.fill_between(sub["year"], sub["ci_lo"], sub["ci_hi"], alpha=0.2, color="steelblue", label="95% CI")
    ax.axhline(0, color="grey", linestyle="--", linewidth=0.8)
    ax.set_xlabel("Year")
    ax.set_ylabel("Spearman r")
    ax.set_title(f"PageRank vs {title}")
    ax.set_xticks(YEARS)
    ax.legend(fontsize=9)

fig.tight_layout()
fig.savefig(OUT_FIG / "fig_correlation.png", dpi=300, bbox_inches="tight")
plt.close(fig)
print("fig_correlation.png saved")


# ── Figure 4: Quadrant plots ──────────────────────────────────────────────
QUADRANT_COLORS = {
    "HH": "#4e9a8c",
    "HL": "#d95f5f",
    "LH": "#7bafd4",
    "LL": "#d4a96a",
}
QUADRANT_LABELS = {
    "HH": "High centrality / High digital",
    "HL": "High centrality / Low digital",
    "LH": "Low centrality / High digital",
    "LL": "Low centrality / Low digital",
}


# Fixed split at 0.5: midpoint of the [0,1] min-max scale.
# Using the mean would shift the threshold with the distribution each year,
# making quadrant membership incomparable across years.
QUADRANT_THRESHOLD = 0.5


def assign_quadrant(row, col):
    h_dig = row[col] >= QUADRANT_THRESHOLD
    h_cen = row["pagerank_norm"] >= QUADRANT_THRESHOLD
    if h_cen and h_dig:
        return "HH"
    if h_cen and not h_dig:
        return "HL"
    if not h_cen and h_dig:
        return "LH"
    return "LL"


for year in YEARS:
    df = panel[panel["year"] == year].copy()
    if df.empty:
        continue

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle(f"Centrality–Digitalisation Quadrants — {year}", fontsize=13, fontweight="bold")

    for ax, (col, col_label) in zip(axes, PAIRS):
        sub = df.dropna(subset=["pagerank_norm", col]).copy()
        sub["quadrant"] = sub.apply(assign_quadrant, axis=1, col=col)

        x0 = sub[col].min() - 0.05
        x1 = sub[col].max() + 0.05
        y0 = sub["pagerank_norm"].min() - 0.001
        y1 = sub["pagerank_norm"].max() + 0.001
        ax.fill_betweenx([QUADRANT_THRESHOLD, y1], x0, QUADRANT_THRESHOLD, color=QUADRANT_COLORS["HL"], alpha=0.08)
        ax.fill_betweenx([QUADRANT_THRESHOLD, y1], QUADRANT_THRESHOLD, x1, color=QUADRANT_COLORS["HH"], alpha=0.08)
        ax.fill_betweenx([y0, QUADRANT_THRESHOLD], x0, QUADRANT_THRESHOLD, color=QUADRANT_COLORS["LL"], alpha=0.08)
        ax.fill_betweenx([y0, QUADRANT_THRESHOLD], QUADRANT_THRESHOLD, x1, color=QUADRANT_COLORS["LH"], alpha=0.08)

        for quad, color in QUADRANT_COLORS.items():
            q_sub = sub[sub["quadrant"] == quad]
            ax.scatter(q_sub[col], q_sub["pagerank_norm"], s=55, color=color,
                       edgecolors="white", linewidths=0.4, label=QUADRANT_LABELS[quad], zorder=3)

        ax.axvline(QUADRANT_THRESHOLD, color="grey", linestyle="--", linewidth=0.9, alpha=0.7)
        ax.axhline(QUADRANT_THRESHOLD, color="grey", linestyle="--", linewidth=0.9, alpha=0.7)

        for _, row in sub.iterrows():
            ax.annotate(row["icio_code"], xy=(row[col], row["pagerank_norm"]),
                        fontsize=7, xytext=(3, 3), textcoords="offset points")

        ax.set_xlabel(col_label)
        ax.set_ylabel("PageRank (norm.)")
        ax.set_title(col_label)
        ax.legend(fontsize=7, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_FIG / f"fig_quadrants_{year}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"fig_quadrants_{year}.png saved")


# ── Tables: per-year CSVs ─────────────────────────────────────────────────
TABLE_COLS = [
    "icio_code",
    "pagerank", "pagerank_norm", "betweenness", "betweenness_norm",
    "in_strength", "out_strength",
    "ict_share", "ict_share_norm",
    "dig_intensity", "dig_intensity_norm",
]

for year in YEARS:
    cols = [c for c in TABLE_COLS if c in panel.columns]
    df = panel[panel["year"] == year][cols].copy()
    if df.empty:
        continue
    df = df.sort_values("pagerank", ascending=False).reset_index(drop=True)
    out_path = OUT_TBL / f"sector_panel_{year}.csv"
    df.to_csv(out_path, index=False)
    print(f"sector_panel_{year}.csv saved — {len(df)} sectors")

print("\nAll outputs saved.")