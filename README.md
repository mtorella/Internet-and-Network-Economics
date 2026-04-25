# Digital Transition and Supply-Chain Structure in the Italian Economy

Internet and Network Economics — Group Project 2025-2026

## Introduction
Italy's economy is embedded in a global production network where sectors are interconnected through complex input-output relationships. Some sectors may be structurally central, acting as key suppliers to many downstream activities, while others remain more peripheral. At the same time, sectors differ considerably in their degree of digitalisation, in terms of ICT investment, digital capital intensity, or adoption of digital technologies. The central question of this project is whether these two dimensions, structural centrality and digitalisation, are systematically correlated. Answering this question matters because it speaks to a common assumption in the digital transition literature, namely that all sectors must digitalise to remain competitive and structurally important. The empirical analysis aims to assess whether this association holds for Italy, without making causal or normative claims about what any sector's position implies.

## Economic Logic
Production network propagation. Sectors that are structurally central act as key suppliers to many downstream activities. If digital investment raises productivity, then a central sector that digitalises can propagate efficiency gains broadly through the network, creating a systemic incentive for central sectors to be digitally intensive. This suggests a positive relationship between centrality and digitalisation.
Intangible capital accumulation. Digital investment in software, R&D and ICT capital is a key driver of modern productivity growth, and sectors that face stronger competitive pressures may have greater incentives to accumulate these assets. However, sectors whose centrality is structurally guaranteed, for instance because they supply physically irreplaceable inputs, may face weaker competitive pressure and therefore lower incentives to digitalise, independently of their position in the network.
These two mechanisms generate competing predictions. The first suggests that centrality and digitalisation should go together. The second suggests that certain sectors can maintain structural relevance without digital intensity, depending on the nature of their centrality. The empirical analysis aims to assess which of these patterns characterises Italy's production network.

## Data Sources

The analysis draws on two main datasets.

| Dataset | Source | Content |
|---|---|---|
| OECD ICIO (2025 edition) | OECD | Inter-country input-output flows, 1995 to 2022, 85 countries and country groupings, 50 sectors |
| EUKLEMS Statistical Module | EUKLEMS and INTANProd, LUISS University | Industry-level capital accounts including ICT and non-ICT capital services, 27 EU member states plus UK, US and Japan, 42 industries, 1995 to 2020 |
| EUKLEMS Analytical Module | EUKLEMS and INTANProd, LUISS University | Industry-level investment and capital stocks for intangible assets beyond national accounts boundaries, including software, R&D, organisational capital and brand, same country and industry coverage |

The first dataset is the OECD Inter-Country Input-Output tables, 2025 edition, which provide a globally balanced view of the inter-country and inter-industry flows of goods and services used as intermediate inputs and to meet final demand, covering 85 countries and country groupings across 50 sectors over the period 1995 to 2022. These tables are used to construct the production network and compute sector-level centrality measures for Italy.

The second is the EUKLEMS and INTANProd database, funded by the Directorate General for Economic and Financial Affairs of the European Commission and developed at LUISS University Rome, which provides industry-level data on output, value added, employment, and capital stocks across both tangible and intangible assets for 27 EU member states, the United Kingdom, the United States and Japan, covering 42 industries over the period 1995 to 2020. The database is organised in two modules: a statistical module, which draws directly from national accounts and provides standard growth accounting variables including ICT and non-ICT capital services; and an analytical module, which extends the asset boundary to include intangible assets not recorded as investment under current national accounts standards, notably software and databases, R&D, organisational capital, brand and training.

## Data Processing
The two datasets are processed separately and then merged through a crosswalk between the NACE industry classification used in EUKLEMS and the ICIO sector classification.

### Digitalisation Metrics

Digitalisation is measured using two distinct proxies, each drawn from a different module of the EUKLEMS and INTANProd database and capturing a complementary dimension of digital intensity at the sector level.

- **Digital capital contribution** (`dig_contribution`): This proxy measures the contribution of software and database capital services to value added growth in a given year, as defined in the growth accounting framework (equation 14 of the EUKLEMS methodology). It is drawn from the statistical module, which follows standard national accounts definitions and is available for all countries and industries in the database. It is a **flow measure**: it captures how much software and database capital actually drives output in that year, weighted by its compensation share in value added. It is therefore sensitive to business-cycle conditions and year-to-year investment variation.

$$\text{dig\_contribution}_s = VACon\_Soft\_DB_s$$

- **Digital capital depth** (`dig_depth`): This proxy measures the stock of software and database capital accumulated by a sector relative to its current-price value added. It is drawn from the analytical module, which uses the perpetual inventory method with geometric depreciation to construct capital stocks for intangible assets not recorded under standard national accounts boundaries. It is a **stock measure**: it captures how structurally digitally intensive a sector is, independently of year-to-year fluctuations in investment, and is therefore better suited for cross-sector comparisons of digital depth.

