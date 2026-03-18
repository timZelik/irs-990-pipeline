import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data import normalize_url, load_org_details, save_prospect_activity


# ── Metrics rows ──────────────────────────────────────────────────────────────

def render_key_metrics(df):
    st.markdown("### Key Metrics")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Orgs", len(df),
                  help="Number of organizations matching current filters")
    with col2:
        avg_score = df['leadscore'].mean() if not df['leadscore'].isna().all() else 0
        st.metric("Avg Lead Score", f"{avg_score:.1f}",
                  help="Composite score (0-100). Higher = better prospect.")
    with col3:
        avg_growth = df['revenuegrowthyoy'].mean() if not df['revenuegrowthyoy'].isna().all() else 0
        st.metric("Avg Revenue Growth", f"{avg_growth*100:.1f}%",
                  help="Year-over-year average revenue change.")
    with col4:
        avg_program = df['programexpenseratio'].mean() if not df['programexpenseratio'].isna().all() else 0
        st.metric("Avg Program Ratio", f"{avg_program*100:.1f}%",
                  help="Percentage of expenses going to programs. 70%+ = excellent.")
    with col5:
        total_revenue = df['totalrevenuecy'].sum() / 1e9 if not df['totalrevenuecy'].isna().all() else 0
        st.metric("Total Revenue", f"${total_revenue:.1f}B",
                  help="Combined total revenue for all filtered organizations")


def render_additional_insights(df):
    st.markdown("### Additional Insights")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        pos_growth = len(df[df['revenuegrowthyoy'] > 0]) if 'revenuegrowthyoy' in df.columns else 0
        pct_pos = pos_growth / len(df) * 100 if len(df) > 0 else 0
        st.metric("Org w/ Positive Growth", f"{pct_pos:.0f}%")
    with col2:
        pos_surplus = len(df[df['surplusdeficitcy'] > 0]) if 'surplusdeficitcy' in df.columns else 0
        pct_surplus = pos_surplus / len(df) * 100 if len(df) > 0 else 0
        st.metric("Org w/ Operating Surplus", f"{pct_surplus:.0f}%")
    with col3:
        avg_admin = df['adminexpenseratio'].mean() * 100 if not df['adminexpenseratio'].isna().all() else 0
        st.metric("Avg Admin Ratio", f"{avg_admin:.1f}%")
    with col4:
        avg_exec = df['execcomppercentofrevenue'].mean() * 100 if not df['execcomppercentofrevenue'].isna().all() else 0
        st.metric("Avg Exec Comp %", f"{avg_exec:.1f}%")


# ── Organization list row ─────────────────────────────────────────────────────

def render_org_row(row, actual_idx, latest_data):
    """Render a single organization as an expandable row."""
    org_name = row.Organization
    phone = row.phone if hasattr(row, 'phone') else ''
    year = row.Year if hasattr(row, 'Year') else ''
    principal_officer = row.PrincipalOfficer if hasattr(row, 'PrincipalOfficer') else ''

    header = f"📅 {year} | 📋 {org_name}"
    if phone:
        header += f" | 📞 {phone}"
    if principal_officer:
        header += f" | 👤 {principal_officer}"

    with st.expander(header):
        ein = latest_data.iloc[actual_idx]['ein']
        org_df, filings_df, _, _, _ = load_org_details(ein)

        if org_df.empty:
            st.warning("Details unavailable.")
            return

        org = org_df.iloc[0]
        city = org.get('city') or 'N/A'
        st.markdown(
            f"**EIN:** {org['ein']} | **City:** {city} | "
            f"**State:** {org['state']} | **NTEE:** {org.get('nteecode') or 'N/A'}"
        )

        website = normalize_url(org.get('websiteurl'))
        if website:
            st.markdown(f"**Website:** [{website}]({website})")
        if org.get('phone'):
            st.markdown(f"**Phone:** {org['phone']}")
        if org.get('principalofficer'):
            st.markdown(f"**Principal Officer:** {org['principalofficer']}")
        if org.get('missiondescription'):
            st.markdown("**Mission:** " + org['missiondescription'])

        if not filings_df.empty:
            latest = filings_df.iloc[0]
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Assets", f"${(latest.get('totalassetseoy') or 0)/1_000_000:.1f}M")
            with col2:
                st.metric("Revenue", f"${(latest.get('totalrevenuecy') or 0)/1_000_000:.1f}M")
            with col3:
                st.metric("Expenses", f"${(latest.get('totalexpensescy') or 0)/1_000_000:.1f}M")
            with col4:
                st.metric("Net Assets", f"${(latest.get('netassetseoy') or 0)/1_000_000:.1f}M")


# ── Org detail page ───────────────────────────────────────────────────────────

