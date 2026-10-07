"""
Order Service (synapse-live-orders)
Port 9003
Orchestrates order creation by calling inventory-service and payment-service,
recording in PostgreSQL and publishing events to RabbitMQ.
"""

import os
import time
import uuid
import json
import logging
from typing import Optional
from pydantic import BaseModel, Field
import httpx
import asyncpg
import aio_pika
from prometheus_client import Counter, Histogram
from fastapi import HTTPException

from shared.base_service import create_base_app

logger = logging.getLogger("order_service")

SERVICE_NAME = os.getenv("SERVICE_NAME", "order-service")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://synapse_admin:synapse_dev_2026@postgres:5432/synapse_riskops")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://live-payments:9004")
INVENTORY_SERVICE_URL = os.getenv("INVENTORY_SERVICE_URL", "http://live-inventory:9005")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@live-rabbitmq:5672/")

# Metrics
orders_created = Counter("orders_created_total", "Total orders successfully created")
orders_failed = Counter("orders_failed_total", "Total orders failed", ["reason"])
order_duration = Histogram(
    "order_processing_duration_seconds",
    "Time taken to process an order",
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

app = create_base_app(
    service_name=SERVICE_NAME,
    title="Synapse Live Order Service",
    description="Core order processing and dependency orchestration microservice"
)

db_pool: Optional[asyncpg.Pool] = None
rabbitmq_connection: Optional[aio_pika.RobustConnection] = None
rabbitmq_channel: Optional[aio_pika.RobustChannel] = None
http_client: Optional[httpx.AsyncClient] = None


@app.on_event("startup")
async def init_resources():
    global db_pool, rabbitmq_connection, rabbitmq_channel, http_client
    http_client = httpx.AsyncClient(timeout=10.0)

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
        rabbitmq_connection = await aio_pika.connect_robust(RABBITMQ_URL)
        rabbitmq_channel = await rabbitmq_connection.channel()
        await rabbitmq_channel.declare_queue("orders_queue", durable=True)
        logger.info("Connected to RabbitMQ successfully and declared orders_queue")
    except Exception as e:
        logger.error(f"Failed to connect to RabbitMQ: {e}")


@app.on_event("shutdown")
async def close_resources():
    global db_pool, rabbitmq_connection, http_client
    if http_client:
        await http_client.aclose()
    if db_pool:
        await db_pool.close()
    if rabbitmq_connection and not rabbitmq_connection.is_closed:
        await rabbitmq_connection.close()


class CreateOrderRequest(BaseModel):
    user_id: str = "user_test"
    sku: str = "SKU-LAPTOP-01"
    quantity: int = Field(1, ge=1)


@app.post("/orders")
async def create_order(req: CreateOrderRequest):
    start_time = time.time()
    order_id = f"ORD-{uuid.uuid4().hex[:10].upper()}"

    if not db_pool:
        orders_failed.labels(reason="db_unavailable").inc()
        raise HTTPException(status_code=503, detail="Database unavailable")

    # 1. Check & Reserve Inventory (HTTP call to inventory-service)
    try:
        inv_res = await http_client.post(
            f"{INVENTORY_SERVICE_URL}/inventory/reserve",
            json={"sku": req.sku, "quantity": req.quantity}
        )
        if inv_res.status_code != 200:
            orders_failed.labels(reason="inventory_reserve_failed").inc()
            raise HTTPException(status_code=400, detail="Failed to reserve inventory")
        inv_data = inv_res.json()
        unit_price = inv_data.get("unit_price", 99.99)
    except httpx.RequestError as e:
        logger.error(f"Inventory service call error: {e}")
        orders_failed.labels(reason="inventory_unreachable").inc()
        raise HTTPException(status_code=502, detail="Inventory service unreachable")

    total_amount = round(unit_price * req.quantity, 2)

    # 2. Process Payment (HTTP call to payment-service)
    try:
        pay_res = await http_client.post(
            f"{PAYMENT_SERVICE_URL}/payments",
            json={"order_id": order_id, "amount": total_amount}
        )
        if pay_res.status_code != 200:
            orders_failed.labels(reason="payment_declined").inc()
            raise HTTPException(status_code=400, detail="Payment processing failed")
        pay_data = pay_res.json()
    except httpx.RequestError as e:
        logger.error(f"Payment service call error: {e}")
        orders_failed.labels(reason="payment_unreachable").inc()
        raise HTTPException(status_code=502, detail="Payment service unreachable")

    # 3. Insert Order in PostgreSQL
    try:
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO live_services.orders (order_id, user_id, sku, quantity, total_amount, status)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                order_id, req.user_id, req.sku, req.quantity, total_amount, "PAID"
            )
    except Exception as e:
        logger.error(f"PostgreSQL order insert error: {e}")
        orders_failed.labels(reason="db_insert_failed").inc()
        raise HTTPException(status_code=500, detail="Database write failure")

    # 4. Publish Event to RabbitMQ
    if rabbitmq_channel and not rabbitmq_channel.is_closed:
        try:
            event = {
                "event": "order.created",
                "order_id": order_id,
                "user_id": req.user_id,
                "sku": req.sku,
                "quantity": req.quantity,
                "total_amount": total_amount,
                "payment_id": pay_data.get("payment_id"),
                "timestamp": time.time()
            }
            await rabbitmq_channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(event).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key="orders_queue"
            )
        except Exception as e:
            logger.warning(f"RabbitMQ publish error: {e}")

    duration = time.time() - start_time
    order_duration.observe(duration)
    orders_created.inc()

    return {
        "order_id": order_id,
        "user_id": req.user_id,
        "sku": req.sku,
        "quantity": req.quantity,
        "total_amount": total_amount,
        "status": "PAID",
        "payment": pay_data
    }


@app.get("/orders")
async def list_orders():
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database unavailable")

    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, order_id, user_id, sku, quantity, total_amount, status, created_at FROM live_services.orders ORDER BY id DESC LIMIT 50"
        )
        return [dict(r) for r in rows]


@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database unavailable")

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, order_id, user_id, sku, quantity, total_amount, status, created_at FROM live_services.orders WHERE order_id = $1",
            order_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Order not found")
        return dict(row)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9003)
