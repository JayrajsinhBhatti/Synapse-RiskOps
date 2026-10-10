"""
Synapse RiskOps - System Mode & Live Verification Tests
=======================================================
Tests:
1. System mode retrieval and switching (demo <-> connected).
2. Clean data isolation: demo records and connected records never mix.
3. Live connection verification probe (/api/system/verify-connection).
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4
import httpx
from httpx import ASGITransport
from sqlalchemy import delete

# Ensure backend root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import AsyncSessionLocal
from app.models.incident import Incident
from app.models.service import Service
from app.models.user import User
from app.main import app


async def get_real_auth_headers(client: httpx.AsyncClient) -> dict:
    login_resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


async def _async_test_system_mode_flow():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await get_real_auth_headers(client)

        # 1. Get initial mode
        mode_resp = await client.get("/api/system/mode", headers=headers)
        assert mode_resp.status_code == 200
        initial_mode = mode_resp.json()["mode"]

        # 2. Set mode to 'connected'
        set_conn = await client.post(
            "/api/system/mode",
            json={"mode": "connected", "connection_config": {"prometheus_url": "http://localhost:9090"}},
            headers=headers,
        )
        assert set_conn.status_code == 200
        assert set_conn.json()["mode"] == "connected"

        # 3. Verify get returns 'connected'
        verify_conn = await client.get("/api/system/mode", headers=headers)
        assert verify_conn.json()["mode"] == "connected"

        # 4. Set back to initial mode
        set_back = await client.post(
            "/api/system/mode",
            json={"mode": initial_mode},
            headers=headers,
        )
        assert set_back.status_code == 200
        assert set_back.json()["mode"] == initial_mode


async def _async_test_mode_isolation():
    transport = ASGITransport(app=app)
    demo_inc_id = uuid4()
    conn_inc_id = uuid4()

    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        svc_res = await session.execute(select(Service).limit(1))
        svc = svc_res.scalar_one()

        demo_inc = Incident(
            id=demo_inc_id,
            title="Isolated Demo Incident",
            severity="MEDIUM",
            status="OPEN",
            service_id=svc.id,
            data_mode="demo",
        )
        conn_inc = Incident(
            id=conn_inc_id,
            title="Isolated Connected Incident",
            severity="HIGH",
            status="OPEN",
            service_id=svc.id,
            data_mode="connected",
        )
        session.add_all([demo_inc, conn_inc])
        await session.commit()

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await get_real_auth_headers(client)

        # Query with mode=demo
        demo_resp = await client.get("/api/incidents?mode=demo", headers=headers)
        assert demo_resp.status_code == 200
        demo_ids = [i["id"] for i in demo_resp.json()]
        assert str(demo_inc_id) in demo_ids
        assert str(conn_inc_id) not in demo_ids

        # Query with mode=connected
        conn_resp = await client.get("/api/incidents?mode=connected", headers=headers)
        assert conn_resp.status_code == 200
        conn_ids = [i["id"] for i in conn_resp.json()]
        assert str(conn_inc_id) in conn_ids
        assert str(demo_inc_id) not in conn_ids

    # Cleanup test records
    async with AsyncSessionLocal() as session:
        await session.execute(delete(Incident).where(Incident.id.in_([demo_inc_id, conn_inc_id])))
        await session.commit()


async def _async_test_verify_connection():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await get_real_auth_headers(client)

        verify_resp = await client.post(
            "/api/system/verify-connection",
            json={
                "connection_method": "synapse-cluster",
                "prometheus_url": "http://localhost:9090",
                "telemetry_bridge_url": "http://localhost:9010",
            },
            headers=headers,
        )
        assert verify_resp.status_code == 200
        data = verify_resp.json()
        assert "checks" in data
        assert len(data["checks"]) >= 4
        assert "services_discovered" in data
        assert "timestamp" in data


async def _async_test_connect_demo_app_rbac():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        admin_headers = await get_real_auth_headers(client)

        # 1. Disconnect succeeds unconditionally for Admin
        disc_res = await client.post(
            "/api/system/connect-demo-app",
            json={"action": "disconnect"},
            headers=admin_headers,
        )
        assert disc_res.status_code == 200
        assert disc_res.json()["mode"] == "demo"
        assert disc_res.json()["external_app_connected"] is False

        # 2. Connect requires reachable gateway or returns informative 400
        conn_res = await client.post(
            "/api/system/connect-demo-app",
            json={"action": "connect", "gateway_url": "http://localhost:9101"},
            headers=admin_headers,
        )
        assert conn_res.status_code in (200, 400)
        if conn_res.status_code == 200:
            assert conn_res.json()["success"] is True
            assert conn_res.json()["external_app_connected"] is True
            assert len(conn_res.json()["services"]) == 10
        else:
            assert "Could not reach external demo application" in conn_res.json()["detail"]

        # 3. Verify non-admin role rejection (403 Forbidden)
        viewer_login = await client.post(
            "/api/auth/login",
            json={"username": "operator", "password": "operator123"},
        )
        if viewer_login.status_code == 200:
            v_token = viewer_login.json()["access_token"]
            v_headers = {"Authorization": f"Bearer {v_token}", "Content-Type": "application/json"}
            forbidden_res = await client.post(
                "/api/system/connect-demo-app",
                json={"action": "connect"},
                headers=v_headers,
            )
            assert forbidden_res.status_code == 403


def test_system_mode_flow():
    asyncio.run(_async_test_system_mode_flow())


def test_mode_isolation():
    asyncio.run(_async_test_mode_isolation())


def test_verify_connection():
    asyncio.run(_async_test_verify_connection())


def test_connect_demo_app_rbac():
    asyncio.run(_async_test_connect_demo_app_rbac())


if __name__ == "__main__":
    test_system_mode_flow()
    test_mode_isolation()
    test_verify_connection()
    test_connect_demo_app_rbac()
    print("All system mode and connection verification tests passed!")

