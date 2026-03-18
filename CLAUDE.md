# IRS 990 Pipeline — Project Guidelines for Claude

## Project Purpose
Lead generation tool for a capital/financial services firm. Identifies mid-market nonprofits in
Florida and New York ($1M–$10M in total assets) that likely lack financial advisors, using
public IRS Form 990 data.

## Repository Structure

```
pipeline/          # 6-step ETL pipeline (run in order)
  step 1: download_bmf_and_filter_eins.py
  step 2: download_index_and_match_urls.py
  step 3: download_xml_filings.py
  step 4: parse_and_load.py
  step 5: validate_pipeline.py
  export: export_to_supabase.py       # psycopg2 direct (requires connection string)
  export: export_to_supabase_api.py   # Supabase SDK (preferred, uses env vars)

database/
  schema.sql         # 5 tables: organizations, filings, executive_compensation,
                     #           derived_metrics, prospect_activity
  db_setup.py        # Creates SQLite DB from schema

dashboard/           # Streamlit app — split into focused modules
  app.py             # Entry point: auth, page config, layout (~120 lines)
  data.py            # Supabase data loading + caching
  filters.py         # Sidebar filter rendering + application
  components.py      # Org rows, detail view, metrics, charts, FAQ
```

## Architecture Decisions

- **Local → Cloud**: Pipeline writes to SQLite; export scripts push to Supabase PostgreSQL.
  The dashboard reads exclusively from Supabase (never local SQLite).
- **Dashboard modules**: Keep the 4-file split (app / data / filters / components).
  Do not collapse back into a monolith. Do not add more files unless clearly warranted.
- **Supabase credentials**: Always use `st.secrets["SUPABASE_URL"]` / `st.secrets["SUPABASE_KEY"]`
  in the dashboard. For pipeline scripts, use `SUPABASE_URL` / `SUPABASE_KEY` env vars.
  Never hardcode credentials in source files.
- **No psycopg2 in dashboard**: The dashboard uses the Supabase SDK only. psycopg2 is for
  the direct-export pipeline script.
- **Column naming**: All DataFrames in the dashboard use lowercase column names (enforced
  in `fetch_table_cached`). `legalname` is aliased to `orgname` on load.

## CI/CD Cycle

Every change should follow:
1. Edit code locally
2. Verify no obvious errors (Python syntax, import paths)
3. Commit with a clear message describing *why* not just *what*
4. Push to `main` — Streamlit Community Cloud auto-deploys from `main`

```bash
git add <specific files>
git commit -m "descriptive message"
git push origin main
```

## Running the Pipeline

```bash
python pipeline/download_bmf_and_filter_eins.py
python pipeline/download_index_and_match_urls.py
python pipeline/download_xml_filings.py
PYTHONPATH=. python pipeline/parse_and_load.py
python pipeline/validate_pipeline.py

# Export to Supabase (choose one):
SUPABASE_URL=... SUPABASE_KEY=... python pipeline/export_to_supabase_api.py
# or:
python pipeline/export_to_supabase.py '<postgres_connection_string>'
```

## Running the Dashboard Locally

```bash
streamlit run dashboard/app.py
```

Requires `.streamlit/secrets.toml` with:
```toml
password = "yourpassword"
SUPABASE_URL = "https://..."
SUPABASE_KEY = "eyJ..."
```

## Lead Score Formula

Weighted composite (0–100):
- Revenue Growth YoY × 25
- Program Expense Ratio × 30
- +20 if Operating Surplus > 0
- −Liability-to-Asset Ratio × 15
- −Exec Comp % of Revenue × 10
- Normalized to 0–100 range

## Key Conventions

- Keep pipeline scripts independent and runnable standalone (no shared state between steps)
- Dashboard caches all Supabase reads with 1-hour TTL (`@st.cache_data(ttl=3600)`)
- Pagination is 70 orgs per page (configurable via `PAGE_SIZE` in `app.py`)
- Target scope: FL and NY, 501(c)(3), active, $1M–$10M assets (ASSET_CD 5 or 6)
- Do not over-engineer. Add abstraction only when three or more places need the same logic.
