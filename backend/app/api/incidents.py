"""
Synapse RiskOps - Incident Management API
=========================================
Owner: Person 2 | Week: 5

CRUD APIs and audit logging for incident management.
All endpoints require JWT authentication.
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.api.auth import get_current_user
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.incident import Incident, IncidentHistory
from app.models.service import Service
from app.models.user import User
from app.schemas.incident import (
    IncidentCreate,
    IncidentHistoryResponse,
    IncidentResponse,
    IncidentUpdate,
)
from app.services.sse_manager import sse_manager

router = APIRouter(
    prefix="/api/incidents",
    tags=["Incidents"],
)


# =====================================================
# CREATE INCIDENT
# =====================================================

@router.post(
    "",
    response_model=IncidentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_incident(
    incident_data: IncidentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new incident record and record an audit log in incident_history.
    The authenticated user automatically becomes the creator.
    """

    # Validate service if supplied
    if incident_data.service_id is not None:
        result = await db.execute(
            select(Service).where(Service.id == incident_data.service_id)
        )
        service = result.scalar_one_or_none()
        if service is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service not found",
            )
        if not service.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Service is inactive",
            )

    # Validate assigned user if supplied
    if incident_data.assigned_to is not None:
        result = await db.execute(
            select(User).where(User.id == incident_data.assigned_to)
        )
        assigned_user = result.scalar_one_or_none()
        if assigned_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assigned user not found",
            )
        if not assigned_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned user is inactive",
            )

    incident = Incident(
        title=incident_data.title,
        description=incident_data.description,
        severity=incident_data.severity.upper(),
        status="OPEN",
        service_id=incident_data.service_id,
        risk_score=incident_data.risk_score,
        confidence=incident_data.confidence,
        predicted_failure=incident_data.predicted_failure,
        assigned_to=incident_data.assigned_to,
        created_by=current_user.id,
    )

    db.add(incident)
    await db.flush()

    # Record initial audit trail entry
    history_entry = IncidentHistory(
        incident_id=incident.id,
        action="CREATED",
        old_value=None,
        new_value=f"Incident created with severity {incident.severity} and status OPEN",
        changed_by=current_user.id,
    )
    db.add(history_entry)

    await db.flush()
    await db.refresh(incident)

    # Broadcast real-time SSE event to connected dashboard clients
    await sse_manager.broadcast_incident_created(incident)

    return incident


# =====================================================
# LIST INCIDENTS
# =====================================================

@router.get(
    "",
    response_model=List[IncidentResponse],
)
async def list_incidents(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    severity: Optional[str] = None,
    service_id: Optional[UUID] = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return list of incidents with optional filtering by status, severity, and service.
    Ordered by detected_at descending.
    """
    query = select(Incident).order_by(Incident.detected_at.desc())

    if status_filter:
        query = query.where(Incident.status == status_filter.upper())

    if severity:
        query = query.where(Incident.severity == severity.upper())

    if service_id:
        query = query.where(Incident.service_id == service_id)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    incidents = result.scalars().all()

    return incidents


# =====================================================
# REAL-TIME SSE STREAMING & ALERTS
# =====================================================

@router.get(
    "/stream",
    summary="Real-time incident event stream",
    description="Server-Sent Events (SSE) stream for live updates on incidents and risk alerts.",
    response_class=EventSourceResponse,
)
async def stream_incidents(
    request: Request,
    token: Optional[str] = Query(default=None, description="Optional JWT bearer token for SSE authentication"),
):
    """
    Real-time Server-Sent Events (SSE) endpoint for the dashboard.
    Yields initial connection handshake, heartbeat pings, and live incident updates:
    - `connected`: Initial connection event
    - `ping`: Keep-alive heartbeat (15s interval)
    - `incident_created`: New incident detected/created
    - `incident_updated`: Incident status/severity/resolution mutation
    - `incident_deleted`: Incident deleted
    - `risk_alert`: High-risk score alerts from ML Engine
    """
    # Optional token verification if token provided via query parameter or Authorization header
    auth_token = token
    if not auth_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            auth_token = auth_header.replace("Bearer ", "").strip()

    if auth_token:
        payload = decode_access_token(auth_token)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return EventSourceResponse(
        sse_manager.subscribe(request),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/stream/status",
    summary="Get active SSE stream listener count",
)
async def stream_status():
    """Return count of active SSE stream connections."""
    return {
        "active_connections": sse_manager.active_connections,
        "service": "sse",
    }


@router.post(
    "/alert",
    status_code=status.HTTP_200_OK,
    summary="Broadcast ML risk alert",
)
async def broadcast_risk_alert_endpoint(
    alert_data: dict,
    current_user: User = Depends(get_current_user),
):
    """Broadcast an incoming risk alert from ML Engine or GenAI agent to connected SSE clients."""
    await sse_manager.broadcast_risk_alert(alert_data)
    return {"status": "broadcasted", "listeners": sse_manager.active_connections}


# =====================================================
# GET SINGLE INCIDENT
# =====================================================

@router.get(
    "/{incident_id}",
    response_model=IncidentResponse,
)
async def get_incident(
    incident_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return a single incident by its UUID."""
    result = await db.execute(
        select(Incident).where(Incident.id == incident_id)
    )
    incident = result.scalar_one_or_none()

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )

    return incident


