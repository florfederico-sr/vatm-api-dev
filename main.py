import os
import io
import math
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from fastapi import FastAPI, Header, HTTPException, Body, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import pandas as pd

from salesforce_auth import get_salesforce_token
from salesforce_queries import (
    search_candidate_accounts,
    filter_accounts_by_inputs
)

from advance_calculator import get_funding_config, calculate_advance

ASSUMED_FUND_OFFSET_DAYS = 15

app = FastAPI()

API_KEY = os.getenv("API_KEY")

def verify_key(access_key: str):
    if access_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

# === MODELS ===

class DealStatusInput(BaseModel):
    user_id: str
    full_name: str
    email_address: Optional[str] = None
    cell_number: Optional[str] = None
    partner_name: Optional[str] = None

    class Config:
        schema_extra = {
            "example": { 
                "user_id": "123456", 
                "full_name": "Joseph Lynn Brown", 
                "email_address": "djmemo@gmail.com", 
                "cell_number": "(530) 355-0640", 
                "partner_name": "cinq" 
            }
        }

class DealStatusResponse(BaseModel):
    status: str
    active: bool
    fullname_match: bool
    email_match: bool
    cell_number_match: bool
    partner_match: bool
    deal_id: str
    source_system: str
    effective_date: str
    user_id: str
    full_name: str
    email_address: Optional[str]
    cell_number: Optional[str]
    partner_name: Optional[str]
    delinquency_flag: bool

    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "active": True,
                "fullname_match": True,
                "email_match": True,
                "cell_number_match": True,
                "partner_match": True,
                "deal_id": "RAG-98765",
                "source_system": "Salesforce",
                "effective_date": "2024-01-15",
                "user_id": "123456",
                "full_name": "joe smith",
                "email_address": "user@example.com",
                "cell_number": "+15555555555",
                "partner_name": "cinq",
                "delinquency_flag": False
            }
        }

class AdvanceAmountCSVResponse(BaseModel):
    artist_id: str
    partner_name: str
    projected_advance: float
    currency: str
    qualifies: bool
    trended_annual: float
    #raw_trended_annual: float
    first_assigned_payment_date: str
    last_assigned_payment_date: str

    class Config:
        schema_extra = {
            "example": {
                "artist_id": "123456",
                "partner_name": "cinq",
                "projected_advance": 14000,
                "currency": "USD_840",
                "qualifies": True,
                "trended_annual": 12000,
                #"raw_trended_annual": 17050.35,
                "first_assigned_payment_date": "2025-07-01",
                "last_assigned_payment_date": "2026-12-31"
                }
        }    


class CollectEarningsInput(BaseModel):
    user_id: str
    full_name: str
    email_address: Optional[str] = None
    cell_number: Optional[str] = None
    partner_name: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "user_id": "123456",
                "full_name": "joe smith",
                "email_address": "user@example.com",
                "cell_number": "+15555555555",
                "partner_name": "cinq"
            }
        }

# === ENDPOINTS ===

@app.post("/api/royalty/active-deal", response_model=List[DealStatusResponse])
def get_royalty_advance_status(
    data: DealStatusInput = Body(...),
    access_key: str = Header(...)
):
    verify_key(access_key)

    access_token, instance_url = get_salesforce_token()

    # Optimized search
    accounts = search_candidate_accounts(
        access_token,
        instance_url,
        name=data.full_name,
        email=data.email_address,
        cell=data.cell_number
    )

    matched_accounts = filter_accounts_by_inputs(
        accounts,
        input_name=data.full_name,
        input_email=data.email_address,
        input_cell=data.cell_number,
        input_partner=data.partner_name
    )

    if not matched_accounts:
        return [DealStatusResponse(
            status="not-found",
            active=False,
            fullname_match=False,
            email_match=False,
            cell_number_match=False,
            partner_match=False,
            deal_id="nan",
            source_system="Salesforce",
            effective_date="nan",
            user_id=data.user_id,
            full_name="nan",
            email_address=None,
            cell_number=None,
            partner_name=None,
            delinquency_flag=False
        )]

    responses = []
    for match in matched_accounts:
        response = DealStatusResponse(
            status="success",
            active=match.get("Active", False),
            fullname_match=match.get("Matched_Name", False),
            email_match=match.get("Matched_Email", False),
            cell_number_match=match.get("Matched_Cell", False),
            partner_match=match.get("Matched_Partner", False),
            deal_id=match.get("Best_Deal_Id") or "nan",
            source_system="Salesforce",
            effective_date=match.get("Effective_Date") or "nan",
            user_id=match.get("Id", data.user_id),
            full_name=match.get("Name", data.full_name),
            email_address=match.get("Email", data.email_address),
            cell_number=match.get("MobilePhone", data.cell_number),
            partner_name=match.get("Payors_Funded_Text__c", data.partner_name),
            delinquency_flag=match.get("Delinquency", False)
        )
        responses.append(response)

    return responses


