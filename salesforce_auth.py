import jwt
import time
import requests
import os
from cryptography.hazmat.primitives import serialization

# === CONFIGURATION ===
PRIVATE_KEY_FILE = "private.key"
CLIENT_ID = os.getenv("TU_CLIENT_ID") #"TU_CLIENT_ID"
USERNAME = os.getenv("TU_USERNAME") #"TU_USERNAME"
AUDIENCE = "https://test.salesforce.com"

def get_salesforce_token():
    with open(PRIVATE_KEY_FILE, "rb") as key_file:
        private_key = key_file.read()

    issued_at = int(time.time())
    expiration_time = issued_at + 300

    jwt_payload = {
        "iss": CLIENT_ID,
        "sub": USERNAME,
        "aud": AUDIENCE,
        "exp": expiration_time
    }

    encoded_jwt = jwt.encode(jwt_payload, private_key, algorithm="RS256")

    token_response = requests.post(
        f"{AUDIENCE}/services/oauth2/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": encoded_jwt
        }
    )

    if token_response.status_code == 200:
        data = token_response.json()
        return data["access_token"], data["instance_url"]
    else:
        raise Exception(f"Failed to get token: {token_response.text}")
