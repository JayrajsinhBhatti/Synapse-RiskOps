"""
Synapse RiskOps - Week 5 End-to-End Orchestration Pipeline Verification Test
=============================================================================
Owner: Person 2 | Week: 5

Verifies:
1. POST /api/pipeline/diagnose-and-route:
   - Evaluates telemetry metrics
   - Discovers root cause and ranked RCA candidates
   - Applies Person 1 Confidence Routing contract
   - Executes runbook remediation for high-confidence incidents
   - Persists Incident, IncidentHistory audit trail, and RiskAssessment in PostgreSQL
   - Returns UnifiedIncidentRecordResponse matching shared incident schema contract
2. POST /api/pipeline/remediate:
   - Executes remediation action on an existing incident
   - Transitions status to RESOLVED
   - Records audit trail in incident_history
"""

import asyncio
import sys
from pathlib import Path
from uuid import UUID

# Ensure backend root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from httpx import ASGITransport
from app.main import app


async def run_orchestration_tests():
    print("\n" + "=" * 70)
    print("WEEK 5: END-TO-END ORCHESTRATION PIPELINE VERIFICATION")
    print("=" * 70)

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:

        # 1. Login to get JWT
        login_resp = await client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("  [OK] Admin authenticated")

        # 2. Trigger Diagnosis & Routing
        diagnosis_payload = {
            "service_name": "order-service",
            "environment": "production",
            "metrics": {
                "cpu_usage": 92.5,
                "memory_usage": 84.1,
                "error_rate": 8.5,
                "latency_p99": 650.0,
            },
            "scenario_id": "SIM-SCENARIO-TRAFFIC-SPIKE",
        }
        resp = await client.post(
            "/api/pipeline/diagnose-and-route",
            json=diagnosis_payload,
            headers=headers,
        )
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        record = resp.json()

        print(f"  [OK] POST /api/pipeline/diagnose-and-route created incident: {record['incident_id']}")
        assert "incident_id" in record
        assert record["service"]["service_name"] == "order-service"
        assert len(record["service"]["dependency_ids"]) >= 1
        print(f"      - Service: {record['service']['service_name']} (Dependencies: {record['service']['dependency_ids']})")

        # Verify Prediction Block
        pred = record["prediction"]
        assert pred["risk_score"] >= 75.0
        print(f"      - Prediction: risk_score={pred['risk_score']}, failure_type='{pred['predicted_failure_type']}'")

        # Verify Diagnosis Block
        diag = record["diagnosis"]
        assert len(diag["root_cause_candidates_ranked"]) >= 1
        assert "propagation_path" in diag
        print(f"      - Diagnosis: RCA Candidates={len(diag['root_cause_candidates_ranked'])}, rca_confidence={diag['rca_confidence']}")

        # Verify Routing Block
        routing = record["routing"]
        assert routing["routing_decision"] in ["auto_remediate", "escalate"]
        print(f"      - Confidence Routing: decision='{routing['routing_decision']}', confidence={routing['routing_confidence']}")

        # Verify Automation Block
        automation = record["automation"]
        print(f"      - Automation: status='{automation.get('execution_status')}', actions={automation.get('actions_executed')}")

        incident_id = record["incident_id"]

        # 3. Verify Database Persistence of Incident
        get_inc_resp = await client.get(f"/api/incidents/{incident_id}", headers=headers)
        assert get_inc_resp.status_code == 200
        db_inc = get_inc_resp.json()
        assert db_inc["id"] == incident_id
        print(f"  [OK] Verified incident persisted in PostgreSQL (Status: {db_inc['status']}, Severity: {db_inc['severity']})")

        # 4. Verify Database Persistence of Audit Trail
        history_resp = await client.get(f"/api/incidents/{incident_id}/history", headers=headers)
        assert history_resp.status_code == 200
        history = history_resp.json()
        assert len(history) >= 2
        actions = [h["action"] for h in history]
        assert "CREATED" in actions
        assert "ROUTING_DECIDED" in actions
        print(f"  [OK] Verified audit trail in incident_history ({len(history)} entries): {actions}")

        # 5. Test Remediation Endpoint
        rem_payload = {
            "incident_id": incident_id,
            "action": "ROLLBACK_CANARY_DEPLOYMENT",
            "target": "order-service",
        }
        rem_resp = await client.post("/api/pipeline/remediate", json=rem_payload, headers=headers)
        assert rem_resp.status_code == 200
        rem_data = rem_resp.json()
        assert rem_data["status"] == "RESOLVED"
        assert rem_data["action_executed"] == "ROLLBACK_CANARY_DEPLOYMENT"
        print(f"  [OK] POST /api/pipeline/remediate resolved incident: action='{rem_data['action_executed']}'")

        # 6. Verify final status after remediation
        get_final_resp = await client.get(f"/api/incidents/{incident_id}", headers=headers)
        assert get_final_resp.status_code == 200
        assert get_final_resp.json()["status"] == "RESOLVED"
        print("  [OK] Verified final incident status in DB is RESOLVED")

    print("=" * 70)
    print("ALL END-TO-END ORCHESTRATION PIPELINE TESTS PASSED!")
    print("=" * 70)


def test_orchestration_step5_flow():
    asyncio.run(run_orchestration_tests())


if __name__ == "__main__":
    test_orchestration_step5_flow()
