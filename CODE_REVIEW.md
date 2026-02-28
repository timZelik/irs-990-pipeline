# Code Review: IRS 990 Core Functionality

## Overview

Review covers: **dashboard** (Streamlit app), **pipeline** (BMF download, index match, XML download, parse_and_load, export to Supabase, validation), and **database** (SQLite schema and setup).

---

## Critical issues

### 1. **Hardcoded Supabase credentials** (`pipeline/export_to_supabase_api.py`)

- **Issue:** Supabase `url` and `key` are hardcoded. This is a serious security risk if the repo is ever shared or public.
- **Fix:** Load from environment variables (e.g. `SUPABASE_URL`, `SUPABASE_ANON_KEY`) or a local config file that is gitignored.

### 2. **Prospect activity save does nothing** (`dashboard/app.py`)

- **Issue:** `save_prospect_activity()` uses `get_connection()`, which returns `None`. The dashboard uses Supabase via `fetch_table_cached` (Streamlit secrets), but the save path checks `if conn is None: return`, so "Save Activity" never persists to Supabase.
- **Fix:** Implement saving via Supabase client using the same credentials as `fetch_table_cached` (e.g. from `st.secrets`), and use Supabase `update`/`upsert` for prospect_activity.

### 3. **Unreachable code and missing Export CSV** (`dashboard/app.py`)

- **Issue:** After the expandable org list loop, `st.stop()` is called. The Export CSV button and its column logic are below `st.stop()`, so they never run.
- **Fix:** Move the Export CSV section above `st.stop()`, or remove `st.stop()` and structure the flow so the export is reachable (e.g. after the table/expandable section, before any conditional stop).

### 4. **Possible KeyError in org detail** (`dashboard/app.py`)

- **Issue:** In `show_org_detail()`, `org['State']` is used (capital S). Elsewhere columns are lowercased (`df.columns = [c.lower() for c in df.columns]`), so the key should be `'state'` for consistency.
- **Fix:** Use `org.get('state', org.get('State', 'N/A'))` or ensure a single convention (e.g. always lowercase from Supabase).

### 5. **Asset filter variable scope** (`dashboard/app.py`)

- **Issue:** `asset_range` is set only inside `if 'totalassetseoy' in latest_data.columns`. The filter `latest_data = latest_data[(latest_data['totalassetseoy'] >= asset_range[0]) ...]` runs outside that block, which can raise `NameError` if the column is missing.
- **Fix:** Define a default `asset_range` before the `if`, or keep the filter inside the same `if` block so it only runs when the slider (and column) exists.

---

## Medium issues

### 6. **Duplicate dependency** (`requirements.txt`)

- **Issue:** `supabase>=2.0.0` is listed twice.
- **Fix:** Keep a single line.

### 7. **Bare except in login** (`dashboard/app.py`)

- **Issue:** `try: default_password = st.secrets.get("password", "")` with `except:` can hide other errors (e.g. missing secrets file).
- **Fix:** Catch a specific exception (e.g. `except Exception`) and optionally log; or use `st.secrets.get("password", "")` and document that missing secrets must be configured.

### 8. **Bare except in XML parsing** (`pipeline/parse_and_load.py`)

- **Issue:** In `get_text()`, `except: pass` swallows all exceptions and returns None, making debugging harder.
- **Fix:** Catch a specific exception (e.g. `Exception`) and optionally log, or re-raise after logging.

### 9. **SQL injection-style pattern** (`pipeline/validate_pipeline.py`)

- **Issue:** `cursor.execute(f"SELECT COUNT(*) FROM {table}")` with `table` from a list. Currently the list is fixed and safe, but the pattern is fragile.
- **Fix:** Use a known allowlist and keep the table name out of the query string (e.g. map table name to a constant), or use parameterized identifier if the driver supports it (SQLite does not for table names), so at least restrict to allowlist only.

### 10. **Export script omits executive_compensation** (`pipeline/export_to_supabase_api.py`)

- **Issue:** Script deletes and inserts organizations, filings, derived_metrics, prospect_activity but does not handle `executive_compensation`. The psycopg2 script `export_to_supabase.py` does include it. Validation expects all five tables.
- **Fix:** Add delete + batch insert for `executive_compensation` in the API-based export so pipeline validation and dashboard stay in sync.

---

## Minor / consistency

### 11. **Side effect on import** (`pipeline/download_bmf_and_filter_eins.py`)

- **Issue:** `os.makedirs('data', exist_ok=True)` at module level runs on import.
- **Fix:** Move into `download_bmf_and_filter()` or `if __name__ == "__main__"` so the script only creates dirs when run.

### 12. **Duplicate column rename** (`dashboard/app.py`)

- **Issue:** In display_df rename, `'phone': 'phone'` is redundant.
- **Fix:** Omit identity renames for clarity.

### 13. **Lead score normalization** (`pipeline/parse_and_load.py`)

- **Issue:** `compute_lead_score` divides by `weight_sum` and scales to 0–100. When some components are None, the effective weights change. Document or add a comment that the score is a weighted average of available components only.

---

## Positive notes

- Clear separation: pipeline (download → parse → export) vs dashboard (read + minimal write).
- Supabase used for dashboard read path with pagination and caching.
- SQLite schema has sensible unique constraints and indexes.
- Parse logic uses lxml and namespaces correctly; filtering by state and assets in parse keeps data focused.

---

## Summary of changes in this branch

- Remove hardcoded credentials from `export_to_supabase_api.py`; use env vars.
- Implement `save_prospect_activity` in the dashboard using Supabase client from secrets.
- Move Export CSV above `st.stop()` and fix asset filter scope and State key in dashboard.
- Fix duplicate supabase in requirements.txt.
- Harden `get_text` in parse_and_load and table name usage in validate_pipeline.
- Add executive_compensation to export_to_supabase_api.py.
- Move `os.makedirs` in download_bmf_and_filter_eins into main/function.
