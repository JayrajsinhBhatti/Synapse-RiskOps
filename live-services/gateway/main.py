"""
API Gateway (synapse-live-gateway)
Port 9001
Single entry point for client traffic. Proxies to auth-service, order-service,
inventory-service, and notification-svc, measuring upstream latencies and error rates.
"""

import os
import time
import logging
from typing import Optional, Dict, Any
from fastapi import Request, Response, HTTPException
import httpx
from prometheus_client import Histogram, Gauge

from shared.base_service import create_base_app

logger = logging.getLogger("gateway")

SERVICE_NAME = os.getenv("SERVICE_NAME", "api-gateway")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://live-auth:9002")
ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://live-orders:9003")
INVENTORY_SERVICE_URL = os.getenv("INVENTORY_SERVICE_URL", "http://live-inventory:9005")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://live-notifications:9006")

# Gateway specific metrics
upstream_duration = Histogram(
    "gateway_upstream_duration_seconds",
    "Upstream response latency",
    ["target"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)
circuit_breaker_state = Gauge(
    "gateway_circuit_breaker_state",
    "Circuit breaker status (0=CLOSED, 1=HALF_OPEN, 2=OPEN)",
    ["target"]
)

app = create_base_app(
    service_name=SERVICE_NAME,
    title="Synapse Live API Gateway",
    description="Edge proxy and service router"
)

http_client: Optional[httpx.AsyncClient] = None


@app.on_event("startup")
async def startup_resources():
    global http_client
    http_client = httpx.AsyncClient(
        timeout=15.0,
        limits=httpx.Limits(max_keepalive_connections=50, max_connections=200)
    )
    for target in ["auth", "orders", "inventory", "notifications"]:
        circuit_breaker_state.labels(target=target).set(0)


@app.on_event("shutdown")
async def shutdown_resources():
    global http_client
    if http_client:
        await http_client.aclose()


async def _proxy_request(target: str, url: str, method: str, content: bytes = None, headers: dict = None) -> Response:
    start_time = time.time()
    try:
        req_headers = {k: v for k, v in (headers or {}).items() if k.lower() not in ("host", "content-length")}
        resp = await http_client.request(
            method=method,
            url=url,
            content=content,
            headers=req_headers
        )
        duration = time.time() - start_time
        upstream_duration.labels(target=target).observe(duration)
        return Response(content=resp.content, status_code=resp.status_code, media_type=resp.headers.get("content-type"))
    except httpx.RequestError as exc:
        duration = time.time() - start_time
        upstream_duration.labels(target=target).observe(duration)
        logger.error(f"Upstream request to {target} failed: {exc}")
        raise HTTPException(status_code=503, detail=f"Upstream {target} error: {str(exc)}")


# Proxy Routes
@app.post("/auth/verify")
async def proxy_auth_verify(request: Request):
    body = await request.body()
    return await _proxy_request("auth", f"{AUTH_SERVICE_URL}/verify", "POST", body, dict(request.headers))


@app.post("/auth/login")
async def proxy_auth_login(request: Request):
    body = await request.body()
    return await _proxy_request("auth", f"{AUTH_SERVICE_URL}/login", "POST", body, dict(request.headers))


@app.get("/orders")
async def proxy_get_orders(request: Request):
    return await _proxy_request("orders", f"{ORDER_SERVICE_URL}/orders", "GET", None, dict(request.headers))


@app.post("/orders")
async def proxy_post_orders(request: Request):
    body = await request.body()
    return await _proxy_request("orders", f"{ORDER_SERVICE_URL}/orders", "POST", body, dict(request.headers))


@app.get("/orders/{order_id}")
async def proxy_get_order_detail(order_id: str, request: Request):
    return await _proxy_request("orders", f"{ORDER_SERVICE_URL}/orders/{order_id}", "GET", None, dict(request.headers))


@app.get("/inventory")
async def proxy_get_inventory(request: Request):
    return await _proxy_request("inventory", f"{INVENTORY_SERVICE_URL}/inventory", "GET", None, dict(request.headers))


@app.get("/inventory/{sku}")
async def proxy_get_inventory_sku(sku: str, request: Request):
    return await _proxy_request("inventory", f"{INVENTORY_SERVICE_URL}/inventory/{sku}", "GET", None, dict(request.headers))


@app.get("/notifications")
async def proxy_get_notifications(request: Request):
    return await _proxy_request("notifications", f"{NOTIFICATION_SERVICE_URL}/notifications", "GET", None, dict(request.headers))


@app.get("/health/deep")
async def deep_health_check():
    targets = {
        "auth": f"{AUTH_SERVICE_URL}/health",
        "orders": f"{ORDER_SERVICE_URL}/health",
        "inventory": f"{INVENTORY_SERVICE_URL}/health",
        "notifications": f"{NOTIFICATION_SERVICE_URL}/health",
    }
    status = {}
    for name, url in targets.items():
        try:
            res = await http_client.get(url, timeout=2.0)
            status[name] = "healthy" if res.status_code == 200 else f"unhealthy ({res.status_code})"
        except Exception as e:
            status[name] = f"down ({str(e)})"
    return {"gateway": "healthy", "upstreams": status}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9001)
