import os
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI()

# Load API Key from environment variable
API_KEY = os.getenv("API_KEY")

# API Key validation
def verify_key(access_key: str):
    if access_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

# ------------------------------
# Advance Amount Endpoint Models
# ------------------------------

class AdvanceInput(BaseModel):
    trended_annual: str = Field(..., example="$2,000", description="Estimated annual earnings (e.g. $2,000)")
    cushion: str = Field(..., example="10.0%", description="Buffer margin (e.g. 10%)")
    decline_rate: str = Field(..., example="0%", description="Expected decline rate (e.g. 0%)")
    term_years: float = Field(..., example=1.5, description="Contract term in years")
    frequency: str = Field(..., example="Monthly", description="Payment frequency (e.g. Monthly)")
    discount_rate: str = Field(..., example="19.0%", description="Discount rate (e.g. 19%)")

def parse_percentage(value: str) -> float:
    return float(value.strip('%')) / 100

def parse_currency(value: str) -> float:
    return float(value.replace('$', '').replace(',', ''))

@app.post("/api/royalty/advance-amount")
def get_advance_amount(
    data: AdvanceInput,
    access_key: str = Header(...)
):
    verify_key(access_key)

    # Parse and calculate
    trended_annual = parse_currency(data.trended_annual)
    cushion = parse_percentage(data.cushion)
    discount_rate = parse_percentage(data.discount_rate)
    decline_rate = parse_percentage(data.decline_rate)
    term = data.term_years

    projected_value = trended_annual * (1 - cushion) * (1 - discount_rate) * term

    return {
        "input_data": data.dict(),
        "projected_advance": round(projected_value, 2),
        "currency": "USD"
    }

# ------------------------------
# Deal Status Endpoint Models
# ------------------------------

class DealStatusInput(BaseModel):
    partner_key: Optional[str] = Field(None, example="partner-123", description="External partner reference key")
    full_name: Optional[str] = Field(None, example="Taylor Swift", description="Full name of the artist or contact")

class DealStatusOutput(BaseModel):
    has_royalty_advance: bool = Field(..., example=True)
    agreement_id: str = Field(..., example="RAG-98765")
    status: str = Field(..., example="completed")
    source_system: str = Field(..., example="Salesforce")
    effective_date: str = Field(..., example="2024-01-15")

@app.post("/api/royalty/deal-status", response_model=DealStatusOutput)
def get_royalty_advance_status(
    data: DealStatusInput,
    access_key: str = Header(...)
):
    verify_key(access_key)

    return {
        "has_royalty_advance": True,
        "agreement_id": "RAG-98765",
        "status": "completed",
        "source_system": "Salesforce",
        "effective_date": "2024-01-15"
    }
