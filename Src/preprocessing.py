from pathlib import Path
import pandas as pd

# Paths and constants
ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = ROOT / "data" / "raw" / "growth accounts.csv"
PROCESSED_DIR = ROOT / "data" / "processed"
PREP_DIR = ROOT / "data" / "prepared"
YEARS = list(range(2016, 2023))

BASE_COLS = ["nace_r2_code", "geo_code", "nace_r2_name", "geo_name", "year", "var", "value"]
KEY_COLS = ["geo_code", "nace_r2_code", "geo_name", "nace_r2_name"]
REQUIRED_COLS = ["nace_r2_code", "geo_code", "year", "var"]

# Sector codes as they appear in the actual ICIO CSV files (OECD 2023/2025 edition)
ICIO_SECTOR_CODES = {
    "A01", "A02", "A03",
    "B05", "B06", "B07", "B08", "B09",
    "C10T12", "C13T15", "C16", "C17_18", "C19",
    "C20", "C21", "C22", "C23", "C24A", "C24B",
    "C25", "C26", "C27", "C28", "C29",
    "C301", "C302T309", "C31T33",
    "D", "E", "F", "G",
    "H49", "H50", "H51", "H52", "H53",
    "I", "J58T60", "J61", "J62_63",
    "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T",
}


def extract_zblock(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Isolate the Z-block from a raw ICIO DataFrame — square intermediate-transactions matrix."""
    intermediate_cols = [c for c in raw_df.columns if "_" in c and c.split("_", 1)[1] in ICIO_SECTOR_CODES]
    intermediate_rows = [r for r in raw_df.index if "_" in str(r) and str(r).split("_", 1)[1] in ICIO_SECTOR_CODES]
    return raw_df.loc[intermediate_rows, intermediate_cols]


# -----------------------------------------------------------------------------
# STEP 1 — Growth accounts: pivot to wide and compute ICT share
# -----------------------------------------------------------------------------
print("=" * 60)
print("STEP 1 — Load and process growth accounts")
print("=" * 60)

df = pd.read_csv(RAW_PATH, low_memory=False)
df["year"] = pd.to_numeric(df["year"], errors="coerce")
df = df[BASE_COLS].dropna(subset=REQUIRED_COLS)
df["year"] = df["year"].astype(int)

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

for year in YEARS:
    year_df = df[df["year"] == year]
    if year_df.empty:
        print(f"  {year}: no rows found, skipped")
        continue

    wide = year_df.pivot_table(index=KEY_COLS, columns="var", values="value", aggfunc="mean").reset_index()
    wide.columns.name = None
    wide = wide.drop_duplicates(subset=KEY_COLS)

    if "CAPICT_QI" in wide.columns and "CAP" in wide.columns:
        wide["ict_share"] = wide["CAPICT_QI"] / wide["CAP"].replace(0, float("nan"))

    wide.to_csv(PROCESSED_DIR / f"growth_accounts_{year}_wide.csv", index=False)
    print(f"  {year}: saved growth_accounts_{year}_wide.csv — {len(wide)} rows")

# -----------------------------------------------------------------------------
# STEP 2 — ICIO: extract Z-block for each year
# -----------------------------------------------------------------------------
print("=" * 60)
print("STEP 2 — Extract ICIO Z-blocks")
print("=" * 60)

PREP_DIR.mkdir(parents=True, exist_ok=True)

for year in YEARS:
    icio_path = ROOT / "data" / "raw" / f"{year}.csv"
    if not icio_path.exists():
        print(f"  {year}: {icio_path.name} not found — skipped")
        continue

    raw = pd.read_csv(icio_path, index_col=0, low_memory=False)
    z_block = extract_zblock(raw)

    if z_block.empty:
        print(f"  {year}: Z-block extraction failed — skipped")
        continue

    z_block.to_csv(PREP_DIR / f"icio_zblock_{year}.csv", index_label="")
    print(f"  {year}: saved icio_zblock_{year}.csv — {z_block.shape}")

# -----------------------------------------------------------------------------
# STEP 3 — Intangibles analytical dataset
# -----------------------------------------------------------------------------
print("=" * 60)
print("STEP 3 — Prepare intangibles dataset")
print("=" * 60)

intangible_path = ROOT / "data" / "raw" / "intangibles analytical.csv"

if not intangible_path.exists():
    print(f"  Intangibles file not found: {intangible_path.name}")
else:
    int_df = pd.read_csv(intangible_path, low_memory=False)
    if "Unnamed: 0" in int_df.columns:
        int_df = int_df.drop(columns=["Unnamed: 0"])
    int_df["year"] = pd.to_numeric(int_df["year"], errors="coerce")
    int_df = int_df.dropna(subset=["nace_r2_code", "geo_code", "year"])
    int_df["year"] = int_df["year"].astype(int)

    for year in YEARS:
        year_df = int_df[int_df["year"] == year]
        if year_df.empty:
            print(f"  {year}: no rows found, skipped")
            continue
        year_df.to_csv(PROCESSED_DIR / f"intangibles_analytical_{year}.csv", index=False)
        print(f"  {year}: saved intangibles_analytical_{year}.csv — {len(year_df)} rows")