# =====================================================
# UPDATE INCIDENT (PUT & PATCH)
# =====================================================

@router.api_route(
    "/{incident_id}",
    methods=["PUT", "PATCH"],
    response_model=IncidentResponse,
)
async def update_incident(
    incident_id: UUID,
    incident_data: IncidentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update incident fields. Automatically tracks state mutations
    in the incident_history audit log and records resolved_at when resolved.
    """
    result = await db.execute(
        select(Incident).where(Incident.id == incident_id)
    )
    incident = result.scalar_one_or_none()

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )

    # Validate service if changed
    if incident_data.service_id is not None:
        res = await db.execute(
            select(Service).where(Service.id == incident_data.service_id)
        )
        service = res.scalar_one_or_none()
        if service is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service not found",
            )

    # Validate assigned user if changed
    if incident_data.assigned_to is not None:
        res = await db.execute(
            select(User).where(User.id == incident_data.assigned_to)
        )
        assigned_user = res.scalar_one_or_none()
        if assigned_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assigned user not found",
            )

    update_data = incident_data.model_dump(exclude_unset=True)

    # Track status change in history & auto-set resolved_at
    if "status" in update_data and update_data["status"]:
        new_status = update_data["status"].upper()
        if new_status != incident.status:
            db.add(
                IncidentHistory(
                    incident_id=incident.id,
                    action="STATUS_CHANGED",
                    old_value=incident.status,
                    new_value=new_status,
                    changed_by=current_user.id,
                )
            )
            # Auto-set resolved_at if transitioning to RESOLVED
            if new_status == "RESOLVED" and not update_data.get("resolved_at"):
                update_data["resolved_at"] = datetime.now(timezone.utc)
            update_data["status"] = new_status

    # Track severity change in history
    if "severity" in update_data and update_data["severity"]:
        new_severity = update_data["severity"].upper()
        if new_severity != incident.severity:
            db.add(
                IncidentHistory(
                    incident_id=incident.id,
                    action="SEVERITY_CHANGED",
                    old_value=incident.severity,
                    new_value=new_severity,
                    changed_by=current_user.id,
                )
            )
            update_data["severity"] = new_severity

    # Apply updates
    for field, value in update_data.items():
        setattr(incident, field, value)

    await db.flush()
    await db.refresh(incident)

    # Broadcast real-time SSE event
    await sse_manager.broadcast_incident_updated(incident)

    return incident


# =====================================================
# DELETE INCIDENT
# =====================================================

@router.delete(
    "/{incident_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_incident(
    incident_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an incident and its associated audit trail."""
    result = await db.execute(
        select(Incident).where(Incident.id == incident_id)
    )
    incident = result.scalar_one_or_none()

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )

    await db.delete(incident)

    # Broadcast real-time SSE event
    await sse_manager.broadcast_incident_deleted(incident_id)

    return None


# =====================================================
# AUDIT TRAIL / INCIDENT HISTORY
# =====================================================

@router.get(
    "/{incident_id}/history",
    response_model=List[IncidentHistoryResponse],
)
async def get_incident_history(
    incident_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the audit history entries for an incident ordered by timestamp descending."""
    result = await db.execute(
        select(IncidentHistory)
        .where(IncidentHistory.incident_id == incident_id)
        .order_by(IncidentHistory.changed_at.desc())
    )
    history_records = result.scalars().all()

    return history_records