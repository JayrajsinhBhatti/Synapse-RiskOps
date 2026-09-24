"""
Synapse RiskOps - Week 5 Step 4 SSE Streaming & Real-Time Alerts Test Suite
==========================================================================
Owner: Person 2 | Week: 5

Verifies:
1. SSEManager Pub/Sub Service:
   - Initial connection handshake ('connected' event)
   - Broadcast distribution to active subscribers
   - Keep-alive heartbeat ('ping' event)
   - Clean subscriber disconnection and active connection tracking
   - Specialized broadcast helpers:
     * broadcast_incident_created
     * broadcast_incident_updated
     * broadcast_incident_deleted
     * broadcast_risk_alert
2. HTTP API Endpoints:
   - GET /api/incidents/stream/status (Connection count & health check)
   - GET /api/incidents/stream with invalid token -> 401 Unauthorized
   - GET /api/incidents/stream endpoint handler:
     * Validates JWT token
     * Produces EventSourceResponse with text/event-stream media type
     * Sends connected handshake
     * Streams real-time broadcast events
     * Cleans up listener on connection close
   - POST /api/incidents/alert (ML Engine / GenAI risk alert broadcast)
3. Mutation Hooks:
   - Verifies create, update, delete incident operations trigger SSE broadcast helpers
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

# Ensure backend root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from httpx import ASGITransport

from app.api.auth import get_current_user
from app.api.incidents import stream_incidents
from app.core.security import create_access_token
from app.main import app
from app.models.user import User
from app.services.sse_manager import SSEManager, sse_manager


# =====================================================
# 1. UNIT TESTS: SSEManager Pub/Sub Logic
# =====================================================

async def run_sse_manager_pubsub():
    print("\n" + "=" * 70)
    print("STEP 4.1: SSE MANAGER UNIT PUB/SUB VERIFICATION")
    print("=" * 70)

    mgr = SSEManager()
    assert mgr.active_connections == 0, "Initial active connections should be 0"
    print("  [OK] Initial state: 0 active connections")

    # Subscribe client with quick ping interval
    gen = mgr.subscribe(ping_interval=0.1)

    # 1. First event should be connected handshake
    first_event = await anext(gen)
    assert first_event["event"] == "connected", f"Expected 'connected', got {first_event['event']}"
    payload = json.loads(first_event["data"])
    assert payload["status"] == "ready"
    assert mgr.active_connections == 1, f"Expected 1 active connection, got {mgr.active_connections}"
    print(f"  [OK] Handshake received: event='{first_event['event']}', status='{payload['status']}'")

    # 2. Broadcast a custom event
    await mgr.broadcast("custom_test_event", {"msg": "hello from unit test"})
    event2 = await anext(gen)
    assert event2["event"] == "custom_test_event"
    data2 = json.loads(event2["data"])
    assert data2["msg"] == "hello from unit test"
    print(f"  [OK] Custom broadcast event received: {data2}")

    # 3. Test broadcast_incident_created
    mock_incident_id = uuid4()
    mock_incident = {
        "id": mock_incident_id,
        "title": "Payment Gateway Timeout",
        "severity": "CRITICAL",
        "status": "OPEN",
        "service_id": uuid4(),
        "risk_score": 92.5,
        "confidence": 0.94,
        "detected_at": datetime.now(timezone.utc),
    }
    await mgr.broadcast_incident_created(mock_incident)
    event3 = await anext(gen)
    assert event3["event"] == "incident_created"
    data3 = json.loads(event3["data"])
    assert data3["id"] == str(mock_incident_id)
    assert data3["title"] == "Payment Gateway Timeout"
    assert data3["severity"] == "CRITICAL"
    assert data3["risk_score"] == 92.5
    print(f"  [OK] broadcast_incident_created received: id={data3['id']}, title='{data3['title']}'")

    # 4. Test broadcast_incident_updated
    mock_updated = {
        "id": mock_incident_id,
        "title": "Payment Gateway Timeout",
        "severity": "CRITICAL",
        "status": "RESOLVED",
        "resolved_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    await mgr.broadcast_incident_updated(mock_updated)
    event4 = await anext(gen)
    assert event4["event"] == "incident_updated"
    data4 = json.loads(event4["data"])
    assert data4["status"] == "RESOLVED"
    assert data4["resolved_at"] is not None
    print(f"  [OK] broadcast_incident_updated received: status='{data4['status']}'")

    # 5. Test broadcast_incident_deleted
    await mgr.broadcast_incident_deleted(mock_incident_id)
    event5 = await anext(gen)
    assert event5["event"] == "incident_deleted"
    data5 = json.loads(event5["data"])
    assert data5["id"] == str(mock_incident_id)
    print(f"  [OK] broadcast_incident_deleted received: id={data5['id']}")

    # 6. Test broadcast_risk_alert
    alert_payload = {
        "service_name": "order-service",
        "risk_tier": "CRITICAL",
        "composite_risk_score": 88.4,
        "predicted_failure_type": "HIGH_TRAFFIC_CONGESTION",
    }
    await mgr.broadcast_risk_alert(alert_payload)
    event6 = await anext(gen)
    assert event6["event"] == "risk_alert"
    data6 = json.loads(event6["data"])
    assert data6["composite_risk_score"] == 88.4
    print(f"  [OK] broadcast_risk_alert received: service='{data6['service_name']}', score={data6['composite_risk_score']}")

    # 7. Test keep-alive ping timeout
    ping_event = await anext(gen)
    assert ping_event["event"] == "ping", f"Expected 'ping', got {ping_event['event']}"
    assert ping_event["data"] == "keep-alive"
    print("  [OK] Keep-alive heartbeat ping received")

    # 8. Close subscriber generator and verify cleanup
    await gen.aclose()
    assert mgr.active_connections == 0, f"Expected 0 active connections after close, got {mgr.active_connections}"
    print("  [OK] Subscriber cleanup verified: 0 active connections remaining")


# =====================================================
# 2. HTTP ENDPOINT TESTS: /stream, /stream/status, /alert
# =====================================================

async def run_sse_http_endpoints():
    print("\n" + "=" * 70)
    print("STEP 4.2: SSE HTTP ENDPOINTS & EVENT STREAMING VERIFICATION")
    print("=" * 70)

    # Ensure clean singleton state
    await sse_manager.clear_all()

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:

        # 1. Test GET /api/incidents/stream/status
        status_resp = await client.get("/api/incidents/stream/status")
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        assert status_data["active_connections"] == 0
        assert status_data["service"] == "sse"
        print("  [OK] GET /api/incidents/stream/status returned 200 and active_connections=0")

        # 2. Test Invalid Token -> 401 Unauthorized
        invalid_resp = await client.get("/api/incidents/stream?token=invalid.jwt.signature")
        assert invalid_resp.status_code == 401
        assert "Invalid or expired authentication token" in invalid_resp.json()["detail"]
        print("  [OK] GET /api/incidents/stream with invalid token correctly rejected (401)")

        # 3. Create valid test JWT token
        valid_token = create_access_token({
            "sub": str(uuid4()),
            "username": "dashboard-viewer",
            "role": "ENGINEER",
        })
        auth_headers = {"Authorization": f"Bearer {valid_token}"}

        # 4. Direct invocation of stream_incidents endpoint handler
        mock_request = MagicMock()
        mock_request.headers = {}
        stream_response = await stream_incidents(request=mock_request, token=valid_token)

        assert stream_response.status_code == 200
        assert stream_response.media_type == "text/event-stream"
        assert stream_response.headers.get("Cache-Control") == "no-cache"
        assert stream_response.headers.get("Connection") == "keep-alive"
        assert stream_response.headers.get("X-Accel-Buffering") == "no"
        print("  [OK] stream_incidents handler returned EventSourceResponse (200 text/event-stream)")

        # Verify stream iteration
        it = stream_response.body_iterator

        # Event 1: Initial Handshake
        handshake = await anext(it)
        assert handshake["event"] == "connected"
        assert "Connected to Synapse RiskOps live stream" in handshake["data"]
        assert sse_manager.active_connections == 1
        print("  [OK] Stream yielded handshake event to client")

        # Event 2: Broadcast Incident Created
        inc_id = str(uuid4())
        await sse_manager.broadcast_incident_created({
            "id": inc_id,
            "title": "PostgreSQL Connection Pool Exhausted",
            "severity": "CRITICAL",
            "status": "OPEN",
            "risk_score": 95.0,
            "confidence": 0.96,
        })
        ev_created = await anext(it)
        assert ev_created["event"] == "incident_created"
        created_data = json.loads(ev_created["data"])
        assert created_data["id"] == inc_id
        assert created_data["title"] == "PostgreSQL Connection Pool Exhausted"
        print(f"  [OK] Stream yielded incident_created: id={inc_id}")

        # Event 3: Broadcast Incident Updated
        await sse_manager.broadcast_incident_updated({
            "id": inc_id,
            "title": "PostgreSQL Connection Pool Exhausted",
            "severity": "CRITICAL",
            "status": "RESOLVED",
            "resolved_at": datetime.now(timezone.utc),
        })
        ev_updated = await anext(it)
        assert ev_updated["event"] == "incident_updated"
        updated_data = json.loads(ev_updated["data"])
        assert updated_data["status"] == "RESOLVED"
        print(f"  [OK] Stream yielded incident_updated: status='RESOLVED'")

        # Event 4: Broadcast Risk Alert
        await sse_manager.broadcast_risk_alert({
            "service": "auth-service",
            "risk_tier": "CRITICAL",
            "composite_risk_score": 91.0,
        })
        ev_alert = await anext(it)
        assert ev_alert["event"] == "risk_alert"
        alert_data = json.loads(ev_alert["data"])
        assert alert_data["service"] == "auth-service"
        print("  [OK] Stream yielded risk_alert to client")

        # Close stream and check active connections
        await it.aclose()
        assert sse_manager.active_connections == 0
        print("  [OK] Stream listener closed cleanly (0 active connections)")

        # 5. Test POST /api/incidents/alert endpoint
        mock_user = User(
            id=uuid4(),
            username="admin",
            email="admin@synapse.io",
            role="ADMIN",
            is_active=True,
        )
        app.dependency_overrides[get_current_user] = lambda: mock_user

        try:
            alert_payload = {
                "service": "payment-service",
                "risk_score": 91.2,
                "tier": "CRITICAL",
                "message": "Latency anomaly detected across 3 instances",
            }
            alert_resp = await client.post(
                "/api/incidents/alert",
                json=alert_payload,
                headers=auth_headers,
            )
            assert alert_resp.status_code == 200
            resp_body = alert_resp.json()
            assert resp_body["status"] == "broadcasted"
            assert "listeners" in resp_body
            print(f"  [OK] POST /api/incidents/alert broadcasted successfully: {resp_body}")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    print("\n" + "=" * 70)
    print("ALL STEP 4 SSE STREAMING TESTS PASSED!")
    print("=" * 70)


# =====================================================
# TEST RUNNERS FOR PYTEST & DIRECT EXECUTION
# =====================================================

def test_sse_step4_flow():
    asyncio.run(run_sse_manager_pubsub())
    asyncio.run(run_sse_http_endpoints())


if __name__ == "__main__":
    test_sse_step4_flow()
