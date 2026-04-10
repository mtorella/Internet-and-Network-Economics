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

For betweenness on a graph this large we use `k=300` pivot sampling (NetworkX), which gives a good approximation in seconds rather than hours.

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

### Step 4 — Digitalisation Intensity Score

```python
# File: step4_digitalisation.py
```

From Intan-Invest (Italy, 2021):

$$\text{Digitalisation intensity}_s = \frac{I\_Soft\_DB_s + I\_RD_s}{VA\_CP_s}$$

Where:
- `I_Soft_DB` = investment in software & databases
- `I_RD` = R&D investment
- `VA_CP` = value added at current prices

**Theoretical justification:** Following the CHS framework, these two components capture a sector's *active accumulation of digital productive capacity*. Software & databases are the most direct measure of digital capital formation; R&D proxies both innovation effort and absorptive capacity — the ability to actually use digital technologies productively. Dividing by value added normalises for sector size, making the measure comparable across sectors of very different scales.

**Note on temporal mismatch:** Intan-Invest runs to 2021; ICIO to 2022. The 1-year gap is minimal and unlikely to affect structural rankings.

**NACE → ICIO crosswalk:** Intan-Invest uses NACE Rev.2 sector codes; ICIO uses ISIC Rev.4. We map between them manually (e.g. NACE `C29-C30` → ICIO `C29`). Where multiple NACE codes map to one ICIO code we average the intensity scores.

In second_version.py, this is extended with EUKLEMS growth-accounts ICT share for 2021, then combined with the intangibles metric into a composite score (equal-weight and weighted variants).

---

### Step 5 — Merge and Identify Double Bottlenecks

```python
# File: step5_merge_bottlenecks.py
```

We merge the Italian centrality data with the digitalisation scores on the sector code, then apply a dual threshold to identify **double bottlenecks**:

- PageRank ≥ 60th percentile among Italian sectors → *structurally central*
- Digitalisation intensity ≤ 40th percentile → *digitally lagging*

Sectors satisfying both conditions simultaneously are the core finding of the analysis.

---

### Step 6 — Visualisations

```python
# File: step6_plots.py
```

Three figures:

**Fig 1 — Hub Ranking:** Horizontal bar chart of top 15 sectors by total IO flow strength. Establishes which sectors are economically large in the global supply chain.

**Fig 2 — Centrality Map:** Scatter of PageRank vs. Betweenness, bubble size = total flow. Separates sectors that are large *recipients* of supply chain inputs (high PageRank) from those that act as *bridges* (high betweenness).

**Fig 3 — Main Result:** Scatter of PageRank vs. Digitalisation intensity, with median dashed lines creating four quadrants. The top-left quadrant (high centrality, low digitalisation) is the double bottleneck zone.

---

## Results Summary

### What Figure 1 tells us
Wholesale & retail ($440B), Construction ($296B), and Professional services ($274B) are Italy's largest supply chain hubs by raw flow volume. Notably, the top sectors are predominantly services — consistent with services acting as universal intermediate inputs across the economy.

### What Figure 2 tells us
Health & social work has the highest PageRank but near-zero betweenness — it is a major recipient of supply chain inputs but not a bridge. The sectors with the highest betweenness (Furniture & repair, Textiles, Fabricated metals) are structural bridges whose disruption would disconnect many supply paths beyond what their size implies.

### What Figure 3 tells us — the core finding
Three sectors sit firmly in the double bottleneck quadrant:

| Sector | PageRank | Dig. Intensity | Why it matters |
|---|---|---|---|
| **Health & social work** | Highest | Near zero | Most supply-network-dependent sector, essentially undigitalised |
| **Construction** | 2nd | Very low | $296B in flows, chronic digital laggard across Europe |
| **Wholesale & retail** | 3rd | Below median | Largest sector by volume, digitalisation intensity below median |

Sectors in the resilient hub quadrant (top-right): Motor vehicles, Machinery, Professional services — high centrality combined with above-median digitalisation.

The weak negative trend across the scatter is the headline result: **Italy's most central production sectors tend to be its least digitalised** — the opposite of what an efficient digital transition would require.

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
