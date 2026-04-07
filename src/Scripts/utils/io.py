"""I/O helpers — loading and saving CSV and Parquet files."""

from pathlib import Path
import pandas as pd

def load_csv(path: Path) -> pd.DataFrame:
    """Load a CSV file into a DataFrame and print a summary."""
    df = pd.read_csv(path)
    print(f"Loaded data from {path.name}: {len(df):,} rows, {len(df.columns):,} columns")
    return df

def ensure_dir(path: Path) -> None:
    """Ensure a directory exists, creating it if necessary."""
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        print(f"Created output folder: {path}")
    else:
        print(f"Output folder already exists: {path}")

def save_csv(df: pd.DataFrame, path: Path) -> None:
    """Save a DataFrame to CSV and print a summary."""
    df.to_csv(path, index=False)
    print(f"Wrote {len(df):,} rows, {len(df.columns):,} columns -> {path.name}")
