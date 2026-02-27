import pandas as pd
import requests
import os
from io import StringIO

INDEX_URLS = [
    ('2021', 'https://apps.irs.gov/pub/epostcard/990/xml/2021/index_2021.csv'),
    ('2022', 'https://apps.irs.gov/pub/epostcard/990/xml/2022/index_2022.csv'),
    ('2023', 'https://apps.irs.gov/pub/epostcard/990/xml/2023/index_2023.csv'),
    ('2024', 'https://apps.irs.gov/pub/epostcard/990/xml/2024/index_2024.csv'),
    ('2025', 'https://apps.irs.gov/pub/epostcard/990/xml/2025/index_2025.csv'),
    ('2026', 'https://apps.irs.gov/pub/epostcard/990/xml/2026/index_2026.csv'),
]

TARGET_EINS_FILE = 'data/target_eins.csv'
OUTPUT_FILE = 'data/matched_filing_index.csv'

def load_target_eins():
    df = pd.read_csv(TARGET_EINS_FILE, dtype=str)
    return set(df['EIN'].astype(str))

def download_index(year, url):
    print(f"Downloading {year} index from {url}...")
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    df = pd.read_csv(StringIO(response.text), dtype=str)
    print(f"  Total rows in index: {len(df)}")
    return df

def main():
    target_eins = load_target_eins()
    print(f"Loaded {len(target_eins)} target EINs from {TARGET_EINS_FILE}")
    
    all_matches = []
    
    for year, url in INDEX_URLS:
        print("-" * 40)
        df = download_index(year, url)
        
        if 'RETURN_TYPE' not in df.columns or 'EIN' not in df.columns:
            print(f"  WARNING: Missing expected columns. Available: {list(df.columns)}")
            continue
        
        filtered = df[
            (df['RETURN_TYPE'] == '990') &
            (df['EIN'].isin(target_eins))
        ].copy()
        
        filtered['YEAR'] = year
        all_matches.append(filtered)
        
        print(f"  Matched 990 filings: {len(filtered)}")
    
    if all_matches:
        combined = pd.concat(all_matches, ignore_index=True)
        
        available_cols = ['EIN', 'TAXPAYER_NAME', 'TAX_PERIOD', 'OBJECT_ID', 'YEAR']
        result = combined[available_cols].copy()
        result = result.drop_duplicates(subset=['EIN', 'TAX_PERIOD'])
        
        os.makedirs('data', exist_ok=True)
        result.to_csv(OUTPUT_FILE, index=False)
        
        print(f"\nTotal matched: {len(result)}")
        print(f"Saved to {OUTPUT_FILE}")
    else:
        print("\nNo matches found!")

if __name__ == "__main__":
    main()
