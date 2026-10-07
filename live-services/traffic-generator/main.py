"""
Traffic Generator for Synapse Live Microservices Environment.
Continuously sends realistic HTTP requests through the API Gateway,
exercising the full dependency graph with realistic traffic patterns.
"""

import os
import sys
import time
import math
import random
import logging
import asyncio
from typing import List
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [TrafficGen] %(message)s")
logger = logging.getLogger("traffic_generator")

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://live-gateway:9001").rstrip("/")
BASE_RPS = float(os.getenv("REQUESTS_PER_SECOND", "10"))
DIURNAL_ENABLED = os.getenv("DIURNAL_ENABLED", "true").lower() == "true"

SKUS = [
    "SKU-LAPTOP-01",
    "SKU-PHONE-02",
    "SKU-HEADPHONES-03",
    "SKU-KEYBOARD-04",
    "SKU-MONITOR-05"
]

USERS = ["user_test", "alice", "bob"]


async def wait_for_gateway(client: httpx.AsyncClient):
    """Wait until API Gateway is healthy."""
    logger.info(f"Waiting for API Gateway at {GATEWAY_URL}/health...")
    for i in range(60):
        try:
            res = await client.get(f"{GATEWAY_URL}/health", timeout=3.0)
            if res.status_code == 200:
                logger.info("API Gateway is online and ready!")
                return True
        except Exception:
            pass
        await asyncio.sleep(2)
    logger.error("API Gateway did not become healthy in time.")
    return False


async def run_traffic():
    limits = httpx.Limits(max_keepalive_connections=50, max_connections=100)
    async with httpx.AsyncClient(timeout=10.0, limits=limits) as client:
        ready = await wait_for_gateway(client)
        if not ready:
            logger.warning("Proceeding anyway to attempt traffic generation...")

        logger.info(f"Starting continuous traffic generation at base {BASE_RPS} RPS...")

        # Stats tracking
        window_requests = 0
        window_errors = 0
        window_latencies: List[float] = []
        last_report_time = time.time()

        while True:
            # Diurnal cycle simulation: multiplier varies between 0.7 and 1.3
            if DIURNAL_ENABLED:
                hour_of_day = (time.time() / 3600.0) % 24.0
                multiplier = 1.0 + 0.3 * math.sin((hour_of_day - 6.0) * math.pi / 12.0)
            else:
                multiplier = 1.0

            current_rps = max(1.0, BASE_RPS * multiplier)
            sleep_interval = 1.0 / current_rps

            # Add random Gaussian noise to delay
            jitter = random.gauss(0, sleep_interval * 0.2)
            actual_sleep = max(0.01, sleep_interval + jitter)

            # Choose request type
            # 40% GET /orders, 20% POST /orders, 15% POST /auth/verify, 15% GET /inventory, 10% GET /notifications
            roll = random.random()
            req_start = time.time()
            success = False

            try:
                if roll < 0.40:
                    res = await client.get(f"{GATEWAY_URL}/orders")
                    success = res.status_code < 500
                elif roll < 0.60:
                    sku = random.choice(SKUS)
                    user = random.choice(USERS)
                    res = await client.post(
                        f"{GATEWAY_URL}/orders",
                        json={"user_id": user, "sku": sku, "quantity": random.randint(1, 3)}
                    )
                    success = res.status_code < 500
                elif roll < 0.75:
                    user = random.choice(USERS)
                    res = await client.post(
                        f"{GATEWAY_URL}/auth/verify",
                        json={"username": user, "token": f"token-{user}-demo"}
                    )
                    success = res.status_code < 500
                elif roll < 0.90:
                    sku = random.choice(SKUS)
                    res = await client.get(f"{GATEWAY_URL}/inventory/{sku}")
                    success = res.status_code < 500
                else:
                    res = await client.get(f"{GATEWAY_URL}/notifications")
                    success = res.status_code < 500

                lat = (time.time() - req_start) * 1000.0
                window_latencies.append(lat)
                if success:
                    window_requests += 1
                else:
                    window_requests += 1
                    window_errors += 1

            except Exception as e:
                window_requests += 1
                window_errors += 1
                lat = (time.time() - req_start) * 1000.0
                window_latencies.append(lat)

            # Log periodic stats every 15 seconds
            now = time.time()
            if now - last_report_time >= 15.0:
                elapsed = now - last_report_time
                rps = window_requests / elapsed if elapsed > 0 else 0
                err_pct = (window_errors / window_requests * 100.0) if window_requests > 0 else 0
                avg_lat = sum(window_latencies) / len(window_latencies) if window_latencies else 0.0
                p95_lat = sorted(window_latencies)[int(len(window_latencies) * 0.95)] if window_latencies else 0.0

                logger.info(
                    f"Traffic Flow: {window_requests} reqs in {elapsed:.1f}s | "
                    f"Throughput: {rps:.1f} req/s | Errors: {window_errors} ({err_pct:.1f}%) | "
                    f"Avg Latency: {avg_lat:.1f}ms | P95: {p95_lat:.1f}ms"
                )

                window_requests = 0
                window_errors = 0
                window_latencies.clear()
                last_report_time = now

            await asyncio.sleep(actual_sleep)


if __name__ == "__main__":
    try:
        asyncio.run(run_traffic())
    except KeyboardInterrupt:
        logger.info("Traffic generator stopped.")
