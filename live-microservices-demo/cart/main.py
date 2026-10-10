"""
Cart Service (Port 9106)
Manages user shopping carts and communicates with catalog-service to validate items.
"""

import os
import sys
import threading
from typing import Dict, List
import httpx
from fastapi import HTTPException
from pydantic import BaseModel

# Add parent to path for shared imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.base_service import create_microservice_app
from shared.models import CartItem, CartState

PORT = int(os.getenv("PORT", 9106))
SERVICE_NAME = "cart-service"
CATALOG_SERVICE_URL = os.getenv("CATALOG_SERVICE_URL", "http://localhost:9104")

app = create_microservice_app(
    service_name=SERVICE_NAME,
    title="Synapse E-Commerce Cart Service",
    port=PORT,
    description="Maintains shopping carts and item aggregations",
)

# User Cart Storage: {user_id: [CartItem]}
CARTS_DB: Dict[str, List[CartItem]] = {}
_lock = threading.Lock()


class AddToCartRequest(BaseModel):
    user_id: str
    product_id: str
    quantity: int = 1


class UpdateQuantityRequest(BaseModel):
    user_id: str
    product_id: str
    quantity: int


def _calculate_cart(user_id: str) -> CartState:
    items = CARTS_DB.get(user_id, [])
    total = sum(item.price * item.quantity for item in items)
    return CartState(
        user_id=user_id,
        items=items,
        total_amount=round(total, 2),
    )


@app.get("/cart/{user_id}", response_model=CartState)
async def get_cart(user_id: str):
    with _lock:
        return _calculate_cart(user_id)


@app.post("/cart/add", response_model=CartState)
async def add_to_cart(req: AddToCartRequest):
    if req.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be at least 1")

    # Fetch product metadata from catalog-service
    async with httpx.AsyncClient(timeout=4.0) as client:
        try:
            resp = await client.get(f"{CATALOG_SERVICE_URL}/products/{req.product_id}")
            if resp.status_code != 200:
                raise HTTPException(status_code=404, detail="Product not found in catalog")
            product = resp.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"Catalog service error: {exc}")

    with _lock:
        if req.user_id not in CARTS_DB:
            CARTS_DB[req.user_id] = []

        existing = next((i for i in CARTS_DB[req.user_id] if i.product_id == req.product_id), None)
        if existing:
            existing.quantity += req.quantity
        else:
            CARTS_DB[req.user_id].append(
                CartItem(
                    product_id=product["id"],
                    name=product["name"],
                    price=product["price"],
                    quantity=req.quantity,
                    image_url=product["image_url"],
                )
            )

        return _calculate_cart(req.user_id)


@app.post("/cart/update", response_model=CartState)
async def update_cart_quantity(req: UpdateQuantityRequest):
    with _lock:
        if req.user_id not in CARTS_DB:
            raise HTTPException(status_code=404, detail="Cart is empty")

        if req.quantity <= 0:
            CARTS_DB[req.user_id] = [i for i in CARTS_DB[req.user_id] if i.product_id != req.product_id]
        else:
            item = next((i for i in CARTS_DB[req.user_id] if i.product_id == req.product_id), None)
            if item:
                item.quantity = req.quantity
            else:
                raise HTTPException(status_code=404, detail="Item not in cart")

        return _calculate_cart(req.user_id)


@app.delete("/cart/{user_id}/item/{product_id}", response_model=CartState)
async def remove_item(user_id: str, product_id: str):
    with _lock:
        if user_id in CARTS_DB:
            CARTS_DB[user_id] = [i for i in CARTS_DB[user_id] if i.product_id != product_id]
        return _calculate_cart(user_id)


@app.delete("/cart/{user_id}/clear")
async def clear_cart(user_id: str):
    with _lock:
        CARTS_DB[user_id] = []
    return {"status": "cleared", "user_id": user_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)
