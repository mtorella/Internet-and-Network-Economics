# Bottlenecks in the Italian Production Network
### Digital Economy — Group Project Proposal
*A network-based analysis of structural vulnerabilities and digitalisation gaps*

---

## The Core Idea

Italy's economy doesn't operate in isolation. Every sector — Construction, Machinery, Wholesale trade — is embedded in a web of supply relationships, both domestic and international. Some sectors sit at the centre of that web: many others depend on them for inputs. If one of those central sectors fails, or is slow to adapt, it drags down everything connected to it.

Our project asks a simple but consequential question:

> **Are the sectors that Italy's production network depends on most heavily also the ones that are most digitally lagging?**

If yes, that's a double bottleneck — structural centrality compounded by digital vulnerability. Identifying these sectors, understanding why they matter, and quantifying the mismatch is the core contribution of this project.

---

## Why This Is Interesting (The Economic Mechanism)

The theoretical motivation draws on two strands of the digital economy literature:

**1. Network theory applied to production**
Input-output tables aren't just accounting tools — they encode a network. Sectors that supply inputs to many others act as multipliers: a productivity gain (or shock) in a hub propagates through the entire chain. Acemoglu et al. (2012) formalise this: in a production network, sector-level shocks don't average out — the most central sectors generate aggregate fluctuations. This is why bottlenecks matter macroeconomically.

**2. The intangibles and digitalisation gap**
The CHS (Corrado-Hulten-Sichel) framework shows that investment in intangible capital — software, R&D, organisational knowledge — is the primary driver of modern productivity growth. Sectors that fail to invest in digital capital accumulate a structural productivity gap. For Italy, this gap is well-documented and larger than most comparable European economies.

**The combination** of these two mechanisms is our analytical angle: a sector with high network centrality and low digitalisation is not just individually unproductive — it is a drag on every sector downstream of it.

---

## Data

| Dataset | Source | What it gives us |
|---|---|---|
| **OECD ICIO 2022** | OECD (2023 edition) | Inter-country input-output flows, 76 countries × 45 sectors |
| **Intan-Invest** | EU Commission / EIB (CHS framework) | Intangible investment by sector for Italy, 1995–2021 |

**Important design choice — open economy:**
We build the network over *all* countries in the ICIO table, not just Italy's domestic flows. Centrality is then computed on the full global graph and Italian sectors are extracted afterwards. This is the correct approach: Italy's Machinery sector's importance depends on how German and French manufacturers depend on it, not just on domestic linkages. Analysing a closed domestic submatrix would systematically underestimate the true structural importance of export-oriented sectors.

---

## Implementation — Step by Step

### Alignment Between main.ipynb and second_version.py

The two files follow the same analytical backbone for network construction and bottleneck detection:

- Build the directed weighted global ICIO graph from the intermediate-use block.
- Apply the same edge threshold logic ($50M).
- Compute the same centrality family (PageRank, betweenness approximation, in/out/total strength).
- Filter to Italian sectors after global centrality is computed.
- Merge centrality with digitalisation metrics and identify high-centrality / low-digital sectors.

Main differences are scope and engineering quality, not the conceptual method:

- main.ipynb is exploratory and presentation-oriented (cell-by-cell workflow).
- second_version.py is a reproducible pipeline script (fixed paths, schema checks, deterministic settings).
- second_version.py is explicitly single-year (2021) and integrates prepared growth-accounts plus intangibles sources into a composite digitalisation measure.

### Step 1 — Load the ICIO Table

```python
# File: step1_load_icio.py
```

The ICIO CSV has one row and one column per country-sector pair (e.g. `ITA_C28` = Italian Machinery). We strip out the final demand columns (household consumption, government spending, investment) and keep only intermediate use — the flows between sectors that represent actual supply chain relationships.

**Output:** `Z` — a ~4,700 × ~4,700 matrix of intermediate flows in million USD.

---

### Step 2 — Build the Directed Weighted Graph

```python
# File: step2_build_graph.py
```

We model the economy as a **directed weighted graph** where:
- Each **node** is a country-sector pair (e.g. `DEU_C29` = German Motor Vehicles)
- Each **edge** `i → j` means sector `i` supplies intermediate inputs to sector `j`
- **Edge weight** = flow value in million USD

We apply a threshold of $50M to filter out noise — very small flows add thousands of edges with no analytical value and slow down centrality computation.

This thresholding logic is shared by both main.ipynb and second_version.py.

**Methodological choice — zeroing the diagonal:**
Before building the graph we set all diagonal entries of `Z` to zero, removing intra-sector flows (e.g. the chemicals sector buying from itself). Intra-sector flows are economically real and can be large, but they are not relevant here. Our question is about *inter-sectoral* dependency: which sectors are pivotal because many *other* sectors rely on them? A self-loop tells us only that a sector is large and internally integrated, not that it is a structural node in the supply network. Keeping diagonal entries would inflate strength and PageRank for sectors with high internal turnover, biasing centrality rankings away from genuine inter-sectoral hubs and toward sectors that simply process a lot internally. Zeroing the diagonal ensures that centrality reflects network position, not sector size alone.

