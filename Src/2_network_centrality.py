"""
network_centrality.py
=====================
For each year in 2016-2021: loads the ICIO Z-block, builds a global
weighted directed graph of technical coefficients, computes four centrality
measures for every node, and stores the Italian-sector rows in a panel
saved to data/processed/centrality_panel.csv.

Centrality measures:
    pagerank     — weighted PageRank (stationary distribution of random walk)
    betweenness  — normalised betweenness centrality (k=500 approximation)
    in_strength  — sum of incoming edge weights
    out_strength — sum of outgoing edge weights
"""

from pathlib import Path
import networkx as nx
import pandas as pd
from utils.helpers import build_coefficient_graph

ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT / "data" / "processed"

YEARS = list(range(2016, 2022))

# Iterate over years, build graph, compute centrality, and store Italian sectors
for year in YEARS:
    # Load Z-block and build graph
    zblock_path = PROCESSED_DIR / f"icio_zblock_{year}.parquet"
    print(f"{year}: loading Z-block ...", end=" ", flush=True)
    z_block = pd.read_parquet(zblock_path)
    G = build_coefficient_graph(z_block)
    print(f"{G.number_of_nodes():,} nodes, {G.number_of_edges():,} edges")

    # Compute centrality measures
    print(f"computing centrality ...", flush=True)
    pagerank = nx.pagerank(G, weight="weight")
    betweenness = nx.betweenness_centrality(G, weight="weight", normalized=True, k=min(500, G.number_of_nodes()))
    in_str = {n: sum(d["weight"] for _, _, d in G.in_edges(n, data=True)) for n in G.nodes()}
    out_str = {n: sum(d["weight"] for _, _, d in G.out_edges(n, data=True)) for n in G.nodes()}

    # Extract Italian sectors and store in DataFrame
    ita_nodes = [n for n in G.nodes() if n.startswith("ITA_")]
    df_year = pd.DataFrame({
        "icio_code": [n.split("_", 1)[1] for n in ita_nodes],
        "pagerank": [pagerank[n] for n in ita_nodes],
        "betweenness": [betweenness[n] for n in ita_nodes],
        "in_strength": [in_str[n] for n in ita_nodes],
        "out_strength": [out_str[n] for n in ita_nodes],
    })
    df_year["year"] = year

    # Store in a file
    out_path = PROCESSED_DIR / f"centrality_{year}.csv"
    df_year.to_csv(out_path, index=False)
    print(f"done — {len(df_year)} Italian sectors saved to {out_path.name}")

print("Centrality computation complete for all years.")