"""Full pipeline runner — executes all four steps in order:
  1. 1_preprocessing.py
  2. 2_network_centrality.py
  3. 3_analysis.py
  4. 4_build_dashboard_bundle.py
"""

import subprocess
import sys
from pathlib import Path

STEPS = ["1_preprocessing.py", "2_network_centrality.py", "3_analysis.py", "4_build_dashboard_bundle.py"]

SRC = Path(__file__).resolve().parent

def run_step(script: str) -> None:
    print(f"\n{'='*60}")
    print(f"Running {script}")
    print('='*60)
    result = subprocess.run([sys.executable, str(SRC / script)], cwd=SRC)
    if result.returncode != 0:
        print(f"\nPipeline aborted: {script} exited with code {result.returncode}.")
        sys.exit(result.returncode)

if __name__ == "__main__":
    for step in STEPS:
        run_step(step)
    print(f"\n{'='*60}")
    print("Pipeline complete.")
    print('='*60)
