"""
Synapse RiskOps - Service & Topology API Schemas
================================================
Owner: Person 2 | Week: 5
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ServiceResponse(BaseModel):
    """Microservice component details."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    service_name: str
    service_type: str
    description: Optional[str] = None
    owner: Optional[str] = None
    criticality: str
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ServiceDependencyResponse(BaseModel):
    """Directed dependency edge between two microservices."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_service_id: UUID
    target_service_id: UUID
    source_service_name: Optional[str] = None
    target_service_name: Optional[str] = None
    dependency_type: str = "SYNC"
    created_at: Optional[datetime] = None


class ServiceTopologyResponse(BaseModel):
    """Full microservice dependency topology graph for dashboard visualization."""

    services: List[ServiceResponse]
    dependencies: List[ServiceDependencyResponse]
    total_services: int
    total_dependencies: int


class ServiceUpdateRequest(BaseModel):
    """Payload to update service configuration, criticality, or inclusion."""
    service_name: Optional[str] = None
    criticality: Optional[str] = Field(None, pattern="^(CRITICAL|HIGH|MEDIUM|LOW)$")
    is_active: Optional[bool] = None
    description: Optional[str] = None
    owner: Optional[str] = None


class BatchServiceConfigureItem(BaseModel):
    """Single service configuration item for onboarding review."""
    id: Optional[UUID] = None
    service_id: Optional[UUID] = None
    service_name: str
    display_name: Optional[str] = None
    criticality: str = Field("MEDIUM", pattern="^(CRITICAL|HIGH|MEDIUM|LOW)$")
    is_active: bool = True
    dependencies: Optional[List[str]] = []


class BatchServiceConfigureRequest(BaseModel):
    """Batch configure detected services during onboarding."""
    services: List[BatchServiceConfigureItem]

