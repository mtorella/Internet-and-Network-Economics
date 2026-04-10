# Internet and Network Economics — Group Project

## Digital Transition and Global Production-Network Structure

This project combines input-output economics and network analysis to study country-sector production interdependencies and their interaction with digital transition patterns. The empirical backbone is the OECD Inter-Country Input-Output (ICIO) table (2022 reference year) plus EUKLEMS Growth Accounts.

The full six-phase analytical pipeline is implemented in `Scripts/`, producing a global integrated dataset of 4,250 country-sector nodes with centrality, GVC participation, Markov-chain, community, and digital-intensity attributes.

---

## Project Structure

```
.
├── notebooks/
│   ├── 1_EDA_EUKLEMS.ipynb              # EUKLEMS exploration and panel preparation
│   ├── 2_EDA_IO_Matrix.ipynb            # ICIO exploration and Z-block extraction
│   └── 3_Network_Analysis.ipynb         # Network construction, diagnostics, baseline centralities
│
├── Scripts/
│   ├── 1_EDA_EUKLEMS.py                 # Phase 1 — EUKLEMS preparation and export
│   ├── 2_EDA_IO_Matrix.py               # Phase 2 — ICIO validation, Z-block, gross output, value added
│   ├── 3_Network_Analysis.py            # Phase 3 — DiGraph construction and baseline centrality
│   ├── 4_Digital_Intensity.py           # Phase 4 — ICT capital share, TFP growth, DT score
│   ├── 5_Integration.py                 # Phase 5 — Global join with diagnostics
│   └── 6_Network_Analysis_Extended.py   # Phase 6 — Leontief, GVC, Markov, communities, resilience
│
├── data/
│   ├── raw/
│   │   ├── 2022.csv                     # OECD ICIO table (2023 edition release, 4253×4737)
│   │   └── growth accounts.csv          # EUKLEMS Growth Accounts (2,467,044 rows, long format)
│   └── prepared/
│       ├── z_block.parquet              # 4250×4250 intermediate-transactions matrix
│       ├── gross_output.parquet         # Gross output vector (OUT row, 4,250 entries)
│       ├── value_added.parquet          # Value-added vector (VA row, 4,250 entries)
│       ├── euklems_wide.parquet         # EUKLEMS pivoted to wide format (all countries, all years)
│       ├── digital_intensity.parquet    # Panel: geo_code × nace_r2_code × year, ICT/TFP variables
│       ├── dt_scores.parquet            # Cross-section: DT score per (geo_code, nace_r2_code)
│       ├── global_integrated_cs.parquet # 4250-node cross-section with centrality + digital attrs
│       └── integrated_panel.parquet     # Panel join (all years 2000–2021)
│
├── outputs/
│   ├── figures/
│   │   ├── network_top_strength_subgraph.png
│   │   ├── network_degree_distribution.png
│   │   ├── ict_share_by_sector.png
│   │   ├── dt_score_vs_tfp.png
│   │   ├── dt_score_by_country.png
│   │   ├── leontief_multiplier_distributions.png
│   │   ├── gvc_position_map.png
│   │   ├── markov_vs_authority.png
│   │   ├── community_sizes.png
│   │   └── dt_score_vs_gvc_position.png
│   └── tables/
│       ├── network_centrality.csv           # 4250 nodes: degree, strength, HITS, betweenness
│       ├── digital_intensity_summary.csv    # DT scores with country/sector labels
│       ├── global_integrated_cs.csv         # Full 4250-node cross-section (all phases)
│       ├── network_extended.csv             # 4250 nodes: Markov, GVC, multipliers, community
│       ├── global_full_analysis.csv         # 4250 nodes: all 42 attributes merged
│       └── data_dictionary.csv             # Column-level documentation for integrated output
│
├── Resources/
│   └── WP5.25-Reshaping-global-value-chains.pdf
│
└── README.md
```

---

## Data Sources

