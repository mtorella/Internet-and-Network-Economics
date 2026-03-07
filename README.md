# Internet and Network Economics — Group Project

## Digital Transition, Supply-Chain Structure and Productivity in the Italian Economy

This project combines input-output economics, network analysis, and productivity econometrics to study Italy's position in the global digital-transition landscape. Using the OECD Inter-Country Input-Output (ICIO) table (2022 release) and the EUKLEMS Growth Accounts, it identifies which Italian sectors are structurally central but digitally underinvested — the so-called *bottleneck* sectors — and maps those findings to Industria 4.0 policy instruments.

The analysis is structured as a pipeline of Jupyter notebooks that must be run in order.

---

## Project Structure

```
.
├── notebooks/
│   ├── 1_EDA_EUKLEMS.ipynb          # EUKLEMS data exploration and feasibility assessment
│   └── 2_EDA_IO_Matrix.ipynb        # ICIO matrix analysis, Leontief inverse, digital intensity
│
├── data/
│   ├── raw/                         # Original source files (not tracked by git)
│   │   ├── 2022.csv                 # OECD ICIO table (2022 release)
│   │   └── growth accounts.csv      # EUKLEMS Growth Accounts
│   └── prepared/                    # Intermediate outputs written by the notebooks (to be populated)
│   
│
├── outputs/
│   ├── figures/                     # All plots (PNG, 150 dpi)
│   └── tables/                      # Exported CSV tables (centrality, regression results, policy ranking)
│
└── README.md
```

---

### Data Sources

| File | Source | Notes |
|------|--------|-------|
| `data/raw/2022.csv` | [OECD ICIO 2023 edition](https://www.oecd.org/sti/ind/inter-country-input-output-tables.htm) | ~4 250 country-sector rows × 4 737 columns; reference year 2022 |
| `data/raw/growth accounts.csv` | [EUKLEMS & INTANProd](https://euklems-intanprod-llee.luiss.it/) | Industry-level TFP, labour productivity, capital services, 2000–2022 |

Both files must be placed in `data/raw/` before running any notebook.

---

### Notebooks

- `1_EDA_EUKLEMS.ipynb` — Explores the structure and coverage of the EUKLEMS Growth Accounts, assesses their suitability for productivity analysis, and prepares a clean industry-level dataset for later merging with ICIO-based indicators.
- `2_EDA_IO_Matrix.ipynb` — Examines the structure of the OECD ICIO table, asserts its validity, and isolates the Z block of intermediate transactions.

## Methodological Notes

### Network Construction
The network is constructed from the ICIO intermediate flow matrix Z by first computing the technical coefficient matrix A, where each entry $a_{ij}$ represents the value of inputs purchased from sector $i$ per unit of output produced by sector $j$. Rather than restricting the analysis to the domestic Italian block alone, which would imply a closed economy assumption, we retain the full international dimension of the matrix. The 50 Italian sectors are kept as individual nodes, while all non-Italian country-sector pairs are aggregated into 50 Rest of World nodes grouped by sector type, for a total of 100 nodes. The weight of each edge between a ROW node and an Italian node is the sum of all input flows from that sector type across all foreign countries into the corresponding Italian sector. This approach preserves the interpretability of an Italy-focused network while correctly accounting for the dependence of Italian sectors on foreign intermediate inputs.