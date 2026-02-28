import sqlite3
import pandas as pd
from supabase import create_client
import sys
import math

url = 'https://wvrmrgfowzbonjzgtahi.supabase.co'
key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind2cm1yZ2Zvd3pib25qemd0YWhpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIyMTcyNzIsImV4cCI6MjA4Nzc5MzI3Mn0.4Za5i2IfF6lDCog_pSJf1_lHXfhXAl78un1SWNs5x9c'

client = create_client(url, key)

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

print("Reading from SQLite...")
conn = sqlite3.connect(SQLITE_DB)
orgs = pd.read_sql_query("SELECT * FROM organizations", conn)
filings = pd.read_sql_query("SELECT * FROM filings", conn)
metrics = pd.read_sql_query("SELECT * FROM derived_metrics", conn)
prospect = pd.read_sql_query("SELECT * FROM prospect_activity", conn)
conn.close()

print(f"Organizations: {len(orgs)}")
print(f"Filings: {len(filings)}")
print(f"Metrics: {len(metrics)}")
print(f"Prospect: {len(prospect)}")

# Delete existing data first
print("\nDeleting existing data...")
client.table('prospect_activity').delete().neq('ein', '').execute()
client.table('derived_metrics').delete().neq('ein', '').execute()
client.table('filings').delete().neq('ein', '').execute()
client.table('organizations').delete().neq('ein', '').execute()
print("Done!")

print("\nInserting organizations...")
orgs.columns = [c.lower() for c in orgs.columns]
for i in range(0, len(orgs), 100):
    batch = [clean_record(r) for r in orgs.iloc[i:i+100].to_dict('records')]
    client.table('organizations').insert(batch).execute()
print(f"  Done! {len(orgs)} orgs")

print("Inserting filings...")
filings.columns = [c.lower() for c in filings.columns]
for i in range(0, len(filings), 100):
    batch = [clean_record(r) for r in filings.iloc[i:i+100].to_dict('records')]
    client.table('filings').insert(batch).execute()
print(f"  Done! {len(filings)} filings")

print("Inserting metrics...")
metrics.columns = [c.lower() for c in metrics.columns]
if len(metrics) > 0:
    for i in range(0, len(metrics), 100):
        batch = [clean_record(r) for r in metrics.iloc[i:i+100].to_dict('records')]
        client.table('derived_metrics').insert(batch).execute()
    print(f"  Done! {len(metrics)} metrics")

print("Inserting prospect activity...")
prospect.columns = [c.lower() for c in prospect.columns]
if len(prospect) > 0:
    for i in range(0, len(prospect), 100):
        batch = [clean_record(r) for r in prospect.iloc[i:i+100].to_dict('records')]
        client.table('prospect_activity').insert(batch).execute()
    print(f"  Done! {len(prospect)} prospect records")

print("\nDone! Data exported to Supabase.")
