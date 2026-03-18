"""
Export SQLite data to Supabase via the Supabase REST API (SDK).

Usage:
    SUPABASE_URL=https://... SUPABASE_KEY=... python pipeline/export_to_supabase_api.py

Credentials are read from environment variables SUPABASE_URL and SUPABASE_KEY.
"""

import math
import os
import sqlite3
import sys

import pandas as pd
from supabase import create_client

SQLITE_DB = "database/nonprofit_intelligence.db"


def get_client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        print("Error: SUPABASE_URL and SUPABASE_KEY environment variables must be set.")
        sys.exit(1)
    return create_client(url, key)


def clean_value(v):
    if v is None:
        return None
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return None
        if v == int(v):
            return int(v)
    return v


def clean_record(record):
    return {k: clean_value(v) for k, v in record.items()}


def insert_batched(client, table_name, df, batch_size=100):
    df.columns = [c.lower() for c in df.columns]
    for i in range(0, len(df), batch_size):
        batch = [clean_record(r) for r in df.iloc[i:i + batch_size].to_dict('records')]
        client.table(table_name).insert(batch).execute()
    print(f"  {len(df)} records inserted into {table_name}")


def main():
    client = get_client()

    print("Reading from SQLite...")
    conn = sqlite3.connect(SQLITE_DB)
    orgs = pd.read_sql_query("SELECT * FROM organizations", conn)
    filings = pd.read_sql_query("SELECT * FROM filings", conn)
    metrics = pd.read_sql_query("SELECT * FROM derived_metrics", conn)
    prospect = pd.read_sql_query("SELECT * FROM prospect_activity", conn)
    conn.close()

    print(f"  Organizations: {len(orgs)}")
    print(f"  Filings:       {len(filings)}")
    print(f"  Metrics:       {len(metrics)}")
    print(f"  Prospect:      {len(prospect)}")

    print("\nDeleting existing data...")
    client.table('prospect_activity').delete().neq('ein', '').execute()
    client.table('derived_metrics').delete().neq('ein', '').execute()
    client.table('filings').delete().neq('ein', '').execute()
    client.table('organizations').delete().neq('ein', '').execute()

    print("\nInserting data...")
    insert_batched(client, 'organizations', orgs)
    insert_batched(client, 'filings', filings)
    if len(metrics) > 0:
        insert_batched(client, 'derived_metrics', metrics)
    if len(prospect) > 0:
        insert_batched(client, 'prospect_activity', prospect)

    print("\nDone! Data exported to Supabase.")


if __name__ == "__main__":
    main()
