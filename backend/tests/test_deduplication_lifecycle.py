"""
Synapse RiskOps - Deduplication & Lifecycle Automated Test Suite
================================================================
Section 9.12 Deduplication Tests:
- test_duplicate_critical_does_not_create_new_incident
- test_duplicate_critical_does_not_trigger_duplicate_automation
- test_recovery_resolves_incident
- test_new_failure_creates_new_incident
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from decimal import Decimal

from app.services.orchestrator import OrchestrationService
from app.models.incident import Incident
from app.models.service import Service


@pytest.fixture
def mock_setup():
    orchestrator = OrchestrationService()
    mock_db = AsyncMock()
    mock_service = Service(id=uuid4(), service_name="payment-service")
    
    mock_res_svc = MagicMock()
    mock_res_svc.scalar_one_or_none.return_value = mock_service

    mock_res_dep = MagicMock()
    mock_res_dep.all.return_value = ["order-service", "api-gateway"]
    
    return orchestrator, mock_db, mock_service, mock_res_svc, mock_res_dep


@pytest.mark.asyncio
async def test_duplicate_critical_does_not_create_new_incident(mock_setup):
    """Subsequent CRITICAL observations for the same service update existing incident without creating a new one."""
    orchestrator, mock_db, mock_service, mock_res_svc, mock_res_dep = mock_setup
    
    # Existing active OPEN incident
    active_incident_id = uuid4()
    existing_incident = Incident(
        id=active_incident_id,
        service_id=mock_service.id,
        status="OPEN",
        risk_score=Decimal("85.0"),
        severity="CRITICAL",
    )
    mock_res_inc = MagicMock()
    mock_res_inc.scalars.return_value.first.return_value = existing_incident

    mock_db.execute = AsyncMock(side_effect=[mock_res_svc, mock_res_dep, mock_res_inc])
    
    orchestrator._call_ml_engine_analyze = AsyncMock(return_value={
        "service_name": "payment-service",
        "prediction": {"risk_score": 88.5, "confidence": 0.92, "predicted_failure_type": "latency_degradation"},
        "diagnosis": {"rca_candidates": [{"service": "payment-service", "label": "ROOT_CAUSE", "confidence": 0.95}]},
    })
    genai_mock = AsyncMock()
    orchestrator._call_genai_diagnose = genai_mock
    
    record = await orchestrator.orchestrate_incident_lifecycle(
        service_name="payment-service",
        metrics={"cpu_usage": 45.0, "response_time_p99": 4200.0},
        db=mock_db,
    )
    
    # Assert same incident ID is preserved
    assert record.incident_id == str(active_incident_id)
    assert existing_incident.risk_score == Decimal("88.50")
    # Assert GenAI is NOT re-invoked
    assert genai_mock.call_count == 0


@pytest.mark.asyncio
async def test_duplicate_critical_does_not_trigger_duplicate_automation(mock_setup):
    """Subsequent observations debounce automation dispatch (no duplicate n8n execution)."""
    orchestrator, mock_db, mock_service, mock_res_svc, mock_res_dep = mock_setup
    
    existing_incident = Incident(
        id=uuid4(),
        service_id=mock_service.id,
        status="OPEN",
        risk_score=Decimal("82.0"),
        severity="CRITICAL",
    )
    mock_res_inc = MagicMock()
    mock_res_inc.scalars.return_value.first.return_value = existing_incident
    mock_db.execute = AsyncMock(side_effect=[mock_res_svc, mock_res_dep, mock_res_inc])
    
    orchestrator._call_ml_engine_analyze = AsyncMock(return_value={
        "service_name": "payment-service",
        "prediction": {"risk_score": 84.0, "confidence": 0.90, "predicted_failure_type": "latency_degradation"},
        "diagnosis": {},
    })
    
    n8n_mock = AsyncMock(return_value=True)
    orchestrator._send_n8n_incident = n8n_mock
    
    record = await orchestrator.orchestrate_incident_lifecycle(
        service_name="payment-service",
        metrics={"cpu_usage": 45.0, "response_time_p99": 4300.0},
        db=mock_db,
    )
    
    # Because incident was already OPEN and risk >= 40, n8n MUST NOT be called again
    assert n8n_mock.call_count == 0
    assert record.automation["execution_status"] == "SKIPPED_DEBOUNCED"


@pytest.mark.asyncio
async def test_recovery_resolves_incident(mock_setup):
    """When telemetry normalizes (risk < 40), active incident is marked RESOLVED and recovery notification is sent."""
    orchestrator, mock_db, mock_service, mock_res_svc, mock_res_dep = mock_setup
    
    active_incident_id = uuid4()
    existing_incident = Incident(
        id=active_incident_id,
        service_id=mock_service.id,
        status="OPEN",
        risk_score=Decimal("82.0"),
        severity="CRITICAL",
    )
    mock_res_inc = MagicMock()
    mock_res_inc.scalars.return_value.first.return_value = existing_incident
    mock_db.execute = AsyncMock(side_effect=[mock_res_svc, mock_res_dep, mock_res_inc])
    
    # Healthy telemetry yielding risk < 40
    orchestrator._call_ml_engine_analyze = AsyncMock(return_value={
        "service_name": "payment-service",
        "prediction": {"risk_score": 18.0, "confidence": 0.80, "predicted_failure_type": "none"},
        "diagnosis": {},
    })
    
    n8n_mock = AsyncMock(return_value=True)
    orchestrator._send_n8n_incident = n8n_mock
    
    record = await orchestrator.orchestrate_incident_lifecycle(
        service_name="payment-service",
        metrics={"cpu_usage": 15.0, "response_time_p99": 25.0},
        db=mock_db,
    )
    
    assert existing_incident.status == "RESOLVED"
    assert existing_incident.resolved_at is not None
    assert record.lifecycle_status == "RESOLVED"
    # n8n notified of recovery to stop further remediation
    assert n8n_mock.call_count == 1
    recovery_payload = n8n_mock.call_args[0][0]
    assert recovery_payload["status"] == "RESOLVED"
    assert recovery_payload["severity"] == "HEALTHY"


@pytest.mark.asyncio
async def test_new_failure_creates_new_incident(mock_setup):
    """Once prior incident is resolved, a new failure triggers creation of a new independent incident."""
    orchestrator, mock_db, mock_service, mock_res_svc, mock_res_dep = mock_setup
    
    # No OPEN incident in database (prior one was resolved)
    mock_res_no_inc = MagicMock()
    mock_res_no_inc.scalars.return_value.first.return_value = None
    mock_db.execute = AsyncMock(side_effect=[mock_res_svc, mock_res_dep, mock_res_no_inc])
    
    orchestrator._call_ml_engine_analyze = AsyncMock(return_value={
        "service_name": "payment-service",
        "prediction": {"risk_score": 90.0, "confidence": 0.94, "predicted_failure_type": "latency_degradation"},
        "diagnosis": {"rca_candidates": [{"service": "payment-service", "label": "ROOT_CAUSE", "confidence": 0.94}]},
    })
    genai_mock = AsyncMock(return_value={
        "root_cause_candidates_ranked": [{"cause": "Latency Degradation", "confidence": 0.94}],
        "guidance": {"summary": "Scale service pods"}
    })
    orchestrator._call_genai_diagnose = genai_mock
    n8n_mock = AsyncMock(return_value=True)
    orchestrator._send_n8n_incident = n8n_mock
    
    record = await orchestrator.orchestrate_incident_lifecycle(
        service_name="payment-service",
        metrics={"cpu_usage": 60.0, "response_time_p99": 5000.0},
        db=mock_db,
    )
    
    # New incident created
    assert record.incident_id is not None
    assert record.lifecycle_status == "OPEN"
    assert genai_mock.call_count == 1
    assert n8n_mock.call_count == 1
    created_payload = n8n_mock.call_args[0][0]
    assert created_payload["severity"] == "CRITICAL"
    assert created_payload["routing_decision"] == "human_approval"
