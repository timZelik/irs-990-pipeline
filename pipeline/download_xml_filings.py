import pandas as pd
import requests
import zipfile
import io
import os
import argparse

INPUT_FILE = 'data/matched_filing_index.csv'
OUTPUT_DIR = 'data/raw_xml'
FAILED_LOG = 'data/failed_downloads.log'

ZIP_SUFFIXES = ['01A', '02A', '03A', '04A', '05A', '06A', '07A',
                '08A', '09A', '10A', '11A', '11B', '11C', '12A']

def build_zip_urls():
    base = "https://apps.irs.gov/pub/epostcard/990/xml"
    urls = []
    for year in [2021, 2022, 2023, 2024, 2025, 2026]:
        for suffix in ZIP_SUFFIXES:
            url = f"{base}/{year}/{year}_TEOS_XML_{suffix}.zip"
            urls.append((year, url))
    return urls

def load_matched_filings():
    df = pd.read_csv(INPUT_FILE, dtype=str)
    return df

def download_from_zips(object_id_to_ein, filings_df):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    zip_urls = build_zip_urls()
    
    ein_to_taxperiod = {}
    for _, row in filings_df.iterrows():
        ein = str(row['EIN'])
        tp = str(row['TAX_PERIOD'])
        if ein not in ein_to_taxperiod:
            ein_to_taxperiod[ein] = tp
    
    extracted = 0
    already_exists = 0
    
    for year, zip_url in zip_urls:
        try:
            print(f"Streaming {zip_url}...")
            response = requests.get(zip_url, stream=True, timeout=300)
            if response.status_code == 404:
                print(f"  Not found (skipping)")
                continue
            
            response.raise_for_status()
            zip_bytes = io.BytesIO(response.content)
            
            with zipfile.ZipFile(zip_bytes) as zf:
                for filename in zf.namelist():
                    if not filename.endswith('_public.xml'):
                        continue
                    
                    object_id = filename.replace('_public.xml', '').split('/')[-1]
                    
                    if object_id not in object_id_to_ein:
                        continue
                    
                    ein = object_id_to_ein[object_id]
                    tax_period = ein_to_taxperiod.get(ein, 'unknown')
                    
                    save_path = os.path.join(OUTPUT_DIR, f"{ein}_{tax_period}.xml")
                    
                    if os.path.exists(save_path):
                        already_exists += 1
                    else:
                        xml_content = zf.read(filename)
                        with open(save_path, 'wb') as f:
                            f.write(xml_content)
                        extracted += 1
                        if extracted % 25 == 0:
                            print(f"  Extracted {extracted} files so far...")
            
            print(f"  Done with {zip_url.split('/')[-1]}")
            
        except Exception as e:
            print(f"  Error with {zip_url}: {e}")
    
    return extracted, already_exists

def main():
    parser = argparse.ArgumentParser(description='Download IRS 990 XML filings')
    parser.add_argument('--sample', type=int, default=None,
                        help='Only extract first N files (for testing)')
    args = parser.parse_args()
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    df = load_matched_filings()
    print(f"Loaded {len(df)} matched filings")
    
    if args.sample:
        df = df.head(args.sample)
        print(f"Running in SAMPLE mode: processing first {args.sample} files")
    
    object_id_to_ein = {}
    for _, row in df.iterrows():
        oid = str(row['OBJECT_ID'])
        ein = str(row['EIN'])
        object_id_to_ein[oid] = ein
    
    print(f"Target OBJECT_IDs: {len(object_id_to_ein)}")
    print(f"Target EINs: {len(set(object_id_to_ein.values()))}")
    
    print("\n--- Starting ZIP streaming ---")
    
    zip_extracted, zip_exists = download_from_zips(object_id_to_ein, df)
    
    print("\n" + "=" * 50)
    print(f"Download complete!")
    print(f"  ZIP extracted: {zip_extracted}")
    print(f"  Already existed: {zip_exists}")

if __name__ == "__main__":
    main()