**Output:** `G` — a NetworkX DiGraph with ~4,250 nodes and ~200,000 edges.

---

### Step 3 — Compute Centrality on the Full Global Graph

```python
# File: step3_centrality.py
```

Three centrality measures, each capturing a different structural role:

| Measure | What it captures | Why we use it |
|---|---|---|
| **In/Out strength** | Raw flow volume | Economic size in the supply chain |
| **PageRank** | Recursive supply authority | A sector scores high if supplied by other important sectors — captures systemic importance |
| **Betweenness** | Broker / bridge role | Fraction of shortest supply paths passing through a node — pure bottleneck measure |

Exact betweenness centrality requires computing shortest paths between every pair of nodes — O(n³) complexity for a weighted graph. With ~4,250 nodes that is billions of path calculations, infeasible in practice. We therefore use the Brandes (2001) approximation: instead of using all n nodes as path sources, NetworkX randomly samples `k=300` pivot nodes and scales the result. This reduces computation to O(k·m) where m is the number of edges, producing stable rankings in seconds. `k=300` corresponds to sampling ~7% of all nodes — sufficient to reliably rank the top sectors, which is all that matters for identifying bottlenecks. The `seed=42` parameter ensures the sample is fixed and results are reproducible across runs.

After computing on the full global graph, we **filter to Italian nodes only** (`ITA_*`) for analysis and visualisation.

---

### Step 3b — Network Visualisation

```python
# File: step3b_visualise_graph.py
# Interactive version: viz1.html
```

**Static version:** Vertical spine layout — Italian sectors sorted by PageRank in the centre column, top 10 trading partners split left and right, bezier arcs for the top 5% of flows by weight.

**Interactive version (D3.js):** Open `viz1.html` in any browser.
- Hover an Italian sector → tooltip with PageRank, flow strength, top 3 trading partners; connected arcs highlight, others dim
- Click a country label → filter all arcs to show only that country's flows
- Click again or click background → clear filter

Top 10 trading partners identified (excluding ROW aggregate): **DEU, FRA, CN1, USA, ESP, IRL, RUS, CHE, GBR, POL**

---

### Step 4 — Digitalisation Measures

```python
# File: step4_digitalisation.py
```

Two independent digitalisation proxies are computed for Italian sectors, both normalised to [0, 1] using min-max scaling before any comparison:

**Digital intensity (Intan-Invest):**

$$\text{Digitalisation intensity}_s = \frac{I\_Soft\_DB_s + I\_RD_s}{VA\_CP_s}$$

Where:
- `I_Soft_DB` = investment in software & databases
- `I_RD` = R&D investment
- `VA_CP` = value added at current prices

Following the CHS framework, these two components capture a sector's *active accumulation of digital productive capacity*. Dividing by value added normalises for sector size. Available for all matched sectors.

**ICT share (EUKLEMS growth accounts):** Share of ICT capital in total capital services. Captures the *stock* of digital capital already embedded in production. Available for 33 of the 37 matched sectors — water transport (H50), air transport (H51), warehousing (H52), and postal services (H53) have no EUKLEMS entry for Italy in 2021.

**Note on temporal mismatch:** Intan-Invest runs to 2021; ICIO to 2022. The 1-year gap is minimal and unlikely to affect structural rankings.

**NACE → ICIO crosswalk:** Both EUKLEMS and Intan-Invest use NACE Rev.2 sector codes; ICIO uses ISIC Rev.4. We map between them manually. ICIO is the coarser classification (38 unique codes vs 50 NACE keys), so multiple NACE codes collapse into one ICIO code — where this happens, scores are averaged across NACE sub-sectors. Unmatched NACE codes (`TOT`, `MARKT`, `MARKTxAG`, `C`, `TOT_IND`) are aggregate convenience rows in EUKLEMS and are correctly excluded; `Q87-Q88` and `T` are genuine gaps in the crosswalk (see Known Issues).

---

### Step 5 — Merge and Identify Double Bottlenecks

```python
# File: step5_merge_bottlenecks.py
```

Italian centrality data is merged with both digitalisation measures. A sector is a **double bottleneck** if:

- PageRank ≥ 60th percentile among Italian sectors → *structurally central*
- Digitalisation ≤ 40th percentile → *digitally lagging*

The classification is run independently on each measure (**Variant A** — digital intensity; **Variant B** — ICT share). Sectors flagged in both variants are **robust double bottlenecks** — the finding is not sensitive to the choice of digitalisation proxy.

---

### Step 6 — Visualisations

```python
# File: step6_plots.py
```

Four figures:

**Fig 0 — Network Spine:** Italy's position in the global supply network. Italian sectors sorted by PageRank in the centre column; top 10 trading partners split left and right; bezier arcs for the top 5% of bilateral flows by weight.

