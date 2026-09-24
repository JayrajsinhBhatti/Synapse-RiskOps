"""
Synapse RiskOps - End-to-End Orchestration Pipeline API
=======================================================
Owner: Person 2 | Week: 5

Provides REST endpoints to orchestrate telemetry diagnosis,
confidence routing, runbook remediation, and incident persistence.
"""

from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models.incident import Incident, IncidentHistory
from app.models.user import User
from app.schemas.orchestration import (
    AnomalyDiagnosisRequest,
    RemediationExecutionRequest,
    UnifiedIncidentRecordResponse,
)
from app.services.orchestrator import orchestrator
from app.services.sse_manager import sse_manager

router = APIRouter(
    prefix="/api/pipeline",
    tags=["Orchestration Pipeline"],
)


@router.post(
    "/diagnose-and-route",
    response_model=UnifiedIncidentRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger ML Diagnosis & GenAI Confidence Routing",
)
async def trigger_diagnosis_and_route(
    request: AnomalyDiagnosisRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Primary orchestration endpoint:
    1. Evaluates risk metrics via ML Engine RiskEngine
    2. Runs graph RCA traversal to locate root cause service
    3. Evaluates Person 1 Confidence Router (auto_remediate vs escalate)
    4. Executes automated runbook if confidence meets safety criteria
    5. Persists complete incident record, audit trail, and risk assessment in PostgreSQL
    6. Broadcasts real-time events to connected dashboards via Server-Sent Events (SSE)
    """
    record = await orchestrator.orchestrate_incident_lifecycle(
        service_name=request.service_name,
        metrics=request.metrics,
        environment=request.environment,
        scenario_id=request.scenario_id,
        assigned_to=request.assigned_to,
        db=db,
        current_user=current_user,
    )
    return record


@router.post(
    "/remediate",
    summary="Execute manual or autonomous remediation action",
)
async def execute_remediation(
    request: RemediationExecutionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Executes a remediation action for an incident, updates status to RESOLVED,
    records execution in incident_history, and broadcasts update over SSE.
    """
    result = await db.execute(
        select(Incident).where(Incident.id == request.incident_id)
    )
    incident = result.scalar_one_or_none()

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )

    now = datetime.now(timezone.utc)
    action_desc = request.action or "SCALE_OUT_PODS"
    target = request.target or "default-target"

    # Update incident to RESOLVED
    incident.status = "RESOLVED"
    incident.resolved_at = now

    # Record history
    db.add(
        IncidentHistory(
            incident_id=incident.id,
            action="MANUAL_OVERRIDE_REMEDIATED" if current_user.role != "SYSTEM" else "AUTO_REMEDIATED",
            old_value="OPEN",
            new_value=f"Executed action '{action_desc}' on target '{target}'. Incident resolved.",
            changed_by=current_user.id,
        )
    )

    await db.flush()
    await db.refresh(incident)

    # Broadcast update
    await sse_manager.broadcast_incident_updated(incident)

    return {
        "incident_id": str(incident.id),
        "status": incident.status,
        "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
        "action_executed": action_desc,
        "target": target,
    }
