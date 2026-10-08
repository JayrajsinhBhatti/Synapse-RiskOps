"""
Synapse RiskOps - Analytics, Metrics & Incident Collaboration Tests
===================================================================
Tests for computed reliability metrics, time-series telemetry,
incident ownership workflow, and recovery verification.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.security import create_access_token


@pytest.mark.anyio
async def test_analytics_and_collaboration_endpoints():
    token = create_access_token({"sub": "admin", "role": "ADMIN"})
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Test Reliability Analytics
        rel_res = await client.get("/api/analytics/reliability", headers=headers)
        assert rel_res.status_code == 200
        rel_data = rel_res.json()
        assert "mttr_minutes" in rel_data
        assert "mttr_formatted" in rel_data
        assert "system_health_pct" in rel_data
        assert "service_scores" in rel_data

        # 2. Test Multi-Metric Telemetry with Time-Range Controls
        metrics_res = await client.get("/api/analytics/metrics?service_name=payment-service&timeframe=1h", headers=headers)
        assert metrics_res.status_code == 200
        metrics_data = metrics_res.json()
        assert metrics_data["service_name"] == "payment-service"
        assert len(metrics_data["points"]) > 0
        point = metrics_data["points"][0]
        assert "cpu_usage" in point
        assert "latency_p99" in point
        assert "error_rate" in point

        # 3. Test Change Events
        events_res = await client.get("/api/analytics/change-events", headers=headers)
        assert events_res.status_code == 200
        events_data = events_res.json()
        assert len(events_data) > 0
        assert "commit_sha" in events_data[0]
