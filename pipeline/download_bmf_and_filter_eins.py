import pandas as pd
import requests
import os
from io import StringIO

BMF_URLS = {
    'NY': 'https://www.irs.gov/pub/irs-soi/eo1.csv',
    'FL': 'https://www.irs.gov/pub/irs-soi/eo3.csv',
}

OUTPUT_PATH = 'data/target_eins.csv'


def download_bmf_and_filter():
    os.makedirs('data', exist_ok=True)
    all_orgs = []

    for state, url in BMF_URLS.items():
        print(f"Downloading BMF for {state} from {url}...")
        
        response = requests.get(url, timeout=300)
        response.raise_for_status()
        
        df = pd.read_csv(StringIO(response.text), dtype=str)
        
        print(f"  Total rows: {len(df)}")
        
        filtered = df[
            (df['STATE'] == state) &
            (df['SUBSECTION'] == '03') &
            (df['ASSET_CD'].isin(['5', '6'])) &
            (df['STATUS'] == '01')
        ]
        
        print(f"  After filters: {len(filtered)}")
        all_orgs.append(filtered)
    
    combined = pd.concat(all_orgs, ignore_index=True)
    
    result = combined[['EIN', 'NAME', 'STATE', 'CITY', 'NTEE_CD', 'ASSET_CD', 'ASSET_AMT']].copy()
    result = result.drop_duplicates(subset=['EIN'])
    
    fl_count = len(result[result['STATE'] == 'FL'])
    ny_count = len(result[result['STATE'] == 'NY'])
    total_count = len(result)
    
    result.to_csv(OUTPUT_PATH, index=False)
    
    print(f"FL: {fl_count} orgs | NY: {ny_count} orgs | Total: {total_count}")
    print(f"Saved to {OUTPUT_PATH}")

if __name__ == "__main__":
    download_bmf_and_filter()
