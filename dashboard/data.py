import streamlit as st
import pandas as pd
from supabase import create_client


def normalize_url(url):
    """Ensure a URL has a scheme so it renders as a proper hyperlink."""
    if not url:
        return None
    url = url.strip()
    if url.lower() in ('n/a', 'none', ''):
        return None
    if not url.lower().startswith(('http://', 'https://')):
        url = 'https://' + url
    return url


@st.cache_data(ttl=3600)
def fetch_table_cached(table_name, columns="*"):
    try:
        supabase_url = st.secrets["SUPABASE_URL"]
        supabase_key = st.secrets["SUPABASE_KEY"]
        client = create_client(supabase_url, supabase_key)

        all_data = []
        page = 0
        page_size = 1000

        while True:
            response = (
                client.table(table_name)
                .select(columns)
                .range(page * page_size, (page + 1) * page_size - 1)
                .execute()
            )
            if not response.data:
                break
            all_data.extend(response.data)
            if len(response.data) < page_size:
                break
            page += 1

        if all_data:
            df = pd.DataFrame(all_data)
            df.columns = [c.lower() for c in df.columns]
            if 'legalname' in df.columns:
                df = df.rename(columns={'legalname': 'orgname'})
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching {table_name}: {e}")
        return pd.DataFrame()


def fetch_table(table_name, columns="*"):
    return fetch_table_cached(table_name, columns)


def load_summary_data():
    orgs_all = fetch_table("organizations", "*")

    if orgs_all.empty:
        return pd.DataFrame()

    orgs = orgs_all[orgs_all['state'].isin(['FL', 'NY'])]
    if orgs.empty:
        return pd.DataFrame()

    filings = fetch_table("filings")
    metrics = fetch_table("derived_metrics")
    prospect = fetch_table("prospect_activity")

    df = orgs.copy()

    if not filings.empty and 'ein' in filings.columns:
        df = df.merge(filings, on="ein", how="left", suffixes=('', '_fil'))

    if not metrics.empty and 'ein' in metrics.columns and 'taxyear' in metrics.columns:
        df = df.merge(metrics, on=["ein", "taxyear"], how="left", suffixes=('', '_met'))

    if not prospect.empty and 'ein' in prospect.columns:
        df = df.merge(prospect, on="ein", how="left", suffixes=('', '_pros'))

    if 'leadscore' in df.columns:
        df = df.sort_values('leadscore', ascending=False, na_position='last')

    return df


def load_org_details(ein):
    org_df = fetch_table("organizations", "*")
    org_df = org_df[org_df['ein'] == ein]

    filings_df = fetch_table("filings", "*")
    if not filings_df.empty and 'ein' in filings_df.columns:
        filings_df = filings_df[filings_df['ein'] == ein].sort_values('taxyear', ascending=False)
    else:
        filings_df = pd.DataFrame()

    metrics_df = fetch_table("derived_metrics", "*")
    if not metrics_df.empty and 'ein' in metrics_df.columns:
        metrics_df = metrics_df[metrics_df['ein'] == ein].sort_values('taxyear', ascending=False)
    else:
        metrics_df = pd.DataFrame()

    exec_df = fetch_table("executive_compensation", "*")
    if not exec_df.empty and 'ein' in exec_df.columns:
        exec_df = exec_df[exec_df['ein'] == ein].sort_values('taxyear', ascending=False)
    else:
        exec_df = pd.DataFrame()

    prospect_df = fetch_table("prospect_activity", "*")
    if not prospect_df.empty and 'ein' in prospect_df.columns:
        prospect_df = prospect_df[prospect_df['ein'] == ein]
    else:
        prospect_df = pd.DataFrame()

    return org_df, filings_df, metrics_df, exec_df, prospect_df


def save_prospect_activity(ein, contact_status, is_watchlisted, notes):
    try:
        supabase_url = st.secrets["SUPABASE_URL"]
        supabase_key = st.secrets["SUPABASE_KEY"]
        conn = create_client(supabase_url, supabase_key)

        existing = conn.table("prospect_activity").select("*").eq("ein", ein).execute()

        if existing.data:
            conn.table("prospect_activity").update({
                "contactstatus": contact_status,
                "iswatchlisted": 1 if is_watchlisted else 0,
                "privatenotes": notes,
            }).eq("ein", ein).execute()
        else:
            conn.table("prospect_activity").insert({
                "ein": ein,
                "contactstatus": contact_status,
                "iswatchlisted": 1 if is_watchlisted else 0,
                "privatenotes": notes,
            }).execute()
    except Exception as e:
        st.error(f"Error saving: {e}")
