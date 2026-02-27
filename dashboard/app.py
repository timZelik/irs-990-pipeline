import streamlit as st
import pandas as pd
from supabase import create_client
import os

# Supabase client - will be initialized on first use
supabase_client = None

def get_db_connection():
    global supabase_client
    try:
        if supabase_client is None:
            supabase_url = st.secrets["database"]["url"]
            supabase_key = st.secrets["database"]["key"]
            supabase_client = create_client(supabase_url, supabase_key)
        return supabase_client
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None

def get_connection():
    conn = get_db_connection()
    if conn is None:
        st.error("Database connection failed. Please configure Streamlit secrets.")
        st.stop()
    return conn

def fetch_table(table_name, columns="*"):
    """Fetch data from a table"""
    conn = get_connection()
    if conn is None:
        return pd.DataFrame()
    
    try:
        response = conn.table(table_name).select(columns).execute()
        if response.data:
            return pd.DataFrame(response.data)
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching {table_name}: {e}")
        return pd.DataFrame()

# Password protection - Python session only (resets when browser closes)

if 'password_correct' not in st.session_state:
    st.session_state['password_correct'] = False
    
if not st.session_state['password_correct']:
    st.title("🔒 IRS 990 FL & NY Search")
    st.markdown("This dashboard is password protected.")
    
    try:
        default_password = st.secrets.get("password", "")
    except:
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

st.set_page_config(page_title="Nonprofit Intelligence", layout="wide")

