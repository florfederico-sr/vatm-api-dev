import os
from fastapi import FastAPI, Header, HTTPException, Body, UploadFile, File
from pydantic import BaseModel
from typing import Optional
import pandas as pd

app = FastAPI()

API_KEY = os.getenv("API_KEY")

def verify_key(access_key: str):
    if access_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

class AdvanceAmountCSVResponse(BaseModel):
    artist_id: str
    partner_name: str
    projected_advance: float
    currency: str
    qualifies: bool

    class Config:
        schema_extra = {
            "example": {
                "artist_id": "123",
                "partner_name": "cinq",
                "projected_advance": 3420.0,
                "currency": "USD",
                "qualifies": True
            }
        }

# CSV-based Advance Amount calculation
@app.post(
    "/api/royalty/advance-amount",
    response_model=AdvanceAmountCSVResponse,
    summary="Calculate projected advance from earnings CSV",
    description="""
Upload a CSV file containing earnings data for a single artist.

**Expected columns**:
- `artist_id` (string or integer)
- `partner_name` (string)
- `track_title` (string)
- `earning_amount` (float)
- `currency` (string, e.g. "USD")
- `date` (YYYY-MM-DD)

**Only one artist per file is expected.

The system will calculate the projected advance using the total earnings and fixed parameters:
- cushion: 10%
- discount rate: 5%
- term: 2 years
"""
)
async def calculate_advance_from_earnings_csv(
    file: UploadFile = File(...),
    access_key: str = Header(...)
):
    verify_key(access_key)

    contents = await file.read()
    try:
        df = pd.read_csv(pd.compat.StringIO(contents.decode("utf-8")))
    except Exception:
        raise HTTPException(status_code=400, detail="File must be a valid CSV")

    expected_cols = {"artist_id", "partner_name", "track_title", "earning_amount", "currency", "date"}
    if not expected_cols.issubset(df.columns):
        raise HTTPException(
            status_code=400,
            detail=f"CSV is missing required columns. Expected: {', '.join(expected_cols)}"
        )

    if df.empty:
        raise HTTPException(status_code=400, detail="CSV is empty")

    artist_id = str(df.iloc[0]["artist_id"])
    partner_name = str(df.iloc[0]["partner_name"])
    currency = str(df.iloc[0]["currency"])

    try:
        total_earnings = df["earning_amount"].astype(float).sum()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or non-numeric values in earning_amount column")

    cushion = 0.10
    discount_rate = 0.05
    term_years = 2

    projected_advance = total_earnings * (1 - cushion) * (1 - discount_rate) * term_years
    qualifies = projected_advance >= 1000

    return {
        "artist_id": artist_id,
        "partner_name": partner_name,
        "projected_advance": round(projected_advance, 2),
        "currency": currency,
        "qualifies": qualifies
    }

# Deal Status Input & Output
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
                "full_name": "joe smith",
                "email_address": "user@example.com",
                "cell_number": "+15555555555",
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
                "partner_name": "cinq"
            }
        }

@app.post("/api/royalty/active_deal", response_model=DealStatusResponse)
def get_royalty_advance_status(
    data: DealStatusInput = Body(...),
    access_key: str = Header(...)
):
    verify_key(access_key)

    return {
        "status": "success",
        "active": True,
        "fullname_match": True,
        "email_match": True,
        "cell_number_match": True,
        "partner_match": True,
        "deal_id": "RAG-98765",
        "source_system": "Salesforce",
        "effective_date": "2024-01-15",
        "user_id": data.user_id,
        "full_name": data.full_name,
        "email_address": data.email_address,
        "cell_number": data.cell_number,
        "partner_name": data.partner_name
    }
