"""
Notification Service (synapse-live-notifications)
Port 9006
Consumes async messages from RabbitMQ (orders_queue, payments_queue),
processes alerts and notifications, and tracks throughput metrics.
"""

import os
import asyncio
import uuid
import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import aio_pika
from prometheus_client import Counter, Gauge

from shared.base_service import create_base_app

logger = logging.getLogger("notification_service")

SERVICE_NAME = os.getenv("SERVICE_NAME", "notification-svc")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@live-rabbitmq:5672/")

# Metrics
notifications_sent = Counter(
    "notifications_sent_total",
    "Total notifications sent",
    ["channel", "status"]
)
messages_consumed = Counter(
    "queue_messages_consumed_total",
    "Total messages consumed from RabbitMQ",
    ["queue"]
)
consumer_lag = Gauge(
    "queue_consumer_lag",
    "Estimated consumer lag in seconds"
)

app = create_base_app(
    service_name=SERVICE_NAME,
    title="Synapse Live Notification Service",
    description="Async event consumer and notification dispatcher"
)

recent_notifications: List[Dict[str, Any]] = []
rabbitmq_connection: Optional[aio_pika.RobustConnection] = None
consumer_task: Optional[asyncio.Task] = None


async def start_rabbitmq_consumer():
    global rabbitmq_connection
    retry_count = 0
    while retry_count < 30:
        try:
            rabbitmq_connection = await aio_pika.connect_robust(RABBITMQ_URL)
            channel = await rabbitmq_connection.channel()
            await channel.set_qos(prefetch_count=10)

            orders_queue = await channel.declare_queue("orders_queue", durable=True)
            payments_queue = await channel.declare_queue("payments_queue", durable=True)

            logger.info("Connected to RabbitMQ, starting consumer loops...")

            async def process_order_message(message: aio_pika.IncomingMessage):
                async with message.process():
                    try:
                        data = json.loads(message.body.decode())
                        messages_consumed.labels(queue="orders_queue").inc()
                        notif = {
                            "id": f"NOTIF-{uuid.uuid4().hex[:8].upper()}",
                            "event": "order.created",
                            "recipient": data.get("user_id", "user@synapse.io"),
                            "subject": f"Order Confirmation: {data.get('order_id')}",
                            "channel": "EMAIL",
                            "status": "SENT",
                            "details": data
                        }
                        notifications_sent.labels(channel="EMAIL", status="SENT").inc()
                        recent_notifications.insert(0, notif)
                        if len(recent_notifications) > 100:
                            recent_notifications.pop()
                    except Exception as e:
                        logger.error(f"Error processing order message: {e}")

            async def process_payment_message(message: aio_pika.IncomingMessage):
                async with message.process():
                    try:
                        data = json.loads(message.body.decode())
                        messages_consumed.labels(queue="payments_queue").inc()
                        notif = {
                            "id": f"NOTIF-{uuid.uuid4().hex[:8].upper()}",
                            "event": "payment.completed",
                            "recipient": "finance@synapse.io",
                            "subject": f"Payment Receipt: {data.get('payment_id')}",
                            "channel": "SLACK",
                            "status": "SENT",
                            "details": data
                        }
                        notifications_sent.labels(channel="SLACK", status="SENT").inc()
                        recent_notifications.insert(0, notif)
                        if len(recent_notifications) > 100:
                            recent_notifications.pop()
                    except Exception as e:
                        logger.error(f"Error processing payment message: {e}")

            await orders_queue.consume(process_order_message)
            await payments_queue.consume(process_payment_message)
            break

        except Exception as e:
            retry_count += 1
            logger.warning(f"RabbitMQ consumer connection attempt {retry_count} failed: {e}. Retrying in 2s...")
            await asyncio.sleep(2)


@app.on_event("startup")
async def startup_resources():
    global consumer_task
    consumer_task = asyncio.create_task(start_rabbitmq_consumer())


@app.on_event("shutdown")
async def shutdown_resources():
    global rabbitmq_connection, consumer_task
    if consumer_task:
        consumer_task.cancel()
    if rabbitmq_connection and not rabbitmq_connection.is_closed:
        await rabbitmq_connection.close()


class DirectNotification(BaseModel):
    recipient: str
    message: str
    channel: str = "EMAIL"


@app.get("/notifications")
async def list_notifications():
    return {
        "count": len(recent_notifications),
        "notifications": recent_notifications[:50]
    }


@app.post("/notifications/send")
async def send_direct_notification(req: DirectNotification):
    notif = {
        "id": f"NOTIF-{uuid.uuid4().hex[:8].upper()}",
        "event": "direct.message",
        "recipient": req.recipient,
        "subject": "Direct Notification",
        "channel": req.channel,
        "status": "SENT",
        "message": req.message
    }
    notifications_sent.labels(channel=req.channel, status="SENT").inc()
    recent_notifications.insert(0, notif)
    if len(recent_notifications) > 100:
        recent_notifications.pop()
    return notif


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9006)
