"""
User Service (Port 9103)
Manages user profiles, addresses, and registration records.
"""

import os
import sys
from datetime import datetime, timezone
from typing import Dict
from fastapi import HTTPException

# Add parent to path for shared imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.base_service import create_microservice_app
from shared.models import UserProfile, UserRegisterRequest

PORT = int(os.getenv("PORT", 9103))
SERVICE_NAME = "user-service"

app = create_microservice_app(
    service_name=SERVICE_NAME,
    title="Synapse E-Commerce User Service",
    port=PORT,
    description="Maintains user profiles and account data",
)

# In-memory database with pre-seeded demo user
USERS_DB: Dict[str, Dict] = {
    "usr-admin": {
        "user_id": "usr-admin",
        "username": "admin",
        "email": "admin@synapse.io",
        "password_hash": "admin123",
        "full_name": "Platform Administrator",
        "address": "Synapse HQ, 100 Innovation Way, Silicon Valley, CA",
        "created_at": datetime.now(timezone.utc).isoformat(),
    },
    "usr-john": {
        "user_id": "usr-john",
        "username": "john_doe",
        "email": "john.doe@example.com",
        "password_hash": "password123",
        "full_name": "John Doe",
        "address": "456 Market St, San Francisco, CA",
        "created_at": datetime.now(timezone.utc).isoformat(),
    },
}


@app.post("/users", response_model=UserProfile)
async def create_user(req: UserRegisterRequest):
    # Check if username exists
    for u in USERS_DB.values():
        if u["username"].lower() == req.username.lower():
            raise HTTPException(status_code=400, detail="Username already exists")

    uid = f"usr-{len(USERS_DB) + 1}"
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "user_id": uid,
        "username": req.username,
        "email": req.email,
        "password_hash": req.password,
        "full_name": req.full_name,
        "address": req.address or "Default Delivery Address",
        "created_at": now,
    }
    USERS_DB[uid] = record
    return UserProfile(
        user_id=uid,
        username=record["username"],
        email=record["email"],
        full_name=record["full_name"],
        address=record["address"],
        created_at=now,
    )


@app.get("/users/{user_id}", response_model=UserProfile)
async def get_user_by_id(user_id: str):
    user = USERS_DB.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserProfile(**{k: v for k, v in user.items() if k != "password_hash"})


@app.get("/users/by-username/{username}")
async def get_user_by_username(username: str):
    for u in USERS_DB.values():
        if u["username"].lower() == username.lower():
            return u
    raise HTTPException(status_code=404, detail="User not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)
