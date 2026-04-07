"""Data transformation helpers — column coercion, pivoting, filtering."""

import pandas as pd


def coerce_year_column(df: pd.DataFrame) -> pd.DataFrame:
    """Parse year to numeric, coercing bad values to NaN, then cast to nullable Int64."""
    df = df.copy()
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    return df

def select_columns(df: pd.DataFrame, base_cols: list[str], optional_cols: list[str]) -> pd.DataFrame:
    """Keep base columns plus any optional ones that exist in the DataFrame."""
    present_optional = [c for c in optional_cols if c in df.columns]
    return df[base_cols + present_optional]

def drop_missing(df: pd.DataFrame, required_cols: list[str]) -> pd.DataFrame:
    before = len(df)
    df = df.dropna(subset=required_cols)
    print(f"Rows after dropping missing in {required_cols}: {before:,} → {len(df):,}")
    return df

def finalize_year_dtype(df: pd.DataFrame) -> pd.DataFrame:
    """Cast nullable Int64 year to plain int (safe after NaNs are removed)."""
    df = df.copy()
    df["year"] = df["year"].astype(int)
    return df

def pivot_to_wide(df: pd.DataFrame, index: list[str], col: str, val: str) -> pd.DataFrame:
    """Pivot a long DataFrame to wide format."""
    wide = df.pivot_table(
        index=index, columns=col, values=val, aggfunc="first"
    ).reset_index()
    wide.columns = [str(c) for c in wide.columns]
    return wide

def filter_year(df: pd.DataFrame, year: int) -> pd.DataFrame:
    """Filter DataFrame to a specific year."""
    return df[df["year"] == year].copy()
