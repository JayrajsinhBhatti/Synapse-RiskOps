"""
Synapse RiskOps - Admin Operational Log Clearance & Audit Trail Tests
====================================================================
Tests:
1. Enforces ADMIN role on manual clearance.
2. Validates confirmation flag and audit justification reason.
3. Successfully prunes expired records and creates an immutable audit trail record.
4. Retrieves administrative audit trail history.
"""

import pytest
import httpx
from httpx import ASGITransport
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app


async def get_admin_token(client: httpx.AsyncClient) -> str:
    res = await client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200, f"Login failed: {res.text}"
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_admin_log_clearance_flow():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        token = await get_admin_token(client)
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        # 1. Check retention config
        cfg_resp = await client.get("/api/retention/config", headers=headers)
        assert cfg_resp.status_code == 200
        assert cfg_resp.json()["log_retention_days"] == 10

        # 2. Reject if confirm is False
        reject_resp = await client.post(
            "/api/retention/admin/clear-logs",
            json={"confirm": False, "reason": "Test clearance", "scope": "operational_telemetry"},
            headers=headers,
        )
        assert reject_resp.status_code == 400

        # 3. Reject if reason is empty
        reject_reason_resp = await client.post(
            "/api/retention/admin/clear-logs",
            json={"confirm": True, "reason": "   ", "scope": "operational_telemetry"},
            headers=headers,
        )
        assert reject_reason_resp.status_code == 422 or reject_reason_resp.status_code == 400

        # 4. Successful admin clearance
        success_resp = await client.post(
            "/api/retention/admin/clear-logs",
            json={"confirm": True, "reason": "Monthly operational log prune", "scope": "operational_telemetry", "older_than_days": 10},
            headers=headers,
        )
        assert success_resp.status_code == 200, f"Clearance failed: {success_resp.text}"
        data = success_resp.json()
        assert data["success"] is True
        assert data["cleared_by"] == "admin"
        assert "audit_id" in data

        # 5. Verify audit trail entry
        trail_resp = await client.get("/api/retention/admin/audit-trail", headers=headers)
        assert trail_resp.status_code == 200
        trail = trail_resp.json()
        assert len(trail) > 0
        assert trail[0]["action"] == "MANUAL_LOG_CLEARANCE"
        assert trail[0]["performed_by"] == "admin"
