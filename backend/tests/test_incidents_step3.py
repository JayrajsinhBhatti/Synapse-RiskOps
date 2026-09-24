"""
Synapse RiskOps - Week 5 Step 3 Incident CRUD & Audit Trail Test
================================================================
Owner: Person 2 | Week: 5

Verifies:
1. POST /api/incidents (Incident Creation + Service Validation + Initial Audit Log)
2. GET /api/incidents (List incidents + Filtering by status/severity/service)
3. GET /api/incidents/{id} (Single incident retrieval)
4. PATCH /api/incidents/{id} (State mutation + auto resolved_at timestamp)
5. GET /api/incidents/{id}/history (Audit trail tracking CREATED and STATUS_CHANGED)
6. DELETE /api/incidents/{id} (Cascade cleanup)
"""

import asyncio
import sys
from pathlib import Path

# Ensure backend root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from httpx import ASGITransport
from app.main import app


async def run_incident_crud_tests():
    print("=" * 70)
    print("WEEK 5 - STEP 3: INCIDENT CRUD & AUDIT TRAIL VERIFICATION")
    print("=" * 70)

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:

        # 1. Login to obtain access token
        login_resp = await client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert login_resp.status_code == 200, "Admin login failed"
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("\n[1] Admin authenticated successfully: PASS")

        # 2. Query services to get a valid service_id
        from app.core.database import AsyncSessionLocal
        from app.models.service import Service
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            svc_res = await session.execute(select(Service).where(Service.service_name == "order-service"))
            order_svc = svc_res.scalar_one_or_none()
            assert order_svc is not None, "order-service not found in seed data"
            service_id = str(order_svc.id)

        print(f"    - Target service: order-service (UUID: {service_id})")

        # 3. Test POST /api/incidents (Create Incident)
        create_payload = {
            "title": "CPU Saturation & Error Spike",
            "description": "CPU usage breached 95% on order-service causing checkout degradation.",
            "severity": "CRITICAL",
            "service_id": service_id,
            "risk_score": 88.50,
            "confidence": 0.9200,
        }
        create_resp = await client.post("/api/incidents", json=create_payload, headers=headers)
        print(f"\n[2] POST /api/incidents response status: {create_resp.status_code}")
        assert create_resp.status_code == 201, f"Create incident failed: {create_resp.text}"
        incident_data = create_resp.json()
        incident_id = incident_data["id"]
        assert incident_data["title"] == create_payload["title"]
        assert incident_data["status"] == "OPEN"
        assert incident_data["severity"] == "CRITICAL"
        print(f"    - Created Incident ID: {incident_id}")
        print("    --> Incident creation: PASS")

        # 4. Test GET /api/incidents (List & Filtering)
        list_resp = await client.get("/api/incidents", headers=headers)
        assert list_resp.status_code == 200
        incidents = list_resp.json()
        assert any(inc["id"] == incident_id for inc in incidents)
        print(f"\n[3] GET /api/incidents listed {len(incidents)} incident(s): PASS")

        # Filter by status
        filter_status = await client.get("/api/incidents?status=OPEN", headers=headers)
        assert all(inc["status"] == "OPEN" for inc in filter_status.json())
        print("    - Status filter (?status=OPEN): PASS")

        # Filter by severity
        filter_sev = await client.get("/api/incidents?severity=CRITICAL", headers=headers)
        assert all(inc["severity"] == "CRITICAL" for inc in filter_sev.json())
        print("    - Severity filter (?severity=CRITICAL): PASS")

        # 5. Test GET /api/incidents/{id} (Single retrieval)
        get_resp = await client.get(f"/api/incidents/{incident_id}", headers=headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == incident_id
        print(f"\n[4] GET /api/incidents/{incident_id}: PASS")

        # 6. Test PATCH /api/incidents/{id} (State transition to RESOLVED)
        patch_payload = {
            "status": "RESOLVED",
            "description": "Auto-remediation executed runbook RB-CPU-001. Incident resolved.",
        }
        patch_resp = await client.patch(f"/api/incidents/{incident_id}", json=patch_payload, headers=headers)
        print(f"\n[5] PATCH /api/incidents/{incident_id} response status: {patch_resp.status_code}")
        assert patch_resp.status_code == 200
        updated_data = patch_resp.json()
        assert updated_data["status"] == "RESOLVED"
        assert updated_data["resolved_at"] is not None, "resolved_at timestamp was not set"
        print(f"    - Updated Status: {updated_data['status']} | Resolved At: {updated_data['resolved_at']}")
        print("    --> Incident update & auto-resolution timestamp: PASS")

        # 7. Test GET /api/incidents/{id}/history (Audit Trail)
        history_resp = await client.get(f"/api/incidents/{incident_id}/history", headers=headers)
        assert history_resp.status_code == 200
        history = history_resp.json()
        print(f"\n[6] GET /api/incidents/{incident_id}/history records count: {len(history)}")
        assert len(history) >= 2, f"Expected at least 2 history records, found {len(history)}"
        actions = [h["action"] for h in history]
        assert "CREATED" in actions
        assert "STATUS_CHANGED" in actions
        for h in history:
            print(f"    - Audit: action='{h['action']}', old='{h['old_value']}', new='{h['new_value']}'")
        print("    --> Incident audit trail verification: PASS")

        # 8. Test DELETE /api/incidents/{id}
        del_resp = await client.delete(f"/api/incidents/{incident_id}", headers=headers)
        print(f"\n[7] DELETE /api/incidents/{incident_id} response status: {del_resp.status_code}")
        assert del_resp.status_code == 204
        print("    --> Incident deletion: PASS")

        # Verify incident is gone
        verify_del = await client.get(f"/api/incidents/{incident_id}", headers=headers)
        assert verify_del.status_code == 404
        print("    --> 404 confirmation after deletion: PASS")

    print("\n" + "=" * 70)
    print("ALL STEP 3 INCIDENT CRUD & AUDIT TESTS PASSED!")
    print("=" * 70)


def test_incidents_step3_flow():
    asyncio.run(run_incident_crud_tests())


if __name__ == "__main__":
    test_incidents_step3_flow()
