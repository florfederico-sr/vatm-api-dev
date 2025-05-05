import os
from fastapi import FastAPI, Header, HTTPException, Query
from typing import Optional

app = FastAPI()

API_KEY = os.getenv("API_KEY")

def verify_key(access_key: str):
    if access_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

@app.get("/api/royalty/advance-amount")
def get_advance_amount(
    trended_annual: float = Query(..., description="Estimated annual earnings (e.g. 2000)"),
    cushion: float = Query(..., description="Cushion as decimal (e.g. 0.10 for 10%)"),
    decline_rate: float = Query(..., description="Decline rate as decimal (e.g. 0.0 for 0%)"),
    term_years: float = Query(..., description="Contract term in years (e.g. 1.5)"),
    frequency: str = Query(..., description="Payment frequency (e.g. Monthly)"),
    discount_rate: float = Query(..., description="Discount rate as decimal (e.g. 0.19 for 19%)"),
    access_key: str = Header(...)
):
    verify_key(access_key)

    # Simple forecast calculation
    projected_value = trended_annual * (1 - cushion) * (1 - discount_rate) * term_years

    return {
        "inputs": {
            "trended_annual": trended_annual,
            "cushion": cushion,
            "decline_rate": decline_rate,
            "term_years": term_years,
            "frequency": frequency,
            "discount_rate": discount_rate
        },
        "projected_advance": round(projected_value, 2),
        "currency": "USD"
    }

@app.get("/api/royalty/deal-status")
def get_royalty_advance_status(
    partner_key: Optional[str] = Query(None, description="External partner reference key"),
    full_name: Optional[str] = Query(None, description="Full name of the artist or contact"),
    access_key: str = Header(...)
):
    verify_key(access_key)

    return {
        "has_royalty_advance": True,
        "agreement_id": "RAG-98765",
        "status": "completed",
        "source_system": "Salesforce",
        "effective_date": "2024-01-15",
        "partner_key": partner_key,
        "full_name": full_name
    }
