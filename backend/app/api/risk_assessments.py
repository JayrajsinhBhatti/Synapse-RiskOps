"""
Synapse RiskOps - Risk Assessment API
=====================================
Owner: Person 2 | Week: 5

APIs for storing and querying ML risk scores, anomaly assessments,
and failure forecasts evaluated by the RiskEngine.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user, get_current_user_or_system, require_role
from app.core.database import get_db
from app.models.risk_assessment import RiskAssessment
from app.models.service import Service
from app.models.user import User
from app.schemas.risk_assessment import (
    RiskAssessmentCreate,
    RiskAssessmentResponse,
)
from app.services.sse_manager import sse_manager

router = APIRouter(
    prefix="/api/risk-assessments",
    tags=["Risk Assessments"],
)


@router.post(
    "",
    response_model=RiskAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record ML risk assessment snapshot",
)
async def create_risk_assessment(
    assessment_data: RiskAssessmentCreate,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_or_system),
):
    """
    Ingest a new risk assessment snapshot from ML Engine.
    Resolves service_name to service_id if needed.
    """
    service_id = assessment_data.service_id

    # If service_name is provided, lookup service
    if not service_id and assessment_data.service_name:
        svc_res = await db.execute(
            select(Service).where(Service.service_name == assessment_data.service_name)
        )
        svc = svc_res.scalar_one_or_none()
        if svc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Service '{assessment_data.service_name}' not found",
            )
        service_id = svc.id

    if not service_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either service_id or service_name must be provided",
        )

    active_mode = getattr(assessment_data, "data_mode", None)
    if not active_mode and request:
        active_mode = request.headers.get("x-synapse-mode")
    active_mode = (active_mode or "demo").lower()

    assessment = RiskAssessment(
        service_id=service_id,
        risk_score=assessment_data.risk_score,
        confidence=assessment_data.confidence,
        anomaly_score=assessment_data.anomaly_score,
        predicted_failure_time=assessment_data.predicted_failure_time,
        affected_services=assessment_data.affected_services,
        features_used=assessment_data.features_used,
        model_version=assessment_data.model_version,
        data_mode=active_mode,
    )

    db.add(assessment)
    await db.commit()
    await db.refresh(assessment)

    return assessment


@router.get(
    "",
    response_model=List[RiskAssessmentResponse],
    summary="List historical risk assessments",
)
async def list_risk_assessments(
    service_id: Optional[UUID] = None,
    mode: Optional[str] = Query(default=None, description="Filter by operational mode ('demo' or 'connected')"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_or_system),
):
    """Retrieve historical risk assessments ordered by newest first."""
    query = select(RiskAssessment).order_by(RiskAssessment.assessed_at.desc())

    if service_id is not None:
        query = query.where(RiskAssessment.service_id == service_id)

    active_mode = mode
    if not active_mode and request:
        active_mode = request.headers.get("x-synapse-mode")
    if active_mode:
        query = query.where(RiskAssessment.data_mode == active_mode.lower())

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    assessments = result.scalars().all()
    return assessments


@router.get(
    "/latest",
    response_model=List[RiskAssessmentResponse],
    summary="Get latest risk assessment for each service",
)
async def get_latest_risk_assessments(
    mode: Optional[str] = Query(default=None, description="Filter by operational mode ('demo' or 'connected')"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_or_system),
):
    """Retrieve the most recent risk score record for each microservice."""
    active_mode = mode
    if not active_mode and request:
        active_mode = request.headers.get("x-synapse-mode")

    sub_q = select(
        RiskAssessment.service_id,
        func.max(RiskAssessment.assessed_at).label("max_assessed_at"),
    )
    if active_mode:
        sub_q = sub_q.where(RiskAssessment.data_mode == active_mode.lower())
    subquery = sub_q.group_by(RiskAssessment.service_id).subquery()

    query = (
        select(RiskAssessment, Service.service_name)
        .join(
            subquery,
            (RiskAssessment.service_id == subquery.c.service_id)
            & (RiskAssessment.assessed_at == subquery.c.max_assessed_at),
        )
        .outerjoin(Service, RiskAssessment.service_id == Service.id)
        .order_by(RiskAssessment.risk_score.desc())
    )
    if active_mode:
        query = query.where(RiskAssessment.data_mode == active_mode.lower())

    result = await db.execute(query)
    rows = result.all()
    latest_assessments = []
    for ra, svc_name in rows:
        resp = RiskAssessmentResponse.model_validate(ra)
        resp.service_name = svc_name
        latest_assessments.append(resp)
    return latest_assessments


@router.delete(
    "",
    status_code=status.HTTP_200_OK,
    summary="Purge all risk assessment records matching active mode (requires confirmation & role)",
)
async def delete_all_risk_assessments(
    confirm_all: bool = Query(False, description="Must be true to confirm bulk deletion"),
    mode: Optional[str] = Query(None, description="'demo', 'connected', or omit to purge all"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "SRE"])),
):
    """
    Bulk delete all historical risk assessments from PostgreSQL.
    Requires explicit confirmation flag (confirm_all=True) and ADMIN or SRE role.
    Respects active operational mode ('demo' or 'connected').
    """
    if not confirm_all:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bulk deletion requires confirm_all=true query parameter.",
        )

    active_mode = mode
    if not active_mode and request:
        active_mode = request.headers.get("x-synapse-mode")

    query = delete(RiskAssessment)
    if active_mode:
        query = query.where(RiskAssessment.data_mode == active_mode.lower())

    result = await db.execute(query)
    deleted_count = result.rowcount or 0
    await db.commit()

    await sse_manager.broadcast_risk_assessments_bulk_deleted(count=deleted_count, mode=active_mode)

    return {
        "status": "success",
        "deleted_count": deleted_count,
        "mode": active_mode or "all",
        "message": f"Successfully deleted {deleted_count} risk assessment records.",
    }


@router.delete(
    "/{assessment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an individual historical risk assessment record",
)
async def delete_risk_assessment(
    assessment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an individual risk assessment record by UUID."""
    result = await db.execute(
        select(RiskAssessment).where(RiskAssessment.id == assessment_id)
    )
    assessment = result.scalar_one_or_none()

    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Risk assessment record not found",
        )

    await db.delete(assessment)
    await db.commit()

    await sse_manager.broadcast_risk_assessment_deleted(assessment_id)

    return None
