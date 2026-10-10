"""
API Gateway Service (Port 9101)
Unified entry point and edge router for the Live E-Commerce microservices ecosystem.
Routes all client traffic, injects correlation headers, provides operations health monitoring,
and centralizes chaos injection dispatch.
"""

import os
import sys
import time
import logging
from typing import Dict, Any, List, Optional
import httpx
from fastapi import Request, Response, HTTPException
from pydantic import BaseModel

# Add parent to path for shared imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.base_service import create_microservice_app

PORT = int(os.getenv("PORT", 9101))
SERVICE_NAME = "api-gateway"

# Downstream service URLs
SERVICES = {
    "auth-service": os.getenv("AUTH_SERVICE_URL", "http://localhost:9102"),
    "user-service": os.getenv("USER_SERVICE_URL", "http://localhost:9103"),
    "catalog-service": os.getenv("CATALOG_SERVICE_URL", "http://localhost:9104"),
    "inventory-service": os.getenv("INVENTORY_SERVICE_URL", "http://localhost:9105"),
    "cart-service": os.getenv("CART_SERVICE_URL", "http://localhost:9106"),
    "order-service": os.getenv("ORDER_SERVICE_URL", "http://localhost:9107"),
    "payment-service": os.getenv("PAYMENT_SERVICE_URL", "http://localhost:9108"),
    "notification-service": os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:9109"),
    "recommendation-service": os.getenv("RECOMMENDATION_SERVICE_URL", "http://localhost:9110"),
}

app = create_microservice_app(
    service_name=SERVICE_NAME,
    title="Synapse E-Commerce API Gateway",
    port=PORT,
    description="Edge router, request dispatcher, and operations controller for 10 microservices",
)

logger = logging.getLogger("demo.gateway")
http_client: Optional[httpx.AsyncClient] = None


@app.on_event("startup")
async def on_startup():
    global http_client
    http_client = httpx.AsyncClient(
        timeout=15.0,
        limits=httpx.Limits(max_keepalive_connections=100, max_connections=300),
    )


@app.on_event("shutdown")
async def on_shutdown():
    global http_client
    if http_client:
        await http_client.aclose()


async def _proxy_request(target_url: str, request: Request) -> Response:
    """Forward incoming request to downstream microservice with header propagation."""
    corr_id = getattr(request.state, "correlation_id", "gen-" + str(int(time.time())))
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}
    headers["X-Correlation-ID"] = corr_id

    body = await request.body()
    try:
        resp = await http_client.request(
            method=request.method,
            url=target_url,
            content=body,
            headers=headers,
            params=dict(request.query_params),
        )
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=dict(resp.headers),
            media_type=resp.headers.get("content-type"),
        )
    except httpx.RequestError as exc:
        logger.error(f"Upstream dispatch to {target_url} failed: {exc}")
        raise HTTPException(status_code=503, detail=f"Upstream service connection error: {str(exc)}")


# -------------------------------------------------------------
# Operations & Health Monitoring for all 10 Services
# -------------------------------------------------------------
@app.get("/api/operations/system-status")
async def get_all_services_status():
    """Polls all 10 microservices and returns unified topology health."""
    results = {}
    all_targets = {"api-gateway": f"http://localhost:{PORT}", **SERVICES}

    async with httpx.AsyncClient(timeout=3.0) as client:
        for name, base_url in all_targets.items():
            try:
                start = time.time()
                resp = await client.get(f"{base_url}/health")
                latency_ms = round((time.time() - start) * 1000, 1)
                if resp.status_code == 200:
                    data = resp.json()
                    results[name] = {
                        "service_name": name,
                        "url": base_url,
                        "status": data.get("status", "healthy"),
                        "latency_ms": latency_ms,
                        "has_active_fault": data.get("has_active_fault", False),
                        "active_faults": data.get("active_faults", {}),
                    }
                else:
                    results[name] = {
                        "service_name": name,
                        "url": base_url,
                        "status": "degraded",
                        "latency_ms": latency_ms,
                        "has_active_fault": True,
                        "error": resp.text,
                    }
            except Exception as e:
                results[name] = {
                    "service_name": name,
                    "url": base_url,
                    "status": "offline",
                    "latency_ms": None,
                    "has_active_fault": True,
                    "error": str(e),
                }

    healthy_count = sum(1 for s in results.values() if s["status"] == "healthy")
    return {
        "total_services": len(results),
        "healthy_count": healthy_count,
        "is_system_operational": healthy_count >= 8,
        "services": results,
    }


class ChaosDispatchPayload(BaseModel):
    service_name: str
    fault_type: str
    duration_seconds: int = 120
    intensity: float = 0.8


