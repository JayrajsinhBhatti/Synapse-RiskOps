"""
Synapse RiskOps - Service & Topology API
========================================
Owner: Person 2 | Week: 5

Provides service directory and dependency topology graph APIs.
Used by the frontend dashboard and orchestration pipeline.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models.service import Service, ServiceDependency
from app.models.user import User
from app.schemas.service import (
    ServiceDependencyResponse,
    ServiceResponse,
    ServiceTopologyResponse,
)

router = APIRouter(
    prefix="/api/services",
    tags=["Services & Topology"],
)


@router.get(
    "",
    response_model=List[ServiceResponse],
    summary="List all tracked microservices",
)
async def list_services(
    is_active: Optional[bool] = None,
    criticality: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all microservices registered in the platform."""
    query = select(Service).order_by(Service.service_name.asc())

    if is_active is not None:
        query = query.where(Service.is_active == is_active)
    if criticality is not None:
        query = query.where(Service.criticality == criticality.upper())

    result = await db.execute(query)
    services = result.scalars().all()
    return services


@router.get(
    "/topology",
    response_model=ServiceTopologyResponse,
    summary="Get microservice dependency topology graph",
)
async def get_topology(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns the complete microservice dependency graph (nodes + directed edges).
    Powers the React architecture map in Week 6.
    """
    # Fetch all services
    svc_result = await db.execute(select(Service).order_by(Service.service_name.asc()))
    services = svc_result.scalars().all()
    service_map = {s.id: s.service_name for s in services}

    # Fetch all dependencies
    dep_result = await db.execute(select(ServiceDependency))
    deps = dep_result.scalars().all()

    dep_responses = [
        ServiceDependencyResponse(
            id=d.id,
            source_service_id=d.source_service_id,
            target_service_id=d.target_service_id,
            source_service_name=service_map.get(d.source_service_id),
            target_service_name=service_map.get(d.target_service_id),
            dependency_type=d.dependency_type,
            created_at=d.created_at,
        )
        for d in deps
    ]

    return ServiceTopologyResponse(
        services=[ServiceResponse.model_validate(s) for s in services],
        dependencies=dep_responses,
        total_services=len(services),
        total_dependencies=len(deps),
    )


@router.get(
    "/{service_id}",
    response_model=ServiceResponse,
    summary="Get single service details by UUID",
)
async def get_service(
    service_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve details for a single microservice."""
    result = await db.execute(
        select(Service).where(Service.id == service_id)
    )
    service = result.scalar_one_or_none()

    if service is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found",
        )

    return service
