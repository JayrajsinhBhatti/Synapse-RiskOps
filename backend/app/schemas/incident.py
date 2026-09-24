"""
Synapse RiskOps - Incident API Schemas
======================================
Owner: Person 2 | Week: 5
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IncidentCreate(BaseModel):
    """Data required to create an incident."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
    )

    description: Optional[str] = None

    severity: str = Field(
        default="MEDIUM",
        max_length=20,
    )

    service_id: Optional[UUID] = None

    assigned_to: Optional[UUID] = None

    risk_score: Optional[Decimal] = None

    confidence: Optional[Decimal] = None

    predicted_failure: Optional[datetime] = None


class IncidentUpdate(BaseModel):
    """Fields that can be updated on an incident."""

    title: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    description: Optional[str] = None

    severity: Optional[str] = Field(
        default=None,
        max_length=20,
    )

    status: Optional[str] = Field(
        default=None,
        max_length=20,
    )

    service_id: Optional[UUID] = None

    assigned_to: Optional[UUID] = None

    risk_score: Optional[Decimal] = None

    confidence: Optional[Decimal] = None

    predicted_failure: Optional[datetime] = None

    resolved_at: Optional[datetime] = None


class IncidentResponse(BaseModel):
    """Incident returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: Optional[str] = None
    severity: str
    status: str

    service_id: Optional[UUID] = None

    risk_score: Optional[Decimal] = None
    confidence: Optional[Decimal] = None
    predicted_failure: Optional[datetime] = None

    detected_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    assigned_to: Optional[UUID] = None
    created_by: Optional[UUID] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class IncidentHistoryResponse(BaseModel):
    """Audit trail record for an incident mutation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    incident_id: UUID
    action: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    changed_by: Optional[UUID] = None
    changed_at: Optional[datetime] = None