-- Organizations table
CREATE TABLE IF NOT EXISTS organizations (
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
    PrincipalOfficer TEXT,
    UNIQUE(EIN)
);

-- Filings table
CREATE TABLE IF NOT EXISTS filings (
    FilingId INTEGER PRIMARY KEY AUTOINCREMENT,
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
);

-- Executive compensation table
CREATE TABLE IF NOT EXISTS executive_compensation (
    ExecId INTEGER PRIMARY KEY AUTOINCREMENT,
    EIN TEXT NOT NULL,
    TaxYear INTEGER,
    OfficerName TEXT,
    Title TEXT,
    AverageHoursPerWeek REAL,
    ReportableCompFromOrg INTEGER,
    ReportableCompFromRelatedOrg INTEGER,
    OtherCompensation INTEGER,
    UNIQUE(EIN, TaxYear, OfficerName)
);

-- Derived metrics table
CREATE TABLE IF NOT EXISTS derived_metrics (
    MetricId INTEGER PRIMARY KEY AUTOINCREMENT,
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
);

-- Prospect activity tracking table
CREATE TABLE IF NOT EXISTS prospect_activity (
    EIN TEXT PRIMARY KEY,
    ContactStatus TEXT DEFAULT 'not_contacted',
    IsWatchlisted INTEGER DEFAULT 0,
    PrivateNotes TEXT,
    LastContactedDate TEXT,
    CreatedAt TEXT DEFAULT (datetime('now')),
    UpdatedAt TEXT DEFAULT (datetime('now'))
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_filings_ein ON filings(EIN);
CREATE INDEX IF NOT EXISTS idx_executive_compensation_ein ON executive_compensation(EIN);
CREATE INDEX IF NOT EXISTS idx_derived_metrics_ein ON derived_metrics(EIN);
