import os
import sqlite3
from lxml import etree
from database.db_setup import get_connection, get_db_path

XML_DIR = "data/raw_xml"

NS = {'efile': 'http://www.irs.gov/efile'}

def parse_int(value):
    if value is None or value == '':
        return None
    try:
        return int(value.replace(',', ''))
    except (ValueError, AttributeError):
        return None

def parse_float(value):
    if value is None or value == '':
        return None
    try:
        return float(value.replace(',', ''))
    except (ValueError, AttributeError):
        return None

def get_text(elem, xpath_expr):
    try:
        result = elem.xpath(xpath_expr, namespaces=NS)
        if result:
            text = result[0].text
            return text.strip() if text else None
    except:
        pass
    return None

def get_text_or_none(elem, xpath_expr):
    result = get_text(elem, xpath_expr)
    return result if result and result.strip() else None

def parse_xml_file(filepath):
    try:
        tree = etree.parse(filepath)
        root = tree.getroot()
    except Exception as e:
        raise Exception(f"Failed to parse XML: {e}")
    
    filing_data = {}
    
    ein = get_text(root, './/efile:Filer/efile:EIN')
    if not ein:
        return None
    filing_data['EIN'] = ein
    
    filing_data['OrgName'] = get_text_or_none(root, './/efile:Filer/efile:BusinessName/efile:BusinessNameLine1Txt')
    filing_data['State'] = get_text_or_none(root, './/efile:Filer/efile:USAddress/efile:StateAbbreviationCd')
    filing_data['City'] = get_text_or_none(root, './/efile:Filer/efile:USAddress/efile:CityNm')
    filing_data['TaxYear'] = parse_int(get_text(root, './/efile:TaxYr'))
    filing_data['TaxPeriodEndDate'] = get_text_or_none(root, './/efile:TaxPeriodEndDt')
    
    irs990 = root.find('.//efile:IRS990', namespaces=NS)
    if irs990 is not None:
        filing_data['TotalAssetsEOY'] = parse_int(get_text(irs990, './/efile:TotalAssetsEOYAmt'))
        filing_data['TotalLiabilitiesEOY'] = parse_int(get_text(irs990, './/efile:TotalLiabilitiesEOYAmt'))
        filing_data['NetAssetsEOY'] = parse_int(get_text(irs990, './/efile:NetAssetsOrFundBalancesEOYAmt'))
        filing_data['TotalRevenueCY'] = parse_int(get_text(irs990, './/efile:CYTotalRevenueAmt'))
        filing_data['TotalRevenuePY'] = parse_int(get_text(irs990, './/efile:PYTotalRevenueAmt'))
        filing_data['TotalExpensesCY'] = parse_int(get_text(irs990, './/efile:CYTotalExpensesAmt'))
        filing_data['TotalExpensesPY'] = parse_int(get_text(irs990, './/efile:PYTotalExpensesAmt'))
        filing_data['ContributionsCY'] = parse_int(get_text(irs990, './/efile:CYContributionsGrantsAmt'))
        filing_data['ProgramServiceRevenueCY'] = parse_int(get_text(irs990, './/efile:CYProgramServiceRevenueAmt'))
        filing_data['InvestmentIncomeCY'] = parse_int(get_text(irs990, './/efile:CYInvestmentIncomeAmt'))
        filing_data['SalariesCY'] = parse_int(get_text(irs990, './/efile:CYSalariesCompEmpBnftPaidAmt'))
        filing_data['FundraisingExpensesCY'] = parse_int(get_text(irs990, './/efile:CYTotalProfFndrsngExpnsAmt'))
        filing_data['ProgramExpensesAmt'] = parse_int(get_text(irs990, './/efile:TotalProgramServiceExpensesAmt'))
        
        other_revenue = 0
        for tag in ['.//efile:CYOtherRevenueAmt', './/efile:CYTotalOtherIncAmt']:
            val = parse_int(get_text(irs990, tag))
            if val:
                other_revenue += val
        filing_data['OtherRevenueCY'] = other_revenue if other_revenue > 0 else None
        
        filing_data['MissionDesc'] = (
            get_text_or_none(irs990, './/efile:MissionDesc') or
            get_text_or_none(irs990, './/efile:ActivityOrMissionDesc')
        )
        filing_data['WebsiteUrl'] = get_text_or_none(irs990, './/efile:WebsiteAddressTxt')
    
    header = root.find('.//efile:ReturnHeader', namespaces=NS)
    if header is not None:
        if not filing_data.get('OrgName'):
            filing_data['OrgName'] = get_text_or_none(header, './/efile:Filer/efile:BusinessName/efile:BusinessNameLine1Txt')
        if not filing_data.get('State'):
            filing_data['State'] = get_text_or_none(header, './/efile:Filer/efile:USAddress/efile:StateAbbreviationCd')
        if not filing_data.get('City'):
            filing_data['City'] = get_text_or_none(header, './/efile:Filer/efile:USAddress/efile:CityNm')
    
    officers = []
    irs990_part_vii = root.find('.//efile:Form990PartVIISectionAGrp', namespaces=NS)
    if irs990_part_vii is not None:
        for officer in irs990_part_vii:
            officer_data = {
                'OfficerName': get_text_or_none(officer, './/efile:PersonNm'),
                'Title': get_text_or_none(officer, './/efile:TitleTxt'),
                'AverageHoursPerWeek': parse_float(get_text(officer, './/efile:AverageHoursPerWeekRt')),
                'ReportableCompFromOrg': parse_int(get_text(officer, './/efile:ReportableCompFromOrgAmt')),
                'ReportableCompFromRelatedOrg': parse_int(get_text(officer, './/efile:ReportableCompFromRltdOrgAmt')),
                'OtherCompensation': parse_int(get_text(officer, './/efile:OtherCompensationAmt')),
            }
            if officer_data['OfficerName']:
                officers.append(officer_data)
    
    filing_data['officers'] = officers
    filing_data['RawXMLPath'] = filepath
    
    return filing_data

