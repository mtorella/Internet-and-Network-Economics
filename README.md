# Digital Transition and Supply-Chain Structure in the Italian Economy

Internet and Network Economics — Group Project

---

## Research Question

Italy's economy is embedded in a global production network. Some sectors are central suppliers for many downstream activities. If these central sectors underinvest in digital capital, the resulting productivity drag can propagate economy-wide.

The project asks:

> Are the sectors most central in Italy's production network also the sectors most digitally lagging?

When both conditions hold, we call the sector a robust bottleneck.

---

## Economic Logic

1. Production network propagation.
Shocks in highly central sectors do not average out. They transmit through input-output linkages and can affect aggregate outcomes.

2. Intangible-capital accumulation.
Digital investment (software, R&D, ICT capital) is a key driver of modern productivity growth. Underinvestment creates persistent capability gaps.

The central contribution is the interaction of these two mechanisms: structural centrality multiplied by digital weakness.

---

## Data Sources

| Dataset | Source | Content |
|---|---|---|
| OECD ICIO (2023 edition) | OECD | Inter-country input-output flows, 2016-2022, about 76 countries x 45 sectors |
| EUKLEMS Growth Accounts | EUKLEMS and INTANProd | ICT capital share by country-sector-year |
| Intan-Invest | EU Commission and EIB | Intangible investment (software, R&D) by sector |

Design choice (open economy): centrality is computed on the full global ICIO network, then Italian sectors are extracted. This avoids domestic-only bias.

---

## Project Scripts

- `Src/preprocessing.py` prepares cleaned yearly inputs.
- `Src/analysis.py` is the baseline 2021 cross-sectional script.
- `Src/analysis_2.py` is the corrected multi-year panel pipeline (2016-2021) and should be used for the main reported results.

Run from repository root:

```bash
python Src/analysis_2.py
```

---

## Corrected Pipeline in `analysis_2.py`

### Part 1. Coefficient-based network and centrality

For each year (2016-2021), the script builds a directed graph from the Leontief coefficient matrix:

$$
a_{ij} = \frac{z_{ij}}{\sum_i z_{ij}}
$$

An edge is retained when $a_{ij} \ge 0.01$. This share threshold is structural and avoids nominal-size bias.

Computed metrics:

- PageRank
- Betweenness (approximate, `k=300`, `seed=42`)
- In-strength and out-strength

### Part 2. Digitalisation measures

Two normalised proxies are merged for Italian sectors:

- Variant A: digital intensity

$$
	ext{dig\_intensity}_s = \frac{I\_Soft\_DB_s + I\_RD_s}{VA\_CP_s}
$$

- Variant B: ICT capital share (EUKLEMS)

Crosswalk handling (`Src/utils/constants.py`): NACE-to-ICIO mappings are exploded and aggregated to ICIO level.

For Variant B, source quality is tracked:

- `direct`: direct NACE-to-ICIO match
- `aggregate`: value inherited from broader NACE aggregate

Variant B bottleneck classification uses only direct-source sectors.

### Part 3. Typology and bottleneck classification

A sector is flagged in a variant if:

- PageRank is at or above the 60th percentile
- Digital score is at or below the variant threshold

Thresholds:

- Variant A: 40th percentile digital cutoff
- Variant B: 30th percentile digital cutoff (direct-source subset)

Robust bottleneck = flagged in both variants.

Digital typology (median splits):

- Digital leader
- In transition
- Past adopter
- Structurally lagging
- Unknown (missing one or both digital metrics)

### Part 4. Outputs

Table:

- `outputs/tables/panel_bottleneck_2016_2021.csv`

Figures:

- `outputs/figures/figA_bottleneck_panel_2016_2021.png`
- `outputs/figures/figB_typology_scatter_2021.png`
- `outputs/figures/figC_coeff_pagerank_vs_digital_2021.png`

---

## Corrections Implemented (April 2026)

1. Typology assignment no longer pushes missing-data sectors into Structurally lagging; they remain Unknown.
2. Heatmap row sorting now reflects all non-zero bottleneck statuses.
3. Variant B threshold plotting handles undefined direct-source cutoffs safely.
4. Bubble-size scaling now guards against zero denominators.
5. Legend style warning in Figure A was removed.
6. Duplicate `C16-C18` key in `NACE_TO_ICIO` was removed to prevent silent overwrite ambiguity.

---

## Core Result

Across both digital proxies, central Italian sectors tend to be less digitally advanced than less-central sectors. The persistence of robust bottlenecks across 2016-2021 suggests the issue is structural, not a one-year anomaly.

---

## Important Caveats

1. Coverage constraints: some ICIO sectors are unavailable or only available through aggregate-source mappings.
2. Data horizon alignment: because Intan-Invest ends in 2021, the validated panel window is 2016-2021.
3. Crosswalk granularity: one-to-many mappings assign shared values across sub-sectors, which is a necessary approximation.

---

## Installation

```bash
pip install pandas numpy networkx matplotlib
```

---

Data sources: OECD Inter-Country Input-Output Tables (2023 edition), Intan-Invest (European Investment Bank / EU Commission), EUKLEMS Growth Accounts.
