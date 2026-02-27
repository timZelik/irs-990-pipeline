import os
import sqlite3
import psycopg2
import pandas as pd
import sys

SQLITE_DB = "database/nonprofit_intelligence.db"

def export_to_supabase(conn_string):
    conn = sqlite3.connect(SQLITE_DB)
    
    print("Reading from SQLite...")
    orgs = pd.read_sql_query("SELECT * FROM organizations", conn)
    filings = pd.read_sql_query("SELECT * FROM filings", conn)
    exec_comp = pd.read_sql_query("SELECT * FROM executive_compensation", conn)
    metrics = pd.read_sql_query("SELECT * FROM derived_metrics", conn)
    prospect = pd.read_sql_query("SELECT * FROM prospect_activity", conn)
    conn.close()
    
    print("Connecting to Supabase...")
    pg_conn = psycopg2.connect(conn_string)
    cursor = pg_conn.cursor()
    
    print("Creating tables...")
    cursor.execute("DROP TABLE IF EXISTS organizations CASCADE")
    cursor.execute("DROP TABLE IF EXISTS filings CASCADE")
    cursor.execute("DROP TABLE IF EXISTS executive_compensation CASCADE")
    cursor.execute("DROP TABLE IF EXISTS derived_metrics CASCADE")
    cursor.execute("DROP TABLE IF EXISTS prospect_activity CASCADE")
    pg_conn.commit()
    
    cursor.execute("""
        CREATE TABLE organizations (
            EIN TEXT PRIMARY KEY,
            LegalName TEXT,
            City TEXT,
            State TEXT,
            NTEECode TEXT,
            SubsectionCode TEXT,
            Status TEXT,
            MissionDescription TEXT,
            WebsiteUrl TEXT,
            Phone TEXT,
            PrincipalOfficer TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE filings (
            FilingId SERIAL PRIMARY KEY,
            EIN TEXT NOT NULL,
            TaxYear INTEGER,
            TaxPeriodEndDate TEXT,
            TotalAssetsEOY INTEGER,
            TotalLiabilitiesEOY INTEGER,
            NetAssetsEOY INTEGER,
            TotalRevenueCY INTEGER,
            TotalRevenuePY INTEGER,
            TotalExpensesCY INTEGER,
            TotalExpensesPY INTEGER,
            ContributionsCY INTEGER,
            ProgramServiceRevenueCY INTEGER,
            InvestmentIncomeCY INTEGER,
            OtherRevenueCY INTEGER,
            SalariesCY INTEGER,
            FundraisingExpensesCY INTEGER,
            ProgramExpensesAmt INTEGER,
            SurplusDeficitCY INTEGER,
            RawXMLPath TEXT,
            UNIQUE(EIN, TaxYear)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE executive_compensation (
            ExecId SERIAL PRIMARY KEY,
            EIN TEXT NOT NULL,
            TaxYear INTEGER,
            OfficerName TEXT,
            Title TEXT,
            AverageHoursPerWeek REAL,
            ReportableCompFromOrg INTEGER,
            ReportableCompFromRelatedOrg INTEGER,
            OtherCompensation INTEGER,
            UNIQUE(EIN, TaxYear, OfficerName)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE derived_metrics (
            MetricId SERIAL PRIMARY KEY,
            EIN TEXT NOT NULL,
            TaxYear INTEGER,
            RevenueGrowthYoY REAL,
            AssetGrowthYoY REAL,
            ProgramExpenseRatio REAL,
            AdminExpenseRatio REAL,
            FundraisingExpenseRatio REAL,
            ExecCompPercentOfRevenue REAL,
            LiabilityToAssetRatio REAL,
            ContributionDependencyPct REAL,
            SurplusTrend REAL,
            LeadScore REAL,
            UNIQUE(EIN, TaxYear)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE prospect_activity (
            EIN TEXT PRIMARY KEY,
            ContactStatus TEXT DEFAULT 'not_contacted',
            IsWatchlisted INTEGER DEFAULT 0,
            PrivateNotes TEXT,
            LastContactedDate TEXT,
            CreatedAt TEXT,
            UpdatedAt TEXT
        )
    """)
    
    pg_conn.commit()
    
    print(f"Inserting {len(orgs)} organizations...")
    cols = ['EIN', 'LegalName', 'City', 'State', 'NTEECode', 'SubsectionCode', 'Status', 'MissionDescription', 'WebsiteUrl', 'Phone', 'PrincipalOfficer']
    values = [tuple(x if pd.notna(x) else None for x in row) for row in orgs[cols].values]
    from psycopg2.extras import execute_values
    execute_values(cursor, "INSERT INTO organizations (EIN, LegalName, City, State, NTEECode, SubsectionCode, Status, MissionDescription, WebsiteUrl, Phone, PrincipalOfficer) VALUES %s", values)
    pg_conn.commit()
    print(f"  Done!")
    
    print(f"Inserting {len(filings)} filings...")
    cols = ['EIN', 'TaxYear', 'TaxPeriodEndDate', 'TotalAssetsEOY', 'TotalLiabilitiesEOY', 'NetAssetsEOY', 'TotalRevenueCY', 'TotalRevenuePY', 'TotalExpensesCY', 'TotalExpensesPY', 'ContributionsCY', 'ProgramServiceRevenueCY', 'InvestmentIncomeCY', 'OtherRevenueCY', 'SalariesCY', 'FundraisingExpensesCY', 'ProgramExpensesAmt', 'SurplusDeficitCY', 'RawXMLPath']
    values = [tuple(x if pd.notna(x) else None for x in row) for row in filings[cols].values]
    execute_values(cursor, "INSERT INTO filings (EIN, TaxYear, TaxPeriodEndDate, TotalAssetsEOY, TotalLiabilitiesEOY, NetAssetsEOY, TotalRevenueCY, TotalRevenuePY, TotalExpensesCY, TotalExpensesPY, ContributionsCY, ProgramServiceRevenueCY, InvestmentIncomeCY, OtherRevenueCY, SalariesCY, FundraisingExpensesCY, ProgramExpensesAmt, SurplusDeficitCY, RawXMLPath) VALUES %s", values)
    pg_conn.commit()
    print(f"  Done!")
    
    print(f"Inserting {len(exec_comp)} executive compensation records...")
    if len(exec_comp) > 0:
        cols = ['EIN', 'TaxYear', 'OfficerName', 'Title', 'AverageHoursPerWeek', 'ReportableCompFromOrg', 'ReportableCompFromRelatedOrg', 'OtherCompensation']
        values = [tuple(x if pd.notna(x) else None for x in row) for row in exec_comp[cols].values]
        execute_values(cursor, "INSERT INTO executive_compensation (EIN, TaxYear, OfficerName, Title, AverageHoursPerWeek, ReportableCompFromOrg, ReportableCompFromRelatedOrg, OtherCompensation) VALUES %s", values)
        pg_conn.commit()
    print(f"  Done!")
    
    print(f"Inserting {len(metrics)} derived metrics...")
    cols = ['EIN', 'TaxYear', 'RevenueGrowthYoY', 'AssetGrowthYoY', 'ProgramExpenseRatio', 'AdminExpenseRatio', 'FundraisingExpenseRatio', 'ExecCompPercentOfRevenue', 'LiabilityToAssetRatio', 'ContributionDependencyPct', 'SurplusTrend', 'LeadScore']
    values = [tuple(x if pd.notna(x) else None for x in row) for row in metrics[cols].values]
    execute_values(cursor, "INSERT INTO derived_metrics (EIN, TaxYear, RevenueGrowthYoY, AssetGrowthYoY, ProgramExpenseRatio, AdminExpenseRatio, FundraisingExpenseRatio, ExecCompPercentOfRevenue, LiabilityToAssetRatio, ContributionDependencyPct, SurplusTrend, LeadScore) VALUES %s", values)
    pg_conn.commit()
    print(f"  Done!")
    
    print(f"Inserting {len(prospect)} prospect activity records...")
    if len(prospect) > 0:
        cols = ['EIN', 'ContactStatus', 'IsWatchlisted', 'PrivateNotes', 'LastContactedDate', 'CreatedAt', 'UpdatedAt']
        values = [tuple(x if pd.notna(x) else None for x in row) for row in prospect[cols].values]
        execute_values(cursor, "INSERT INTO prospect_activity (EIN, ContactStatus, IsWatchlisted, PrivateNotes, LastContactedDate, CreatedAt, UpdatedAt) VALUES %s", values)
        pg_conn.commit()
    print(f"  Done!")
    
    cursor.close()
    pg_conn.close()
    
    print("Done! Data exported to Supabase.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python export_to_supabase.py '<connection_string>'")
        sys.exit(1)
    export_to_supabase(sys.argv[1])
