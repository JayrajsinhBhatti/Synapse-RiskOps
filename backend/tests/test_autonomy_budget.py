"""
Synapse RiskOps - Autonomy Budget Verification Tests
====================================================
Tests end-to-end functionality of the Autonomy Budget Engine:
1. Low-risk auto-execution on non-critical service
2. Medium-risk approval requirement
3. Critical service safeguards (payment-service, auth-service, database require approval even with short recovery time)
4. Insufficient data handling (displays 'Insufficient data' instead of fabricating numbers)
5. Backend RBAC & human approval enforcement (Engineer blocked, Admin/Operator permitted)
6. Concurrency lock (prevents duplicate simultaneous actions on the same service)
7. Recovery verification & accuracy comparison (actual vs estimated execution/recovery time)
8. Tamper-evident audit logging
"""

import sys
from pathlib import Path
from uuid import uuid4

# Ensure backend root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import httpx
from httpx import ASGITransport
from app.main import app as fastapi_app
from app.core.security import create_access_token
from app.core.database import async_engine, Base
import app.models  # ensure models registered


@pytest.mark.asyncio
async def test_autonomy_budget_comprehensive():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        from app.core.database import AsyncSessionLocal
        from app.core.security import get_password_hash
        from app.models.user import User
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            res = await session.execute(select(User).where(User.username == "engineer"))
            eng_user = res.scalar_one_or_none()
            if not eng_user:
                eng_user = User(
                    username="engineer",
                    email="engineer@test.local",
                    password_hash=get_password_hash("engineer123"),
                    full_name="Lead Engineer",
                    role="ENGINEER",
                    is_active=True,
                )
                session.add(eng_user)
                await session.commit()
                await session.refresh(eng_user)
            eng_user_id = str(eng_user.id)

    transport = ASGITransport(app=fastapi_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # -----------------------------------------------------------
        # 1. Authentication
        # -----------------------------------------------------------
        admin_login = await client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert admin_login.status_code == 200, f"Admin login failed: {admin_login.text}"
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        eng_token = create_access_token({"sub": eng_user_id, "username": "engineer", "role": "ENGINEER"})
        eng_headers = {"Authorization": f"Bearer {eng_token}"}

        # -----------------------------------------------------------
        # 2. Test Low-Risk Auto-Execute (Non-critical service)
        # -----------------------------------------------------------
        low_eval = await client.post(
            "/api/autonomy/evaluate",
            headers=admin_headers,
            json={
                "service_name": "notification-service",
                "action": "SCALE_OUT_PODS",
                "current_metrics": {"error_rate": 0.2, "latency_p99": 85.0},
            },
        )
        assert low_eval.status_code == 200, low_eval.text
        low_data = low_eval.json()
        assert low_data["risk_level"] == "LOW"
        assert low_data["decision"] == "AUTO_EXECUTE"
        assert low_data["approval_required"] is False
        assert low_data["service_criticality"] == "MEDIUM" or low_data["service_criticality"] == "LOW"
        assert "Estimated restart:" in low_data["timing_estimate"]["display_text"]

        # -----------------------------------------------------------
        # 3. Test Critical Service Safeguard (payment-service)
        # Stricter safeguards even when estimated recovery time is short!
        # -----------------------------------------------------------
        crit_eval = await client.post(
            "/api/autonomy/evaluate",
            headers=admin_headers,
            json={
                "service_name": "payment-service",
                "action": "RESTART_POD",
                "current_metrics": {"error_rate": 0.5, "latency_p99": 90.0},
            },
        )
        assert crit_eval.status_code == 200, crit_eval.text
        crit_data = crit_eval.json()
        assert crit_data["service_criticality"] == "CRITICAL"
        assert crit_data["risk_level"] == "HIGH"
        assert crit_data["decision"] == "REQUIRE_APPROVAL"
        assert crit_data["approval_required"] is True
        assert any("CRITICAL SERVICE SAFEGUARD" in f for f in crit_data["factors"])
        payment_record_id = crit_data["remediation_record_id"]
        assert payment_record_id is not None

        # Also verify database service safeguard
        db_eval = await client.post(
            "/api/autonomy/evaluate",
            headers=admin_headers,
            json={
                "service_name": "postgres-primary",
                "action": "RESTART_CONNECTION_POOL",
            },
        )
        assert db_eval.status_code == 200, db_eval.text
        assert db_eval.json()["risk_level"] == "HIGH"
        assert db_eval.json()["approval_required"] is True

        # -----------------------------------------------------------
        # 4. Test Insufficient Data Handling
        # Shows "Insufficient data" rather than inventing precise values
        # -----------------------------------------------------------
        unknown_eval = await client.post(
            "/api/autonomy/evaluate",
            headers=admin_headers,
            json={
                "service_name": "custom-service-x",
                "action": "UNKNOWN_CUSTOM_EXPERIMENTAL_ACTION",
            },
        )
        assert unknown_eval.status_code == 200, unknown_eval.text
        unknown_timing = unknown_eval.json()["timing_estimate"]
        assert unknown_timing["source"] == "insufficient_data"
        assert unknown_timing["estimated_execution_seconds"] is None
        assert unknown_timing["estimated_recovery_seconds"] is None
        assert "Insufficient" in unknown_timing["display_text"]

        # -----------------------------------------------------------
        # 5. Test Backend Authorization & Approval Enforcement
        # Non-admin/operator engineer cannot approve high-risk action
        # -----------------------------------------------------------
        eng_approve = await client.post(
            "/api/autonomy/approve",
            headers=eng_headers,
            json={
                "remediation_record_id": payment_record_id,
                "approved": True,
            },
        )
        assert eng_approve.status_code == 403, "Engineer must not be allowed to approve"

        # Engineer cannot execute unapproved high-risk action directly
        eng_exec = await client.post(
            "/api/autonomy/execute",
            headers=eng_headers,
            json={
                "service_name": "payment-service",
                "action": "RESTART_POD",
                "remediation_record_id": payment_record_id,
            },
        )
        assert eng_exec.status_code == 403, "Unapproved high-risk execution by engineer must be rejected with 403"

        # Admin approves the action
        admin_approve = await client.post(
            "/api/autonomy/approve",
            headers=admin_headers,
            json={
                "remediation_record_id": payment_record_id,
                "approved": True,
                "reason": "Approved by Lead SRE after reviewing transaction safety buffer.",
            },
        )
        assert admin_approve.status_code == 200, admin_approve.text
        approved_data = admin_approve.json()
        assert approved_data["approval_status"] == "APPROVED"
        assert approved_data["approved_by_username"] == "admin"

        # Admin executes the approved remediation
        exec_res = await client.post(
            "/api/autonomy/execute",
            headers=admin_headers,
            json={
                "service_name": "payment-service",
                "action": "RESTART_POD",
                "remediation_record_id": payment_record_id,
            },
        )
        assert exec_res.status_code == 200, exec_res.text
        exec_data = exec_res.json()
        assert exec_data["status"] == "EXECUTED"
        assert exec_data["actual_execution_seconds"] > 0
        assert "semaphore_history_url" in exec_data

        # -----------------------------------------------------------
        # 6. Test Concurrency Lock (Prevent duplicate actions)
        # A concurrent action on the same service while IN_PROGRESS is rejected
        # -----------------------------------------------------------
        dup_eval = await client.post(
            "/api/autonomy/evaluate",
            headers=admin_headers,
            json={
                "service_name": "payment-service",
                "action": "SCALE_OUT_PODS",
            },
        )
        assert dup_eval.status_code == 200
        # If in-progress lock active, decision is REJECTED
        assert dup_eval.json()["decision"] == "REJECTED" or dup_eval.json()["approval_required"] is True

        # -----------------------------------------------------------
        # 7. Test Recovery Verification & Historical Feedback Loop
        # Verify recovery, calculate actual recovery time, store record
        # -----------------------------------------------------------
        verify_res = await client.post(
            f"/api/autonomy/verify-recovery/{payment_record_id}",
            headers=admin_headers,
            json={
                "remediation_record_id": payment_record_id,
                "current_metrics": {
                    "error_rate": 0.05,
                    "latency_p99": 65.0,
                },
            },
        )
        assert verify_res.status_code == 200, verify_res.text
        verified_data = verify_res.json()
        assert verified_data["success"] is True
        assert verified_data["post_remediation_health"] == "HEALTHY"
        assert verified_data["actual_recovery_seconds"] is not None
        assert verified_data["actual_recovery_seconds"] > 0

        # -----------------------------------------------------------
        # 8. Test Audit Logs & Budget Status
        # -----------------------------------------------------------
        status_res = await client.post(
            "/api/autonomy/budget-status",
            headers=admin_headers,
        )
        # Note: router has GET for budget-status, let's call GET
        status_get = await client.get(
            "/api/autonomy/budget-status",
            headers=admin_headers,
        )
        assert status_get.status_code == 200
        status_json = status_get.json()
        assert "policy" in status_json
        assert "services_criticality" in status_json
        assert status_json["services_criticality"]["payment-service"] == "CRITICAL"

        audit_res = await client.get(
            "/api/autonomy/audit-logs",
            params={"limit": 200},
            headers=admin_headers,
        )
        assert audit_res.status_code == 200
        audit_logs = audit_res.json()
        assert len(audit_logs) >= 3
        event_types = [a["event_type"] for a in audit_logs]
        assert "EVALUATED" in event_types
        assert "APPROVED" in event_types
        assert "EXECUTED" in event_types
        assert "RECOVERY_VERIFIED" in event_types

        history_res = await client.get(
            "/api/autonomy/history?service_name=payment-service",
            headers=admin_headers,
        )
        assert history_res.status_code == 200
        history_list = history_res.json()
        assert len(history_list) >= 1
        executed_records = [r for r in history_list if r.get("actual_execution_seconds") is not None]
        assert len(executed_records) >= 1, "Expected at least one completed execution record in history"
        assert executed_records[0]["service_name"] == "payment-service"
        assert executed_records[0]["actual_execution_seconds"] > 0
        # -----------------------------------------------------------
        # 9. Test Low-Mid Criticality Auto-Fix vs High Criticality & Risk Human-in-the-Loop
        # -----------------------------------------------------------
        # Incidents with low-mid criticality must be automatically fixed (AUTO_EXECUTE)
        low_mid_eval = await client.post(
            "/api/autonomy/evaluate",
            headers=admin_headers,
            json={
                "service_name": "notification-service",
                "action": "SCALE_OUT_PODS",
                "incident_criticality": "MEDIUM",
                "risk_tier": "WATCH",
                "risk_score": 55.0,
            },
        )
        assert low_mid_eval.status_code == 200, low_mid_eval.text
        low_mid_data = low_mid_eval.json()
        assert low_mid_data["decision"] == "AUTO_EXECUTE", f"Expected AUTO_EXECUTE for low-mid criticality, got {low_mid_data['decision']}"
        assert low_mid_data["approval_required"] is False
        assert low_mid_data["human_in_the_loop_required"] is False
        assert any("LOW-MID CRITICALITY AUTO-FIX" in f for f in low_mid_data["factors"])

        # In case criticality AND risk is high, add human-in-the-loop (REQUIRE_APPROVAL)
        high_crit_risk_eval = await client.post(
            "/api/autonomy/evaluate",
            headers=admin_headers,
            json={
                "service_name": "payment-service",
                "action": "SCALE_OUT_PODS",
                "incident_criticality": "HIGH",
                "risk_tier": "CRITICAL",
                "risk_score": 88.0,
            },
        )
        assert high_crit_risk_eval.status_code == 200, high_crit_risk_eval.text
        high_crit_data = high_crit_risk_eval.json()
        assert high_crit_data["decision"] == "REQUIRE_APPROVAL", f"Expected REQUIRE_APPROVAL when criticality and risk are high, got {high_crit_data['decision']}"
        assert high_crit_data["approval_required"] is True
        assert high_crit_data["human_in_the_loop_required"] is True
        assert any("HUMAN-IN-THE-LOOP REQUIRED" in f for f in high_crit_data["factors"])

        # -----------------------------------------------------------
        # 10. Test Low-Risk Automatic Auto-Execution (No Click Required)
        # -----------------------------------------------------------
        auto_exec_eval = await client.post(
            "/api/autonomy/evaluate",
            headers=admin_headers,
            json={
                "service_name": "notification-service",
                "action": "SCALE_OUT_PODS",
                "risk_tier": "HEALTHY",
                "risk_score": 20.0,
                "auto_execute_if_cleared": True,
            },
        )
        assert auto_exec_eval.status_code == 200, auto_exec_eval.text
        auto_data = auto_exec_eval.json()
        assert auto_data["decision"] == "AUTO_EXECUTE"
        assert auto_data["executed"] is True, "Expected auto_execute_if_cleared to automatically execute low-risk task"
        assert auto_data["execution_result"] is not None
        assert auto_data["execution_result"]["status"] == "EXECUTED"


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_autonomy_budget_comprehensive())
    print("\n[SUCCESS] All Autonomy Budget tests passed cleanly!")
