"""
Recommendation Service (Port 9110)
Provides real-time product recommendations, trending items, and category-based suggestions.
Communicates with catalog-service to retrieve candidate items.
"""

import os
import sys
import random
from typing import List, Dict, Any
import httpx
from fastapi import HTTPException

# Add parent to path for shared imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.base_service import create_microservice_app
from shared.models import Product

PORT = int(os.getenv("PORT", 9110))
SERVICE_NAME = "recommendation-service"
CATALOG_SERVICE_URL = os.getenv("CATALOG_SERVICE_URL", "http://localhost:9104")

app = create_microservice_app(
    service_name=SERVICE_NAME,
    title="Synapse E-Commerce Recommendation Service",
    port=PORT,
    description="Machine-learning inspired product affinity and related item suggestions",
)


@app.get("/recommendations/trending", response_model=List[Product])
async def get_trending_recommendations():
    async with httpx.AsyncClient(timeout=4.0) as client:
        try:
            resp = await client.get(f"{CATALOG_SERVICE_URL}/products")
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="Failed to fetch catalog")
            products = resp.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"Catalog service error: {exc}")

    # Return top rated products
    sorted_prods = sorted(products, key=lambda p: p.get("rating", 0), reverse=True)
    return [Product(**p) for p in sorted_prods[:4]]


@app.get("/recommendations/related/{product_id}", response_model=List[Product])
async def get_related_recommendations(product_id: str):
    async with httpx.AsyncClient(timeout=4.0) as client:
        try:
            resp = await client.get(f"{CATALOG_SERVICE_URL}/products")
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="Failed to fetch catalog")
            all_prods = resp.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"Catalog service error: {exc}")

    # Find category of target product
    target = next((p for p in all_prods if p["id"] == product_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Target product not found")

    related = [p for p in all_prods if p["id"] != product_id and p.get("category") == target.get("category")]
    if not related:
        # Fallback to other items
        related = [p for p in all_prods if p["id"] != product_id]

    return [Product(**p) for p in related[:3]]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)
