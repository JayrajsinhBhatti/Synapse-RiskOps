"""
Payment Service (Port 9108)
Processes simulated financial transactions and authorization holds.
Primary target for high-latency and dependency error chaos experiments.
"""

import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Dict
from fastapi import HTTPException

# Add parent to path for shared imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.base_service import create_microservice_app
from shared.models import PaymentProcessRequest, PaymentReceipt

PORT = int(os.getenv("PORT", 9108))
SERVICE_NAME = "payment-service"

app = create_microservice_app(
    service_name=SERVICE_NAME,
    title="Synapse E-Commerce Payment Gateway",
    port=PORT,
    description="Processes authorizations, captures funds, and simulates payment processing",
)

PAYMENTS_LOG: Dict[str, PaymentReceipt] = {}


@app.post("/payments/process", response_model=PaymentReceipt)
async def process_payment(req: PaymentProcessRequest):
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Payment amount must be greater than zero")

    # Generate receipt
    pay_id = f"pay-{uuid.uuid4().hex[:8]}"
    ref = f"tx_ref_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()

    receipt = PaymentReceipt(
        payment_id=pay_id,
        order_id=req.order_id,
        amount=round(req.amount, 2),
        status="SUCCESS",
        transaction_ref=ref,
        processed_at=now,
    )
    PAYMENTS_LOG[pay_id] = receipt
    return receipt


@app.get("/payments/{payment_id}", response_model=PaymentReceipt)
async def get_payment(payment_id: str):
    receipt = PAYMENTS_LOG.get(payment_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Payment not found")
    return receipt


@app.get("/payments/by-order/{order_id}")
async def get_payment_by_order(order_id: str):
    for r in PAYMENTS_LOG.values():
        if r.order_id == order_id:
            return r
    raise HTTPException(status_code=404, detail="No payment for this order")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)
