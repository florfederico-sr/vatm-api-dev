import requests
import unicodedata
import re

# === Utility functions ===

def normalize_phone(phone):
    if not phone:
        return ""
    return re.sub(r"[^\d+]", "", phone)

def normalize_text(text):
    if not text:
        return ""
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8')
    for char in [" ", "-", ".", "'"]:
        text = text.replace(char, "")
    return text.lower().strip()

# === Run SOQL with pagination ===

def run_soql_query(access_token, instance_url, soql):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    all_records = []
    url = f"{instance_url}/services/data/v60.0/query"
    params = {"q": soql}

    while url:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            break

        data = response.json()
        all_records.extend(data.get("records", []))

        next_url = data.get("nextRecordsUrl")
        url = f"{instance_url}{next_url}" if next_url else None
        params = None

    return all_records

# === Search Salesforce Accounts ===

def search_candidate_accounts(access_token, instance_url, name=None, email=None, cell=None):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    queries = []
    if email:
        queries.append(f"FIND {{{email}}} IN EMAIL FIELDS RETURNING Account(Id, Name, Payors_Funded_Text__c, Marketing_Status__pc)")
    if cell:
        normalized_cell = normalize_phone(cell)
        queries.append(f"FIND {{{normalized_cell}}} IN PHONE FIELDS RETURNING Account(Id, Name, Payors_Funded_Text__c, Marketing_Status__pc)")
    if name:
        queries.append(f"FIND {{{name}}} IN NAME FIELDS RETURNING Account(Id, Name, Payors_Funded_Text__c, Marketing_Status__pc)")

    accounts = {}

    for q in queries:
        url = f"{instance_url}/services/data/v60.0/search/?q={q}"
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print("❌ Search failed:", response.text)
            continue

        results = response.json().get("searchRecords", [])
        for acc in results:
            acc_id = acc.get("Id")
            if acc_id and acc_id not in accounts:
                accounts[acc_id] = acc

    enriched_accounts = []
    for acc in accounts.values():
        enriched = enrich_account_data(access_token, instance_url, acc["Id"])
        if enriched:
            enriched_accounts.append(enriched)

    return enriched_accounts

# === Enrichment ===

def enrich_account_data(access_token, instance_url, account_id):
    soql = f"""
    SELECT Id, Name, Payors_Funded_Text__c, Marketing_Status__pc,
        (SELECT Id, Email, MobilePhone FROM Contacts),
        (SELECT Id, Funding_Date__c, Status_of_Deal__c, Type FROM Opportunities WHERE Type LIKE '%Assignment%')
    FROM Account
    WHERE Id = '{account_id}'
      AND Test_Record__c = false
      AND Test_Record__pc = false
      AND IsPersonAccount = true
    """
    results = run_soql_query(access_token, instance_url, soql)
    return results[0] if results else None

# === Deduplication (not strictly needed but included) ===

def deduplicate_accounts(*account_lists):
    merged = {}
    for acc_list in account_lists:
        for acc in acc_list:
            acc_id = acc.get("Id")
            if acc_id and acc_id not in merged:
                merged[acc_id] = acc
    return list(merged.values())

# === Filter and enrich locally ===

def filter_accounts_by_inputs(accounts, input_name=None, input_email=None, input_cell=None, input_partner=None):
    filtered = []
    normalized_input_name = normalize_text(input_name) if input_name else None
    input_email = input_email.lower() if input_email else ""
    input_cell = input_cell.strip() if input_cell else ""
    normalized_input_partner = normalize_text(input_partner) if input_partner else ""

    for acc in accounts:
        acc_name = normalize_text(acc.get("Name"))
        partner_field = normalize_text(acc.get("Payors_Funded_Text__c", ""))
        contacts_raw = acc.get("Contacts")
        contacts = contacts_raw.get("records", []) if contacts_raw else []
        opps_raw = acc.get("Opportunities")
        opportunities = opps_raw.get("records", []) if opps_raw else []

        name_match = normalized_input_name in acc_name if normalized_input_name else False
        email_match = any(input_email in (c.get("Email", "") or "").lower() for c in contacts)
        cell_match = any((c.get("MobilePhone") or "").strip() == input_cell for c in contacts)
        partner_match = normalized_input_partner in partner_field if normalized_input_partner else False
        has_valid_opportunity = any("Assignment" in (o.get("Type") or "") for o in opportunities)

        marketing_status = acc.get("Marketing_Status__pc", "")
        acc["Delinquency"] = 1 if marketing_status == "DNM - Delinquency" else 0

        funded_opp = next((o for o in opportunities if o.get("Status_of_Deal__c") == "Funded"), None)
        acc["Best_Deal_Id"] = funded_opp.get("Id") if funded_opp else None
        acc["Effective_Date"] = funded_opp.get("Funding_Date__c") if funded_opp else None
        acc["Active"] = bool(funded_opp)

        primary_contact = next((c for c in contacts if c.get("Email") or c.get("MobilePhone")), {})
        acc["Email"] = primary_contact.get("Email")
        acc["MobilePhone"] = primary_contact.get("MobilePhone")

        if name_match or email_match or cell_match:
            acc["Matched_Name"] = name_match
            acc["Matched_Email"] = email_match
            acc["Matched_Cell"] = cell_match
            acc["Matched_Partner"] = partner_match
            acc["Has_Valid_Opportunity"] = has_valid_opportunity
            filtered.append(acc)

    return filtered
