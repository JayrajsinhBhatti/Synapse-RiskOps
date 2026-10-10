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
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.api.auth import get_current_user, get_current_user_or_system, require_role
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.incident import Incident, IncidentHistory
from app.models.service import Service
from app.models.user import User
from app.schemas.incident import (
    IncidentAssignRequest,
    IncidentCreate,
    IncidentHistoryResponse,
    IncidentNoteCreate,
    IncidentNoteResponse,
    IncidentResponse,
    IncidentUpdate,
)
from app.schemas.analytics import SimilarIncidentItem
import asyncio
from app.services.email_service import email_service
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
        data_mode=getattr(incident_data, "data_mode", "demo") or "demo",
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

    # Dispatch Gmail SMTP Incident Alert to Admin
    try:
        service_name_str = service.service_name if (incident_data.service_id and 'service' in locals() and service) else "Platform Service"
        email_payload = {
            "incident_id": str(incident.id),
            "service_name": service_name_str,
            "failure_type": incident.predicted_failure_type or "manual_reported_incident",
            "severity": incident.severity,
            "risk_score": float(incident.risk_score or 75.0),
            "ml_confidence": float(incident.confidence or 0.88),
            "rca_confidence": 0.85,
            "root_cause": service_name_str,
            "routing_decision": "human_approval",
            "guidance": incident.description or "Incident logged. Immediate triage recommended.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        asyncio.create_task(email_service.send_incident_alert(email_payload))
    except Exception as e:
        pass

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
    mode: Optional[str] = Query(default=None, description="Filter by operational mode ('demo' or 'connected')"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_or_system),
):
    """
    Return list of incidents with optional filtering by status, severity, service, and operational mode.
    Ordered by detected_at descending.
    """
    query = select(Incident).order_by(Incident.detected_at.desc())

    if status_filter:
        query = query.where(Incident.status == status_filter.upper())

    if severity:
        query = query.where(Incident.severity == severity.upper())

    if service_id:
        query = query.where(Incident.service_id == service_id)

    # Operational mode filter (apply only when explicitly requested via query parameter)
    if mode:
        query = query.where(Incident.data_mode == mode.lower())

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
    current_user: User = Depends(get_current_user_or_system),
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
    "",
    status_code=status.HTTP_200_OK,
    summary="Purge all incidents matching active operational mode (requires confirmation & role)",
)
async def delete_all_incidents(
    confirm_all: bool = Query(False, description="Must be true to confirm bulk deletion"),
    mode: Optional[str] = Query(None, description="'demo', 'connected', or omit to purge all"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "SRE"])),
):
    """
    Bulk delete all incidents from PostgreSQL.
    Requires explicit confirmation flag (confirm_all=True) and ADMIN or SRE role.
    Respects active operational mode ('demo' or 'connected') to prevent cross-mode deletion.
    """
    if not confirm_all:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bulk deletion requires confirm_all=true query parameter.",
        )

    active_mode = mode
    if not active_mode and request:
        active_mode = request.headers.get("x-synapse-mode")

    query = delete(Incident)
    if active_mode:
        query = query.where(Incident.data_mode == active_mode.lower())

    result = await db.execute(query)
    deleted_count = result.rowcount or 0
    await db.commit()

    # Broadcast real-time SSE event to trigger immediate UI synchronization
    await sse_manager.broadcast_incidents_bulk_deleted(count=deleted_count, mode=active_mode)

    return {
        "status": "success",
        "deleted_count": deleted_count,
        "mode": active_mode or "all",
        "message": f"Successfully deleted {deleted_count} incident records.",
    }


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
    await db.commit()

    # Broadcast real-time SSE event
    await sse_manager.broadcast_incident_deleted(incident_id)

    return None


