"""
Order Service (Port 9107)
Coordinates multi-service distributed transaction:
1. Fetches user cart from cart-service
2. Atomically reserves stock via inventory-service
3. Executes financial charge via payment-service
4. Handles automatic rollback / stock release on payment failure
5. Dispatches customer alert via notification-service
6. Clears cart and persists confirmed order
"""

import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
import httpx
from fastapi import HTTPException

# Add parent to path for shared imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.base_service import create_microservice_app
from shared.models import Order, CheckoutRequest

PORT = int(os.getenv("PORT", 9107))
SERVICE_NAME = "order-service"

CART_SERVICE_URL = os.getenv("CART_SERVICE_URL", "http://localhost:9106")
INVENTORY_SERVICE_URL = os.getenv("INVENTORY_SERVICE_URL", "http://localhost:9105")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://localhost:9108")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:9109")

app = create_microservice_app(
    service_name=SERVICE_NAME,
    title="Synapse E-Commerce Order Service",
    port=PORT,
    description="Orchestrates distributed checkout, inventory reservation, and payment flows",
)

ORDERS_DB: Dict[str, Order] = {}


@app.post("/orders/checkout", response_model=Order)
async def checkout_order(req: CheckoutRequest):
    order_id = f"ord-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Step 1: Retrieve cart
        try:
            cart_resp = await client.get(f"{CART_SERVICE_URL}/cart/{req.user_id}")
            if cart_resp.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to fetch user cart")
            cart_data = cart_resp.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"Cart service unavailable: {exc}")

        items = cart_data.get("items", [])
        if not items:
            raise HTTPException(status_code=400, detail="Cannot checkout an empty cart")

        total_amount = cart_data.get("total_amount", 0.0)

        # Step 2: Reserve Inventory
        reserve_payload = {
            "order_id": order_id,
            "items": [{"product_id": i["product_id"], "quantity": i["quantity"]} for i in items],
        }
        try:
            inv_resp = await client.post(f"{INVENTORY_SERVICE_URL}/inventory/reserve", json=reserve_payload)
            if inv_resp.status_code != 200:
                detail = inv_resp.json().get("detail", "Inventory reservation failed")
                raise HTTPException(status_code=409, detail=detail)
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"Inventory service unavailable: {exc}")

        # Step 3: Execute Payment
        payment_payload = {
            "order_id": order_id,
            "user_id": req.user_id,
            "amount": total_amount,
            "payment_method": req.payment_method,
        }
        payment_id = None
        try:
            pay_resp = await client.post(f"{PAYMENT_SERVICE_URL}/payments/process", json=payment_payload)
            if pay_resp.status_code != 200:
                # Rollback reserved inventory!
                await client.post(f"{INVENTORY_SERVICE_URL}/inventory/release/{order_id}")
                raise HTTPException(status_code=502, detail=f"Payment processing failed: {pay_resp.text}")
            payment_data = pay_resp.json()
            payment_id = payment_data.get("payment_id")
        except (httpx.RequestError, HTTPException) as exc:
            # Compensating transaction: release inventory
            try:
                await client.post(f"{INVENTORY_SERVICE_URL}/inventory/release/{order_id}")
            except Exception:
                pass
            if isinstance(exc, HTTPException):
                raise exc
            raise HTTPException(status_code=503, detail=f"Payment service error: {exc}")

        # Step 4: Dispatch Notification
        try:
            notif_payload = {
                "user_id": req.user_id,
                "type": "ORDER_CONFIRMED",
                "title": f"Order Confirmed #{order_id}",
                "message": f"Your order of ${total_amount:.2f} ({len(items)} items) has been confirmed and paid.",
            }
            await client.post(f"{NOTIFICATION_SERVICE_URL}/notifications", json=notif_payload)
        except Exception:
            pass  # Non-fatal

        # Step 5: Clear Cart
        try:
            await client.delete(f"{CART_SERVICE_URL}/cart/{req.user_id}/clear")
        except Exception:
            pass

    # Record confirmed order
    order = Order(
        order_id=order_id,
        user_id=req.user_id,
        items=items,
        total_amount=total_amount,
        status="CONFIRMED",
        payment_id=payment_id,
        created_at=now,
        shipping_address=req.shipping_address,
    )
    ORDERS_DB[order_id] = order
    return order


@app.get("/orders/{order_id}", response_model=Order)
async def get_order(order_id: str):
    order = ORDERS_DB.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@app.get("/orders/user/{user_id}", response_model=List[Order])
async def get_user_orders(user_id: str):
    user_orders = [o for o in ORDERS_DB.values() if o.user_id == user_id]
    return sorted(user_orders, key=lambda o: o.created_at, reverse=True)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)