$$\text{dig\_depth}_s = \frac{K\_Soft\_DB_s}{VA\_CP_s}$$

The two proxies are complementary by construction. `dig_contribution` is dynamic and growth-oriented; `dig_depth` is structural and level-oriented. A sector can score high on one and low on the other — for instance, a sector with a large accumulated stock of digital capital that is currently growing slowly, or one investing heavily in a year of rapid expansion despite a modest existing stock.

**Coverage note.** `dig_contribution` is available for all 58 Italian sectors in the growth accounts data. `dig_depth` is available for 49 of those 58 sectors; the remaining 9 — concentrated in distribution (G45, G46, G47), transport (H49–H53) and real estate (L68A) — lack a reliable capital stock estimate from the analytical module's perpetual inventory method. Both proxies are retained in the processed files with missing values where applicable. Sectors missing `dig_depth` are included in any analysis that uses `dig_contribution` alone, and are dropped only from analyses that require both metrics jointly.

Both proxies are normalised to the unit interval using min-max scaling before any comparison or visualisation, so that differences in units and scale do not drive the results.

## Crosswalk: NACE to ICIO

The two datasets speak different classification languages.

EUKLEMS uses **NACE Rev. 2** codes. In the Italian sample we observe 58 unique NACE codes:

- `A`, `B`, `C`, `C10-C12`, `C13-C15`, `C16-C18`, `C19`, `C20`, `C20-C21`, `C21`, `C22-C23`, `C24-C25`
- `C26`, `C26-C27`, `C27`, `C28`, `C29-C30`, `C31-C33`, `D`, `D-E`, `E`, `F`, `G`, `G45`
- `G46`, `G47`, `H`, `H49`, `H50`, `H51`, `H52`, `H53`, `I`, `J`, `J58-J60`, `J61`
- `J62-J63`, `K`, `L`, `L68A`, `M`, `M-N`, `MARKT`, `MARKTxAG`, `N`, `O`, `O-Q`, `P`
- `Q`, `Q86`, `Q87-Q88`, `R`, `R-S`, `S`, `T`, `TOT`, `TOT_IND`, `U`

ICIO uses its own sector codes and is more granular for several production activities. In the Italian network we use 50 ICIO codes:

- `A01`, `A02`, `A03`, `B05`, `B06`, `B07`, `B08`, `B09`, `C10T12`, `C13T15`
- `C16`, `C17_18`, `C19`, `C20`, `C21`, `C22`, `C23`, `C24A`, `C24B`, `C25`
- `C26`, `C27`, `C28`, `C29`, `C301`, `C302T309`, `C31T33`, `D`, `E`, `F`
- `G`, `H49`, `H50`, `H51`, `H52`, `H53`, `I`, `J58T60`, `J61`, `J62_63`
- `K`, `L`, `M`, `N`, `O`, `P`, `Q`, `R`, `S`, `T`

Some are one-to-one matches with NACE, while others are aggregates or splits. For instance, ICIO `C16` corresponds to NACE `C16-C18`, while ICIO `C26` corresponds to NACE `C26`. ICIO also includes sectors such as `C301` and `C302T309`, both mapping to NACE `C29-C30`.

Another issue is that in some cases more ICIO sectors, such as `A01`, `A02` and `A03`, correspond to a single NACE sector, in this case `A`. This is because the ICIO classification is designed to capture the full structure of global production networks, which requires a more detailed breakdown of certain sectors that play a key role in international trade and supply chains. The NACE classification, by contrast, is designed for national statistical purposes and therefore allows for more aggregation in some areas.

Hence, a direct merge is not possible and a crosswalk is required.

We use ICIO codes as the canonical identifier, since it is much easier to aggregate digitalisation from NACE to ICIO than to disaggregate ICIO sectors into NACE sub-sectors, and we want to preserve the full ICIO network structure.

In the current codebase, the crosswalk is implemented as a dictionary mapping **ICIO to NACE** in `Src/utils/constants.py` (`ICIO_TO_NACE`), for instance:

  "C26": "C26"          # one-to-one
  "A01": "A"            # many ICIO sectors map to one NACE aggregate
  "A02": "A"
  "A03": "A"

So the implemented logic is many-to-one at the code-system level (multiple ICIO sectors can map to one NACE code), but the dictionary direction is ICIO -> NACE. ICIO sectors with no NACE match in the EUKLEMS Italy data appear in the centrality panel with missing digitalisation values.

### From Input-Output Flows to a Directed Graph

