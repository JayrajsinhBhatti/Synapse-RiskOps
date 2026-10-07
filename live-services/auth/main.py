"""
Auth Service (synapse-live-auth)
Port 9002
Handles token validation, user authentication, queries PostgreSQL and caches in Redis.
"""

import os
import uuid
import json
import logging
from typing import Optional
from pydantic import BaseModel
import asyncpg
import redis.asyncio as aioredis
from prometheus_client import Counter

from shared.base_service import create_base_app

logger = logging.getLogger("auth_service")

SERVICE_NAME = os.getenv("SERVICE_NAME", "auth-service")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://synapse_admin:synapse_dev_2026@postgres:5432/synapse_riskops")
REDIS_URL = os.getenv("REDIS_URL", "redis://live-redis:6379/0")

# Service-specific metrics
auth_token_validations = Counter(
    "auth_token_validations_total",
    "Total auth token validations",
    ["result"]
)
auth_cache_hits = Counter(
    "auth_cache_hits_total",
    "Total auth cache hits"
)
auth_cache_misses = Counter(
    "auth_cache_misses_total",
    "Total auth cache misses"
)

app = create_base_app(
    service_name=SERVICE_NAME,
    title="Synapse Live Auth Service",
    description="Authentication and session management microservice"
)

db_pool: Optional[asyncpg.Pool] = None
redis_client: Optional[aioredis.Redis] = None


@app.on_event("startup")
async def init_resources():
    global db_pool, redis_client
    try:
        db_pool = await asyncpg.create_pool(
            dsn=DATABASE_URL,
            min_size=2,
            max_size=10,
            command_timeout=10.0
        )
        logger.info("Connected to PostgreSQL successfully")
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")

    try:
        redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
        await redis_client.ping()
        logger.info("Connected to Redis successfully")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")


@app.on_event("shutdown")
async def close_resources():
    global db_pool, redis_client
    if db_pool:
        await db_pool.close()
    if redis_client:
        await redis_client.close()


class VerifyRequest(BaseModel):
    token: Optional[str] = None
    username: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: Optional[str] = "password"


@app.post("/verify")
async def verify_token(req: VerifyRequest):
    token = req.token or "default_token"
    username = req.username or "user_test"

    # 1. Check Redis Cache
    cached_session = None
    if redis_client:
        try:
            cached = await redis_client.get(f"auth:token:{token}")
            if cached:
                auth_cache_hits.inc()
                auth_token_validations.labels(result="valid_cached").inc()
                cached_session = json.loads(cached)
                return {"valid": True, "source": "cache", "user": cached_session}
        except Exception as e:
            logger.warning(f"Redis get failed: {e}")

    auth_cache_misses.inc()

    # 2. Query PostgreSQL live_services.users
    user_row = None
    if db_pool:
        try:
            async with db_pool.acquire() as conn:
                user_row = await conn.fetchrow(
                    "SELECT id, username, email, role FROM live_services.users WHERE username = $1 LIMIT 1",
                    username
                )
        except Exception as e:
            logger.error(f"Postgres query failed: {e}")
            raise

    if not user_row:
        # Fallback query if username wasn't matched
        if db_pool:
            async with db_pool.acquire() as conn:
                user_row = await conn.fetchrow("SELECT id, username, email, role FROM live_services.users LIMIT 1")

    if user_row:
        user_data = {
            "id": user_row["id"],
            "username": user_row["username"],
            "email": user_row["email"],
            "role": user_row["role"]
        }
        # Save to Redis with 120s TTL
        if redis_client:
            try:
                await redis_client.setex(f"auth:token:{token}", 120, json.dumps(user_data))
            except Exception as e:
                logger.warning(f"Redis set failed: {e}")

        auth_token_validations.labels(result="valid_db").inc()
        return {"valid": True, "source": "db", "user": user_data}

    auth_token_validations.labels(result="invalid").inc()
    return {"valid": False, "source": "none", "user": None}


@app.post("/login")
async def login(req: LoginRequest):
    token = str(uuid.uuid4())
    user_data = {"id": 1, "username": req.username, "email": f"{req.username}@synapse.io", "role": "user"}

    if db_pool:
        try:
            async with db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT id, username, email, role FROM live_services.users WHERE username = $1",
                    req.username
                )
                if row:
                    user_data = {"id": row["id"], "username": row["username"], "email": row["email"], "role": row["role"]}
        except Exception as e:
            logger.warning(f"Postgres login fetch failed: {e}")

    if redis_client:
        try:
            await redis_client.setex(f"auth:token:{token}", 300, json.dumps(user_data))
        except Exception as e:
            logger.warning(f"Redis set failed: {e}")

    return {"token": token, "user": user_data}


@app.get("/users/{username}")
async def get_user(username: str):
    if db_pool:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, username, email, role, created_at FROM live_services.users WHERE username = $1",
                username
            )
            if row:
                return dict(row)
    return {"error": "User not found"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9002)
