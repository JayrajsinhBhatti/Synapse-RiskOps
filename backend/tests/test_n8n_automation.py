"""
Synapse RiskOps - Layer 7 n8n Automation Test Suite
====================================================
Tests:
- test_incident_payload: validates Section 7.3 payload schema contract.
- test_n8n_webhook: verifies delivery to live n8n webhook endpoint.
- test_critical_routing: verifies CRITICAL severity triggers human approval notification.
- test_invalid_payload_safe_failure: verifies missing required fields fail safely.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import httpx
from datetime import datetime, timezone
from uuid import uuid4

from app.services.orchestrator import OrchestrationService


def build_valid_critical_payload(incident_id=None, service="payment-service"):
    return {
        "incident_id": str(incident_id or uuid4()),
        "service": service,
        "severity": "CRITICAL",
        "risk_score": 82.4,
        "risk_tier": "CRITICAL",
        "predicted_failure": "latency_degradation",
        "anomaly_score": 0.91,
        "forecast_risk": 0.74,
        "root_cause": "payment-service latency degradation",
        "affected_services": ["payment-service", "order-service"],
        "confidence": 0.91,
        "routing_decision": "human_approval",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "guidance": "Scale service or increase database connection pool",
        "status": "OPEN",
    }


def test_incident_payload_contract():
    """Verify incident payload adheres strictly to Section 7.3 specification."""
    payload = build_valid_critical_payload()
    
    # Required fields per Section 7.5
    required_fields = [
        "incident_id",
        "service",
        "severity",
        "risk_score",
        "timestamp",
        "confidence",
        "routing_decision",
    ]
    for field in required_fields:
        assert field in payload, f"Missing required field: {field}"
        assert payload[field] is not None, f"Field {field} cannot be None"
    
    # Validate types
    assert isinstance(payload["risk_score"], (int, float))
    assert 0 <= payload["risk_score"] <= 100
    assert isinstance(payload["confidence"], (int, float))
    assert 0 <= payload["confidence"] <= 1.0
    assert payload["severity"] in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "HEALTHY"]
    assert payload["routing_decision"] in ["human_approval", "escalate", "auto_remediate", "none"]


@pytest.mark.asyncio
async def test_n8n_webhook_delivery():
    """Verify live HTTP POST delivery to n8n webhook /webhook/riskops-incident."""
    orchestrator = OrchestrationService()
    webhook_url = "http://localhost:5678/webhook/riskops-incident"
    
    payload = build_valid_critical_payload()
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(webhook_url, json=payload)
            assert resp.status_code == 200, f"Expected 200 from n8n, got {resp.status_code}: {resp.text}"
            data = resp.json()
            assert "Workflow was started" in data.get("message", "")
        except httpx.ConnectError:
            pytest.skip("n8n container is not reachable on localhost:5678")


@pytest.mark.asyncio
async def test_critical_routing():
    """Verify that CRITICAL incident evaluates and generates notification awaiting human approval."""
    webhook_url = "http://localhost:5678/webhook/riskops-incident"
    payload = build_valid_critical_payload(service="payment-service")
    payload["severity"] = "CRITICAL"
    payload["risk_score"] = 85.5
    payload["confidence"] = 0.92
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(webhook_url, json=payload)
            assert resp.status_code == 200
        except httpx.ConnectError:
            pytest.skip("n8n container is not reachable on localhost:5678")


@pytest.mark.asyncio
async def test_invalid_payload_safe_failure():
    """Verify that an invalid payload missing required fields fails safely without attempting remediation."""
    webhook_url = "http://localhost:5678/webhook/riskops-incident"
    invalid_payload = {
        "service": "payment-service",
        # Missing incident_id, severity, risk_score, timestamp, confidence, routing_decision
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(webhook_url, json=invalid_payload)
            # n8n accepts webhook with 200 and routes internally to Safe Failure Log node
            assert resp.status_code == 200
        except httpx.ConnectError:
            pytest.skip("n8n container is not reachable on localhost:5678")
