# Refactoring / implementation: code review fixes

## Summary

Applies fixes from a full code review of core functionality (dashboard, pipeline, database).

## Critical

- **Security:** No hardcoded Supabase credentials. `pipeline/export_to_supabase_api.py` now uses `SUPABASE_URL` and `SUPABASE_ANON_KEY` environment variables. Script logic is in `export_to_supabase()` and run via `if __name__ == "__main__"`.
- **Dashboard save:** `save_prospect_activity()` was a no-op because `get_connection()` returns `None`. Saving now uses a Supabase client from `st.secrets["database"]` via `get_supabase_client()` so **Save Activity** persists.
- **Export CSV:** The Export to CSV button was unreachable (code lived after `st.stop()`). The export section is now above `st.stop()` so the button is visible and usable.
- **State key:** Org detail used `org['State']` while data is lowercased; fixed with `org.get('state', org.get('State', 'N/A'))`.
- **Asset filter:** `asset_range` was only set inside `if 'totalassetseoy' in latest_data.columns` but used outside, risking `NameError`. A default `asset_range` is set and the filter is applied only when the column exists.
- **Export API:** Added **executive_compensation** to the Supabase API export (previously only orgs, filings, metrics, prospect).

## Other

- **requirements.txt:** Removed duplicate `supabase>=2.0.0`.
- **Dashboard:** Replaced bare `except:` with `except Exception:` when reading password from secrets.
- **Parse:** `get_text()` in `parse_and_load.py` now catches `AttributeError`, `IndexError`, `TypeError` instead of bare `except: pass`.
- **Validate pipeline:** Table names for count queries use a fixed tuple instead of f-strings.
- **download_bmf_and_filter_eins.py:** Moved `os.makedirs('data', exist_ok=True)` from module level into `download_bmf_and_filter()` so it only runs when the script is executed.
- **Dashboard:** Removed redundant identity renames in `display_df.rename(columns=...)`.
- **CODE_REVIEW.md** added with full review notes and change summary.

## Testing

- **Dashboard:** Run Streamlit; confirm login, filters, org list, expanders, **Export to CSV** button, and that **Save Activity** on org detail persists to Supabase.
- **Export API:** Set `SUPABASE_URL` and `SUPABASE_ANON_KEY`, run `python pipeline/export_to_supabase_api.py`, and confirm all five tables (including `executive_compensation`) are populated.
- **Pipeline:** Run `validate_pipeline.py` and other pipeline steps as usual.
