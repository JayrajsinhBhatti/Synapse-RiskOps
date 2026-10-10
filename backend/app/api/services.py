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
    BatchServiceConfigureRequest,
    ServiceDependencyResponse,
    ServiceResponse,
    ServiceTopologyResponse,
    ServiceUpdateRequest,
)

router = APIRouter(
    prefix="/api/services",
    tags=["Services & Topology"],
)


from app.models.retention import WorkspaceSetting


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
    # Check active workspace mode
    setting_res = await db.execute(
        select(WorkspaceSetting).where(WorkspaceSetting.key == "system_mode")
    )
    setting = setting_res.scalar_one_or_none()
    is_ext_connected = bool(setting and isinstance(setting.value, dict) and setting.value.get("external_app_connected"))
    active_svcs = setting.value.get("config", {}).get("services") if (setting and is_ext_connected) else None

    query = select(Service).order_by(Service.service_name.asc())

    if is_ext_connected and active_svcs:
        query = query.where(Service.service_name.in_(active_svcs))

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
    # Check active workspace mode
    setting_res = await db.execute(
        select(WorkspaceSetting).where(WorkspaceSetting.key == "system_mode")
    )
    setting = setting_res.scalar_one_or_none()
    is_ext_connected = bool(setting and isinstance(setting.value, dict) and setting.value.get("external_app_connected"))
    active_svcs = setting.value.get("config", {}).get("services") if (setting and is_ext_connected) else None

    # Fetch services
    svc_query = select(Service).order_by(Service.service_name.asc())
    if is_ext_connected and active_svcs:
        svc_query = svc_query.where(Service.service_name.in_(active_svcs))

    svc_result = await db.execute(svc_query)
    services = svc_result.scalars().all()
    service_map = {s.id: s.service_name for s in services}
    service_ids = set(service_map.keys())

    # Fetch dependencies scoped to active services
    dep_query = select(ServiceDependency)
    if is_ext_connected and service_ids:
        dep_query = dep_query.where(
            ServiceDependency.source_service_id.in_(service_ids),
            ServiceDependency.target_service_id.in_(service_ids),
        )

    dep_result = await db.execute(dep_query)
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


@router.patch(
    "/{service_id}",
    response_model=ServiceResponse,
    summary="Update service attributes (rename, criticality, exclude/include)",
)
async def update_service(
    service_id: UUID,
    payload: ServiceUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update service attributes such as name, criticality, or exclusion status."""
    result = await db.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()

    if service is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found",
        )

    if payload.service_name is not None and payload.service_name.strip():
        service.service_name = payload.service_name.strip()
    if payload.criticality is not None:
        service.criticality = payload.criticality.upper()
    if payload.is_active is not None:
        service.is_active = payload.is_active
    if payload.description is not None:
        service.description = payload.description
    if payload.owner is not None:
        service.owner = payload.owner

    await db.commit()
    await db.refresh(service)
    return service


@router.post(
    "/batch-configure",
    response_model=List[ServiceResponse],
    summary="Batch configure detected services during onboarding review",
)
async def batch_configure_services(
    payload: BatchServiceConfigureRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Allows the customer to review, rename, exclude, and assign criticality
    to detected microservices before launching the platform pipeline.
    """
    updated_services: List[Service] = []

    for item in payload.services:
        # Search by id if provided, otherwise by service_name
        service = None
        lookup_id = item.id or item.service_id
        if lookup_id:
            res = await db.execute(select(Service).where(Service.id == lookup_id))
            service = res.scalar_one_or_none()

        if service is None:
            res = await db.execute(select(Service).where(Service.service_name == item.service_name))
            service = res.scalar_one_or_none()

        if service is None:
            # Create new service if not found
            service = Service(
                service_name=item.display_name or item.service_name,
                service_type="MICROSERVICE",
                criticality=item.criticality.upper(),
                is_active=item.is_active,
            )
            db.add(service)
        else:
            if item.display_name and item.display_name.strip():
                service.service_name = item.display_name.strip()
            elif item.service_name and item.service_name.strip():
                service.service_name = item.service_name.strip()
            service.criticality = item.criticality.upper()
            service.is_active = item.is_active

        updated_services.append(service)

    await db.commit()
    for s in updated_services:
        await db.refresh(s)

    return updated_services

