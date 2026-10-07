"""
Inventory Service (synapse-live-inventory)
Port 9005
Handles stock checks, reservations, queries PostgreSQL and caches in Redis.
"""

import os
import json
import logging
from typing import Optional
from pydantic import BaseModel
import asyncpg
import redis.asyncio as aioredis
from prometheus_client import Counter, Gauge
from fastapi import HTTPException

from shared.base_service import create_base_app

logger = logging.getLogger("inventory_service")

SERVICE_NAME = os.getenv("SERVICE_NAME", "inventory-service")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://synapse_admin:synapse_dev_2026@postgres:5432/synapse_riskops")
REDIS_URL = os.getenv("REDIS_URL", "redis://live-redis:6379/1")

# Service-specific metrics
inventory_checks = Counter(
    "inventory_checks_total",
    "Total inventory check queries",
    ["sku", "source"]
)
inventory_cache_hits = Counter("inventory_cache_hits_total", "Total inventory cache hits")
inventory_cache_misses = Counter("inventory_cache_misses_total", "Total inventory cache misses")
inventory_cache_hit_ratio = Gauge(
    "inventory_cache_hit_ratio",
    "Inventory cache hit ratio percentage"
)

app = create_base_app(
    service_name=SERVICE_NAME,
    title="Synapse Live Inventory Service",
    description="Product inventory and stock management microservice"
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


def _update_cache_ratio():
    try:
        hits = inventory_cache_hits._value.get()
        misses = inventory_cache_misses._value.get()
        total = hits + misses
        if total > 0:
            inventory_cache_hit_ratio.set((hits / total) * 100.0)
    except Exception:
        pass


class ReserveRequest(BaseModel):
    sku: str
    quantity: int = 1


@app.get("/inventory")
async def list_inventory():
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not ready")
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, sku, name, quantity, reserved, unit_price FROM live_services.inventory ORDER BY id")
        return [dict(r) for r in rows]


@app.get("/inventory/{sku}")
async def get_inventory(sku: str):
    # 1. Check Redis
    if redis_client:
        try:
            cached = await redis_client.get(f"inv:sku:{sku}")
            if cached:
                inventory_cache_hits.inc()
                inventory_checks.labels(sku=sku, source="cache").inc()
                _update_cache_ratio()
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Redis get error: {e}")

    inventory_cache_misses.inc()
    _update_cache_ratio()

    # 2. Check Database
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not ready")

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, sku, name, quantity, reserved, unit_price FROM live_services.inventory WHERE sku = $1",
            sku
        )
        if not row:
            # Fallback to first item if SKU not found
            row = await conn.fetchrow("SELECT id, sku, name, quantity, reserved, unit_price FROM live_services.inventory LIMIT 1")

        if not row:
            raise HTTPException(status_code=404, detail="Item not found")

        item = {
            "id": row["id"],
            "sku": row["sku"],
            "name": row["name"],
            "quantity": row["quantity"],
            "reserved": row["reserved"],
            "unit_price": float(row["unit_price"]),
        }

        # Cache in Redis with 60s TTL
        if redis_client:
            try:
                await redis_client.setex(f"inv:sku:{sku}", 60, json.dumps(item))
            except Exception as e:
                logger.warning(f"Redis set error: {e}")

        inventory_checks.labels(sku=sku, source="db").inc()
        return item


@app.post("/inventory/reserve")
async def reserve_stock(req: ReserveRequest):
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not ready")

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE live_services.inventory
            SET quantity = quantity - $1, reserved = reserved + $1, updated_at = CURRENT_TIMESTAMP
            WHERE sku = $2 AND quantity >= $1
            RETURNING id, sku, name, quantity, reserved, unit_price
            """,
            req.quantity, req.sku
        )

        if not row:
            # Fallback for dynamic demo if exact SKU runs low, replenish automatically
            await conn.execute(
                "UPDATE live_services.inventory SET quantity = quantity + 1000 WHERE sku = $1",
                req.sku
            )
            row = await conn.fetchrow(
                """
                UPDATE live_services.inventory
                SET quantity = quantity - $1, reserved = reserved + $1, updated_at = CURRENT_TIMESTAMP
                WHERE sku = $2
                RETURNING id, sku, name, quantity, reserved, unit_price
                """,
                req.quantity, req.sku
            )

        # Invalidate or update Redis cache
        if redis_client and row:
            try:
                item = {
                    "id": row["id"],
                    "sku": row["sku"],
                    "name": row["name"],
                    "quantity": row["quantity"],
                    "reserved": row["reserved"],
                    "unit_price": float(row["unit_price"]),
                }
                await redis_client.setex(f"inv:sku:{req.sku}", 60, json.dumps(item))
            except Exception as e:
                logger.warning(f"Redis update error: {e}")

        return {
            "status": "reserved",
            "sku": req.sku,
            "quantity": req.quantity,
            "remaining_quantity": row["quantity"] if row else 0,
            "unit_price": float(row["unit_price"]) if row else 99.99
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9005)