def upsert_organization(conn, data):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO organizations 
        (EIN, LegalName, City, State, WebsiteUrl, MissionDescription)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        data['EIN'],
        data.get('OrgName'),
        data.get('City'),
        data.get('State'),
        data.get('WebsiteUrl'),
        data.get('MissionDesc')
    ))

def upsert_filing(conn, data):
    cursor = conn.cursor()
    
    surplus_deficit = None
    if data.get('TotalRevenueCY') and data.get('TotalExpensesCY'):
        surplus_deficit = data['TotalRevenueCY'] - data['TotalExpensesCY']
    
    cursor.execute("""
        INSERT OR REPLACE INTO filings 
        (EIN, TaxYear, TaxPeriodEndDate, TotalAssetsEOY, TotalLiabilitiesEOY, 
         NetAssetsEOY, TotalRevenueCY, TotalRevenuePY, TotalExpensesCY, 
         TotalExpensesPY, ContributionsCY, ProgramServiceRevenueCY, 
         InvestmentIncomeCY, OtherRevenueCY, SalariesCY, FundraisingExpensesCY, 
         ProgramExpensesAmt, SurplusDeficitCY, RawXMLPath)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data['EIN'],
        data.get('TaxYear'),
        data.get('TaxPeriodEndDate'),
        data.get('TotalAssetsEOY'),
        data.get('TotalLiabilitiesEOY'),
        data.get('NetAssetsEOY'),
        data.get('TotalRevenueCY'),
        data.get('TotalRevenuePY'),
        data.get('TotalExpensesCY'),
        data.get('TotalExpensesPY'),
        data.get('ContributionsCY'),
        data.get('ProgramServiceRevenueCY'),
        data.get('InvestmentIncomeCY'),
        data.get('OtherRevenueCY'),
        data.get('SalariesCY'),
        data.get('FundraisingExpensesCY'),
        data.get('ProgramExpensesAmt'),
        surplus_deficit,
        data.get('RawXMLPath')
    ))

def upsert_executive_compensation(conn, ein, tax_year, officers):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM executive_compensation WHERE EIN = ? AND TaxYear = ?", (ein, tax_year))
    
    for officer in officers:
        cursor.execute("""
            INSERT INTO executive_compensation 
            (EIN, TaxYear, OfficerName, Title, AverageHoursPerWeek, 
             ReportableCompFromOrg, ReportableCompFromRelatedOrg, OtherCompensation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ein, tax_year,
            officer.get('OfficerName'),
            officer.get('Title'),
            officer.get('AverageHoursPerWeek'),
            officer.get('ReportableCompFromOrg'),
            officer.get('ReportableCompFromRelatedOrg'),
            officer.get('OtherCompensation')
        ))

