"""
Synapse RiskOps - Risk Assessment API
=====================================
Owner: Person 2 | Week: 5

APIs for storing and querying ML risk scores, anomaly assessments,
and failure forecasts evaluated by the RiskEngine.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models.risk_assessment import RiskAssessment
from app.models.service import Service
from app.models.user import User
from app.schemas.risk_assessment import (
    RiskAssessmentCreate,
    RiskAssessmentResponse,
)

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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
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

    assessment = RiskAssessment(
        service_id=service_id,
        risk_score=assessment_data.risk_score,
        confidence=assessment_data.confidence,
        anomaly_score=assessment_data.anomaly_score,
        predicted_failure_time=assessment_data.predicted_failure_time,
        affected_services=assessment_data.affected_services,
        features_used=assessment_data.features_used,
        model_version=assessment_data.model_version,
    )

    db.add(assessment)
    await db.flush()
    await db.refresh(assessment)

    return assessment


@router.get(
    "",
    response_model=List[RiskAssessmentResponse],
    summary="List historical risk assessments",
)
async def list_risk_assessments(
    service_id: Optional[UUID] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve historical risk assessments ordered by newest first."""
    query = select(RiskAssessment).order_by(RiskAssessment.assessed_at.desc())

    if service_id is not None:
        query = query.where(RiskAssessment.service_id == service_id)

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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve the most recent risk score record for each microservice."""
    # Distinct on service_id ordered by assessed_at desc
    subquery = (
        select(
            RiskAssessment.service_id,
            func.max(RiskAssessment.assessed_at).label("max_assessed_at"),
        )
        .group_by(RiskAssessment.service_id)
        .subquery()
    )

    query = (
        select(RiskAssessment)
        .join(
            subquery,
            (RiskAssessment.service_id == subquery.c.service_id)
            & (RiskAssessment.assessed_at == subquery.c.max_assessed_at),
        )
        .order_by(RiskAssessment.risk_score.desc())
    )

    result = await db.execute(query)
    latest_assessments = result.scalars().all()
    return latest_assessments
