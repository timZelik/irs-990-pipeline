import streamlit as st
import pandas as pd
import sqlite3
import os

DB_PATH = "database/nonprofit_intelligence.db"

# Password protection
if 'password_correct' not in st.session_state:
    st.session_state['password_correct'] = False

if not st.session_state['password_correct']:
    st.title("🔒 Nonprofit Intelligence Dashboard")
    st.markdown("This dashboard is password protected.")
    
    # Check if secrets.toml exists (local) or use Streamlit Cloud secrets
    try:
        default_password = st.secrets.get("password", "")
    except:
        default_password = ""
    
    password = st.text_input("Enter password to access:", type="password")
    
    if st.button("Access Dashboard"):
        if password == default_password and default_password:
            st.session_state['password_correct'] = True
            st.rerun()
        else:
            st.error("Incorrect password. Please contact the owner for access.")
    st.stop()

st.set_page_config(page_title="Nonprofit Intelligence", layout="wide")

def get_connection():
    return sqlite3.connect(DB_PATH)

def load_summary_data():
    conn = get_connection()
    
    query = """
        SELECT 
            o.LegalName as OrgName,
            o.EIN,
            o.State,
            o.City,
            o.NTEECode,
            f.TotalAssetsEOY,
            f.TotalRevenueCY,
            f.TotalExpensesCY,
            f.NetAssetsEOY,
            f.ProgramExpensesAmt,
            f.FundraisingExpensesCY,
            f.ContributionsCY,
            f.SurplusDeficitCY,
            d.RevenueGrowthYoY,
            d.ProgramExpenseRatio,
            d.AdminExpenseRatio,
            d.FundraisingExpenseRatio,
            d.ExecCompPercentOfRevenue,
            d.LiabilityToAssetRatio,
            d.ContributionDependencyPct,
            d.SurplusTrend,
            d.LeadScore,
            f.TaxYear,
            p.ContactStatus,
            p.IsWatchlisted
        FROM organizations o
        LEFT JOIN filings f ON o.EIN = f.EIN
        LEFT JOIN derived_metrics d ON o.EIN = d.EIN AND f.TaxYear = d.TaxYear
        LEFT JOIN prospect_activity p ON o.EIN = p.EIN
        WHERE o.State IN ('FL', 'NY')
        ORDER BY d.LeadScore DESC
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def load_org_details(ein):
    conn = get_connection()
    
    org_query = "SELECT * FROM organizations WHERE EIN = ?"
    org_df = pd.read_sql_query(org_query, conn, params=(ein,))
    
    filings_query = """
        SELECT * FROM filings 
        WHERE EIN = ? 
        ORDER BY TaxYear DESC
    """
    filings_df = pd.read_sql_query(filings_query, conn, params=(ein,))
    
    metrics_query = """
        SELECT * FROM derived_metrics 
        WHERE EIN = ? 
        ORDER BY TaxYear DESC
    """
    metrics_df = pd.read_sql_query(metrics_query, conn, params=(ein,))
    
    exec_query = """
        SELECT * FROM executive_compensation 
        WHERE EIN = ? 
        ORDER BY TaxYear DESC
    """
    exec_df = pd.read_sql_query(exec_query, conn, params=(ein,))
    
    prospect_query = "SELECT * FROM prospect_activity WHERE EIN = ?"
    prospect_df = pd.read_sql_query(prospect_query, conn, params=(ein,))
    
    conn.close()
    
    return org_df, filings_df, metrics_df, exec_df, prospect_df

def save_prospect_activity(ein, contact_status, is_watchlisted, notes):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO prospect_activity 
        (EIN, ContactStatus, IsWatchlisted, PrivateNotes, UpdatedAt)
        VALUES (?, ?, ?, ?, datetime('now'))
    """, (ein, contact_status, 1 if is_watchlisted else 0, notes))
    conn.commit()
    conn.close()