def compute_derived_metrics(conn):
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            f.EIN,
            f.TaxYear,
            f.TotalAssetsEOY,
            f.TotalLiabilitiesEOY,
            f.NetAssetsEOY,
            f.TotalRevenueCY,
            f.TotalRevenuePY,
            f.TotalExpensesCY,
            f.ProgramExpensesAmt,
            f.FundraisingExpensesCY,
            f.ContributionsCY,
            f.SurplusDeficitCY
        FROM filings f
    """)
    
    filings = cursor.fetchall()
    
    metrics_by_ein_year = {}
    
    for row in filings:
        ein = row[0]
        tax_year = row[1]
        key = (ein, tax_year)
        metrics_by_ein_year[key] = {
            'TotalAssetsEOY': row[2],
            'TotalLiabilitiesEOY': row[3],
            'NetAssetsEOY': row[4],
            'TotalRevenueCY': row[5],
            'TotalRevenuePY': row[6],
            'TotalExpensesCY': row[7],
            'ProgramExpensesAmt': row[8],
            'FundraisingExpensesCY': row[9],
            'ContributionsCY': row[10],
            'SurplusDeficitCY': row[11]
        }
    
    for (ein, tax_year), m in metrics_by_ein_year.items():
        prev_key = (ein, tax_year - 1)
        prev_m = metrics_by_ein_year.get(prev_key)
        
        revenue_growth = None
        if m['TotalRevenueCY'] and m['TotalRevenuePY'] and m['TotalRevenuePY'] != 0:
            revenue_growth = (m['TotalRevenueCY'] - m['TotalRevenuePY']) / m['TotalRevenuePY']
        
        asset_growth = None
        if m['TotalAssetsEOY'] and prev_m and prev_m['TotalAssetsEOY'] and prev_m['TotalAssetsEOY'] != 0:
            asset_growth = (m['TotalAssetsEOY'] - prev_m['TotalAssetsEOY']) / prev_m['TotalAssetsEOY']
        
        program_ratio = None
        if m['ProgramExpensesAmt'] and m['TotalExpensesCY'] and m['TotalExpensesCY'] != 0:
            program_ratio = m['ProgramExpensesAmt'] / m['TotalExpensesCY']
        
        admin_ratio = None
        admin_expenses = None
        if m['TotalExpensesCY'] and m['ProgramExpensesAmt'] and m['FundraisingExpensesCY']:
            admin_expenses = m['TotalExpensesCY'] - m['ProgramExpensesAmt'] - m['FundraisingExpensesCY']
            if admin_expenses > 0:
                admin_ratio = admin_expenses / m['TotalExpensesCY']
        
        fundraiser_ratio = None
        if m['FundraisingExpensesCY'] and m['TotalExpensesCY'] and m['TotalExpensesCY'] != 0:
            fundraiser_ratio = m['FundraisingExpensesCY'] / m['TotalExpensesCY']
        
        cursor.execute("""
            SELECT SUM(ReportableCompFromOrg) 
            FROM executive_compensation 
            WHERE EIN = ? AND TaxYear = ?
        """, (ein, tax_year))
        exec_comp = cursor.fetchone()[0] or 0
        
        exec_comp_pct = None
        if exec_comp and m['TotalRevenueCY'] and m['TotalRevenueCY'] != 0:
            exec_comp_pct = exec_comp / m['TotalRevenueCY']
        
        liability_asset_ratio = None
        if m['TotalLiabilitiesEOY'] and m['TotalAssetsEOY'] and m['TotalAssetsEOY'] != 0:
            liability_asset_ratio = m['TotalLiabilitiesEOY'] / m['TotalAssetsEOY']
        
        contrib_dep_pct = None
        if m['ContributionsCY'] and m['TotalRevenueCY'] and m['TotalRevenueCY'] != 0:
            contrib_dep_pct = m['ContributionsCY'] / m['TotalRevenueCY']
        
        surplus_trend = None
        if m['SurplusDeficitCY'] and prev_m and prev_m.get('SurplusDeficitCY') is not None:
            if m['SurplusDeficitCY'] > 0 and prev_m['SurplusDeficitCY'] > 0:
                surplus_trend = 1
            elif m['SurplusDeficitCY'] < 0 and prev_m['SurplusDeficitCY'] < 0:
                surplus_trend = -1
            else:
                surplus_trend = 0
        
        lead_score = compute_lead_score(
            revenue_growth, program_ratio, m['SurplusDeficitCY'],
            liability_asset_ratio, exec_comp_pct
        )
        
        cursor.execute("""
            INSERT OR REPLACE INTO derived_metrics 
            (EIN, TaxYear, RevenueGrowthYoY, AssetGrowthYoY, ProgramExpenseRatio,
             AdminExpenseRatio, FundraisingExpenseRatio, ExecCompPercentOfRevenue,
             LiabilityToAssetRatio, ContributionDependencyPct, SurplusTrend, LeadScore)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ein, tax_year, revenue_growth, asset_growth, program_ratio,
            admin_ratio, fundraiser_ratio, exec_comp_pct, liability_asset_ratio,
            contrib_dep_pct, surplus_trend, lead_score
        ))

