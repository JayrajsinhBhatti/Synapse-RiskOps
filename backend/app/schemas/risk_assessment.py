"""
Synapse RiskOps - Risk Assessment Schemas
=========================================
Owner: Person 2 | Week: 5
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class RiskAssessmentCreate(BaseModel):
    """Payload to record an ML Risk assessment snapshot."""

    service_id: Optional[UUID] = None
    service_name: Optional[str] = None
    risk_score: Decimal = Field(..., ge=0, le=100)
    confidence: Decimal = Field(..., ge=0, le=1)
    anomaly_score: Optional[Decimal] = None
    predicted_failure_time: Optional[datetime] = None
    affected_services: Optional[List[str]] = None
    features_used: Optional[Dict[str, Any]] = None
    model_version: Optional[str] = "v1.0.0"


class RiskAssessmentResponse(BaseModel):
    """Historical risk assessment record returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    service_id: UUID
    service_name: Optional[str] = None
    risk_score: Decimal
    confidence: Decimal
    anomaly_score: Optional[Decimal] = None
    predicted_failure_time: Optional[datetime] = None
    affected_services: Optional[List[str]] = None
    features_used: Optional[Dict[str, Any]] = None
    model_version: Optional[str] = None
    assessed_at: Optional[datetime] = None