# Simple accent - green highlights only
st.markdown("""
<style>
    /* Buttons - green */
    .stButton > button {
        background-color: #00C853 !important;
        color: #000 !important;
    }
    
    /* Default text - white */
    .stApp, p, div, span, li, td, th, label {
        color: #ffffff !important;
    }
    
    /* Metric values in quick stats - green */
    [data-testid="stMetricValue"] {
        color: #00C853 !important;
    }
    
    /* Metric labels - white */
    [data-testid="stMetricLabel"] {
        color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)

def load_summary_data():
    conn = get_connection()
    
    # Fetch organizations with FL/NY
    orgs_fl = fetch_table("organizations", "*")
    orgs = orgs_fl[orgs_fl['state'] == 'FL']
    orgs_ny = orgs_fl[orgs_fl['state'] == 'NY']
    if not orgs_ny.empty:
        orgs = pd.concat([orgs, orgs_ny]) if not orgs.empty else orgs_ny
    
    if orgs.empty:
        return pd.DataFrame()
    
    # Fetch all filings
    filings = fetch_table("filings")
    
    # Fetch all derived_metrics  
    metrics = fetch_table("derived_metrics")
    
    # Fetch prospect_activity
    prospect = fetch_table("prospect_activity")
    
    # Merge data
    df = orgs.merge(filings, on="ein", how="left", suffixes=('', '_fil'))
    df = df.merge(metrics, on=["ein", "taxyear"], how="left", suffixes=('', '_met'))
    df = df.merge(prospect, on="ein", how="left", suffixes=('', '_pros'))
    
    # Sort by leadscore
    df = df.sort_values('leadscore', ascending=False, na_position='last')
    
    return df

def lowercase_columns(df):
    if df is not None and not df.empty:
        df.columns = [c.lower() for c in df.columns]
    return df

def load_org_details(ein):
    conn = get_connection()
    
    org_df = fetch_table("organizations", "*")
    org_df = org_df[org_df['ein'] == ein]
    
    filings_df = fetch_table("filings", "*")
    filings_df = filings_df[filings_df['ein'] == ein].sort_values('taxyear', ascending=False)
    
    metrics_df = fetch_table("derived_metrics", "*")
    metrics_df = metrics_df[metrics_df['ein'] == ein].sort_values('taxyear', ascending=False)
    
    exec_df = fetch_table("executive_compensation", "*")
    exec_df = exec_df[exec_df['ein'] == ein].sort_values('taxyear', ascending=False)
    
    prospect_df = fetch_table("prospect_activity", "*")
    prospect_df = prospect_df[prospect_df['ein'] == ein]
    
    conn.close()
    
    return org_df, filings_df, metrics_df, exec_df, prospect_df

def save_prospect_activity(ein, contact_status, is_watchlisted, notes):
    conn = get_connection()
    if conn is None:
        return
    
    try:
        # Check if record exists
        existing = conn.table("prospect_activity").select("*").eq("ein", ein).execute()
        
        if existing.data:
            # Update
            conn.table("prospect_activity").update({
                "contactstatus": contact_status,
                "iswatchlisted": 1 if is_watchlisted else 0,
                "privatenotes": notes
            }).eq("ein", ein).execute()
        else:
            # Insert
            conn.table("prospect_activity").insert({
                "ein": ein,
                "contactstatus": contact_status,
                "iswatchlisted": 1 if is_watchlisted else 0,
                "privatenotes": notes
            }).execute()
    except Exception as e:
        st.error(f"Error saving: {e}")

def main():
    if 'selected_ein' not in st.session_state:
        st.session_state.selected_ein = None
    
    if st.session_state.selected_ein:
        with st.spinner("Loading organization details..."):
            show_org_detail(st.session_state.selected_ein)
    else:
        show_dashboard()

def show_dashboard():
    st.title("IRS 990 FL & NY Search")
    
    tab1, tab2 = st.tabs(["Dashboard", "FAQ & Help"])
    
    with tab2:
        st.markdown("""
        ## About This Dashboard
        This dashboard provides intelligence on nonprofit organizations in Florida and New York 
        with $1M to $10M in assets. It's designed to help identify prospective clients for accounting/financial services.
        
        ## Data Source
        - **IRS Form 990** filings (publicly available)
        - Data includes financial metrics, executive compensation, and organizational details
        - Updated periodically from raw IRS XML files
        
        ## Metrics Explained
        
        ### Lead Score (0-100)
        A composite score ranking organizations by their financial health and efficiency:
        - **Revenue Growth (25%)**: Year-over-year revenue growth
        - **Program Expense Ratio (30%)**: % of expenses going to programs (higher = better)
        - **Operating Surplus (20%)**: Positive surplus = +20 points
        - **Liability Ratio (15%)**: Lower liabilities relative to assets = better
        - **Exec Compensation (10%)**: Lower exec pay relative to revenue = better
        
        ### Revenue Growth (YoY)
        Year-over-year change in total revenue. Positive = growing, negative = declining.
        
        ### Program Ratio
        Percentage of total expenses dedicated to program services (vs. administration/fundraising).
        - **70%+** = Excellent
        - **50-70%** = Good  
        - **<50%** = May indicate inefficiency
        
        ### Assets
        Total assets at fiscal year end.
        
        ### Revenue
        Total revenue for the current fiscal year.
        
        ## How to Use
        1. Use sidebar filters to narrow down prospects (by state, score, assets, etc.)
        2. Click any organization to view detailed financials
        3. Update contact status to track your outreach
        4. Use watchlist to flag promising prospects
        5. Export filtered lists to CSV for external tracking
        """)
    
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
        
        latest_data = df.sort_values('taxyear', ascending=False).drop_duplicates(subset=['ein'], keep='first')
        
        st.sidebar.header("Filters")
        
        st.sidebar.markdown("**Filter by:**")
        
        status_options = ['not_contacted', 'called_no_answer', 'called_not_interested', 
                         'called_interested', 'meeting_scheduled', 'client']
        if 'contactstatus' in latest_data.columns:
            selected_statuses = st.sidebar.multiselect(
                "Contact Status", status_options, default=['not_contacted'],
                help="Filter organizations by your contact status tracking"
            )
            latest_data = latest_data[latest_data['contactstatus'].isin(selected_statuses)]
        
        state_options = ['FL', 'NY']
        selected_states = st.sidebar.multiselect(
            "state (FL/NY)", state_options, default=state_options,
            help="Filter by state - Florida or New York"
        )
        latest_data = latest_data[latest_data['state'].isin(selected_states)]
        
        min_score = int(latest_data['leadscore'].min()) if not latest_data['leadscore'].isna().all() else 0
        max_score = int(latest_data['leadscore'].max()) if not latest_data['leadscore'].isna().all() else 100
        min_lead_score = st.sidebar.slider(
            "Min Lead Score", 0, 100, min_score,
            help="Minimum composite score (0-100). Higher scores indicate better prospects based on financial health metrics."
        )
        latest_data = latest_data[latest_data['leadscore'] >= min_lead_score]
        
        if 'totalassetseoy' in latest_data.columns:
            min_assets = 1000000  # Always start at $1M
            max_assets = 50000000  # Max slider goes to $50M
            default_max = 10000000  # Default selection is $10M
            
            # Custom styled label with formatted numbers
            st.sidebar.markdown(f"""
            <div style="color: #00C853; font-weight: bold; margin-bottom: -10px;">
                Asset Range: ${min_assets:,.0f} - ${default_max:,.0f}
            </div>
            """, unsafe_allow_html=True)
            
            asset_range = st.sidebar.slider(
                "",
                min_assets, max_assets, 
                (min_assets, default_max),
                help="Filter by total assets at fiscal year end"
            )
        latest_data = latest_data[
            (latest_data['totalassetseoy'] >= asset_range[0]) & 
            (latest_data['totalassetseoy'] <= asset_range[1])
        ]
    
    # Filter by Tax Year
    tax_years = sorted(latest_data['taxyear'].dropna().unique().tolist())
    if tax_years:
        selected_years = st.sidebar.multiselect(
            "Tax Year", tax_years, default=tax_years,
            help="Filter by IRS Form 990 filing year"
        )
        latest_data = latest_data[latest_data['taxyear'].isin(selected_years)]
    
    ntee_categories = latest_data['nteecode'].dropna().unique().tolist()
    if ntee_categories:
        selected_ntee = st.sidebar.multiselect(
            "NTEE Category", ntee_categories, default=ntee_categories[:5],
            help="National Taxonomy of Exempt Entities code - categories like Arts, Education, Health, etc."
        )
        latest_data = latest_data[latest_data['nteecode'].isin(selected_ntee)]
    
    min_program_ratio = st.sidebar.slider(
        "Min Program Expense Ratio", 0.0, 1.0, 0.0,
        help="Minimum percentage of expenses going to programs. 70%+ is excellent."
    )
    if 'programexpenseratio' in latest_data.columns:
        latest_data = latest_data[latest_data['programexpenseratio'] >= min_program_ratio]
    
    search_query = st.text_input("Search organizations", "")
    if search_query:
        latest_data = latest_data[latest_data['orgname'].str.contains(search_query, case=False, na=False)]
    
    # Sort by year (newest first)
    latest_data = latest_data.sort_values('taxyear', ascending=False)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Quick Stats")
    st.sidebar.metric("Total Orgs", len(latest_data))
    if not latest_data['leadscore'].isna().all():
        st.sidebar.metric("Avg Lead Score", f"{latest_data['leadscore'].mean():.1f}")
    if not latest_data['revenuegrowthyoy'].isna().all():
        st.sidebar.metric("Avg Revenue Growth", f"{latest_data['revenuegrowthyoy'].mean()*100:.1f}%")
    if not latest_data['programexpenseratio'].isna().all():
        st.sidebar.metric("Avg Program Ratio", f"{latest_data['programexpenseratio'].mean()*100:.1f}%")
    
    st.markdown("### Key Metrics")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Orgs", len(latest_data), help="Number of organizations matching current filters")
    with col2:
        avg_score = latest_data['leadscore'].mean() if not latest_data['leadscore'].isna().all() else 0
        st.metric("Avg Lead Score", f"{avg_score:.1f}", help="Composite score (0-100) based on revenue growth, program ratio, operating surplus, liability ratio, and executive compensation. Higher = better prospect.")
    with col3:
        avg_growth = latest_data['revenuegrowthyoy'].mean() if not latest_data['revenuegrowthyoy'].isna().all() else 0
        st.metric("Avg Revenue Growth", f"{avg_growth*100:.1f}%", help="Year-over-year average revenue change. Positive = growing organizations")
    with col4:
        avg_program = latest_data['programexpenseratio'].mean() if not latest_data['programexpenseratio'].isna().all() else 0
        st.metric("Avg Program Ratio", f"{avg_program*100:.1f}%", help="Percentage of expenses going to programs. 70%+ = excellent, 50-70% = good, <50% = may indicate inefficiency")
    with col5:
        total_revenue = latest_data['totalrevenuecy'].sum() / 1e9 if not latest_data['totalrevenuecy'].isna().all() else 0
        st.metric("Total Revenue", f"${total_revenue:.1f}B", help="Combined total revenue for all filtered organizations")
    
    st.markdown("### Additional Insights")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        pos_growth = len(latest_data[latest_data['revenuegrowthyoy'] > 0]) if 'revenuegrowthyoy' in latest_data.columns else 0
        pct_pos = pos_growth / len(latest_data) * 100 if len(latest_data) > 0 else 0
        st.metric("Org w/ Positive Growth", f"{pct_pos:.0f}%", help="Percentage of organizations with positive year-over-year revenue growth")
    with col2:
        pos_surplus = len(latest_data[latest_data['surplusdeficitcy'] > 0]) if 'surplusdeficitcy' in latest_data.columns else 0
        pct_surplus = pos_surplus / len(latest_data) * 100 if len(latest_data) > 0 else 0
        st.metric("Org w/ Operating Surplus", f"{pct_surplus:.0f}%", help="Percentage of organizations with more revenue than expenses (operating surplus)")
    with col3:
        avg_admin = latest_data['adminexpenseratio'].mean() * 100 if not latest_data['adminexpenseratio'].isna().all() else 0
        st.metric("Avg Admin Ratio", f"{avg_admin:.1f}%", help="Percentage of expenses used for administrative costs. Lower is generally better.")
    with col4:
        avg_exec = latest_data['execcomppercentofrevenue'].mean() * 100 if not latest_data['execcomppercentofrevenue'].isna().all() else 0
        st.metric("Avg Exec Comp %", f"{avg_exec:.1f}%", help="Executive compensation as percentage of revenue. Lower = more funds go to mission.")
    
    st.markdown("### Organization List")
    
    display_cols = ['orgname', 'phone', 'city', 'state', 'taxyear', 'totalassetseoy', 'totalrevenuecy', 
                    'revenuegrowthyoy', 'programexpenseratio', 'leadscore']
    
    display_df = latest_data[display_cols].copy()
    
    display_df['phone'] = display_df['phone'].apply(
        lambda x: x if pd.notna(x) else "N/A"
    )
    display_df['totalassetseoy'] = display_df['totalassetseoy'].apply(
        lambda x: f"${x/1000000:.1f}M" if pd.notna(x) else "N/A"
    )
    display_df['totalrevenuecy'] = display_df['totalrevenuecy'].apply(
        lambda x: f"${x/1000000:.1f}M" if pd.notna(x) else "N/A"
    )
    display_df['revenuegrowthyoy'] = display_df['revenuegrowthyoy'].apply(
        lambda x: f"{x*100:.1f}%" if pd.notna(x) else "N/A"
    )
    display_df['programexpenseratio'] = display_df['programexpenseratio'].apply(
        lambda x: f"{x*100:.1f}%" if pd.notna(x) else "N/A"
    )
    display_df['leadscore'] = display_df['leadscore'].apply(
        lambda x: f"{x:.1f}" if pd.notna(x) else "N/A"
    )
    
    display_df = display_df.rename(columns={
        'orgname': 'Organization',
        'phone': 'phone',
        'city': 'city',
        'state': 'state',
        'taxyear': 'Year',
        'totalassetseoy': 'Assets',
        'totalrevenuecy': 'Revenue',
        'revenuegrowthyoy': 'Rev Growth',
        'programexpenseratio': 'Program %',
        'leadscore': 'Score'
    })
    
    # Pagination controls with numbered buttons
    PAGE_SIZE = 70
    total_rows = len(display_df)
    total_pages = max(1, (total_rows + PAGE_SIZE - 1) // PAGE_SIZE)
    
    # Initialize page in session state if not exists
    if 'org_page' not in st.session_state:
        st.session_state.org_page = 1
    
    page = st.session_state.org_page
    start_idx = (page - 1) * PAGE_SIZE
    end_idx = min(start_idx + PAGE_SIZE, total_rows)
    paged_df = display_df.iloc[start_idx:end_idx].copy()
    paged_df.insert(0, '#', range(start_idx + 1, end_idx + 1))
    
    st.caption(f"Showing {start_idx + 1}-{end_idx} of {total_rows} organizations")
    
    # Numbered page buttons
    page_cols = st.columns(min(total_pages, 10))
    for i, col in enumerate(page_cols):
        with col:
            btn_label = str(i + 1)
            if st.button(btn_label, key=f"page_btn_{i+1}"):
                st.session_state.org_page = i + 1
                st.rerun()
    
    # Show "..." and last page if more than 10 pages
    if total_pages > 10:
        col_last = st.columns(1)
        with col_last[0]:
            if st.button(f"... {total_pages}", key="page_btn_last"):
                st.session_state.org_page = total_pages
                st.rerun()
    
    # Render table with expandable rows
    for i, row in enumerate(paged_df.itertuples()):
        org_name = row.Organization
        phone = row.phone if hasattr(row, 'phone') else ''
        year = row.Year if hasattr(row, 'Year') else ''
        with st.expander(f"📅 {year} | 📋 {org_name} | 📞 {phone}"):
            actual_idx = start_idx + i
            ein = latest_data.iloc[actual_idx]['ein']
            
            # Load and display org details inline
            org_df, filings_df, metrics_df, exec_df, prospect_df = load_org_details(ein)
            
            if not org_df.empty:
                org = org_df.iloc[0]
                
                city = org.get('city') or 'N/A'
                st.markdown(f"**ein:** {org['ein']} | **city:** {city} | **state:** {org['state']} | **NTEE:** {org['nteecode'] or 'N/A'}")
                
                if org.get('websiteurl'):
                    st.markdown(f"**Website:** [{org['websiteurl']}]({org['websiteurl']})")
                
                if org.get('phone'):
                    st.markdown(f"**phone:** {org['phone']}")
                
                if org.get('principalofficer'):
                    st.markdown(f"**Principal Officer:** {org['principalofficer']}")
                
                if org.get('missiondescription'):
                    st.markdown("### Mission")
                    st.markdown(org['missiondescription'])
                
                if not filings_df.empty:
                    latest = filings_df.iloc[0]
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        assets = latest.get('totalassetseoy') or 0
                        st.metric("Assets", f"${assets/1000000:.1f}M")
                    with col2:
                        revenue = latest.get('totalrevenuecy') or 0
                        st.metric("Revenue", f"${revenue/1000000:.1f}M")
                    with col3:
                        expenses = latest.get('totalexpensescy') or 0
                        st.metric("Expenses", f"${expenses/1000000:.1f}M")
                    with col4:
                        net = latest.get('netassetseoy') or 0
                        st.metric("Net Assets", f"${net/1000000:.1f}M")
    
    st.stop()  # Stop here - no redirect needed
    
    col1, col2 = st.columns([1, 1])
    with col2:
        csv = display_df.to_csv(index=False)
        st.download_button(
            label="Export to CSV",
            data=csv,
            file_name="prospects.csv",
            mime="text/csv"
        )

def show_org_detail(ein):
    org_df, filings_df, metrics_df, exec_df, prospect_df = load_org_details(ein)
    
    if org_df.empty:
        st.warning("Organization not found")
        if st.button("Back to Dashboard"):
            st.session_state.selected_ein = None
            st.rerun()
        return
    
    org = org_df.iloc[0]
    
    col_back, col_title = st.columns([1, 10])
    with col_back:
        if st.button("← Back"):
            st.session_state.selected_ein = None
            st.rerun()
    
    st.title(f"{org['legalname'] or 'Unknown Organization'}")
    
    city = org.get('city') or 'N/A'
    st.markdown(f"**ein:** {org['ein']} | **city:** {city} | **state:** {org['state']} | **NTEE:** {org['nteecode'] or 'N/A'}")
    
    if org.get('websiteurl'):
        st.markdown(f"**Website:** [{org['websiteurl']}]({org['websiteurl']})")
    
    if org.get('phone'):
        st.markdown(f"**phone:** {org['phone']}")
    
    if org.get('principalofficer'):
        st.markdown(f"**Principal Officer:** {org['principalofficer']}")
    
    if org.get('missiondescription'):
        st.markdown("### Mission")
        st.markdown(org['missiondescription'])
    
    st.markdown("---")
    st.markdown("### Financial Snapshot")
    
    if not filings_df.empty:
        latest = filings_df.iloc[0]
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            assets = latest.get('totalassetseoy') or 0
            st.metric("Total Assets", f"${assets/1000000:.1f}M")
        with col2:
            revenue = latest.get('totalrevenuecy') or 0
            st.metric("Total Revenue", f"${revenue/1000000:.1f}M")
        with col3:
            expenses = latest.get('totalexpensescy') or 0
            st.metric("Total Expenses", f"${expenses/1000000:.1f}M")
        with col4:
            net_assets = latest.get('netassetseoy') or 0
            st.metric("Net Assets", f"${net_assets/1000000:.1f}M")
    
    st.markdown("---")
    st.markdown("### 3-Year Trend")
    
    if not filings_df.empty:
        trend_data = filings_df.sort_values('taxyear')
        
        import plotly.graph_objects as go
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=trend_data['taxyear'], 
            y=trend_data['totalrevenuecy'] / 1000000,
            mode='lines+markers',
            name='Revenue'
        ))
        fig.add_trace(go.Scatter(
            x=trend_data['taxyear'], 
            y=trend_data['totalexpensescy'] / 1000000,
            mode='lines+markers',
            name='Expenses'
        ))
        fig.add_trace(go.Scatter(
            x=trend_data['taxyear'], 
            y=trend_data['netassetseoy'] / 1000000,
            mode='lines+markers',
            name='Net Assets'
        ))
        
        fig.update_layout(
            xaxis_title="Tax Year",
            yaxis_title="Amount ($M)",
            legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    st.markdown("### Ratio Analysis")
    
    if not metrics_df.empty:
        latest_metrics = metrics_df.iloc[0]
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            program_pct = (latest_metrics.get('programexpenseratio') or 0) * 100
            st.metric("Program %", f"{program_pct:.1f}%")
        with col2:
            admin_pct = (latest_metrics.get('adminexpenseratio') or 0) * 100
            st.metric("Admin %", f"{admin_pct:.1f}%")
        with col3:
            fund_pct = (latest_metrics.get('FundraisingExpenseRatio') or 0) * 100
            st.metric("Fundraising %", f"{fund_pct:.1f}%")
        with col4:
            exec_pct = (latest_metrics.get('execcomppercentofrevenue') or 0) * 100
            st.metric("Exec Comp %", f"{exec_pct:.1f}%")
    
    st.markdown("---")
    st.markdown("### Risk Flags")
    
    risk_flags = []
    
    if not filings_df.empty and not metrics_df.empty:
        latest_filing = filings_df.iloc[0]
        latest_metrics = metrics_df.iloc[0]
        
        if latest_filing.get('surplusdeficitcy', 0) < 0:
            risk_flags.append(("🔴", "Operating Deficit"))
        
        liability_ratio = latest_metrics.get('LiabilityToAssetRatio') or 0
        if liability_ratio > 0.5:
            risk_flags.append(("🔴", f"Liabilities > 50% of Assets ({liability_ratio*100:.1f}%)"))
        
        contrib_dep = latest_metrics.get('ContributionDependencyPct') or 0
        if contrib_dep > 0.8:
            risk_flags.append(("🟡", f"Contribution Dependency > 80% ({contrib_dep*100:.1f}%)"))
        
        exec_pct = latest_metrics.get('execcomppercentofrevenue') or 0
        if exec_pct > 0.1:
            risk_flags.append(("🟡", f"Exec Comp > 10% of Revenue ({exec_pct*100:.1f}%)"))
        
        surplus_trend = latest_metrics.get('SurplusTrend')
        if surplus_trend == 1:
            risk_flags.append(("🟢", "3-Year Surplus Trend"))
    
    if risk_flags:
        for icon, flag in risk_flags:
            st.markdown(f"{icon} {flag}")
    else:
        st.info("No significant risk flags identified")
    
    st.markdown("---")
    st.markdown("### — Sales Activity —")
    
    current_status = prospect_df.iloc[0]['contactstatus'] if not prospect_df.empty else 'not_contacted'
    current_watchlisted = bool(prospect_df.iloc[0]['iswatchlisted']) if not prospect_df.empty else False
    current_notes = prospect_df.iloc[0]['privatenotes'] or '' if not prospect_df.empty else ''
    
    col1, col2 = st.columns([1, 1])
    with col1:
        status_labels = {
            'not_contacted': '📧 Not Contacted',
            'called_no_answer': '📞 Called - No Answer',
            'called_not_interested': '📞 Called - Not Interested',
            'called_interested': '📞 Called - Interested',
            'meeting_scheduled': '🤝 Meeting Scheduled',
            'client': '✅ Client'
        }
        st.markdown(f"**Current Status:** {status_labels.get(current_status, current_status)}")
    
    with col2:
        is_watchlisted = st.checkbox("Watchlist this organization", value=current_watchlisted)
    
    notes = st.text_area("Private Notes", value=current_notes, height=100)
    
    status_options = ['not_contacted', 'called_no_answer', 'called_not_interested', 
                      'called_interested', 'meeting_scheduled', 'client']
    new_status = st.selectbox("Update Contact Status", status_options, 
                               index=status_options.index(current_status) if current_status in status_options else 0)
    
    if st.button("Save Activity"):
        save_prospect_activity(ein, new_status, is_watchlisted, notes)
        st.success("Saved!")
        st.rerun()

if __name__ == "__main__":
    main()
