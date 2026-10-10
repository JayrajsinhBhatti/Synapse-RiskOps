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

from app.api.auth import get_current_user_or_system, require_role
from app.core.database import get_db
from app.models.incident import Incident, IncidentHistory
from app.models.retention import RetentionPolicy
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
