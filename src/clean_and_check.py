#!/usr/bin/env python3
"""Clean the matching Kaggle customer file and recalculate the report's five findings."""
import argparse
import hashlib
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATASET = 'https://www.kaggle.com/datasets/uom190346a/e-commerce-customer-behavior-dataset'
SOURCE = ROOT / 'data/raw/customer_behavior.csv'
FIELDS = ['Customer ID', 'Gender', 'Age', 'City', 'Membership Type', 'Total Spend',
          'Items Purchased', 'Average Rating', 'Discount Applied',
          'Days Since Last Purchase', 'Satisfaction Level']
NUMERIC = ['Customer ID', 'Age', 'Total Spend', 'Items Purchased', 'Average Rating', 'Days Since Last Purchase']
TEXT = ['Gender', 'City', 'Membership Type', 'Satisfaction Level']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--city', help='Optional exact city name, e.g. "New York"')
    parser.add_argument('--membership', choices=['Gold', 'Silver', 'Bronze'], help='Optional membership filter')
    args = parser.parse_args()
    for directory in [ROOT / 'data/processed', ROOT / 'outputs']:
        directory.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(SOURCE)
    missing_fields = set(FIELDS) - set(raw.columns)
    if missing_fields:
        raise ValueError(f'Missing required columns: {sorted(missing_fields)}')
    data = raw[FIELDS].copy()
    for col in TEXT:
        data[col] = data[col].astype('string').str.strip().replace('', pd.NA)
    for col in NUMERIC:
        original_missing = data[col].isna().sum()
        data[col] = pd.to_numeric(data[col], errors='coerce')
        if data[col].isna().sum() > original_missing:
            raise ValueError(f'Unparseable numeric value in {col}; review source')
    flags = data['Discount Applied'].astype('string').str.strip().str.lower()
    if not set(flags.dropna().unique()).issubset({'true', 'false'}):
        raise ValueError('Unexpected discount value; review source')
    data['Discount Applied'] = flags.map({'true': True, 'false': False}).astype('boolean')
    if data['Customer ID'].isna().any() or data['Customer ID'].duplicated().any():
        raise ValueError('Missing or duplicate customer IDs require investigation')
    if not data['Age'].dropna().between(0, 120).all() or not data['Average Rating'].dropna().between(0, 5).all():
        raise ValueError('Unexpected age or rating; review source')
    if not (data[['Total Spend', 'Items Purchased', 'Days Since Last Purchase']].dropna() >= 0).all().all():
        raise ValueError('Negative values require investigation')
    data['Age Group'] = pd.cut(data['Age'], [0, 24, 34, 44, 54, 120],
                               labels=['0-24', '25-34', '35-44', '45-54', '55+'], include_lowest=True)
    # Different customer IDs can share attributes. Never delete on that basis alone.
    repeat_profiles = int(data.duplicated(subset=[c for c in FIELDS if c != 'Customer ID']).sum())
    data.to_csv(ROOT / 'data/processed/customer_behavior_clean.csv', index=False)

    selected = data.copy()
    if args.city:
        available = sorted(data['City'].dropna().unique().tolist())
        if args.city not in available:
            raise ValueError(f'City not found. Available: {", ".join(available)}')
        selected = selected[selected['City'] == args.city]
    if args.membership:
        selected = selected[selected['Membership Type'] == args.membership]
    if selected.empty:
        raise ValueError('The requested filters select no records. No findings were generated.')

    def summary(column):
        return (selected.groupby(column, observed=True, dropna=False)
                .agg(records=('Customer ID', 'size'), total_items=('Items Purchased', 'sum'),
                     average_items=('Items Purchased', 'mean'), total_spend=('Total Spend', 'sum'),
                     average_spend=('Total Spend', 'mean'))
                .reset_index())

    for name, column in [('age_group', 'Age Group'), ('membership', 'Membership Type'),
                         ('discount', 'Discount Applied'), ('city', 'City'),
                         ('items', 'Items Purchased')]:
        summary(column).to_csv(ROOT / f'outputs/{name}_summary.csv', index=False)
    pairs = selected[['Items Purchased', 'Total Spend']].dropna()
    correlation = pairs['Items Purchased'].corr(pairs['Total Spend']) if len(pairs) >= 2 else float('nan')
    evidence = {
        'source': DATASET,
        'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'grain': 'one source record per customer ID',
        'raw_rows': int(len(raw)), 'cleaned_rows': int(len(data)), 'analysis_rows': int(len(selected)),
        'filters': {'city': args.city, 'membership': args.membership},
        'missing_by_column': {k: int(v) for k, v in data[FIELDS].isna().sum().items()},
        'exact_duplicate_rows': int(raw.duplicated().sum()),
        'repeat_profiles_excluding_customer_id': repeat_profiles,
        'complete_item_spend_pairs': int(len(pairs)),
        'item_spend_pearson_correlation': None if pd.isna(correlation) else float(correlation),
        'population': 'All cleaned records unless command-line filters are specified.',
        'currency_and_period': 'Not specified by the source.',
        'interpretation': 'Group differences and correlation are descriptive and do not prove causation or proportionality.'
    }
    # Independent arithmetic check against the selected source rows.
    assert int(summary('Membership Type')['total_items'].sum()) == int(selected['Items Purchased'].sum())
    assert abs(float(summary('City')['total_spend'].sum()) - float(selected['Total Spend'].sum())) < 1e-7
    (ROOT / 'outputs/analysis_metadata.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print(f"Cleaned {len(data)} records; analyzed {len(selected)} records.")
    print(f"Item/spend Pearson correlation: {correlation:.3f}" if pd.notna(correlation) else 'Correlation unavailable for selected records.')
    print('Output files: data/processed/customer_behavior_clean.csv and outputs/*.csv, analysis_metadata.json')


if __name__ == '__main__':
    main()