@app.post("/api/royalty/advance-amount", response_model=AdvanceAmountCSVResponse)
async def calculate_advance_from_earnings_csv(
    file: UploadFile = File(...),
    access_key: str = Header(...)
):
    verify_key(access_key)

    contents = await file.read()
    try:
        df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
    except Exception:
        raise HTTPException(status_code=400, detail="File must be a valid CSV")

    expected_cols = {"artist_id", "partner_name", "track_title", "earning_amount", "currency", "date"}
    if not expected_cols.issubset(df.columns):
        raise HTTPException(status_code=400, detail=f"CSV is missing required columns: {', '.join(expected_cols)}")

    if df.empty:
        raise HTTPException(status_code=400, detail="CSV is empty")

    artist_id = str(df.iloc[0]["artist_id"])
    partner_name = str(df.iloc[0]["partner_name"])
    currency = str(df.iloc[0]["currency"])

    try:
        cushion, decline_rate, term_years, frequency, discount_rate = get_funding_config(partner_name)

        df["earning_amount"] = df["earning_amount"].astype(float)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

        latest_date = df["date"].max()
        df_6m = df[df["date"] > latest_date - pd.DateOffset(months=6)]
        df_12m = df[df["date"] > latest_date - pd.DateOffset(months=12)]

        if df_6m.empty and df_12m.empty:
            raise HTTPException(status_code=400, detail="Not enough data in the last 12 months to compute trended annual")

        def total_monthly_sum(df_subset):
            if df_subset.empty:
                return 0.0
            df_subset = df_subset.copy()
            df_subset["month"] = df_subset["date"].dt.to_period("M")
            monthly_totals = df_subset.groupby("month")["earning_amount"].sum()
            return monthly_totals.sum()

        def total_monthly_sum_rounded(df_subset):
            if df_subset.empty:
                return 0.0
            df_subset = df_subset.copy()
            df_subset["month"] = df_subset["date"].dt.to_period("M")
            monthly_totals = df_subset.groupby("month")["earning_amount"].sum()
            rounded_monthly = monthly_totals.apply(lambda x: math.floor(x / 1000) * 1000)
            return rounded_monthly.sum()

        #raw_total_6m = total_monthly_sum(df_6m)
        #raw_total_12m = total_monthly_sum(df_12m)
        #raw_trended = min(raw_total_12m, raw_total_6m * 2)

        #rounded_total_6m = total_monthly_sum_rounded(df_6m)
        #rounded_total_12m = total_monthly_sum_rounded(df_12m)
        #trended_annual = min(rounded_total_12m, rounded_total_6m * 2)

        total_6m = total_monthly_sum(df_6m)
        total_12m = total_monthly_sum(df_12m)
        trended = min(total_12m, total_6m * 2)

        # === Assigned Payment Dates ===
        today = datetime.today().date()
        assumed_fund_date = today + timedelta(days=ASSUMED_FUND_OFFSET_DAYS)
        first_assigned_payment_date = (assumed_fund_date.replace(day=1) + relativedelta(months=1))

        frequency_map = {
            "Monthly": 12,
            "Quarterly": 4,
            "Annually": 1
        }
        periods_per_year = frequency_map.get(frequency, 12)
        total_periods = int(term_years * periods_per_year)

        last_assigned_payment_date = first_assigned_payment_date + relativedelta(months=total_periods) - timedelta(days=1)

        # ISO
        first_assigned_payment_date = first_assigned_payment_date.isoformat()
        last_assigned_payment_date = last_assigned_payment_date.isoformat()

    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Data processing error: {str(e)}")

    try:
        projected_advance = calculate_advance(
            trended, cushion, decline_rate, term_years, discount_rate, frequency
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")

    qualifies = projected_advance >= 1000

    return {
        "artist_id": artist_id,
        "partner_name": partner_name,
        "projected_advance": round(projected_advance, 2),
        "currency": currency,
        "qualifies": qualifies,
        "trended_annual": round(trended, 2),
        #"raw_trended_annual": round(raw_trended, 2),
        "first_assigned_payment_date": first_assigned_payment_date,
        "last_assigned_payment_date": last_assigned_payment_date
    }


@app.post(
    "/api/royalty/collect-earningsdata",
    summary="Generate CSV with earnings data for a user"
)
def collect_earnings_data(
    data: CollectEarningsInput = Body(...),
    access_key: str = Header(...)
):
    verify_key(access_key)

    earnings_data = [
        {
            "artist_id": data.user_id,
            "partner_name": data.partner_name or "cinq",
            "track_title": f"Track {i+1}",
            "earning_amount": round(1000 + i * 250.75, 2),
            "currency": "USD_840",
            "date": f"2024-0{i+1}-15"
        }
        for i in range(3)
    ]

    df = pd.DataFrame(earnings_data)

    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=earnings_{data.user_id}.csv"}
    )