def compute_lead_score(revenue_growth, program_ratio, surplus_deficit, liability_ratio, exec_comp_pct):
    score = 0
    weight_sum = 0
    
    if revenue_growth is not None:
        score += revenue_growth * 25
        weight_sum += 25
    
    if program_ratio is not None:
        score += program_ratio * 30
        weight_sum += 30
    
    if surplus_deficit is not None:
        if surplus_deficit > 0:
            score += 20
        weight_sum += 20
    
    if liability_ratio is not None:
        score -= liability_ratio * 15
        weight_sum += 15
    
    if exec_comp_pct is not None:
        score -= exec_comp_pct * 10
        weight_sum += 10
    
    if weight_sum == 0:
        return None
    
    normalized_score = (score / weight_sum) * 100
    
    return max(0, min(100, normalized_score))

def process_xml_files():
    files = [f for f in os.listdir(XML_DIR) if f.endswith('.xml')]
    print(f"Found {len(files)} XML files to process")
    
    conn = get_connection()
    
    success_count = 0
    fail_count = 0
    fail_log = []
    
    for i, filename in enumerate(files):
        filepath = os.path.join(XML_DIR, filename)
        
        try:
            data = parse_xml_file(filepath)
            if data:
                upsert_organization(conn, data)
                upsert_filing(conn, data)
                if data.get('officers'):
                    upsert_executive_compensation(
                        conn, data['EIN'], data.get('TaxYear'), data['officers']
                    )
                success_count += 1
                
                if (i + 1) % 50 == 0:
                    print(f"Processed {i + 1}/{len(files)} files")
            else:
                fail_count += 1
                fail_log.append((filename, "No data parsed"))
        except Exception as e:
            fail_count += 1
            fail_log.append((filename, str(e)))
    
    conn.commit()
    print("Computing derived metrics...")
    compute_derived_metrics(conn)
    conn.commit()
    conn.close()
    
    print("=" * 50)
    print(f"PARSE SUMMARY:")
    print(f"  Records inserted: {success_count}")
    print(f"  Records failed: {fail_count}")
    print("=" * 50)
    
    if fail_log:
        print("\nFailed files:")
        for fn, err in fail_log[:10]:
            print(f"  {fn}: {err}")
        if len(fail_log) > 10:
            print(f"  ... and {len(fail_log) - 10} more")

if __name__ == "__main__":
    process_xml_files()
