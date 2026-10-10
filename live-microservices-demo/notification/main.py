"""
Notification Service (Port 9109)
Emits and stores customer notifications (Order Confirmation, Payment Success, Shipping Alerts).
"""

import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Dict, List
from fastapi import HTTPException
from pydantic import BaseModel

# Add parent to path for shared imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.base_service import create_microservice_app
from shared.models import NotificationEvent

PORT = int(os.getenv("PORT", 9109))
SERVICE_NAME = "notification-service"

app = create_microservice_app(
    service_name=SERVICE_NAME,
    title="Synapse E-Commerce Notification Service",
    port=PORT,
    description="Customer alerts, order confirmations, and messaging feeds",
)

NOTIFICATIONS_DB: Dict[str, List[NotificationEvent]] = {}


class CreateNotificationRequest(BaseModel):
    user_id: str
    type: str
    title: str
    message: str


@app.post("/notifications", response_model=NotificationEvent)
async def dispatch_notification(req: CreateNotificationRequest):
    nid = f"notif-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()
    event = NotificationEvent(
        id=nid,
        user_id=req.user_id,
        type=req.type,
        title=req.title,
        message=req.message,
        timestamp=now,
        read=False,
    )
    if req.user_id not in NOTIFICATIONS_DB:
        NOTIFICATIONS_DB[req.user_id] = []
    NOTIFICATIONS_DB[req.user_id].insert(0, event)
    return event


@app.get("/notifications/{user_id}", response_model=List[NotificationEvent])
async def get_user_notifications(user_id: str):
    return NOTIFICATIONS_DB.get(user_id, [])


@app.post("/notifications/{user_id}/mark-read")
async def mark_read(user_id: str):
    notifs = NOTIFICATIONS_DB.get(user_id, [])
    for n in notifs:
        n.read = True
    return {"status": "ok", "count": len(notifs)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)
