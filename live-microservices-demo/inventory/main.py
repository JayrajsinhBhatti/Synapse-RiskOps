"""
Inventory Service (Port 9105)
Manages warehouse stock counts, item reservations, and inventory depletion.
Supports realistic stock bottleneck fault injection.
"""

import os
import sys
import threading
from typing import Dict, Any, List
from fastapi import HTTPException

# Add parent to path for shared imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.base_service import create_microservice_app
from shared.models import InventoryCheckRequest, InventoryReserveRequest

PORT = int(os.getenv("PORT", 9105))
SERVICE_NAME = "inventory-service"

app = create_microservice_app(
    service_name=SERVICE_NAME,
    title="Synapse E-Commerce Inventory Service",
    port=PORT,
    description="Tracks warehouse stock levels and coordinates reservations",
)

# Seeded inventory catalog
STOCK_DB: Dict[str, int] = {
    "prod-1": 45,   # Synapse Neural Core Processor
    "prod-2": 80,   # Quantum Telemetry Edge Sensor
    "prod-3": 25,   # Obsidian SRE Command Terminal
    "prod-4": 120,  # Zero-Latency Fiber Transceiver
    "prod-5": 60,   # Autonomous Runbook Controller
    "prod-6": 15,   # Cryo-Cooled Cluster Node
    "prod-7": 95,   # Cybernetic Redundancy Power Supply
    "prod-8": 30,   # Multi-Cloud Gateway Router
}

RESERVATIONS: Dict[str, List[Dict[str, Any]]] = {}
_lock = threading.Lock()


@app.get("/inventory")
async def get_all_inventory():
    with _lock:
        return {"inventory": {k: v for k, v in STOCK_DB.items()}}


@app.get("/inventory/{product_id}")
async def get_product_stock(product_id: str):
    with _lock:
        if product_id not in STOCK_DB:
            raise HTTPException(status_code=404, detail=f"Product {product_id} not found in inventory")
        return {"product_id": product_id, "stock_count": STOCK_DB[product_id], "in_stock": STOCK_DB[product_id] > 0}


@app.post("/inventory/check")
async def check_availability(req: InventoryCheckRequest):
    with _lock:
        stock = STOCK_DB.get(req.product_id, 0)
        available = stock >= req.quantity
        return {
            "product_id": req.product_id,
            "requested": req.quantity,
            "current_stock": stock,
            "is_available": available,
        }


@app.post("/inventory/reserve")
async def reserve_stock(req: InventoryReserveRequest):
    """Atomically reserve inventory for an order."""
    with _lock:
        # Check all items first
        for item in req.items:
            pid = item.get("product_id")
            qty = item.get("quantity", 1)
            current = STOCK_DB.get(pid, 0)
            if current < qty:
                raise HTTPException(
                    status_code=409,
                    detail=f"Insufficient inventory for product {pid}. Available: {current}, Requested: {qty}",
                )

        # Deduct stock
        for item in req.items:
            pid = item.get("product_id")
            qty = item.get("quantity", 1)
            STOCK_DB[pid] -= qty

        RESERVATIONS[req.order_id] = req.items

    return {
        "status": "RESERVED",
        "order_id": req.order_id,
        "items_reserved_count": len(req.items),
    }


@app.post("/inventory/release/{order_id}")
async def release_stock(order_id: str):
    """Release reserved stock on canceled or failed orders."""
    with _lock:
        items = RESERVATIONS.pop(order_id, None)
        if items:
            for item in items:
                pid = item.get("product_id")
                qty = item.get("quantity", 1)
                STOCK_DB[pid] = STOCK_DB.get(pid, 0) + qty
            return {"status": "RELEASED", "order_id": order_id, "items_restored": len(items)}
    return {"status": "NOOP", "order_id": order_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)
