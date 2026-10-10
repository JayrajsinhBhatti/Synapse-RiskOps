"""
Traffic Generator & Real-time Telemetry Streamer.
Continuously runs realistic user transactions across the 10 microservices:
1. Browses product catalog & categories
2. Retrieves recommendations
3. Adds items to cart
4. Completes full checkout orders (inventory reservation + payment + notification)
5. Extracts live operational metrics from all 10 microservices
6. Streams live metric vectors directly into Synapse RiskOps Ingestion API (http://localhost:8080/api/v1/ingest/metrics)
"""

import time
import os
import random
import logging
import asyncio
import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [TrafficGenerator] %(message)s",
)
logger = logging.getLogger("demo.traffic")

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:9101/api")
SYNAPSE_BACKEND_URL = os.getenv("SYNAPSE_BACKEND_URL", "http://localhost:8080")

# 10 Microservices ports for direct metric extraction
MICROSERVICES_PORTS = {
    "api-gateway": 9101,
    "auth-service": 9102,
    "user-service": 9103,
    "catalog-service": 9104,
    "inventory-service": 9105,
    "cart-service": 9106,
    "order-service": 9107,
    "payment-service": 9108,
    "notification-service": 9109,
    "recommendation-service": 9110,
}

SAMPLE_USERS = ["usr-admin", "usr-john"]


async def simulate_user_session(client: httpx.AsyncClient):
    """Executes a realistic user journey through the microservices."""
    user_id = random.choice(SAMPLE_USERS)

    try:
        # 1. Browse catalog
        resp = await client.get(f"{GATEWAY_URL}/products")
        if resp.status_code != 200:
            return
        products = resp.json()
        if not products:
            return

        # 2. Browse recommendations
        await client.get(f"{GATEWAY_URL}/recommendations/trending")

        # 3. Add 1-2 items to cart
        chosen = random.sample(products, k=min(2, len(products)))
        for prod in chosen:
            await client.post(
                f"{GATEWAY_URL}/cart/add",
                json={"user_id": user_id, "product_id": prod["id"], "quantity": random.randint(1, 2)},
            )

        # 4. 60% chance to execute full checkout
        if random.random() < 0.6:
            checkout_payload = {
                "user_id": user_id,
                "payment_method": random.choice(["credit_card", "upi", "netbanking"]),
                "shipping_address": f"{random.randint(100, 999)} Enterprise Way, CA",
            }
            c_resp = await client.post(f"{GATEWAY_URL}/orders/checkout", json=checkout_payload)
            if c_resp.status_code == 200:
                logger.info(f"🛒 Order #{c_resp.json().get('order_id')} placed successfully!")
            else:
                logger.warning(f"⚠️ Checkout returned status {c_resp.status_code}: {c_resp.text}")

    except Exception as e:
        logger.debug(f"User session transient exception: {e}")