def show_org_detail(ein):
    org_df, filings_df, metrics_df, exec_df, prospect_df = load_org_details(ein)

    if org_df.empty:
        st.warning("Organization not found")
        if st.button("Back to Dashboard"):
            st.session_state.selected_ein = None
            st.rerun()
        return

    org = org_df.iloc[0]

    col_back, _ = st.columns([1, 10])
    with col_back:
        if st.button("← Back"):
            st.session_state.selected_ein = None
            st.rerun()

    st.title(org.get('orgname') or 'Unknown Organization')
    city = org.get('city') or 'N/A'
    st.markdown(
        f"**EIN:** {org['ein']} | **City:** {city} | "
        f"**State:** {org['state']} | **NTEE:** {org.get('nteecode') or 'N/A'}"
    )

    website = normalize_url(org.get('websiteurl'))
    if website:
        st.markdown(f"**Website:** [{website}]({website})")
    if org.get('phone'):
        st.markdown(f"**Phone:** {org['phone']}")
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
            st.metric("Total Assets", f"${(latest.get('totalassetseoy') or 0)/1_000_000:.1f}M")
        with col2:
            st.metric("Total Revenue", f"${(latest.get('totalrevenuecy') or 0)/1_000_000:.1f}M")
        with col3:
            st.metric("Total Expenses", f"${(latest.get('totalexpensescy') or 0)/1_000_000:.1f}M")
        with col4:
            st.metric("Net Assets", f"${(latest.get('netassetseoy') or 0)/1_000_000:.1f}M")

    st.markdown("---")
    st.markdown("### 3-Year Trend")
    if not filings_df.empty:
        trend_data = filings_df.sort_values('taxyear')
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=trend_data['taxyear'], y=trend_data['totalrevenuecy'] / 1_000_000,
            mode='lines+markers', name='Revenue',
        ))
        fig.add_trace(go.Scatter(
            x=trend_data['taxyear'], y=trend_data['totalexpensescy'] / 1_000_000,
            mode='lines+markers', name='Expenses',
        ))
        fig.add_trace(go.Scatter(
            x=trend_data['taxyear'], y=trend_data['netassetseoy'] / 1_000_000,
            mode='lines+markers', name='Net Assets',
        ))
        fig.update_layout(
            xaxis_title="Tax Year", yaxis_title="Amount ($M)",
            legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown("### Ratio Analysis")
    if not metrics_df.empty:
        m = metrics_df.iloc[0]
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Program %", f"{(m.get('programexpenseratio') or 0)*100:.1f}%")
        with col2:
            st.metric("Admin %", f"{(m.get('adminexpenseratio') or 0)*100:.1f}%")
        with col3:
            st.metric("Fundraising %", f"{(m.get('fundraisingexpenseratio') or 0)*100:.1f}%")
        with col4:
            st.metric("Exec Comp %", f"{(m.get('execcomppercentofrevenue') or 0)*100:.1f}%")

    st.markdown("---")
    st.markdown("### Risk Flags")
    risk_flags = []
    if not filings_df.empty and not metrics_df.empty:
        lf = filings_df.iloc[0]
        lm = metrics_df.iloc[0]
        if (lf.get('surplusdeficitcy') or 0) < 0:
            risk_flags.append(("🔴", "Operating Deficit"))
        lr = lm.get('liabilitytoassetratio') or 0
        if lr > 0.5:
            risk_flags.append(("🔴", f"Liabilities > 50% of Assets ({lr*100:.1f}%)"))
        cd = lm.get('contributiondependencypct') or 0
        if cd > 0.8:
            risk_flags.append(("🟡", f"Contribution Dependency > 80% ({cd*100:.1f}%)"))
        ep = lm.get('execcomppercentofrevenue') or 0
        if ep > 0.1:
            risk_flags.append(("🟡", f"Exec Comp > 10% of Revenue ({ep*100:.1f}%)"))
        if lm.get('surplustrend') == 1:
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
    current_notes = (prospect_df.iloc[0]['privatenotes'] or '') if not prospect_df.empty else ''

    status_labels = {
        'not_contacted': '📧 Not Contacted',
        'called_no_answer': '📞 Called - No Answer',
        'called_not_interested': '📞 Called - Not Interested',
        'called_interested': '📞 Called - Interested',
        'meeting_scheduled': '🤝 Meeting Scheduled',
        'client': '✅ Client',
    }

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Current Status:** {status_labels.get(current_status, current_status)}")
    with col2:
        is_watchlisted = st.checkbox("Watchlist this organization", value=current_watchlisted)

    notes = st.text_area("Private Notes", value=current_notes, height=100)
    status_options = list(status_labels.keys())
    new_status = st.selectbox(
        "Update Contact Status", status_options,
        index=status_options.index(current_status) if current_status in status_options else 0,
    )

    if st.button("Save Activity"):
        save_prospect_activity(ein, new_status, is_watchlisted, notes)
        st.success("Saved!")
        st.rerun()


# ── FAQ tab ───────────────────────────────────────────────────────────────────

def render_faq():
    st.markdown("""
## About This Dashboard
This dashboard provides intelligence on nonprofit organizations in Florida and New York
with $1M to $10M in assets. Designed to identify prospective clients for accounting/financial services.

## Data Source
- **IRS Form 990** filings (publicly available)
- Data includes financial metrics, executive compensation, and organizational details
- Updated periodically from raw IRS XML files

## Metrics Explained

### Lead Score (0-100)
A composite score ranking organizations by financial health and efficiency:
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
1. Use sidebar filters to narrow down prospects (state, score, assets, etc.)
2. Click any organization row to view detailed financials
3. Update contact status to track your outreach
4. Use watchlist to flag promising prospects
5. Export filtered lists to CSV for external tracking
""")
