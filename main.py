import os
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

API_KEY = os.getenv("API_KEY")

def verify_key(access_key: str):
    if access_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

class AdvanceInput(BaseModel):
    trended_annual: float
    cushion: float
    decline_rate: float
    term_years: float
    frequency: str
    discount_rate: float

@app.post("/api/royalty/advance-amount")
def calculate_advance_amount(
    data: AdvanceInput,
    access_key: str = Header(...)
):
    verify_key(access_key)

    projected_value = data.trended_annual * (1 - data.cushion) * (1 - data.discount_rate) * data.term_years

    return {
        "inputs": data.dict(),
        "projected_advance": round(projected_value, 2),
        "currency": "USD"
    }

class DealStatusInput(BaseModel):
    user_id: str
    full_name: str
    email_address: Optional[str] = None
    cell_number: Optional[str] = None
    partner_name: Optional[str] = None

@app.post("/api/royalty/active_deal")
def get_royalty_advance_status(
    data: DealStatusInput,
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