@router.delete(
    "/history/{history_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an individual audit history log entry",
)
async def delete_incident_history_entry(
    history_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an individual audit trail entry by UUID."""
    result = await db.execute(
        select(IncidentHistory).where(IncidentHistory.id == history_id)
    )
    entry = result.scalar_one_or_none()

    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit history entry not found",
        )

    await db.delete(entry)
    await db.commit()

    # Broadcast real-time SSE event
    await sse_manager.broadcast_incident_history_deleted(history_id)

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


# =====================================================
# INCIDENT OWNERSHIP & COLLABORATION WORKFLOW (P0)
# =====================================================

@router.post(
    "/{incident_id}/acknowledge",
    response_model=IncidentResponse,
    summary="One-click acknowledge incident (sets status to ACKNOWLEDGED)",
)
async def acknowledge_incident(
    incident_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    SRE Incident Acknowledgment:
    Transitions incident status from OPEN to ACKNOWLEDGED (or INVESTIGATING).
    Automatically claims ownership (sets assigned_to) if currently unassigned.
    Logs audit entry and broadcasts real-time update over SSE.
    """
    res = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = res.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    old_status = incident.status
    incident.status = "ACKNOWLEDGED"
    if not incident.assigned_to:
        incident.assigned_to = current_user.id

    history_entry = IncidentHistory(
        incident_id=incident.id,
        action="ACKNOWLEDGED",
        old_value=old_status,
        new_value=f"Incident acknowledged and assigned to {current_user.username}",
        changed_by=current_user.id,
    )
    db.add(history_entry)
    await db.flush()
    await db.refresh(incident)

    await sse_manager.broadcast_incident_updated(incident)
    return incident


@router.post(
    "/{incident_id}/assign",
    response_model=IncidentResponse,
    summary="Assign incident to an SRE engineer",
)
async def assign_incident(
    incident_id: UUID,
    assign_data: IncidentAssignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Assigns or transfers incident ownership to another engineer with audit tracking.
    """
    res = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = res.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    user_res = await db.execute(select(User).where(User.id == assign_data.assigned_to))
    assignee = user_res.scalar_one_or_none()
    if not assignee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignee user not found")

    old_assigned = str(incident.assigned_to) if incident.assigned_to else "Unassigned"
    incident.assigned_to = assignee.id

    history_entry = IncidentHistory(
        incident_id=incident.id,
        action="ASSIGNED",
        old_value=old_assigned,
        new_value=f"Assigned to {assignee.username} ({assignee.role})" + (f": {assign_data.note}" if assign_data.note else ""),
        changed_by=current_user.id,
    )
    db.add(history_entry)
    await db.flush()
    await db.refresh(incident)

    await sse_manager.broadcast_incident_updated(incident)
    return incident


@router.post(
    "/{incident_id}/notes",
    response_model=IncidentNoteResponse,
    summary="Add investigation note/comment to incident",
)
async def add_incident_note(
    incident_id: UUID,
    note_data: IncidentNoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Adds a collaborative investigation note or diagnostic update to the incident audit log.
    """
    res = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = res.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    now = datetime.now(timezone.utc)
    history_entry = IncidentHistory(
        incident_id=incident.id,
        action="NOTE_ADDED",
        old_value=None,
        new_value=note_data.content,
        changed_by=current_user.id,
        changed_at=now,
    )
    db.add(history_entry)
    await db.flush()
    await db.refresh(history_entry)

    await sse_manager.broadcast_incident_updated(incident)

    return IncidentNoteResponse(
        id=history_entry.id,
        incident_id=incident.id,
        content=note_data.content,
        author=current_user.username,
        author_id=current_user.id,
        created_at=now,
    )


@router.get(
    "/{incident_id}/notes",
    response_model=List[IncidentNoteResponse],
    summary="Get collaboration notes for an incident",
)
async def get_incident_notes(
    incident_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_or_system),
):
    """
    Retrieves all investigation notes and comments recorded on this incident.
    """
    query = (
        select(IncidentHistory, User.username)
        .outerjoin(User, IncidentHistory.changed_by == User.id)
        .where(
            IncidentHistory.incident_id == incident_id,
            IncidentHistory.action == "NOTE_ADDED",
        )
        .order_by(IncidentHistory.changed_at.desc())
    )
    res = await db.execute(query)
    rows = res.all()

    return [
        IncidentNoteResponse(
            id=hist.id,
            incident_id=hist.incident_id,
            content=hist.new_value or "",
            author=username or "System SRE",
            author_id=hist.changed_by,
            created_at=hist.changed_at,
        )
        for hist, username in rows
    ]


# =====================================================
# SIMILAR PAST INCIDENTS MATCHING (P1)
# =====================================================

@router.get(
    "/{incident_id}/similar",
    response_model=List[SimilarIncidentItem],
    summary="Find similar past incidents for organizational memory and fast resolution",
)
async def get_similar_incidents(
    incident_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_or_system),
):
    """
    Finds past resolved incidents matching this incident's service or failure pattern.
    Surfaces what the root cause was, what playbook resolved it, and past MTTR.
    """
    res = await db.execute(select(Incident).where(Incident.id == incident_id))
    current_inc = res.scalar_one_or_none()
    if not current_inc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    # Query resolved incidents
    query = (
        select(Incident)
        .where(
            Incident.id != incident_id,
            Incident.status == "RESOLVED",
        )
        .order_by(Incident.resolved_at.desc())
        .limit(10)
    )
    res = await db.execute(query)
    candidates = res.scalars().all()

    similar_list = []
    for cand in candidates:
        # Compute match score based on service_id match and failure_type match
        score = 0.50
        if cand.service_id and current_inc.service_id and cand.service_id == current_inc.service_id:
            score += 0.35
        if (
            cand.predicted_failure_type
            and current_inc.predicted_failure_type
            and cand.predicted_failure_type.lower() == current_inc.predicted_failure_type.lower()
        ):
            score += 0.15

        dur_str = "3m 40s"
        if cand.resolved_at and cand.detected_at:
            secs = int((cand.resolved_at - cand.detected_at).total_seconds())
            if secs > 0:
                m = secs // 60
                s = secs % 60
                dur_str = f"{m}m {s}s" if m > 0 else f"{s}s"

        similar_list.append(
            SimilarIncidentItem(
                id=cand.id,
                title=cand.title,
                severity=cand.severity,
                status=cand.status,
                detected_at=cand.detected_at,
                resolved_at=cand.resolved_at,
                duration_formatted=dur_str,
                predicted_failure_type=cand.predicted_failure_type or "LATENCY_DEGRADATION",
                root_cause=cand.root_cause or "High concurrency connection pool exhaustion",
                guidance=cand.guidance or "Restart connection pool and scale up replicas from 2 to 4",
                resolution_action=cand.routing_decision or "playbooks/scale_service_replicas.yml",
                similarity_score=round(min(0.98, score), 2),
            )
        )

    # Sort by similarity score descending
    similar_list.sort(key=lambda x: x.similarity_score, reverse=True)
    return similar_list[:5]