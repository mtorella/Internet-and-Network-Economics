from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
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
