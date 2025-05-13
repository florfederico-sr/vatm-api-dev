import os
from fastapi import FastAPI, Header, HTTPException, Body
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

API_KEY = os.getenv("API_KEY")

def verify_key(access_key: str):
    if access_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

# ------------------------------
# Advance Amount Input & Output
# ------------------------------
class AdvanceInput(BaseModel):
    trended_annual: float
    cushion: float
    decline_rate: float
    term_years: float
    frequency: str
    discount_rate: float

    class Config:
        schema_extra = {
            "example": {
                "trended_annual": 2000,
                "cushion": 0.1,
                "decline_rate": 0.0,
                "term_years": 2,
                "frequency": "monthly",
                "discount_rate": 0.05
            }
        }

class AdvanceAmountResponse(BaseModel):
    inputs: AdvanceInput
    projected_advance: float
    currency: str

    class Config:
        schema_extra = {
            "example": {
                "inputs": {
                    "trended_annual": 2000,
                    "cushion": 0.1,
                    "decline_rate": 0.0,
                    "term_years": 2,
                    "frequency": "monthly",
                    "discount_rate": 0.05
                },
                "projected_advance": 3420.0,
                "currency": "USD"
            }
        }

@app.post("/api/royalty/advance-amount", response_model=AdvanceAmountResponse)
def calculate_advance_amount(
    data: AdvanceInput = Body(...),
    access_key: str = Header(...)
):
    verify_key(access_key)

    projected_value = data.trended_annual * (1 - data.cushion) * (1 - data.discount_rate) * data.term_years

    return {
        "inputs": data,
        "projected_advance": round(projected_value, 2),
        "currency": "USD"
    }

# ------------------------------
# Deal Status Input & Output
# ------------------------------
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
                "full_name": "Joe Smith",
                "email_address": "user@example.com",
                "cell_number": "+15555555555",
                "partner_name": "cinq"
            }
        }

# ----- Deal Status Response -----
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
                "partner_name": "Cinq"
            }
        }

@app.post("/api/royalty/active_deal", response_model=DealStatusResponse)
def get_royalty_advance_status(
    data: DealStatusInput = Body(...),
    access_key: str = Header(...)
):
    verify_key(access_key)

    return {
        "status": "allowed",
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
