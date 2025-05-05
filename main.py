import os
from fastapi import FastAPI, Header, HTTPException
from typing import Optional

app = FastAPI()

API_KEY = os.getenv("API_KEY")
print("Loaded API_KEY from environment:", repr(API_KEY))

def verify_key(access_key: Optional[str]):
    if access_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

@app.get("/api/royalty/advance-amount")
def get_advance_amount(
    partner_key: Optional[str] = None,
    email: Optional[str] = None,
    access_key: Optional[str] = Header(None)
):
    verify_key(access_key)
    return {
        "advance_amount": 10000,
        "currency": "USD",
        "status": "qualified"
    }

@app.get("/api/royalty/deal-status")
def get_royalty_advance_status(
    partner_key: Optional[str] = None,
    full_name: Optional[str] = None,
    access_key: Optional[str] = Header(None)
):
    verify_key(access_key)
    return {
        "has_royalty_advance": True,
        "agreement_id": "RAG-98765",
        "status": "completed",
        "source_system": "Salesforce",
        "effective_date": "2024-01-15"
    }
