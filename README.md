# Internet and Network Economics - Group Project

## EUKLEMS Growth Accounts Dataset Analysis

This project performs exploratory data analysis on the EUKLEMS Growth Accounts dataset to assess feasibility of:
- Constructing industry-level productivity time series
- Building inter-industry productivity co-movement networks
- Overlaying AI/software intensity measures
- Performing dynamic (pre/post 2015) comparison

## Setup Instructions

### Data Requirements

1. Create a `data/` folder in the project root directory
2. Download the EUKLEMS Growth Accounts dataset (CSV format)
3. Place the dataset file in the `data/` folder
4. If your dataset filename differs from `growth accounts.csv`, update the path in [analysis.ipynb](analysis.ipynb):

```python
# Update this line with your dataset filename
data_path = Path('data/growth accounts.csv')
```

### Dependencies

Install required Python packages:
```bash
pip install pandas numpy matplotlib seaborn
```

## Project Structure

```
.
├── analysis.ipynb          # Main exploratory data analysis notebook
├── data/                   # Dataset folder (not tracked by git)
│   └── growth accounts.csv # EUKLEMS dataset (add manually)
└── README.md              # This file
```

## Usage

1. Ensure dataset is placed in `data/` folder
2. Update the data path in the notebook if necessary
3. Open `analysis.ipynb` in Jupyter or VS Code
4. Run all cells to perform the exploratory data analysis

## Note

The `data/` folder is excluded from version control via `.gitignore` to avoid committing large dataset files.