"""
Payment Service (synapse-live-payments)
Port 9004
Processes transactions, inserts into PostgreSQL and publishes events to RabbitMQ.
"""

import os
import time
import uuid
import json
import logging
from typing import Optional
from pydantic import BaseModel, Field
import asyncpg
import aio_pika
from prometheus_client import Counter, Histogram
from fastapi import HTTPException

from shared.base_service import create_base_app

logger = logging.getLogger("payment_service")

SERVICE_NAME = os.getenv("SERVICE_NAME", "payment-service")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://synapse_admin:synapse_dev_2026@postgres:5432/synapse_riskops")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@live-rabbitmq:5672/")

# Service-specific metrics
payments_processed = Counter(
    "payments_processed_total",
    "Total payments processed",
    ["status", "provider"]
)
payment_duration = Histogram(
    "payment_processing_duration_seconds",
    "Time taken to process payment",
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

app = create_base_app(
    service_name=SERVICE_NAME,
    title="Synapse Live Payment Service",
    description="Payment processing and transaction settlement microservice"
)

db_pool: Optional[asyncpg.Pool] = None
rabbitmq_connection: Optional[aio_pika.RobustConnection] = None
rabbitmq_channel: Optional[aio_pika.RobustChannel] = None


@app.on_event("startup")
async def init_resources():
    global db_pool, rabbitmq_connection, rabbitmq_channel
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
        # Declare payments queue
        await rabbitmq_channel.declare_queue("payments_queue", durable=True)
        logger.info("Connected to RabbitMQ successfully and declared payments_queue")
    except Exception as e:
        logger.error(f"Failed to connect to RabbitMQ: {e}")


@app.on_event("shutdown")
async def close_resources():
    global db_pool, rabbitmq_connection
    if db_pool:
        await db_pool.close()
    if rabbitmq_connection and not rabbitmq_connection.is_closed:
        await rabbitmq_connection.close()


class PaymentRequest(BaseModel):
    order_id: str
    amount: float = Field(..., gt=0)
    payment_method: str = "CREDIT_CARD"
    provider: str = "STRIPE"


@app.post("/payments")
async def process_payment(req: PaymentRequest):
    start_time = time.time()
    payment_id = f"PAY-{uuid.uuid4().hex[:10].upper()}"

    if not db_pool:
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    # 1. Insert into PostgreSQL
    try:
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO live_services.payments (payment_id, order_id, amount, status, payment_method)
                VALUES ($1, $2, $3, $4, $5)
                """,
                payment_id, req.order_id, req.amount, "COMPLETED", req.payment_method
            )
    except Exception as e:
        logger.error(f"Failed to record payment in DB: {e}")
        payments_processed.labels(status="FAILED", provider=req.provider).inc()
        raise HTTPException(status_code=500, detail="Database write failure")

    # 2. Publish to RabbitMQ
    if rabbitmq_channel and not rabbitmq_channel.is_closed:
        try:
            event = {
                "event": "payment.completed",
                "payment_id": payment_id,
                "order_id": req.order_id,
                "amount": req.amount,
                "provider": req.provider,
                "timestamp": time.time()
            }
            await rabbitmq_channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(event).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key="payments_queue"
            )
        except Exception as e:
            logger.warning(f"RabbitMQ publish warning: {e}")

    duration = time.time() - start_time
    payment_duration.observe(duration)
    payments_processed.labels(status="COMPLETED", provider=req.provider).inc()

    return {
        "payment_id": payment_id,
        "order_id": req.order_id,
        "amount": req.amount,
        "status": "COMPLETED",
        "provider": req.provider,
        "processed_at": time.time()
    }


@app.get("/payments/{payment_id}")
async def get_payment(payment_id: str):
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, payment_id, order_id, amount, status, payment_method, created_at FROM live_services.payments WHERE payment_id = $1",
            payment_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Payment record not found")
        return dict(row)


@app.get("/payments")
async def list_payments():
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, payment_id, order_id, amount, status, payment_method, created_at FROM live_services.payments ORDER BY id DESC LIMIT 50"
        )
        return [dict(r) for r in rows]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9004)
