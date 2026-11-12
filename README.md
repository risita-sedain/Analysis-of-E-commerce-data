# E-commerce report: Python cleaning and updated findings

This project uses Python for **data cleaning and recalculating the report's updated findings only**. The original report's Power BI charts are not recreated here. Its report and PDF are not included.

## Contents

- `data/raw/customer_behavior.csv` — unmodified Kaggle source file.
- `src/clean_and_check.py` — Python cleaning, validation and five finding calculations.
- `data/processed/customer_behavior_clean.csv` — cleaned records with a derived age group.
- `outputs/` — grouped summaries and metadata from the most recent run.
- `requirements.txt` — Python dependency.

## Run

```bash
python -m venv .venv
source .venv/bin/activate       # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
python src/clean_and_check.py
```

The default analyzes every record. To filter only the analysis, optionally run:

```bash
python src/clean_and_check.py --city "New York"
python src/clean_and_check.py --membership Gold
python src/clean_and_check.py --city "New York" --membership Gold
```

Each run replaces the files in `outputs/`; copy them elsewhere to retain multiple runs. The cleaned CSV always contains **all** source rows. Some comparisons may be unavailable or inappropriate in a filtered subset; consult the record counts and filter metadata.

## Cleaning and interpretation

The script standardizes text and data types, checks required columns, unique customer IDs and basic value ranges, and derives age groups. It does **not** fill missing values or remove repeated profiles: the two missing satisfaction values remain missing, and records with unique customer IDs are retained even when other attributes repeat. The source does not establish currency, calendar coverage or representativeness.

The five summary files correspond to the report's age, membership, discount, city, and items/spend findings. Group totals and averages are descriptive. The Pearson correlation describes association, not causation or proportionality. Because the original PDF does not cite its precise dataset link, this is a very strong matching source, not independently proven to be the authors' original copy.

Dataset: Laksika Tharmalingam, [E-commerce Customer Behavior Dataset](https://www.kaggle.com/datasets/uom190346a/e-commerce-customer-behavior-dataset), Kaggle, version 1; source lists CC0.
