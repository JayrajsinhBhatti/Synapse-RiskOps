"""
Product Catalog Service (Port 9104)
Maintains product information, categories, and descriptions.
Enriches catalog entries by querying inventory-service for real-time stock levels.
"""

import os
import sys
from typing import List, Optional, Dict
import httpx
from fastapi import HTTPException, Query

# Add parent to path for shared imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.base_service import create_microservice_app
from shared.models import Product

PORT = int(os.getenv("PORT", 9104))
SERVICE_NAME = "catalog-service"
INVENTORY_SERVICE_URL = os.getenv("INVENTORY_SERVICE_URL", "http://localhost:9105")

app = create_microservice_app(
    service_name=SERVICE_NAME,
    title="Synapse E-Commerce Catalog Service",
    port=PORT,
    description="Product listings, categories, and inventory-enriched details",
)

PRODUCTS_STATIC = [
    {
        "id": "prod-1",
        "name": "Synapse Neural Core Processor",
        "category": "Processors",
        "price": 899.99,
        "description": "Next-gen AI edge inference chip with 48 TOPS neural acceleration and sub-millisecond tensor processing.",
        "image_url": "https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?w=500&auto=format&fit=crop&q=60",
        "rating": 4.9,
    },
    {
        "id": "prod-2",
        "name": "Quantum Telemetry Edge Sensor",
        "category": "Sensors",
        "price": 249.50,
        "description": "Precision microsecond telemetry capture node for high-frequency infrastructure telemetry and distributed metrics.",
        "image_url": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=500&auto=format&fit=crop&q=60",
        "rating": 4.7,
    },
    {
        "id": "prod-3",
        "name": "Obsidian SRE Command Terminal",
        "category": "Hardware",
        "price": 1499.00,
        "description": "Industrial grade cybernetic mission control console with tactile mechanical switches and triple 4K OLED output.",
        "image_url": "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=500&auto=format&fit=crop&q=60",
        "rating": 5.0,
    },
    {
        "id": "prod-4",
        "name": "Zero-Latency Fiber Transceiver",
        "category": "Networking",
        "price": 129.99,
        "description": "Ultra low jitter 100Gbps QSFP28 optical module designed for mission-critical trading and telemetry backbones.",
        "image_url": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=500&auto=format&fit=crop&q=60",
        "rating": 4.6,
    },
    {
        "id": "prod-5",
        "name": "Autonomous Runbook Controller",
        "category": "Controllers",
        "price": 649.00,
        "description": "Hardware-enforced execution gateway for automated Ansible and Kubernetes self-healing playbooks.",
        "image_url": "https://images.unsplash.com/photo-1517430816045-df4b7de01ddf?w=500&auto=format&fit=crop&q=60",
        "rating": 4.8,
    },
    {
        "id": "prod-6",
        "name": "Cryo-Cooled Cluster Node",
        "category": "Servers",
        "price": 3299.00,
        "description": "Liquid nitrogen chilled 2U server blade providing zero thermal throttling during sustained chaos and peak loads.",
        "image_url": "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=500&auto=format&fit=crop&q=60",
        "rating": 4.9,
    },
    {
        "id": "prod-7",
        "name": "Cybernetic Redundancy Power Supply",
        "category": "Hardware",
        "price": 379.00,
        "description": "Hot-swappable dual 1600W platinum power unit with active telemetry and battery backup buffer.",
        "image_url": "https://images.unsplash.com/photo-1563770660941-20978e870e26?w=500&auto=format&fit=crop&q=60",
        "rating": 4.5,
    },
    {
        "id": "prod-8",
        "name": "Multi-Cloud Gateway Router",
        "category": "Networking",
        "price": 799.00,
        "description": "Hardware SD-WAN router featuring BGP failover, active mesh tunnels, and wire-speed packet inspection.",
        "image_url": "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=500&auto=format&fit=crop&q=60",
        "rating": 4.8,
    },
]


async def _enrich_with_inventory(product: dict) -> Product:
    stock_count = 50
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{INVENTORY_SERVICE_URL}/inventory/{product['id']}")
            if resp.status_code == 200:
                stock_count = resp.json().get("stock_count", 50)
    except Exception:
        pass
    return Product(**product, stock_count=stock_count)


@app.get("/products", response_model=List[Product])
async def list_products(
    category: Optional[str] = None,
    q: Optional[str] = None,
):
    results = PRODUCTS_STATIC
    if category and category.lower() != "all":
        results = [p for p in results if p["category"].lower() == category.lower()]
    if q:
        query = q.lower()
        results = [p for p in results if query in p["name"].lower() or query in p["description"].lower()]

    # Fetch live stock from inventory-service for each product
    enriched = []
    for p in results:
        enriched.append(await _enrich_with_inventory(p))
    return enriched


@app.get("/products/categories")
async def get_categories():
    categories = sorted(list({p["category"] for p in PRODUCTS_STATIC}))
    return {"categories": ["All"] + categories}


@app.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: str):
    for p in PRODUCTS_STATIC:
        if p["id"] == product_id:
            return await _enrich_with_inventory(p)
    raise HTTPException(status_code=404, detail="Product not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)