| File | Source | Notes |
|------|--------|-------|
| `data/raw/2022.csv` | [OECD ICIO 2023 edition](https://www.oecd.org/sti/ind/inter-country-input-output-tables.htm) | Country-sector transaction matrix; reference year 2022 |
| `data/raw/growth accounts.csv` | [EUKLEMS & INTANProd](https://euklems-intanprod-llee.luiss.it/) | Industry-level productivity and factor indicators; 34 countries, 58 sectors |

Both files must be present in `data/raw/` before running scripts.

---

## Execution Order

Scripts must be run in numeric order; each script depends on outputs from the previous one.

```
python Scripts/1_EDA_EUKLEMS.py
python Scripts/2_EDA_IO_Matrix.py
python Scripts/3_Network_Analysis.py
python Scripts/4_Digital_Intensity.py
python Scripts/5_Integration.py
python Scripts/6_Network_Analysis_Extended.py
```

---

## Methodological Summary

### Network construction (Script 3)
A directed weighted graph is built from the $Z$ intermediate-transactions block. Edge $i \to j$ represents intermediate deliveries (USD million) from producing country-sector $i$ to using country-sector $j$. Self-loops are removed. Edges below the 99th-percentile weight threshold are dropped to retain only structurally significant flows, yielding a sparse graph of 4,250 nodes and ~104,000 edges.

Baseline centrality metrics exported per node: in/out degree, normalised in/out strength, HITS hub and authority scores, approximate betweenness centrality (k=500 random pivot nodes).

### Digital intensity (Script 4)
Three indicators are computed from EUKLEMS for all available country-sector-year combinations (34 countries, 58 sectors, 2000–2021):

- **ICT capital share** — `CAPICT_QI / CAP`: flow of ICT capital services as a fraction of total capital services.
- **ICT growth rate** — `Δlog(CAPICT_QI)`: year-on-year log change in ICT capital services.
- **TFP growth** — `Δlog(VATFP_I)`: year-on-year log change in the value-added TFP index.

A composite **Digital Transition (DT) score** is computed as an equal-weight Z-score average of the three indicators across all (country, sector) pairs. Reference year: 2022 (falling back to 2021, the last available year for most countries).

### Integration (Script 5)
ICIO nodes are joined to EUKLEMS digital indicators via a two-key concordance:

- **Country**: ISO3 (ICIO) → 2-letter EU code (EUKLEMS), with explicit handling of GRC→EL, GBR→UK, USA→US. Four pseudo-country splits (CN1, CN2, MX1, MX2) are excluded from the join but retained in network outputs.
- **Sector**: ICIO T-notation and underscore codes (e.g., `C10T12`, `J62_63`) are mapped to EUKLEMS hyphen notation (e.g., `C10-C12`, `J62-J63`) via a priority-based concordance that tries the exact code first and falls back to broader aggregates.

Join diagnostics (mandatory quality gate):
- 30 of 85 ICIO countries have EUKLEMS data (dataset coverage limit, not a join error).
- Sector match rate among country-covered nodes: 100%.
- 1,500 nodes matched; 820 of those have non-null DT score (VATFP_I sparseness accounts for the remainder).

### Extended network analysis (Script 6)
- **Leontief inverse** — approximated via Neumann series $L \approx I + A + A^2 + \cdots + A^{15}$. Only vector products are computed; the full 4,250×4,250 matrix is never materialised. Residual $\|(I-A)L\mathbf{1} - \mathbf{1}\|_\infty = 8.3 \times 10^{-5}$.
- **IO linkage indices** — backward multiplier (output triggered upstream per unit), forward multiplier (output triggered downstream per unit), VA content multiplier.
- **GVC participation** — simplified Koopman-Wang-Wei position index: $(f_{mult} / \bar{f}) - (b_{mult} / \bar{b})$; positive = net upstream supplier, negative = net downstream assembler.
- **Markov-chain centrality** — steady-state distribution $\pi$ of a random walk on the thresholded DiGraph. Dangling nodes (zero out-degree) redistribute their probability mass uniformly across all nodes at each iteration. Converged at iteration 1,169. Top node: USA_G (3.5%).
- **Community detection** — Louvain algorithm applied to the undirected projection of the largest weakly connected component (3,380 nodes). Produces 35 communities with modularity 0.700. Nodes outside the WCC are assigned community −1.
- **PTF approximation** — local one-step (fraction of outflow reaching non-sink nodes) and global Leontief backward multiplier. Spearman rank correlation between the two: 0.50.
- **Resilience** — top-10 nodes by out-strength removed individually; flow loss and WCC fragmentation measured. USA_G causes the largest flow loss (5.3%).

---

## Phase Checklist

### Phase 1 — EUKLEMS Preparation
- [x] Load and audit `growth accounts.csv`
- [x] Long-to-wide pivot (country × sector × year × variable)
- [x] Baseline panel diagnostics (missingness, coverage)
- [x] Export `euklems_wide.parquet`
- [x] NACE concordance diagnostic vs. ICIO 50 codes

### Phase 2 — ICIO Preparation
- [x] Load and validate ICIO 2022 structure
- [x] Identify and document CN1/CN2/MX1/MX2 pseudo-country splits
- [x] Extract and save Z-block (`z_block.parquet`, 4250×4250)
- [x] Extract and save gross output vector (`gross_output.parquet`, 4,250 entries)
- [x] Extract and save value-added vector (`value_added.parquet`, 4,250 entries)

### Phase 3 — Network Construction
- [x] Build directed weighted DiGraph from Z-block (PERCENTILE=99)
- [x] Compute degree, strength, HITS, betweenness centrality
- [x] Export `network_centrality.csv` with `icio_country` / `icio_sector` join keys
- [x] Generate subgraph and degree-distribution figures

### Phase 4 — Digital Intensity
- [x] Compute ICT capital share, ICT growth rate, TFP growth for all EUKLEMS countries
- [x] Build composite DT score (equal-weight Z-score composite)
- [x] Export `digital_intensity.parquet` (panel) and `dt_scores.parquet` (cross-section)
- [x] Generate ICT-share, DT-score, and TFP scatter figures

### Phase 5 — Integration
- [x] Build ISO3→EUKLEMS country code mapping (30 countries)
- [x] Build ICIO→EUKLEMS sector concordance (priority-list approach)
- [x] Execute cross-section join aligned to ICIO reference year 2022
- [x] Execute panel join (all years 2000–2021)
- [x] Print mandatory join diagnostics; quality gate passed (100% sector match among covered countries)
- [x] Export `global_integrated_cs.parquet/csv` and `integrated_panel.parquet`

### Phase 6 — Extended Network Analysis
- [x] Build technical coefficient matrix A (column-normalised by gross output)
- [x] Compute Leontief inverse via Neumann series (backward, forward, VA vector products)
- [x] Compute IO linkage indices and GVC position for all 4,250 nodes
- [x] Compute Markov-chain centrality with dangling-node redistribution
- [x] Detect communities on largest WCC via Louvain (35 communities, modularity 0.700)
- [x] Compute PTF local and PTF global (Leontief backward multiplier)
- [x] Run resilience simulation (top-10 node removal)
- [x] Export `network_extended.csv` (4,250 × 25) and `global_full_analysis.csv` (4,250 × 42)

---

## Key Empirical Findings

- **Most central node (Markov)**: USA_G (retail/wholesale, π = 3.5%), followed by USA_O (public admin, 3.0%) and CN1_F (construction, 2.6%).
- **Highest backward multiplier**: ROW_B06 (33.2), USA_G (23.0) — sectors that trigger the largest upstream output ripple per unit of demand.
- **Net upstream sectors**: 2,845 of 4,250 nodes have positive GVC position (net suppliers to global chains).
- **Community structure**: 35 production blocs identified within the connected network. The largest (355 nodes) is a Central European manufacturing cluster anchored by Poland, Germany, and Czech Republic.
- **Digital coverage**: 30 countries and 58 EUKLEMS sectors matched; 820 nodes have full DT scores; the remainder lack VATFP_I observations in the source data.
- **Resilience**: No single node removal fragments the main connected component; USA_G removal causes the largest flow disruption (5.3% of total network flow).

---

## Known Issues and Possible Improvements

### Known Issues

**1. Two sectors with column sums of A ≥ 1 (Leontief convergence)**
CYP_H51 (Cyprus — water transport) and ISL_C21 (Iceland — pharmaceuticals) have technical coefficient column sums slightly above 1 (max 1.12), violating the standard Hawkins-Simon condition. This slows Neumann series convergence for those columns. Both are likely data artefacts from the ICIO source (small economies with large re-export activity recorded as domestic production). At K=15, the global residual remains acceptably small (8.3e-5), but results for these two nodes should be interpreted with caution.

**2. 213 sectors with zero gross output**
These sectors have their A-matrix column zeroed (no technical coefficients can be defined). They produce zero output in the ICIO table, likely because the ICIO includes all 85 country × 50 sector combinations structurally, even where a sector is inactive in a given economy. These nodes receive a backward multiplier of exactly 1 (identity contribution only) and a Markov centrality drawn entirely from dangling-node redistribution.

**3. Markov centrality slow convergence (1,169 iterations)**
With 1,112 sink nodes (26% of the graph), the dangling-node redistribution significantly slows convergence. An alternative is to run the Markov chain only on the largest WCC where sinks are a smaller fraction, analogously to the community detection fix.

**4. 820 of 1,500 joined nodes lack a DT score**
VATFP_I (value-added TFP index) is sparse in EUKLEMS — roughly 50% of (country, sector) pairs have missing values, especially for smaller EU member states and non-EU countries. The DT score is therefore only available for the 820 nodes where all three component variables are non-null.

**5. EUKLEMS covers only 30 of 85 ICIO countries**
The EUKLEMS dataset is limited to EU member states plus Japan, the US, and a small number of other countries. The remaining 55 ICIO countries (including China, India, Russia, Brazil, and the ROW aggregate) have no EUKLEMS counterpart and carry NaN digital indicators throughout.

**6. CN1/CN2/MX1/MX2 excluded from digital join**
The four OECD processing-trade pseudo-countries have no ISO country code and no EUKLEMS equivalent. They are retained in the network and Leontief computations but are excluded from all digital intensity attributes.

### Possible Improvements

**Data coverage**
- Incorporate the World KLEMS dataset or Penn World Tables to extend digital-intensity proxies to countries not covered by EUKLEMS (particularly China, India, Russia, and developing economies).
- Use multiple ICIO reference years (e.g., 2015, 2018, 2022) to construct a longitudinal panel of network structure and GVC participation, enabling change analysis rather than a single cross-section.

**Sector concordance**
- The current priority-based concordance falls back to broad EUKLEMS aggregates (e.g., `C`) when a fine-grained match is unavailable, which may introduce measurement error. A formal crosswalk table verified against OECD documentation would improve precision.
- Several ICIO codes (e.g., `B05`, `B06`, `C24A`, `C24B`, `C301`) have no standard EUKLEMS counterpart; these are currently mapped to the parent letter-code aggregate or left unmatched.

**Network methodology**
- The 99th-percentile threshold for graph sparsification is a heuristic choice. A sensitivity analysis across a range of thresholds (95th–99.9th percentile) would establish how stable the centrality rankings and community structure are to this choice.
- Community detection is restricted to the largest WCC. A multi-resolution approach (varying the Louvain resolution parameter γ) would reveal whether the 35-community solution is stable or if meaningful sub-structure exists within large communities.
- The GVC position index used here is a simplified Leontief-linkage ratio, not the full Koopman-Wang-Wei (2014) decomposition. The full KWW decomposition requires bilateral final demand by origin-destination pair, which is available in the ICIO table and would yield a more precise measure of foreign value-added content.
- Markov centrality could be computed on the largest WCC only (matching the community detection approach) to avoid the influence of 1,112 isolated sink nodes on the stationary distribution.

**Visualisation and reporting**
- Country-level aggregation of node attributes (e.g., mean DT score, mean GVC position by country) would support cleaner cross-country comparison in presentation.
- A bipartite community–country heatmap would make the production-bloc structure more interpretable.
- Network visualisations currently use position-free layouts; a geography-aware layout (e.g., nodes placed at country centroids) would add spatial interpretability.

**Reproducibility**
- Scripts currently write figures with `plt.show()` calls that are suppressed by the Agg backend. Adding explicit figure-close calls (`plt.close()`) after each save would prevent memory accumulation in long runs.
- A lightweight `requirements.txt` or `environment.yml` pinning package versions (NetworkX, pandas, scipy, numpy, seaborn) would improve cross-machine reproducibility.
