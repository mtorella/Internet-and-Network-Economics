from pathlib import Path
import pandas as pd
from utils.helpers import extract_zblock
from utils.constants import NACE_EXCLUDED

# Paths and constants
ROOT = Path(__file__).resolve().parent.parent
GROWTH_PATH = ROOT / "data" / "raw" / "growth accounts.csv"
INTANGIBLE_PATH = ROOT / "data" / "raw" / "intangibles analytical.csv"
PROCESSED_DIR = ROOT / "data" / "processed"
YEARS = list(range(2016, 2022))
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

BASE_COLS = ["nace_r2_code", "geo_code", "nace_r2_name", "geo_name", "year", "var", "value"]
KEY_COLS = ["geo_code", "nace_r2_code", "geo_name", "nace_r2_name"]
REQUIRED_COLS = ["nace_r2_code", "geo_code", "year", "var"]
EXCLUDE = set(NACE_EXCLUDED.keys())

# --- Growth accounts import and cleaning ---
print("Loading and processing growth accounts...\n")
df_growth = pd.read_csv(GROWTH_PATH, low_memory=False)
df_growth["year"] = pd.to_numeric(df_growth["year"], errors="coerce")
df_growth = df_growth[BASE_COLS].dropna(subset=REQUIRED_COLS)
df_growth["year"] = df_growth["year"].astype(int)
print("Growth accounts dataset loaded with shape:", df_growth.shape)

# ---  Intangibles analytical dataset import and cleaning ---
print("Loading and processing intangibles analytical dataset...\n")
df_intangibles = pd.read_csv(INTANGIBLE_PATH, low_memory=False)
if "Unnamed: 0" in df_intangibles.columns:
    df_intangibles = df_intangibles.drop(columns=["Unnamed: 0"])
df_intangibles["year"] = pd.to_numeric(df_intangibles["year"], errors="coerce")
df_intangibles = df_intangibles.dropna(subset=["nace_r2_code", "geo_code", "year"])
df_intangibles["year"] = df_intangibles["year"].astype(int)
print("Intangibles analytical dataset loaded with shape:", df_intangibles.shape)

# --- Merge the two digitalisation datasets ---
print("\nBuilding digitalisation panel for Italy...\n")
for year in YEARS:

    # Filter growth accounts to the year and to Italy
    year_growth_df = df_growth[(df_growth["year"] == year) & (df_growth["geo_code"] == "IT")]
    if year_growth_df.empty:
        print(f"{year}: no rows found, skipped")
        continue

    # Pivot to wide format: one row per (geo_code, nace_r2_code) with var columns as separate columns
    df_growth_wide= year_growth_df.pivot_table(index=KEY_COLS, columns="var", values="value", aggfunc="mean").reset_index()
    df_growth_wide.columns.name = None
    df_growth_wide = df_growth_wide.drop_duplicates(subset=KEY_COLS)

    # Extract digital capital contribution (flow measure) if available
    if "VACon_Soft_DB" in df_growth_wide.columns:
        df_growth_wide["dig_contribution"] = df_growth_wide["VACon_Soft_DB"]

    # Filter intangibles analytical to the year and to Italy
    year_intangibles_df = df_intangibles[(df_intangibles["year"] == year) & (df_intangibles["geo_code"] == "IT")].copy()
    if year_intangibles_df.empty:
        print(f"{year}: no rows found, skipped")
        continue

    # Compute digital capital depth: software/database stock relative to value added
    year_intangibles_df["dig_depth"] = year_intangibles_df["K_Soft_DB"] / year_intangibles_df["VA_CP"].replace(0, float("nan"))

    # Compute missing values
    n_missing = year_intangibles_df["dig_depth"].isna().sum()
    if n_missing > 0:
        print(f"{year}: computed digital capital depth with {n_missing} missing values")
    
    # Merge these two datasets through the NACE-ICIO crosswalk
    df_digitalisation = df_growth_wide.merge(year_intangibles_df, on="nace_r2_code", how="outer", suffixes=("", "_r"))
    for col in ["geo_code", "geo_name", "nace_r2_name"]:
        if col + "_r" in df_digitalisation.columns:
            df_digitalisation[col] = df_digitalisation[col].combine_first(df_digitalisation.pop(col + "_r"))
    
    # Select only NACE codes and digitalisation variables
    df_digitalisation = df_digitalisation[KEY_COLS + ["dig_contribution", "dig_depth"]]

    # Add year column for clarity
    df_digitalisation["year"] = year

    # Remove rows with excluded NACE codes
    df_digitalisation = df_digitalisation[~df_digitalisation["nace_r2_code"].isin(EXCLUDE)]

    # Store the result for this year to CSV
    out_path = PROCESSED_DIR / f"digitalisation_{year}.csv"
    df_digitalisation.to_csv(out_path, index=False)
    print(f"{year}: digitalisation panel saved with {len(df_digitalisation)} rows — {out_path.name}")

# --- ICIO: extract Z-block for each year ---
print("\nExtracting Z-block from ICIO tables...\n")

for year in YEARS:
    icio_path = ROOT / "data" / "raw" / f"{year}.csv"
    if not icio_path.exists():
        print(f"{year}: {icio_path.name} not found — skipped")
        continue

    raw = pd.read_csv(icio_path, index_col=0, low_memory=False)
    z_block = extract_zblock(raw)

    if z_block.empty:
        print(f"{year}: Z-block extraction failed — skipped")
        continue

    z_block.to_parquet(PROCESSED_DIR / f"icio_zblock_{year}.parquet")
    print(f"{year}: saved icio_zblock_{year}.parquet — {z_block.shape}")

print("\nPreprocessing complete. Processed files saved to 'data/processed/'.")