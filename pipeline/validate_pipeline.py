import os
import sqlite3

DB_PATH = "database/nonprofit_intelligence.db"
TARGET_EINS_FILE = "data/target_eins.csv"
MATCHED_INDEX_FILE = "data/matched_filing_index.csv"
XML_DIR = "data/raw_xml"

def count_csv_lines(filepath):
    if not os.path.exists(filepath):
        return 0
    with open(filepath, 'r') as f:
        return sum(1 for _ in f) - 1

def count_xml_files():
    if not os.path.exists(XML_DIR):
        return 0
    return len([f for f in os.listdir(XML_DIR) if f.endswith('.xml')])

def count_db_records():
    if not os.path.exists(DB_PATH):
        return {t: 0 for t in ['organizations', 'filings', 'executive_compensation', 'derived_metrics', 'prospect_activity']}
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    allowed_tables = ('organizations', 'filings', 'executive_compensation', 'derived_metrics', 'prospect_activity')
    counts = {}
    for table in allowed_tables:
        try:
            cursor.execute("SELECT COUNT(*) FROM " + table)
            counts[table] = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            counts[table] = 0
    
    conn.close()
    return counts

def main():
    print("=" * 60)
    print("PIPELINE VALIDATION SUMMARY")
    print("=" * 60)
    
    ein_count = count_csv_lines(TARGET_EINS_FILE)
    index_count = count_csv_lines(MATCHED_INDEX_FILE)
    xml_count = count_xml_files()
    db_counts = count_db_records()
    
    print(f"\nData Files:")
    print(f"  target_eins.csv:           {ein_count:>6} EINs")
    print(f"  matched_filing_index.csv:  {index_count:>6} rows")
    print(f"  raw_xml/ directory:        {xml_count:>6} XML files")
    
    print(f"\nDatabase Records:")
    print(f"  organizations:            {db_counts.get('organizations', 0):>6} records")
    print(f"  filings:                  {db_counts.get('filings', 0):>6} records")
    print(f"  executive_compensation:   {db_counts.get('executive_compensation', 0):>6} records")
    print(f"  derived_metrics:          {db_counts.get('derived_metrics', 0):>6} records")
    print(f"  prospect_activity:         {db_counts.get('prospect_activity', 0):>6} records")
    
    print("\n" + "=" * 60)
    print("PIPELINE HEALTH CHECK:")
    print("=" * 60)
    
    health = []
    
    if ein_count > 0:
        health.append("✓ Target EINs downloaded")
    else:
        health.append("✗ No target EINs - run download_bmf_and_filter_eins.py")
    
    if index_count > 0:
        health.append("✓ Matched filing index found")
    else:
        health.append("✗ No matched filings - run download_index_and_match_urls.py")
    
    if xml_count > 0:
        health.append("✓ XML files downloaded")
    else:
        health.append("✗ No XML files - run download_xml_filings.py")
    
    if db_counts.get('organizations', 0) > 0:
        health.append("✓ Database populated")
    else:
        health.append("✗ Database empty - run parse_and_load.py")
    
    if db_counts.get('derived_metrics', 0) > 0:
        health.append("✓ Derived metrics computed")
    else:
        health.append("✗ No derived metrics - run parse_and_load.py")
    
    for item in health:
        print(f"  {item}")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