def main():
    if 'selected_ein' not in st.session_state:
        st.session_state.selected_ein = None
    
    if st.session_state.selected_ein:
        show_org_detail(st.session_state.selected_ein)
    else:
        show_dashboard()

def show_dashboard():
    st.title("Nonprofit Prospect Dashboard")
    
    df = load_summary_data()
    
    if df.empty:
        st.warning("No data available. Please run the data pipeline first.")
        return
    
    df['ContactStatus'] = df['ContactStatus'].fillna('not_contacted')
    df['IsWatchlisted'] = df['IsWatchlisted'].fillna(0)
    
    latest_data = df.sort_values('TaxYear', ascending=False).drop_duplicates(subset=['EIN'], keep='first')
    
    st.sidebar.header("Filters")
    
    status_options = ['not_contacted', 'called_no_answer', 'called_not_interested', 
                     'called_interested', 'meeting_scheduled', 'client']
    selected_statuses = st.sidebar.multiselect(
        "Contact Status", status_options, default=['not_contacted']
    )
    latest_data = latest_data[latest_data['ContactStatus'].isin(selected_statuses)]
    
    state_options = ['FL', 'NY']
    selected_states = st.sidebar.multiselect(
        "State", state_options, default=state_options
    )
    latest_data = latest_data[latest_data['State'].isin(selected_states)]
    
    min_score = int(latest_data['LeadScore'].min()) if not latest_data['LeadScore'].isna().all() else 0
    max_score = int(latest_data['LeadScore'].max()) if not latest_data['LeadScore'].isna().all() else 100
    min_lead_score = st.sidebar.slider("Min Lead Score", 0, 100, min_score)
    latest_data = latest_data[latest_data['LeadScore'] >= min_lead_score]
    
    if 'TotalAssetsEOY' in latest_data.columns:
        min_assets = latest_data['TotalAssetsEOY'].min() if latest_data['TotalAssetsEOY'].notna().any() else 1000000
        max_assets = latest_data['TotalAssetsEOY'].max() if latest_data['TotalAssetsEOY'].notna().any() else 10000000
        asset_range = st.sidebar.slider("Asset Range ($)", int(min_assets), int(max_assets), (int(min_assets), int(max_assets)))
        latest_data = latest_data[
            (latest_data['TotalAssetsEOY'] >= asset_range[0]) & 
            (latest_data['TotalAssetsEOY'] <= asset_range[1])
        ]
    
    ntee_categories = latest_data['NTEECode'].dropna().unique().tolist()
    if ntee_categories:
        selected_ntee = st.sidebar.multiselect("NTEE Category", ntee_categories, default=ntee_categories[:5])
        latest_data = latest_data[latest_data['NTEECode'].isin(selected_ntee)]
    
    min_program_ratio = st.sidebar.slider("Min Program Expense Ratio", 0.0, 1.0, 0.0)
    if 'ProgramExpenseRatio' in latest_data.columns:
        latest_data = latest_data[latest_data['ProgramExpenseRatio'] >= min_program_ratio]
    
    search_query = st.text_input("Search organizations", "")
    if search_query:
        latest_data = latest_data[latest_data['OrgName'].str.contains(search_query, case=False, na=False)]
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Quick Stats")
    st.sidebar.metric("Total Orgs", len(latest_data))
    if not latest_data['LeadScore'].isna().all():
        st.sidebar.metric("Avg Lead Score", f"{latest_data['LeadScore'].mean():.1f}")
    if not latest_data['RevenueGrowthYoY'].isna().all():
        st.sidebar.metric("Avg Revenue Growth", f"{latest_data['RevenueGrowthYoY'].mean()*100:.1f}%")
    if not latest_data['ProgramExpenseRatio'].isna().all():
        st.sidebar.metric("Avg Program Ratio", f"{latest_data['ProgramExpenseRatio'].mean()*100:.1f}%")
    
    st.markdown("### Key Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Orgs Matching", len(latest_data))
    with col2:
        avg_score = latest_data['LeadScore'].mean() if not latest_data['LeadScore'].isna().all() else 0
        st.metric("Avg Lead Score", f"{avg_score:.1f}")
    with col3:
        avg_growth = latest_data['RevenueGrowthYoY'].mean() if not latest_data['RevenueGrowthYoY'].isna().all() else 0
        st.metric("Avg Revenue Growth", f"{avg_growth*100:.1f}%")
    with col4:
        avg_program = latest_data['ProgramExpenseRatio'].mean() if not latest_data['ProgramExpenseRatio'].isna().all() else 0
        st.metric("Avg Program Ratio", f"{avg_program*100:.1f}%")
    
    st.markdown("### Organization List")
    
    display_cols = ['OrgName', 'City', 'State', 'TotalAssetsEOY', 'TotalRevenueCY', 
                    'RevenueGrowthYoY', 'ProgramExpenseRatio', 'LeadScore']
    
    display_df = latest_data[display_cols].copy()
    
    display_df['TotalAssetsEOY'] = display_df['TotalAssetsEOY'].apply(
        lambda x: f"${x/1000000:.1f}M" if pd.notna(x) else "N/A"
    )
    display_df['TotalRevenueCY'] = display_df['TotalRevenueCY'].apply(
        lambda x: f"${x/1000000:.1f}M" if pd.notna(x) else "N/A"
    )
    display_df['RevenueGrowthYoY'] = display_df['RevenueGrowthYoY'].apply(
        lambda x: f"{x*100:.1f}%" if pd.notna(x) else "N/A"
    )
    display_df['ProgramExpenseRatio'] = display_df['ProgramExpenseRatio'].apply(
        lambda x: f"{x*100:.1f}%" if pd.notna(x) else "N/A"
    )
    display_df['LeadScore'] = display_df['LeadScore'].apply(
        lambda x: f"{x:.1f}" if pd.notna(x) else "N/A"
    )
    
    display_df = display_df.rename(columns={
        'OrgName': 'Organization',
        'City': 'City',
        'State': 'State',
        'TotalAssetsEOY': 'Assets',
        'TotalRevenueCY': 'Revenue',
        'RevenueGrowthYoY': 'Rev Growth',
        'ProgramExpenseRatio': 'Program %',
        'LeadScore': 'Score'
    })
    
    selected_row = st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row"
    )
    
    if selected_row.selection and len(selected_row.selection['rows']) > 0:
        idx = selected_row.selection['rows'][0]
        ein = latest_data.iloc[idx]['EIN']
        st.session_state.selected_ein = ein
        st.rerun()
    
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
    
    st.title(f"{org['LegalName'] or 'Unknown Organization'}")
    
    city = org.get('City') or 'N/A'
    st.markdown(f"**EIN:** {org['EIN']} | **City:** {city} | **State:** {org['State']} | **NTEE:** {org['NTEECode'] or 'N/A'}")
    
    if org.get('WebsiteUrl'):
        st.markdown(f"**Website:** [{org['WebsiteUrl']}]({org['WebsiteUrl']})")
    
    if org.get('MissionDescription'):
        st.markdown("### Mission")
        st.markdown(org['MissionDescription'])
    
    st.markdown("---")
    st.markdown("### Financial Snapshot")
    
    if not filings_df.empty:
        latest = filings_df.iloc[0]
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            assets = latest.get('TotalAssetsEOY') or 0
            st.metric("Total Assets", f"${assets/1000000:.1f}M")
        with col2:
            revenue = latest.get('TotalRevenueCY') or 0
            st.metric("Total Revenue", f"${revenue/1000000:.1f}M")
        with col3:
            expenses = latest.get('TotalExpensesCY') or 0
            st.metric("Total Expenses", f"${expenses/1000000:.1f}M")
        with col4:
            net_assets = latest.get('NetAssetsEOY') or 0
            st.metric("Net Assets", f"${net_assets/1000000:.1f}M")
    
    st.markdown("---")
    st.markdown("### 3-Year Trend")
    
    if not filings_df.empty:
        trend_data = filings_df.sort_values('TaxYear')
        
        import plotly.graph_objects as go
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=trend_data['TaxYear'], 
            y=trend_data['TotalRevenueCY'] / 1000000,
            mode='lines+markers',
            name='Revenue'
        ))
        fig.add_trace(go.Scatter(
            x=trend_data['TaxYear'], 
            y=trend_data['TotalExpensesCY'] / 1000000,
            mode='lines+markers',
            name='Expenses'
        ))
        fig.add_trace(go.Scatter(
            x=trend_data['TaxYear'], 
            y=trend_data['NetAssetsEOY'] / 1000000,
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
            program_pct = (latest_metrics.get('ProgramExpenseRatio') or 0) * 100
            st.metric("Program %", f"{program_pct:.1f}%")
        with col2:
            admin_pct = (latest_metrics.get('AdminExpenseRatio') or 0) * 100
            st.metric("Admin %", f"{admin_pct:.1f}%")
        with col3:
            fund_pct = (latest_metrics.get('FundraisingExpenseRatio') or 0) * 100
            st.metric("Fundraising %", f"{fund_pct:.1f}%")
        with col4:
            exec_pct = (latest_metrics.get('ExecCompPercentOfRevenue') or 0) * 100
            st.metric("Exec Comp %", f"{exec_pct:.1f}%")
    
    st.markdown("---")
    st.markdown("### Executive Compensation")
    
    if not exec_df.empty:
        exec_display = exec_df[['OfficerName', 'Title', 'ReportableCompFromOrg', 
                                 'ReportableCompFromRelatedOrg', 'OtherCompensation']].copy()
        exec_display['TotalComp'] = (
            exec_display['ReportableCompFromOrg'].fillna(0) + 
            exec_display['ReportableCompFromRelatedOrg'].fillna(0) + 
            exec_display['OtherCompensation'].fillna(0)
        )
        
        for col in ['ReportableCompFromOrg', 'ReportableCompFromRelatedOrg', 'OtherCompensation', 'TotalComp']:
            exec_display[col] = exec_display[col].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "N/A")
        
        exec_display = exec_display.rename(columns={
            'OfficerName': 'Name',
            'Title': 'Title',
            'ReportableCompFromOrg': 'From Org',
            'ReportableCompFromRelatedOrg': 'From Related',
            'OtherCompensation': 'Other',
            'TotalComp': 'Total'
        })
        
        st.dataframe(exec_display, use_container_width=True, hide_index=True)
    else:
        st.info("No executive compensation data available")
    
    st.markdown("---")
    st.markdown("### Risk Flags")
    
    risk_flags = []
    
    if not filings_df.empty and not metrics_df.empty:
        latest_filing = filings_df.iloc[0]
        latest_metrics = metrics_df.iloc[0]
        
        if latest_filing.get('SurplusDeficitCY', 0) < 0:
            risk_flags.append(("🔴", "Operating Deficit"))
        
        liability_ratio = latest_metrics.get('LiabilityToAssetRatio') or 0
        if liability_ratio > 0.5:
            risk_flags.append(("🔴", f"Liabilities > 50% of Assets ({liability_ratio*100:.1f}%)"))
        
        contrib_dep = latest_metrics.get('ContributionDependencyPct') or 0
        if contrib_dep > 0.8:
            risk_flags.append(("🟡", f"Contribution Dependency > 80% ({contrib_dep*100:.1f}%)"))
        
        exec_pct = latest_metrics.get('ExecCompPercentOfRevenue') or 0
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
    
    current_status = prospect_df.iloc[0]['ContactStatus'] if not prospect_df.empty else 'not_contacted'
    current_watchlisted = bool(prospect_df.iloc[0]['IsWatchlisted']) if not prospect_df.empty else False
    current_notes = prospect_df.iloc[0]['PrivateNotes'] or '' if not prospect_df.empty else ''
    
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