The starting point of the network analysis is the intermediate flow matrix extracted from the OECD ICIO tables. For a given year, let $z_{ij}$ denote the value of intermediate inputs supplied by sector $i$ to sector $j$, measured in current USD. These flows are recorded for all pairs of the $N = 50$ sectors present in the ICIO tables for the Italian economy.

The raw flow matrix $\mathbf{Z}$ captures the monetary volume of production interdependencies, but it is sensitive to the overall scale of the economy: a large sector will mechanically show large flows even if its structural role is modest. To remove this nominal-size bias, we normalise each column of $\mathbf{Z}$ by the total intermediate input purchases of the receiving sector, obtaining the matrix of Leontief technical coefficients:

$$a_{ij} = \frac{z_{ij}}{\sum_{i} z_{ij}}$$

The coefficient $a_{ij}$ measures the share of sector $j$'s intermediate inputs that originate from sector $i$. It is a structural, scale-invariant quantity: it reflects how dependent sector $j$ is on sector $i$ as a supplier, independently of whether the economy is large or small in absolute terms. This normalisation ensures that the network topology we recover is driven by the organisation of production rather than by nominal magnitudes.

**Sparsification.** The full coefficient matrix is dense by construction, since most entries $a_{ij}$ are positive but very small, representing economically negligible input relationships. We therefore apply a minimum threshold of $a_{ij} \geq 0.01$, retaining only those supplier–buyer relationships in which sector $i$ accounts for at least one percent of sector $j$'s total intermediate purchases. Edges falling below this threshold are set to zero. The threshold is structural rather than data-driven: it filters out noise while preserving all economically meaningful supply linkages.

The resulting object is a weighted directed graph $G = (V, E, w)$, where:

- the node set $V$ contains the global sectors;
- each directed edge $(i \to j) \in E$ indicates that sector $i$ is a meaningful intermediate
  supplier to sector $j$;
- the edge weight $w_{ij} = a_{ij}$ records the intensity of that supply relationship.

This procedure is repeated independently for each year in the window 2016–2021, yielding a sequence of six annual graphs that allow us to assess the stability of the network structure over time.

### Centrality Measures

Four centrality measures are computed for every node in each annual graph. All measures operate on the weighted, directed graph of technical coefficients described above.

- **PageRank**: the stationary distribution of a random walk on the directed graph, where transition probabilities are proportional to edge weights. A sector's PageRank score reflects how much of the global flow of intermediate demand passes through it, accounting for the full recursive structure of the network. This is the primary centrality measure used in the analysis.

- **Betweenness centrality**: the fraction of shortest paths between all pairs of nodes that pass through a given sector, normalised to the unit interval. It captures a sector's role as a structural bridge in the network. Shortest paths are weighted by the inverse of edge weight, so that stronger supply relationships are treated as shorter. Given the size of the graph, betweenness is approximated using a random sample of $k = 500$ pivot nodes.

- **In-strength** and **out-strength**: the sum of incoming and outgoing edge weights for each node, respectively. In-strength measures how intensively a sector draws on other sectors as suppliers; out-strength measures how intensively it supplies inputs to others.

PageRank and betweenness are additionally normalised to the unit interval using within-year min-max scaling, producing `pagerank_norm` and `betweenness_norm`. This facilitates visual comparison across sectors within a given year. Normalised values should not be compared across years, as the scaling is performed independently for each annual graph.

## Analysis

The analysis examines whether sector-level digitalisation is systematically associated with supply-chain centrality across Italian sectors over the period 2016–2021. The two datasets are merged through the NACE-to-ICIO crosswalk described above, yielding a panel of 49 Italian sectors per year.

### Digitalisation Rankings

For each year, horizontal bar charts display the ten sectors with the highest raw digital capital contribution and the ten sectors with the highest raw digital capital depth. These charts use the unscaled proxies and serve as a descriptive baseline, showing which sectors are most digitalised in absolute terms independently of their network position.

### Correlation Analysis

The statistical relationship between supply-chain centrality and digitalisation is assessed using Spearman rank correlation. For each year and each digitalisation proxy, the Spearman coefficient between `pagerank_norm` and the normalised proxy is computed together with a 95% confidence interval derived from the Fisher $z$-transformation:

$$z = \text{arctanh}(r), \quad \text{SE}(z) = \frac{1}{\sqrt{n-3}}, \quad \text{CI} = \left[\tanh(z - z_{0.025} \cdot \text{SE}),\ \tanh(z + z_{0.025} \cdot \text{SE})\right]$$

Spearman rank correlation is used rather than Pearson because both the centrality and digitalisation distributions are right-skewed, and the research question concerns monotonic association rather than a linear one. Because Spearman operates on ranks, the choice of min-max normalisation does not affect the results; the normalised and raw series yield identical coefficients.

