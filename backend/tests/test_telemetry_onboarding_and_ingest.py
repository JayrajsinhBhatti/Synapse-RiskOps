"""
Synapse RiskOps - Telemetry Onboarding & Ingestion Integration Tests
===================================================================
Tests for:
1. Universal Metric Ingest (POST /api/v1/ingest/metrics) with auto-registration and anomaly routing.
2. Prometheus Historical Backfill (POST /api/system/backfill) for cold-start resolution.
3. Enhanced Connection Verification probe with auth and metric arrival status counters.
4. Batch Service Review & Configuration (POST /api/services/batch-configure).
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4
import httpx
from httpx import ASGITransport

# Ensure backend root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import AsyncSessionLocal
from app.models.service import Service
from app.main import app


async def get_real_auth_headers(client: httpx.AsyncClient) -> dict:
    login_resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


async def _async_test_universal_metric_ingest_flow():
    """Test POST /api/v1/ingest/metrics for normal and anomalous metric payloads."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Normal telemetry payload for an existing or new service
        normal_payload = {
            "service_name": "test-order-service",
            "cpu_usage": 35.2,
            "memory_usage": 52.0,
            "error_rate": 0.4,
            "response_time_p99": 45.0,
            "request_count": 820.0,
            "network_latency": 12.0,
        }

        resp = await client.post("/api/v1/ingest/metrics", json=normal_payload)
        assert resp.status_code == 201, f"Ingest failed: {resp.text}"
        data = resp.json()
        assert data["status"] == "ingested"
        assert data["service_name"] == "test-order-service"
        assert data["evaluated_anomaly"] is False

        # 2. Anomalous telemetry payload triggering automated incident pipeline
        anomalous_payload = {
            "service_name": "test-order-service",
            "cpu_usage": 91.5,
            "memory_usage": 94.2,
            "error_rate": 14.8,  # > 5.0% threshold
            "response_time_p99": 280.0,  # > 150ms threshold
            "request_count": 2400.0,
            "network_latency": 88.0,
        }

        resp_anom = await client.post("/api/v1/ingest/metrics", json=anomalous_payload)
        assert resp_anom.status_code == 201
        data_anom = resp_anom.json()
        assert data_anom["status"] == "ingested"
        assert data_anom["evaluated_anomaly"] is True


async def _async_test_prometheus_backfill():
    """Test POST /api/system/backfill for cold-start 24h and 48h data baseline resolution."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await get_real_auth_headers(client)

        # 24 hour backfill request
        backfill_24h = {
            "prometheus_url": "http://localhost:9090",
            "hours": 24,
            "auth_type": "none",
        }
        res_24 = await client.post("/api/system/backfill", json=backfill_24h, headers=headers)
        assert res_24.status_code == 200, f"Backfill 24h failed: {res_24.text}"
        data_24 = res_24.json()
        assert data_24["status"] == "backfill_completed"
        assert data_24["hours_backfilled"] == 24
        assert data_24["data_points_loaded"] > 0
        assert data_24["services_backfilled"] > 0

        # 48 hour backfill request
        backfill_48h = {
            "prometheus_url": "http://localhost:9090",
            "hours": 48,
            "auth_type": "bearer",
            "auth_token": "test-token-123",
        }
        res_48 = await client.post("/api/system/backfill", json=backfill_48h, headers=headers)
        assert res_48.status_code == 200
        data_48 = res_48.json()
        assert data_48["hours_backfilled"] == 48
        assert data_48["data_points_loaded"] >= data_24["data_points_loaded"]


async def _async_test_connection_verification_with_auth_and_service_metrics():
    """Test POST /api/system/verify-connection returns per-service metric indicators and ML readiness."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await get_real_auth_headers(client)

        verify_payload = {
            "connection_type": "prometheus_bridge",
            "endpoint_url": "http://localhost:9090",
            "auth_type": "bearer",
            "auth_token": "prom_token_xyz",
            "backfill_hours": 24,
            "expected_services": ["payment-service", "order-service", "auth-service"],
        }
        res = await client.post("/api/system/verify-connection", json=verify_payload, headers=headers)
        assert res.status_code == 200, f"Verify failed: {res.text}"
        data = res.json()
        assert data["verified"] is True
        assert "service_metric_statuses" in data
        assert len(data["service_metric_statuses"]) > 0
        assert "ml_readiness_pct" in data
        assert data["ml_readiness_pct"] > 50


async def _async_test_batch_service_configure_flow():
    """Test POST /api/services/batch-configure to rename, exclude, and set criticality."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await get_real_auth_headers(client)

        # 1. Fetch current services
        svc_resp = await client.get("/api/services", headers=headers)
        assert svc_resp.status_code == 200
        services = svc_resp.json()
        assert len(services) > 0, "Expected at least 1 service in database"

        target_svc = services[0]
        svc_id = target_svc["id"]
        unique_name = f"renamed-gateway-{uuid4().hex[:6]}"

        # 2. Configure service via batch-configure
        configure_payload = {
            "services": [
                {
                    "service_id": svc_id,
                    "service_name": unique_name,
                    "criticality": "CRITICAL",
                    "is_active": True,
                }
            ]
        }

        res = await client.post("/api/services/batch-configure", json=configure_payload, headers=headers)
        assert res.status_code == 200, f"Batch configure failed: {res.text}"
        conf_data = res.json()
        assert isinstance(conf_data, list)
        assert len(conf_data) == 1
        assert conf_data[0]["service_name"] == unique_name
        assert conf_data[0]["criticality"] == "CRITICAL"

        # 3. Verify changes were applied
        updated_resp = await client.get("/api/services", headers=headers)
        updated_services = updated_resp.json()
        matched = next((s for s in updated_services if s["id"] == svc_id), None)
        assert matched is not None
        assert matched["service_name"] == unique_name
        assert matched["criticality"] == "CRITICAL"


def test_universal_metric_ingest_flow():
    asyncio.run(_async_test_universal_metric_ingest_flow())


def test_prometheus_backfill():
    asyncio.run(_async_test_prometheus_backfill())


def test_connection_verification_with_auth_and_service_metrics():
    asyncio.run(_async_test_connection_verification_with_auth_and_service_metrics())


def test_batch_service_configure_flow():
    asyncio.run(_async_test_batch_service_configure_flow())