@app.post("/api/operations/chaos/inject")
async def dispatch_chaos(payload: ChaosDispatchPayload):
    """Dispatches a controlled chaos fault to any targeted microservice."""
    target_url = SERVICES.get(payload.service_name)
    if payload.service_name == "api-gateway":
        target_url = f"http://localhost:{PORT}"
    if not target_url:
        raise HTTPException(status_code=404, detail=f"Unknown service '{payload.service_name}'")

    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.post(
                f"{target_url}/chaos/inject",
                json={
                    "fault_type": payload.fault_type,
                    "duration_seconds": payload.duration_seconds,
                    "intensity": payload.intensity,
                },
            )
            chaos_res = resp.json()

            # Immediately stream anomaly metric vector to Synapse RiskOps
            try:
                p99_val = 35.0
                err_val = 0.0
                cpu_val = 35.0
                if payload.fault_type == "latency":
                    p99_val = 800.0 + payload.intensity * 2500.0
                elif payload.fault_type in ("error_rate", "service_outage"):
                    err_val = 100.0 if payload.fault_type == "service_outage" else (payload.intensity * 100.0)
                    p99_val = 500.0 if payload.fault_type == "service_outage" else 45.0
                elif payload.fault_type == "cpu_spike":
                    cpu_val = 50.0 + payload.intensity * 45.0

                fault_metric = {
                    "service_name": payload.service_name,
                    "cpu_usage": round(cpu_val, 1),
                    "memory_usage": 68.0,
                    "error_rate": round(err_val, 2),
                    "response_time_p99": round(p99_val, 1),
                    "network_latency_ms": round(p99_val * 0.7, 1),
                    "request_count": 280,
                    "data_mode": "connected",
                }
                await client.post("http://localhost:8080/api/v1/ingest/metrics", json=fault_metric, timeout=3.0)
            except Exception as stream_err:
                logger.debug(f"Direct metric ingest dispatch error: {stream_err}")

            return chaos_res
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Failed to reach service: {e}")


@app.post("/api/operations/chaos/clear-all")
async def clear_all_chaos():
    """Restores all 10 microservices to baseline healthy operation."""
    all_targets = {"api-gateway": f"http://localhost:{PORT}", **SERVICES}
    cleared = []
    async with httpx.AsyncClient(timeout=4.0) as client:
        for name, url in all_targets.items():
            try:
                await client.post(f"{url}/chaos/clear")
                cleared.append(name)
            except Exception:
                pass

        # Send recovery metric signals to Synapse RiskOps
        for name in cleared:
            try:
                rec_metric = {
                    "service_name": name,
                    "cpu_usage": 15.0,
                    "memory_usage": 32.0,
                    "error_rate": 0.0,
                    "response_time_p99": 22.0,
                    "network_latency_ms": 4.5,
                    "request_count": 60,
                    "data_mode": "connected",
                }
                await client.post("http://localhost:8080/api/v1/ingest/metrics", json=rec_metric, timeout=2.0)
            except Exception:
                pass

    return {"status": "cleared", "services_reset": cleared}


# -------------------------------------------------------------
# Microservice Proxy Routes
# -------------------------------------------------------------
# 1. Auth & Users
@app.api_route("/api/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_auth(path: str, request: Request):
    return await _proxy_request(f"{SERVICES['auth-service']}/auth/{path}", request)


@app.api_route("/api/users/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_users(path: str, request: Request):
    return await _proxy_request(f"{SERVICES['user-service']}/users/{path}", request)


# 2. Catalog & Products
@app.api_route("/api/products/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_products_sub(path: str, request: Request):
    return await _proxy_request(f"{SERVICES['catalog-service']}/products/{path}", request)


@app.api_route("/api/products", methods=["GET", "POST"])
async def route_products(request: Request):
    return await _proxy_request(f"{SERVICES['catalog-service']}/products", request)


# 3. Inventory
@app.api_route("/api/inventory/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_inventory(path: str, request: Request):
    return await _proxy_request(f"{SERVICES['inventory-service']}/inventory/{path}", request)


# 4. Cart
@app.api_route("/api/cart/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_cart(path: str, request: Request):
    return await _proxy_request(f"{SERVICES['cart-service']}/cart/{path}", request)


# 5. Orders
@app.api_route("/api/orders/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_orders(path: str, request: Request):
    return await _proxy_request(f"{SERVICES['order-service']}/orders/{path}", request)


# 6. Payments
@app.api_route("/api/payments/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_payments(path: str, request: Request):
    return await _proxy_request(f"{SERVICES['payment-service']}/payments/{path}", request)


# 7. Notifications
@app.api_route("/api/notifications/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_notifications(path: str, request: Request):
    return await _proxy_request(f"{SERVICES['notification-service']}/notifications/{path}", request)


# 8. Recommendations
@app.api_route("/api/recommendations/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_recommendations(path: str, request: Request):
    return await _proxy_request(f"{SERVICES['recommendation-service']}/recommendations/{path}", request)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)
