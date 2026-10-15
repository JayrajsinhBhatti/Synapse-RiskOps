"""
Synapse RiskOps - Autonomy Budget API Router
============================================
Provides REST endpoints for evaluating proposed actions against autonomy policies,
enforcing human approvals, executing verified playbooks, recording recovery metrics,
and viewing audit logs.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user, get_current_user_or_system, require_role
from app.core.database import get_db
from app.models.autonomy import AutonomyAuditLog, AutonomyPolicyModel, RemediationRecord
from app.models.user import User
from app.schemas.autonomy import (
    AutonomyApprovalRequest,
    AutonomyAuditLogResponse,
    AutonomyBudgetStatusResponse,
    AutonomyEvaluationRequest,
    AutonomyEvaluationResponse,
    AutonomyExecuteRequest,
    AutonomyPolicyUpdate,
    AutonomyVerifyRecoveryRequest,
    RemediationRecordResponse,
)
from app.services.autonomy_budget import autonomy_budget_engine

router = APIRouter(
    prefix="/api/autonomy",
    tags=["Autonomy Budget"],
)


@router.post(
    "/evaluate",
    response_model=AutonomyEvaluationResponse,
    summary="Evaluate proposed remediation against Autonomy Budget policy",
)
async def evaluate_action(
    request: AutonomyEvaluationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_or_system),
):
    """
    Evaluates service criticality, blast radius, action reversibility,
    error budget, and historical execution/recovery timing.
    """
    try:
        evaluation = await autonomy_budget_engine.evaluate(
            service_name=request.service_name,
            action=request.action,
            runbook_id=request.runbook_id,
            incident_id=request.incident_id,
            current_metrics=request.current_metrics,
            risk_tier=request.risk_tier,
            risk_score=request.risk_score,
            incident_criticality=request.incident_criticality,
            auto_execute_if_cleared=bool(request.auto_execute_if_cleared),
            db=db,
            current_user=current_user,
        )
        return evaluation
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Autonomy evaluation failed: {str(e)}",
        )


@router.post(
    "/execute",
    summary="Execute remediation with backend autonomy policy enforcement",
)
async def execute_action(
    request: AutonomyExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Enforces autonomy policies on the backend:
    - Verifies approval requirement for medium/high risk or critical services.
    - Prevents concurrent duplicate actions on the same service.
    - Dispatches Ansible Semaphore task and logs immutable audit trail.
    """
    try:
        result = await autonomy_budget_engine.execute_remediation_with_budget(
            service_name=request.service_name,
            action=request.action,
            incident_id=request.incident_id,
            remediation_record_id=request.remediation_record_id,
            user=current_user,
            db=db,
            approval_notes=request.approval_notes,
        )
        return result
    except PermissionError as pe:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(pe),
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Execution error: {str(e)}",
        )


@router.post(
    "/approve",
    response_model=RemediationRecordResponse,
    summary="Approve or reject a pending medium/high risk remediation (OPERATOR or ADMIN)",
)
async def approve_remediation(
    request: AutonomyApprovalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "OPERATOR"])),
):
    """Human approval sign-off required for critical services or medium/high risk actions."""
    try:
        record = await autonomy_budget_engine.approve_or_reject(
            record_id=request.remediation_record_id,
            approved=request.approved,
            reason=request.reason,
            user=current_user,
            db=db,
        )
        return record
    except PermissionError as pe:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(pe),
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(ve),
        )


@router.post(
    "/verify-recovery/{record_id}",
    response_model=RemediationRecordResponse,
    summary="Verify post-remediation health and record actual recovery duration",
)
async def verify_recovery(
    record_id: UUID,
    request: Optional[AutonomyVerifyRecoveryRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Computes actual recovery time vs estimate, verifies healthy metric thresholds,
    and stores verified outcome to calibrate future historical estimates.
    """
    try:
        metrics = request.current_metrics if request else None
        record = await autonomy_budget_engine.verify_and_record_recovery(
            record_id=record_id,
            current_metrics=metrics,
            db=db,
        )
        return record
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(ve),
        )


@router.get(
    "/budget-status",
    response_model=AutonomyBudgetStatusResponse,
    summary="Get Autonomy Budget overview, active policies, and reliability status",
)
async def get_budget_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_or_system),
):
    """Retrieves current organizational policies, active counts, and service error budgets."""
    return await autonomy_budget_engine.get_budget_status(db)


@router.get(
    "/history",
    response_model=List[RemediationRecordResponse],
    summary="Get historical remediation records with estimated vs actual timing",
)
async def get_remediation_history(
    service_name: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_or_system),
):
    """Retrieves past remediation evaluations and actual results for audits and accuracy tracking."""
    query = (
        select(RemediationRecord)
        .where(RemediationRecord.status != "PROPOSED")
        .order_by(desc(RemediationRecord.created_at))
        .limit(limit)
    )
    if service_name:
        query = query.where(RemediationRecord.service_name == service_name)
    if action:
        query = query.where(RemediationRecord.action == action)

    res = await db.execute(query)
    return res.scalars().all()


@router.get(
    "/audit-logs",
    response_model=List[AutonomyAuditLogResponse],
    summary="Get tamper-evident Autonomy Audit trail",
)
async def get_audit_logs(
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_or_system),
):
    """Immutable audit trail of all autonomy evaluations, approvals, overrides, and dispatches."""
    res = await db.execute(
        select(AutonomyAuditLog).order_by(desc(AutonomyAuditLog.timestamp)).limit(limit)
    )
    return res.scalars().all()


@router.put(
    "/policy",
    summary="Update organizational Autonomy Budget policies (ADMIN only)",
)
async def update_policy(
    update_data: AutonomyPolicyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN"])),
):
    """Configures thresholds for auto-execution, error budgets, and critical service safeguards."""
    policy = await autonomy_budget_engine.get_or_create_policy(db)

    for field, val in update_data.model_dump(exclude_unset=True).items():
        setattr(policy, field, val)

    await db.flush()

    # Log policy change
    audit = AutonomyAuditLog(
        event_type="POLICY_UPDATED",
        service_name="SYSTEM",
        action="UPDATE_AUTONOMY_POLICY",
        user_id=current_user.id,
        user_role=current_user.role,
        user_username=current_user.username,
        decision="POLICY_UPDATED",
        details=update_data.model_dump(exclude_unset=True),
    )
    db.add(audit)
    await db.flush()

    return {
        "status": "UPDATED",
        "policy": {
            "low_risk_auto_execute": policy.low_risk_auto_execute,
            "medium_risk_requires_approval": policy.medium_risk_requires_approval,
            "critical_services_always_require_approval": policy.critical_services_always_require_approval,
            "min_historical_samples": policy.min_historical_samples,
            "error_budget_threshold_percent": policy.error_budget_threshold_percent,
            "max_auto_recovery_time_seconds": policy.max_auto_recovery_time_seconds,
        },
    }
