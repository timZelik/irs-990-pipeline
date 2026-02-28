import sqlite3
import pandas as pd
from supabase import create_client
import sys
import os
import math

SQLITE_DB = "database/nonprofit_intelligence.db"


def clean_value(v):
    if v is None:
        return None
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return None
        if v == int(v):
            return int(v)
        return v
    if isinstance(v, (int, bool)):
        return v
    return v


def clean_record(record):
    return {k: clean_value(v) for k, v in record.items()}


def export_to_supabase():
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_ANON_KEY", "")
    if not url or not key:
        print("Error: Set SUPABASE_URL and SUPABASE_ANON_KEY environment variables.")
        sys.exit(1)
    client = create_client(url, key)

    print("Reading from SQLite...")
    conn = sqlite3.connect(SQLITE_DB)
    orgs = pd.read_sql_query("SELECT * FROM organizations", conn)
    filings = pd.read_sql_query("SELECT * FROM filings", conn)
    exec_comp = pd.read_sql_query("SELECT * FROM executive_compensation", conn)
    metrics = pd.read_sql_query("SELECT * FROM derived_metrics", conn)
    prospect = pd.read_sql_query("SELECT * FROM prospect_activity", conn)
    conn.close()

    print(f"Organizations: {len(orgs)}")
    print(f"Filings: {len(filings)}")
    print(f"Executive compensation: {len(exec_comp)}")
    print(f"Metrics: {len(metrics)}")
    print(f"Prospect: {len(prospect)}")

    print("\nDeleting existing data...")
    client.table("prospect_activity").delete().neq("ein", "").execute()
    client.table("derived_metrics").delete().neq("ein", "").execute()
    client.table("executive_compensation").delete().neq("ein", "").execute()
    client.table("filings").delete().neq("ein", "").execute()
    client.table("organizations").delete().neq("ein", "").execute()
    print("Done!")

    print("\nInserting organizations...")
    orgs.columns = [c.lower() for c in orgs.columns]
    for i in range(0, len(orgs), 100):
        batch = [clean_record(r) for r in orgs.iloc[i : i + 100].to_dict("records")]
        client.table("organizations").insert(batch).execute()
    print(f"  Done! {len(orgs)} orgs")

    print("Inserting filings...")
    filings.columns = [c.lower() for c in filings.columns]
    for i in range(0, len(filings), 100):
        batch = [clean_record(r) for r in filings.iloc[i : i + 100].to_dict("records")]
        client.table("filings").insert(batch).execute()
    print(f"  Done! {len(filings)} filings")

    print("Inserting executive compensation...")
    exec_comp.columns = [c.lower() for c in exec_comp.columns]
    exec_cols = [c for c in exec_comp.columns if c != "execid"]
    exec_comp = exec_comp[exec_cols]
    if len(exec_comp) > 0:
        for i in range(0, len(exec_comp), 100):
            batch = [clean_record(r) for r in exec_comp.iloc[i : i + 100].to_dict("records")]
            client.table("executive_compensation").insert(batch).execute()
        print(f"  Done! {len(exec_comp)} records")
    else:
        print("  (none)")

    print("Inserting metrics...")
    metrics.columns = [c.lower() for c in metrics.columns]
    if len(metrics) > 0:
        for i in range(0, len(metrics), 100):
            batch = [clean_record(r) for r in metrics.iloc[i : i + 100].to_dict("records")]
            client.table("derived_metrics").insert(batch).execute()
        print(f"  Done! {len(metrics)} metrics")
    else:
        print("  (none)")

    print("Inserting prospect activity...")
    prospect.columns = [c.lower() for c in prospect.columns]
    if len(prospect) > 0:
        for i in range(0, len(prospect), 100):
            batch = [clean_record(r) for r in prospect.iloc[i : i + 100].to_dict("records")]
            client.table("prospect_activity").insert(batch).execute()
        print(f"  Done! {len(prospect)} prospect records")
    else:
        print("  (none)")

    print("\nDone! Data exported to Supabase.")


if __name__ == "__main__":
    export_to_supabase()
