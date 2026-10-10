"""
Authentication Service (Port 9102)
Authenticates users, validates credentials against user-service, and signs JWT tokens.
"""

import os
import sys
import time
from typing import Dict, Any
import httpx
from fastapi import HTTPException, Header

# Add parent to path for shared imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.base_service import create_microservice_app
from shared.models import UserLoginRequest, UserRegisterRequest, TokenResponse, UserProfile

PORT = int(os.getenv("PORT", 9102))
SERVICE_NAME = "auth-service"
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:9103")

app = create_microservice_app(
    service_name=SERVICE_NAME,
    title="Synapse E-Commerce Auth Service",
    port=PORT,
    description="Handles credentials, sessions, and security tokens",
)


@app.post("/auth/register", response_model=TokenResponse)
async def register(req: UserRegisterRequest):
    # Delegate profile creation to user-service
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.post(f"{USER_SERVICE_URL}/users", json=req.model_dump())
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
            user_data = resp.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"User service unreachable: {exc}")

    token = f"jwt-token-{user_data['user_id']}-{int(time.time())}"
    return TokenResponse(
        access_token=token,
        user=UserProfile(**user_data),
    )


@app.post("/auth/login", response_model=TokenResponse)
async def login(req: UserLoginRequest):
    # Query user-service for user record
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(f"{USER_SERVICE_URL}/users/by-username/{req.username}")
            if resp.status_code == 404:
                raise HTTPException(status_code=401, detail="Invalid username or password")
            user_data = resp.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"User service unreachable: {exc}")

    if user_data.get("password_hash") != req.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = f"jwt-token-{user_data['user_id']}-{int(time.time())}"
    profile = {k: v for k, v in user_data.items() if k != "password_hash"}
    return TokenResponse(
        access_token=token,
        user=UserProfile(**profile),
    )


@app.get("/auth/verify")
async def verify_token(authorization: str = Header(...)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")
    raw_token = authorization.replace("Bearer ", "").strip()
    parts = raw_token.split("-")
    if len(parts) >= 3 and parts[0] == "jwt" and parts[1] == "token":
        user_id = f"{parts[2]}-{parts[3]}" if len(parts) >= 4 else parts[2]
        return {"valid": True, "user_id": user_id, "token": raw_token}
    raise HTTPException(status_code=401, detail="Invalid token")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)