**Fig 1 — Hub Ranking:** Horizontal bar chart of top 15 sectors by total IO flow strength. Establishes which sectors are economically large in the global supply chain.

**Fig 2 — Centrality Map:** Scatter of PageRank vs. Betweenness, bubble size = total flow. Separates sectors that are large *recipients* of supply chain inputs (high PageRank) from those that act as *bridges* (high betweenness). The two roles do not always coincide.

**Fig 3 — Main Result:** Two-panel scatter of PageRank vs. digitalisation score, one panel per variant. The top-left quadrant (high centrality, low digitalisation) is the double bottleneck zone, marked by red dashed threshold lines. Sectors robust across both variants are highlighted with a white ring.

---

## Results Summary

### What Figure 1 tells us
Wholesale & retail ($440B), Construction ($296B), and Professional services ($274B) are Italy's largest supply chain hubs by raw flow volume. Notably, the top sectors are predominantly services — consistent with services acting as universal intermediate inputs across the economy.

### What Figure 2 tells us
Health & social work has the highest PageRank but near-zero betweenness — it is a major recipient of supply chain inputs but not a bridge. The sectors with the highest betweenness (Furniture & repair, Textiles, Fabricated metals) are structural bridges whose disruption would disconnect many supply paths beyond what their size implies.

### What Figure 3 tells us — the core finding
Sectors in the double bottleneck quadrant (top-left: high PageRank, low digitalisation) are the core finding. Sectors flagged as robust — appearing in both Variant A (digital intensity) and Variant B (ICT share) — are the most reliable candidates.

The weak negative trend across both panels is the headline result: **Italy's most central production sectors tend to be its least digitalised** — the opposite of what an efficient digital transition would require.

Sectors in the resilient hub quadrant (top-right): high centrality combined with above-median digitalisation on both measures — these sectors are not a concern.

---

## File Structure

```
project/
│
├── data/
│   ├── prepared/
│   │   └── icio_zblock_2021.csv
│   └── processed/
│       ├── growth_accounts_2021_wide.csv
│       └── intangibles_analytical_2021.csv
│
├── martas_proposal/
│   ├── main.ipynb
│   ├── second_version.py
│   └── viz/
│       └── viz1.html
│
└── outputs/
	├── figures/
	│   ├── fig0_network_spine_2021.png
	│   ├── fig1_hub_ranking_2021.png
	│   ├── fig2_centrality_map_2021.png
	│   └── fig3_centrality_vs_digitalisation_panel_2021.png
	└── tables/
		├── df_composite_2021.csv
		└── robustness_check_2021.csv
```

**Run order:** Steps 1 → 2 → 3 → 3b → 4 → 5 → 6
Steps 1–3 must be run in sequence (each depends on the previous). Step 4 is independent. Steps 5 and 6 depend on Steps 3 and 4.

---

## Dependencies

```bash
pip install pandas numpy networkx matplotlib seaborn
```

D3.js for the interactive graph is loaded from CDN — requires internet on first open, then works offline.

---

## Known Issues

### NACE codes unmatched in the EUKLEMS → ICIO crosswalk

When mapping EUKLEMS growth accounts to ICIO sector codes, 7 rows have no entry in `NACE_TO_ICIO` and are dropped. The unmatched codes are:

| Code | Description | Action |
|---|---|---|
| `TOT` | Total economy | Correctly excluded — aggregate summary row |
| `TOT_IND` | Total industries | Correctly excluded — aggregate summary row |
| `MARKT` | Market economy | Correctly excluded — aggregate summary row |
| `MARKTxAG` | Market economy excl. agriculture | Correctly excluded — aggregate summary row |
| `C` | Total manufacturing | Correctly excluded — too broad to map to a single ICIO code |
| `Q87-Q88` | Residential care & social work | **Genuine gap** — valid sector with no entry in the crosswalk |
| `T` | Household services as employers | **Genuine gap** — present in `SECTOR_LABELS` but missing from `NACE_TO_ICIO` |

The first five are EUKLEMS convenience aggregates that should never be mapped. `Q87-Q88` and `T` are real sectors that could in principle be added to the crosswalk and recovered for the analysis.

---

## Project Readiness

The project is close to submission-ready.

What is already ready:

- Clear research question and economic mechanism.
- Consistent network methodology across notebook and script versions.
- Reproducible 2021 script pipeline with saved tables and figures.
- Robustness check included for bottleneck classification variants.

What should still be finalised before submission:

- Add one short methodology note in the report explaining why 2021 is used consistently in second_version.py.
- Include one sensitivity check appendix (e.g., threshold $40M/$60M or quantile-based threshold) to show ranking stability.
- Add a pinned environment file (requirements.txt) for full reproducibility.

*Data sources: OECD Inter-Country Input-Output Tables (2023 edition); Intan-Invest Database, European Investment Bank / EU Commission; EUKLEMS Growth Accounts.*
