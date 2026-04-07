from pathlib import Path
import pandas as pd

from utils.display import step, print_summary
from utils.io import load_csv, ensure_dir, save_csv
from utils.transforms import coerce_year_column, select_columns, drop_missing, finalize_year_dtype, pivot_to_wide, filter_year
from utils.icio import extract_zblock

# Paths and constants
ROOT          = Path(__file__).resolve().parent.parent.parent
RAW_PATH      = ROOT / "data" / "raw" / "growth accounts.csv"
PROCESSED_DIR = ROOT / "data" / "processed"
PREP_DIR      = ROOT / "data" / "prepared"
YEARS         = list(range(2016, 2023))

BASE_COLS     = ["nace_r2_code", "geo_code", "nace_r2_name", "geo_name", "year", "var", "value"]
KEY_COLS      = ["geo_code", "nace_r2_code", "geo_name", "nace_r2_name"]
REQUIRED_COLS = ["nace_r2_code", "geo_code", "year", "var"]

# PASS 1 — Growth accounts: pivot to wide and compute digital intensity
step("STEP 1 - Load growth accounts dataset")
df = load_csv(RAW_PATH)
df = coerce_year_column(df)
df = select_columns(df, BASE_COLS, [])
df = drop_missing(df, REQUIRED_COLS)
df = finalize_year_dtype(df)

ensure_dir(PROCESSED_DIR)

for year in YEARS:
    year_df = filter_year(df, year)
    if year_df.empty:
        print(f"  {year}: no rows found, skipped")
        continue

    wide = pivot_to_wide(year_df, index=KEY_COLS, col="var", val="value")
    wide = wide.drop_duplicates(subset=KEY_COLS)

    # ICT capital share: fraction of total capital services coming from ICT assets
    # CAPICT_QI = ICT capital services (volume index), CAP = total capital compensation
    if "CAPICT_QI" in wide.columns and "CAP" in wide.columns:
        wide["ict_share"] = wide["CAPICT_QI"] / wide["CAP"].replace(0, float("nan"))

    save_csv(wide, PROCESSED_DIR / f"growth_accounts_{year}_wide.csv")

# PASS 2 — ICIO: extract Z-block for each year
step("PASS 2 - Extract ICIO Z-blocks for each year")
ensure_dir(PREP_DIR)

for year in YEARS:
    icio_path = ROOT / "data" / "raw" / f"{year}.csv"
    if not icio_path.exists():
        print(f"{year}: {icio_path.name} not found — skipped")
        continue

    raw = pd.read_csv(icio_path, index_col=0, low_memory=False)

    # Extract Z-block
    z_block = extract_zblock(raw)
    if z_block.empty:
        print(f"{year}: Z-block extraction failed — skipped")
        continue
    save_csv(z_block, PREP_DIR / f"icio_zblock_{year}.csv")