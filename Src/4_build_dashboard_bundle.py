from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TABLES = ROOT / "outputs" / "tables"
OUT_FILE = ROOT / "dashboard" / "data.bundle.js"
YEARS = list(range(2016, 2022))


def build_year(year: int) -> list[dict]:
    panel = pd.read_csv(TABLES / f"sector_panel_{year}.csv")

    rows: list[dict] = []
    for _, p in panel.iterrows():
        icio = str(p.get("icio_code", "")).strip()
        if not icio:
            continue

        rows.append(
            {
                "icio_code": icio,
                "pagerank_norm": None if pd.isna(p.get("pagerank_norm")) else float(p.get("pagerank_norm")),
                "pagerank": None if pd.isna(p.get("pagerank")) else float(p.get("pagerank")),
                "ict_share": None if pd.isna(p.get("ict_share")) else float(p.get("ict_share")),
                "ict_share_norm": None if pd.isna(p.get("ict_share_norm")) else float(p.get("ict_share_norm")),
                "dig_intensity": None if pd.isna(p.get("dig_intensity")) else float(p.get("dig_intensity")),
                "dig_intensity_norm": None if pd.isna(p.get("dig_intensity_norm")) else float(p.get("dig_intensity_norm")),
            }
        )

    return rows


def main() -> None:
    payload = {str(year): build_year(year) for year in YEARS}
    content = "window.DASHBOARD_BUNDLE = " + json.dumps(payload, separators=(",", ":")) + ";\n"
    OUT_FILE.write_text(content, encoding="utf-8")
    print(f"Bundle written: {OUT_FILE}")


if __name__ == "__main__":
    main()
