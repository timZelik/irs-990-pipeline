import streamlit as st
import pandas as pd
from data import load_summary_data
from filters import apply_sidebar_filters
from components import render_key_metrics, render_additional_insights, render_org_row, show_org_detail, render_faq

# ── Auth ──────────────────────────────────────────────────────────────────────

if 'password_correct' not in st.session_state:
    st.session_state['password_correct'] = False

if not st.session_state['password_correct']:
    st.title("🔒 IRS 990 FL & NY Search")
    st.markdown("This dashboard is password protected.")

    try:
        default_password = st.secrets.get("password", "")
    except Exception:
        default_password = ""

    with st.form("login_form"):
        password = st.text_input("Enter password to access:")
        submitted = st.form_submit_button("Access Dashboard")
        if submitted:
            if password == default_password and default_password:
                st.session_state['password_correct'] = True
                st.rerun()
            else:
                st.error("Incorrect password. Please contact the owner for access.")
    st.stop()

# ── Page config & global styles ───────────────────────────────────────────────

st.set_page_config(page_title="Nonprofit Intelligence", layout="wide")
st.markdown("""
<style>
    .stButton > button {
        background-color: #00C853 !important;
        color: #000 !important;
    }
    [data-testid="stMetricValue"] {
        color: #00C853 !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Dashboard layout ──────────────────────────────────────────────────────────

def show_dashboard():
    st.title("IRS 990 FL & NY Search")
    tab1, tab2 = st.tabs(["Dashboard", "FAQ & Help"])

    with tab2:
        render_faq()

    with tab1:
        df = load_summary_data()

        if df.empty:
            st.warning("No data available. Please run the data pipeline first.")
            return

        required_cols = ['ein', 'orgname', 'taxyear']
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            st.warning(f"Missing columns in data: {missing_cols}. Please run the data pipeline.")
            return

        if df['taxyear'].isna().all():
            st.warning("No filing data available. Please run the data pipeline first.")
            return

        if 'contactstatus' in df.columns:
            df['contactstatus'] = df['contactstatus'].fillna('not_contacted')
        if 'iswatchlisted' in df.columns:
            df['iswatchlisted'] = df['iswatchlisted'].fillna(0)

        # One row per org (most recent year)
        latest_data = (
            df.sort_values('taxyear', ascending=False)
            .drop_duplicates(subset=['ein'], keep='first')
        )

        # Sidebar filters
        latest_data = apply_sidebar_filters(latest_data)

        # Org name search (main area)
        search_query = st.text_input("Search organizations", "")
        if search_query:
            latest_data = latest_data[
                latest_data['orgname'].str.contains(search_query, case=False, na=False)
            ]

        latest_data = latest_data.sort_values('taxyear', ascending=False)

        # Summary metrics
        render_key_metrics(latest_data)
        render_additional_insights(latest_data)

        st.markdown("### Organization List")

        # Build display DataFrame
        display_cols = [
            'orgname', 'phone', 'principalofficer', 'city', 'state', 'taxyear',
            'totalassetseoy', 'totalrevenuecy', 'revenuegrowthyoy', 'programexpenseratio', 'leadscore',
        ]
        display_df = latest_data[display_cols].copy()
        display_df['phone'] = display_df['phone'].apply(lambda x: x if pd.notna(x) else "N/A")
        display_df['totalassetseoy'] = display_df['totalassetseoy'].apply(
            lambda x: f"${x/1_000_000:.1f}M" if pd.notna(x) else "N/A")
        display_df['totalrevenuecy'] = display_df['totalrevenuecy'].apply(
            lambda x: f"${x/1_000_000:.1f}M" if pd.notna(x) else "N/A")
        display_df['revenuegrowthyoy'] = display_df['revenuegrowthyoy'].apply(
            lambda x: f"{x*100:.1f}%" if pd.notna(x) else "N/A")
        display_df['programexpenseratio'] = display_df['programexpenseratio'].apply(
            lambda x: f"{x*100:.1f}%" if pd.notna(x) else "N/A")
        display_df['leadscore'] = display_df['leadscore'].apply(
            lambda x: f"{x:.1f}" if pd.notna(x) else "N/A")
        display_df = display_df.rename(columns={
            'orgname': 'Organization', 'phone': 'phone', 'principalofficer': 'PrincipalOfficer',
            'city': 'city', 'state': 'state', 'taxyear': 'Year', 'totalassetseoy': 'Assets',
            'totalrevenuecy': 'Revenue', 'revenuegrowthyoy': 'Rev Growth',
            'programexpenseratio': 'Program %', 'leadscore': 'Score',
        })

        # Pagination
        PAGE_SIZE = 70
        total_rows = len(display_df)
        total_pages = max(1, (total_rows + PAGE_SIZE - 1) // PAGE_SIZE)

        if 'org_page' not in st.session_state:
            st.session_state.org_page = 1

        page = st.session_state.org_page
        start_idx = (page - 1) * PAGE_SIZE
        end_idx = min(start_idx + PAGE_SIZE, total_rows)
        paged_df = display_df.iloc[start_idx:end_idx].copy()
        paged_df.insert(0, '#', range(start_idx + 1, end_idx + 1))

        st.caption(f"Showing {start_idx + 1}–{end_idx} of {total_rows} organizations")

        page_cols = st.columns(min(total_pages, 10))
        for i, col in enumerate(page_cols):
            with col:
                if st.button(str(i + 1), key=f"page_btn_{i+1}"):
                    st.session_state.org_page = i + 1
                    st.rerun()

        if total_pages > 10:
            if st.columns(1)[0].button(f"... {total_pages}", key="page_btn_last"):
                st.session_state.org_page = total_pages
                st.rerun()

        # Org rows
        for i, row in enumerate(paged_df.itertuples()):
            render_org_row(row, start_idx + i, latest_data)

        # CSV export
        _, col_right = st.columns([1, 1])
        with col_right:
            st.download_button(
                label="Export to CSV",
                data=display_df.to_csv(index=False),
                file_name="prospects.csv",
                mime="text/csv",
            )


def main():
    if 'selected_ein' not in st.session_state:
        st.session_state.selected_ein = None

    if st.session_state.selected_ein:
        with st.spinner("Loading organization details..."):
            show_org_detail(st.session_state.selected_ein)
    else:
        show_dashboard()


if __name__ == "__main__":
    main()
