# Nonprofit Financial Intelligence Tool

A capital firm lead generation tool to identify mid-market nonprofits in FL and NY with $1M-$10M in total assets that likely lack financial advisors.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Initialize the database:
```bash
python database/db_setup.py
```

## Execution Order

Run the scripts in the following order:

### Step 1: Download and Filter EINs
```bash
python pipeline/download_bmf_and_filter_eins.py
```
- Downloads IRS Business Master File for FL and NY
- Filters for 501c3 organizations with $1M-$10M in assets
- Saves filtered EINs to `data/target_eins.csv`

### Step 2: Download Index and Match URLs
```bash
python pipeline/download_index_and_match_urls.py
```
- Downloads IRS 990 index files for 2021, 2022, 2023
- Cross-references with target EINs
- Saves matched filing URLs to `data/matched_filing_urls.csv`

### Step 3: Download XML Filings (Takes 20-40 minutes)
```bash
python pipeline/download_xml_filings.py
```
- Downloads XML filings for all matched 990s
- Saves to `data/raw_xml/`
- Streams ZIP files in-memory (no disk space issues)

### Step 4: Parse and Load to Database
```bash
PYTHONPATH=. python pipeline/parse_and_load.py
```
- Parses XML files using lxml
- Extracts financial data and executive compensation
- Computes derived metrics and lead scores
- Loads all data into SQLite database

### Step 5: Validate Pipeline
```bash
python pipeline/validate_pipeline.py
```

### Step 6: Launch Dashboard
```bash
streamlit run dashboard/app.py
```
Opens the interactive dashboard with:
- Prospect filtering and search
- Organization details
- Financial metrics and trends
- Risk flag analysis

## Deployment to Streamlit Community Cloud

1. Push code to GitHub:
```bash
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/irs-990-pipeline.git
git push -u origin main
```

2. Deploy:
   - Go to https://share.streamlit.io
   - Connect your GitHub repository
   - Select the main branch and `dashboard/app.py` as the main file

## Password Protection

To add password protection to your deployed Streamlit app:

### Option 1: Using Streamlit Secrets (Recommended)

1. In your GitHub repo, create `.streamlit/secrets.toml`:
```toml
[general]
password = "your-secret-password-here"
```

2. Add this to the top of `dashboard/app.py`:
```python
import streamlit as st

# Password protection
if 'password_correct' not in st.session_state:
    st.session_state['password_correct'] = False

if not st.session_state['password_correct']:
    st.title("🔒 Private Dashboard")
    password = st.text_input("Enter password to access:", type="password")
    if st.button("Access"):
        try:
            if password == st.secrets["password"]:
                st.session_state['password_correct'] = True
                st.rerun()
            else:
                st.error("Incorrect password")
        except:
            st.error("Please set password in Streamlit Cloud secrets")
    st.stop()
```

3. In Streamlit Cloud dashboard:
   - Go to your app settings
   - Add secrets: `password = "your-password"`

### Option 2: Using Environment Variables

```python
import os
import streamlit as st

password = os.environ.get("DASHBOARD_PASSWORD", "default")
user_input = st.text_input("Password", type="password")
if user_input != password:
    st.stop()
```

## File Structure

```
/project_root
  /data
    /raw_xml          <- downloaded XMLs
    target_eins.csv
    matched_filing_urls.csv
  /database
    schema.sql
    db_setup.py
    nonprofit_intelligence.db
  /pipeline
    download_bmf_and_filter_eins.py
    download_index_and_match_urls.py
    download_xml_filings.py
    parse_and_load.py
  /dashboard
    app.py
  requirements.txt
  README.md
```

## Database Schema

- **organizations**: EIN, LegalName, City, State, NTEECode, SubsectionCode, Status, MissionDescription, WebsiteUrl
- **filings**: EIN, TaxYear, TaxPeriodEndDate, TotalAssetsEOY, TotalLiabilitiesEOY, NetAssetsEOY, TotalRevenueCY, TotalRevenuePY, TotalExpensesCY, TotalExpensesPY, etc.
- **executive_compensation**: EIN, TaxYear, OfficerName, Title, AverageHoursPerWeek, ReportableCompFromOrg, etc.
- **derived_metrics**: EIN, TaxYear, RevenueGrowthYoY, AssetGrowthYoY, ProgramExpenseRatio, AdminExpenseRatio, FundraisingExpenseRatio, ExecCompPercentOfRevenue, ContributionDependency, LiabilityToAssetRatio, SurplusTrend, LeadScore

## Lead Score Formula

The lead score (0-100) is calculated using:
- Revenue Growth YoY × 25
- Program Expense Ratio × 30
- +20 if Surplus Deficit > 0
- -Liability to Asset Ratio × 15
- -Exec Comp % of Revenue × 10

Higher scores indicate better prospects for the capital firm.
