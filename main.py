import os
import io
from fastapi import FastAPI, Header, HTTPException, Body, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import pandas as pd
import random

app = FastAPI()

API_KEY = os.getenv("API_KEY")

def verify_key(access_key: str):
    if access_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

class AdvanceAmountCSVResponse(BaseModel):
    artist_id: str
    partner_name: str
    projected_advance: float
    currency: str = "USD_840"
    qualifies: bool

    class Config:
        schema_extra = {
            "example": {
                "artist_id": "123",
                "partner_name": "cinq",
                "projected_advance": 3420.0,
                "currency": "USD_840",
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
- 'artist_id' (string or integer)
- 'partner_name' (string)
- 'track_title' (string)
- 'earning_amount' (float)
- 'currency' (string: ISO 4217 Codes) (Default=USD_840)
- 'date' (YYYY-MM-DD)

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
        df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
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

@app.post("/api/royalty/active-deal", response_model=DealStatusResponse)
def get_royalty_advance_status(
    data: DealStatusInput = Body(...),
    access_key: str = Header(...)
):
    verify_key(access_key)

    examples = [
        {
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
        },
        {
            "status": "success",
            "active": True,
            "fullname_match": True,
            "email_match": False,
            "cell_number_match": False,
            "partner_match": False,
            "deal_id": "RAG-12345",
            "source_system": "Salesforce",
            "effective_date": "2023-10-01",
            "user_id": data.user_id,
            "full_name": data.full_name,
            "email_address": None,
            "cell_number": None,
            "partner_name": "ascap"
        },
        {
            "status": "success",
            "active": True,
            "fullname_match": False,
            "email_match": True,
            "cell_number_match": False,
            "partner_match": False,
            "deal_id": "RAG-12345",
            "source_system": "Salesforce",
            "effective_date": "2023-10-01",
            "user_id": data.user_id,
            "full_name": "jamie scott",
            "email_address": data.email_address,
            "cell_number": None,
            "partner_name": "bmi"
        },
        {
            "status": "success",
            "active": True,
            "fullname_match": False,
            "email_match": False,
            "cell_number_match": True,
            "partner_match": False,
            "deal_id": "RAG-12345",
            "source_system": "Salesforce",
            "effective_date": "2023-10-01",
            "user_id": data.user_id,
            "full_name": "jamie scott",
            "email_address": None,
            "cell_number": data.cell_number,
            "partner_name": None
        },
        {
            "status": "not-found",
            "active": False,
            "fullname_match": False,
            "email_match": False,
            "cell_number_match": False,
            "partner_match": False,
            "deal_id": "N/A",
            "source_system": "Salesforce",
            "effective_date": "N/A",
            "user_id": data.user_id,
            "full_name": None,
            "email_address": None,
            "cell_number": None,
            "partner_name": None
        }
    ]

    return random.choice(examples)

class CollectEarningsRequest(BaseModel):
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

@app.post(
    "/api/royalty/collect-earningsdata",
    summary="Generate CSV with earnings data for a user",
    description="""
Accepts user information and returns a downloadable CSV file with earnings data.

**The returned CSV includes**:
- 'artist_id'
- 'partner_name'
- 'track_title'
- 'earning_amount'
- 'currency'
- 'date'

**This is a simulated earnings dataset for development purposes.**
**Note:** Swagger UI will only show the text.  
To download the file, use a client like Postman, curl, or your browser.
"""
)

def collect_earnings_data(
    data: CollectEarningsRequest = Body(...),
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

    # Crear CSV en memoria
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=earnings_{data.user_id}.csv"}
    )
