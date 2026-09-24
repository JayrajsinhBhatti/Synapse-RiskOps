"""
Synapse RiskOps - Week 5 Services & Topology API Verification Test
==================================================================
Owner: Person 2 | Week: 5

Verifies:
1. GET /api/services (List all 12 microservices)
2. GET /api/services/{id} (Fetch single service details)
3. GET /api/services/topology (Full dependency graph: 12 nodes, 19 edges)
"""

import asyncio
import sys
from pathlib import Path

# Ensure backend root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from httpx import ASGITransport
from app.main import app


async def run_services_and_topology_tests():
    print("\n" + "=" * 70)
    print("WEEK 5: SERVICES & TOPOLOGY GRAPH VERIFICATION")
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

        # 2. List services
        svc_resp = await client.get("/api/services", headers=headers)
        assert svc_resp.status_code == 200
        services = svc_resp.json()
        assert len(services) == 12, f"Expected 12 services, got {len(services)}"
        print(f"  [OK] GET /api/services returned {len(services)} services")

        # 3. Get single service
        first_svc = services[0]
        svc_id = first_svc["id"]
        single_resp = await client.get(f"/api/services/{svc_id}", headers=headers)
        assert single_resp.status_code == 200
        assert single_resp.json()["service_name"] == first_svc["service_name"]
        print(f"  [OK] GET /api/services/{svc_id} verified: '{first_svc['service_name']}'")

        # 4. Get Topology Graph
        topo_resp = await client.get("/api/services/topology", headers=headers)
        assert topo_resp.status_code == 200
        topo = topo_resp.json()
        assert topo["total_services"] == 12
        assert topo["total_dependencies"] == 19
        assert len(topo["dependencies"]) == 19
        print(f"  [OK] GET /api/services/topology verified: {topo['total_services']} nodes, {topo['total_dependencies']} directed edges")

    print("=" * 70)
    print("ALL SERVICES & TOPOLOGY TESTS PASSED!")
    print("=" * 70)


def test_services_step5_flow():
    asyncio.run(run_services_and_topology_tests())


if __name__ == "__main__":
    test_services_step5_flow()
