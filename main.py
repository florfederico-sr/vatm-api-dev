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
    full_legal_name: Optional[str] = None
    email: Optional[str] = None
    cellphone: Optional[str] = None

@app.post("/api/royalty/deal-status")
def get_royalty_advance_status(
    data: DealStatusInput,
    access_key: str = Header(...)
):
    verify_key(access_key)

    return {
        "has_deal": True,
        "deal_id": "RAG-98765",
        "status": "active",
        "source_system": "Salesforce",
        "effective_date": "2024-01-15",
        "full_legal_name": data.full_legal_name,
        "email": data.email,
        "cellphone": data.cellphone
    }
