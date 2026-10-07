"""
Synapse RiskOps - Incident Deduplication, Trigger & Recovery Test Suite
========================================================================
Validates:
1. First CRITICAL creates one incident and triggers GenAI RCA.
2. Repeated CRITICAL observations for the SAME active incident update record
   and DO NOT invoke GenAI/Gemini again (Debounced).
3. Recovery observation (risk < 40) closes/resolves the active incident.
4. A later independent failure creates a new incident.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from decimal import Decimal
from datetime import datetime, timezone

from app.services.orchestrator import OrchestrationService
from app.models.incident import Incident
from app.models.service import Service


@pytest.mark.asyncio
async def test_deduplication_and_trigger_lifecycle():
    orchestrator = OrchestrationService()

    mock_db = AsyncMock()
    mock_service = Service(id=uuid4(), service_name="payment-service")

    # 1. Mock ML engine response for first critical observation
    orchestrator._call_ml_engine_analyze = AsyncMock(return_value={
        "service_name": "payment-service",
        "prediction": {"risk_score": 85.0, "confidence": 0.90, "predicted_failure_type": "latency_degradation"},
        "diagnosis": {"rca_candidates": [{"service": "payment-service", "label": "ROOT_CAUSE", "confidence": 0.95}]},
    })

    # Mock GenAI diagnose call
    genai_mock = AsyncMock(return_value={
        "root_cause_candidates_ranked": [
            {
                "cause": "Latency degradation on payment-service",
                "confidence": 0.95,
                "affected_services": ["order-service", "api-gateway"],
                "reason": "Extreme latency spike detected.",
            }
        ],
        "guidance": {"summary": "Investigate payment-service database connection pool and downstream timeout."}
    })
    orchestrator._call_genai_diagnose = genai_mock

    # Step 1: No open incident exists initially
    mock_res_svc = MagicMock()
    mock_res_svc.scalar_one_or_none.return_value = mock_service

    mock_res_dep = MagicMock()
    mock_res_dep.all.return_value = []

    mock_res_no_inc = MagicMock()
    mock_res_no_inc.scalars.return_value.first.return_value = None

    mock_db.execute = AsyncMock(side_effect=[mock_res_svc, mock_res_dep, mock_res_no_inc])

    # FIRST OBSERVATION (CRITICAL)
    rec1 = await orchestrator.orchestrate_incident_lifecycle(
        service_name="payment-service",
        metrics={"cpu_usage": 30.0, "response_time_p99": 4500.0},
        db=mock_db,
    )
    # GenAI MUST be invoked on first critical
    assert genai_mock.call_count == 1
    assert rec1.prediction["risk_score"] == 85.0
    first_incident_id = rec1.incident_id

    # 2. REPEATED OBSERVATION for SAME active incident
    active_incident = Incident(
        id=uuid4(),
        service_id=mock_service.id,
        status="OPEN",
        risk_score=Decimal("85.0"),
        severity="CRITICAL",
    )
    mock_res_active_inc = MagicMock()
    mock_res_active_inc.scalars.return_value.first.return_value = active_incident

    mock_db.execute = AsyncMock(side_effect=[mock_res_svc, mock_res_dep, mock_res_active_inc])

    rec2 = await orchestrator.orchestrate_incident_lifecycle(
        service_name="payment-service",
        metrics={"cpu_usage": 30.0, "response_time_p99": 4600.0},
        db=mock_db,
    )
    # GenAI must NOT be invoked again (Debounced!)
    assert genai_mock.call_count == 1
    assert rec2.incident_id == str(active_incident.id)

    # 3. RECOVERY OBSERVATION (risk drops below 40)
    orchestrator._call_ml_engine_analyze = AsyncMock(return_value={
        "service_name": "payment-service",
        "prediction": {"risk_score": 25.0, "confidence": 0.85, "predicted_failure_type": "none"},
        "diagnosis": {},
    })
    mock_db.execute = AsyncMock(side_effect=[mock_res_svc, mock_res_dep, mock_res_active_inc])

    rec3 = await orchestrator.orchestrate_incident_lifecycle(
        service_name="payment-service",
        metrics={"cpu_usage": 20.0, "response_time_p99": 35.0},
        db=mock_db,
    )
    assert active_incident.status == "RESOLVED"
    assert rec3.lifecycle_status == "RESOLVED"
    assert genai_mock.call_count == 1  # Still 1

    # 4. SUBSEQUENT INDEPENDENT FAILURE LATER (creates a new incident)
    orchestrator._call_ml_engine_analyze = AsyncMock(return_value={
        "service_name": "payment-service",
        "prediction": {"risk_score": 92.0, "confidence": 0.95, "predicted_failure_type": "cpu_saturation"},
        "diagnosis": {"rca_candidates": [{"service": "payment-service", "label": "ROOT_CAUSE", "confidence": 0.95}]},
    })
    # Now query returns None again (since previous was resolved)
    mock_db.execute = AsyncMock(side_effect=[mock_res_svc, mock_res_dep, mock_res_no_inc])

    rec4 = await orchestrator.orchestrate_incident_lifecycle(
        service_name="payment-service",
        metrics={"cpu_usage": 95.0, "response_time_p99": 35.0},
        db=mock_db,
    )
    # GenAI called again for the NEW independent incident!
    assert genai_mock.call_count == 2
    assert rec4.incident_id != first_incident_id
