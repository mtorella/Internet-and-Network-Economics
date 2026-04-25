from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TABLES = ROOT / "outputs" / "tables"
OUT_FILE = ROOT / "dashboard" / "data.bundle.js"
YEARS = list(range(2016, 2022))

SECTOR_NAMES = {
    "A01": "Crop & animal production",
    "A02": "Forestry & logging",
    "A03": "Fishing & aquaculture",
    "B05": "Coal mining",
    "B06": "Oil & gas extraction",
    "B07": "Metal ore mining",
    "B08": "Other mining & quarrying",
    "B09": "Mining support services",
    "C10T12": "Food, beverages & tobacco",
    "C13T15": "Textiles, apparel & leather",
    "C16": "Wood & wood products",
    "C17_18": "Paper & printing",
    "C19": "Coke & refined petroleum",
    "C20": "Chemicals",
    "C21": "Pharmaceuticals",
    "C22": "Rubber & plastics",
    "C23": "Non-metallic mineral products",
    "C24A": "Basic metals (ferrous)",
    "C24B": "Basic metals (non-ferrous)",
    "C25": "Fabricated metal products",
    "C26": "Computer & electronic products",
    "C27": "Electrical equipment",
    "C28": "Machinery & equipment",
    "C29": "Motor vehicles",
    "C301": "Ships & boats",
    "C302T309": "Other transport equipment",
    "C31T33": "Furniture & other manufacturing",
    "D": "Electricity & gas",
    "E": "Water supply & waste",
    "F": "Construction",
    "G": "Wholesale & retail trade",
    "H49": "Land transport",
    "H50": "Water transport",
    "H51": "Air transport",
    "H52": "Warehousing & logistics",
    "H53": "Postal & courier",
    "I": "Accommodation & food services",
    "J58T60": "Publishing & broadcasting",
    "J61": "Telecommunications",
    "J62_63": "IT & computer services",
    "K": "Financial & insurance",
    "L": "Real estate",
    "M": "Professional & scientific services",
    "N": "Administrative & support services",
    "O": "Public administration",
    "P": "Education",
    "Q": "Health & social work",
    "R": "Arts & entertainment",
    "S": "Other services",
}


def _f(val) -> float | None:
    """Return float or None, never NaN."""
    return None if pd.isna(val) else float(val)


def build_year(year: int) -> list[dict]:
    panel = pd.read_csv(TABLES / f"sector_panel_{year}.csv")
    rows = []
    for _, p in panel.iterrows():
        icio = str(p.get("icio_code", "")).strip()
        if not icio:
            continue
        rows.append({
            "icio_code": icio,
            "sector_name": SECTOR_NAMES.get(icio, icio),
            "pagerank_norm": _f(p.get("pagerank_norm")),
            "pagerank": _f(p.get("pagerank")),
            "dig_contribution": _f(p.get("dig_contribution")),
            "dig_contribution_norm": _f(p.get("dig_contribution_norm")),
            "dig_depth": _f(p.get("dig_depth")),
            "dig_depth_norm": _f(p.get("dig_depth_norm")),
        })
    return rows


def main() -> None:
    payload = {str(year): build_year(year) for year in YEARS}
    content = "window.DASHBOARD_BUNDLE = " + json.dumps(payload, separators=(",", ":")) + ";\n"
    OUT_FILE.write_text(content, encoding="utf-8")
    total = sum(len(v) for v in payload.values())
    print(f"Bundle written: {OUT_FILE}  ({total} rows across {len(YEARS)} years)")


if __name__ == "__main__":
    main()
