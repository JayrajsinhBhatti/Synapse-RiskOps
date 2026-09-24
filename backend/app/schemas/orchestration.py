"""
Synapse RiskOps - Inter-Service Orchestration Schemas
=====================================================
Owner: Person 2 | Week: 5

Matches shared/schemas/incident_record.schema.json contract for full incident lifecycle:
Prediction -> Diagnosis -> Routing -> Automation -> Resolution
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class AnomalyDiagnosisRequest(BaseModel):
    """Request payload to trigger diagnosis & routing pipeline."""

    service_name: str = Field(..., description="Target service exhibiting anomalous telemetry")
    environment: str = Field(default="production", description="Runtime environment")
    metrics: Dict[str, float] = Field(..., description="Current telemetry metrics snapshot")
    scenario_id: Optional[str] = Field(default=None, description="Optional simulated scenario identifier")
    assigned_to: Optional[UUID] = None


class RankedRootCauseCandidate(BaseModel):
    service: str
    label: str
    confidence: float


class RemediationExecutionRequest(BaseModel):
    """Request to execute runbook remediation actions for an incident."""

    incident_id: UUID
    runbook_id: Optional[str] = None
    action: Optional[str] = None
    target: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class UnifiedIncidentRecordResponse(BaseModel):
    """Unified incident record matching shared/schemas/incident_record.schema.json."""

    incident_id: str
    created_at: str
    service: Dict[str, Any]
    prediction: Dict[str, Any]
    diagnosis: Dict[str, Any]
    routing: Dict[str, Any]
    automation: Dict[str, Any]
    lifecycle_status: str
