import streamlit as st
import pandas as pd


def apply_sidebar_filters(df):
    """Render sidebar filters and return filtered DataFrame."""
    st.sidebar.header("Filters")
    st.sidebar.markdown("**Filter by:**")

    # Contact status
    status_options = [
        'not_contacted', 'called_no_answer', 'called_not_interested',
        'called_interested', 'meeting_scheduled', 'client',
    ]
    if 'contactstatus' in df.columns:
        selected_statuses = st.sidebar.multiselect(
            "Contact Status", status_options, default=['not_contacted'],
            help="Filter organizations by your contact status tracking",
        )
        df = df[df['contactstatus'].isin(selected_statuses)]

    # State
    selected_states = st.sidebar.multiselect(
        "State (FL/NY)", ['FL', 'NY'], default=['FL', 'NY'],
        help="Filter by state - Florida or New York",
    )
    df = df[df['state'].isin(selected_states)]

    # Lead score
    min_score = int(df['leadscore'].min()) if not df['leadscore'].isna().all() else 0
    min_lead_score = st.sidebar.slider(
        "Min Lead Score", 0, 100, min_score,
        help="Minimum composite score (0-100). Higher scores indicate better prospects.",
    )
    df = df[df['leadscore'] >= min_lead_score]

    # Asset range
    if 'totalassetseoy' in df.columns:
        min_assets = 1_000_000
        max_assets = 50_000_000
        default_max = 10_000_000
        st.sidebar.markdown(
            f'<div style="color:#00C853;font-weight:bold;margin-bottom:-10px;">'
            f'Asset Range: ${min_assets:,.0f} – ${default_max:,.0f}</div>',
            unsafe_allow_html=True,
        )
        asset_range = st.sidebar.slider(
            "", min_assets, max_assets, (min_assets, default_max),
            help="Filter by total assets at fiscal year end",
        )
        df = df[
            (df['totalassetseoy'] >= asset_range[0]) &
            (df['totalassetseoy'] <= asset_range[1])
        ]

    # Tax year
    tax_years = sorted(df['taxyear'].dropna().unique().tolist())
    if tax_years:
        selected_years = st.sidebar.multiselect(
            "Tax Year", tax_years, default=tax_years,
            help="Filter by IRS Form 990 filing year",
        )
        df = df[df['taxyear'].isin(selected_years)]

    # NTEE category
    ntee_categories = df['nteecode'].dropna().unique().tolist()
    if ntee_categories:
        selected_ntee = st.sidebar.multiselect(
            "NTEE Category", ntee_categories, default=ntee_categories[:5],
            help="National Taxonomy of Exempt Entities code",
        )
        df = df[df['nteecode'].isin(selected_ntee)]

    # Program expense ratio
    min_program_ratio = st.sidebar.slider(
        "Min Program Expense Ratio", 0.0, 1.0, 0.0,
        help="Minimum percentage of expenses going to programs. 70%+ is excellent.",
    )
    if 'programexpenseratio' in df.columns:
        df = df[df['programexpenseratio'] >= min_program_ratio]

    # Quick stats summary
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Quick Stats")
    st.sidebar.metric("Total Orgs", len(df))
    if not df['leadscore'].isna().all():
        st.sidebar.metric("Avg Lead Score", f"{df['leadscore'].mean():.1f}")
    if not df['revenuegrowthyoy'].isna().all():
        st.sidebar.metric("Avg Revenue Growth", f"{df['revenuegrowthyoy'].mean()*100:.1f}%")
    if not df['programexpenseratio'].isna().all():
        st.sidebar.metric("Avg Program Ratio", f"{df['programexpenseratio'].mean()*100:.1f}%")

    return df
