"""Display helpers — console printing and plot/display configuration."""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Console helpers
def step(msg: str) -> None:
    """Print a formatted step header to the console."""
    print("\n" + "=" * 72)
    print(msg)
    print("=" * 72)

def print_summary(written_files: list[str], output_dir: str = None) -> None:
    """Print a summary of written files to the console."""
    print(f"Completed writing {len(written_files)} files into {output_dir or 'output directory'}:")
    for fname in written_files:
        print(f"  - {fname}")


# Environment setup helpers
def setup_display_options() -> None:
    """Apply standard pandas display options used across all scripts."""
    pd.set_option("display.max_columns", None)
    pd.set_option("display.max_rows", 120)
    pd.set_option("display.float_format", lambda x: f"{x:.4f}")


def setup_plot_style() -> None:
    """Apply standard seaborn / matplotlib style used across all scripts."""
    sns.set_style("whitegrid")
    plt.rcParams["figure.figsize"] = (12, 6)
    plt.rcParams["figure.dpi"] = 120
    plt.rcParams["font.size"] = 11
