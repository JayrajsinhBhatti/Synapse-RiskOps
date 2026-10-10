"""
Synapse RiskOps - Retention & Deletion Integration Tests
========================================================
Tests:
1. Retention settings retrieval and update (1d, 7d, 30d, 90d, all).
2. Timestamp-based retention cutoff: verifies that records older than 7 days
   are pruned, while records within the last 7 days are strictly preserved.
3. Individual record deletion for incidents, audit history, and risk assessments.
4. Safe bulk deletion with required confirmation flag (confirm_all=True).
5. Role-based authorization enforcement.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4
import httpx
from httpx import ASGITransport
from sqlalchemy import select, delete

# Ensure backend root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import AsyncSessionLocal
from app.models.incident import Incident, IncidentHistory
from app.models.risk_assessment import RiskAssessment
from app.models.retention import RetentionPolicy
from app.models.service import Service
from app.models.user import User
from app.core.security import create_access_token
from app.main import app


async def get_real_auth_headers(client: httpx.AsyncClient) -> dict:
    login_resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


async def _async_test_retention_settings():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await get_real_auth_headers(client)
        # GET settings
        resp = await client.get("/api/retention/settings", headers=headers)
        assert resp.status_code == 200, f"GET settings failed: {resp.text}"
        data = resp.json()
        assert "policies" in data
        assert len(data["policies"]) >= 2
        modules = [p["module"] for p in data["policies"]]
        assert "incidents" in modules
        assert "risk_assessments" in modules

        # PUT settings to 7d
        update_resp = await client.put(
            "/api/retention/settings",
            json={"module": "incidents", "retention_period": "7d", "auto_purge_enabled": True},
            headers=headers,
        )
        assert update_resp.status_code == 200, f"PUT settings failed: {update_resp.text}"
        up_data = update_resp.json()
        assert up_data["retention_period"] == "7d"
        assert up_data["cutoff_timestamp"] is not None

        # Reset back to all
        reset_resp = await client.put(
            "/api/retention/settings",
            json={"module": "incidents", "retention_period": "all"},
            headers=headers,
        )
        assert reset_resp.status_code == 200


async def _async_test_timestamp_prune():
    from app.api.retention import execute_timestamp_purge

    now = datetime.now(timezone.utc)
    ts_2_days_ago = now - timedelta(days=2)
    ts_5_days_ago = now - timedelta(days=5)
    ts_8_days_ago = now - timedelta(days=8)
    ts_30_days_ago = now - timedelta(days=30)

    async with AsyncSessionLocal() as session:
        svc_res = await session.execute(select(Service).limit(1))
        svc = svc_res.scalar_one()

        inc_recent_1 = Incident(
            id=uuid4(),
            title="Incident 2 Days Ago",
            severity="MEDIUM",
            status="RESOLVED",
            service_id=svc.id,
            data_mode="demo",
            detected_at=ts_2_days_ago,
        )
        inc_recent_2 = Incident(
            id=uuid4(),
            title="Incident 5 Days Ago",
            severity="HIGH",
            status="RESOLVED",
            service_id=svc.id,
            data_mode="demo",
            detected_at=ts_5_days_ago,
        )
        inc_old_1 = Incident(
            id=uuid4(),
            title="Incident 8 Days Ago",
            severity="CRITICAL",
            status="RESOLVED",
            service_id=svc.id,
            data_mode="demo",
            detected_at=ts_8_days_ago,
        )
        inc_old_2 = Incident(
            id=uuid4(),
            title="Incident 30 Days Ago",
            severity="CRITICAL",
            status="RESOLVED",
            service_id=svc.id,
            data_mode="demo",
            detected_at=ts_30_days_ago,
        )

        session.add_all([inc_recent_1, inc_recent_2, inc_old_1, inc_old_2])
        await session.commit()

        # Run 7-day retention purge
        deleted_count = await execute_timestamp_purge(module="incidents", period="7d", db=session)
        assert deleted_count >= 2

        # Verify recent records (<= 7 days) are preserved
        c_recent_1 = await session.execute(select(Incident).where(Incident.id == inc_recent_1.id))
        assert c_recent_1.scalar_one_or_none() is not None

        c_recent_2 = await session.execute(select(Incident).where(Incident.id == inc_recent_2.id))
        assert c_recent_2.scalar_one_or_none() is not None

        # Verify older records (> 7 days) are deleted
        c_old_1 = await session.execute(select(Incident).where(Incident.id == inc_old_1.id))
        assert c_old_1.scalar_one_or_none() is None

        c_old_2 = await session.execute(select(Incident).where(Incident.id == inc_old_2.id))
        assert c_old_2.scalar_one_or_none() is None

        # Clean up test recent records
        await session.execute(delete(Incident).where(Incident.id.in_([inc_recent_1.id, inc_recent_2.id])))
        await session.commit()


async def _async_test_deletions():
    transport = ASGITransport(app=app)
    eng_user_id = uuid4()
    async with AsyncSessionLocal() as session:
        # Create engineer user to test RBAC rejection
        eng_user = User(
            id=eng_user_id,
            username=f"eng_{eng_user_id.hex[:6]}",
            email=f"eng_{eng_user_id.hex[:6]}@synapse.local",
            password_hash="testhash",
            role="ENGINEER",
        )
        session.add(eng_user)

        svc_res = await session.execute(select(Service).limit(1))
        svc = svc_res.scalar_one()

        test_inc = Incident(
            id=uuid4(),
            title="Individual Delete Test Incident",
            severity="MEDIUM",
            status="OPEN",
            service_id=svc.id,
            data_mode="demo",
        )
        session.add(test_inc)
        await session.flush()

        test_history = IncidentHistory(
            id=uuid4(),
            incident_id=test_inc.id,
            action="TEST_ACTION",
            new_value="Audit entry to delete individually",
        )
        session.add(test_history)

        test_risk = RiskAssessment(
            id=uuid4(),
            service_id=svc.id,
            risk_score=Decimal("45.5"),
            confidence=Decimal("0.85"),
            data_mode="demo",
        )
        session.add(test_risk)
        await session.commit()

        inc_id = str(test_inc.id)
        hist_id = str(test_history.id)
        risk_id = str(test_risk.id)

    eng_token = create_access_token(data={"sub": str(eng_user_id), "username": "eng_test", "role": "ENGINEER"})
    eng_headers = {"Authorization": f"Bearer {eng_token}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        admin_headers = await get_real_auth_headers(client)

        # 1. Delete individual audit history entry
        del_hist = await client.delete(f"/api/incidents/history/{hist_id}", headers=admin_headers)
        assert del_hist.status_code == 204

        # 2. Delete individual risk assessment
        del_risk = await client.delete(f"/api/risk-assessments/{risk_id}", headers=admin_headers)
        assert del_risk.status_code == 204

        # 3. Delete individual incident
        del_inc = await client.delete(f"/api/incidents/{inc_id}", headers=admin_headers)
        assert del_inc.status_code == 204

        # 4. Verify bulk delete requires confirm_all=true
        fail_bulk = await client.delete("/api/incidents", headers=admin_headers)
        assert fail_bulk.status_code == 400

        # 5. Verify non-admin/non-sre role cannot bulk delete
        unauth_bulk = await client.delete("/api/incidents?confirm_all=true", headers=eng_headers)
        assert unauth_bulk.status_code == 403

        # 6. Bulk delete with confirm_all=true succeeds for admin
        bulk_resp = await client.delete("/api/incidents?confirm_all=true&mode=demo", headers=admin_headers)
        assert bulk_resp.status_code == 200
        assert bulk_resp.json()["status"] == "success"

        # 7. Clean up engineer user
        async with AsyncSessionLocal() as session:
            await session.execute(delete(User).where(User.id == eng_user_id))
            await session.commit()


def test_retention_settings_api():
    asyncio.run(_async_test_retention_settings())


def test_timestamp_based_retention_prune():
    asyncio.run(_async_test_timestamp_prune())


def test_individual_and_bulk_deletion():
    asyncio.run(_async_test_deletions())


if __name__ == "__main__":
    test_retention_settings_api()
    test_timestamp_based_retention_prune()
    test_individual_and_bulk_deletion()
    print("All retention and deletion tests passed successfully!")