async def harvest_and_stream_telemetry(client: httpx.AsyncClient):
    """Polls each microservice's /metrics & /health and posts to Synapse RiskOps."""
    for service_name, port in MICROSERVICES_PORTS.items():
        base_url = f"http://localhost:{port}"
        try:
            # Measure direct probe latency
            start = time.time()
            h_resp = await client.get(f"{base_url}/health", timeout=2.0)
            latency_ms = (time.time() - start) * 1000.0

            # Query health & active chaos status
            h_data = {}
            if h_resp.status_code == 200:
                try:
                    h_data = h_resp.json()
                except Exception:
                    pass

            # Query raw prometheus text
            m_resp = await client.get(f"{base_url}/metrics", timeout=2.0)
            metrics_text = m_resp.text if m_resp.status_code == 200 else ""

            # Parse key Prometheus gauges
            cpu = 20.0
            mem = 35.0
            error_rate = 0.0
            p99 = max(15.0, latency_ms)
            req_count = 10
            active_conns = 4

            for line in metrics_text.splitlines():
                if line.startswith("app_cpu_usage{"):
                    cpu = float(line.split()[-1])
                elif line.startswith("app_memory_usage{"):
                    mem = float(line.split()[-1])
                elif line.startswith("app_error_rate{"):
                    error_rate = float(line.split()[-1])
                elif line.startswith("app_active_connections{"):
                    active_conns = int(float(line.split()[-1]))
                elif line.startswith("http_requests_total{"):
                    req_count += 1

            # Explicitly reflect active chaos injection faults
            if h_data.get("has_active_fault"):
                active_faults = h_data.get("active_faults", {})
                if "latency" in active_faults:
                    lat_intensity = float(active_faults["latency"].get("intensity", 0.8))
                    p99 = max(p99, 800.0 + lat_intensity * 2500.0)
                    latency_ms = max(latency_ms, p99 * 0.8)
                if "error_rate" in active_faults:
                    err_intensity = float(active_faults["error_rate"].get("intensity", 0.85))
                    error_rate = max(error_rate, err_intensity * 100.0)
                if "cpu_spike" in active_faults:
                    cpu_intensity = float(active_faults["cpu_spike"].get("intensity", 0.9))
                    cpu = max(cpu, 50.0 + cpu_intensity * 45.0)
                if "service_outage" in active_faults:
                    error_rate = 100.0
                    p99 = max(p99, 5000.0)
                    latency_ms = max(latency_ms, 5000.0)


            # Prepare standardized telemetry payload for Synapse
            payload = {
                "service_name": service_name,
                "cpu_usage": round(cpu, 1),
                "memory_usage": round(mem, 1),
                "error_rate": round(error_rate, 2),
                "response_time_p99": round(p99, 1),
                "network_latency_ms": round(latency_ms, 1),
                "request_count": req_count,
                "data_mode": "connected",
                "extra_metrics": {
                    "active_connections": active_conns,
                    "disk_io": round(random.uniform(5.0, 25.0), 1),
                    "gc_pause_ms": round(random.uniform(0.5, 4.0), 2),
                    "thread_count": random.randint(12, 28),
                },
            }

            # Ingest into Synapse RiskOps Core Backend
            ingest_resp = await client.post(
                f"{SYNAPSE_BACKEND_URL}/api/v1/ingest/metrics",
                json=payload,
                timeout=3.0,
            )
            if ingest_resp.status_code in (200, 201):
                logger.debug(f"📡 Telemetry streamed for {service_name} (CPU: {cpu}%, P99: {p99:.1f}ms, Err: {error_rate}%)")

        except Exception as e:
            logger.debug(f"Telemetry ingest error for {service_name}: {e}")


async def check_synapse_connected(client: httpx.AsyncClient) -> bool:
    """Check if Synapse RiskOps is in connected mode before streaming operational telemetry."""
    try:
        resp = await client.get(f"{SYNAPSE_BACKEND_URL}/api/system/mode", timeout=3.0)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("mode") == "connected" and bool(data.get("external_app_connected", False))
    except Exception:
        pass
    return False


async def main_loop():
    logger.info("Starting Live E-Commerce Traffic Generator & Telemetry Streamer...")
    async with httpx.AsyncClient(timeout=10.0) as client:
        last_log_state = None
        while True:
            is_connected = await check_synapse_connected(client)

            # Also check if any microservice has an active fault injected
            has_any_active_fault = False
            try:
                h_res = await client.get(f"{GATEWAY_URL}/operations/system-status", timeout=2.0)
                if h_res.status_code == 200:
                    h_data = h_res.json()
                    for svc in h_data.get("services", []):
                        if svc.get("has_active_fault"):
                            has_any_active_fault = True
                            break
            except Exception:
                pass

            if not is_connected and not has_any_active_fault:
                if last_log_state != "disconnected":
                    logger.info("Synapse RiskOps is in DEMO mode (External Website NOT connected). Pausing baseline stream until Admin connects the application.")
                    last_log_state = "disconnected"
                await asyncio.sleep(3)
                continue

            if last_log_state != "connected":
                logger.info("Live connection / fault streaming ACTIVE! Streaming operational telemetry for 10 microservices to Synapse RiskOps...")
                last_log_state = "connected"

            # Generate 2-4 concurrent user actions
            tasks = [simulate_user_session(client) for _ in range(random.randint(1, 3))]
            await asyncio.gather(*tasks, return_exceptions=True)

            # Harvest & stream operational metrics to Synapse RiskOps
            await harvest_and_stream_telemetry(client)

            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main_loop())

