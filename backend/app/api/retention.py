"""
Synapse RiskOps - Time-Based Data Retention & Purge API
======================================================
Manages time-based retention policies (1d, 7d, 30d, 90d, all)
and executes timestamp-based pruning for Incidents, Audit Logs, and Risk Assessments.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

import uuid
from pydantic import BaseModel, Field

from app.api.auth import get_current_user_or_system, require_role
from app.core.config import settings
from app.core.database import get_db
from app.models.incident import Incident, IncidentHistory
from app.models.retention import RetentionPolicy, AdminAuditLog
from app.models.risk_assessment import RiskAssessment
from app.models.user import User
from app.schemas.system import (
    RetentionPurgeResponse,
    RetentionSettingItem,
    RetentionSettingsResponse,
    RetentionUpdateRequest,
)
from app.services.sse_manager import sse_manager

logger = logging.getLogger("synapse.retention")

class AdminLogClearRequest(BaseModel):
    confirm: bool = Field(..., description="Must explicitly be true to confirm deletion")
    reason: str = Field(..., min_length=3, description="Audit justification for log clearance")
    scope: str = Field("operational_telemetry", description="'operational_telemetry' or 'transient_risk_assessments'")
    older_than_days: Optional[int] = Field(None, ge=0, description="Delete records older than N days (defaults to LOG_RETENTION_DAYS)")

class AdminLogClearResponse(BaseModel):
    success: bool
    records_cleared: int
    cleared_by: str
    cleared_at: str
    scope: str
    reason: str
    audit_id: str
    message: str

router = APIRouter(
    prefix="/api/retention",
    tags=["Data Retention"],
)

RETENTION_DELTAS: Dict[str, timedelta] = {
    "1d": timedelta(days=1),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "90d": timedelta(days=90),
}


async def _get_or_init_policies(db: AsyncSession) -> List[RetentionPolicy]:
    """Retrieve policies or seed default records if table is uninitialized."""
    res = await db.execute(select(RetentionPolicy))
    policies = list(res.scalars().all())

    existing_modules = {p.module for p in policies}
    required_modules = ["incidents", "risk_assessments"]

    needed_seeds = []
    for mod in required_modules:
        if mod not in existing_modules:
            needed_seeds.append(RetentionPolicy(module=mod, retention_period="all"))

    if needed_seeds:
        for seed in needed_seeds:
            db.add(seed)
        await db.commit()
        res = await db.execute(select(RetentionPolicy))
        policies = list(res.scalars().all())

    return policies


async def execute_timestamp_purge(
    module: str,
    period: str,
    db: AsyncSession,
) -> int:
    """
    Executes timestamp-based deletion: records older than the cutoff timestamp are deleted.
    Strictly evaluates timestamps (e.g. detected_at < now - 7 days), NOT record count.
    """
    if period not in RETENTION_DELTAS:
        return 0  # 'all' time -> no records pruned

    delta = RETENTION_DELTAS[period]
    cutoff = datetime.now(timezone.utc) - delta
    deleted_count = 0

    if module == "incidents":
        # Delete incidents older than cutoff (cascades to incident_history)
        inc_del = await db.execute(
            delete(Incident).where(Incident.detected_at < cutoff)
        )
        deleted_count = inc_del.rowcount or 0

        # Also purge any older audit trail events
        hist_del = await db.execute(
            delete(IncidentHistory).where(IncidentHistory.changed_at < cutoff)
        )
        hist_count = hist_del.rowcount or 0
        logger.info(f"Purged {deleted_count} incidents and {hist_count} audit history records older than {cutoff.isoformat()}")

    elif module == "risk_assessments":
        risk_del = await db.execute(
            delete(RiskAssessment).where(RiskAssessment.assessed_at < cutoff)
        )
        deleted_count = risk_del.rowcount or 0
        logger.info(f"Purged {deleted_count} risk assessments older than {cutoff.isoformat()}")

    # Update retention_policies metadata
    res = await db.execute(select(RetentionPolicy).where(RetentionPolicy.module == module))
    pol = res.scalar_one_or_none()
    if pol:
        pol.last_purged_at = datetime.now(timezone.utc)
        pol.records_purged_last = deleted_count
        await db.commit()

    return deleted_count


@router.get(
    "/settings",
    response_model=RetentionSettingsResponse,
    summary="Get retention policy settings for all modules",
)
async def get_retention_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_or_system),
):
    """Return all configured module retention policies (1d, 7d, 30d, 90d, all)."""
    policies = await _get_or_init_policies(db)
    items = [
        RetentionSettingItem(
            module=p.module,
            retention_period=p.retention_period,
            auto_purge_enabled=p.auto_purge_enabled,
            last_purged_at=p.last_purged_at,
            records_purged_last=p.records_purged_last or 0,
        )
        for p in policies
    ]
    return RetentionSettingsResponse(
        policies=items,
        supported_periods=["1d", "7d", "30d", "90d", "all"],
    )


@router.put(
    "/settings",
    response_model=RetentionPurgeResponse,
    summary="Update retention policy for a module and apply timestamp cutoff immediately",
)
async def update_retention_policy(
    request: RetentionUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_or_system),
):
    """
    Update retention policy for 'incidents' or 'risk_assessments'.
    If a timeframe (e.g. '7d') is selected, automatically removes records older than that timeframe.
    """
    res = await db.execute(
        select(RetentionPolicy).where(RetentionPolicy.module == request.module)
    )
    policy = res.scalar_one_or_none()

    if policy is None:
        policy = RetentionPolicy(
            module=request.module,
            retention_period=request.retention_period,
            auto_purge_enabled=request.auto_purge_enabled if request.auto_purge_enabled is not None else True,
        )
        db.add(policy)
    else:
        policy.retention_period = request.retention_period
        if request.auto_purge_enabled is not None:
            policy.auto_purge_enabled = request.auto_purge_enabled

    await db.commit()

    # Apply retention immediately
    records_deleted = 0
    cutoff_str = None
    if request.retention_period != "all":
        cutoff = datetime.now(timezone.utc) - RETENTION_DELTAS[request.retention_period]
        cutoff_str = cutoff.isoformat()
        records_deleted = await execute_timestamp_purge(
            module=request.module,
            period=request.retention_period,
            db=db,
        )

    # Broadcast SSE update
    await sse_manager.broadcast_retention_purged(
        module=request.module,
        records_deleted=records_deleted,
        cutoff=cutoff_str,
    )

    return RetentionPurgeResponse(
        module=request.module,
        retention_period=request.retention_period,
        cutoff_timestamp=cutoff_str,
        records_deleted=records_deleted,
        purged_at=datetime.now(timezone.utc).isoformat(),
        message=(
            f"Retention set to '{request.retention_period}'. Removed {records_deleted} records older than {request.retention_period}."
            if request.retention_period != "all"
            else f"Retention set to 'all'. All historical records will be preserved."
        ),
    )


@router.post(
    "/purge",
    response_model=RetentionPurgeResponse,
    summary="Manually trigger timestamp-based retention cleanup",
)
async def trigger_retention_purge(
    module: str = Query(..., pattern="^(incidents|risk_assessments)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_or_system),
):
    """
    Manually triggers retention cleanup according to the configured retention policy.
    Removes records whose timestamps are older than the active retention window.
    """
    res = await db.execute(
        select(RetentionPolicy).where(RetentionPolicy.module == module)
    )
    policy = res.scalar_one_or_none()
    period = policy.retention_period if policy else "all"

    records_deleted = 0
    cutoff_str = None

    if period != "all":
        cutoff = datetime.now(timezone.utc) - RETENTION_DELTAS[period]
        cutoff_str = cutoff.isoformat()
        records_deleted = await execute_timestamp_purge(module=module, period=period, db=db)

    await sse_manager.broadcast_retention_purged(
        module=module,
        records_deleted=records_deleted,
        cutoff=cutoff_str,
    )

    return RetentionPurgeResponse(
        module=module,
        retention_period=period,
        cutoff_timestamp=cutoff_str,
        records_deleted=records_deleted,
        purged_at=datetime.now(timezone.utc).isoformat(),
        message=f"Pruned {records_deleted} records older than {period}.",
    )


@router.get(
    "/config",
    summary="Get active operational telemetry retention configuration",
)
async def get_retention_config():
    """Returns the default and active operational log retention policy."""
    return {
        "log_retention_days": getattr(settings, "LOG_RETENTION_DAYS", 10),
        "default_retention_period": f"{getattr(settings, 'LOG_RETENTION_DAYS', 10)}d",
        "description": "Operational telemetry logs retained for 10 days by default. Automatically pruned.",
        "admin_clearance_supported": True,
    }


@router.post(
    "/admin/clear-logs",
    response_model=AdminLogClearResponse,
    summary="ADMIN-only manual operational log clearance with audit trail",
)
async def admin_clear_operational_logs(
    payload: AdminLogClearRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_role(["ADMIN", "admin"])),
):
    """
    ADMIN-only control to safely clear operational telemetry logs.
    Enforces ADMIN role, requires explicit confirmation, records reason in an immutable audit record,
    and protects all critical business records (incidents, users, services, topology).
    """
    if not payload.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation flag 'confirm' must be explicitly True to execute manual log clearance.",
        )

    if not payload.reason.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audit reason is required for administrative log clearance.",
        )

    # Determine cutoff timestamp
    days = payload.older_than_days if payload.older_than_days is not None else getattr(settings, "LOG_RETENTION_DAYS", 10)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    records_deleted = 0

    if payload.scope in ("operational_telemetry", "all_transient_logs", "transient_risk_assessments"):
        # Prune risk assessments older than cutoff (protecting incidents and audit trails)
        risk_del = await db.execute(
            delete(RiskAssessment).where(RiskAssessment.assessed_at < cutoff)
        )
        records_deleted = risk_del.rowcount or 0

    audit_id = f"audit-clear-{uuid.uuid4().hex[:10]}"
    now_str = datetime.now(timezone.utc).isoformat()

    # Record in immutable AdminAuditLog table
    audit_entry = AdminAuditLog(
        id=audit_id,
        action="MANUAL_LOG_CLEARANCE",
        scope=payload.scope,
        reason=payload.reason.strip(),
        records_affected=records_deleted,
        performed_by=admin_user.username,
        metadata_json={
            "cutoff_timestamp": cutoff.isoformat(),
            "days_threshold": days,
            "admin_id": str(admin_user.id),
        },
    )
    db.add(audit_entry)
    await db.commit()

    # Broadcast event via SSE
    await sse_manager.broadcast(
        "admin_logs_cleared",
        {
            "audit_id": audit_id,
            "scope": payload.scope,
            "records_cleared": records_deleted,
            "cleared_by": admin_user.username,
            "cleared_at": now_str,
        },
    )

    logger.info(
        f"Admin [{admin_user.username}] manually cleared {records_deleted} records in scope '{payload.scope}' (reason: '{payload.reason}')"
    )

    return AdminLogClearResponse(
        success=True,
        records_cleared=records_deleted,
        cleared_by=admin_user.username,
        cleared_at=now_str,
        scope=payload.scope,
        reason=payload.reason.strip(),
        audit_id=audit_id,
        message=f"Successfully pruned {records_deleted} records older than {days} days. Audit record {audit_id} created.",
    )


@router.get(
    "/admin/audit-trail",
    summary="ADMIN-only view of administrative clearance audit logs",
)
async def get_admin_audit_trail(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_role(["ADMIN", "admin"])),
):
    """Retrieve immutable audit history of administrative operations."""
    res = await db.execute(select(AdminAuditLog).order_by(AdminAuditLog.performed_at.desc()).limit(50))
    logs = res.scalars().all()
    return [
        {
            "audit_id": l.id,
            "action": l.action,
            "scope": l.scope,
            "reason": l.reason,
            "records_affected": l.records_affected,
            "performed_by": l.performed_by,
            "performed_at": l.performed_at.isoformat() if l.performed_at else None,
            "metadata": l.metadata_json or {},
        }
        for l in logs
    ]
