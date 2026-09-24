"""
Synapse RiskOps - Week 5 Risk Assessment API Verification Test
==============================================================
Owner: Person 2 | Week: 5

Verifies:
1. POST /api/risk-assessments (Ingest risk assessment snapshot from ML Engine)
2. GET /api/risk-assessments (List historical assessments with service filter)
3. GET /api/risk-assessments/latest (Retrieve latest risk score per service)
"""

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

# Ensure backend root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from httpx import ASGITransport
from app.main import app


async def run_risk_assessment_tests():
    print("\n" + "=" * 70)
    print("WEEK 5: RISK ASSESSMENT API VERIFICATION")
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

        # 2. Record a risk assessment snapshot
        payload = {
            "service_name": "order-service",
            "risk_score": 88.5,
            "confidence": 0.92,
            "anomaly_score": 0.885,
            "affected_services": ["order-service", "payment-service"],
            "features_used": {"cpu_usage": 91.2, "latency_p99": 420.0},
            "model_version": "v1.0.0",
        }
        create_resp = await client.post("/api/risk-assessments", json=payload, headers=headers)
        assert create_resp.status_code == 201
        created = create_resp.json()
        assert float(created["risk_score"]) == 88.5
        assert float(created["confidence"]) == 0.92
        svc_id = created["service_id"]
        print(f"  [OK] POST /api/risk-assessments created snapshot for order-service (ID: {created['id']})")

        # 3. List risk assessments
        list_resp = await client.get(f"/api/risk-assessments?service_id={svc_id}", headers=headers)
        assert list_resp.status_code == 200
        assessments = list_resp.json()
        assert len(assessments) >= 1
        print(f"  [OK] GET /api/risk-assessments retrieved {len(assessments)} record(s) for order-service")

        # 4. Get latest risk assessments per service
        latest_resp = await client.get("/api/risk-assessments/latest", headers=headers)
        assert latest_resp.status_code == 200
        latest = latest_resp.json()
        assert len(latest) >= 1
        print(f"  [OK] GET /api/risk-assessments/latest returned {len(latest)} service snapshot(s)")

    print("=" * 70)
    print("ALL RISK ASSESSMENT TESTS PASSED!")
    print("=" * 70)


def test_risk_assessments_step5_flow():
    asyncio.run(run_risk_assessment_tests())


if __name__ == "__main__":
    test_risk_assessments_step5_flow()