### Quadrant Classification

Each year, sectors are classified into four quadrants based on their joint position in the centrality-digitalisation space. The split is applied at a fixed threshold of 0.5 on the normalised scale for both axes:

| Quadrant | Centrality | Digitalisation |
|---|---|---|
| HH | $\geq 0.5$ | $\geq 0.5$ |
| HL | $\geq 0.5$ | $< 0.5$ |
| LH | $< 0.5$ | $\geq 0.5$ |
| LL | $< 0.5$ | $< 0.5$ |

A fixed threshold is used rather than the sample mean to ensure that quadrant boundaries do not shift with the distribution from year to year, which would make quadrant membership incomparable across the panel. The value 0.5 corresponds to the midpoint of the min-max normalised range and has a natural interpretation: a sector is classified as high if its value lies in the upper half of the observed range for that year.

## Results and Economic Interpretation

This section reports the main outputs directly from the generated figures and tables.

![Spearman correlation over time](outputs/figures/fig_correlation.png)

![Top-10 digitalisation sectors in 2021](outputs/figures/fig_bars_2021.png)

![Centrality-digitalisation quadrants in 2021](outputs/figures/fig_quadrants_2021.png)

### Consolidated Results Table (2016-2021)

The table below is built from `outputs/tables/sector_panel_YYYY.csv` files. Correlations are Spearman between normalised PageRank and each digital proxy. Quadrant counts are reported as HH/HL/LH/LL and are computed on non-missing observations for each proxy.

| Year | N corr (contrib) | rho contrib | Quadrants contrib (HH/HL/LH/LL) | N corr (depth) | rho depth | Quadrants depth (HH/HL/LH/LL) |
|---:|---:|---:|:---|---:|---:|:---|
| 2016 | 44 | 0.133 | 0/0/2/42 | 44 | -0.031 | 0/0/35/9 |
| 2017 | 44 | -0.053 | 0/0/3/41 | 44 | -0.056 | 0/0/35/9 |
| 2018 | 44 | -0.081 | 0/1/4/39 | 44 | -0.006 | 1/0/34/9 |
| 2019 | 44 | -0.038 | 0/0/4/40 | 44 | -0.001 | 0/0/36/8 |
| 2020 | 44 | -0.006 | 0/0/2/42 | 44 | -0.122 | 0/0/34/10 |
| 2021 | 44 | -0.076 | 2/5/3/34 | 22 | -0.269 | 3/0/11/8 |

### What the outputs show

- Correlation panel: the contribution correlation is close to zero in every year except a mild positive value in 2016; the depth correlation becomes more negative in 2020-2021, with the lowest value in 2021.
- 2021 bar chart: top digital contribution sectors are C29, C301 and C302T309, while top digital depth sectors are B06, B09 and B05.
- 2021 quadrant chart: in the contribution panel, J58T60 and J62_63 are in HH, while C29/C301/C302T309 are in LH; in the depth panel, O, M and R are in HH, and several B sectors are LH.
- Table confirmation: LL dominates in the contribution proxy for 2016-2020; LH dominates in the depth proxy in all years; 2021 is the only year where HH becomes non-zero for both proxies.

### Interpretation constrained to these outputs

From the visible figures and the table above, centrality and digitalisation do not move together strongly or consistently across the sample period. The ranking and quadrant outputs show that the sectors leading digital contribution and depth are not the same sectors that repeatedly occupy the highest centrality positions.

## Repository Structure and Execution

The repository is currently organised as follows:

- `Src/1_preprocessing.py`: builds annual digitalisation files (`digitalisation_YYYY.csv`) and extracts annual ICIO Z-block files (`icio_zblock_YYYY.csv`).
- `Src/2_network_centrality.py`: computes network centrality indicators from each yearly Z-block and writes `centrality_YYYY.csv`.
- `Src/3_analysis.py`: merges annual centrality and digitalisation files and generates figures and per-year output tables.
- `Src/4_build_dashboard_bundle.py`: generates the dashboard data bundle (`dashboard/data.bundle.js`).
- `Src/5_Full_Pipeline.py`: runs the full workflow end-to-end.
- `dashboard/index.html`, `dashboard/styles.css`, `dashboard/app.js`: interactive dashboard.

Suggested execution order:

1. `python Src/1_preprocessing.py`
2. `python Src/2_network_centrality.py`
3. `python Src/3_analysis.py`
4. `python Src/4_build_dashboard_bundle.py`

Alternative:

1. `python Src/5_Full_Pipeline.py`

To view the dashboard, open `dashboard/index.html` in your browser (or serve via `python -m http.server 8000` and open `/dashboard/index.html`).
