import os
import pyodbc

def get_sql_connection():
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={os.getenv('SQL_SERVER')};"
        f"DATABASE={os.getenv('SQL_DATABASE')};"
        f"UID={os.getenv('SQL_USER')};"
        f"PWD={os.getenv('SQL_PASSWORD')}"
    )

def get_funding_config(partner_name: str):
    conn = get_sql_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT TOP 1 fc.cushion, fc.declineRate, fc.termYears, fc.frequency, fc.discountRate
        FROM [dbo].[FundingConfig] fc
        INNER JOIN [dbo].[PartnerDetail] pd ON fc.partnerUUID = pd.partnerUUID
        WHERE LOWER(pd.partnerName) LIKE '%' + LOWER(?) + '%'
        ORDER BY LEN(pd.partnerName) ASC
    """, partner_name)

    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row:
        raise ValueError(f"No config found for partner similar to '{partner_name}'")

    return row  # (cushion, decline_rate, term_years, frequency, discount_rate)

def calculate_advance(trended_annual, cushion, decline_rate, term_years, discount_rate, frequency):
    # Convert decimals to floats
    cushion = float(cushion)
    decline_rate = float(decline_rate)
    term_years = float(term_years)
    discount_rate = float(discount_rate)

    frequency_map = {
        "Monthly": 12,
        "Quarterly": 4,
        "Annually": 1
    }

    periods_per_year = frequency_map.get(frequency, 12)  # default to monthly if unrecognized
    total_periods = int(term_years * periods_per_year)
    periodic_discount_rate = discount_rate / periods_per_year
    periodic_payment = (trended_annual * (1 - cushion)) / periods_per_year

    cash_flows = [
        periodic_payment * ((1 - decline_rate) ** i) / ((1 + periodic_discount_rate) ** (i + 1))
        for i in range(total_periods)
    ]

    return sum(cash_flows)

